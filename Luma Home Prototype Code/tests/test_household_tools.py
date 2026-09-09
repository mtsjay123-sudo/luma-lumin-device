import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from luma.agent.household import Household
from luma.memory.store import Store


class HouseholdToolsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store = Store(self.root / "state.db", self.root / "state.key")
        self.now = datetime(2026, 9, 8, 12, tzinfo=ZoneInfo("America/New_York")).timestamp()
        self.home = Household(self.store, now=lambda: self.now)

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def reopen(self):
        self.store.close()
        self.store = Store(self.root / "state.db", self.root / "state.key")
        self.home = Household(self.store, now=lambda: self.now)

    def test_timer_survives_restart_and_recovers_missed_alarm_once(self):
        timer = self.home.start_timer("Pasta", 60)
        self.now += 90
        self.reopen()
        recovered = self.home.timers()[0]
        self.assertEqual(recovered["id"], timer["id"])
        self.assertEqual(recovered["state"], "elapsed")
        self.assertEqual(recovered["remaining_seconds"], 0)
        self.assertEqual(recovered["overdue_seconds"], 30)
        self.assertTrue(recovered["elapsed_while_stopped"])
        event = self.home.timer_events()[0]
        self.assertIn("not running", event["text"])
        self.assertEqual(self.home.timer_events(), [])
        self.reopen()
        self.assertEqual(self.home.timer_events(), [])

    def test_restarted_running_timer_does_not_claim_it_elapsed_offline(self):
        self.home.start_timer("Tea", 60)
        self.now += 10
        self.reopen()
        self.assertTrue(self.home.timers()[0]["recovered_after_restart"])
        self.now += 55
        event = self.home.timer_events()[0]
        self.assertFalse(event["elapsed_while_stopped"])
        self.assertNotIn("not running", event["text"])

    def test_pause_resume_keeps_exact_remaining_time_across_restart(self):
        timer = self.home.start_timer("Bread", 120)
        self.now += 25.5
        paused = self.home.timer_action(timer["id"], "pause")
        self.assertEqual(paused["remaining_seconds"], 94.5)
        self.now += 300
        self.reopen()
        self.assertEqual(self.home.timers()[0]["remaining_seconds"], 94.5)
        self.home.timer_action("bread", "resume")
        self.now += 94
        self.assertEqual(self.home.timers()[0]["state"], "running")
        self.assertEqual(self.home.timers()[0]["remaining_seconds"], 1)
        self.now += 0.5
        self.assertEqual(self.home.timers()[0]["state"], "elapsed")

    def test_invalid_timer_transitions_never_resurrect_finished_timer(self):
        timer = self.home.start_timer("Eggs", 10)
        with self.assertRaises(ValueError):
            self.home.timer_action(timer["id"], "resume")
        self.home.timer_action(timer["id"], "cancel")
        self.now += 30
        self.assertEqual(self.home.timer_events(), [])
        for action in ["pause", "resume", "acknowledge", "cancel"]:
            with self.assertRaises(ValueError):
                self.home.timer_action(timer["id"], action)

    def test_named_timers_are_distinct_and_validate_duration(self):
        self.home.start_timer("Rice", 30)
        with self.assertRaises(ValueError):
            self.home.start_timer(" rice ", 60)
        self.home.start_timer("Sauce", 60)
        self.assertEqual(len(self.home.timers()), 2)
        for duration in [0, -1, 86401, True, 1.2, "30"]:
            with self.assertRaises(ValueError):
                self.home.start_timer("Invalid", duration)

    def test_quiet_hours_and_hush_preserve_due_alarms_for_later(self):
        self.store.set_setting("quiet_hours", [11, 13])
        self.home.start_timer("Cake", 5)
        self.now += 10
        self.assertEqual(self.home.timer_events(), [])
        self.assertFalse(self.home.timers()[0]["announced"])
        self.store.set_setting("quiet_hours", [0, 0])
        self.store.set_setting("hush_until", self.now + 50)
        self.assertEqual(self.home.timer_events(), [])
        self.now += 60
        self.assertEqual(self.home.timer_events(deliver=False), [])
        self.assertEqual(len(self.home.timer_events()), 1)

    def test_concurrent_timer_delivery_with_shared_store_claims_once(self):
        self.home.start_timer("Soup", 1)
        self.now += 2
        with ThreadPoolExecutor(4) as pool:
            batches = list(pool.map(lambda _: self.home.timer_events(), range(4)))
        self.assertEqual(sum(len(batch) for batch in batches), 1)

    def test_household_notes_are_encrypted_editable_searchable_and_removable(self):
        note = self.home.save_record("location", "Spare keys", "In the purple drawer under the private lighthouse ornament")
        self.assertNotIn(b"lighthouse", self.store.db_path.read_bytes())
        self.assertEqual(self.home.records(query="keys")[0]["id"], note["id"])
        edited = self.home.save_record("location", "Spare keys", "In the hall cupboard", id=note["id"])
        self.assertEqual(edited["id"], note["id"])
        self.assertEqual(len(self.home.records()), 1)
        self.assertEqual(self.home.records(query="purple"), [])
        self.reopen()
        self.assertEqual(self.home.records()[0]["details"], "In the hall cupboard")
        self.assertTrue(self.home.delete_record(note["id"]))
        self.assertEqual(self.home.records(), [])

    def test_note_edit_by_title_updates_original_id(self):
        note = self.home.save_record("pantry", "Flour", "Two bags")
        edited = self.home.save_record("pantry", "Flour", "One bag", id="Flour")
        self.assertEqual(edited["id"], note["id"])
        self.assertEqual(len(self.home.records()), 1)

    def test_household_modes_keep_child_records_isolated(self):
        adult = self.home.save_record("preference", "Gift", "Surprise birthday details")
        self.home.save_record("preference", "Favorite snack", "Apples", mode="kids")
        timer = self.home.start_timer("Adult dinner", 30)
        self.assertEqual(len(self.home.records(mode="study")), 1)
        self.assertEqual(self.home.records(mode="kids")[0]["title"], "Favorite snack")
        self.assertEqual(self.home.timers(mode="kids"), [])
        with self.assertRaises(ValueError):
            self.home.delete_record(adult["id"], mode="kids")
        with self.assertRaises(ValueError):
            self.home.timer_action(timer["id"], "cancel", mode="kids")

    def test_sensitive_records_and_unsafe_source_urls_are_rejected(self):
        for details in ["password: unsafe-example", "card number: 4111111111111111"]:
            with self.assertRaises(ValueError):
                self.home.save_record("preference", "Do not save", details)
        for url in ["javascript:alert(1)", "file:///etc/passwd", "https://name:password@example.test/manual", "http://example.test/manual"]:
            with self.assertRaises(ValueError):
                self.home.save_record("manual", "Oven", "Instructions", source_url=url)
        with self.assertRaises(ValueError):
            self.home.save_record("warranty", "Fridge", "Proof of purchase is in the folder", due_date="2026-02-30")
        self.assertEqual(self.home.records(), [])

    def test_recipe_progress_preserves_steps_across_interruptions_and_restart(self):
        recipe = self.home.save_recipe("Pasta", ["Boil the water", "Add pasta", "Drain"], ["Pasta", "Water"])
        self.home.recipe_action(recipe["id"], "start")
        self.home.recipe_action(recipe["id"], "next")
        self.home.recipe_action(recipe["id"], "pause")
        self.reopen()
        self.assertEqual(self.home.recipes()[0]["step_number"], 2)
        with self.assertRaises(ValueError):
            self.home.recipe_action(recipe["id"], "next")
        self.home.recipe_action(recipe["id"], "resume")
        repeated = self.home.recipe_action(recipe["id"], "repeat")
        self.assertEqual(repeated["current_step"], "Add pasta")
        self.home.recipe_action(recipe["id"], "next")
        with self.assertRaises(ValueError):
            self.home.recipe_action(recipe["id"], "next")
        self.assertEqual(self.home.recipe_action(recipe["id"], "finish")["state"], "finished")

    def test_recipe_edit_clamps_cursor_without_losing_original_identity(self):
        recipe = self.home.save_recipe("Salad", ["Wash", "Chop", "Dress"])
        self.home.recipe_action(recipe["id"], "start")
        self.home.recipe_action(recipe["id"], "next")
        self.home.recipe_action(recipe["id"], "next")
        revised = self.home.save_recipe("Salad", ["Wash", "Toss"], id="Salad")
        self.assertEqual(revised["id"], recipe["id"])
        self.assertEqual(revised["current_step"], "Toss")
        self.assertEqual(revised["state"], "cooking")
        self.assertEqual(len(self.home.recipes()), 1)

    def test_briefing_uses_current_local_facts_and_filters_finished_and_child_tasks(self):
        self.store.put("task", {"title": "Call the plumber", "due": self.now + 3600, "done": False, "mode": "friend"})
        self.store.put("task", {"title": "Already completed", "due": self.now - 3600, "done": True, "mode": "friend"})
        self.store.put("task", {"title": "Child private reminder", "due": self.now, "done": False, "mode": "kids"})
        self.store.put("task", {"title": "Next week", "due": self.now + 7 * 86400, "done": False, "mode": "study"})
        self.store.put("routine", {"title": "Water plants", "at": "17:00", "enabled": True, "last_day": None, "mode": "friend"})
        self.home.save_record("maintenance", "Replace filter", "Use the size printed on the unit", due_date="2026-09-07")
        brief = self.home.briefing()
        self.assertIn("Call the plumber", brief["text"])
        self.assertIn("Replace filter", brief["text"])
        self.assertIn("Water plants", brief["text"])
        self.assertEqual(brief["unfinished_count"], 2)
        self.assertNotIn("Already completed", brief["text"])
        self.assertNotIn("Child private", brief["text"])
        self.assertIn("external calendars", brief["scope"])

    def test_requested_briefing_works_during_quiet_but_proactive_waits_and_runs_once(self):
        self.store.put("task", {"title": "Check garden", "due": self.now, "done": False, "mode": "friend"})
        self.store.set_setting("quiet_hours", [11, 13])
        self.assertIsNone(self.home.briefing(proactive=True))
        self.assertIsNotNone(self.home.briefing())
        self.store.set_setting("quiet_hours", [0, 0])
        self.assertIsNotNone(self.home.briefing(proactive=True))
        self.assertIsNone(self.home.briefing(proactive=True))
        self.assertIsNotNone(self.home.briefing())

    def test_quiet_hours_across_midnight_and_no_empty_proactive_briefing(self):
        self.assertIsNone(self.home.briefing(proactive=True))
        for hour, expected in [(22, False), (23, True), (0, True), (6, True), (7, False)]:
            self.now = datetime(2026, 9, 8, hour, tzinfo=ZoneInfo("America/New_York")).timestamp()
            self.assertEqual(self.home.is_quiet(), expected)

    def test_fast_commands_create_exact_named_timers_without_claiming_external_actions(self):
        result = self.home.command("Set a pasta timer for 10 minutes.")
        self.assertEqual(result["timer"]["duration_seconds"], 600)
        self.assertEqual(result["timer"]["name"], "pasta")
        self.assertEqual(self.home.command("Pause the pasta timer")["timer"]["state"], "paused")
        self.assertEqual(self.home.command("Resume pasta timer")["timer"]["state"], "running")
        self.assertIsNone(self.home.command("Could you explain why cooking timers are useful?"))
        self.assertIsNone(self.home.command("Order these groceries and text Mom"))

    def test_ambiguous_recipe_command_requests_selection_and_keeps_both_cursors(self):
        for title in ["Soup", "Salad"]:
            recipe = self.home.save_recipe(title, ["Prepare", "Finish"])
            self.home.recipe_action(recipe["id"], "start")
        result = self.home.command("next step")
        self.assertIn("Choose the recipe", result["text"])
        self.assertEqual([r["step_number"] for r in self.home.recipes()], [1, 1])


if __name__ == "__main__":
    unittest.main()

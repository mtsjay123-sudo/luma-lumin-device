"""Gmail and 1,500+ apps through one hub (Composio), the way Open Dot does it: two clicks to connect, reading runs on its
own, and anything that sends, posts, creates or deletes waits for the owner's yes."""
import shlex
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from test_dots_features import agent_with
from luma.agent import runtime

HUB = Path(__file__).parent / "fixtures" / "mcp" / "apps_hub.py"


class AppsHubTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.agent, self.store = agent_with(Path(self.temp.name))
        self.agent.oauth_redirect = "http://127.0.0.1:8095/api/connect/oauth/callback"

    def tearDown(self):
        self.agent.connectors.close()
        runtime.register_connector_tools({})
        self.store.close()
        self.temp.cleanup()

    def add_hub(self):
        app = self.agent.connectors.add("Apps", command=f"{shlex.quote(sys.executable)} {shlex.quote(str(HUB))}")
        self.agent.enable("connectors", True)
        return app

    def test_the_hub_never_hands_luma_a_remote_shell(self):
        app = self.add_hub()
        names = {t["name"] for t in app["tools"]}
        self.assertIn("COMPOSIO_MULTI_EXECUTE_TOOL", names)
        self.assertNotIn("COMPOSIO_REMOTE_BASH_TOOL", names)
        self.assertEqual(self.agent.connectors.hub(), "apps")

    def test_reading_runs_on_its_own_and_sending_waits_for_a_yes(self):
        self.add_hub()
        run = "mcp.apps.composio_multi_execute_tool"
        fetch = {"tools": '[{"tool_slug": "GMAIL_FETCH_EMAILS", "arguments": {"max_results": 5}}]', "thought": ""}
        read = self.agent.propose(run, fetch)
        self.assertNotEqual(read.get("state"), "pending")
        self.assertIn("Lunch Friday?", read["text_from_app"])
        send = {"tools": '[{"tool_slug": "GMAIL_SEND_EMAIL", "arguments": {"recipient_email": "sam@example.com", "subject": "Lunch", "body": "Friday works"}}]', "thought": ""}
        pending = self.agent.propose(run, send)
        self.assertEqual(pending["state"], "pending")  # nothing sent yet
        self.assertEqual(pending["review"]["app"], "Gmail")
        self.assertEqual(pending["review"]["does"], "send email")
        self.assertEqual(pending["review"]["recipient email"], "sam@example.com")
        done = self.agent.confirm(pending["action"], pending["confirm_token"])
        self.assertIn("GMAIL_SEND_EMAIL", done["text_from_app"])
        mixed = {"tools": '[{"tool_slug": "GMAIL_FETCH_EMAILS"}, {"tool_slug": "GMAIL_DELETE_MESSAGE"}]', "thought": ""}
        self.assertEqual(self.agent.propose(run, mixed)["state"], "pending")  # one change in the batch: the whole batch asks
        from luma.integrations.connectors import only_reads
        self.assertTrue(only_reads("GMAIL_FETCH_EMAILS") and only_reads("GOOGLECALENDAR_EVENTS_LIST"))
        for change in ["GMAIL_SEND_EMAIL", "SLACK_SEARCH_AND_DELETE_MESSAGES", "GMAIL_LIST_AND_TRASH", "GITHUB_CREATE_ISSUE", "", None]:
            self.assertFalse(only_reads(change), change)  # a name that changes anything always asks
        self.assertTrue(self.agent.connectors.reads_only("mcp.apps.composio_manage_connections", {"toolkits": '[{"name": "gmail", "action": "list"}]'}))
        self.assertFalse(self.agent.connectors.reads_only("mcp.apps.composio_manage_connections", {"toolkits": '[{"name": "gmail", "action": "add"}]'}))

    def test_connect_my_gmail_is_two_clicks(self):
        with mock.patch.object(self.agent.connectors, "sign_in_start", return_value={"auth_url": "https://connect.composio.dev/authorize?x=1"}) as start:
            reply = self.agent.chat("yo connect my gmail")
        self.assertEqual(reply["open_url"], "https://connect.composio.dev/authorize?x=1")  # step one: sign in to the hub, opened for them
        self.assertIn("two clicks", reply["text"])
        self.assertIn("ask before I send", reply["text"])
        self.assertEqual(start.call_args.kwargs["then"], "gmail")  # step two follows on its own after sign-in
        self.add_hub()
        reply = self.agent.chat("connect my gmail")
        self.assertTrue(reply["open_url"].startswith("https://accounts.google.com/"))  # with the hub in place: straight to Google's Allow
        self.assertIn("&app=gmail", reply["open_url"])
        self.assertIn("already connected", self.agent.chat("hook up gmail")["text"])
        self.assertIn("accounts.google.com", self.agent.chat("can you connect my slack")["open_url"])

    def test_after_signing_in_the_browser_goes_straight_to_the_apps_allow_page(self):
        connectors = self.agent.connectors
        connectors._signins = {"st": {"name": "Apps", "url": "https://connect.composio.dev/mcp", "client_id": "c", "token_endpoint": "https://t/token",
                                      "verifier": "v", "redirect_uri": self.agent.oauth_redirect, "at": __import__("time").time(), "then": "gmail"}}
        with mock.patch.object(connectors, "_json", return_value={"access_token": "a"}), \
                mock.patch.object(connectors, "add", return_value={"id": "apps", "name": "Apps"}), \
                mock.patch.object(connectors, "app_link", return_value="https://accounts.google.com/o/oauth2/v2/auth?app=gmail"):
            done = connectors.sign_in_finish("st", "code")
        self.assertEqual(done["then_app"], "Gmail")
        self.assertTrue(done["then_url"].startswith("https://accounts.google.com/"))

    def test_kids_cant_connect_apps(self):
        self.store.set_setting("mode", "kids")
        self.assertNotIn("open_url", self.agent.connect_app("gmail"))


if __name__ == "__main__":
    unittest.main()

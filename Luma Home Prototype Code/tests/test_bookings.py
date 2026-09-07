"""Booking adapter checks use only a deterministic in-memory HTTP fixture."""
import copy
import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from luma.integrations.bookings import CalBookings
from luma.integrations.providers import OutcomeUnknown, ProviderError
from luma.memory.store import Store


class CalFixture:
    def __init__(self):
        self.calls = []
        self.event = {"id": 42, "title": "Studio consultation", "price": 0,
                      "lengthInMinutes": 30, "locations": [{"type": "integration"}]}
        self.slots = {"2026-09-08": [{"start": "2026-09-08T10:00:00-04:00", "end": "2026-09-08T10:30:00-04:00"}]}
        self.booking = {"uid": "fixture_booking_123", "eventTypeId": 42, "status": "accepted",
                        "start": "2026-09-08T14:00:00Z", "end": "2026-09-08T14:30:00Z", "title": "Studio consultation"}
        self.post_error = None
        self.post_result = None
        self.disappear = False
        self.slot_gets = 0

    def __call__(self, method, url, headers, payload=None, **kwargs):
        self.calls.append((method, url, copy.deepcopy(headers), copy.deepcopy(payload)))
        path = urlsplit(url).path
        if method == "POST":
            if self.post_error:
                raise self.post_error
            return copy.deepcopy(self.post_result if self.post_result is not None else {"status": "success", "data": self.booking})
        if path.startswith("/v2/event-types/"):
            return {"status": "success", "data": copy.deepcopy(self.event)}
        if path == "/v2/slots":
            self.slot_gets += 1
            return {"status": "success", "data": {} if self.disappear and self.slot_gets > 1 else copy.deepcopy(self.slots)}
        if path.startswith("/v2/bookings/"):
            return {"status": "success", "data": copy.deepcopy(self.booking)}
        raise AssertionError("Unexpected fixture route")

    @property
    def posts(self):
        return [r for r in self.calls if r[0] == "POST"]


class BookingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        p = Path(self.temp.name)
        self.store = Store(p / "db", p / "key")
        self.now = datetime(2026, 9, 7, 12, tzinfo=timezone.utc).timestamp()
        self.env = {"CAL_COM_API_KEY": "fixture-not-a-real-key", "LUMA_CAL_EVENT_TYPES_JSON": '{"consultation":42}'}
        self.http = CalFixture()
        self.adapter = CalBookings(self.store, self.env, self.http, lambda: self.now)

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def availability(self):
        return self.adapter.availability({"service": "consultation", "start": "2026-09-08", "end": "2026-09-09", "time_zone": "America/New_York"})

    def args(self):
        offer = self.availability()["slots"][0]
        return {"offer_id": offer["offer_id"], "name": "Test Attendee", "email": "fixture@example.test"}

    def test_real_slot_times_are_bound_to_opaque_offer_and_timezone(self):
        data = self.availability()
        slot = data["slots"][0]
        self.assertEqual(slot["start"], "2026-09-08T14:00:00Z")
        self.assertEqual(slot["local_start"], "2026-09-08T10:00:00-04:00")
        self.assertEqual(slot["expires"], self.now + 600)
        query = parse_qs(urlsplit(self.http.calls[1][1]).query)
        self.assertEqual(query["start"], ["2026-09-08T04:00:00Z"])
        self.assertEqual(query["end"], ["2026-09-09T04:00:00Z"])
        self.assertEqual(query["format"], ["range"])
        self.assertFalse(self.http.posts)

    def test_forged_offer_or_extra_date_cannot_be_booked(self):
        with self.assertRaises(ValueError):
            self.adapter.create({"offer_id": "invented", "name": "Test", "email": "fixture@example.test"})
        args = self.args()
        with self.assertRaises(ValueError):
            self.adapter.create({**args, "start": "2026-09-09T14:00:00Z"})
        self.assertFalse(self.http.posts)

    def test_preview_does_not_send_and_create_uses_exact_reviewed_details(self):
        args = self.args()
        preview = self.adapter.preview(args)
        self.assertEqual(preview["attendee"]["time_zone"], "America/New_York")
        self.assertFalse(self.http.posts)
        receipt = self.adapter.create(args)
        self.assertTrue(receipt["confirmed"])
        method, url, headers, payload = self.http.posts[0]
        self.assertEqual(headers["cal-api-version"], "2026-02-25")
        self.assertEqual(payload["start"], preview["start"])
        self.assertEqual(payload["eventTypeId"], 42)
        self.assertEqual(payload["attendee"], {"name": "Test Attendee", "email": "fixture@example.test", "timeZone": "America/New_York"})
        self.assertNotIn("allowConflicts", payload)
        self.assertNotIn("allowBookingOutOfBounds", payload)

    def test_pending_is_not_claimed_as_confirmed(self):
        self.http.booking["status"] = "pending"
        result = self.adapter.create(self.args())
        self.assertFalse(result["confirmed"])
        self.assertIn("awaiting", result["summary"])

    def test_offer_expiry_and_restart_require_fresh_search(self):
        args = self.args()
        self.now += 601
        with self.assertRaises(ValueError):
            self.adapter.create(args)
        self.adapter = CalBookings(self.store, self.env, self.http, lambda: self.now)
        with self.assertRaises(ValueError):
            self.adapter.create(args)
        self.assertFalse(self.http.posts)

    def test_concurrent_duplicate_confirmation_sends_once(self):
        args = self.args()
        def create():
            try:
                return self.adapter.create(args)
            except ValueError:
                return None
        with ThreadPoolExecutor(2) as pool:
            list(pool.map(lambda _: create(), range(2)))
        self.assertEqual(len(self.http.posts), 1)

    def test_unknown_outcome_blocks_new_offer_even_after_restart(self):
        self.http.post_error = OutcomeUnknown("Fixture uncertain response")
        with self.assertRaises(OutcomeUnknown):
            self.adapter.create(self.args())
        self.adapter = CalBookings(self.store, self.env, self.http, lambda: self.now)
        with self.assertRaisesRegex(ProviderError, "uncertain attempt"):
            self.adapter.create(self.args())
        self.assertEqual(len(self.http.posts), 1)
        self.assertNotIn(b"fixture@example.test", self.store.db_path.read_bytes())

    def test_missing_receipt_is_unknown_and_not_retried(self):
        self.http.post_result = {"status": "success", "data": {}}
        with self.assertRaises(OutcomeUnknown):
            self.adapter.create(self.args())
        with self.assertRaises(ProviderError):
            self.adapter.create(self.args())
        self.assertEqual(len(self.http.posts), 1)

    def test_changed_slot_receipt_is_unknown(self):
        self.http.booking["start"] = "2026-09-08T15:00:00Z"
        with self.assertRaises(OutcomeUnknown):
            self.adapter.create(self.args())
        self.assertEqual(self.store.all("booking"), [])

    def test_no_alternative_time_when_slot_disappears(self):
        self.http.disappear = True
        with self.assertRaisesRegex(ProviderError, "no longer available"):
            self.adapter.create(self.args())
        self.assertFalse(self.http.posts)

    def test_price_and_duration_are_rechecked_at_submission(self):
        args = self.args()
        self.http.event["price"] = 2500
        with self.assertRaisesRegex(ProviderError, "verified as free"):
            self.adapter.create(args)
        self.assertFalse(self.http.posts)

    def test_paid_recurring_and_multiple_location_services_are_rejected(self):
        for update in [{"price": 1}, {"recurrence": {"occurrences": 3, "disabled": False}}, {"locations": [{"type": "address"}, {"type": "integration"}]}]:
            previous = copy.deepcopy(self.http.event)
            self.http.event.update(update)
            with self.assertRaises(ProviderError):
                self.availability()
            self.http.event = previous
        self.assertFalse(self.http.posts)

    def test_status_only_reads_known_receipts_and_reports_changes(self):
        with self.assertRaises(ValueError):
            self.adapter.status({"booking_uid": "somebody_elses_booking"})
        self.assertFalse(self.http.calls)
        created = self.adapter.create(self.args())
        self.http.booking.update(status="cancelled", start="2026-09-08T15:00:00Z", end="2026-09-08T15:30:00Z")
        result = self.adapter.status({"booking_uid": created["booking_uid"]})
        self.assertFalse(result["confirmed"])
        self.assertTrue(result["time_changed"])
        self.assertEqual(result["status"], "cancelled")

    def test_invalid_config_identity_timezone_or_window_never_sends(self):
        self.env["LUMA_CAL_EVENT_TYPES_JSON"] = '{"consultation":"42"}'
        with self.assertRaises(ProviderError):
            self.availability()
        self.env["LUMA_CAL_EVENT_TYPES_JSON"] = '{"consultation":42}'
        for change in [{"time_zone": "invented/zone"}, {"start": "2024-01-01"}, {"end": "2027-01-01"}, {"service": "not-approved"}]:
            args = {"service": "consultation", "start": "2026-09-08", "end": "2026-09-09", "time_zone": "America/New_York", **change}
            with self.assertRaises((ValueError, ProviderError)):
                self.adapter.availability(args)
        args = self.args()
        with self.assertRaises(ValueError):
            self.adapter.preview({**args, "email": "not-an-email"})
        self.assertFalse(self.http.posts)

    def test_allowlist_removal_invalidates_an_existing_offer(self):
        args = self.args()
        self.env["LUMA_CAL_EVENT_TYPES_JSON"] = "{}"
        with self.assertRaises(ProviderError):
            self.adapter.create(args)
        self.assertFalse(self.http.posts)

    def test_rejected_request_is_not_automatically_retried(self):
        args = self.args()
        self.http.post_error = ProviderError("Fixture validation rejection")
        with self.assertRaises(ProviderError):
            self.adapter.create(args)
        with self.assertRaises(ValueError):
            self.adapter.create(args)
        self.assertEqual(len(self.http.posts), 1)


if __name__ == "__main__":
    unittest.main()

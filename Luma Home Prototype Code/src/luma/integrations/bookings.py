"""Cal.com appointments with verified, short-lived offers and durable receipts.

The control surface must obtain explicit approval for ``create``. The model may
search availability, but must not select a slot or invent attendee details.
Offers are RAM-only and expire on restart. Attempt/receipt records use Luma's
encrypted Store so an uncertain mutation is never automatically retried.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import threading
import time
from datetime import datetime, timezone
from urllib.parse import urlencode
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from luma.integrations.providers import OutcomeUnknown, ProviderError, transport


BASE = "https://api.cal.com/v2"
SLOTS_VERSION = "2024-09-04"
BOOKINGS_VERSION = "2026-02-25"
EVENT_TYPES_VERSION = "2026-06-12"
OFFER_SECONDS = 600


def _fields(args, names):
    if not isinstance(args, dict) or set(args) != set(names):
        raise ValueError("Booking arguments must match their declared fields exactly.")
    for name in names:
        if not isinstance(args[name], str) or not args[name].strip() or len(args[name]) > 254:
            raise ValueError(f"{name} must be nonempty text of at most 254 characters.")


def _zone(name):
    try:
        return ZoneInfo(name)
    except (ValueError, ZoneInfoNotFoundError):
        raise ValueError("Use a valid IANA time zone, such as America/New_York.") from None


def _time(value, zone=None):
    if not isinstance(value, str) or len(value) > 50:
        raise ValueError("Use an ISO date or a timestamp with a UTC offset.")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("Use an ISO date or a timestamp with a UTC offset.") from None
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value) and zone is not None:
        result = result.replace(tzinfo=zone)
    if result.tzinfo is None:
        raise ValueError("Appointment timestamps must include an explicit UTC offset.")
    return result.astimezone(timezone.utc)


def _iso(value):
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


class CalBookings:
    def __init__(self, store, env=None, request=None, clock=None):
        self.store = store
        self.env = os.environ if env is None else env
        self.request = request or transport
        self.clock = clock or time.time
        self._offers = {}
        self._lock = threading.RLock()

    def services(self):
        try:
            configured = json.loads(self.env.get("LUMA_CAL_EVENT_TYPES_JSON", "{}"))
        except (ValueError, TypeError):
            raise ProviderError("LUMA_CAL_EVENT_TYPES_JSON must map service names to event type IDs.") from None
        if not isinstance(configured, dict) or len(configured) > 30:
            raise ProviderError("Configure up to 30 approved Cal.com event types.")
        for service, event_id in configured.items():
            if not re.fullmatch(r"[a-z][a-z0-9_-]{0,63}", service) or type(event_id) is not int or event_id < 1:
                raise ProviderError("Use lowercase service aliases and positive integer Cal.com event type IDs.")
        return [{"service": service, "event_type_id": event_id} for service, event_id in configured.items()]

    def _event_id(self, service):
        event_id = next((r["event_type_id"] for r in self.services() if r["service"] == service), None)
        if event_id is None:
            raise ProviderError("This appointment service is not configured in LUMA_CAL_EVENT_TYPES_JSON.")
        return event_id

    def _headers(self, version):
        token = self.env.get("CAL_COM_API_KEY", "")
        if not token or "\n" in token or "\r" in token:
            raise ProviderError("Configure CAL_COM_API_KEY first.")
        return {"Authorization": "Bearer " + token, "cal-api-version": version, "Accept": "application/json"}

    def _get(self, path, version):
        result = self.request("GET", BASE + path, self._headers(version))
        if not isinstance(result, dict) or result.get("status") != "success" or not isinstance(result.get("data"), dict):
            raise ProviderError("Cal.com did not return usable data. No booking was made.")
        return result["data"]

    def _event(self, event_id):
        event = self._get(f"/event-types/{event_id}", EVENT_TYPES_VERSION)
        if event.get("id") != event_id:
            raise ProviderError("Cal.com returned a different event type.")
        # Verify these on every search and again immediately before booking.
        # A configured event must never silently become a paid or recurring order.
        if type(event.get("price")) not in {int, float} or event["price"] != 0:
            raise ProviderError("Luma currently books only appointments verified as free. Use the provider for paid bookings.")
        recurrence = event.get("recurrence")
        if recurrence and (not isinstance(recurrence, dict) or recurrence.get("disabled") is not True):
            raise ProviderError("Recurring appointment types are not supported by this booking connector.")
        seats = event.get("seats") or {}
        if event.get("seatsPerTimeSlot") or (isinstance(seats, dict) and seats.get("seatsPerTimeSlot") and seats.get("disabled") is not True):
            raise ProviderError("Group/seated appointments require the provider's booking page.")
        if event.get("isInstantEvent") or event.get("bookingRequiresAuthentication"):
            raise ProviderError("Instant or attendee-authenticated appointments require the provider's booking page.")
        duration = event.get("lengthInMinutes")
        if type(duration) is not int or not 1 <= duration <= 1440:
            raise ProviderError("The provider did not return a supported appointment duration.")
        locations = event.get("locations", [])
        if not isinstance(locations, list) or len(locations) > 1:
            raise ProviderError("Configure an event with one location; choosing among locations is not supported yet.")
        location = locations[0] if locations else {}
        if not isinstance(location, dict):
            raise ProviderError("The provider returned an invalid appointment location.")
        location_text = str(location.get("address") or location.get("link") or location.get("type") or "Set by the appointment provider")[:500]
        return {"event_type_id": event_id, "title": str(event.get("title") or "Appointment")[:200],
                "duration": duration, "location": location_text, "price_cents": 0}

    def _slots(self, event_id, start, end, zone, duration):
        query = urlencode({"eventTypeId": event_id, "start": _iso(start), "end": _iso(end), "timeZone": zone.key, "format": "range"})
        data = self._get("/slots?" + query, SLOTS_VERSION)
        valid = {}
        for rows in data.values():
            if not isinstance(rows, list):
                raise ProviderError("Cal.com returned an invalid availability list.")
            for row in rows:
                try:
                    a, b = _time(row["start"]), _time(row["end"])
                except (ValueError, KeyError, TypeError):
                    continue
                if a.timestamp() <= self.clock() or not start <= a < end or b > end:
                    continue
                if (b - a).total_seconds() != duration * 60:
                    continue
                valid[_iso(a)] = (_iso(a), _iso(b))
        return [valid[key] for key in sorted(valid)]

    def availability(self, args):
        _fields(args, {"service", "start", "end", "time_zone"})
        zone = _zone(args["time_zone"])
        start, end = _time(args["start"], zone), _time(args["end"], zone)
        now = self.clock()
        if not start < end or (end - start).total_seconds() > 31 * 86400:
            raise ValueError("Choose a positive search window of at most 31 days; end is exclusive.")
        if end.timestamp() <= now or start.timestamp() < now - 86400 or end.timestamp() > now + 366 * 86400:
            raise ValueError("Search upcoming appointments within one year.")
        event_id = self._event_id(args["service"])
        event = self._event(event_id)
        rows = self._slots(event_id, start, end, zone, event["duration"])
        offered = []
        with self._lock:
            self._offers = {k: v for k, v in self._offers.items() if v["expires"] > now}
            # Bound RAM use; old offers can safely be searched again if evicted.
            while len(self._offers) > 800:
                self._offers.pop(next(iter(self._offers)))
            for a, b in rows[:100]:
                offer_id = secrets.token_urlsafe(24)
                offer = {"offer_id": offer_id, "service": args["service"], **event,
                         "start": a, "end": b, "time_zone": zone.key,
                         "local_start": _time(a).astimezone(zone).isoformat(),
                         "local_end": _time(b).astimezone(zone).isoformat(),
                         "expires": min(self.clock() + OFFER_SECONDS, _time(a).timestamp())}
                self._offers[offer_id] = offer
                offered.append(dict(offer))
        return {"service": args["service"], "event_type_id": event_id, "title": event["title"],
                "time_zone": zone.key, "slots": offered, "truncated": len(rows) > 100,
                "summary": "Live appointment slots found. Select a time and review before booking; availability is not reserved." if offered else "No available appointments were returned for this window."}

    def _offer(self, offer_id):
        offer = self._offers.get(offer_id)
        if not offer or offer["expires"] <= self.clock():
            self._offers.pop(offer_id, None)
            raise ValueError("This appointment offer expired or was already used. Search availability again.")
        if self._event_id(offer["service"]) != offer["event_type_id"]:
            raise ProviderError("The configured service changed. Search availability again.")
        return dict(offer)

    def preview(self, args):
        _fields(args, {"offer_id", "name", "email"})
        name, email = args["name"].strip(), args["email"].strip()
        if len(name) > 120 or any(ord(c) < 32 for c in name):
            raise ValueError("Enter an attendee name of at most 120 characters.")
        if not re.fullmatch(r"[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+", email):
            raise ValueError("Enter the attendee's real email address.")
        with self._lock:
            offer = self._offer(args["offer_id"])
        return {**offer, "attendee": {"name": name, "email": email, "time_zone": offer["time_zone"]},
                "summary": "Review this exact appointment and attendee. Confirming sends a booking request and can send provider confirmation emails."}

    def create(self, args):
        """Called only from the runtime's confirmed-action path; never the LLM."""
        preview = self.preview(args)
        with self._lock:
            offer = self._offer(args["offer_id"])
            # Claim the offer before network I/O. Concurrent calls cannot use it.
            self._offers.pop(args["offer_id"])
        attendee = preview["attendee"]
        attempt_id = "booking-attempt:" + hashlib.sha256(json.dumps([offer["event_type_id"], offer["start"], attendee["email"].lower()]).encode()).hexdigest()
        with self._lock:
            existing = self.store.get("booking_attempt", attempt_id)
            if existing and existing["state"] != "rejected":
                raise ProviderError("This appointment already has a submitted or uncertain attempt. Check its receipt/provider dashboard; no retry was sent.")
            event = self._event(offer["event_type_id"])
            if any(event[k] != offer[k] for k in event):
                raise ProviderError("Appointment details changed after your review. Search and review again.")
            still_open = self._slots(offer["event_type_id"], _time(offer["start"]), _time(offer["end"]), _zone(offer["time_zone"]), offer["duration"])
            if (offer["start"], offer["end"]) not in still_open or offer["expires"] <= self.clock():
                raise ProviderError("That exact appointment is no longer available. No alternative time was booked.")
            attempt = {"state": "submitting", "service": offer["service"], "event_type_id": offer["event_type_id"],
                       "start": offer["start"], "end": offer["end"], "attendee": attendee, "created": self.clock()}
            self.store.put("booking_attempt", attempt, attempt_id)
        payload = {"eventTypeId": offer["event_type_id"], "start": offer["start"],
                   "attendee": {"name": attendee["name"], "email": attendee["email"], "timeZone": attendee["time_zone"]},
                   "metadata": {"source": "luma", "attempt": attempt_id.removeprefix("booking-attempt:")}}
        try:
            result = self.request("POST", BASE + "/bookings", self._headers(BOOKINGS_VERSION), payload)
        except OutcomeUnknown:
            self.store.put("booking_attempt", {**attempt, "state": "unknown"}, attempt_id)
            raise
        except ProviderError:
            self.store.put("booking_attempt", {**attempt, "state": "rejected"}, attempt_id)
            raise
        # Any malformed success response might still have created the booking.
        try:
            receipt = self._receipt(result, offer)
        except (ProviderError, ValueError, TypeError):
            self.store.put("booking_attempt", {**attempt, "state": "unknown"}, attempt_id)
            raise OutcomeUnknown("Cal.com returned an incomplete booking result. Check its dashboard before trying again.") from None
        self.store.put("booking", {**receipt, "event_type_id": offer["event_type_id"], "attendee": attendee, "created": self.clock()}, "booking:" + receipt["booking_uid"])
        self.store.put("booking_attempt", {**attempt, "state": "submitted", "booking_uid": receipt["booking_uid"]}, attempt_id)
        return receipt

    def _receipt(self, result, expected, exact_slot=True):
        if not isinstance(result, dict) or result.get("status") != "success" or not isinstance(result.get("data"), dict):
            raise ProviderError("The provider did not return a single booking receipt.")
        row = result["data"]
        uid = row.get("uid")
        if not isinstance(uid, str) or not re.fullmatch(r"[A-Za-z0-9_-]{6,200}", uid):
            raise ProviderError("The provider did not return a usable booking ID.")
        start, end = _iso(_time(row.get("start"))), _iso(_time(row.get("end")))
        if row.get("eventTypeId") != expected["event_type_id"] or (exact_slot and (start != expected["start"] or end != expected["end"])):
            raise ProviderError("The returned appointment differs from the selected appointment.")
        if _time(end) <= _time(start):
            raise ProviderError("The provider returned an invalid appointment duration.")
        status = str(row.get("status", "unknown")).lower()
        if status not in {"accepted", "pending", "unconfirmed", "cancelled", "rejected"}:
            status = "unknown"
        summaries = {"accepted": "Cal.com reports this appointment as accepted.",
                     "pending": "Booking requested; the appointment is awaiting provider confirmation.",
                     "unconfirmed": "Booking requested; the appointment is awaiting provider confirmation.",
                     "cancelled": "Cal.com reports this appointment as cancelled.",
                     "rejected": "Cal.com reports that the booking was rejected.",
                     "unknown": "A booking ID was returned, but its confirmation status is unknown. Check the provider."}
        changed = start != expected["start"] or end != expected["end"]
        return {"booking_uid": uid, "status": status, "confirmed": status == "accepted", "start": start,
                "end": end, "title": str(row.get("title") or expected.get("title", "Appointment"))[:200],
                "service": expected["service"], "time_changed": changed,
                "summary": summaries[status] + (" The appointment time changed at the provider; review the new time." if changed else "")}

    def status(self, args):
        _fields(args, {"booking_uid"})
        uid = args["booking_uid"]
        if not re.fullmatch(r"[A-Za-z0-9_-]{6,200}", uid):
            raise ValueError("Use a booking ID recorded by this Luma device.")
        stored = self.store.get("booking", "booking:" + uid)
        if not stored:
            raise ValueError("This booking was not recorded by this Luma device.")
        if self._event_id(stored["service"]) != stored["event_type_id"]:
            raise ProviderError("This service's configured event type has changed. Check the original provider directly.")
        result = self._get("/bookings/" + uid, BOOKINGS_VERSION)
        if result.get("uid") != uid:
            raise ProviderError("The provider returned a different booking ID.")
        receipt = self._receipt({"status": "success", "data": result}, stored, exact_slot=False)
        self.store.put("booking", {**stored, **receipt, "checked": self.clock()}, "booking:" + uid)
        return receipt

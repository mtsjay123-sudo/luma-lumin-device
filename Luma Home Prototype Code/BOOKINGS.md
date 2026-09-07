# Appointment booking connector

Luma can query live availability and submit a reviewed appointment request to
**configured Cal.com services**. This is a real API adapter, not a universal
restaurant, flight, hotel, or medical booking service. It has been verified with
mock HTTP responses; no real appointment or provider email was created in tests.

Configure these values in the private `.env`, then restart Luma:

```dotenv
CAL_COM_API_KEY=
LUMA_CAL_EVENT_TYPES_JSON={"consultation":12345}
```

Replace `12345` with an actual Cal.com event type ID you are authorized to book.
Service aliases use lowercase letters, numbers, underscores, or hyphens. Enable
the booking integration in Luma's owner controls. The account must have access to
read that event type, query slots, create bookings, and retrieve its receipts.

The current adapter supports free, nonrecurring appointments with one configured
location and the event's default duration. Paid, group/seated, instant,
attendee-authenticated, or multiple-location types are blocked. Event types that
require additional attendee fields or email verification need their normal
provider flow; the adapter does not fabricate those fields or bypass checks.

The owner enters the attendee's real name and email, chooses one returned time,
reviews the exact appointment, and confirms. Submission may cause Cal.com to
send booking emails to the attendee and host. A pending result remains pending;
only a provider `accepted` status is presented as confirmed. Calendar sync and
conferencing behavior depend on the Cal.com event's own setup.

For runtime integration:

```python
bookings = CalBookings(store, env=providers.env, request=providers.request, clock=clock)
bookings.services()  # [{"service": "consultation", "event_type_id": 12345}]
bookings.availability({
    "service": "consultation",
    "start": "2026-09-08",
    "end": "2026-09-09",
    "time_zone": "America/New_York",
})
bookings.preview({"offer_id": selected_offer_id, "name": attendee_name, "email": attendee_email})
# Only the confirmed-action path may call create with those exact reviewed args.
bookings.create({"offer_id": selected_offer_id, "name": attendee_name, "email": attendee_email})
bookings.status({"booking_uid": recorded_booking_uid})
```

Search dates are interpreted in the selected IANA timezone. Timestamp inputs
must include a UTC offset. The end of the search window is exclusive. Luma
searches at most 31 days at once, within the next year, and displays at most 100
slots. Offers expire after ten minutes or when the slot begins, and disappear
when the process restarts. An offer is not a reservation. The adapter rechecks
the event configuration and exact availability before posting; it never replaces
a selected time with another time or turns on Cal.com's conflict overrides.

Offers are consumed once, even when the network fails. Durable encrypted attempt
records block a new attempt for the same service, start, and attendee email when
the prior result is submitted or uncertain. There is no automatic mutation retry.
If the outcome is unknown, check Cal.com's dashboard before taking further
action. The current adapter deliberately has no automatic “clear uncertainty”
button. Run one local Luma process against a state database; process-local offer
claims do not provide distributed coordination between multiple devices.

Receipt refresh is limited to IDs recorded by this device. A refresh can show a
provider cancellation or changed appointment time. Cancel/reschedule mutations
are not implemented yet; use the appointment provider for those operations.

Official API references (verified September 7, 2026):

- [Slot availability](https://cal.com/docs/api-reference/v2/slots/get-available-time-slots-for-an-event-type): version `2024-09-04`, explicit range output.
- [Event type details](https://cal.com/docs/api-reference/v2/event-types/get-an-event-type): version `2026-06-12`, price, duration, recurrence, and location metadata.
- [Create a booking](https://cal.com/docs/api-reference/v2/bookings/create-a-booking): version `2026-02-25`, UTC start and attendee timezone.
- [Retrieve a booking](https://cal.com/docs/api-reference/v2/bookings/get-a-booking): version `2026-02-25`, provider status and recorded appointment details.

Run the adapter's deterministic checks with:

```sh
.venv/bin/python -m unittest discover -s tests -p test_bookings.py -v
```

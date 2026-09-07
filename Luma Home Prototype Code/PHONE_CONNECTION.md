# Luma phone connection

The companion connects a phone browser to the Luma computer on the same private Wi-Fi network. The local Luma process and computer must remain running. This is a companion interface for Luma's existing tools, memory and action review; pairing does not grant access to the phone's native Messages app, contacts, calendar, payment wallet or cellular service.

The desktop control starts a separate HTTPS listener only when phone access is explicitly enabled. A fresh desktop-generated pairing link expires after ten minutes and works once. Open it on the phone, give the phone a recognizable name, and pair. The invite belongs in the URL fragment, never a query string: the browser removes it from the address bar and sends it to the pairing POST endpoint over HTTPS. Each later pairing link replaces the previous unused link.

The paired credential lasts thirty days, including while the device is idle. Pairing supports up to five active phones. The desktop can list phone names and validity dates, and revoke a lost or shared phone immediately. Expired and revoked credentials cannot reconnect. Phone credentials and invite secrets are stored as hashes inside the encrypted local state, and raw credentials are returned only when issued. A paired phone has the owner's assistant permissions; use a device you control.

Local HTTPS uses a self-signed certificate for the computer's private IPv4 address and localhost. This keeps traffic encrypted, but the phone must trust the local certificate before use. No public certificate authority or public website is involved. Do not bypass certificate warnings on unfamiliar networks or install a certificate sent by someone else. A Wi-Fi address change can require a new certificate and phone trust setup. This prototype does not create a tunnel, router port forward, automatic trust profile or remote access over the cellular network.

## What phone pairing enables

- Use the same assistant, reminders and memory from the phone browser while connected to the Luma computer.
- Read a proposed action's actual destination, contents and relevant terms, then explicitly confirm or cancel it.
- See which connected services have been configured and enabled.

Sending SMS additionally requires a configured messaging provider and a provider-owned sending number. It does not send from your personal iMessage identity. Web search requires its search provider. Reservations require a connected booking provider and an available, verified reservation; calendar entries and opening a booking website are not completed bookings. Shopping handoff opens the merchant, where the user can use that merchant's saved payment method. Pairing does not supply these provider accounts or turn a checkout link into a purchase.

## Integration contract

`PairingManager(store, clock=time.time)` offers `create_invite()`, `pair(invite_token, device_name)`, `authenticate(device_token)`, `list_devices()` and `revoke(device_id)`. Only the local desktop may issue invites, list/revoke devices or enable the LAN listener. The HTTP integration must enforce that distinction using the connection it actually received; forwarded headers never prove a local caller.

`create_invite()` returns `{token, expires_at}`. `pair()` returns `{token, device}` once. The server should place the device credential in an HttpOnly, Secure, SameSite=Strict cookie and never expose it to the application JavaScript or logs. Authenticate the cookie on every protected request and enforce Host, Origin, content type and bounded request sizes. Pairing requests need rate limits. The invite should not enter referrers, analytics, screenshots, browser history or server access logs. Action confirmation remains a separate step after pairing.

`ensure_local_certificate(directory, private_ipv4, clock=time.time)` returns `(certificate_path, key_path)`. Use a dedicated owner-only directory; it creates an owner-only EC private key and certificate, reuses matching certificates with more than one day remaining, and renews them when necessary. It accepts only RFC1918 IPv4 addresses, never a public bind or wildcard. The helper does not start a server or change the operating system trust store.

The credential tests use temporary databases, fake clocks and no network services. They cover concurrent invite consumption across separate SQLite connections, token tampering, expiry, revocation, the device cap, metadata privacy and certificate validity. No real phone, message, booking or payment is used in these tests.

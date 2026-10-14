# Luma Desktop

Luma as a real app on your computer. It's an AI that works for you: it finds the cheapest price, goes through your email, keeps an eye on what matters, and asks before anything goes out. Its brain (Qwen3 4B) runs on your computer; nothing goes to a cloud model.

- **Main chat, Feed, Ideas, Goals, Library**: tabs in the sidebar, plus side chats for anything you want to keep separate.
- **Luma's computer**: watch Luma's browser live while it works, with Pause, Stop and Take over.
- **Checkout cards**: "Luma wants to add this to your cart at bestbuy.com", with **Deny** and **Allow**. Emails and texts show the exact words first.
- **Goals**: price watches, inbox checks, feed catch-ups and a morning agenda that run on their own and leave what they find in the Feed.
- **Apps**: connect email (with an app password), your calendar (private iCal link), Instagram and stores (Luma's own browser), texts, and your phone. All free.
- **Rules**: what Luma just does, asks about, or never does. Checkout and payment are always yours.
- **⌘K** searches everything; **⌥Space** brings Luma up from anywhere; light and dark.
- **See-through**: like Vision Pro, what's behind Luma (a movie, another app) shows through its glass. Turn it on from the top bar, Settings or View → See-Through; Settings has a Clarity slider and **Float on Top** to keep Luma over a video. On a Mac and Linux the window itself goes clear; on Windows the whole window fades.
- **Always on**: closing the window doesn't stop Luma. It stays in the menu bar (Mac) or the system tray (Windows) and starts when you log in, so your Goals run every day. Use that icon to quit Luma or to turn off Start Luma When I Log In.

## Get it

Download it from the website (**/download**) or from the repository's latest release:
- `Luma-mac-apple-silicon.dmg` for Macs from late 2020 on;
- `Luma-mac-intel.dmg` for older Macs;
- `Luma-windows-setup.exe` for Windows 10 and 11.

**The first time you open it**:
- **Mac:** if it says “Apple cannot check it for malicious software”, open System Settings → Privacy & Security and click **Open Anyway**, once. Or install from Terminal with no warning: `curl -fsSL https://lumin-holdings-site.vercel.app/install-mac.sh | bash`. This build isn't notarized by Apple yet.
- **Windows:** if SmartScreen appears, choose **More info → Run anyway**.

Then Luma sets itself up, once, in its own folder (no admin password):
1. a private Python;
2. Luma's tools, including llama.cpp;
3. a browser to drive: your Chrome or Edge if you have one;
4. its brain, about 2.5 GB, checked against its published SHA-256.

If a download is interrupted, it picks up where it left off. On a Mac without Apple's free Command Line Tools, Luma opens their installer. Press **Try again** when it's done.

**Build it yourself:** double-click `Build Luma Desktop.command` on a Mac (needs Node.js), or run `npm ci && npm run dist:mac` / `npm run dist:win` here.

**Developers:** if you have the `luma-lumin-device` folder with its `.venv`, the app uses that instead of its own copy (Help → Where Luma Keeps Its Folder…).

## How it fits together

The window is a thin Electron shell (`main.js`, `preload.js`):
- `setup.js` does the first-launch setup.
- Luma's Python runtime ships inside the app (`resources/luma`). It runs `python -m luma.cli serve` on port 8095 and serves the interface at `/desktop/`.
- The runtime does all the work. Approvals use its one-time tokens, so the window can't approve anything by itself.

CI (`.github/workflows/luma-desktop.yml`) works in this order:
1. It runs the same first launch on a real Mac and a real Windows PC (`scripts/smoke.js`). Luma has to answer, and its browser has to open a page.
2. It builds the installers.
3. It publishes them as a release with names that never change, so the website's Download buttons always get the newest one.

## Your logo

The app icon is in `build/` (`icon.png`, `icon.icns`, `icon.ico`). Luma's face in the app is `assets/logo.svg` and `Luma Home Prototype Code/src/luma/control/web/desktop/brand/logo.svg`.

## Signing and notarizing the Mac app

With an Apple Developer account ($99 a year), add these repository secrets and every build after that is signed and notarized, so macOS opens Luma with no warning:
- `MAC_CERTIFICATE_P12_BASE64`: your **Developer ID Application** certificate exported from Keychain Access as a .p12, then base64-encoded (`base64 -i cert.p12 | pbcopy`).
- `MAC_CERTIFICATE_PASSWORD`: the password you gave that .p12.
- `APPLE_ID`: the Apple ID email of the developer account.
- `APPLE_APP_SPECIFIC_PASSWORD`: an app-specific password from account.apple.com → Sign-In and Security.
- `APPLE_TEAM_ID`: the 10-character Team ID from developer.apple.com → Membership.

CI uses `notarize.config.js` when all of them are set, and the ad-hoc build otherwise.

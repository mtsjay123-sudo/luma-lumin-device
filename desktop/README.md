# Luma Desktop

Luma as a real app on your computer: a friendly window to talk to Luma, watch it work, and approve what goes out. It runs the same Luma that lives on this machine (the local Qwen brain); nothing goes to a cloud model.

- **Talk**: type or press the mic. Luma's face shows what it's doing ("Drafting the text to Maya", "Building your deck").
- **The work panel** shows what Luma made: the exact text with **Send it / Edit / Don't send**, deck slides with a download, a page it read.
- **⌥Space** brings Luma up from anywhere; closing the window keeps it around.
- **Library, Today, People, Settings** live in the left rail.

## Get it

**Easiest:** GitHub → Actions → **Luma Desktop** → newest run → Artifacts → **Luma-for-Mac**. Unzip, open the `.dmg` for your Mac (`arm64` for Apple Silicon), drag Luma into Applications.

**Or build it on your Mac:** double-click `Build Luma Desktop.command` (needs Node.js from nodejs.org).

The first time you open it, macOS says it can't check the app (it isn't notarized yet). Right-click Luma → **Open** → **Open**. Notarizing needs an Apple Developer account; the workflow notes which secrets to add.

Luma Desktop starts Luma for you. It looks for the `luma-lumin-device` folder in your home, Desktop, Documents or Developer folder; if it can't find it, it asks once and remembers. Run `Luma Home Prototype Code/scripts/setup_mac.sh` once first so Luma's brain is installed.

## Your logo

Put the Omni Short / Luma logo at `Luma Home Prototype Code/src/luma/control/web/desktop/brand/logo.png` and it replaces the mascot in the rail and tab icon. For the app icon, replace `desktop/build/icon.png` (1024×1024) and `icon.icns`.

## How it fits together

The window is a thin Electron shell. Luma's runtime (`python -m luma.cli serve`, port 8095) serves the page at `/desktop/` and does all the work; approvals still use the runtime's one-time tokens. This is the same shape as ChatGPT's desktop app and its local agent server (see `Luma Home Prototype Code/docs/DOTS_TEARDOWN.md`).

#!/usr/bin/env python3
"""Render or install an unprivileged systemd service for this exact checkout."""
from __future__ import annotations

import argparse
import datetime
import os
from pathlib import Path
import platform
import pwd
import shutil
import subprocess
import tempfile


def unit_text(root: Path, user: str, state_home: Path):
    root = root.resolve()
    state_home = state_home.resolve()
    if any(char in user for char in "\n\r\x00 /\\") or not user:
        raise ValueError("A local system username is required.")

    def quote(value):
        value = str(value)
        if any(char in value for char in "\n\r\x00"):
            raise ValueError("Service paths cannot contain newlines or NUL bytes.")
        return '"' + value.replace('\\', '\\\\').replace('"', '\\"').replace('%', '%%') + '"'

    return f"""# Generated for this checkout; do not copy between accounts without regenerating.
[Unit]
Description=Luma local household companion
After=sound.target
StartLimitIntervalSec=300
StartLimitBurst=6

[Service]
Type=simple
User={user}
WorkingDirectory={quote(root)}
Environment=PYTHONUNBUFFERED=1
Environment=HF_HUB_OFFLINE=1
Environment=TRANSFORMERS_OFFLINE=1
ExecStart=:/bin/bash {quote(root / 'scripts/device_run.sh')}
Restart=on-failure
RestartSec=10
TimeoutStopSec=20
KillSignal=SIGTERM
KillMode=control-group
UMask=0077
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths={quote(state_home / '.luma')} {quote(state_home / '.cache')} {quote(root / '.local-state')}
RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
"""


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--install", action="store_true", help="Install and enable on the actual Linux Jetson")
    parser.add_argument("--check", action="store_true", help="Run systemd-analyze verify on the rendered unit")
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parent.parent
    account = pwd.getpwuid(os.getuid())
    text = unit_text(root, account.pw_name, Path(account.pw_dir))
    if not args.install and not args.check:
        print(text)
        return 0
    if platform.system() != "Linux" or platform.machine() not in {"aarch64", "arm64"}:
        raise SystemExit("Service installation/check requires the actual Linux/aarch64 Jetson; use no flags to preview.")
    board = Path("/proc/device-tree/model")
    if not board.exists() or "NVIDIA" not in board.read_text():
        raise SystemExit("NVIDIA Jetson board not detected. No service changes made.")
    if os.getuid() == 0:
        raise SystemExit("Run as the intended Luma account; the service must not run as root.")
    if not shutil.which("systemd-analyze"):
        raise SystemExit("systemd-analyze is required to validate the generated service.")
    with tempfile.TemporaryDirectory(prefix="luma-service-") as temporary:
        staged = Path(temporary) / "luma.service"
        staged.write_text(text)
        subprocess.run(["systemd-analyze", "verify", str(staged)], check=True)
        if not args.install:
            print("systemd syntax check passed; no service installed.")
            return 0
        python = root / ".venv/bin/python"
        # Missing models, speech libraries, devices or dependencies block enablement.
        subprocess.run([str(python), "-m", "luma.hardware.diagnostics"], cwd=root, check=True)
        for path in (Path(account.pw_dir) / ".luma", Path(account.pw_dir) / ".cache", root / ".local-state"):
            path.mkdir(mode=0o700, parents=True, exist_ok=True)
        target = Path("/etc/systemd/system/luma.service")
        if target.exists():
            stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            subprocess.run(["sudo", "cp", "--preserve=all", str(target), str(target) + "." + stamp + ".bak"], check=True)
        subprocess.run(["sudo", "install", "-m", "0644", str(staged), str(target)], check=True)
        subprocess.run(["sudo", "systemctl", "daemon-reload"], check=True)
        subprocess.run(["sudo", "systemctl", "enable", "--now", "luma.service"], check=True)
    print("Luma service enabled. Use journalctl -u luma.service and open http://127.0.0.1:8095/.")
    print("Startup stays muted. Validate cold boot, crash recovery and physical privacy on the device.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

import importlib.util
import json
from pathlib import Path
import sqlite3
import stat
import subprocess
import sys

import pytest

from luma.hardware.device import DeviceConfig, DeviceController, resolve_audio_device
from luma.hardware import diagnostics

ROOT = Path(__file__).resolve().parent.parent


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class GPIO:
    BOARD = "BOARD"
    IN = "IN"
    OUT = "OUT"
    def __init__(self):
        self.value = 1
        self.output_value = None
        self.cleaned = []
    def setmode(self, mode): self.mode = mode
    def setup(self, pin, mode, initial=None):
        if initial is not None: self.output_value = initial
    def input(self, pin):
        if self.value == "broken": raise OSError("disconnected")
        return self.value
    def output(self, pin, value): self.output_value = value
    def cleanup(self, pins): self.cleaned.extend(pins)


def test_mac_does_not_import_gpio_or_claim_physical_cutoff():
    controller = DeviceController(DeviceConfig())
    assert controller.capture_allowed()
    assert controller.privacy_state()["configured"] is False
    assert controller.set_indicator(muted=True) is False
    controller.close()
    assert not controller.capture_allowed()


def test_privacy_is_fail_closed_and_fault_does_not_silently_clear():
    gpio = GPIO()
    controller = DeviceController(DeviceConfig(privacy_pin=11, privacy_active_level=0,
                                                indicator_pin=13, indicator_active_level=1), gpio=gpio)
    assert gpio.output_value == 1  # startup shows muted
    assert controller.capture_allowed()
    gpio.value = 0
    assert not controller.capture_allowed()
    controller.set_indicator(muted=False)
    assert gpio.output_value == 1  # cannot display open when cutoff reports muted
    gpio.value = "broken"
    assert not controller.capture_allowed()
    gpio.value = 1
    assert not controller.capture_allowed()
    assert "restart" in controller.privacy_state()["detail"]
    controller.close()
    controller.close()
    assert gpio.cleaned == [11, 13]


def test_failed_initialization_blocks_configured_device():
    class Missing(GPIO):
        def setmode(self, _mode): raise RuntimeError("permission denied")
    controller = DeviceController(DeviceConfig(privacy_pin=11), gpio=Missing())
    assert not controller.capture_allowed()
    assert controller.privacy_state()["configured"]


@pytest.mark.parametrize("env", [
    {"LUMA_PRIVACY_GPIO": "11"},
    {"LUMA_PRIVACY_GPIO": "11", "LUMA_PRIVACY_ACTIVE_LEVEL": "yes"},
    {"LUMA_INDICATOR_GPIO": "41", "LUMA_INDICATOR_ACTIVE_LEVEL": "1"},
    {"LUMA_PRIVACY_GPIO": "11", "LUMA_PRIVACY_ACTIVE_LEVEL": "0", "LUMA_INDICATOR_GPIO": "11", "LUMA_INDICATOR_ACTIVE_LEVEL": "1"},
])
def test_gpio_requires_unambiguous_actual_circuit_configuration(env):
    with pytest.raises(ValueError): DeviceConfig.from_env(env)


def test_audio_rejects_ambiguous_or_wrong_direction_device():
    devices = [{"name": "USB Array", "max_input_channels": 6, "max_output_channels": 0},
               {"name": "USB Speaker", "max_input_channels": 0, "max_output_channels": 2},
               {"name": "USB Array 2", "max_input_channels": 6, "max_output_channels": 0}]
    assert resolve_audio_device(None, devices, direction="input") is None
    assert resolve_audio_device("speaker", devices, direction="output") == 1
    assert resolve_audio_device("2", devices, direction="input") == 2
    with pytest.raises(ValueError): resolve_audio_device("USB", devices, direction="input")
    with pytest.raises(ValueError): resolve_audio_device("1", devices, direction="input")


def test_model_manifest_detects_tampering_and_relocation(tmp_path, monkeypatch):
    asset = tmp_path / "model.gguf"
    asset.write_bytes(b"verified transfer payload")
    monkeypatch.setattr(diagnostics, "asset_paths", lambda: {"conversation": asset})
    manifest = diagnostics.model_manifest()
    manifest["assets"][0]["path"] = "/old/mac/location/model.gguf"
    assert diagnostics.verify_manifest(manifest)["verified"]
    asset.write_bytes(b"corrupted transfer payload")
    with pytest.raises(ValueError, match="integrity mismatch"):
        diagnostics.verify_manifest(manifest)


def test_model_manifest_rejects_incomplete_or_duplicate_roles(tmp_path, monkeypatch):
    asset = tmp_path / "model.gguf"
    asset.write_bytes(b"model")
    monkeypatch.setattr(diagnostics, "asset_paths", lambda: {"conversation": asset})
    manifest = diagnostics.model_manifest()
    manifest["assets"].append(manifest["assets"][0])
    with pytest.raises(ValueError, match="duplicate"):
        diagnostics.verify_manifest(manifest)
    with pytest.raises(ValueError, match="roles"):
        diagnostics.verify_manifest({"format": 1, "assets": []})


def test_service_runs_as_owner_quotes_spaces_and_does_not_start_listening():
    service = load_script("device_service")
    unit = service.unit_text(Path("/home/owner/Luma Device 100%"), "owner", Path("/home/owner"))
    assert "User=owner" in unit
    assert "100%%" in unit
    expected = str(Path("/home/owner/Luma Device 100%").resolve()).replace("%", "%%")
    assert f'ExecStart=:/bin/bash "{expected}/scripts/device_run.sh"' in unit
    assert "Restart=on-failure" in unit
    assert "NoNewPrivileges=true" in unit
    assert "--hands-free" not in unit
    with pytest.raises(ValueError): service.unit_text(Path("/bad\npath"), "owner", Path("/home/owner"))


def test_backup_keeps_matching_key_database_and_private_permissions(tmp_path):
    module = load_script("device_backup")
    root, state, destination = tmp_path / "source", tmp_path / "state", tmp_path / "backup"
    root.mkdir(); state.mkdir()
    with sqlite3.connect(state / "state.db") as db:
        db.execute("CREATE TABLE records (payload TEXT)")
        db.execute("INSERT INTO records VALUES ('encrypted payload')")
    (state / "state.key").write_bytes(b"matching test key")
    (root / ".env").write_text("PRIVATE_TEST_SETTING=example\n")
    module.backup(root, state, destination)
    assert (destination / "state.key").read_bytes() == b"matching test key"
    with sqlite3.connect(destination / "state.db") as db:
        assert db.execute("SELECT payload FROM records").fetchone()[0] == "encrypted payload"
    assert stat.S_IMODE(destination.stat().st_mode) == 0o700
    assert all(stat.S_IMODE(p.stat().st_mode) == 0o600 for p in destination.iterdir())
    with pytest.raises(FileExistsError): module.backup(root, state, destination)


def test_backup_refuses_missing_key_before_creating_destination(tmp_path):
    module = load_script("device_backup")
    state = tmp_path / "state"; state.mkdir()
    (state / "state.db").write_bytes(b"existing database")
    with pytest.raises(ValueError, match="matching key"):
        module.backup(tmp_path, state, tmp_path / "backup")
    assert not (tmp_path / "backup").exists()


def test_jetson_installer_refuses_other_platform_before_mutations(tmp_path):
    # Own uname stub guarantees the test can never enter the apt-install branch.
    uname = tmp_path / "uname"
    uname.write_text("#!/bin/sh\necho Darwin\n")
    uname.chmod(0o755)
    import os
    result = subprocess.run(["/bin/bash", str(ROOT / "scripts/setup_jetson.sh"), "--install"],
                            env={**os.environ, "PATH": str(tmp_path) + os.pathsep + os.environ["PATH"]},
                            capture_output=True, text=True, timeout=10)
    assert result.returncode == 1
    assert "No changes made" in result.stderr

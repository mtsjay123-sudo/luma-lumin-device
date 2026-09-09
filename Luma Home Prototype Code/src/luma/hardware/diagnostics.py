"""Read-only device and local-model readiness report; never records audio."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import shutil
import sys

from .device import DeviceConfig, resolve_audio_device


def _read(path):
    try:
        return Path(path).read_text().replace("\x00", "").strip()
    except OSError:
        return ""


def asset_paths():
    from luma import config
    assets = {"conversation": config.LLAMA_MODEL_PATH,
              "speech": config.KOKORO_MODEL_PATH, "voices": config.KOKORO_VOICES_PATH}
    # A directory path can be configured for an explicitly copied offline model.
    selected = os.environ.get("LUMA_WHISPER_MODEL", getattr(config, "WHISPER_MODEL_SIZE", "base.en"))
    path = Path(selected).expanduser()
    if path.is_dir():
        assets["hearing_model"] = path / "model.bin"
        assets["hearing_config"] = path / "config.json"
        assets["hearing_tokenizer"] = path / "tokenizer.json"
    else:
        # Resolve only an existing local HF cache; never trigger a download.
        try:
            from huggingface_hub import snapshot_download
            model_name = selected if "/" in selected else f"Systran/faster-whisper-{selected}"
            cache = Path(snapshot_download(model_name, local_files_only=True))
            assets.update({f"hearing_{name.split('.')[0]}": cache / name
                           for name in ("model.bin", "config.json", "tokenizer.json")})
        except Exception:
            assets["hearing"] = path / "MODEL_NOT_CACHED"
    return assets


def build_report(*, query_audio=True, include_assets=True):
    checks = []
    def check(name, ok, detail, *, required=True):
        checks.append({"name": name, "ok": bool(ok), "required": required, "detail": detail})

    machine = platform.machine()
    board = _read("/proc/device-tree/model")
    jetson = platform.system() == "Linux" and machine in {"aarch64", "arm64"} and "NVIDIA" in board
    check("python", sys.version_info >= (3, 11), platform.python_version())
    check("target_board", jetson, board or f"{platform.system()} {machine}; physical Jetson not detected", required=False)
    check("cuda_compiler", bool(shutil.which("nvcc") or Path("/usr/local/cuda/bin/nvcc").exists()),
          "Optional for GPU build; CPU mode remains available.", required=False)
    check("jetpack", Path("/etc/nv_tegra_release").is_file(), _read("/etc/nv_tegra_release")[:250] or "Not a JetPack installation", required=False)
    for package in ("llama-cpp-python", "faster-whisper", "kokoro-onnx", "sounddevice", "silero-vad"):
        try:
            check(package, True, importlib.metadata.version(package))
        except importlib.metadata.PackageNotFoundError:
            check(package, False, "Not installed in this Python environment")
    if include_assets:
        for label, path in asset_paths().items():
            check(f"asset:{label}", path.is_file() and path.stat().st_size > 0, str(path))
        from luma.config import ESPEAK_LIB, ESPEAK_DATA
        check("espeak_library", Path(ESPEAK_LIB).is_file(), str(ESPEAK_LIB))
        check("espeak_data", Path(ESPEAK_DATA).is_dir(), str(ESPEAK_DATA))
    audio = []
    if query_audio:
        try:
            import sounddevice as sd
            audio = [{"index": i, "name": device["name"],
                      "inputs": device["max_input_channels"], "outputs": device["max_output_channels"],
                      "sample_rate": device["default_samplerate"]}
                     for i, device in enumerate(sd.query_devices())]
            devices = sd.query_devices()
            for direction in ("input", "output"):
                selected = resolve_audio_device(os.getenv(f"LUMA_{direction.upper()}_DEVICE"), devices, direction=direction)
                available = any(row[f"max_{direction}_channels"] > 0 for row in devices)
                check(f"audio_{direction}", available,
                      f"Selected index {selected}" if selected is not None else "System default; choose USB device explicitly on the appliance")
        except Exception as exc:
            check("audio", False, f"Audio enumeration failed: {type(exc).__name__}. Run with the audio device connected and permissions granted.")
    try:
        device = DeviceConfig.from_env()
        check("physical_privacy", device.privacy_pin is not None,
              "GPIO feedback configured; electrical cutoff still requires physical validation." if device.privacy_pin else "No physical cutoff feedback configured.", required=False)
        check("status_led", device.indicator_pin is not None,
              "Digital LED configured; target wiring not tested." if device.indicator_pin else "No digital status LED configured.", required=False)
    except ValueError as exc:
        check("gpio_configuration", False, str(exc))
    peripherals = {"cameras": sorted(str(p) for p in Path("/dev").glob("video*")),
                   "spi": sorted(str(p) for p in Path("/dev").glob("spidev*")),
                   "camera_recording": False,
                   "lcd": "GC9A01 rendering driver not configured; SPI nodes alone do not prove a connected display.",
                   "light_ring": "NeoPixel driver not configured; digital status LED is a separate adapter."}
    return {"ready": all(item["ok"] for item in checks if item["required"]),
            "physical_hardware_validated": False, "checks": checks, "audio_devices": audio,
            "peripherals": peripherals}


def model_manifest():
    rows = []
    for role, path in asset_paths().items():
        if not path.is_file():
            raise FileNotFoundError(f"Missing local model asset: {role} ({path})")
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
                digest.update(block)
        rows.append({"role": role, "path": str(path), "bytes": path.stat().st_size, "sha256": digest.hexdigest()})
    return {"format": 1, "assets": rows,
            "note": "Local transfer/recovery integrity snapshot; not an upstream authenticity attestation."}


def verify_manifest(manifest):
    """Match by semantic role so a Mac snapshot can verify a relocated Jetson."""
    if not isinstance(manifest, dict) or manifest.get("format") != 1 or not isinstance(manifest.get("assets"), list):
        raise ValueError("Unsupported model manifest format.")
    expected = manifest["assets"]
    expected_roles = [item.get("role") for item in expected if isinstance(item, dict)]
    if len(expected_roles) != len(expected) or len(set(expected_roles)) != len(expected_roles):
        raise ValueError("Manifest has invalid or duplicate asset roles.")
    actual = {item["role"]: item for item in model_manifest()["assets"]}
    if set(expected_roles) != set(actual):
        raise ValueError("Manifest roles do not match the configured local model assets.")
    mismatches = [item["role"] for item in expected
                  if actual[item["role"]]["sha256"] != item.get("sha256") or
                  actual[item["role"]]["bytes"] != item.get("bytes")]
    if mismatches:
        raise ValueError("Model integrity mismatch: " + ", ".join(mismatches))
    return {"verified": True, "assets": len(actual)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--no-audio", action="store_true", help="Do not enumerate audio hardware")
    parser.add_argument("--manifest", type=Path, help="Write hashes of local model assets (does not overwrite)")
    parser.add_argument("--verify", type=Path, help="Verify local model assets against a saved manifest")
    args = parser.parse_args(argv)
    try:
        from dotenv import load_dotenv
        from luma.config import REPO_ROOT
        load_dotenv(REPO_ROOT / ".env", override=False)
        # CLI callers should load .env before importing model configuration.
        # Import was necessary only for the static project root; refresh its values.
        import importlib
        import luma.config
        importlib.reload(luma.config)
        if args.manifest:
            value = model_manifest()
            args.manifest.parent.mkdir(parents=True, exist_ok=True)
            with args.manifest.open("x") as handle:
                json.dump(value, handle, indent=2)
            print(f"Model manifest saved: {args.manifest}")
            return 0
        if args.verify:
            print(json.dumps(verify_manifest(json.loads(args.verify.read_text()))))
            return 0
        report = build_report(query_audio=not args.no_audio)
        if args.json:
            print(json.dumps(report, indent=2))
        else:
            for item in report["checks"]:
                status = "OK" if item["ok"] else "MISSING" if item["required"] else "PENDING"
                print(f"{status:7} {item['name']}: {item['detail']}")
            for item in report["audio_devices"]:
                print(f"Audio {item['index']}: {item['name']} ({item['inputs']} input / {item['outputs']} output channels)")
            print("Physical Jetson, privacy circuit, camera, LCD and light ring still need target-hardware tests.")
        return 0 if report["ready"] else 1
    except (OSError, ValueError) as exc:
        print(f"Device check failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

# Luma device setup and recovery

This checkout runs on the Mac now. The Jetson installer, service generator, private backup utility, model integrity checks, audio selection and optional GPIO privacy/indicator adapter are implemented. They are **not a claim that a physical Luma has been assembled or tested**.

## Hardware prerequisites

Target: NVIDIA Jetson Orin Nano Super 8 GB, supported JetPack, NVMe storage, USB ReSpeaker microphone, powered speaker, and the verified privacy circuit. Use the kit's **19 V barrel supply**. The USB-C connector is data-only. Follow [NVIDIA's setup guide](https://docs.nvidia.com/jetson/orin-nano-devkit/user-guide/latest/quick_start.html).

The proposed Waveshare 1.28-inch GC9A01 is a **240 × 240 SPI LCD**, not an I²C OLED. Camera Module 3 / IMX708 needs a driver matched to the installed JetPack/kernel and the correct connector cable. Camera capture, GC9A01 graphics, the NeoPixel ring, thermal/enclosure behavior and electrical sensor cutoff remain target-hardware milestones. No pin assignments are guessed by this code.

## Install on the Jetson

1. Clone the `mtsjay123-sudo/luma-lumin-device` repository onto the Jetson. Enter `Luma Home Prototype Code`. Do not copy the Mac `.venv`; create a native Linux environment.
2. Provide a trusted **Python 3.11 or newer** interpreter with venv support. JetPack's system Python may be older; this script does not replace it or add package repositories. Confirm the target Python and JetPack version before proceeding.
3. Inspect first, then install on the actual board:

   ```bash
   bash scripts/setup_jetson.sh --check
   bash scripts/setup_jetson.sh --install --python python3.11
   ```

   Add `--cuda` only when the matching CUDA toolkit is installed. CPU mode is the default. The installer refuses other platforms before package mutations. The current constraint file is a starting point; a clean Jetson install has not been validated.
4. Copy the local GGUF, Kokoro model/voices and cached Whisper assets. Set their device-local paths in `.env`. Never copy absolute Mac paths into a Jetson configuration. `LUMA_WHISPER_MODEL` can be a copied local model directory. Runtime model loading is offline; installation/downloads are a separate setup step.
5. Enumerate devices without recording:

   ```bash
   .venv/bin/python -m luma.hardware.diagnostics
   ```

   Set `LUMA_INPUT_DEVICE` and `LUMA_OUTPUT_DEVICE` to the reported exact device names or indexes. Ambiguous names and devices of the wrong direction are rejected. Use a stable distinct name where possible.
6. Start manually with `bash scripts/device_run.sh`. Open `http://127.0.0.1:8095/` on the device. Startup is muted. Verify input/output, local conversation and Stop before installing the boot service.
7. Preview, validate and install the unprivileged service:

   ```bash
   .venv/bin/python scripts/device_service.py
   .venv/bin/python scripts/device_service.py --check
   .venv/bin/python scripts/device_service.py --install
   ```

   Installation requires a detected Jetson, `systemd-analyze verify` and passing readiness checks. It enables `luma.service`, restarts failures with a bounded rate, and runs under the installing account. No microphone activation or automatic external actions occur on boot. Phone pairing is opt-in on the home LAN.

## Physical privacy feedback

Configure `LUMA_PRIVACY_GPIO` only after verifying the board pin and actual cutoff circuit, with `LUMA_PRIVACY_ACTIVE_LEVEL=0` or `1`. Optional `LUMA_INDICATOR_GPIO` and `LUMA_INDICATOR_ACTIVE_LEVEL` drive a plain digital status LED. These use BOARD numbering. A configured unreadable input blocks capture and stays faulted until repair/restart.

This adapter reads **feedback** from the circuit. Software does not physically disconnect microphone or camera power. Prove the electrical cutoff independently. A plain LED is not a NeoPixel driver. The Mac has no GPIO configured and uses its explicit software microphone toggle.

## Recovery and updates

Before updating, stop Luma and make a new private backup:

```bash
sudo systemctl stop luma.service
.venv/bin/python scripts/device_backup.py /your/private/backup-directory
```

The backup contains `state.db`, its matching `state.key`, local `.env` settings and a revision record. Keep all of it private; losing the key makes encrypted records unreadable. The backup refuses to overwrite an existing directory. Store a second copy on your own encrypted backup disk.

Record the current Git revision, review the incoming revision, update the checkout, rerun the target installer and checks, then start the service. If verification fails, return to the recorded revision and restore its matching environment. There is no unattended OTA updater. Do not reset or overwrite uncommitted work.

Use model manifests to verify transfer/recovery without embedding your Mac paths in the comparison:

```bash
.venv/bin/python -m luma.hardware.diagnostics --manifest /your/private/models.json
.venv/bin/python -m luma.hardware.diagnostics --verify /your/private/models.json
```

The hashes verify consistency with your saved assets; they are not an upstream authenticity attestation. Never run installer, updater or live provider transactions as an automated test.

## Physical acceptance checklist

- Cold boot and restart recovery, with microphone still muted.
- USB mic/speaker routing, unplug/replug, missing-device failure and long listening sessions.
- Actual electrical privacy cutoff, faulted input behavior and visible indicator.
- Normal speaker Stop and opt-in headphone voice interruption; no acoustic echo cancellation is claimed.
- Offline chat, hearing, speech, timers and saved notes; no silent downloads.
- Timers while asleep/stopped and recovered overdue reminders.
- Heat, sustained power, audio feedback, enclosure acoustics and storage capacity.
- Camera driver, SPI display, light ring and production update/recovery process on the selected parts.
- A real paired phone and one user-reviewed workflow through each connected account.

Mac tests and mocked GPIO tests cannot replace these physical checks.

"""Optional device adapters. Pins are supplied only after the wiring is verified.

The privacy input is feedback from an electrical cutoff, not the cutoff itself.
An unreadable configured input always blocks capture. Nothing accesses GPIO or
opens an audio stream merely by importing this module.
"""
from __future__ import annotations

from dataclasses import dataclass
import os
import threading
from typing import Mapping


@dataclass(frozen=True)
class DeviceConfig:
    privacy_pin: int | None = None
    privacy_active_level: int = 0
    indicator_pin: int | None = None
    indicator_active_level: int = 1

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None):
        env = os.environ if environ is None else environ

        def pin(name):
            value = env.get(name, "").strip()
            if not value:
                return None
            try:
                number = int(value)
            except ValueError as exc:
                raise ValueError(f"{name} must be a verified BOARD pin number.") from exc
            if not 1 <= number <= 40:
                raise ValueError(f"{name} must be a verified BOARD pin number from 1 to 40.")
            return number

        def level(name, required=False, default=0):
            value = env.get(name, "").strip()
            if not value and not required:
                return default
            if value not in {"0", "1"}:
                raise ValueError(f"{name} must explicitly be 0 or 1 for the actual circuit.")
            return int(value)

        privacy = pin("LUMA_PRIVACY_GPIO")
        indicator = pin("LUMA_INDICATOR_GPIO")
        if privacy is not None and privacy == indicator:
            raise ValueError("Privacy input and indicator output cannot share a pin.")
        return cls(privacy, level("LUMA_PRIVACY_ACTIVE_LEVEL", privacy is not None),
                   indicator, level("LUMA_INDICATOR_ACTIVE_LEVEL", indicator is not None, 1))


class DeviceController:
    """Read cutoff feedback and drive a plain status LED, with no pin defaults.

    ``privacy_state()`` returns configured/blocked/detail. ``capture_allowed()``
    can be included in every audio capture cancellation predicate. A fault does
    not automatically clear; call ``close()`` and repair/restart the device.
    The single LED is not a NeoPixel ring and does not attest electrical privacy.
    """
    def __init__(self, config: DeviceConfig | None = None, *, gpio=None):
        self.config = config or DeviceConfig.from_env()
        self._gpio = gpio
        self._lock = threading.RLock()
        self._fault = None
        self._closed = False
        self._pins = []
        if self.config.privacy_pin is None and self.config.indicator_pin is None:
            return
        try:
            if self._gpio is None:
                import Jetson.GPIO as GPIO
                self._gpio = GPIO
            self._gpio.setmode(self._gpio.BOARD)
            if self.config.privacy_pin is not None:
                self._gpio.setup(self.config.privacy_pin, self._gpio.IN)
                self._pins.append(self.config.privacy_pin)
            if self.config.indicator_pin is not None:
                self._gpio.setup(self.config.indicator_pin, self._gpio.OUT,
                                 initial=self.config.indicator_active_level)
                self._pins.append(self.config.indicator_pin)
        except Exception:
            # Do not leak low-level paths or treat an absent adapter as working.
            self._fault = "Configured GPIO is unavailable; check its driver, permissions and wiring."

    @classmethod
    def from_env(cls):
        return cls(DeviceConfig.from_env())

    def privacy_state(self):
        with self._lock:
            if self._closed:
                return {"configured": self.config.privacy_pin is not None, "blocked": True,
                        "detail": "Device controller stopped."}
            if self._fault:
                return {"configured": self.config.privacy_pin is not None, "blocked": True,
                        "detail": self._fault}
            if self.config.privacy_pin is None:
                return {"configured": False, "blocked": False,
                        "detail": "No physical cutoff feedback configured; software mute only."}
            try:
                value = self._gpio.input(self.config.privacy_pin)
                if value not in (0, 1):
                    raise ValueError("Invalid GPIO value")
                blocked = int(value) == self.config.privacy_active_level
                return {"configured": True, "blocked": blocked,
                        "detail": "Physical cutoff reports muted." if blocked else "Physical cutoff reports enabled."}
            except Exception:
                self._fault = "Privacy input could not be read; capture is blocked until restart."
                return {"configured": True, "blocked": True, "detail": self._fault}

    def capture_allowed(self):
        return not self.privacy_state()["blocked"]

    def set_indicator(self, *, muted: bool):
        """The configured plain LED illuminates for muted/fault state."""
        with self._lock:
            if self._closed or self.config.indicator_pin is None or self._fault:
                return False
            try:
                active = self.config.indicator_active_level
                self._gpio.output(self.config.indicator_pin,
                                  active if muted or not self.capture_allowed() else 1 - active)
                return True
            except Exception:
                self._fault = "Status indicator failed; capture is blocked until restart."
                return False

    def close(self):
        with self._lock:
            if self._closed:
                return
            self._closed = True
            if self._gpio is not None and self._pins:
                try:
                    self._gpio.cleanup(self._pins)
                except Exception:
                    pass


def resolve_audio_device(value, devices, *, direction):
    """Resolve an explicit PortAudio index or unique case-insensitive name.

    Returns None for the system default, and refuses ambiguous matches so the
    wrong microphone is not silently selected after USB enumeration changes.
    """
    if direction not in {"input", "output"}:
        raise ValueError("Audio direction must be input or output.")
    if value is None or not str(value).strip():
        return None
    text = str(value).strip()
    channel_key = f"max_{direction}_channels"
    matches = [(index, item) for index, item in enumerate(devices)
               if item.get(channel_key, 0) > 0 and
               ((text.isdecimal() and index == int(text)) or
                (not text.isdecimal() and text.casefold() in item.get("name", "").casefold()))]
    if len(matches) != 1:
        raise ValueError(f"Choose one available {direction} device; {text!r} matched {len(matches)} devices.")
    return matches[0][0]

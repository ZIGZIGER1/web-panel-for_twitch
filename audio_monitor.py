from __future__ import annotations

import threading
from dataclasses import dataclass

import numpy as np
import sounddevice as sd


@dataclass(slots=True)
class InputDevice:
    index: int
    name: str
    samplerate: int


class AudioMonitor:
    def __init__(self) -> None:
        self.stream: sd.InputStream | None = None
        self.level = 0.0
        self.status = ""
        self.lock = threading.Lock()

    def start(self, device: InputDevice) -> None:
        self.stop()

        def callback(indata: np.ndarray, frames: int, time_info, status) -> None:
            del frames, time_info
            power = 0.0
            if indata.size:
                power = min(float(np.sqrt(np.mean(indata.astype(np.float32) ** 2))) * 1500.0, 100.0)
            with self.lock:
                self.level = (self.level * 0.55) + (power * 0.45)
                self.status = str(status) if status else ""

        self.stream = sd.InputStream(
            device=device.index,
            channels=1,
            samplerate=device.samplerate,
            dtype="float32",
            callback=callback,
        )
        self.stream.start()

    def stop(self) -> None:
        if self.stream is not None:
            try:
                self.stream.stop()
            finally:
                self.stream.close()
                self.stream = None

        with self.lock:
            self.level = 0.0
            self.status = ""

    def snapshot(self) -> tuple[float, str]:
        with self.lock:
            return self.level, self.status

    @property
    def running(self) -> bool:
        return self.stream is not None


def list_input_devices() -> tuple[dict[str, InputDevice], list[str], str]:
    devices = sd.query_devices()
    device_map: dict[str, InputDevice] = {}
    labels: list[str] = []

    try:
        default_input = sd.default.device[0]
    except Exception:
        default_input = None

    default_label = ""

    for index, raw in enumerate(devices):
        if raw["max_input_channels"] < 1:
            continue
        label = f"{raw['name']} (#{index})"
        device_map[label] = InputDevice(
            index=index,
            name=label,
            samplerate=int(raw["default_samplerate"] or 44100),
        )
        labels.append(label)
        if index == default_input:
            default_label = label

    return device_map, labels, default_label
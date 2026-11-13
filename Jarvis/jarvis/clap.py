"""Double-clap detector.

A clap is a loud, very short burst of sound. We track the room's background
level and count a "clap" when the level jumps well above it and falls back
within ~120 ms (speech and music stay loud for longer, so they don't count).
Two claps between `min_gap` and `max_gap` seconds apart wake Jarvis.
"""
import threading
import time

import numpy as np
import sounddevice as sd

RATE = 16000
BLOCK = 256            # 16 ms per block
MAX_CLAP_SECONDS = 0.12


class ClapDetector:
    def __init__(self, cfg: dict):
        c = cfg["clap"]
        s = float(c.get("sensitivity", 1.0)) or 1.0
        self.ratio = 7.0 / s           # how far above background a clap must be
        self.min_level = 0.04 / s      # absolute floor so a silent room doesn't trigger on a tap
        self.min_gap = float(c.get("min_gap", 0.15))
        self.max_gap = float(c.get("max_gap", 0.9))
        self._reset()

    def _reset(self):
        self.noise = 0.005
        self.event_start = None
        self.last_clap = None
        self.blocks_seen = 0
        self.fired = threading.Event()

    def _process(self, rms: float, now: float):
        self.blocks_seen += 1
        threshold = max(self.noise * self.ratio, self.min_level)
        if self.event_start is None:
            if rms > threshold and self.blocks_seen > 30:   # ignore the first ~0.5 s while we learn the room
                self.event_start = now
            else:
                self.noise = 0.97 * self.noise + 0.03 * rms  # slowly learn the background level
        elif rms < threshold * 0.5:
            duration = now - self.event_start
            start, self.event_start = self.event_start, None
            if duration <= MAX_CLAP_SECONDS:
                self._on_clap(start)
        elif now - self.event_start > 1.0:
            self.event_start = None  # a long sound; not a clap

    def _on_clap(self, t: float):
        if self.last_clap is not None and self.min_gap <= t - self.last_clap <= self.max_gap:
            self.last_clap = None
            self.fired.set()
        else:
            self.last_clap = t

    def wait(self):
        """Block until a double clap is heard."""
        self._reset()

        def callback(indata, frames, time_info, status):
            rms = float(np.sqrt(np.mean(indata[:, 0] ** 2)))
            self._process(rms, time.monotonic())

        with sd.InputStream(samplerate=RATE, blocksize=BLOCK, channels=1, dtype="float32", callback=callback):
            while not self.fired.wait(0.1):
                pass

    def calibrate(self):
        """Print live levels so you can tune `sensitivity`."""
        print("Clap calibration: clap a few times. Ctrl+C to stop.\n")
        self._reset()
        claps = []

        def callback(indata, frames, time_info, status):
            rms = float(np.sqrt(np.mean(indata[:, 0] ** 2)))
            before = self.last_clap
            self._process(rms, time.monotonic())
            if self.last_clap != before and self.last_clap is not None:
                claps.append("clap")
            if self.fired.is_set():
                claps.append("DOUBLE CLAP - Jarvis would wake")
                self.fired.clear()

        try:
            with sd.InputStream(samplerate=RATE, blocksize=BLOCK, channels=1, dtype="float32", callback=callback):
                while True:
                    time.sleep(0.1)
                    threshold = max(self.noise * self.ratio, self.min_level)
                    while claps:
                        print("  ->", claps.pop(0))
                    print(f"\rbackground {self.noise:.4f}   clap threshold {threshold:.4f}   ", end="", flush=True)
        except KeyboardInterrupt:
            print()

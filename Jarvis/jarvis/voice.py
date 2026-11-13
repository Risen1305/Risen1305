"""Speech output: a calm British voice."""
import asyncio
import os
import re
import tempfile

import numpy as np
import sounddevice as sd

BRITISH_HINTS = ("george", "ryan", "thomas", "hazel", "susan", "daniel", "en-gb", "en_gb", "united kingdom", "british")


def _clean(text: str) -> str:
    # Strip markdown so it isn't read aloud.
    text = re.sub(r"[*_`#>]+", "", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    return text.strip()


class Voice:
    def __init__(self, cfg: dict, muted: bool = False):
        v = cfg["voice"]
        self.engine = v.get("engine", "edge")
        self.edge_voice = v.get("edge_voice", "en-GB-RyanNeural")
        self.rate = v.get("rate", "-8%")
        self.pitch = v.get("pitch", "-2Hz")
        self.muted = muted
        self._tts = None

    def say(self, text: str):
        text = _clean(text)
        if not text:
            return
        print(f"Jarvis: {text}")
        if self.muted:
            return
        if self.engine == "edge":
            try:
                self._say_edge(text)
                return
            except Exception as e:
                print(f"  (online voice unavailable: {e}; switching to the built-in voice)")
                self.engine = "system"
        self._say_system(text)

    def _say_edge(self, text: str):
        import edge_tts
        import miniaudio

        fd, path = tempfile.mkstemp(suffix=".mp3")
        os.close(fd)
        try:
            comm = edge_tts.Communicate(text, self.edge_voice, rate=self.rate, pitch=self.pitch)
            asyncio.run(comm.save(path))
            decoded = miniaudio.decode_file(path, output_format=miniaudio.SampleFormat.SIGNED16, nchannels=1)
            audio = np.frombuffer(decoded.samples, dtype=np.int16)
            sd.play(audio, decoded.sample_rate)
            sd.wait()
        finally:
            os.remove(path)

    def _say_system(self, text: str):
        if self._tts is None:
            import pyttsx3

            self._tts = pyttsx3.init()
            for voice in self._tts.getProperty("voices"):
                desc = f"{voice.id} {voice.name} {getattr(voice, 'languages', '')}".lower()
                if any(h in desc for h in BRITISH_HINTS):
                    self._tts.setProperty("voice", voice.id)
                    break
            self._tts.setProperty("rate", 165)
        self._tts.say(text)
        self._tts.runAndWait()


def chime(rising: bool = True):
    """A short, soft two-note tone: rising = 'I'm listening', falling = 'going to sleep'."""
    rate = 24000
    notes = (660, 880) if rising else (880, 587)
    parts = []
    for f in notes:
        t = np.linspace(0, 0.09, int(rate * 0.09), endpoint=False)
        tone = 0.18 * np.sin(2 * np.pi * f * t) * np.hanning(t.size)
        parts.append(tone)
    sd.play(np.concatenate(parts).astype(np.float32), rate)
    sd.wait()

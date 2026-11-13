"""Speech input: record until you stop talking, then transcribe locally with Whisper."""
import numpy as np
import sounddevice as sd

RATE = 16000
BLOCK = 800  # 50 ms


class Ears:
    def __init__(self, cfg: dict):
        e = cfg["ears"]
        self.model_name = e.get("whisper_model", "base.en")
        self.silence_seconds = float(e.get("silence_seconds", 1.2))
        self.max_seconds = float(e.get("max_listen_seconds", 15))
        self._model = None

    def load(self):
        if self._model is None:
            from faster_whisper import WhisperModel

            self._model = WhisperModel(self.model_name, device="cpu", compute_type="int8")

    def listen(self, wait_seconds: float = 6.0) -> str:
        """Return what was said, or '' if nobody spoke within `wait_seconds`."""
        audio = self._record(wait_seconds)
        if audio is None:
            return ""
        self.load()
        segments, _ = self._model.transcribe(audio, language="en", beam_size=1, vad_filter=True)
        return " ".join(s.text.strip() for s in segments).strip()

    def _record(self, wait_seconds: float):
        blocks = []
        noise = None
        speaking = False
        silent_for = 0.0
        waited = 0.0
        step = BLOCK / RATE
        with sd.InputStream(samplerate=RATE, blocksize=BLOCK, channels=1, dtype="float32") as stream:
            # Learn the room's background level for a moment.
            calib = [stream.read(BLOCK)[0][:, 0] for _ in range(4)]
            noise = max(float(np.sqrt(np.mean(np.concatenate(calib) ** 2))), 0.003)
            threshold = max(noise * 3.0, 0.012)
            pre_roll = []
            while True:
                chunk = stream.read(BLOCK)[0][:, 0].copy()
                loud = float(np.sqrt(np.mean(chunk ** 2))) > threshold
                if not speaking:
                    pre_roll = (pre_roll + [chunk])[-6:]  # keep 300 ms before speech starts
                    waited += step
                    if loud:
                        speaking = True
                        blocks.extend(pre_roll)
                    elif waited >= wait_seconds:
                        return None
                    continue
                blocks.append(chunk)
                silent_for = 0.0 if loud else silent_for + step
                if silent_for >= self.silence_seconds or len(blocks) * step >= self.max_seconds:
                    break
        return np.concatenate(blocks)

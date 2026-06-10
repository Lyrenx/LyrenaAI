from __future__ import annotations

import audioop
import json
import threading
from pathlib import Path

from core.config import (
    VOICE_BLOCKSIZE,
    VOICE_INPUT_DEVICE_HINTS,
    VOICE_INPUT_DEVICE_INDEX,
    VOICE_TARGET_SAMPLE_RATE,
)
from services.voice.engine import VoiceEngine


class VoskUnavailableError(RuntimeError):
    pass


class VoskVoiceEngine(VoiceEngine):
    def __init__(self, model_path: Path) -> None:
        try:
            import sounddevice as sd  # type: ignore
            from vosk import KaldiRecognizer, Model  # type: ignore
        except Exception as exc:  # pragma: no cover - optional dependency
            raise VoskUnavailableError("Vosk veya sounddevice yuklu degil") from exc

        if not model_path.exists():
            raise VoskUnavailableError(f"Model bulunamadi: {model_path}")

        self.sd = sd
        self.KaldiRecognizer = KaldiRecognizer
        self.Model = Model
        self.model_path = model_path
        self._thread = None
        self._stop_event = threading.Event()
        self._last_partial = ""
        self._started = False

    def start(self, on_text, on_error=None, on_partial=None):
        if self._started:
            return
        self._started = True
        self._stop_event.clear()
        device_index, device_info = self._select_input_device()
        input_samplerate = int(device_info.get("default_samplerate") or VOICE_TARGET_SAMPLE_RATE)
        model = self.Model(str(self.model_path))
        recognizer = self.KaldiRecognizer(model, VOICE_TARGET_SAMPLE_RATE)
        recognizer.SetWords(True)

        def _worker():
            try:
                rate_state = None

                def callback(indata, frames, time, status):
                    nonlocal rate_state
                    if self._stop_event.is_set():
                        raise self.sd.CallbackStop()

                    audio = bytes(indata)
                    if input_samplerate != VOICE_TARGET_SAMPLE_RATE:
                        audio, rate_state = audioop.ratecv(
                            audio,
                            2,
                            1,
                            input_samplerate,
                            VOICE_TARGET_SAMPLE_RATE,
                            rate_state,
                        )

                    if recognizer.AcceptWaveform(audio):
                        payload = json.loads(recognizer.Result())
                        text = payload.get("text", "").strip()
                        if text:
                            on_text(text)
                            self._last_partial = ""
                    else:
                        partial_payload = json.loads(recognizer.PartialResult())
                        partial = partial_payload.get("partial", "").strip()
                        if partial and partial != self._last_partial:
                            self._last_partial = partial
                            if on_partial is not None:
                                on_partial(partial)

                with self.sd.RawInputStream(
                    device=device_index,
                    samplerate=input_samplerate,
                    blocksize=VOICE_BLOCKSIZE,
                    dtype="int16",
                    channels=1,
                    callback=callback,
                ):
                    while not self._stop_event.is_set():
                        self._stop_event.wait(0.1)
            except Exception as exc:
                if on_error is not None:
                    on_error(exc)
                else:
                    raise

        from core.terminal import terminal_log

        terminal_log(
            "VOICE",
            f"Input device={device_index} rate={input_samplerate} target={VOICE_TARGET_SAMPLE_RATE}",
        )
        self._thread = threading.Thread(target=_worker, daemon=True)
        self._thread.start()

    def _select_input_device(self):
        if VOICE_INPUT_DEVICE_INDEX is not None:
            info = self.sd.query_devices(VOICE_INPUT_DEVICE_INDEX)
            return VOICE_INPUT_DEVICE_INDEX, info

        devices = self.sd.query_devices()
        default_input = self.sd.default.device[0] if self.sd.default.device else None

        for index, device in enumerate(devices):
            if device.get("max_input_channels", 0) <= 0:
                continue
            name = str(device.get("name", "")).lower()
            if any(hint.lower() in name for hint in VOICE_INPUT_DEVICE_HINTS):
                return index, device

        if default_input is not None and default_input >= 0:
            info = self.sd.query_devices(default_input)
            if info.get("max_input_channels", 0) > 0:
                return default_input, info

        for index, device in enumerate(devices):
            if device.get("max_input_channels", 0) > 0:
                return index, device

        raise VoskUnavailableError("Uygun bir mikrofon bulunamadi")

    def stop(self):
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        self._thread = None
        self._started = False

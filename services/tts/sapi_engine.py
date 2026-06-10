from __future__ import annotations

import queue
import threading
import time

from core.terminal import terminal_log
from services.tts.engine import TtsEngine


class SapiTtsUnavailable(RuntimeError):
    pass


class SapiTtsEngine(TtsEngine):
    def __init__(self) -> None:
        try:
            import pythoncom  # type: ignore
            import win32com.client  # type: ignore
        except Exception as exc:  # pragma: no cover - optional dependency
            raise SapiTtsUnavailable("Windows SAPI kullanilamadi") from exc

        self.pythoncom = pythoncom
        self.win32com = win32com
        self._queue: queue.Queue[str | None] = queue.Queue()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._voice = None
        self._started = False

    def start(self) -> None:
        if self._started:
            return
        self._started = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()

    def speak(self, text: str) -> None:
        clean = " ".join(str(text).split()).strip()
        if clean:
            self._queue.put(clean)

    def stop(self) -> None:
        self._stop_event.set()
        self._queue.put(None)
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.5)

    def _worker(self) -> None:
        self.pythoncom.CoInitialize()
        try:
            self._voice = self.win32com.client.Dispatch("SAPI.SpVoice")
            self._configure_voice(self._voice)
            terminal_log("TTS", "SAPI ses motoru hazir")

            while not self._stop_event.is_set():
                try:
                    item = self._queue.get(timeout=0.2)
                except queue.Empty:
                    continue

                if item is None:
                    break

                terminal_log("TTS", item)
                try:
                    self._voice.Speak(item, 0)
                except Exception as exc:
                    terminal_log("TTS-ERR", f"{type(exc).__name__}: {exc}")
        finally:
            self.pythoncom.CoUninitialize()

    def _configure_voice(self, voice) -> None:
        try:
            voices = list(voice.GetVoices())
            if not voices:
                return

            chosen = None
            for token in voices:
                text = f"{token.GetDescription()} {getattr(token, 'Name', '')}".lower()
                if "turk" in text or "türk" in text or "turkish" in text:
                    chosen = token
                    break
            if chosen is None:
                chosen = voices[0]

            voice.Voice = chosen
            voice.Rate = 0
            voice.Volume = 100
            terminal_log("TTS", f"Voice secildi: {chosen.GetDescription()}")
        except Exception as exc:
            terminal_log("TTS", f"Voice ayari atlandi: {exc}")


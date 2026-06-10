from __future__ import annotations

import threading

from services.voice.engine import VoiceEngine


class SilentVoiceEngine(VoiceEngine):
    def __init__(self, reason: str) -> None:
        self.reason = reason
        self._stop = threading.Event()

    def start(self, on_text, on_error=None, on_partial=None):
        # The GUI keeps running even when voice dependencies are missing.
        return None

    def stop(self):
        self._stop.set()

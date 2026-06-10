from __future__ import annotations

from services.tts.engine import TtsEngine


class SilentTtsEngine(TtsEngine):
    def __init__(self, reason: str) -> None:
        self.reason = reason

    def start(self) -> None:
        return None

    def speak(self, text: str) -> None:
        return None

    def stop(self) -> None:
        return None


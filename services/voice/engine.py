from __future__ import annotations

from abc import ABC, abstractmethod

from core.config import VOICE_MODEL_PATH


class VoiceEngine(ABC):
    @abstractmethod
    def start(self, on_text):
        raise NotImplementedError

    @abstractmethod
    def stop(self):
        raise NotImplementedError


def create_voice_engine() -> VoiceEngine:
    from services.voice.vosk_engine import VoskVoiceEngine, VoskUnavailableError

    try:
        return VoskVoiceEngine(VOICE_MODEL_PATH)
    except VoskUnavailableError as exc:
        from services.voice.fallback_engine import SilentVoiceEngine

        return SilentVoiceEngine(str(exc))

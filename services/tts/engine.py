from __future__ import annotations

from abc import ABC, abstractmethod


class TtsEngine(ABC):
    @abstractmethod
    def start(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def speak(self, text: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def stop(self) -> None:
        raise NotImplementedError


def create_tts_engine() -> TtsEngine:
    from services.tts.edge_engine import EdgeTtsEngine, EdgeTtsUnavailable
    from services.tts.sapi_engine import SapiTtsEngine, SapiTtsUnavailable

    try:
        return EdgeTtsEngine()
    except EdgeTtsUnavailable:
        try:
            return SapiTtsEngine()
        except SapiTtsUnavailable as exc:
            from services.tts.fallback_engine import SilentTtsEngine

            return SilentTtsEngine(str(exc))
    except Exception:
        from services.tts.fallback_engine import SilentTtsEngine

        return SilentTtsEngine("TTS baslatilamadi")

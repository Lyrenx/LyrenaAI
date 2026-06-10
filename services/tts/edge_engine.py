from __future__ import annotations

import asyncio
import queue
import threading

from PyQt6.QtCore import QByteArray, QBuffer, QObject, QIODevice, QUrl, pyqtSignal, pyqtSlot
from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer

from core.terminal import terminal_log
class EdgeTtsUnavailable(RuntimeError):
    pass


class EdgeTtsEngine(QObject):
    request_play = pyqtSignal(object)
    speaking_started = pyqtSignal()
    speaking_finished = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        try:
            import edge_tts  # type: ignore
        except Exception as exc:  # pragma: no cover - optional dependency
            raise EdgeTtsUnavailable("edge-tts yuklu degil") from exc

        self.edge_tts = edge_tts
        self.voice_name = "tr-TR-EmelNeural"
        self._started = False
        self._stop_event = threading.Event()
        self._queue: "queue.Queue[str | None]" | None = None
        self._worker: threading.Thread | None = None
        self._current_buffer: QBuffer | None = None
        self._current_audio: QByteArray | None = None
        self.audio_output = QAudioOutput()
        self.audio_output.setVolume(1.0)
        self.player = QMediaPlayer()
        self.player.setAudioOutput(self.audio_output)
        self.player.mediaStatusChanged.connect(self._on_media_status_changed)
        self.request_play.connect(self._play_audio)

    def start(self) -> None:
        if self._started:
            return
        self._started = True
        self._stop_event.clear()
        import queue

        self._queue = queue.Queue()
        self._worker = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker.start()
        terminal_log("TTS", f"Edge TTS hazir ({self.voice_name})")

    def speak(self, text: str) -> None:
        clean = " ".join(str(text).split()).strip()
        if not clean:
            return
        if self._queue is None:
            self.start()
        assert self._queue is not None
        self._queue.put(clean)

    def stop(self) -> None:
        self._stop_event.set()
        if self._queue is not None:
            self._queue.put(None)
        self.player.stop()
        self._cleanup_current_buffer()
        if self._worker and self._worker.is_alive():
            self._worker.join(timeout=1.5)

    def _worker_loop(self) -> None:
        assert self._queue is not None
        while not self._stop_event.is_set():
            try:
                item = self._queue.get(timeout=0.2)
            except Exception:
                continue

            if item is None:
                break

            try:
                audio_data = self._synthesize(item)
                self.request_play.emit(audio_data)
            except Exception as exc:
                terminal_log("TTS-ERR", f"{type(exc).__name__}: {exc}")
                self.speaking_finished.emit()

    def _synthesize(self, text: str) -> QByteArray:
        chunks: list[bytes] = []

        async def _collect() -> None:
            communicate = self.edge_tts.Communicate(text, voice=self.voice_name)
            async for chunk in communicate.stream():
                if chunk.get("type") == "audio":
                    data = chunk.get("data")
                    if data:
                        chunks.append(bytes(data))

        asyncio.run(_collect())
        return QByteArray(b"".join(chunks))

    @pyqtSlot(object)
    def _play_audio(self, audio_data) -> None:
        if isinstance(audio_data, QByteArray):
            payload = QByteArray(audio_data)
        else:
            payload = QByteArray(bytes(audio_data))

        if payload.isEmpty():
            terminal_log("TTS-ERR", "Bos ses verisi alindi")
            self.speaking_finished.emit()
            return

        self.player.stop()
        self._cleanup_current_buffer()
        self._current_audio = payload
        buffer = QBuffer(self)
        buffer.setData(payload)
        buffer.open(QIODevice.OpenModeFlag.ReadOnly)
        self._current_buffer = buffer
        self.player.setSourceDevice(buffer, QUrl("memory://lyrena/tts"))
        self.speaking_started.emit()
        self.player.play()
        terminal_log("TTS", "Bellekten oynatiliyor")

    def _on_media_status_changed(self, status) -> None:
        if status in (QMediaPlayer.MediaStatus.EndOfMedia, QMediaPlayer.MediaStatus.InvalidMedia):
            self._cleanup_current_buffer()
            self.speaking_finished.emit()

    def _cleanup_current_buffer(self) -> None:
        self.player.stop()
        if self._current_buffer is not None:
            try:
                self._current_buffer.close()
            except Exception:
                pass
        self._current_buffer = None
        self._current_audio = None

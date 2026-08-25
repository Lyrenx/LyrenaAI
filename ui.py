from __future__ import annotations

import json
import os
import queue
import sys
import threading
from pathlib import Path

from PyQt6.QtCore import QObject, QTimer, Qt, QUrl, pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings
from PyQt6.QtWebEngineWidgets import QWebEngineView

from actions.base import ActionContext
from core.config import (
    APP_NAME,
    COMMAND_WINDOW_SECONDS,
    DEFAULT_CITY,
    DEFAULT_LAT,
    DEFAULT_LON,
    SYSTEM_TICK_MS,
    UI_TICK_MS,
    WEATHER_TICK_MS,
)
from core.terminal import terminal_log
from core.phone_link import PhoneLink
from core.memory import MemoryStore
from core.router import CommandRouter
from core.state import AssistantState, DisplayMode
from services.gemini import GeminiService
from services.system_info import SystemInfoSampler
from services.voice.engine import create_voice_engine
from services.weather import WeatherService
from services.weather import WeatherSnapshot
from services.tts.engine import create_tts_engine
APP_ROOT = Path(__file__).resolve().parent
WEB_ROOT = APP_ROOT / "webui"
WEB_INDEX = WEB_ROOT / "index.html"


class Bridge(QObject):
    def __init__(self, window: "LyrenaWindow") -> None:
        super().__init__()
        self.window = window

    @pyqtSlot()
    def trigger_manual_wake(self) -> None:
        self.window.manual_wake()

    @pyqtSlot(int, int)
    def startDrag(self, screen_x: int, screen_y: int) -> None:
        self.window.start_drag(screen_x, screen_y)

    @pyqtSlot(int, int)
    def dragTo(self, screen_x: int, screen_y: int) -> None:
        self.window.drag_to(screen_x, screen_y)

    @pyqtSlot()
    def endDrag(self) -> None:
        self.window.end_drag()


class Controller:
    def __init__(self, window: "LyrenaWindow") -> None:
        self.window = window
        self.state = AssistantState()
        self.ready_color = "#2fe37b"
        self.busy_color = "#ff5b5b"
        self.idle_color = "#00ffcc"
        self.memory = MemoryStore()
        self.gemini = GeminiService(self.memory)
        self.action_context = ActionContext(controller=self)
        self.transcript_queue: queue.Queue[str] = queue.Queue()
        self.phone_command_queue: queue.Queue[str] = queue.Queue()
        self.phone_link = PhoneLink(self.handle_phone_command)
        self.router = CommandRouter(self)
        self.latest_weather: WeatherSnapshot | None = None
        self.phone_link.start()

    def handle_transcript(self, text: str) -> None:
        terminal_log("HEARD", text)
        self.transcript_queue.put(text)

    def handle_partial(self, text: str) -> None:
        terminal_log("PARTIAL", text)

    def handle_phone_command(self, command: str) -> None:
        self.phone_command_queue.put(command)

    def tick(self) -> None:
        while True:
            try:
                transcript = self.transcript_queue.get_nowait()
            except queue.Empty:
                break
            self.router.ingest_transcript(transcript)

        while True:
            try:
                command = self.phone_command_queue.get_nowait()
            except queue.Empty:
                break
            self.router.execute_command(command, response_target="phone")

        self.router.tick()
        self.window.sync_state_to_ui()

    def show_windowed(self) -> None:
        self.state.mode = DisplayMode.WINDOWED
        self.window.show_windowed()

    def show_fullscreen(self) -> None:
        self.state.mode = DisplayMode.FULLSCREEN
        self.window.show_fullscreen()

    def hide_window(self) -> None:
        self.state.mode = DisplayMode.HIDDEN
        self.state.status_text = "GIZLENDI"
        self.state.visual_state = "standby"
        self.window.hide_window()

    def request_exit(self) -> None:
        self.state.should_exit = True
        self.memory.close()
        self.window.request_exit()

    def request_restart(self) -> None:
        self.state.should_exit = True
        self.memory.close()
        self.window.request_restart()

    def log_status(self, text: str) -> None:
        self.state.status_text = text
        terminal_log("STATUS", text)

    def record_written(self, text: str, target: str = "pc") -> None:
        terminal_log("SPOKE", text)
        self.memory.add_message("assistant", text)
        if target == "phone":
            self.phone_link.speak(text)
            return
        if self.window.controller.state.should_exit:
            return
        try:
            self.window.speak_response(text)
        except Exception as exc:
            terminal_log("TTS-ERR", f"{type(exc).__name__}: {exc}")

    def get_weather_snapshot(self) -> WeatherSnapshot | None:
        return self.window.latest_weather

    def manual_wake(self) -> None:
        self.state.arm(COMMAND_WINDOW_SECONDS)
        self.state.status_text = "DINLIYOR..."
        self.state.visual_state = "listening"
        terminal_log("WAKE", "Manual wake triggered")
        self.window.sync_state_to_ui()

    def on_action_started(self, text: str = "ISLENIYOR") -> None:
        self.state.visual_state = "speaking"
        self.state.status_text = text
        terminal_log("ACTION", text)
        self.window.sync_state_to_ui()

    def on_action_finished(self) -> None:
        def reset_state() -> None:
            self.state.visual_state = "standby"
            self.window.sync_state_to_ui()

        QTimer.singleShot(220, reset_state)


class LyrenaWindow(QMainWindow):
    weather_ready = pyqtSignal(object, object, object)
    debug_command = pyqtSignal(str)
    gemini_response = pyqtSignal(str, str)
    gemini_decision = pyqtSignal(object, str)

    def __init__(self, *, enable_voice: bool = True, debug_console: bool = False) -> None:
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setStyleSheet("background: transparent;")
        self.resize(520, 360)
        self._drag_active = False
        self._drag_origin = None
        self._window_origin = None
        self._restart_requested = False
        self._page_loaded = False
        self._pending_js: list[str] = []
        self.latest_weather: WeatherSnapshot | None = None
        self._tts_lock_count = 0
        self._voice_paused_for_tts = False
        self._enable_voice = enable_voice
        self._debug_console = debug_console

        self.controller = Controller(self)
        self.system_sampler = SystemInfoSampler()
        self.weather_service = WeatherService(DEFAULT_CITY, DEFAULT_LAT, DEFAULT_LON)
        self.voice_engine = create_voice_engine()
        self.tts_engine = create_tts_engine()
        self.weather_ready.connect(self._apply_weather_result)
        self.debug_command.connect(self._handle_debug_command)
        self.gemini_response.connect(self._handle_gemini_response)
        self.gemini_decision.connect(self._handle_gemini_decision)
        if hasattr(self.tts_engine, "speaking_started") and hasattr(self.tts_engine, "speaking_finished"):
            self.tts_engine.speaking_started.connect(self._on_tts_started)
            self.tts_engine.speaking_finished.connect(self._on_tts_finished)

        self.browser = QWebEngineView(self)
        self.browser.setStyleSheet("background: transparent; border: none;")
        self.page = QWebEnginePage(self.browser)
        self.browser.setPage(self.page)
        self.page.setBackgroundColor(Qt.GlobalColor.transparent)
        self.page.settings().setAttribute(
            QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True
        )
        self.page.settings().setAttribute(
            QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True
        )
        self.page.settings().setAttribute(
            QWebEngineSettings.WebAttribute.Accelerated2dCanvasEnabled, False
        )
        self.setCentralWidget(self.browser)

        self.channel = QWebChannel(self.page)
        self.bridge = Bridge(self)
        self.channel.registerObject("pyBridge", self.bridge)
        self.page.setWebChannel(self.channel)
        self.page.loadFinished.connect(self.on_page_loaded)

        self.browser.setUrl(QUrl.fromLocalFile(str(WEB_INDEX)))

        self.system_timer = QTimer(self)
        self.system_timer.timeout.connect(self.refresh_system)
        self.system_timer.start(SYSTEM_TICK_MS)

        self.weather_timer = QTimer(self)
        self.weather_timer.timeout.connect(self.refresh_weather)
        self.weather_timer.start(WEATHER_TICK_MS)

        self.voice_timer = QTimer(self)
        self.voice_timer.timeout.connect(self.controller.tick)
        self.voice_timer.start(100)

        self.ui_timer = QTimer(self)
        self.ui_timer.timeout.connect(self.push_state_to_ui)
        self.ui_timer.start(UI_TICK_MS)

        if self._enable_voice:
            self.start_voice()
        else:
            terminal_log("VOICE", "STT devre disi (debug modu)")
        self.start_tts()
        if self._debug_console:
            self.start_debug_console()
        self.refresh_system()
        self.refresh_weather()
        self.sync_mode_to_ui(fullscreen=False)
        self.sync_state_to_ui()

    def run(self) -> None:
        self.show_windowed()

    def start_voice(self) -> None:
        engine_name = type(self.voice_engine).__name__
        terminal_log("VOICE", f"{engine_name} baslatiliyor")

        if hasattr(self.voice_engine, "reason"):
            terminal_log("VOICE", f"Fallback aktif: {self.voice_engine.reason}")
            return

        try:
            self.voice_engine.start(
                self.controller.handle_transcript,
                on_error=self._voice_error,
                on_partial=self.controller.handle_partial,
            )
            terminal_log("VOICE", "Mic dinleme basladi")
        except Exception as exc:
            self._voice_error(exc)

    def start_tts(self) -> None:
        engine_name = type(self.tts_engine).__name__
        terminal_log("TTS", f"{engine_name} baslatiliyor")

        if hasattr(self.tts_engine, "reason"):
            terminal_log("TTS", f"Fallback aktif: {self.tts_engine.reason}")
            return

        try:
            self.tts_engine.start()
        except Exception as exc:
            terminal_log("TTS-ERR", f"{type(exc).__name__}: {exc}")

    def start_debug_console(self) -> None:
        def worker() -> None:
            terminal_log("DEBUG", "Terminal komut modu hazir. /exit ile cikis yapabilirsin.")
            while True:
                try:
                    raw = input("Lyrena debug> ")
                except EOFError:
                    break
                except Exception as exc:
                    terminal_log("DEBUG-ERR", f"{type(exc).__name__}: {exc}")
                    break

                command = raw.strip()
                if not command:
                    continue
                if command in {"/exit", "/quit"}:
                    terminal_log("DEBUG", "Cikis komutu alindi")
                    self.debug_command.emit(command)
                    break
                self.debug_command.emit(command)

        threading.Thread(target=worker, daemon=True).start()

    @pyqtSlot(str)
    def _handle_debug_command(self, command: str) -> None:
        command = command.strip()
        if not command:
            return
        if command in {"/exit", "/quit"}:
            self.request_exit()
            return
        if command in {"/fullscreen", "/fs"}:
            self.show_fullscreen()
            return
        if command in {"/window", "/win"}:
            self.show_windowed()
            return
        if command in {"/hide"}:
            self.hide_window()
            return

        self.controller.router.execute_command(command)

    @pyqtSlot(str, str)
    def _handle_gemini_response(self, answer: str, response_target: str) -> None:
        self.controller.state.status_text = "HAZIR"
        self.controller.state.accent = self.controller.idle_color
        self.controller.state.visual_state = "standby"
        self.controller.record_written(answer, target=response_target)

    @pyqtSlot(object, str)
    def _handle_gemini_decision(self, decision: object, response_target: str) -> None:
        if not isinstance(decision, dict):
            self._handle_gemini_response(str(decision), response_target)
            return

        decision_type = str(decision.get("type", "answer")).strip().lower()
        if decision_type == "action":
            action_name = str(decision.get("action_name", "")).strip()
            command = str(decision.get("command", "")).strip()
            if action_name and self.controller.router.execute_action_by_name(
                action_name,
                command or action_name,
                response_target=response_target,
            ):
                return
            fallback = str(decision.get("message", "")).strip() or "Bu komut icin uygun bir action bulunamadi."
            self._handle_gemini_response(fallback, response_target)
            return

        message = str(decision.get("message", "")).strip()
        if not message:
            message = "Gemini su anda yanit veremiyor."
        self._handle_gemini_response(message, response_target)

    def _voice_error(self, exc: Exception) -> None:
        terminal_log("VOICE-ERR", f"{type(exc).__name__}: {exc}")
        self.controller.log_status("VOICE ERROR")

    def on_page_loaded(self, ok: bool) -> None:
        self._page_loaded = ok
        if ok:
            for code in self._pending_js:
                self.browser.page().runJavaScript(code)
            self._pending_js.clear()
            self.sync_mode_to_ui(self.controller.state.mode == DisplayMode.FULLSCREEN)
            self.sync_state_to_ui()

    def execute_js(self, code: str) -> None:
        if self._page_loaded:
            self.browser.page().runJavaScript(code)
        else:
            self._pending_js.append(code)

    def _js(self, func: str, *args) -> str:
        return f"{func}({', '.join(json.dumps(arg) for arg in args)});"

    def sync_state_to_ui(self) -> None:
        state = self.controller.state
        self.execute_js(self._js("setAiState", state.visual_state, state.status_text))

    def push_state_to_ui(self) -> None:
        self.sync_state_to_ui()

    def refresh_system(self) -> None:
        snapshot = self.system_sampler.snapshot()
        cpu = snapshot.cpu_percent
        ram = snapshot.ram_percent
        temp = snapshot.cpu_temp_c
        ram_used = snapshot.ram_used_gb
        ram_total = snapshot.ram_total_gb

        self.execute_js(
            self._js("updateTelemetry", cpu, ram, temp, ram_used, ram_total)
        )

    def refresh_weather(self) -> None:
        def worker() -> None:
            snapshot = self.weather_service.fetch()
            self.latest_weather = snapshot
            self.weather_ready.emit(
                snapshot.city,
                snapshot.temperature_c,
                snapshot.description,
            )

        threading.Thread(target=worker, daemon=True).start()

    def _apply_weather_result(self, city, temp, desc) -> None:
        self.execute_js(self._js("showWeather", city, temp, desc))

    def sync_mode_to_ui(self, fullscreen: bool) -> None:
        self.execute_js(self._js("toggleUIMode", fullscreen))

    def show_windowed(self) -> None:
        self.showNormal()
        self.resize(520, 360)
        self.center_on_screen()
        self.sync_mode_to_ui(False)
        self.execute_js(self._js("setPanelMode", "none"))

    def show_fullscreen(self) -> None:
        self.showFullScreen()
        self.sync_mode_to_ui(True)
        self.execute_js(self._js("setPanelMode", "all"))

    def hide_window(self) -> None:
        self.hide()

    def request_exit(self) -> None:
        self.controller.state.should_exit = True
        self.stop_voice()
        self.stop_tts()
        QApplication.instance().quit()

    def request_restart(self) -> None:
        self.controller.state.should_exit = True
        self._restart_requested = True
        self.stop_voice()
        self.stop_tts()
        QApplication.instance().quit()

    def stop_voice(self) -> None:
        try:
            self.voice_engine.stop()
        except Exception:
            pass

    def start_voice_safe(self) -> None:
        if self.controller.state.should_exit:
            return
        try:
            self.start_voice()
        except Exception:
            pass

    def stop_tts(self) -> None:
        try:
            self.tts_engine.stop()
        except Exception:
            pass

    def speak_response(self, text: str) -> None:
        if self.controller.state.should_exit:
            return
        if hasattr(self.tts_engine, "speaking_started") and hasattr(self.tts_engine, "speaking_finished"):
            self._pause_voice_for_tts()
        self.tts_engine.speak(text)

    def _pause_voice_for_tts(self) -> None:
        self._tts_lock_count += 1
        if self._voice_paused_for_tts:
            return
        self._voice_paused_for_tts = True
        self.stop_voice()
        terminal_log("VOICE", "TTS icin mikrofon durduruldu")

    def _on_tts_started(self) -> None:
        terminal_log("TTS", "Ses calimi basladi")

    def _on_tts_finished(self) -> None:
        if self._tts_lock_count > 0:
            self._tts_lock_count -= 1
        if self._tts_lock_count > 0:
            return
        if not self._voice_paused_for_tts:
            return
        self._voice_paused_for_tts = False
        self.start_voice_safe()
        terminal_log("VOICE", "TTS bitti, mikrofon yeniden acildi")

    def manual_wake(self) -> None:
        self.controller.manual_wake()

    def center_on_screen(self) -> None:
        screen = QApplication.primaryScreen().availableGeometry()
        x = int((screen.width() - self.width()) / 2)
        y = int((screen.height() - self.height()) / 2)
        self.move(x, y)

    def start_drag(self, screen_x: int, screen_y: int) -> None:
        if self.isFullScreen():
            return
        self._drag_active = True
        self._drag_origin = (screen_x, screen_y)
        self._window_origin = (self.frameGeometry().x(), self.frameGeometry().y())

    def drag_to(self, screen_x: int, screen_y: int) -> None:
        if not self._drag_active or self._drag_origin is None or self._window_origin is None:
            return
        dx = screen_x - self._drag_origin[0]
        dy = screen_y - self._drag_origin[1]
        self.move(self._window_origin[0] + dx, self._window_origin[1] + dy)

    def end_drag(self) -> None:
        self._drag_active = False
        self._drag_origin = None
        self._window_origin = None

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_F11:
            if self.isFullScreen():
                self.show_windowed()
            else:
                self.show_fullscreen()
            return
        if event.key() == Qt.Key.Key_Escape and self.isFullScreen():
            self.show_windowed()
            return
        if event.key() == Qt.Key.Key_H and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.hide_window()
            return
        if event.key() == Qt.Key.Key_Q and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.request_exit()
            return
        super().keyPressEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.start_drag(event.globalPosition().toPoint().x(), event.globalPosition().toPoint().y())
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._drag_active:
            self.drag_to(event.globalPosition().toPoint().x(), event.globalPosition().toPoint().y())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        self.end_drag()
        super().mouseReleaseEvent(event)

    def closeEvent(self, event) -> None:
        self.stop_voice()
        self.controller.phone_link.stop()
        event.accept()


def run_app(*, enable_voice: bool = True, debug_console: bool = False) -> None:
    app = QApplication.instance() or QApplication(sys.argv)
    window = LyrenaWindow(enable_voice=enable_voice, debug_console=debug_console)
    window.show_windowed()
    app.exec()

    if window._restart_requested:
        os.execv(sys.executable, [sys.executable, *sys.argv])

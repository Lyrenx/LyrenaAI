from __future__ import annotations

import queue
import threading
import tkinter as tk

from actions.base import ActionContext
from core.config import (
    APP_NAME,
    DEFAULT_CITY,
    DEFAULT_LAT,
    DEFAULT_LON,
    SYSTEM_TICK_MS,
    UI_TICK_MS,
    WEATHER_TICK_MS,
    WINDOWED_MIN_SIZE,
    WINDOWED_SIZE,
)
from core.router import CommandRouter
from core.state import AssistantState, DisplayMode
from services.system_info import SystemInfoSampler, format_system_snapshot
from services.voice.engine import create_voice_engine
from services.weather import WeatherService
from UI.theme import THEME
from UI.widgets import MetricBlock, OrbWidget, StatusStrip, current_time_text


class AssistantController:
    def __init__(self, window: "LyrenaAppWindow") -> None:
        self.window = window
        self.state = AssistantState()
        self.ready_color = THEME["ready"]
        self.busy_color = THEME["busy"]
        self.idle_color = THEME["idle"]
        self.action_context = ActionContext(controller=self)
        self.router = CommandRouter(self)
        self.transcript_queue: queue.Queue[str] = queue.Queue()

    def handle_transcript(self, text: str) -> None:
        self.transcript_queue.put(text)

    def tick(self) -> None:
        self.router.tick()

    def request_exit(self) -> None:
        self.state.should_exit = True
        self.window.stop_voice()
        self.window.destroy()

    def request_restart(self) -> None:
        self.state.should_exit = True
        self.window.restart_requested = True
        self.window.stop_voice()
        self.window.destroy()

    def hide_window(self) -> None:
        self.state.mode = DisplayMode.HIDDEN
        self.state.status_text = "Gizlendi"
        self.state.accent = self.idle_color
        self.window.withdraw()

    def show_windowed(self) -> None:
        self.state.mode = DisplayMode.WINDOWED
        self.window.show_windowed()

    def show_fullscreen(self) -> None:
        self.state.mode = DisplayMode.FULLSCREEN
        self.window.show_fullscreen()

    def log_status(self, text: str) -> None:
        self.state.status_text = text


class LyrenaAppWindow(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_NAME)
        self.configure(bg=THEME["bg"])
        self.geometry(WINDOWED_SIZE)
        self.minsize(*WINDOWED_MIN_SIZE)
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.attributes("-topmost", True)
        self.resizable(True, True)
        self.restart_requested = False

        self.controller = AssistantController(self)
        self.system_sampler = SystemInfoSampler()
        self.weather_service = WeatherService(DEFAULT_CITY, DEFAULT_LAT, DEFAULT_LON)
        self.voice_engine = create_voice_engine()
        self._weather_fetching = False
        self.weather_queue: queue.Queue[str] = queue.Queue()

        if hasattr(self.voice_engine, "reason"):
            self.controller.state.status_text = f"Ses kapali: {self.voice_engine.reason}"
            self.controller.state.accent = THEME["warning"]

        self._build_ui()
        self._bind_keys()
        self._start_voice()
        self.after(UI_TICK_MS, self._tick_animation)
        self.after(150, self._poll_voice_state)
        self.after(500, self._poll_weather_queue)
        self._refresh_system()
        self._refresh_weather()
        self._refresh_clock()

    def _build_ui(self) -> None:
        self.header = tk.Frame(self, bg=THEME["bg"])
        self.header.pack(fill="x", padx=14, pady=(12, 6))

        self.mode_button = tk.Button(
            self.header,
            text="Tam Ekran",
            command=self.toggle_mode,
            bg=THEME["panel"],
            fg=THEME["text"],
            activebackground=THEME["panel_alt"],
            activeforeground=THEME["text"],
            relief="flat",
            padx=12,
            pady=6,
        )
        self.hide_button = tk.Button(
            self.header,
            text="Gizle",
            command=self.hide_window,
            bg=THEME["panel"],
            fg=THEME["text"],
            activebackground=THEME["panel_alt"],
            activeforeground=THEME["text"],
            relief="flat",
            padx=12,
            pady=6,
        )
        self.mode_button.pack(side="right", padx=(6, 0))
        self.hide_button.pack(side="right")

        self.title_block = tk.Frame(self, bg=THEME["bg"])
        self.title_block.pack(fill="both", expand=True, padx=18, pady=(6, 8))

        self.orb = OrbWidget(self.title_block, width=260, height=260)
        self.orb.pack(pady=(18, 10))

        self.title_label = tk.Label(
            self.title_block,
            text=APP_NAME,
            bg=THEME["bg"],
            fg=THEME["text"],
            font=("Segoe UI", 24, "bold"),
        )
        self.subtitle_label = tk.Label(
            self.title_block,
            text="Wake words: Hey Bot / Ok Bot",
            bg=THEME["bg"],
            fg=THEME["muted"],
            font=("Segoe UI", 10),
        )
        self.title_label.pack()
        self.subtitle_label.pack(pady=(2, 0))

        self.metrics_row = tk.Frame(self, bg=THEME["bg"])
        self.metrics_row.pack(fill="x", padx=14, pady=(4, 4))

        self.clock_block = MetricBlock(self.metrics_row, "Saat", "00:00:00")
        self.weather_block = MetricBlock(self.metrics_row, "Hava Durumu", "Yukleniyor")
        self.system_block = MetricBlock(self.metrics_row, "Sistem", "Bekleniyor")
        self.clock_block.pack(side="left", expand=True, fill="x", padx=(0, 6))
        self.weather_block.pack(side="left", expand=True, fill="x", padx=6)
        self.system_block.pack(side="left", expand=True, fill="x", padx=(6, 0))

        self.status_strip = StatusStrip(self)
        self.status_strip.pack(fill="x", padx=14, pady=(8, 12))

    def _bind_keys(self) -> None:
        self.bind("<F11>", lambda _e: self.toggle_mode())
        self.bind("<Escape>", lambda _e: self.show_windowed())

    def _start_voice(self) -> None:
        self.voice_engine.start(self.controller.handle_transcript)

    def stop_voice(self) -> None:
        try:
            self.voice_engine.stop()
        except Exception:
            pass

    def run(self) -> None:
        self.mainloop()

    def on_close(self) -> None:
        self.stop_voice()
        self.destroy()

    def toggle_mode(self) -> None:
        if self.controller.state.mode == DisplayMode.FULLSCREEN:
            self.show_windowed()
        else:
            self.show_fullscreen()

    def show_windowed(self) -> None:
        self.attributes("-fullscreen", False)
        self.deiconify()
        self.geometry(WINDOWED_SIZE)
        self.attributes("-topmost", True)
        self.mode_button.config(text="Tam Ekran")
        self.controller.state.mode = DisplayMode.WINDOWED

    def show_fullscreen(self) -> None:
        self.deiconify()
        self.attributes("-fullscreen", True)
        self.attributes("-topmost", True)
        self.mode_button.config(text="Pencere")
        self.controller.state.mode = DisplayMode.FULLSCREEN

    def hide_window(self) -> None:
        self.controller.hide_window()

    def _tick_animation(self) -> None:
        state = self.controller.state
        if state.status_text.startswith("Ses kapali"):
            self.orb.set_color(THEME["warning"])
        elif state.awake or state.status_text == "Isleniyor":
            self.orb.set_color(state.accent)
        else:
            self.orb.set_color(THEME["idle"])

        self.orb.animate()
        self.status_strip.set_text(state.status_text)
        self.after(UI_TICK_MS, self._tick_animation)

    def _poll_voice_state(self) -> None:
        while True:
            try:
                transcript = self.controller.transcript_queue.get_nowait()
            except queue.Empty:
                break
            self.controller.router.ingest_transcript(transcript)

        self.controller.tick()
        self.after(150, self._poll_voice_state)

    def _refresh_clock(self) -> None:
        self.clock_block.set_value(current_time_text())
        self.after(1000, self._refresh_clock)

    def _refresh_system(self) -> None:
        snapshot = self.system_sampler.snapshot()
        cpu, ram, temp, memory = format_system_snapshot(snapshot)
        self.system_block.set_value(f"{cpu} | {ram}\n{temp} | {memory}")
        self.after(SYSTEM_TICK_MS, self._refresh_system)

    def _refresh_weather(self) -> None:
        if self._weather_fetching:
            self.after(WEATHER_TICK_MS, self._refresh_weather)
            return

        self._weather_fetching = True

        def worker() -> None:
            snapshot = self.weather_service.fetch()
            value = (
                f"{snapshot.city}\n{snapshot.description}"
                if snapshot.temperature_c is None
                else f"{snapshot.city} | {snapshot.temperature_c:.0f}C\n{snapshot.description}"
            )
            self.weather_queue.put(value)

        threading.Thread(target=worker, daemon=True).start()
        self.after(WEATHER_TICK_MS, self._refresh_weather)

    def _poll_weather_queue(self) -> None:
        while True:
            try:
                value = self.weather_queue.get_nowait()
            except queue.Empty:
                break
            self._weather_fetching = False
            self.weather_block.set_value(value)

        self.after(500, self._poll_weather_queue)

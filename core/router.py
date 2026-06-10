from __future__ import annotations

import time

from actions.loader import discover_actions
from core.config import ACTION_ROOT, COMMAND_WINDOW_SECONDS, WAKE_WORDS
from core.state import DisplayMode
from core.text import normalize_text, strip_wake_word


class CommandRouter:
    def __init__(self, controller) -> None:
        self.controller = controller
        self.actions = discover_actions(ACTION_ROOT)

    def refresh_actions(self) -> None:
        self.actions = discover_actions(ACTION_ROOT)

    def ingest_transcript(self, text: str) -> None:
        state = self.controller.state
        raw = text.strip()
        if not raw:
            return

        state.last_transcript = raw
        wake_hit, remainder = strip_wake_word(raw, WAKE_WORDS)

        if wake_hit:
            state.arm(COMMAND_WINDOW_SECONDS)
            state.status_text = "Komut bekleniyor"
            state.accent = self.controller.ready_color
            self.controller.log_status("Wake word algilandi")
            if remainder:
                state.command_buffer.append(remainder)
            return

        if state.awake:
            state.command_buffer.append(normalize_text(raw))

    def tick(self) -> None:
        state = self.controller.state
        if not state.awake:
            return

        if state.command_deadline and state.command_deadline <= time.time():
            self.finish_pending_command()

    def finish_pending_command(self) -> None:
        state = self.controller.state
        command = normalize_text(" ".join(state.command_buffer))
        state.disarm()

        if not command:
            state.status_text = "Komut alinmadi"
            state.accent = self.controller.idle_color
            self.controller.record_written("Komut alinmadi")
            return

        state.status_text = "ISLENIYOR"
        state.accent = self.controller.busy_color
        state.visual_state = "speaking"
        if hasattr(self.controller, "on_action_started"):
            self.controller.on_action_started(state.status_text)
        self.execute_command(command)

    def execute_command(self, text: str) -> None:
        normalized = normalize_text(text)
        state = self.controller.state

        if not normalized:
            state.status_text = "KOMUT ANLASILMADI"
            state.accent = self.controller.idle_color
            state.visual_state = "standby"
            self.controller.record_written("KOMUT ANLASILMADI")
            return

        matched = self.find_action(normalized)
        if matched is None:
            state.status_text = "KOMUT ANLASILMADI"
            state.accent = self.controller.idle_color
            state.visual_state = "standby"
            self.controller.log_status(f"Tanimlanmayan komut: {normalized}")
            self.controller.record_written("KOMUT ANLASILMADI")
            return

        try:
            outcome = matched["run"](self.controller.action_context, normalized) or {}
        except Exception as exc:
            state.status_text = "KOMUT HATASI"
            state.accent = self.controller.idle_color
            state.visual_state = "standby"
            self.controller.log_status(f"Aksiyon hatasi: {matched['name']} -> {exc}")
            self.controller.record_written("KOMUT HATASI")
            return

        state.status_text = outcome.get("message", f"{matched['name']} calisti")
        state.accent = self.controller.idle_color
        if hasattr(self.controller, "on_action_finished"):
            self.controller.on_action_finished()
        else:
            state.visual_state = "standby"
        should_exit = bool(outcome.get("exit"))
        if should_exit:
            state.should_exit = True

        if outcome.get("message") and outcome.get("speak", True) and not state.should_exit:
            self.controller.record_written(outcome["message"])

        if outcome.get("mode") == DisplayMode.HIDDEN:
            self.controller.hide_window()
        elif outcome.get("mode") == DisplayMode.FULLSCREEN:
            self.controller.show_fullscreen()
        elif outcome.get("mode") == DisplayMode.WINDOWED:
            self.controller.show_windowed()

        if should_exit:
            self.controller.request_exit()

    def find_action(self, text: str):
        best_action = None
        best_score = -1

        for action in self.actions:
            for trigger in action["triggers"]:
                if trigger in text:
                    score = len(trigger)
                    if score > best_score:
                        best_score = score
                        best_action = action

        return best_action

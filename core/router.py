from __future__ import annotations

import time
import threading
from pathlib import Path

from actions.loader import discover_actions
from core.config import ACTION_ROOT, COMMAND_WINDOW_SECONDS, WAKE_WORDS
from core.state import DisplayMode
from core.text import normalize_text, strip_wake_word


_CHAT_HINTS = (
    "sen nesin",
    "sen kimsin",
    "kimsin",
    "nedir",
    "ne demek",
    "ne yaparsin",
    "ne yapıyorsun",
    "ne yapiyorsun",
    "hangi",
    "neden",
    "nasil",
    "nasıl",
    "anlat",
    "acikla",
    "açıkla",
)

_ACTION_HINTS = (
    "ac ",
    "aç ",
    "kapat",
    "ara ",
    "mesaj",
    "gonder",
    "gönder",
    "uygulama",
    "youtube",
    "whatsapp",
    "telefon",
    "bildirim",
    "ekran",
    "uyandir",
    "uyandır",
    "yeniden baslat",
    "yeniden başlat",
    "gizlen",
    "tam ekran",
    "fullscreen",
    "windowed",
    "hava ",
)


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

    def execute_command(self, text: str, response_target: str = "pc") -> None:
        normalized = normalize_text(text)
        state = self.controller.state
        self.controller.memory.add_message("user", normalized)

        if not normalized:
            state.status_text = "KOMUT ANLASILMADI"
            state.accent = self.controller.idle_color
            state.visual_state = "standby"
            self.controller.record_written("KOMUT ANLASILMADI", target=response_target)
            return

        matched = self.find_action(normalized)
        if matched is None:
            if self._looks_like_action_request(normalized):
                state.status_text = "GEMINI DUSUNUYOR"
                state.accent = self.controller.busy_color
                state.visual_state = "thinking"
                threading.Thread(
                    target=self._ask_gemini_route,
                    args=(normalized, response_target),
                    daemon=True,
                ).start()
            else:
                state.status_text = "GEMINI YANITLIYOR"
                state.accent = self.controller.busy_color
                state.visual_state = "thinking"
                threading.Thread(
                    target=self._ask_gemini_answer,
                    args=(normalized, response_target),
                    daemon=True,
                ).start()
            return

        self._run_action(matched, normalized, response_target)

    def execute_action_by_name(
        self, action_name: str, text: str, response_target: str = "pc"
    ) -> bool:
        normalized_name = normalize_text(action_name)
        matched = self.find_action_by_name(normalized_name)
        if matched is None:
            self.controller.log_status(f"Gemini action bulunamadi: {action_name}")
            return False

        self._run_action(matched, text, response_target)
        return True

    def _run_action(
        self, matched: dict, text: str, response_target: str = "pc"
    ) -> None:
        state = self.controller.state
        try:
            outcome = matched["run"](self.controller.action_context, text) or {}
        except Exception as exc:
            state.status_text = "KOMUT HATASI"
            state.accent = self.controller.idle_color
            state.visual_state = "standby"
            self.controller.log_status(f"Aksiyon hatasi: {matched['name']} -> {exc}")
            self.controller.record_written("KOMUT HATASI", target=response_target)
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
            self.controller.record_written(outcome["message"], target=response_target)

        if outcome.get("mode") == DisplayMode.HIDDEN:
            self.controller.hide_window()
        elif outcome.get("mode") == DisplayMode.FULLSCREEN:
            self.controller.show_fullscreen()
        elif outcome.get("mode") == DisplayMode.WINDOWED:
            self.controller.show_windowed()

        if should_exit:
            self.controller.request_exit()

    def _ask_gemini_route(self, prompt: str, response_target: str) -> None:
        try:
            decision = self.controller.gemini.route_command(
                prompt, self._action_catalog()
            )
        except Exception as exc:
            self.controller.log_status(f"Gemini hatasi: {type(exc).__name__}: {exc}")
            decision = {
                "type": "answer",
                "message": "Gemini su anda yanit veremiyor. GEMINI_API_KEY ve internet baglantisini kontrol et.",
            }
        self.controller.window.gemini_decision.emit(decision, response_target)

    def _ask_gemini_answer(self, prompt: str, response_target: str) -> None:
        try:
            answer = self.controller.gemini.ask(prompt)
        except Exception as exc:
            self.controller.log_status(f"Gemini hatasi: {type(exc).__name__}: {exc}")
            answer = "Gemini su anda yanit veremiyor. GEMINI_API_KEY ve internet baglantisini kontrol et."
        self.controller.window.gemini_response.emit(answer, response_target)

    def find_action(self, text: str):
        best_action = None
        best_score = -1

        for action in self.actions:
            matcher = action.get("matches")
            if callable(matcher) and not matcher(text):
                continue
            for trigger in action["triggers"]:
                if trigger in text:
                    score = len(trigger)
                    if score > best_score:
                        best_score = score
                        best_action = action

        return best_action

    def find_action_by_name(self, action_name: str):
        for action in self.actions:
            if normalize_text(action.get("name", "")) == action_name:
                return action
            path = action.get("path")
            if isinstance(path, Path) and normalize_text(path.stem) == action_name:
                return action
        return None

    def _action_catalog(self) -> list[dict]:
        catalog: list[dict] = []
        for action in self.actions:
            catalog.append(
                {
                    "name": action.get("name", ""),
                    "triggers": action.get("triggers", []),
                }
            )
        return catalog

    def _looks_like_action_request(self, text: str) -> bool:
        if not text:
            return False

        if any(hint in text for hint in _CHAT_HINTS):
            return False

        if "?" in text:
            return False

        return any(hint in text for hint in _ACTION_HINTS)

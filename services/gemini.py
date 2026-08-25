from __future__ import annotations

import json
import os
from typing import Any

from core.memory import MemoryStore


class GeminiUnavailable(RuntimeError):
    pass


class GeminiService:
    def __init__(self, memory: MemoryStore) -> None:
        self.memory = memory
        self.api_key = os.environ.get("GEMINI_API_KEY", "").strip()
        self.model = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash").strip()
        self._client: Any = None

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def ask(self, prompt: str) -> str:
        if not self.configured:
            raise GeminiUnavailable(
                "Gemini API anahtari ayarlanmamis. GEMINI_API_KEY gerekli."
            )

        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:
            raise GeminiUnavailable(
                "google-genai yuklu degil. requirements.txt kurulumu gerekli."
            ) from exc

        if self._client is None:
            self._client = genai.Client(api_key=self.api_key)

        response = self._client.models.generate_content(
            model=self.model,
            contents=self._build_contents(prompt),
            config=types.GenerateContentConfig(
                system_instruction=(
                    self.memory.system_prompt()
                    + "\n"
                    + "Answer in Turkish.\n"
                    + "Keep replies short, but always finish the sentence completely.\n"
                    + "Never stop mid-word or leave the answer unfinished.\n"
                ),
                temperature=0.4,
                max_output_tokens=500,
                automatic_function_calling=types.AutomaticFunctionCallingConfig(
                    disable=True
                ),
            ),
        )
        answer = (getattr(response, "text", None) or "").strip()
        if not answer:
            raise GeminiUnavailable("Gemini bos bir yanit dondu.")
        if self._looks_incomplete(answer):
            answer = self._repair_answer(prompt, answer)
        return answer

    def route_command(self, prompt: str, actions: list[dict[str, Any]]) -> dict[str, str]:
        if not self.configured:
            raise GeminiUnavailable(
                "Gemini API anahtari ayarlanmamis. GEMINI_API_KEY gerekli."
            )

        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:
            raise GeminiUnavailable(
                "google-genai yuklu degil. requirements.txt kurulumu gerekli."
            ) from exc

        if self._client is None:
            self._client = genai.Client(api_key=self.api_key)

        routing_prompt = self._build_routing_prompt(prompt, actions)
        response = self._client.models.generate_content(
            model=self.model,
            contents=self._build_contents(routing_prompt),
            config=types.GenerateContentConfig(
                system_instruction=(
                    self.memory.system_prompt()
                    + "\n"
                    + "You are deciding whether a user command should run an existing Lyrena action.\n"
                    + "If an action fits, choose it and provide a concise command to pass to that action.\n"
                    + "If no action fits, answer normally in Turkish.\n"
                    + "Never invent an action name that is not in the list."
                ),
                temperature=0.2,
                max_output_tokens=250,
                response_mime_type="application/json",
                response_json_schema=self._route_response_schema(),
                automatic_function_calling=types.AutomaticFunctionCallingConfig(
                    disable=True
                ),
            ),
        )
        answer = (getattr(response, "text", None) or "").strip()
        if not answer:
            raise GeminiUnavailable("Gemini bos bir yanit dondu.")
        return self._parse_route_response(answer)

    def _build_contents(self, prompt: str) -> list[dict[str, Any]]:
        contents: list[dict[str, Any]] = []
        messages = self.memory.recent_messages(limit=20)
        if messages and messages[-1].role == "user" and messages[-1].content == prompt:
            messages = messages[:-1]
        for message in messages:
            role = "model" if message.role == "assistant" else "user"
            contents.append({"role": role, "parts": [{"text": message.content}]})
        contents.append({"role": "user", "parts": [{"text": prompt}]})
        return contents

    def _build_routing_prompt(self, prompt: str, actions: list[dict[str, Any]]) -> str:
        action_lines: list[str] = []
        for action in actions:
            triggers = ", ".join(action.get("triggers", []))
            action_lines.append(
                f'- {action.get("name", "unknown")}: {triggers}'
            )

        actions_text = "\n".join(action_lines) if action_lines else "- none"
        return (
            "User command:\n"
            f"{prompt}\n\n"
            "Available actions:\n"
            f"{actions_text}\n\n"
            "Return only the JSON object that matches the schema.\n"
        )

    def _route_response_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "type": {
                    "type": "string",
                    "enum": ["action", "answer"],
                },
                "action_name": {
                    "type": ["string", "null"],
                },
                "command": {
                    "type": ["string", "null"],
                },
                "message": {
                    "type": "string",
                },
            },
            "required": ["type", "message"],
            "additionalProperties": False,
        }

    def _parse_route_response(self, text: str) -> dict[str, str]:
        candidate = text.strip()

        start = candidate.find("{")
        end = candidate.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return {"type": "answer", "message": text.strip()}

        try:
            payload = json.loads(candidate[start : end + 1])
        except json.JSONDecodeError:
            return {"type": "answer", "message": text.strip()}

        kind = str(payload.get("type", "answer")).strip().lower()
        if kind == "action":
            action_name = str(payload.get("action_name", "")).strip()
            command = str(payload.get("command", "")).strip()
            message = str(payload.get("message", "")).strip()
            if not action_name:
                return {"type": "answer", "message": text.strip()}
            result: dict[str, str] = {
                "type": "action",
                "action_name": action_name,
                "command": command,
            }
            if message:
                result["message"] = message
            return result

        message = str(payload.get("message", "")).strip()
        if not message:
            message = text.strip()
        return {"type": "answer", "message": message}

    @staticmethod
    def _looks_incomplete(text: str) -> bool:
        clean = text.strip()
        if not clean:
            return False
        if clean.endswith((".", "!", "?", "…")):
            return False
        words = clean.split()
        if not words:
            return False
        last_word = words[-1].strip(".,!?;:\"'`()[]{}")
        if len(last_word) <= 3:
            return True
        return len(clean) > 12 and clean[-1].islower() and not clean.endswith(tuple("aeiouıioöuü"))

    def _repair_answer(self, prompt: str, draft: str) -> str:
        try:
            from google import genai
            from google.genai import types
        except ImportError:
            return draft

        if self._client is None:
            self._client = genai.Client(api_key=self.api_key)

        repair_prompt = (
            "Asagidaki cevabi tek bir tam Turkce cumle olarak duzelt.\n"
            "Kisa olsun, ama yarim kalmasin.\n"
            "Sadece duzeltilmis cevabi ver, aciklama yazma.\n\n"
            f"Soru: {prompt}\n"
            f"Cevap taslagi: {draft}\n"
        )
        response = self._client.models.generate_content(
            model=self.model,
            contents=repair_prompt,
            config=types.GenerateContentConfig(
                temperature=0.2,
                max_output_tokens=120,
                automatic_function_calling=types.AutomaticFunctionCallingConfig(
                    disable=True
                ),
            ),
        )
        repaired = (getattr(response, "text", None) or "").strip()
        return repaired or draft

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from core.config import WHATSAPP_CONTACTS_PATH
from core.text import normalize_text


@dataclass
class WhatsAppContact:
    name: str
    number: str
    aliases: list[str] = field(default_factory=list)


_COMMAND_TOKENS = {
    "whatsapp",
    "mesaj",
    "mesajini",
    "yaz",
    "gonder",
    "gonderi",
    "at",
    "yolla",
    "ile",
    "icin",
    "kisisine",
    "kisine",
    "kisiye",
    "uzerinden",
    "tarafindan",
}


def load_contacts(path: Path | None = None) -> list[WhatsAppContact]:
    source = path or WHATSAPP_CONTACTS_PATH
    if not source.exists():
        return []

    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except Exception:
        return []

    contacts: list[WhatsAppContact] = []
    if isinstance(payload, dict):
        for name, raw in payload.items():
            contact = _parse_contact(name, raw)
            if contact is not None:
                contacts.append(contact)
    elif isinstance(payload, list):
        for raw in payload:
            contact = _parse_contact("bilinmeyen", raw)
            if contact is not None:
                contacts.append(contact)

    return contacts


def resolve_contact(text: str, path: Path | None = None) -> tuple[WhatsAppContact | None, str]:
    contacts = load_contacts(path)
    cleaned = normalize_text(text)
    if not contacts:
        return None, cleaned

    tokens = cleaned.split()
    if not tokens:
        return None, ""

    best_contact: WhatsAppContact | None = None
    best_alias = ""
    best_index = -1

    for contact in contacts:
        for alias in [contact.name, *contact.aliases]:
            alias_clean = normalize_text(alias)
            if not alias_clean:
                continue
            for index, token in enumerate(tokens):
                if token == alias_clean or token.startswith(alias_clean):
                    if len(alias_clean) > len(best_alias):
                        best_contact = contact
                        best_alias = alias_clean
                        best_index = index

    if best_contact is None:
        return None, cleaned

    remaining_tokens = [token for index, token in enumerate(tokens) if index != best_index]
    message_tokens = [token for token in remaining_tokens if token not in _COMMAND_TOKENS]
    return best_contact, normalize_text(" ".join(message_tokens))


def normalize_number(number: str) -> str:
    digits = re.sub(r"\D+", "", str(number))
    if not digits:
        return ""

    if digits.startswith("0090") and len(digits) >= 14:
        digits = digits[2:]
    elif digits.startswith("0") and len(digits) == 11:
        digits = f"90{digits[1:]}"
    elif digits.startswith("5") and len(digits) == 10:
        digits = f"90{digits}"
    elif len(digits) == 10:
        digits = f"90{digits}"

    if not digits.startswith("90") and len(digits) >= 11:
        digits = f"90{digits.lstrip('0')}"

    return f"+{digits}"


def build_wa_link(number: str, message: str = "") -> str:
    clean_number = normalize_number(number).replace("+", "")
    if not clean_number:
        return "https://web.whatsapp.com/"

    url = f"https://wa.me/{clean_number}"
    if message:
        from urllib.parse import quote

        url += f"?text={quote(message)}"
    return url


def _parse_contact(name: str, raw) -> WhatsAppContact | None:
    if isinstance(raw, str):
        number = raw
        aliases = [name]
    elif isinstance(raw, dict):
        number = raw.get("number") or raw.get("phone") or raw.get("value") or ""
        aliases = raw.get("aliases") or raw.get("alias") or []
        if isinstance(aliases, str):
            aliases = [aliases]
        aliases = [name, *aliases]
    else:
        return None

    clean_number = normalize_number(number)
    if not clean_number:
        return None

    return WhatsAppContact(
        name=name,
        number=clean_number,
        aliases=[alias for alias in aliases if alias],
    )

from __future__ import annotations

import re
import webbrowser

from actions.base import outcome
from core.text import normalize_text, remove_phrases, strip_tokens
from services.contacts.whatsapp_contacts import (
    build_wa_link,
    normalize_number,
    resolve_contact,
)

ACTION_NAME = "whatsappmessage"
TRIGGERS = (
    "whatsapp",
    "whatsapp mesaj",
    "whatsapp mesaj yaz",
    "whatsapp mesaj gonder",
    "whatsapp mesaj gonder",
    "whatsapp a mesaj yaz",
    "whatsappa mesaj yaz",
    "mesaj gonder",
    "mesaj yaz",
)


def run(context, text: str) -> dict:
    contact, message = resolve_contact(text)
    number = contact.number if contact is not None else _extract_number(text)

    if not number:
        webbrowser.open("https://web.whatsapp.com/")
        return outcome("WhatsApp acildi, ancak kisi bulunamadi")

    if not message:
        message = _extract_message(text)

    if not message:
        webbrowser.open("https://web.whatsapp.com/")
        return outcome("Mesaj metni bulunamadi")

    url = build_wa_link(number, message)
    webbrowser.open(url)

    if contact is not None:
        return outcome(f"WhatsApp acildi. {contact.name} icin mesaj hazirlaniyor")
    return outcome("WhatsApp acildi")


def _extract_number(text: str) -> str:
    digits = "".join(re.findall(r"\d+", text))
    if not digits:
        return ""
    return normalize_number(digits)


def _extract_message(text: str) -> str:
    cleaned = normalize_text(text)
    cleaned = remove_phrases(
        cleaned,
        (
            "whatsapp",
            "mesajini",
            "mesaj",
            "mesaj gonder",
            "mesaj yaz",
            "gonder",
            "gonder",
            "yaz",
            "at",
            "uzerinden",
            "icin",
            "kisisine",
            "kisine",
            "kisiye",
            "gor",
            "goster",
        ),
    )
    cleaned = strip_tokens(
        cleaned,
        (
            "whatsapp",
            "mesaj",
            "mesajini",
            "gonder",
            "yaz",
            "at",
            "kisisine",
            "kisine",
            "kisiye",
            "uzerinden",
            "icin",
        ),
    )
    return cleaned

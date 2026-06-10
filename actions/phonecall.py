from __future__ import annotations

import re
import webbrowser

from actions.base import outcome
from services.contacts.whatsapp_contacts import normalize_number

ACTION_NAME = "phonecall"
TRIGGERS = ("telefon ara", "telefon aramasi yap", "telefonu ara", "call")


def run(context, text: str) -> dict:
    number = "".join(re.findall(r"\d+", text))
    if number:
        webbrowser.open(f"tel:{normalize_number(number)}")
        return outcome("Arama komutu hazirlandi")

    webbrowser.open("tel:")
    return outcome("Arama uygulamasi acildi")

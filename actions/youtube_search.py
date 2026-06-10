from __future__ import annotations

import urllib.parse
import webbrowser

from actions.base import outcome
from core.text import normalize_text, remove_phrases

ACTION_NAME = "youtube_search"
TRIGGERS = (
    "youtube",
    "youtube'de ara",
    "youtube de ara",
    "youtube'da ara",
    "youtube da ara",
    "youtube videosu ara",
    "youtube video ara",
    "video ara",
    "videoyu ara",
)


def run(context, text: str) -> dict:
    query = normalize_text(text)
    query = remove_phrases(
        query,
        (
            "youtube de ara",
            "youtube da ara",
            "youtube'de ara",
            "youtube'da ara",
            "youtube videosu ara",
            "youtube video ara",
        ),
    )
    stopwords = {
        "youtube",
        "video",
        "videosu",
        "videoyu",
        "ara",
        "bul",
        "ac",
        "izle",
    }
    filtered_tokens = [
        token
        for token in query.split()
        if token not in stopwords and "youtu" not in token
    ]
    query = " ".join(filtered_tokens).strip()

    if not query:
        query = "lyrena ai"

    url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote(query)
    webbrowser.open(url)
    return outcome(f"YouTube'de '{query}' araniyor")

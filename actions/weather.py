from __future__ import annotations

from actions.base import outcome

ACTION_NAME = "weather"
TRIGGERS = (
    "hava ne",
    "hava durumu",
    "hava nasil",
    "disarida hava",
    "hava durumu ne",
)


def run(context, text: str) -> dict:
    snapshot = context.controller.get_weather_snapshot()

    if snapshot is None:
        return outcome("Hava bilgisi henüz hazır değil")

    if snapshot.temperature_c is None:
        message = f"{snapshot.city} için hava bilgisi alınamadı. {snapshot.description}."
    else:
        message = f"{snapshot.city} hava durumu {snapshot.temperature_c:.0f} derece. {snapshot.description}."

    return outcome(message)


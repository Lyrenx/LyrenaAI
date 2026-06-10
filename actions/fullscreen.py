from core.state import DisplayMode
from actions.base import outcome

ACTION_NAME = "fullscreen"
TRIGGERS = ("tam ekran", "fullscreen", "full screen", "ekranı kapla")


def run(context, text: str) -> dict:
    context.controller.show_fullscreen()
    return outcome("Tam ekran modu", mode=DisplayMode.FULLSCREEN)


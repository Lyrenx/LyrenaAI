from core.state import DisplayMode
from actions.base import outcome

ACTION_NAME = "hide"
TRIGGERS = ("gizlen", "saklan", "gizle", "gizem","gizleyen", "hide", "sakla")


def run(context, text: str) -> dict:
    context.controller.hide_window()
    return outcome("Lyrena gizlendi", mode=DisplayMode.HIDDEN)


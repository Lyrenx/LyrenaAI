from core.state import DisplayMode
from actions.base import outcome

ACTION_NAME = "windowed"
TRIGGERS = ("pencere modu", "pencereli mod", "windowed", "pencere", "normal mod", "görün")


def run(context, text: str) -> dict:
    context.controller.show_windowed()
    return outcome("Pencere modu", mode=DisplayMode.WINDOWED)

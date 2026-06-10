from dataclasses import dataclass
from typing import Any


@dataclass
class ActionContext:
    controller: Any


def outcome(message: str = "", mode=None, exit: bool = False, speak: bool = True) -> dict:
    data = {"message": message, "exit": exit, "speak": speak}
    if mode is not None:
        data["mode"] = mode
    return data

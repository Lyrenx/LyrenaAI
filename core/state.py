from dataclasses import dataclass, field
from enum import Enum
import time


class DisplayMode(str, Enum):
    WINDOWED = "windowed"
    FULLSCREEN = "fullscreen"
    HIDDEN = "hidden"


@dataclass
class AssistantState:
    mode: DisplayMode = DisplayMode.WINDOWED
    awake: bool = False
    visual_state: str = "standby"
    command_deadline: float = 0.0
    command_buffer: list[str] = field(default_factory=list)
    listening_text: str = ""
    last_transcript: str = ""
    status_text: str = "Hazir"
    accent: str = "#6176ff"
    should_exit: bool = False

    def arm(self, seconds: float) -> None:
        self.awake = True
        self.visual_state = "listening"
        self.command_deadline = time.time() + seconds
        self.command_buffer.clear()

    def disarm(self) -> None:
        self.awake = False
        self.visual_state = "standby"
        self.command_deadline = 0.0
        self.command_buffer.clear()
        self.listening_text = ""

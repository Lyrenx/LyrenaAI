from pathlib import Path


APP_NAME = "Lyrena AI"
APP_ROOT = Path(__file__).resolve().parents[1]
UI_ROOT = APP_ROOT / "UI"
ACTION_ROOT = APP_ROOT / "actions"
WHATSAPP_CONTACTS_PATH = APP_ROOT / "config" / "whatsapp_contacts.json"
VOICE_MODEL_ROOT = APP_ROOT / "voicemodel"
VOICE_MODEL_PATH = VOICE_MODEL_ROOT / "vosk-model-small-tr-0.3"

WINDOWED_SIZE = "420x620"
WINDOWED_MIN_SIZE = (360, 540)

WAKE_WORDS = ("hey bot", "ok bot", "hey yapay", "ok yapay")
COMMAND_WINDOW_SECONDS = 6.0

COLOR_BG = "#090b12"
COLOR_PANEL = "#0f1420"
COLOR_PANEL_ALT = "#131a28"
COLOR_TEXT = "#e6edf7"
COLOR_MUTED = "#8b96ab"
COLOR_IDLE = "#6176ff"
COLOR_READY = "#2fe37b"
COLOR_BUSY = "#ff5b5b"
COLOR_WARNING = "#ffb84d"
COLOR_EDGE = "#1f2a3d"

DEFAULT_CITY = "Istanbul"
DEFAULT_LAT = 41.0082
DEFAULT_LON = 28.9784

UI_TICK_MS = 33
SYSTEM_TICK_MS = 1200
WEATHER_TICK_MS = 15 * 60 * 1000

VOICE_TARGET_SAMPLE_RATE = 16000
VOICE_BLOCKSIZE = 4096
VOICE_INPUT_DEVICE_INDEX = None
VOICE_INPUT_DEVICE_HINTS = (
    "USB Audio Device",
    "Mikrofon",
    "Microphone",
    "Realtek",
)

from __future__ import annotations

from datetime import datetime


def terminal_log(source: str, message: str) -> None:
    stamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{stamp}] [{source}] {message}", flush=True)


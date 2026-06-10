import subprocess

from actions.base import outcome

ACTION_NAME = "shutdowncomputer"
TRIGGERS = (
    "bilgisayari kapat",
    "bilgisayar kapat",
    "pc kapat",
    "sistemi kapat",
    "kapat bilgisayar",
)


def run(context, text: str) -> dict:
    subprocess.Popen(["shutdown", "/s", "/t", "0"], shell=False)
    return outcome("Bilgisayar kapatma komutu verildi", speak=False)

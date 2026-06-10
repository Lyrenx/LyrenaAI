import subprocess

from actions.base import outcome

ACTION_NAME = "restartcomputer"
TRIGGERS = (
    "bilgisayari yeniden baslat",
    "bilgisayar yeniden baslat",
    "pc yeniden baslat",
    "sistemi yeniden baslat",
    "yeniden baslat bilgisayar",
)


def run(context, text: str) -> dict:
    subprocess.Popen(["shutdown", "/r", "/t", "0"], shell=False)
    return outcome("Bilgisayar yeniden baslatma komutu verildi", speak=False)

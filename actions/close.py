from actions.base import outcome

ACTION_NAME = "close"
TRIGGERS = ("kapan", "kapat", "cik", "quit", "exit")


def run(context, text: str) -> dict:
    context.controller.log_status("Lyrena kapatiliyor")
    return outcome("Lyrena kapaniyor", exit=True, speak=False)

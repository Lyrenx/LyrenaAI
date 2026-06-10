from actions.base import outcome

ACTION_NAME = "restart"
TRIGGERS = ("yeniden baslat", "restart et", "restart", "uygulamayi yeniden baslat")


def run(context, text: str) -> dict:
    context.controller.log_status("Lyrena yeniden baslatiliyor")
    context.controller.request_restart()
    return outcome("Lyrena yeniden baslatiliyor", exit=True, speak=False)

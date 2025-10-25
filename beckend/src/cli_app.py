import time
from datetime import datetime
from .scheduler import TikTokScheduler

def run_cli(visible: bool = False):
    """
    visible=False => HEADLESS (segundo plano)
    visible=True  => COM JANELA
    """
    def log(m): print(f"[{datetime.now().strftime('%H:%M:%S')}] {m}")

    print("\n=== TikTok Scheduler (Modo CLI) ===\n")
    acc = "default"
    print(f"Conta ativa: {acc}")

    sched = TikTokScheduler(account_name=acc, logger=log, visible=visible)
    sched.initial_setup()
    print("Iniciando agendador real (Ctrl+C para sair)...")
    sched.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nEncerrando agendador...")
        sched.stop()
        print("Finalizado.")

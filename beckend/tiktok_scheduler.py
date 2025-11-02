# tiktok_scheduler.py - Versão com Scheduler Daemon Multi-Conta
import sys
import argparse
import threading
import time
import traceback

from src.cli_app import run_cli
from src.gui_app import run_gui
from src.driver import build_driver
from src.cookies import save_cookies
from src.paths import account_dirs
from src.scheduler import TikTokScheduler
from src.scheduler_daemon import start_scheduler_daemon, stop_scheduler_daemon
import uvicorn  # pyright: ignore[reportMissingImports]

from pathlib import Path
import os, stat, subprocess
from dotenv import load_dotenv

def _force_perms():
    targets = ["/app/users", "/app/state", "users", "state"]
    for t in targets:
        p = Path(t)
        if p.exists():
            try:
                # dá permissão total (rwx) recursiva
                subprocess.run(["chmod", "-R", "0777", str(p)], check=False)
            except Exception:
                pass
_force_perms()


def start_http(app):
    # força asyncio, evita uvloop
    config = uvicorn.Config(app, host="0.0.0.0", port=8082, log_level="info", loop="asyncio", http="h11")
    server = uvicorn.Server(config)
    server.run()  # roda síncrono; se quiser em thread, suba antes do scheduler

if __name__ == "__main__":
    load_dotenv(Path(__file__).resolve().parent / ".env")
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")

    raw_visible = os.getenv("TIKTOK_BROWSER_VISIBLE", "")
    visible = str(raw_visible).strip().lower() in {"1", "true", "yes", "on"}

    # 1) sobe HTTP no thread dedicado PRIMEIRO
    import threading
    from src.http_health import app as http_app
    http_thread = threading.Thread(target=start_http, args=(http_app,), daemon=True)
    http_thread.start()

    # 2) Inicia o daemon de schedulers (um scheduler por conta TikTok)
    print("🔄 Iniciando daemon de schedulers multi-conta...")
    if visible:
        print("🖥️ Navegador visível habilitado (TIKTOK_BROWSER_VISIBLE)")
    else:
        print("🕶️ Executando em modo headless (defina TIKTOK_BROWSER_VISIBLE=1 para visualizar o Chrome)")
    scheduler_daemon = start_scheduler_daemon(visible=visible)

    # 3) mantém o processo vivo
    try:
        print("🚀 Servidor HTTP rodando na porta 8082")
        print("📊 Sistema multi-conta ativo - cada conta tem seu próprio scheduler")
        print("💡 O daemon monitora o banco de dados e cria schedulers automaticamente")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Encerrando sistema...")
        stop_scheduler_daemon()
        print("✅ Sistema encerrado")


def save_cookies_interactive():
    """
    DEPRECADO: Agora cada conta TikTok tem seus próprios cookies armazenados no banco de dados.
    Use a interface web para gerenciar cookies de contas.
    """
    print("\n❌ DEPRECADO: Use a interface web para gerenciar contas TikTok")
    print("📋 Acesse: http://localhost:8082/tiktok-accounts")
    print("💡 Cada conta tem seus próprios cookies isolados")
    return

def run_cli_wrapper(visible=False):
    """
    DEPRECADO: Sistema agora usa isolamento por conta via banco de dados.
    Use a interface web para gerenciar agendamentos.
    """
    print("\n❌ DEPRECADO: Modo CLI não é mais suportado")
    print("📋 Use a interface web: http://localhost:8082")
    print("💡 Sistema agora tem isolamento completo por conta TikTok")
    return

if __name__ == "__main__" and len(sys.argv) > 1:
    try:
        parser = argparse.ArgumentParser(prog="tiktok_scheduler")
        parser.add_argument("--cli", action="store_true", help="Executa em modo terminal (DEPRECADO)")
        parser.add_argument("--browser", "--visible", dest="visible", action="store_true",
                            help="No modo --cli, abre o navegador visível (DEPRECADO)")
        parser.add_argument("--save-cookies", action="store_true", help="Abre navegador para salvar cookies (DEPRECADO)")
        args = parser.parse_args()

        if args.save_cookies:
            save_cookies_interactive()
        elif args.cli:
            run_cli_wrapper(visible=args.visible)
        else:
            run_gui()  # GUI desktop opcional (tkinter)
    except Exception as e:
        print(f"❌ Erro fatal não tratado: {e}")
        traceback.print_exc()
        sys.exit(1)
    except KeyboardInterrupt:
        print("🛑 Encerrado pelo usuário.")
        sys.exit(0)

#!/usr/bin/env python3
"""
Gerenciador do scheduler daemon.

Comandos:
  - start_scheduler.py                # inicia em primeiro plano (com logs)
  - start_scheduler.py start --daemon # inicia em segundo plano
  - start_scheduler.py stop           # encerra instância em execução
  - start_scheduler.py reload --daemon# reinicia (stop + start)
  - start_scheduler.py status         # mostra PID/estado atual
"""

from __future__ import annotations
import logging
from src.logging_config import setup_scheduler_logging

import argparse
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

from src.scheduler_daemon import start_scheduler_daemon, stop_scheduler_daemon

BASE_DIR = Path(__file__).resolve().parent
PID_FILE = BASE_DIR / "state" / "scheduler.pid"
INTERNAL_FLAG = "--_internal_run"


def _write_pid(pid: int) -> None:
    PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    try:
        PID_FILE.write_text(str(pid), encoding="utf-8")
    except PermissionError as exc:
        print(f"[scheduler-daemon] ⚠️ Não consegui gravar PID em {PID_FILE}: {exc}")
    except OSError as exc:
        print(f"[scheduler-daemon] ⚠️ Erro ao registrar PID: {exc}")


def _read_pid() -> Optional[int]:
    if not PID_FILE.exists():
        return None
    try:
        return int(PID_FILE.read_text(encoding="utf-8").strip())
    except Exception:
        return None


def _cleanup_pid() -> None:
    try:
        PID_FILE.unlink()
    except FileNotFoundError:
        pass
    except PermissionError as exc:
        print(f"[scheduler-daemon] ⚠️ Sem permissão para remover {PID_FILE}: {exc}")
    except OSError as exc:
        print(f"[scheduler-daemon] ⚠️ Erro ao remover PID: {exc}")


def _is_process_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _wait_for_shutdown(pid: int, timeout: float = 20.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if not _is_process_alive(pid):
            return True
        time.sleep(0.5)
    return False


def _scheduler_loop() -> None:
    print("🔄 Iniciando scheduler daemon...")
    # Set DISPLAY for Chrome wrapper script
    os.environ.setdefault("DISPLAY", ":99")
    # Setup logging
    setup_scheduler_logging("logs/scheduler.log")
    scheduler_daemon = start_scheduler_daemon()

    current_pid = os.getpid()
    _write_pid(current_pid)

    print("✅ Scheduler daemon ativo! (PID {})".format(current_pid))
    print("📊 Monitorando contas TikTok a cada 60 segundos")
    print("💡 Use 'python start_scheduler.py stop' para encerrar")

    def _shutdown_handler(signum, _frame):
        signame = signal.Signals(signum).name if signum else "UNKNOWN"
        print(f"\n🛑 Sinal recebido ({signame}) — encerrando scheduler...")
        try:
            stop_scheduler_daemon()
        finally:
            _cleanup_pid()
        sys.exit(0)

    # Trata SIGTERM/SIGINT/SIGHUP para desligar com segurança
    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        signal.signal(sig, _shutdown_handler)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        _shutdown_handler(signal.SIGINT, None)


def cmd_start(daemon: bool) -> None:
    existing = _read_pid()
    if existing and _is_process_alive(existing):
        print(f"⚠️ Scheduler já está em execução (PID {existing}).")
        return

    # Limpa PID antigo
    _cleanup_pid()

    if daemon:
        print("🚀 Iniciando scheduler em segundo plano…")
        subprocess.Popen(
            [sys.executable, __file__, INTERNAL_FLAG],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=str(BASE_DIR),
        )
        time.sleep(1.5)
        pid = _read_pid()
        if pid and _is_process_alive(pid):
            print(f"✅ Scheduler em background ativo (PID {pid}).")
        else:
            print("❌ Falha ao iniciar scheduler em background. Verifique os logs.")
    else:
        _scheduler_loop()


def cmd_stop() -> None:
    pid = _read_pid()
    if not pid:
        print("ℹ️ Scheduler não está em execução.")
        return

    if not _is_process_alive(pid):
        print(f"ℹ️ PID {pid} não está mais ativo. Limpando PID.")
        _cleanup_pid()
        return

    print(f"🛑 Enviando SIGTERM para o scheduler (PID {pid})…")
    os.kill(pid, signal.SIGTERM)
    if _wait_for_shutdown(pid):
        print("✅ Scheduler encerrado com sucesso.")
    else:
        print("⚠️ Scheduler não respondeu. Verifique manualmente.")
    _cleanup_pid()


def cmd_reload(daemon: bool) -> None:
    pid = _read_pid()
    if pid and _is_process_alive(pid):
        print("🔁 Reiniciando scheduler…")
        os.kill(pid, signal.SIGTERM)
        if not _wait_for_shutdown(pid):
            print("⚠️ Scheduler antigo não encerrou. Abortando reload.")
            return
        _cleanup_pid()
        time.sleep(1)
    else:
        _cleanup_pid()
    cmd_start(daemon=daemon or True)


def cmd_status() -> None:
    pid = _read_pid()
    if pid and _is_process_alive(pid):
        print(f"✅ Scheduler em execução (PID {pid}).")
    else:
        print("⏹ Scheduler parado.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Gerencia o scheduler daemon.")
    parser.add_argument(
        "command",
        nargs="?",
        default="start",
        choices=["start", "stop", "reload", "status"],
        help="Comando: start/stop/reload/status",
    )
    parser.add_argument(
        "--daemon",
        action="store_true",
        help="Executa em segundo plano (apenas start/reload).",
    )
    parser.add_argument(
        INTERNAL_FLAG,
        action="store_true",
        dest="internal_run",
        help=argparse.SUPPRESS,
    )
    args = parser.parse_args()

    if args.internal_run:
        _scheduler_loop()
        return

    if args.command == "start":
        cmd_start(daemon=args.daemon)
    elif args.command == "stop":
        cmd_stop()
    elif args.command == "reload":
        cmd_reload(daemon=args.daemon)
    elif args.command == "status":
        cmd_status()


if __name__ == "__main__":
    main()

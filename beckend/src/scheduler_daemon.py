# src/scheduler_daemon.py - Gerenciador SIMULTÂNEO multi-conta para TikTokScheduler
# MODIFICADO PARA RODAR INSTÂNCIAS INDEPENDENTES: Cada conta ativa roda seu próprio scheduler simultaneamente
import os
import logging
import threading
import time
import traceback
from typing import Dict, Optional, List

try:
    from src import log_service
except ImportError:  # pragma: no cover
    log_service = None  # type: ignore

from src.database import SessionLocal
from src.repositories import TikTokAccountRepository
from src.scheduler import TikTokScheduler

DEFAULT_POLL_SECONDS = int(os.getenv("SCHEDULER_SYNC_INTERVAL", "60"))


def _log(message: str, level: str = "info", account_name: Optional[str] = None) -> None:
    """Dispara logs para arquivo via logging e para o serviço centralizado."""
    logger = logging.getLogger("scheduler_daemon")
    prefix = "[scheduler-daemon]"
    if account_name:
        prefix = f"{prefix}[{account_name}]"

    # Log via logging module para arquivo
    log_method = getattr(logger, level, logger.info)
    log_method(f"{prefix} {message}")

    # Removido print() para evitar duplicação no systemd log
    # O systemd já redireciona o output do logging module

    if log_service:
        log_service.add_log(
            message=message,
            level=level,
            account_name=account_name,
            module="scheduler_daemon",
        )


class SchedulerDaemon:
    """
    Monitora contas ativas no banco e roda MÚLTIPLOS SCHEDULERS SIMULTANEAMENTE.
    Cada conta ativa possui uma instância independente do scheduler rodando em paralelo.
    """

    def __init__(self, poll_interval: int = DEFAULT_POLL_SECONDS, visible: bool = False):
        self.poll_interval = max(10, poll_interval)
        self.visible = visible
        self._schedulers: Dict[str, TikTokScheduler] = {}
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> "SchedulerDaemon":
        with self._lock:
            if self._thread and self._thread.is_alive():
                _log("Daemon já está em execução")
                return self
            self._stop_event.clear()
            self._thread = threading.Thread(
                target=self._run,
                name="SchedulerDaemon",
                daemon=True,
            )
            self._thread.start()
            _log("Daemon iniciado")
        return self

    def stop(self) -> None:
        with self._lock:
            self._stop_event.set()
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=self.poll_interval + 5)
            self._thread = None
        self._stop_all_schedulers()
        _log("Daemon encerrado")

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._sync_accounts()
            except Exception as exc:  # pragma: no cover
                _log(f"Erro inesperado: {exc}", level="error")
                traceback.print_exc()
            finally:
                self._stop_event.wait(self.poll_interval)

    def _sync_accounts(self) -> None:
        """
        MODO SIMULTÂNEO:
        - Roda todos os schedulers simultaneamente, cada um em sua própria thread
        - Cada conta ativa possui uma instância independente do scheduler
        - Sincroniza a lista de schedulers ativos com as contas ativas no banco
        """
        active_accounts = self._fetch_active_accounts()
        if not active_accounts:
            _log("Nenhuma conta ativa encontrada")
            # Para todos os schedulers se não há contas
            with self._lock:
                for account_name in list(self._schedulers.keys()):
                    self._stop_scheduler(account_name)
            return

        account_names = {acc.account_name.strip() for acc in active_accounts if acc.account_name}
        if not account_names:
            return

        with self._lock:
            current_accounts = set(self._schedulers.keys())

            # Para schedulers de contas que foram desativadas
            for account_name in current_accounts - account_names:
                _log(f"⏹️  Parando scheduler '{account_name}' (conta desativada)", account_name=account_name)
                self._stop_scheduler(account_name)

            # Inicia schedulers para contas ativas que não estão rodando
            for account_name in account_names - current_accounts:
                _log(f"▶️  Iniciando scheduler '{account_name}'", account_name=account_name)
                self._start_scheduler(account_name)

            # Log do status atual
            if len(account_names) > 0:
                _log(f"✓ Rodando {len(account_names)} scheduler(s) simultaneamente: {', '.join(sorted(account_names))}")

    def _fetch_active_accounts(self):
        db = SessionLocal()
        try:
            return TikTokAccountRepository.list_all_active(db)
        except Exception as exc:
            _log(f"Falha ao listar contas ativas: {exc}", level="error")
            return []
        finally:
            db.close()

    def _start_scheduler(self, account_name: str) -> None:
        try:
            scheduler = TikTokScheduler(
                account_name=account_name,
                logger=lambda msg, acc=account_name: _log(msg, account_name=acc),
                visible=self.visible,
            )
            scheduler.initial_setup()
            scheduler.start()
            self._schedulers[account_name] = scheduler
            _log(f"Scheduler iniciado para '{account_name}'")
        except Exception as exc:
            _log(f"Erro ao iniciar scheduler '{account_name}': {exc}", level="error")
            traceback.print_exc()

    def _stop_scheduler(self, account_name: str) -> None:
        scheduler = self._schedulers.pop(account_name, None)
        if not scheduler:
            return
        try:
            scheduler.stop()
        except Exception as exc:
            _log(f"Erro durante stop() da conta '{account_name}': {exc}", level="error")
        finally:
            scheduler.running = False
            thread = getattr(scheduler, "scheduler_thread", None)
            if thread and thread.is_alive():
                thread.join(timeout=5)
            _log(f"Scheduler encerrado para '{account_name}'")

    def _stop_all_schedulers(self) -> None:
        for account_name in list(self._schedulers.keys()):
            self._stop_scheduler(account_name)


_daemon_instance: Optional[SchedulerDaemon] = None


def start_scheduler_daemon(
    poll_interval: int = DEFAULT_POLL_SECONDS,
    visible: bool = False,
) -> SchedulerDaemon:
    global _daemon_instance
    if _daemon_instance:
        _log("Reaproveitando daemon existente")
        return _daemon_instance
    daemon = SchedulerDaemon(poll_interval=poll_interval, visible=visible)
    _daemon_instance = daemon.start()
    return _daemon_instance


def stop_scheduler_daemon() -> None:
    global _daemon_instance
    if not _daemon_instance:
        _log("Daemon já está parado")
        return
    _daemon_instance.stop()
    _daemon_instance = None

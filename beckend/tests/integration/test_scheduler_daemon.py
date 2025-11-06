import threading
import types
from types import SimpleNamespace


def test_scheduler_daemon_starts_and_stops_accounts(monkeypatch):
    from src import scheduler_daemon as daemon_mod

    # Evita ruído de log em testes
    monkeypatch.setattr(daemon_mod, "_log", lambda *args, **kwargs: None)

    started_accounts = []
    stopped_accounts = []
    instantiated = {}

    class FakeScheduler:
        def __init__(self, account_name, logger=None, visible=False):
            self.account_name = account_name
            self.logger = logger
            self.visible = visible
            self.initialized = False
            self.started = False
            self.stopped = False
            self.running = True
            self.scheduler_thread = types.SimpleNamespace(is_alive=lambda: False)
            instantiated[account_name] = self

        def initial_setup(self):
            self.initialized = True

        def start(self):
            self.started = True
            started_accounts.append(self.account_name)

        def stop(self):
            self.stopped = True
            stopped_accounts.append(self.account_name)

    monkeypatch.setattr(daemon_mod, "TikTokScheduler", FakeScheduler)

    daemon = daemon_mod.SchedulerDaemon(poll_interval=5, visible=False)

    def set_accounts(accounts):
        monkeypatch.setattr(
            daemon,
            "_fetch_active_accounts",
            lambda accs=accounts: accs,
        )

    # Primeira sincronização: duas contas ativas
    set_accounts(
        [
            SimpleNamespace(account_name="alpha"),
            SimpleNamespace(account_name="beta"),
        ]
    )
    daemon._sync_accounts()

    assert set(daemon._schedulers.keys()) == {"alpha", "beta"}
    for name in ("alpha", "beta"):
        sched = instantiated[name]
        assert sched.initialized is True
        assert sched.started is True

    # Segunda sincronização: apenas uma conta permanece
    set_accounts([SimpleNamespace(account_name="beta")])
    daemon._sync_accounts()

    assert set(daemon._schedulers.keys()) == {"beta"}
    assert "alpha" in stopped_accounts
    assert instantiated["alpha"].stopped is True

    # Terceira sincronização: nenhuma conta ativa => encerra remanescente
    set_accounts([])
    daemon._sync_accounts()

    assert daemon._schedulers == {}
    assert "beta" in stopped_accounts
    assert instantiated["beta"].stopped is True


def test_scheduler_daemon_log_includes_log_service(monkeypatch, caplog):
    from src import scheduler_daemon as daemon_mod

    logged = []

    fake_log_service = types.SimpleNamespace(add_log=lambda **payload: logged.append(payload))
    monkeypatch.setattr(daemon_mod, "log_service", fake_log_service)

    with caplog.at_level("ERROR", logger="scheduler_daemon"):
        daemon_mod._log("test message", level="error", account_name="acc-1")

    assert any(record.levelname == "ERROR" and "test message" in record.message for record in caplog.records)
    assert logged[0]["message"] == "test message"
    assert logged[0]["account_name"] == "acc-1"


def test_scheduler_daemon_start_reuses_existing_instance(monkeypatch):
    from src import scheduler_daemon as daemon_mod

    class FakeDaemon:
        def __init__(self, poll_interval=0, visible=False):
            self.started = False
            self.stop_called = False

        def start(self):
            self.started = True
            return self

        def stop(self):
            self.stop_called = True

    monkeypatch.setattr(daemon_mod, "SchedulerDaemon", FakeDaemon)
    daemon_mod._daemon_instance = None

    first = daemon_mod.start_scheduler_daemon()
    assert isinstance(first, FakeDaemon)
    assert first.started is True

    second = daemon_mod.start_scheduler_daemon()
    assert second is first

    daemon_mod.stop_scheduler_daemon()
    assert first.stop_called is True
    assert daemon_mod._daemon_instance is None


def test_scheduler_daemon_handles_start_failure(monkeypatch):
    from src import scheduler_daemon as daemon_mod

    captured = []
    monkeypatch.setattr(daemon_mod, "_log", lambda msg, **kwargs: captured.append(msg))

    class BoomScheduler(Exception):
        pass

    class BadScheduler:
        def __init__(self, *args, **kwargs):
            raise BoomScheduler("failure")

    monkeypatch.setattr(daemon_mod, "TikTokScheduler", BadScheduler)

    daemon = daemon_mod.SchedulerDaemon()
    daemon._start_scheduler("danger")

    assert any("Erro ao iniciar scheduler 'danger'" in msg for msg in captured)


def test_scheduler_daemon_fetch_accounts_error(monkeypatch):
    from src import scheduler_daemon as daemon_mod

    captured = []
    monkeypatch.setattr(daemon_mod, "_log", lambda msg, **kwargs: captured.append(msg))

    def failing_list(db):
        raise RuntimeError("db down")

    monkeypatch.setattr(daemon_mod.TikTokAccountRepository, "list_all_active", failing_list)

    result = daemon_mod.SchedulerDaemon()._fetch_active_accounts()

    assert result == []
    assert any("Falha ao listar contas ativas" in msg for msg in captured)


def test_scheduler_daemon_stop_handles_thread_alive(monkeypatch):
    from src import scheduler_daemon as daemon_mod

    daemon = daemon_mod.SchedulerDaemon(poll_interval=1)
    daemon._thread = types.SimpleNamespace(is_alive=lambda: True, join=lambda timeout: None)

    stop_called = []

    def fake_stop_all():
        stop_called.append(True)

    monkeypatch.setattr(daemon, "_stop_all_schedulers", fake_stop_all)
    monkeypatch.setattr(daemon_mod, "_log", lambda *args, **kwargs: None)

    daemon.stop()

    assert stop_called, "stop should call _stop_all_schedulers"

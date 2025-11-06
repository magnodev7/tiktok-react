import threading
from types import SimpleNamespace
from typing import Dict
import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import src.scheduler_daemon as daemon_module


class DummySession:
    def close(self):
        pass


@pytest.fixture()
def fake_repo(monkeypatch):
    accounts = {"acc1", "acc2"}

    def list_all_active(db):
        return [SimpleNamespace(account_name=name) for name in accounts]

    monkeypatch.setattr(
        daemon_module.TikTokAccountRepository,
        "list_all_active",
        staticmethod(lambda db: list_all_active(db)),
        raising=False,
    )
    monkeypatch.setattr(daemon_module, "SessionLocal", lambda: DummySession(), raising=False)
    return accounts


@pytest.fixture()
def fake_scheduler_cls(monkeypatch):
    created: Dict[str, "FakeScheduler"] = {}

    class FakeScheduler:
        def __init__(self, account_name, logger=None, visible=False):
            self.account_name = account_name
            self.logger = logger
            self.visible = visible
            self.initialized = False
            self.started = False
            self.stopped = False
            self.running = True
            self.scheduler_thread = None
            created[account_name] = self

        def initial_setup(self):
            self.initialized = True

        def start(self):
            self.started = True

        def stop(self):
            self.stopped = True

    monkeypatch.setattr(daemon_module, "TikTokScheduler", FakeScheduler, raising=False)
    return created


def test_sync_accounts_starts_and_stops(monkeypatch, fake_repo, fake_scheduler_cls):
    daemon = daemon_module.SchedulerDaemon(poll_interval=1, visible=False)

    daemon._sync_accounts()
    assert set(daemon._schedulers.keys()) == fake_repo
    for name in fake_repo:
        sched = fake_scheduler_cls[name]
        assert sched.initialized and sched.started

    # Remove one account and re-sync; should stop the removed scheduler
    fake_repo.remove("acc1")
    daemon._sync_accounts()
    assert set(daemon._schedulers.keys()) == fake_repo
    assert fake_scheduler_cls["acc1"].stopped

    # No active accounts should stop everything
    fake_repo.clear()
    daemon._sync_accounts()
    assert daemon._schedulers == {}


def test_daemon_start_and_stop(monkeypatch, fake_repo, fake_scheduler_cls):
    def dummy_run(self):
        self._stop_event.set()

    monkeypatch.setattr(daemon_module.SchedulerDaemon, "_run", dummy_run, raising=False)
    stop_calls = {"count": 0}

    def fake_stop_all(self):
        stop_calls["count"] += 1

    monkeypatch.setattr(daemon_module.SchedulerDaemon, "_stop_all_schedulers", fake_stop_all, raising=False)

    daemon = daemon_module.SchedulerDaemon(poll_interval=1)
    daemon.start()
    assert daemon._thread is not None

    daemon.stop()
    assert daemon._thread is None
    assert stop_calls["count"] == 1


def test_fetch_active_accounts_handles_errors(monkeypatch):
    monkeypatch.setattr(
        daemon_module.TikTokAccountRepository,
        "list_all_active",
        staticmethod(lambda db: (_ for _ in ()).throw(RuntimeError("db down"))),
        raising=False,
    )
    monkeypatch.setattr(daemon_module, "SessionLocal", lambda: DummySession(), raising=False)

    daemon = daemon_module.SchedulerDaemon()
    accounts = daemon._fetch_active_accounts()
    assert accounts == []

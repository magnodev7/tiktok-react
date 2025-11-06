import sys
from pathlib import Path
import importlib
import pytest


@pytest.fixture(autouse=True)
def _add_backend_src_to_path():
    """Expose beckend/src as top-level imports when running pytest."""
    backend_root = Path(__file__).resolve().parents[1]
    backend_str = str(backend_root)
    src_str = str(backend_root / "src")
    for entry in (backend_str, src_str):
        if entry not in sys.path:
            sys.path.insert(0, entry)
    yield


@pytest.fixture
def scheduler_module(tmp_path, monkeypatch):
    """
    Provide the scheduler module with isolated state/log files under a temp dir.
    """
    scheduler = importlib.import_module("src.scheduler")

    state_dir = tmp_path / "state"
    state_dir.mkdir()

    monkeypatch.setattr(scheduler, "STATE_DIR", state_dir, raising=False)
    monkeypatch.setattr(scheduler, "SCHEDULES_JSON", state_dir / "schedules.json", raising=False)
    monkeypatch.setattr(scheduler, "LOGS_JSON", state_dir / "logs.json", raising=False)

    return scheduler

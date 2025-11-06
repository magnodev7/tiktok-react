import json
import datetime as dt
from pathlib import Path
from typing import Callable, List, Tuple
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import pytest
from zoneinfo import ZoneInfo

from src import scheduler
from src import config
from src import paths


class FakeClock:
    def __init__(self, start: dt.datetime):
        self._current = start

    def now(self) -> dt.datetime:
        return self._current

    def set(self, new_value: dt.datetime) -> None:
        if new_value < self._current:
            raise ValueError("FakeClock cannot go backwards")
        self._current = new_value

    def advance(self, delta: dt.timedelta | float | int) -> None:
        if isinstance(delta, dt.timedelta):
            self._current += delta
        else:
            self._current += dt.timedelta(seconds=float(delta))


class SimulatedScheduler(scheduler.TikTokScheduler):
    def __init__(self, account_name: str, clock: FakeClock, logger: Callable[[str], None]):
        super().__init__(account_name, logger=logger, visible=False)
        self._clock = clock
        self.posted_order: List[Tuple[dt.datetime, str]] = []
        self._force_fail_once = False

    def fail_next_login(self) -> None:
        self._force_fail_once = True

    def _ensure_logged(self) -> bool:  # type: ignore[override]
        if self._force_fail_once:
            self._force_fail_once = False
            self._last_cookie_failure_time = self._clock.now()
            self.log("🧪 Simulando falha de cookies")
            return False
        self.log("🧪 Sessão simulada OK")
        return True

    def _post_one(self, path: str) -> bool:  # type: ignore[override]
        self.posted_order.append((self._clock.now(), Path(path).name))
        return True

    def _finalize_success(self, vpath: str):  # type: ignore[override]
        p = Path(vpath)
        meta_path = p.with_suffix(".json")
        meta = scheduler._read_json(meta_path) or {}
        meta["status"] = "posted"
        meta["posted_at"] = self._clock.now().astimezone(dt.timezone.utc).isoformat()
        scheduler._write_json_atomic(meta_path, meta)
        if p.exists():
            p.unlink()


@pytest.fixture()
def scheduler_environment(monkeypatch, tmp_path):
    profiles = tmp_path / "profiles"
    videos = tmp_path / "videos"
    posted = tmp_path / "posted"
    state = tmp_path / "state"
    for directory in (profiles, videos, posted, state):
        directory.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(config, "BASE_USER_DATA_DIR", str(profiles), raising=False)
    monkeypatch.setattr(config, "BASE_VIDEO_DIR", str(videos), raising=False)
    monkeypatch.setattr(config, "BASE_POSTED_DIR", str(posted), raising=False)

    monkeypatch.setattr(paths, "BASE_USER_DATA_DIR", str(profiles), raising=False)
    monkeypatch.setattr(paths, "BASE_VIDEO_DIR", str(videos), raising=False)
    monkeypatch.setattr(paths, "BASE_POSTED_DIR", str(posted), raising=False)

    monkeypatch.setattr(scheduler, "STATE_DIR", state, raising=False)
    monkeypatch.setattr(scheduler, "SCHEDULES_JSON", state / "schedules.json", raising=False)
    monkeypatch.setattr(scheduler, "LOGS_JSON", state / "logs.json", raising=False)

    schedules = ["08:00", "10:00", "12:00", "14:00", "16:00", "18:00", "20:00", "22:00"]
    scheduler.SCHEDULES_JSON.write_text(json.dumps({"schedules": schedules}), encoding="utf-8")
    monkeypatch.setattr(scheduler, "SCHEDULES", schedules, raising=False)
    monkeypatch.setattr(config, "SCHEDULES", schedules, raising=False)

    return {
        "profiles": profiles,
        "videos": videos,
        "posted": posted,
        "state": state,
        "schedules": schedules,
    }


def _seed_videos(base_dir: Path, schedules: List[str], start_date: dt.datetime, days: int = 30):
    utc = dt.timezone.utc
    uploaded_reference = start_date - dt.timedelta(hours=2)
    slot_map: List[Tuple[str, dt.datetime]] = []
    for day in range(days):
        for slot_idx, hhmm in enumerate(schedules):
            name = f"video_{day:02d}_{hhmm.replace(':', '')}.mp4"
            video_path = base_dir / name
            video_path.write_bytes(b"00")
            uploaded_at = (uploaded_reference + dt.timedelta(minutes=day * 5 + slot_idx)).astimezone(utc)
            meta = {
                "status": "pending",
                "uploaded_at": uploaded_at.isoformat(),
            }
            video_path.with_suffix(".json").write_text(json.dumps(meta), encoding="utf-8")
            slot_map.append((str(video_path), hhmm))
    return slot_map


def test_scheduler_handles_30_days_with_cookie_failure(monkeypatch, scheduler_environment):
    tz = ZoneInfo("America/Sao_Paulo")
    start = dt.datetime(2025, 1, 1, 7, 55, tzinfo=tz)
    clock = FakeClock(start)
    monkeypatch.setattr(scheduler, "_now_app", clock.now, raising=False)
    monkeypatch.setattr(scheduler, "_nowstamp", lambda: clock.now().strftime("%Y%m%d_%H%M%S"), raising=False)

    account = "test_account"
    video_dir = scheduler_environment["videos"] / account
    video_dir.mkdir(parents=True, exist_ok=True)

    slot_entries = _seed_videos(
        video_dir,
        scheduler_environment["schedules"],
        start_date=start,
        days=30,
    )

    logs: List[str] = []

    def logger(msg: str):
        logs.append(msg)

    sim = SimulatedScheduler(account, clock=clock, logger=logger)
    sim.scheduler_active = True
    candidates = sim._assign_dynamic_slots()
    assert len(candidates) == len(slot_entries)

    slot_by_path = {Path(dv.path).name: dv.scheduled_at for dv in candidates}
    ordered_slots = sorted(slot_by_path.items(), key=lambda item: item[1])
    assert len(ordered_slots) == len(slot_entries)

    target_fail_slot = None
    for name, when in ordered_slots:
        if when.date() == start.date() and when.strftime("%H:%M") == "16:00":
            target_fail_slot = (name, when)
            break
    assert target_fail_slot is not None

    # Process every scheduled slot sequentially
    for name, scheduled_at in ordered_slots:
        clock.set(scheduled_at + dt.timedelta(seconds=10))
        if name == target_fail_slot[0]:
            sim.fail_next_login()
            sim.scheduled_posting()
            meta_after_fail = scheduler._read_json((video_dir / name).with_suffix(".json"))
            assert meta_after_fail and meta_after_fail.get("status") != "posted"
            clock.advance(dt.timedelta(minutes=5))
            sim.scheduled_posting()
        else:
            sim.scheduled_posting()

    assert len(sim.posted_order) == len(ordered_slots)

    # Posted order must follow chronological order, even around the simulated failure
    posted_names = [name for _, name in sim.posted_order]
    expected_order = [name for name, _ in ordered_slots]
    assert posted_names == expected_order

    # Every metadata file should be marked as posted
    for name, scheduled_at in ordered_slots:
        meta = scheduler._read_json((video_dir / name).with_suffix(".json"))
        assert meta is not None
        assert meta.get("status") == "posted"
        posted_at = meta.get("posted_at")
        assert posted_at is not None

    # Logs should include the simulated failure hint
    assert any("Simulando falha de cookies" in entry for entry in logs)


def test_scheduler_recovers_after_restart(monkeypatch, scheduler_environment):
    tz = ZoneInfo("America/Sao_Paulo")
    start = dt.datetime(2025, 1, 1, 7, 55, tzinfo=tz)
    clock = FakeClock(start)
    monkeypatch.setattr(scheduler, "_now_app", clock.now, raising=False)
    monkeypatch.setattr(scheduler, "_nowstamp", lambda: clock.now().strftime("%Y%m%d_%H%M%S"), raising=False)

    account = "restart_account"
    video_dir = scheduler_environment["videos"] / account
    video_dir.mkdir(parents=True, exist_ok=True)
    _seed_videos(video_dir, scheduler_environment["schedules"], start_date=start, days=2)

    logs_a: List[str] = []
    sim_a = SimulatedScheduler(account, clock=clock, logger=logs_a.append)
    sim_a.scheduler_active = True

    first_day_slots = sorted({dv.scheduled_at for dv in sim_a._assign_dynamic_slots() if dv.scheduled_at.date() == start.date()})
    assert first_day_slots

    # Process half of the first day
    midpoint = len(first_day_slots) // 2 or 1
    for slot in first_day_slots[:midpoint]:
        clock.set(slot + dt.timedelta(seconds=5))
        sim_a.scheduled_posting()

    posted_before_restart = len(sim_a.posted_order)
    assert posted_before_restart == midpoint

    # Simulate service restart by creating a new scheduler instance
    logs_b: List[str] = []
    sim_b = SimulatedScheduler(account, clock=clock, logger=logs_b.append)
    sim_b.scheduler_active = True

    remaining_slots = [
        dv.scheduled_at
        for dv in sim_b._assign_dynamic_slots()
        if dv.scheduled_at >= clock.now()
    ]
    assert remaining_slots

    for slot in remaining_slots:
        clock.set(slot + dt.timedelta(seconds=5))
        sim_b.scheduled_posting()

    total_posted = posted_before_restart + len(sim_b.posted_order)
    unique_posted_after_restart = {name for _, name in sim_b.posted_order}
    assert total_posted == posted_before_restart + len(unique_posted_after_restart)

    # All remaining metadata must be marked as posted
    for meta_path in video_dir.glob("*.json"):
        meta = scheduler._read_json(meta_path)
        assert meta is not None
        assert meta.get("status") == "posted"


def test_scheduler_reschedules_leftovers_with_burst_limit(monkeypatch, scheduler_environment):
    tz = ZoneInfo("America/Sao_Paulo")
    start = dt.datetime(2025, 1, 1, 7, 55, tzinfo=tz)
    clock = FakeClock(start)
    monkeypatch.setattr(scheduler, "_now_app", clock.now, raising=False)
    monkeypatch.setattr(scheduler, "_nowstamp", lambda: clock.now().strftime("%Y%m%d_%H%M%S"), raising=False)

    monkeypatch.setattr(scheduler, "MAX_POSTS_PER_TICK", 1, raising=False)

    account = "burst_account"
    video_dir = scheduler_environment["videos"] / account
    video_dir.mkdir(parents=True, exist_ok=True)
    _seed_videos(video_dir, scheduler_environment["schedules"], start_date=start, days=1)

    logs: List[str] = []
    sim = SimulatedScheduler(account, clock=clock, logger=logs.append)
    sim.scheduler_active = True

    candidates = sim._assign_dynamic_slots()
    assert candidates
    original_slots = {
        Path(dv.path).with_suffix(".json").name: dv.scheduled_at
        for dv in candidates
    }

    # Jump to end of day so all slots are simultaneously due
    clock.set(dt.datetime(2025, 1, 1, 23, 0, tzinfo=tz))
    sim.scheduled_posting()

    # Only one video should have been posted initially due to MAX_POSTS_PER_TICK=1
    assert len(sim.posted_order) == 1

    # Remaining videos must have been rescheduled to near-future timestamps
    rescheduled_metas = []
    for json_meta in video_dir.glob("*.json"):
        if json_meta.name.endswith(".meta.json"):
            continue
        meta = scheduler._read_json(json_meta) or {}
        if meta.get("status") != "posted":
            new_time = scheduler._parse_iso_maybe(meta.get("scheduled_at"))
            original_time = original_slots.get(json_meta.name)
            rescheduled_metas.append((json_meta.name, original_time, new_time))
    assert rescheduled_metas
    for name, original_time, new_time in rescheduled_metas:
        assert new_time is not None, f"{name} should have a new scheduled_at"
        assert original_time is not None
        assert new_time > original_time, f"{name} should move forward in time"

    # Advance time to process rescheduled videos
    for _ in range(len(rescheduled_metas) + 1):
        clock.advance(dt.timedelta(minutes=1))
        sim.scheduled_posting()

    remaining_pending = [
        json_meta
        for json_meta in video_dir.glob("*.json")
        if not json_meta.name.endswith(".meta.json")
        and (scheduler._read_json(json_meta) or {}).get("status") != "posted"
    ]
    assert not remaining_pending, "All videos should be posted after processing leftovers"

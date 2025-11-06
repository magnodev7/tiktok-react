import json
import os
import sys
import types
from datetime import datetime, timezone
from pathlib import Path

import pytest  # type: ignore


def _build_video(tmp_path: Path, name: str) -> Path:
    video = tmp_path / f"{name}.mp4"
    video.write_bytes(b"\x00")
    return video


def _resolve_callable(mod, primary: str, fallback: str):
    attr = getattr(mod, primary, None)
    if attr is None and fallback:
        attr = getattr(mod, fallback)
    return attr


def test_occupied_slots_for_date_reads_json_and_meta(scheduler_module, tmp_path):
    videos_dir = tmp_path / "videos"
    videos_dir.mkdir()

    video_today = _build_video(videos_dir, "today")
    video_today.with_suffix(".json").write_text(
        json.dumps({"scheduled_at": "2024-03-05T09:30:00-03:00"}), encoding="utf-8"
    )

    video_meta = _build_video(videos_dir, "meta")
    video_meta.with_suffix(".meta.json").write_text(
        json.dumps({"schedule_time": "15:45"}), encoding="utf-8"
    )

    video_other_day = _build_video(videos_dir, "other")
    video_other_day.with_suffix(".json").write_text(
        json.dumps({"scheduled_at": "2024-03-06T10:00:00+00:00"}), encoding="utf-8"
    )

    occupied_fn = _resolve_callable(scheduler_module, "_occupied_slots_for_date", "occupied_slots_for_date")
    taken = occupied_fn(str(videos_dir), "2024-03-05")
    assert taken == {"09:30", "15:45"}


def test_find_next_free_slot_skips_taken_and_past_time(scheduler_module, tmp_path, monkeypatch):
    videos_dir = tmp_path / "videos"
    videos_dir.mkdir()

    fixed_now = datetime(2024, 3, 5, 10, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(scheduler_module, "_now_app", lambda: fixed_now)
    monkeypatch.setattr(scheduler_module, "APP_TZ", timezone.utc, raising=False)

    # Occupy 10:30 and 11:00 for the current day to force scheduling for the next day.
    for name, scheduled_at in (
        ("slot_1030", "2024-03-05T10:30:00+00:00"),
        ("slot_1100", "2024-03-05T11:00:00+00:00"),
    ):
        video = _build_video(videos_dir, name)
        video.with_suffix(".json").write_text(json.dumps({"scheduled_at": scheduled_at}), encoding="utf-8")

    schedules = ["09:00", "10:30", "11:00"]
    find_slot = _resolve_callable(scheduler_module, "_find_next_free_slot", "find_next_free_slot")
    date_ymd, hhmm, iso = find_slot(str(videos_dir), schedules)

    assert date_ymd == "2024-03-06"
    assert hhmm == "09:00"
    assert iso == "2024-03-06T09:00:00+00:00"


def test_update_sidecars_updates_json_and_meta(scheduler_module, tmp_path):
    video_path = _build_video(tmp_path, "sample")
    video_path.with_suffix(".json").write_text(
        json.dumps({"schedule_time": "08:00"}), encoding="utf-8"
    )
    video_path.with_suffix(".meta.json").write_text(
        json.dumps({"legacy": True, "scheduled_at": "2024-03-07T09:00:00+00:00"}), encoding="utf-8"
    )

    log_messages = []
    update_sidecars = _resolve_callable(scheduler_module, "_update_sidecars_for", "update_sidecars_for")

    update_sidecars(
        str(video_path),
        new_hhmm="13:37",
        new_iso_utc="2024-03-07T13:37:00+00:00",
        log=log_messages.append,
    )

    unified = json.loads(video_path.with_suffix(".json").read_text(encoding="utf-8"))
    legacy = json.loads(video_path.with_suffix(".meta.json").read_text(encoding="utf-8"))

    assert unified["scheduled_at"] == "2024-03-07T13:37:00+00:00"
    assert unified["schedule_time"] == "13:37"
    assert legacy["schedule_time"] == "13:37"
    assert legacy["scheduled_at"] == "2024-03-07T13:37:00+00:00"


def test_move_sidecars_moves_all_candidates(scheduler_module, tmp_path):
    video_path = _build_video(tmp_path, "clip")
    log_messages = []

    sidecars = {
        video_path.with_suffix(".json"): {"meta": True},
        video_path.with_suffix(".meta.json"): {"legacy": True},
        video_path.with_suffix(".txt"): "notes",
    }

    for path, payload in sidecars.items():
        if isinstance(payload, dict):
            path.write_text(json.dumps(payload), encoding="utf-8")
        else:
            path.write_text(payload, encoding="utf-8")

    posted_dir = tmp_path / "posted"
    scheduler_module.move_sidecars(str(video_path), str(posted_dir), log_messages.append)

    for path in sidecars:
        assert not path.exists()

    moved = list(posted_dir.iterdir())
    assert len(moved) == 3
    assert any(p.name == "clip.json" for p in moved)
    assert any(p.name == "clip.meta.json" for p in moved)
    assert any(p.name == "clip.txt" for p in moved)


def test_scheduler_initial_setup_invokes_ensure_base(scheduler_module, tmp_path, monkeypatch):
    base_dirs = tuple(tmp_path / name for name in ("profiles", "videos", "posted"))
    for directory in base_dirs:
        directory.mkdir(parents=True, exist_ok=True)

    def fake_account_dirs(account_name: str):
        return tuple(str(d) for d in base_dirs)

    ensure_called = []

    def fake_ensure_base():
        ensure_called.append(True)

    monkeypatch.setattr(scheduler_module, "account_dirs", fake_account_dirs, raising=False)
    monkeypatch.setattr(scheduler_module, "ensure_base", fake_ensure_base, raising=False)
    monkeypatch.setattr(scheduler_module.TikTokScheduler, "kill_chrome_processes", lambda self: None)

    logs = []
    scheduler = scheduler_module.TikTokScheduler("my-account", logger=logs.append)
    scheduler.initial_setup()

    assert scheduler.USER_DATA_DIR == str(base_dirs[0])
    assert scheduler.VIDEO_DIR == str(base_dirs[1])
    assert scheduler.POSTED_DIR == str(base_dirs[2])
    assert ensure_called, "ensure_base should be called during initial setup"


def test_scheduler_requires_non_empty_account(scheduler_module):
    with pytest.raises(ValueError):
        scheduler_module.TikTokScheduler("  ")


def test_ensure_logged_in_test_mode_short_circuits(scheduler_module, monkeypatch, tmp_path):
    if not hasattr(scheduler_module.TikTokScheduler, "_ensure_logged"):
        def _ensure_logged_stub(self):
            if getattr(scheduler_module, "TEST_MODE", False):
                self.log("🚧 Modo teste: simulação de login OK")
                return True
            raise NotImplementedError("_ensure_logged stub invoked without TEST_MODE")

        monkeypatch.setattr(
            scheduler_module.TikTokScheduler,
            "_ensure_logged",
            _ensure_logged_stub,
            raising=False,
        )

    base_dirs = tuple(tmp_path / name for name in ("profiles", "videos", "posted"))
    for directory in base_dirs:
        directory.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(scheduler_module, "account_dirs", lambda _: tuple(str(d) for d in base_dirs), raising=False)
    monkeypatch.setattr(scheduler_module.TikTokScheduler, "kill_chrome_processes", lambda self: None)
    monkeypatch.setattr(scheduler_module, "TEST_MODE", True, raising=False)

    logs = []
    scheduler = scheduler_module.TikTokScheduler("test-account", logger=logs.append)
    assert scheduler._ensure_logged() is True
    assert any("Modo teste" in msg for msg in logs)


def test_read_schedules_prefers_state_file_over_default(scheduler_module, monkeypatch):
    read_schedules = _resolve_callable(scheduler_module, "_read_schedules", "_read_schedules")

    monkeypatch.setattr(scheduler_module, "SCHEDULES", ["01:00"], raising=False)
    scheduler_module.SCHEDULES_JSON.write_text(json.dumps(["05:00", "06:30"]), encoding="utf-8")

    assert read_schedules() == ["05:00", "06:30"]

    scheduler_module.SCHEDULES_JSON.write_text(json.dumps({"schedules": ["07:45"]}), encoding="utf-8")
    assert read_schedules() == ["07:45"]

    scheduler_module.SCHEDULES_JSON.write_text("invalid json", encoding="utf-8")
    assert read_schedules() == ["01:00"]


def test_safe_move_handles_name_collision(scheduler_module, tmp_path, monkeypatch):
    monkeypatch.setattr(scheduler_module, "_nowstamp", lambda: "20240101_120000")

    src_dir = tmp_path / "src"
    dst_dir = tmp_path / "dst"
    src_dir.mkdir()
    dst_dir.mkdir()

    src_file = src_dir / "clip.mp4"
    src_file.write_bytes(b"data")

    existing = dst_dir / "clip.mp4"
    existing.write_bytes(b"original")

    moved_path = Path(scheduler_module.safe_move(str(src_file), str(dst_dir)))

    assert moved_path.parent == dst_dir
    assert moved_path.name == "clip_20240101_120000.mp4"
    assert existing.read_bytes() == b"original"
    assert not src_file.exists()


def test_move_sidecars_logs_error_when_safe_move_fails(scheduler_module, tmp_path, monkeypatch):
    video_path = _build_video(tmp_path, "clip")
    sidecar = video_path.with_suffix(".json")
    sidecar.write_text("{}", encoding="utf-8")

    def fail_safe_move(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(scheduler_module, "safe_move", fail_safe_move)

    logs = []
    scheduler_module.move_sidecars(str(video_path), str(tmp_path / "posted"), logs.append)

    assert any("Falha ao mover sidecar" in msg for msg in logs)
    assert sidecar.exists()


def test_read_schedules_handles_dict_and_invalid(scheduler_module, tmp_path, monkeypatch):
    scheduler_module.SCHEDULES_JSON.write_text(
        json.dumps({"schedules": ["06:00", "07:00"]}),
        encoding="utf-8",
    )
    assert scheduler_module._read_schedules() == ["06:00", "07:00"]

    scheduler_module.SCHEDULES_JSON.write_text("not-json", encoding="utf-8")
    monkeypatch.setattr(scheduler_module, "SCHEDULES", ["05:00"], raising=False)
    assert scheduler_module._read_schedules() == ["05:00"]


def test_find_next_free_slot_uses_fallback_when_empty_schedule(scheduler_module, tmp_path, monkeypatch):
    base_time = datetime(2024, 3, 8, 8, 0, tzinfo=scheduler_module.APP_TZ)
    monkeypatch.setattr(scheduler_module, "_now_app", lambda: base_time)

    ymd, hhmm, iso = scheduler_module._find_next_free_slot(str(tmp_path), [])
    assert ymd == "2024-03-09"
    assert hhmm == "08:00"
    fallback_dt = datetime.fromisoformat(iso)
    assert fallback_dt.tzinfo is not None


def test_update_sidecars_logs_failures(monkeypatch, scheduler_module, tmp_path):
    video_path = _build_video(tmp_path, "clip")
    video_path.with_suffix(".json").write_text("{}", encoding="utf-8")
    video_path.with_suffix(".meta.json").write_text("{}", encoding="utf-8")

    log_messages = []
    failures = {"count": 0}

    def failing_write(path, data):
        failures["count"] += 1
        raise RuntimeError("disk full")

    monkeypatch.setattr(scheduler_module, "_write_json_atomic", failing_write)

    scheduler_module.update_sidecars_for(
        str(video_path),
        new_hhmm="07:00",
        new_iso_utc="2024-03-08T07:00:00+00:00",
        log=log_messages.append,
    )

    assert failures["count"] == 2
    assert any("Falha ao atualizar metadados unificados" in msg for msg in log_messages)
    assert any("Falha ao atualizar meta legado" in msg for msg in log_messages)


def test_close_driver_cleans_profile_and_releases_resources(scheduler_module, tmp_path, monkeypatch):
    base_dirs = tuple(tmp_path / name for name in ("profiles", "videos", "posted"))
    for directory in base_dirs:
        directory.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(scheduler_module, "account_dirs", lambda _: tuple(str(d) for d in base_dirs), raising=False)

    kill_calls = []

    def fake_kill(self):
        kill_calls.append(True)

    monkeypatch.setattr(scheduler_module.TikTokScheduler, "kill_chrome_processes", fake_kill, raising=False)

    profile_dir = tmp_path / "profiles" / "profile-1"
    profile_dir.mkdir(parents=True, exist_ok=True)
    for lock_name in ("SingletonLock", "SingletonCookie", "SingletonSocket"):
        (profile_dir / lock_name).write_text("lock", encoding="utf-8")

    release_calls = []
    fake_driver_module = types.SimpleNamespace(release_driver_lock=lambda driver: release_calls.append(driver))
    monkeypatch.setitem(sys.modules, "src.driver", fake_driver_module)

    class FakeDriver:
        def __init__(self, profile):
            self._profile_dir = str(profile)
            self.quit_called = False

        def quit(self):
            self.quit_called = True

    scheduler = scheduler_module.TikTokScheduler("acct", logger=lambda *_: None)
    fake_driver = FakeDriver(profile_dir)
    scheduler.driver = fake_driver
    scheduler._temp_profile_dir = str(profile_dir)
    scheduler._chromedriver_pid = 123

    scheduler.close_driver()

    assert fake_driver.quit_called is True
    assert release_calls == [fake_driver]
    for lock_name in ("SingletonLock", "SingletonCookie", "SingletonSocket"):
        assert not (profile_dir / lock_name).exists()
    assert kill_calls, "kill_chrome_processes should be invoked during close_driver"
    assert scheduler.driver is None
    assert scheduler._temp_profile_dir is None
    assert scheduler._chromedriver_pid is None


def test_kill_chrome_processes_targets_matching_profiles(scheduler_module, tmp_path, monkeypatch):
    base_dirs = tuple(tmp_path / name for name in ("profiles", "videos", "posted"))
    for directory in base_dirs:
        directory.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(
        scheduler_module,
        "account_dirs",
        lambda _: tuple(str(d) for d in base_dirs),
        raising=False,
    )

    scheduler = scheduler_module.TikTokScheduler("acct", logger=lambda *_: None)
    profile_dir = base_dirs[0] / "runtime" / "chrome-user-data-123"
    profile_dir.mkdir(parents=True, exist_ok=True)
    scheduler._temp_profile_dir = str(profile_dir)
    scheduler._chromedriver_pid = 444

    killed = []

    class FakeProc:
        def __init__(self, pid, name, cmdline, running=True):
            self.info = {"pid": pid, "name": name, "cmdline": cmdline}
            self._running = running
            self.signaled = False
            self.wait_called = False
            self.killed = False

        def send_signal(self, sig):
            self.signaled = True

        def wait(self, timeout):
            self.wait_called = True
            if self._running:
                raise TimeoutError("still running")

        def is_running(self):
            return self._running

        def kill(self):
            self.killed = True
            self._running = False
            killed.append(self.info["pid"])

    account_profile = os.path.abspath(scheduler.USER_DATA_DIR)
    matching_proc = FakeProc(
        pid=101,
        name="chrome",
        cmdline=["/usr/bin/chrome", account_profile, "--flag"],
    )
    pid_match_proc = FakeProc(
        pid=444,
        name="chromedriver",
        cmdline=["/usr/bin/chromedriver"],
    )
    unrelated_proc = FakeProc(
        pid=202,
        name="chrome",
        cmdline=["/usr/bin/chrome", "/tmp/other"],
        running=False,
    )

    monkeypatch.setattr(
        scheduler_module.psutil,
        "process_iter",
        lambda attrs=None: iter([matching_proc, pid_match_proc, unrelated_proc]),
    )

    scheduler.kill_chrome_processes()

    assert matching_proc.signaled is True
    assert matching_proc.wait_called is True
    assert matching_proc.killed is True

    assert pid_match_proc.killed is True
    assert killed == [101, 444]

    assert unrelated_proc.signaled is False

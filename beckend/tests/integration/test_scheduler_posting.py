import json
import os
import sys
import threading
import types
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


def _iso(dt):
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


@pytest.fixture
def scheduler_instance(tmp_path, monkeypatch, scheduler_module):
    base_dirs = tuple(tmp_path / name for name in ("profiles", "videos", "posted"))
    for directory in base_dirs:
        directory.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(
        scheduler_module,
        "account_dirs",
        lambda _: tuple(str(d) for d in base_dirs),
        raising=False,
    )
    monkeypatch.setattr(
        scheduler_module.TikTokScheduler,
        "kill_chrome_processes",
        lambda self: None,
        raising=False,
    )

    logs = []
    scheduler = scheduler_module.TikTokScheduler("acc", logger=logs.append, visible=False)
    scheduler.initial_setup()
    scheduler.scheduler_active = True
    scheduler._logs = logs  # debugging aid
    return scheduler


def _write_video(video_dir: Path, name: str, scheduled: datetime, uploaded: datetime):
    video_path = video_dir / f"{name}.mp4"
    video_path.write_bytes(b"\x00")
    meta = {
        "uploaded_at": _iso(uploaded),
        "scheduled_at": _iso(scheduled),
        "schedule_time": scheduled.strftime("%H:%M"),
        "status": None,
    }
    video_path.with_suffix(".json").write_text(json.dumps(meta), encoding="utf-8")
    return video_path


def test_scheduled_posting_respects_burst_limit_and_reschedules(
    scheduler_instance, scheduler_module, tmp_path, monkeypatch
):
    base_time = datetime(2024, 3, 5, 10, 0, tzinfo=scheduler_module.APP_TZ)
    current_time = {"value": base_time}
    monkeypatch.setattr(scheduler_module, "_now_app", lambda: current_time["value"])
    monkeypatch.setattr(scheduler_module, "MAX_POSTS_PER_TICK", 1, raising=False)
    monkeypatch.setattr(scheduler_module, "DELETE_AFTER_POST", True, raising=False)
    monkeypatch.setattr(scheduler_module, "BURST_RESCHEDULE_GAP_SECONDS", 30.0, raising=False)
    monkeypatch.setattr(scheduler_module, "BURST_RESCHEDULE_WINDOW_SECONDS", 60.0, raising=False)

    video_dir = Path(scheduler_instance.VIDEO_DIR)
    uploaded0 = base_time - timedelta(minutes=2)
    uploaded1 = base_time - timedelta(minutes=1)

    v1 = _write_video(video_dir, "vid1", scheduled=base_time, uploaded=uploaded0)
    v2 = _write_video(video_dir, "vid2", scheduled=base_time, uploaded=uploaded1)
    future_slot = base_time + timedelta(hours=1)
    v3 = _write_video(video_dir, "vid3", scheduled=future_slot, uploaded=future_slot - timedelta(minutes=5))

    post_calls = []

    def fake_post(self, path):
        post_calls.append(Path(path).name)
        return True

    monkeypatch.setattr(scheduler_module.TikTokScheduler, "_post_one", fake_post, raising=False)
    monkeypatch.setattr(scheduler_module.TikTokScheduler, "_ensure_logged", lambda self: True, raising=False)

    scheduler_instance.scheduled_posting()

    assert post_calls == ["vid1.mp4"]

    # vid2 should remain and be rescheduled for a future slot
    meta_vid2 = json.loads(v2.with_suffix(".json").read_text(encoding="utf-8"))
    rescheduled = scheduler_module._parse_iso_maybe(meta_vid2["scheduled_at"])
    assert rescheduled is not None
    assert rescheduled > current_time["value"]

    # Advance time beyond rescheduled slot and run again
    current_time["value"] = rescheduled + timedelta(seconds=5)
    scheduler_instance.scheduled_posting()
    assert post_calls == ["vid1.mp4", "vid2.mp4"]

    # vid3 not yet due
    assert not post_calls or post_calls[-1] != "vid3.mp4"

    # Advance to future slot and run again to confirm third video posts once
    future_due = future_slot + timedelta(minutes=5)
    current_time["value"] = future_due
    scheduler_instance.scheduled_posting()
    assert post_calls == ["vid1.mp4", "vid2.mp4", "vid3.mp4"]

    # Second run at same time should not repost already posted videos
    scheduler_instance.scheduled_posting()
    assert post_calls == ["vid1.mp4", "vid2.mp4", "vid3.mp4"]


def test_scheduled_posting_skips_future_until_due(scheduler_instance, scheduler_module, monkeypatch):
    base_time = datetime(2024, 3, 6, 9, 0, tzinfo=scheduler_module.APP_TZ)
    current_time = {"value": base_time}
    monkeypatch.setattr(scheduler_module, "_now_app", lambda: current_time["value"])
    monkeypatch.setattr(scheduler_module, "MAX_POSTS_PER_TICK", 2, raising=False)
    monkeypatch.setattr(scheduler_module, "DELETE_AFTER_POST", True, raising=False)

    video_dir = Path(scheduler_instance.VIDEO_DIR)
    future = base_time + timedelta(minutes=45)
    video = _write_video(video_dir, "future", scheduled=future, uploaded=base_time - timedelta(minutes=5))

    post_calls = []
    monkeypatch.setattr(scheduler_module.TikTokScheduler, "_post_one", lambda self, path: post_calls.append(Path(path).name) or True, raising=False)
    monkeypatch.setattr(scheduler_module.TikTokScheduler, "_ensure_logged", lambda self: True, raising=False)

    scheduler_instance.scheduled_posting()
    assert post_calls == []

    current_time["value"] = future + timedelta(minutes=1)
    scheduler_instance.scheduled_posting()
    assert post_calls == ["future.mp4"]

    # File removed after success; rerun should not add duplicates
    scheduler_instance.scheduled_posting()
    assert post_calls == ["future.mp4"]


def test_assign_dynamic_slots_persists_new_slots(scheduler_instance, scheduler_module, tmp_path, monkeypatch):
    base_time = datetime(2024, 3, 7, 9, 0, tzinfo=scheduler_module.APP_TZ)
    monkeypatch.setattr(scheduler_module, "_now_app", lambda: base_time)
    monkeypatch.setattr(scheduler_module, "_read_schedules", lambda: ["09:15"])

    video_dir = Path(scheduler_instance.VIDEO_DIR)

    # Posted video should be ignored
    posted = video_dir / "posted.mp4"
    posted.write_bytes(b"0")
    posted_meta = posted.with_suffix(".json")
    posted_meta.write_text(
        json.dumps({"status": "posted", "uploaded_at": _iso(base_time - timedelta(minutes=10))}),
        encoding="utf-8",
    )

    future_slot = base_time + timedelta(minutes=45)
    keep = video_dir / "keep.mp4"
    keep.write_bytes(b"0")
    keep_meta = keep.with_suffix(".json")
    keep_meta.write_text(
        json.dumps(
            {
                "uploaded_at": _iso(base_time - timedelta(minutes=5)),
                "scheduled_at": _iso(future_slot),
                "schedule_time": future_slot.strftime("%H:%M"),
            }
        ),
        encoding="utf-8",
    )

    needs_slot = video_dir / "assign.mp4"
    needs_slot.write_bytes(b"0")
    needs_slot_meta = needs_slot.with_suffix(".json")
    needs_slot_meta.write_text(
        json.dumps({"uploaded_at": _iso(base_time - timedelta(minutes=2))}),
        encoding="utf-8",
    )

    legacy_only = video_dir / "legacy_only.mp4"
    legacy_only.write_bytes(b"0")
    legacy_path = legacy_only.with_suffix(".meta.json")
    legacy_path.write_text(
        json.dumps({"uploaded_at": _iso(base_time - timedelta(minutes=1)), "caption": "legacy caption"}),
        encoding="utf-8",
    )

    candidates = scheduler_instance._collect_candidates()
    names = {Path(dv.path).name for dv in candidates}

    assert "posted.mp4" not in names
    assert "keep.mp4" in names
    assert "assign.mp4" in names
    assert "legacy_only.mp4" in names

    assigned_meta = json.loads(needs_slot_meta.read_text(encoding="utf-8"))
    assigned_dt = scheduler_module._parse_iso_maybe(assigned_meta["scheduled_at"])
    assert assigned_dt is not None
    assert assigned_dt >= base_time

    legacy_meta = json.loads(legacy_path.read_text(encoding="utf-8"))
    assert "scheduled_at" in legacy_meta
    logs = "\n".join(getattr(scheduler_instance, "_logs", []))


def test_assign_dynamic_slots_warns_when_no_slots_available(scheduler_instance, scheduler_module, monkeypatch):
    base_time = datetime(2024, 3, 7, 10, 0, tzinfo=scheduler_module.APP_TZ)
    monkeypatch.setattr(scheduler_module, "_now_app", lambda: base_time)
    monkeypatch.setattr(scheduler_module, "_read_schedules", lambda: [])

    video_dir = Path(scheduler_instance.VIDEO_DIR)
    for name in ("no1", "no2"):
        path = video_dir / f"{name}.mp4"
        path.write_bytes(b"0")
        path.with_suffix(".json").write_text(
            json.dumps({"uploaded_at": _iso(base_time - timedelta(minutes=1))}),
            encoding="utf-8",
        )

    scheduler_instance._collect_candidates()
    logs = "\n".join(getattr(scheduler_instance, "_logs", []))
    assert "sem slot disponível" in logs


def test_finalize_success_updates_and_moves_files(scheduler_instance, scheduler_module, tmp_path, monkeypatch):
    monkeypatch.setattr(scheduler_module, "DELETE_AFTER_POST", False, raising=False)

    video_path = Path(scheduler_instance.VIDEO_DIR) / "clip.mp4"
    video_path.write_bytes(b"0")
    meta_path = video_path.with_suffix(".json")
    meta_path.write_text(json.dumps({"status": None}), encoding="utf-8")
    legacy_path = video_path.with_suffix(".meta.json")
    legacy_path.write_text(json.dumps({}), encoding="utf-8")
    sidecar_txt = video_path.with_suffix(".txt")
    sidecar_txt.write_text("notes", encoding="utf-8")

    moved_targets = []

    def fake_safe_move(src, dst):
        moved_targets.append(Path(dst) / Path(src).name)
        return str(moved_targets[-1])

    monkeypatch.setattr(scheduler_module, "safe_move", fake_safe_move, raising=False)

    scheduler_instance._finalize_success(str(video_path))

    posted_meta = json.loads(meta_path.read_text(encoding="utf-8"))
    assert posted_meta["status"] == "posted"
    assert "posted_at" in posted_meta

    legacy_meta = json.loads(legacy_path.read_text(encoding="utf-8"))
    assert "posted_at" in legacy_meta
    assert len(moved_targets) == 4  # json, meta.json, txt, mp4
    moved_names = {p.name for p in moved_targets}
    assert moved_names == {"clip.json", "clip.meta.json", "clip.txt", "clip.mp4"}


def test_reschedule_leftovers_calls_update_with_gap(scheduler_instance, scheduler_module, monkeypatch, tmp_path):
    base_time = datetime(2024, 3, 7, 9, 0, tzinfo=scheduler_module.APP_TZ)
    monkeypatch.setattr(scheduler_module, "_now_app", lambda: base_time)

    updates = []

    def fake_update(path, hhmm, iso, log):
        updates.append((Path(path).name, hhmm, iso))

    monkeypatch.setattr(scheduler_module, "_update_sidecars_for", fake_update)

    leftovers = [
        scheduler_module.DueVideo(
            path=str(Path(scheduler_instance.VIDEO_DIR) / f"v{i}.mp4"),
            meta_path="",
            scheduled_at=base_time,
            schedule_time=None,
        )
        for i in range(3)
    ]
    scheduler_instance._reschedule_leftovers(leftovers)

    assert len(updates) == 3
    prev_dt = scheduler_module._parse_iso_maybe(updates[0][2])
    for _, _, iso in updates[1:]:
        next_dt = scheduler_module._parse_iso_maybe(iso)
        assert next_dt > prev_dt
        prev_dt = next_dt


def test_ensure_logged_handles_cookie_failures(scheduler_instance, scheduler_module, monkeypatch):
    base_time = datetime(2024, 3, 7, 10, 0, tzinfo=scheduler_module.APP_TZ)
    current_time = {"value": base_time}
    monkeypatch.setattr(scheduler_module, "_now_app", lambda: current_time["value"])
    monkeypatch.setattr(scheduler_module, "TEST_MODE", False, raising=False)
    monkeypatch.setattr(scheduler_module, "load_cookies_for_account", lambda driver, account: False)
    fake_cookies_module = types.SimpleNamespace(
        cookies_marked_invalid=lambda account: False,
        load_cookies_for_account=scheduler_module.load_cookies_for_account,
    )
    monkeypatch.setitem(sys.modules, "src.cookies", fake_cookies_module)
    monkeypatch.setattr(scheduler_module, "time", types.SimpleNamespace(sleep=lambda _: None))

    attempts = {"count": 0}

    class FakeDriver:
        def __init__(self):
            self.current_url = "https://www.tiktok.com/home"
            self._profile_dir = "/tmp/driver-profile"
            self._service_pid = 777

        def quit(self):
            pass

    fake_driver_module = types.SimpleNamespace(
        get_fresh_driver=lambda *args, **kwargs: attempts.__setitem__("count", attempts["count"] + 1) or FakeDriver(),
        is_session_alive=lambda driver: False,
    )
    monkeypatch.setitem(sys.modules, "src.driver", fake_driver_module)

    scheduler_instance.max_session_attempts = 2
    ok = scheduler_instance._ensure_logged()
    assert ok is False
    assert attempts["count"] == 1
    assert scheduler_instance._last_cookie_failure_time is not None

    # Subsequent attempts within cooldown should short-circuit
    current_time["value"] = scheduler_instance._last_cookie_failure_time + timedelta(seconds=10)
    ok = scheduler_instance._ensure_logged()
    assert ok is False

    # If cookies marked invalid, shortcut immediately
    scheduler_instance._last_cookie_failure_time = None
    current_time["value"] = base_time + timedelta(minutes=10)
    fake_cookies_module.cookies_marked_invalid = lambda account: True
    ok = scheduler_instance._ensure_logged()
    assert ok is False


def test_ensure_logged_reuses_existing_session(scheduler_instance, scheduler_module, monkeypatch):
    base_time = datetime(2024, 3, 8, 14, 0, tzinfo=scheduler_module.APP_TZ)
    monkeypatch.setattr(scheduler_module, "_now_app", lambda: base_time)
    monkeypatch.setattr(scheduler_module, "TEST_MODE", False, raising=False)

    class AliveDriver:
        current_url = "https://www.tiktok.com/foryou"

    scheduler_instance.driver = AliveDriver()
    fake_driver_module = types.SimpleNamespace(
        get_fresh_driver=lambda *args, **kwargs: None,
        is_session_alive=lambda driver: True,
    )
    monkeypatch.setitem(sys.modules, "src.driver", fake_driver_module)

    ok = scheduler_instance._ensure_logged()
    assert ok is True
    assert scheduler_instance._last_cookie_failure_time is None


def test_ensure_logged_successful_cookie_login(scheduler_instance, scheduler_module, monkeypatch):
    base_time = datetime(2024, 3, 8, 15, 0, tzinfo=scheduler_module.APP_TZ)
    monkeypatch.setattr(scheduler_module, "_now_app", lambda: base_time)
    monkeypatch.setattr(scheduler_module, "TEST_MODE", False, raising=False)
    monkeypatch.setattr(scheduler_module, "load_cookies_for_account", lambda driver, account: True)
    fake_cookies_module = types.SimpleNamespace(
        cookies_marked_invalid=lambda account: False,
        load_cookies_for_account=scheduler_module.load_cookies_for_account,
    )
    monkeypatch.setitem(sys.modules, "src.cookies", fake_cookies_module)

    class FreshDriver:
        def __init__(self):
            self.current_url = "https://www.tiktok.com/login"
            self._profile_dir = "/tmp/profile"
            self._service_pid = 999

        def quit(self):
            pass

    fake_driver_module = types.SimpleNamespace(
        get_fresh_driver=lambda *args, **kwargs: FreshDriver(),
        is_session_alive=lambda driver: False,
    )
    monkeypatch.setitem(sys.modules, "src.driver", fake_driver_module)

    ok = scheduler_instance._ensure_logged()
    assert ok is True
    assert scheduler_instance._last_cookie_failure_time is None


def test_ensure_logged_retries_after_transient_error(scheduler_instance, scheduler_module, monkeypatch):
    base_time = datetime(2024, 3, 8, 15, 30, tzinfo=scheduler_module.APP_TZ)
    monkeypatch.setattr(scheduler_module, "_now_app", lambda: base_time)
    monkeypatch.setattr(scheduler_module, "TEST_MODE", False, raising=False)
    monkeypatch.setattr(scheduler_module, "load_cookies_for_account", lambda driver, account: True)
    fake_cookies_module = types.SimpleNamespace(
        cookies_marked_invalid=lambda account: False,
        load_cookies_for_account=scheduler_module.load_cookies_for_account,
    )
    monkeypatch.setitem(sys.modules, "src.cookies", fake_cookies_module)

    class FakeDriver:
        def __init__(self):
            self.current_url = "https://www.tiktok.com/home"
            self._profile_dir = "/tmp/reretry"
            self._service_pid = 321

        def quit(self):
            pass

    attempts = {"count": 0}

    def get_fresh(*args, **kwargs):
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise scheduler_module.TRANSIENT_DRIVER_ERRORS[0]("transient")
        return FakeDriver()

    fake_driver_module = types.SimpleNamespace(
        get_fresh_driver=get_fresh,
        is_session_alive=lambda driver: False,
    )
    monkeypatch.setitem(sys.modules, "src.driver", fake_driver_module)
    monkeypatch.setattr(scheduler_module, "time", types.SimpleNamespace(sleep=lambda _: None))

    close_calls = []
    kill_calls = []
    monkeypatch.setattr(scheduler_instance, "close_driver", lambda: close_calls.append(True))
    monkeypatch.setattr(scheduler_instance, "kill_chrome_processes", lambda: kill_calls.append(True))

    scheduler_instance.max_session_attempts = 2
    ok = scheduler_instance._ensure_logged()
    assert ok is True
    assert attempts["count"] == 2
    assert close_calls  # triggered after transient failure
    assert kill_calls  # triggered during retry preparation


def test_post_one_generates_caption_when_missing(scheduler_instance, scheduler_module, monkeypatch):
    video_path = Path(scheduler_instance.VIDEO_DIR) / "clip.mp4"
    video_path.write_bytes(b"0")
    video_path.with_suffix(".json").write_text(json.dumps({}), encoding="utf-8")
    video_path.with_suffix(".meta.json").write_text(json.dumps({}), encoding="utf-8")

    captured = {"caption": None}

    class FakeUploader:
        def __init__(self, driver, log, debug_dir, account_name, reuse_existing_session):
            pass

        def post_video(self, path, desc):
            captured["caption"] = desc
            return True

    monkeypatch.setitem(
        sys.modules,
        "src.uploader_modular",
        types.SimpleNamespace(TikTokUploader=FakeUploader),
    )
    monkeypatch.setitem(
        sys.modules,
        "src.caption",
        types.SimpleNamespace(build_caption_for_video=lambda *args, **kwargs: "generated caption"),
    )

    ok = scheduler_instance._post_one(str(video_path))
    assert ok is True
    assert captured["caption"] == "generated caption"


def test_post_one_uses_description_when_caption_blank(scheduler_instance, scheduler_module, monkeypatch):
    video_path = Path(scheduler_instance.VIDEO_DIR) / "desc.mp4"
    video_path.write_bytes(b"0")
    video_path.with_suffix(".json").write_text(
        json.dumps({"caption": "", "description": "from description"}),
        encoding="utf-8",
    )

    captured = {}

    class DummyUploader:
        def __init__(self, *args, **kwargs):
            pass

        def post_video(self, path, desc):
            captured["caption"] = desc
            return True

    monkeypatch.setitem(
        sys.modules,
        "src.uploader_modular",
        types.SimpleNamespace(TikTokUploader=DummyUploader),
    )
    monkeypatch.setitem(
        sys.modules,
        "src.caption",
        types.SimpleNamespace(build_caption_for_video=lambda *a, **k: "unused"),
    )

    ok = scheduler_instance._post_one(str(video_path))
    assert ok is True
    assert captured["caption"] == "from description"


def test_post_one_uses_legacy_caption_when_json_missing(scheduler_instance, scheduler_module, monkeypatch):
    video_path = Path(scheduler_instance.VIDEO_DIR) / "legacycap.mp4"
    video_path.write_bytes(b"0")
    video_path.with_suffix(".meta.json").write_text(
        json.dumps({"caption": "legacy content"}),
        encoding="utf-8",
    )

    captured = {}

    class DummyUploader:
        def __init__(self, *args, **kwargs):
            pass

        def post_video(self, path, desc):
            captured["caption"] = desc
            return True

    monkeypatch.setitem(
        sys.modules,
        "src.uploader_modular",
        types.SimpleNamespace(TikTokUploader=DummyUploader),
    )
    monkeypatch.setitem(
        sys.modules,
        "src.caption",
        types.SimpleNamespace(build_caption_for_video=lambda *a, **k: "unused"),
    )

    ok = scheduler_instance._post_one(str(video_path))
    assert ok is True
    assert captured["caption"] == "legacy content"


def test_due_now_logs_when_no_videos_due(scheduler_instance, scheduler_module, monkeypatch):
    base_time = datetime(2024, 3, 8, 16, 0, tzinfo=scheduler_module.APP_TZ)
    monkeypatch.setattr(scheduler_module, "_now_app", lambda: base_time)
    logs = []
    scheduler_instance._logger = logs.append

    later = base_time + timedelta(minutes=30)
    candidates = [
        scheduler_module.DueVideo(
            path=str(Path(scheduler_instance.VIDEO_DIR) / "future.mp4"),
            meta_path="",
            scheduled_at=later,
            schedule_time="16:30",
        )
    ]
    due = scheduler_instance._due_now(candidates)
    assert due == []
    joined = "\n".join(logs)
    assert "🔍 DEBUG _due_now" in joined


def test_scheduled_posting_aborts_when_not_logged(scheduler_instance, scheduler_module, monkeypatch):
    base_time = datetime(2024, 3, 8, 17, 0, tzinfo=scheduler_module.APP_TZ)
    monkeypatch.setattr(scheduler_module, "_now_app", lambda: base_time)
    monkeypatch.setattr(scheduler_module, "MAX_POSTS_PER_TICK", 5, raising=False)
    video = _write_video(Path(scheduler_instance.VIDEO_DIR), "pending", base_time, base_time - timedelta(minutes=5))

    logs = []
    scheduler_instance._logger = logs.append
    monkeypatch.setattr(scheduler_module.TikTokScheduler, "_ensure_logged", lambda self: False, raising=False)
    scheduler_instance.scheduled_posting()

    text = "\n".join(logs)
    assert "Sem sessão válida" in text
    assert Path(video).exists()


def test_scheduled_posting_handles_transient_errors(scheduler_instance, scheduler_module, monkeypatch):
    base_time = datetime(2024, 3, 8, 18, 0, tzinfo=scheduler_module.APP_TZ)
    monkeypatch.setattr(scheduler_module, "_now_app", lambda: base_time)
    monkeypatch.setattr(scheduler_module, "MAX_POSTS_PER_TICK", 2, raising=False)
    video = _write_video(Path(scheduler_instance.VIDEO_DIR), "error", base_time, base_time - timedelta(minutes=1))

    close_calls = []
    monkeypatch.setattr(scheduler_instance, "close_driver", lambda: close_calls.append(True))

    class RetryError(scheduler_module.TRANSIENT_DRIVER_ERRORS[0]):
        pass

    calls = {"post": 0, "ensure": 0}

    def flaky_post(self, path):
        calls["post"] += 1
        if calls["post"] == 1:
            raise RetryError("temporary")
        return True

    def ensure_logged(self):
        calls["ensure"] += 1
        return True

    monkeypatch.setattr(scheduler_module.TikTokScheduler, "_post_one", flaky_post, raising=False)
    monkeypatch.setattr(scheduler_module.TikTokScheduler, "_ensure_logged", ensure_logged, raising=False)

    scheduler_instance.scheduled_posting()
    assert calls["post"] == 2
    assert calls["ensure"] == 2
    assert close_calls, "close_driver should be called after transient error"


def test_setup_schedules_configures_interval(scheduler_instance, scheduler_module, monkeypatch):
    recorded = {"interval": None}

    class FakeScheduler:
        def __init__(self):
            self.jobs = []

        def clear(self):
            self.jobs.clear()

        def every(self, seconds):
            recorded["interval"] = seconds

            class Dummy:
                def __init__(inner_self):
                    inner_self.seconds = inner_self

                def do(inner_self, func):
                    scheduler_instance._scheduled_func = func
                    return func

            return Dummy()

    monkeypatch.setattr(scheduler_instance, "schedule", FakeScheduler())
    monkeypatch.setattr(scheduler_module, "_read_schedules", lambda: ["10:00"])
    monkeypatch.setattr(os, "getenv", lambda key, default=None: "30" if key == "TIKTOK_CHECK_INTERVAL_SECONDS" else default)

    scheduler_instance.setup_schedules()
    assert recorded["interval"] == 30
    assert hasattr(scheduler_instance, "_scheduled_func")


def test_start_and_stop_scheduler_thread(monkeypatch, scheduler_instance, scheduler_module):
    calls = {"ensure_base": 0, "run_loop": 0}

    monkeypatch.setattr(scheduler_module, "ensure_base", lambda: calls.__setitem__("ensure_base", calls["ensure_base"] + 1))

    class FakeThread:
        def __init__(self, target, daemon):
            self._target = target

        def start(self):
            # Make the loop exit immediately
            scheduler_instance.running = False
            calls["run_loop"] += 1
            self._target()

        def is_alive(self):
            return False

        def join(self, timeout=None):
            pass

    monkeypatch.setattr(threading, "Thread", FakeThread)
    scheduler_instance.running = False
    scheduler_instance.start()
    assert calls["ensure_base"] == 1
    assert calls["run_loop"] == 1

    close_calls = []
    monkeypatch.setattr(scheduler_instance, "close_driver", lambda: close_calls.append(True))
    scheduler_instance.stop()
    assert close_calls


def test_scheduled_posting_logs_failure(scheduler_instance, scheduler_module, monkeypatch):
    base_time = datetime(2024, 3, 8, 19, 0, tzinfo=scheduler_module.APP_TZ)
    monkeypatch.setattr(scheduler_module, "_now_app", lambda: base_time)
    monkeypatch.setattr(scheduler_module, "MAX_POSTS_PER_TICK", 2, raising=False)
    video = _write_video(Path(scheduler_instance.VIDEO_DIR), "fail", base_time, base_time - timedelta(minutes=1))

    monkeypatch.setattr(scheduler_module.TikTokScheduler, "_ensure_logged", lambda self: True, raising=False)
    monkeypatch.setattr(scheduler_module.TikTokScheduler, "_post_one", lambda self, path: False, raising=False)

    logs = []
    scheduler_instance._logger = logs.append

    scheduler_instance.scheduled_posting()
    text = "\n".join(logs)
    assert "Postagem não confirmada" in text
    assert Path(video).exists()


def test_post_one_uses_existing_caption_fields(scheduler_instance, scheduler_module, monkeypatch):
    video_path = Path(scheduler_instance.VIDEO_DIR) / "caption.mp4"
    video_path.write_bytes(b"0")
    video_path.with_suffix(".json").write_text(
        json.dumps({"caption": "from json"}), encoding="utf-8"
    )

    captured = {"caption": None}

    class DummyUploader:
        def __init__(self, *args, **kwargs):
            pass

        def post_video(self, path, desc):
            captured["caption"] = desc
            return True

    monkeypatch.setitem(
        sys.modules,
        "src.uploader_modular",
        types.SimpleNamespace(TikTokUploader=DummyUploader),
    )
    monkeypatch.setitem(
        sys.modules,
        "src.caption",
        types.SimpleNamespace(build_caption_for_video=lambda *a, **k: "unused"),
    )

    ok = scheduler_instance._post_one(str(video_path))
    assert ok is True
    assert captured["caption"] == "from json"


def test_run_loop_handles_exception_and_recovers(scheduler_instance, scheduler_module, monkeypatch):
    calls = {"run_pending": 0}

    def fake_run_pending():
        calls["run_pending"] += 1
        if calls["run_pending"] == 1:
            raise RuntimeError("boom")
        scheduler_instance.running = False

    scheduler_instance.schedule.run_pending = fake_run_pending

    close_calls = []
    monkeypatch.setattr(scheduler_instance, "close_driver", lambda: close_calls.append(True))
    monkeypatch.setattr(scheduler_module, "time", types.SimpleNamespace(sleep=lambda _: None))

    scheduler_instance.scheduler_active = True
    scheduler_instance.running = True
    scheduler_instance.run_loop()

    assert close_calls, "close_driver should be called after exception"
    assert calls["run_pending"] >= 2

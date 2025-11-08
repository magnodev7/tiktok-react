import json
import os
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

import src.planner as planner


@pytest.fixture
def planner_env(tmp_path, monkeypatch):
    videos_dir = tmp_path / "videos"
    state_dir = tmp_path / "state"
    videos_dir.mkdir()

    monkeypatch.setattr(planner, "BASE_VIDEOS_DIR", str(videos_dir), raising=False)
    monkeypatch.setattr(planner, "BASE_STATE_DIR", str(state_dir), raising=False)
    monkeypatch.setattr(
        planner,
        "SCHEDULE_INDEX_FILE",
        os.path.join(str(state_dir), "schedule_index.json"),
        raising=False,
    )
    monkeypatch.setattr(planner, "CATCH_UP", False, raising=False)

    def ensure_account(name: str):
        path = videos_dir / name
        path.mkdir(parents=True, exist_ok=True)
        return path

    def add_video(account: str, basename: str, meta: dict):
        acc_dir = ensure_account(account)
        (acc_dir / f"{basename}.mp4").write_bytes(b"video")
        (acc_dir / f"{basename}.json").write_text(
            json.dumps(meta), encoding="utf-8"
        )
        return acc_dir / f"{basename}.json"

    def sidecar_path(account: str, basename: str):
        return videos_dir / account / f"{basename}.json"

    return SimpleNamespace(
        videos_dir=videos_dir,
        state_dir=state_dir,
        ensure_account=ensure_account,
        add_video=add_video,
        sidecar_path=sidecar_path,
    )


def test_plan_all_accounts_allocates_and_reallocates(planner_env):
    planner_env.add_video("acc1", "video1", {"status": "pending"})
    past_dt = planner.datetime.now(planner.TZ) - timedelta(hours=4)
    planner_env.add_video(
        "acc1",
        "video2",
        {"status": "pending", "scheduled_at": past_dt.isoformat()},
    )

    summary = planner.plan_all_accounts()
    assert "acc1" in summary
    account_summary = summary["acc1"]
    assert account_summary["assigned"] == 1
    assert account_summary["waitlisted"] == 0
    assert account_summary["account"] == "acc1"
    assert any(item[0] == "video1.mp4" for item in account_summary["items"])

    video1_sidecar = json.loads(
        planner_env.sidecar_path("acc1", "video1").read_text(encoding="utf-8")
    )
    video2_sidecar = json.loads(
        planner_env.sidecar_path("acc1", "video2").read_text(encoding="utf-8")
    )

    assert video1_sidecar["status"] == "pending"
    assert "scheduled_at" in video1_sidecar
    assert video2_sidecar["status"] == "pending"
    assert "scheduled_at" in video2_sidecar

    video1_scheduled = planner.datetime.fromisoformat(video1_sidecar["scheduled_at"])
    video2_scheduled = planner.datetime.fromisoformat(video2_sidecar["scheduled_at"])
    now = planner.datetime.now(planner.TZ)
    assert video1_scheduled.tzinfo is not None
    assert video2_scheduled.tzinfo is not None
    assert video1_scheduled >= now - timedelta(days=planner.HORIZON_DAYS)
    assert video2_scheduled > now

    with open(planner.SCHEDULE_INDEX_FILE, "r", encoding="utf-8") as fh:
        schedule_index = json.load(fh)
    assert "acc1" in schedule_index
    assert any(value in {"video1", "video2"} for value in schedule_index["acc1"].values())

    preview = planner.preview_schedule("acc1")
    assert preview["account"] == "acc1"
    assert preview["tz"] == planner.TZ_NAME
    assert any(item["video"] == "video1" for item in preview["grid"])


def test_reallocate_skips_when_catch_up_enabled(planner_env, monkeypatch):
    past_dt = planner.datetime.now(planner.TZ) - timedelta(days=1)
    planner_env.add_video(
        "acc1",
        "video-old",
        {"status": "pending", "scheduled_at": past_dt.isoformat()},
    )
    monkeypatch.setattr(planner, "CATCH_UP", True, raising=False)

    result = planner.reallocate_missed_slots_for_account("acc1")
    assert result == {"account": "acc1", "changed": 0, "catch_up": True}

    sidecar = json.loads(
        planner_env.sidecar_path("acc1", "video-old").read_text(encoding="utf-8")
    )
    assert sidecar["scheduled_at"] == past_dt.isoformat()
    assert sidecar["status"] == "pending"


def test_allocate_waitlists_when_capacity_exceeded(planner_env, monkeypatch):
    planner_env.add_video("acc1", "video1", {"status": "pending"})
    planner_env.add_video("acc1", "video2", {"status": "pending"})

    slot_dt = planner.datetime.now(planner.TZ) + timedelta(hours=1)
    monkeypatch.setattr(
        planner,
        "generate_slots_now",
        lambda horizon=planner.HORIZON_DAYS: [planner.Slot(dt=slot_dt)],
        raising=False,
    )

    summary = planner.plan_all_accounts()
    account_summary = summary["acc1"]
    assert account_summary["assigned"] == 1
    assert account_summary["waitlisted"] == 1

    video1_data = json.loads(
        planner_env.sidecar_path("acc1", "video1").read_text(encoding="utf-8")
    )
    video2_data = json.loads(
        planner_env.sidecar_path("acc1", "video2").read_text(encoding="utf-8")
    )

    assigned = {"status": video1_data["status"], "scheduled": video1_data.get("scheduled_at")}
    waitlisted = {"status": video2_data["status"], "reason": video2_data.get("waitlist_reason")}
    assert assigned["status"] == "pending"
    assert assigned["scheduled"] == slot_dt.isoformat()
    assert waitlisted["status"] == "waitlist"
    assert waitlisted["reason"] == f"capacity_exceeded_{planner.HORIZON_DAYS}d"


def test_parse_hhmm_invalid_format():
    with pytest.raises(ValueError):
        planner._parse_hhmm("8:00")


def test_day_slots_raises_when_end_before_start(monkeypatch):
    day = datetime.now(planner.TZ)
    monkeypatch.setattr(planner, "SLOT_START", "10:00", raising=False)
    monkeypatch.setattr(planner, "SLOT_END", "08:00", raising=False)
    with pytest.raises(ValueError):
        planner._day_slots(day)


def test_collect_occupied_slots_handles_malformed_json(planner_env):
    acc_dir = planner_env.ensure_account("acc1")
    (acc_dir / "bad.mp4").write_bytes(b"video")
    (acc_dir / "bad.json").write_text("{ malformed", encoding="utf-8")

    occ = planner._collect_occupied_slots(str(acc_dir))
    assert occ == {}

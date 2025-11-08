import os
import time

from src.modules.duplicate_protection import DuplicateProtectionModule


def test_stale_lock_is_removed_automatically(tmp_path, monkeypatch):
    monkeypatch.setenv("TIKTOK_LOCK_VALID_SECONDS", "1")
    module = DuplicateProtectionModule(logger=lambda *_: None)

    video_path = tmp_path / "sample.mp4"
    video_path.write_text("dummy")
    lock_path = video_path.with_suffix(".posting.lock")
    lock_path.write_text("lock")

    past = time.time() - 5
    os.utime(lock_path, (past, past))

    exists, age = module.check_posting_lock_exists(str(video_path))

    assert exists is False
    assert age >= 5
    assert not lock_path.exists()

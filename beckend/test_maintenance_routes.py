import io
import tarfile
from types import SimpleNamespace

import pytest

import src.api.maintenance_routes as maintenance


def test_resolve_git_pull_target_uses_upstream(monkeypatch):
    def fake_run_command(cmd, cwd=None, timeout=300):
        if cmd == ["git", "rev-parse", "--abbrev-ref", "HEAD"]:
            return {"success": True, "stdout": "feature\n", "stderr": "", "returncode": 0}
        if cmd == ["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"]:
            return {"success": True, "stdout": "origin/feature\n", "stderr": "", "returncode": 0}
        raise AssertionError(f"Unexpected command: {cmd}")

    monkeypatch.setattr(maintenance, "_run_command", fake_run_command)

    remote, branch, current = maintenance._resolve_git_pull_target()
    assert remote == "origin"
    assert branch == "feature"
    assert current == "feature"


def test_resolve_git_pull_target_without_upstream(monkeypatch):
    def fake_run_command(cmd, cwd=None, timeout=300):
        if cmd == ["git", "rev-parse", "--abbrev-ref", "HEAD"]:
            return {"success": True, "stdout": "develop\n", "stderr": "", "returncode": 0}
        if cmd == ["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"]:
            return {"success": False, "stdout": "", "stderr": "fatal: no upstream", "returncode": 1}
        raise AssertionError(f"Unexpected command: {cmd}")

    monkeypatch.setattr(maintenance, "_run_command", fake_run_command)

    remote, branch, current = maintenance._resolve_git_pull_target()
    assert remote == "origin"
    assert branch == "develop"
    assert current == "develop"


@pytest.fixture
def maintenance_env(tmp_path, monkeypatch):
    project_root = tmp_path / "project"
    project_root.mkdir()

    beckend_dir = project_root / "beckend"
    beckend_dir.mkdir()
    (beckend_dir / "manage.sh").write_text("#!/bin/sh\n", encoding="utf-8")

    src_dir = beckend_dir / "src"
    src_dir.mkdir()
    (src_dir / "main.py").write_text("print('hello')\n", encoding="utf-8")
    venv_bin = beckend_dir / "venv" / "bin"
    venv_bin.mkdir(parents=True, exist_ok=True)
    (venv_bin / "python3").write_text("python-bin", encoding="utf-8")

    videos_dir = project_root / "videos"
    videos_dir.mkdir()
    (videos_dir / "video1.mp4").write_text("video-data", encoding="utf-8")

    profiles_dir = project_root / "profiles"
    profiles_dir.mkdir()
    (profiles_dir / "profile1").write_text("profile-data", encoding="utf-8")

    (project_root / "app.txt").write_text("original", encoding="utf-8")

    git_dir = project_root / ".git"
    git_dir.mkdir()
    (git_dir / "config").write_text("[core]\n", encoding="utf-8")

    backups_dir = project_root / "backups"
    dist_dir = project_root / "dist"
    dist_dir.mkdir()
    (dist_dir / "index.html").write_text("<html></html>", encoding="utf-8")

    monkeypatch.setattr(maintenance, "PROJECT_ROOT", project_root, raising=False)
    monkeypatch.setattr(maintenance, "BACKEND_DIR", beckend_dir, raising=False)
    monkeypatch.setattr(maintenance, "MANAGE_SH", beckend_dir / "manage.sh", raising=False)
    monkeypatch.setattr(maintenance, "BACKUPS_DIR", backups_dir, raising=False)
    monkeypatch.setattr(maintenance, "RESTORE_STATUS_DIR", backups_dir / "restore-status", raising=False)
    monkeypatch.setattr(maintenance, "PRESERVE_DIRS", {"videos"}, raising=False)
    monkeypatch.setattr(
        maintenance,
        "BACKUP_EXCLUDES",
        {"videos", "backups", "restore-status", ".git", "__pycache__", ".pytest_cache", "venv", ".venv"},
        raising=False,
    )

    return SimpleNamespace(
        project_root=project_root,
        backups_dir=backups_dir,
        videos_dir=videos_dir,
        profiles_dir=profiles_dir,
    )


def test_create_project_backup_excludes_preserved_dirs(maintenance_env):
    archive_path = maintenance._create_project_backup()
    assert archive_path.exists()

    with tarfile.open(archive_path, "r:*") as tar:
        names = tar.getnames()
        assert "app.txt" in names
        assert any(name.startswith("beckend/") for name in names)
        assert not any(name.startswith("videos") for name in names)
        assert any(name.startswith("profiles/") for name in names)


def test_restore_project_from_archive_preserves_videos_and_profiles(maintenance_env):
    archive_path = maintenance._create_project_backup()

    (maintenance_env.project_root / "app.txt").write_text("modified", encoding="utf-8")
    profile_path = maintenance_env.profiles_dir / "profile1"
    profile_path.write_text("profile-modified", encoding="utf-8")
    maintenance_env.videos_dir.mkdir(exist_ok=True)
    video_path = maintenance_env.videos_dir / "video1.mp4"
    video_path.write_text("new-video-data", encoding="utf-8")
    new_layout = maintenance_env.project_root / "new_layout.jsx"
    new_layout.write_text("latest layout", encoding="utf-8")
    backend_src = maintenance_env.project_root / "beckend" / "src" / "main.py"
    backend_src.write_text("latest backend code\n", encoding="utf-8")

    restore_info = maintenance._restore_project_from_archive(archive_path)

    assert (maintenance_env.project_root / "app.txt").read_text(encoding="utf-8") == "original"
    assert profile_path.read_text(encoding="utf-8") == "profile-data"
    assert video_path.read_text(encoding="utf-8") == "new-video-data"
    assert new_layout.read_text(encoding="utf-8") == "latest layout"
    assert backend_src.read_text(encoding="utf-8") == "latest backend code\n"
    assert "app.txt" in restore_info["restored_items"]
    assert "beckend" in restore_info["restored_items"]
    assert "beckend/src" in restore_info["skipped_items"]
    assert any(item.startswith("beckend/venv") for item in restore_info["skipped_items"])


def test_restore_project_from_archive_rejects_path_traversal(maintenance_env, tmp_path):
    malicious = tmp_path / "malicious.tar.gz"
    with tarfile.open(malicious, "w:gz") as tar:
        payload = b"malicious"
        info = tarfile.TarInfo(name="../evil.txt")
        info.size = len(payload)
        tar.addfile(info, io.BytesIO(payload))

    with pytest.raises(ValueError):
        maintenance._restore_project_from_archive(malicious)


def test_run_update_job_records_status(maintenance_env, monkeypatch, tmp_path):
    commands = []

    def fake_run_command(cmd, cwd=None, timeout=300):
        commands.append(tuple(cmd))
        if cmd == ["git", "status", "--porcelain", "--untracked-files=no"]:
            return {"success": True, "stdout": "", "stderr": "", "returncode": 0}
        if cmd[:2] == ["git", "fetch"]:
            return {"success": True, "stdout": "", "stderr": "", "returncode": 0}
        if cmd == ["git", "rev-parse", "--abbrev-ref", "HEAD"]:
            return {"success": True, "stdout": "main\n", "stderr": "", "returncode": 0}
        if cmd[:2] == ["git", "pull"]:
            return {
                "success": True,
                "stdout": "Updating abc..def",
                "stderr": "",
                "returncode": 0,
            }
        if cmd == ["git", "diff", "--name-only", "HEAD@{1}", "HEAD"]:
            return {
                "success": True,
                "stdout": "src/app.js\n",
                "stderr": "",
                "returncode": 0,
            }
        if cmd == ["npm", "install"]:
            return {"success": True, "stdout": "", "stderr": "", "returncode": 0}
        if cmd == ["npm", "run", "build"]:
            return {"success": True, "stdout": "build success", "stderr": "", "returncode": 0}
        return {"success": True, "stdout": "", "stderr": "", "returncode": 0}

    restart_called = {"value": False}

    monkeypatch.setattr(maintenance, "_run_command", fake_run_command)
    monkeypatch.setattr(maintenance, "_resolve_git_pull_target", lambda: ("origin", "main", "main"))
    monkeypatch.setattr(maintenance, "_trigger_restart_async", lambda: restart_called.update(value=True))

    job_id = "test-job"
    maintenance._run_update_job(job_id, {"force": False, "target_ref": None, "remote": "origin"})

    status_path = maintenance.UPDATE_STATUS_DIR / f"{job_id}.json"
    status_data = maintenance._read_json(status_path)

    assert status_data is not None
    assert status_data["state"] == "waiting_restart"
    assert status_data["completed"] is True
    assert any(step["step"] == "git_pull" for step in status_data["steps"])
    assert any(step["step"] == "git_diff_summary" for step in status_data["steps"])
    assert any(step["step"] == "frontend_build" for step in status_data["steps"])
    assert restart_called["value"] is True
    web_index = maintenance.BACKEND_DIR / "web" / "index.html"
    assert web_index.exists()
    assert ("git", "status", "--porcelain", "--untracked-files=no") in commands
    assert ("git", "fetch", "origin") in [cmd[:3] for cmd in commands if cmd[0] == "git" and cmd[1] == "fetch"]
    assert ("git", "diff", "--name-only", "HEAD@{1}", "HEAD") in commands


def test_run_update_job_checkout_remote_branch(maintenance_env, monkeypatch):
    commands = []

    def fake_run_command(cmd, cwd=None, timeout=300):
        commands.append(tuple(cmd))
        if cmd == ["git", "status", "--porcelain", "--untracked-files=no"]:
            return {"success": True, "stdout": "", "stderr": "", "returncode": 0}
        if cmd[:2] == ["git", "fetch"]:
            return {"success": True, "stdout": "", "stderr": "", "returncode": 0}
        if cmd == ["git", "rev-parse", "--abbrev-ref", "HEAD"]:
            return {"success": True, "stdout": "main\n", "stderr": "", "returncode": 0}
        if cmd == ["git", "checkout", "release"]:
            return {
                "success": False,
                "stdout": "",
                "stderr": "error: pathspec 'release' did not match any file(s) known to git",
                "returncode": 1,
            }
        if cmd == ["git", "checkout", "-B", "release", "origin/release"]:
            return {"success": True, "stdout": "", "stderr": "", "returncode": 0}
        if cmd[:2] == ["git", "pull"]:
            return {"success": True, "stdout": "Updating 123..456", "stderr": "", "returncode": 0}
        if cmd == ["git", "diff", "--name-only", "HEAD@{1}", "HEAD"]:
            return {
                "success": True,
                "stdout": "beckend/requirements.txt\nsrc/app.js\n",
                "stderr": "",
                "returncode": 0,
            }
        if cmd == ["npm", "run", "build"]:
            return {"success": True, "stdout": "build ok", "stderr": "", "returncode": 0}
        if cmd == ["bash", "-c", "cd beckend && source venv/bin/activate && pip install -r requirements.txt"]:
            return {"success": True, "stdout": "pip ok", "stderr": "", "returncode": 0}
        return {"success": True, "stdout": "", "stderr": "", "returncode": 0}

    monkeypatch.setattr(maintenance, "_run_command", fake_run_command)
    monkeypatch.setattr(maintenance, "_trigger_restart_async", lambda: None)

    job_id = "checkout-job"
    maintenance._run_update_job(job_id, {"force": False, "target_ref": "origin/release", "remote": "origin"})

    status_path = maintenance.UPDATE_STATUS_DIR / f"{job_id}.json"
    status_data = maintenance._read_json(status_path)

    assert status_data is not None
    assert status_data["state"] == "waiting_restart"
    assert status_data["current_branch"] == "release"
    assert status_data["checked_out_branch"] == "release"
    checkout_steps = [step for step in status_data["steps"] if step["step"] in {"git_checkout_target", "git_checkout_track"}]
    assert checkout_steps and checkout_steps[-1]["step"] == "git_checkout_track"
    assert ("git", "status", "--porcelain", "--untracked-files=no") in commands
    assert ("git", "checkout", "release") in commands
    assert ("git", "checkout", "-B", "release", "origin/release") in commands


def test_run_update_job_force_stash_includes_untracked(maintenance_env, monkeypatch):
    commands = []

    def fake_run_command(cmd, cwd=None, timeout=300):
        commands.append(tuple(cmd))
        if cmd == ["git", "status", "--porcelain", "--untracked-files=no"]:
            return {"success": True, "stdout": " M src/file.txt\n", "stderr": "", "returncode": 0}
        if cmd[:2] == ["git", "fetch"]:
            return {"success": True, "stdout": "", "stderr": "", "returncode": 0}
        if cmd[:2] == ["git", "pull"]:
            return {"success": True, "stdout": "Updating 1..2", "stderr": "", "returncode": 0}
        if cmd == ["git", "diff", "--name-only", "HEAD@{1}", "HEAD"]:
            return {"success": True, "stdout": "", "stderr": "", "returncode": 0}
        return {"success": True, "stdout": "", "stderr": "", "returncode": 0}

    monkeypatch.setattr(maintenance, "_run_command", fake_run_command)
    monkeypatch.setattr(maintenance, "_trigger_restart_async", lambda: None)

    job_id = "force-job"
    maintenance._run_update_job(job_id, {"force": True, "target_ref": None, "remote": "origin"})

    assert ("git", "stash", "--include-untracked") in commands

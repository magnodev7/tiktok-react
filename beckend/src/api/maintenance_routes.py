"""Rotas de manutenção e gerenciamento do sistema."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tarfile
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, List, Set
import logging

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, BackgroundTasks, status
from fastapi.responses import FileResponse
from pydantic import BaseModel

from src.auth import get_current_active_user, get_db
from src.models import User as UserModel
from sqlalchemy.orm import Session

from .schemas import APIResponse
from .utils import raise_http_error, success_response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/maintenance", tags=["maintenance"])

# Diretórios do projeto
PROJECT_ROOT = Path(__file__).resolve().parents[3]
BACKEND_DIR = PROJECT_ROOT / "beckend"
MANAGE_SH = BACKEND_DIR / "manage.sh"
BACKUPS_DIR = PROJECT_ROOT / "backups"
RESTORE_STATUS_DIR = BACKUPS_DIR / "restore-status"
UPDATE_STATUS_DIR = BACKUPS_DIR / "update-status"
PRESERVE_DIRS: Set[str] = {"videos"}
BACKUP_EXCLUDES: Set[str] = PRESERVE_DIRS | {
    "backups",
    "restore-status",
    ".git",
    "__pycache__",
    ".pytest_cache",
    "venv",
    ".venv",
}
RESTORE_PROTECTED_PREFIXES = {
    Path(".git"),
    Path("src"),
    Path("beckend/src"),
    Path("beckend/web"),
    Path("beckend/venv"),
    Path("beckend/.venv"),
    Path("dist"),
    Path("node_modules"),
    Path("package.json"),
    Path("package-lock.json"),
    Path("pnpm-lock.yaml"),
    Path("yarn.lock"),
    Path("venv"),
}


class ServiceActionRequest(BaseModel):
    action: str  # start, stop, restart, status


class UpdateRequest(BaseModel):
    force: bool = False
    target_ref: Optional[str] = None
    remote: str = "origin"


class GitConfigRequest(BaseModel):
    remote_url: str
    remote_name: str = "origin"


class GitCheckoutRequest(BaseModel):
    branch: str
    force: bool = False
    fetch: bool = True


def _run_command(cmd: List[str], cwd: Optional[Path] = None, timeout: int = 300) -> dict:
    """Executa comando e retorna resultado."""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd or PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "success": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "returncode": -1,
            "stdout": "",
            "stderr": f"Timeout após {timeout}s",
        }
    except Exception as e:
        return {
            "success": False,
            "returncode": -1,
            "stdout": "",
            "stderr": str(e),
        }


def _check_admin(user: UserModel) -> None:
    """Verifica se o usuário é admin."""
    if not user.is_admin:
        raise_http_error(
            status.HTTP_403_FORBIDDEN,
            error="admin_required",
            message="Somente administradores podem acessar esta funcionalidade"
        )


def _parse_branch_list(raw: str) -> List[dict]:
    branches: List[dict] = []
    for line in raw.strip().splitlines():
        if not line.strip():
            continue
        parts = line.split("|")
        if len(parts) < 4:
            # Espera formato: name|commit|date|subject
            name = parts[0].strip()
            commit = parts[1].strip() if len(parts) > 1 else ""
            date = parts[2].strip() if len(parts) > 2 else ""
            subject = parts[3].strip() if len(parts) > 3 else ""
        else:
            name, commit, date, subject = [p.strip() for p in parts[:4]]
        branches.append({
            "name": name,
            "commit": commit,
            "date": date,
            "subject": subject,
        })
    return branches


def _run_manage_command(action_args: List[str], timeout: int = 60) -> Tuple[dict, bool]:
    """
    Executa manage.sh tentando sudo sem senha primeiro.

    Retorna (resultado, sudo_falhou) onde sudo_falhou indica que a execução com sudo
    falhou por falta de configuração (senha requisitada, permissão insuficiente, etc).
    """
    sudo_cmd = ["sudo", "-n", str(MANAGE_SH), *action_args]
    sudo_result = _run_command(sudo_cmd, timeout=timeout)

    if sudo_result["success"]:
        return sudo_result, False

    stderr_lower = (sudo_result.get("stderr") or "").lower()
    sudo_failed = any(
        keyword in stderr_lower
        for keyword in [
            "a password is required",
            "password is required",
            "a terminal is required",
            "sudo:",
            "permission denied",
            "not in the sudoers",
        ]
    )

    fallback_result = _run_command(
        ["bash", str(MANAGE_SH), *action_args],
        timeout=timeout,
    )

    if fallback_result["success"]:
        sudo_failed = False

    return fallback_result, sudo_failed


def _resolve_git_pull_target() -> Tuple[str, str, str]:
    """
    Determina parâmetros (remote, branch, current_branch) para git pull.

    - Se houver upstream configurado (origin/feature), usa esse remoto/branch.
    - Senão, utiliza branch atual com remote origin.
    - Caso branch atual não possa ser determinado, retorna remote origin e branch vazio.
    """
    current_branch_cmd = _run_command(["git", "rev-parse", "--abbrev-ref", "HEAD"], timeout=5)
    current_branch = current_branch_cmd["stdout"].strip() if current_branch_cmd["success"] else "unknown"

    upstream_cmd = _run_command(
        ["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"],
        timeout=5
    )
    if upstream_cmd["success"]:
        upstream = upstream_cmd["stdout"].strip()
        if upstream:
            if "/" in upstream:
                remote, branch = upstream.split("/", 1)
            else:
                remote, branch = upstream, ""
            return remote or "origin", branch, current_branch

    remote = "origin"
    branch = current_branch if current_branch and current_branch != "unknown" else ""
    return remote, branch, current_branch


def _ensure_backups_dir() -> Path:
    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
    return BACKUPS_DIR


def _ensure_restore_status_dir() -> Path:
    global RESTORE_STATUS_DIR
    path = _ensure_backups_dir() / "restore-status"
    path.mkdir(parents=True, exist_ok=True)
    RESTORE_STATUS_DIR = path
    return path


def _ensure_update_status_dir() -> Path:
    global UPDATE_STATUS_DIR
    path = _ensure_backups_dir() / "update-status"
    path.mkdir(parents=True, exist_ok=True)
    UPDATE_STATUS_DIR = path
    return path


def _read_json(path: Path) -> Optional[dict]:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return None


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with open(tmp_path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    tmp_path.replace(path)


def _iter_backup_candidates() -> List[Path]:
    items: List[Path] = []
    for item in PROJECT_ROOT.iterdir():
        if item.name in BACKUP_EXCLUDES:
            continue
        items.append(item)
    return items


def _create_project_backup() -> Path:
    backup_dir = _ensure_backups_dir()
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    archive_path = backup_dir / f"project-backup-{timestamp}.tar.gz"

    with tarfile.open(archive_path, "w:gz") as tar:
        for item in _iter_backup_candidates():
            arcname = item.relative_to(PROJECT_ROOT)
            tar.add(item, arcname=str(arcname))

    return archive_path


def _safe_extract_tar(tar: tarfile.TarFile, destination: Path) -> None:
    dest_resolved = destination.resolve()
    for member in tar.getmembers():
        member_path = (dest_resolved / member.name).resolve()
        if not member_path.is_relative_to(dest_resolved):
            raise ValueError(f"Caminho inseguro no arquivo: {member.name}")
    tar.extractall(destination)


def _restore_project_from_archive(archive_path: Path) -> dict:
    if not archive_path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {archive_path}")

    restored_items: Set[str] = set()

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        with tarfile.open(archive_path, "r:*") as tar:
            _safe_extract_tar(tar, tmp_path)

        skipped_paths: Set[str] = set()
        tmp_root = tmp_path.resolve()

        def _register_skip(rel_path: Path) -> None:
            for prefix in RESTORE_PROTECTED_PREFIXES:
                if rel_path == prefix or rel_path.is_relative_to(prefix):
                    skipped_paths.add(str(prefix))
                    return
            skipped_paths.add(str(rel_path))

        def _should_skip(rel_path: Path) -> bool:
            if rel_path.parts and rel_path.parts[0] in BACKUP_EXCLUDES:
                _register_skip(rel_path)
                return True
            for prefix in RESTORE_PROTECTED_PREFIXES:
                if rel_path == prefix or rel_path.is_relative_to(prefix):
                    skipped_paths.add(str(prefix))
                    return True
            if any(part in {"venv", ".venv", ".git"} for part in rel_path.parts):
                _register_skip(rel_path)
                return True
            return False

        def _copy_file(src: str, dst: str, *, follow_symlinks: bool = True) -> str:
            src_path = Path(src)
            try:
                return shutil.copy2(src_path, dst, follow_symlinks=follow_symlinks)
            except shutil.SameFileError:
                logger.debug("Ignorando arquivo idêntico durante restauração: %s -> %s", src_path, dst)
                return dst
            except PermissionError as exc:
                try:
                    rel = src_path.resolve().relative_to(tmp_root)
                except ValueError:
                    rel = src_path.name
                _register_skip(Path(rel))
                logger.warning("Sem permissão para copiar %s -> %s: %s", src_path, dst, exc)
                return dst

        def _ignore(path: str, names: List[str]) -> List[str]:
            ignored: Set[str] = set()
            current_path = Path(path)
            try:
                rel_base = current_path.resolve().relative_to(tmp_root)
            except ValueError:
                rel_base = Path()

            for name in names:
                child_rel = rel_base / name if rel_base != Path() else Path(name)
                if _should_skip(child_rel):
                    ignored.add(name)
            return list(ignored)

        for item in tmp_path.iterdir():
            if item.name in BACKUP_EXCLUDES:
                continue

            relative_path = item.relative_to(tmp_path)
            if _should_skip(relative_path):
                continue

            target = PROJECT_ROOT / item.name
            if item.is_dir():
                if target.exists() and target.is_file():
                    target.unlink()
                target.mkdir(parents=True, exist_ok=True)
                try:
                    shutil.copytree(
                        item,
                        target,
                        dirs_exist_ok=True,
                        symlinks=True,
                        copy_function=_copy_file,
                        ignore=_ignore,
                        ignore_dangling_symlinks=True,
                    )
                except Exception as exc:
                    _register_skip(relative_path)
                    logger.warning("Falha ao copiar diretório %s: %s", item, exc)
                    continue
            else:
                if target.exists() and target.is_dir():
                    shutil.rmtree(target)
                target.parent.mkdir(parents=True, exist_ok=True)
                try:
                    _copy_file(str(item), str(target))
                except Exception as exc:
                    _register_skip(relative_path)
                    logger.warning("Falha ao copiar arquivo %s: %s", item, exc)
                    continue

            restored_items.add(item.name)

    return {
        "restored_items": sorted(restored_items),
        "preserved_directories": sorted(PRESERVE_DIRS),
        "skipped_items": sorted(skipped_paths),
    }


def _record_restore_status(job_id: str, status: dict) -> Path:
    status_dir = _ensure_restore_status_dir()
    status["job_id"] = job_id
    status_path = status_dir / f"{job_id}.json"
    _write_json(status_path, status)
    _write_json(status_dir / "latest.json", status)
    logger.info("Status da restauração %s atualizado (%s)", job_id, status.get("state", "unknown"))
    return status_path


def _record_update_status(job_id: str, status: dict) -> Path:
    status_dir = _ensure_update_status_dir()
    status["job_id"] = job_id
    status_path = status_dir / f"{job_id}.json"
    _write_json(status_path, status)
    _write_json(status_dir / "latest.json", status)
    logger.info("Status da atualização %s atualizado (%s)", job_id, status.get("state", "unknown"))
    return status_path


def _trigger_restart_async():
    """Dispara reinício dos serviços em processo independente."""
    cmd = f"cd {BACKEND_DIR} && ./manage.sh all restart"
    try:
        subprocess.Popen(
            ["nohup", "bash", "-lc", cmd],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        logger.info("manage.sh all restart disparado em background.")
    except Exception as exc:
        logger.error("Falha ao disparar restart em background: %s", exc)


def _run_restore_job(job_id: str, archive_path: Path):
    logger.info("Iniciando job de restauração %s usando arquivo %s", job_id, archive_path)
    steps: List[dict] = []
    errors: List[str] = []
    status: dict = {
        "job_id": job_id,
        "archive": archive_path.name,
        "started_at": datetime.now().isoformat(),
        "state": "running",
        "steps": steps,
        "errors": errors,
        "completed": False,
    }
    _record_restore_status(job_id, status)

    try:
        restore_info = _restore_project_from_archive(archive_path)
        steps.append({
            "step": "restore_files",
            "success": True,
            "message": "Arquivos restaurados a partir do backup",
            "restored_items": restore_info["restored_items"],
            "skipped_items": restore_info["skipped_items"],
        })
        status["restored_items"] = restore_info["restored_items"]
        status["skipped_items"] = restore_info["skipped_items"]

        build_result = _run_command(["npm", "run", "build"], cwd=PROJECT_ROOT, timeout=300)
        steps.append({
            "step": "frontend_build",
            "success": build_result["success"],
            "output": build_result["stdout"][-500:] if build_result["stdout"] else "",
            "error": build_result["stderr"] if not build_result["success"] else None,
        })

        if not build_result["success"]:
            errors.append("Falha ao executar npm run build após restaurar o backup.")
            status["state"] = "failed"
            status["completed"] = False
            return

        dist_dir = PROJECT_ROOT / "dist"
        web_dir = BACKEND_DIR / "web"
        if dist_dir.exists():
            if web_dir.exists():
                shutil.rmtree(web_dir)
            shutil.copytree(dist_dir, web_dir)
            steps.append({
                "step": "copy_build",
                "success": True,
                "message": "Build copiado para beckend/web",
            })

        status["state"] = "waiting_restart"
        status["completed"] = True
        status["finished_at"] = datetime.now().isoformat()
        status["restart_scheduled"] = True
    except Exception as exc:
        logger.exception("Erro durante job de restauração %s", job_id)
        errors.append(str(exc))
        steps.append({
            "step": "exception",
            "success": False,
            "error": str(exc),
        })
        status["state"] = "failed"
        status["completed"] = False
    finally:
        status["errors"] = errors
        status.setdefault("finished_at", datetime.now().isoformat())
        _record_restore_status(job_id, status)

    if status["completed"]:
        _trigger_restart_async()


def _run_update_job(job_id: str, request_data: dict):
    logger.info("Iniciando job de atualização %s", job_id)
    req = UpdateRequest(**request_data)
    steps: List[dict] = []
    errors: List[str] = []
    status: dict = {
        "job_id": job_id,
        "request": request_data,
        "started_at": datetime.now().isoformat(),
        "state": "running",
        "steps": steps,
        "errors": errors,
        "completed": False,
    }
    _record_update_status(job_id, status)

    def _append_step(entry: dict):
        steps.append(entry)
        status["steps"] = steps
        _record_update_status(job_id, status)

    try:
        status_result = _run_command(["git", "status", "--porcelain"], timeout=10)
        dirty = status_result["success"] and status_result["stdout"].strip()
        _append_step({
            "step": "git_status",
            "success": status_result["success"],
            "output": status_result["stdout"],
            "error": status_result["stderr"] if not status_result["success"] else None,
        })

        if dirty and not req.force:
            errors.append("Há alterações locais não commitadas. Use force=true para sobrescrever.")
            status["state"] = "failed"
            return

        if dirty and req.force:
            stash_result = _run_command(["git", "stash"], timeout=30)
            _append_step({
                "step": "stash",
                "success": stash_result["success"],
                "output": stash_result["stdout"],
                "error": stash_result["stderr"] if not stash_result["success"] else None,
            })
            if not stash_result["success"]:
                errors.append("Falha ao executar git stash.")
                status["state"] = "failed"
                return

        remote = req.remote or "origin"
        target_branch: Optional[str] = None
        current_branch: Optional[str] = None

        if req.target_ref:
            status["target_ref"] = req.target_ref
            if "/" in req.target_ref and req.target_ref in {req.remote, remote}:
                # Rare case: target ref equals remote name only (no branch); treat as default branch
                target_branch = None
            elif "/" in req.target_ref:
                parts = req.target_ref.split("/", 1)
                if len(parts) == 2 and parts[0]:
                    remote = parts[0]
                    target_branch = parts[1]
                else:
                    target_branch = req.target_ref.split("/")[-1]
            else:
                target_branch = req.target_ref
        else:
            remote_resolved, branch_resolved, current_branch = _resolve_git_pull_target()
            remote = remote_resolved or remote
            target_branch = branch_resolved
            status["current_branch"] = current_branch

        fetch_cmd = ["git", "fetch", remote]
        if target_branch:
            fetch_cmd.append(target_branch)
        fetch_result = _run_command(fetch_cmd, timeout=120)
        _append_step({
            "step": "git_fetch",
            "success": fetch_result["success"],
            "output": fetch_result["stdout"],
            "error": fetch_result["stderr"] if not fetch_result["success"] else None,
        })
        if not fetch_result["success"]:
            errors.append("Falha ao executar git fetch.")
            status["state"] = "failed"
            return

        # Garantir que estamos no branch desejado antes do pull
        checkout_branch = target_branch
        current_branch_cmd = _run_command(["git", "rev-parse", "--abbrev-ref", "HEAD"], timeout=5)
        if current_branch_cmd["success"]:
            current_branch = current_branch_cmd["stdout"].strip()
            status["current_branch"] = current_branch
        else:
            current_branch = None

        if checkout_branch and (not current_branch or current_branch != checkout_branch):
            checkout_result = _run_command(["git", "checkout", checkout_branch], timeout=60)
            _append_step({
                "step": "git_checkout_target",
                "success": checkout_result["success"],
                "output": checkout_result["stdout"],
                "error": checkout_result["stderr"] if not checkout_result["success"] else None,
                "branch": checkout_branch,
            })
            if not checkout_result["success"]:
                track_result = _run_command(
                    ["git", "checkout", "-B", checkout_branch, f"{remote}/{checkout_branch}"],
                    timeout=60,
                )
                _append_step({
                    "step": "git_checkout_track",
                    "success": track_result["success"],
                    "output": track_result["stdout"],
                    "error": track_result["stderr"] if not track_result["success"] else None,
                    "branch": checkout_branch,
                    "remote": remote,
                })
                if not track_result["success"]:
                    errors.append(f"Não foi possível trocar para o branch '{checkout_branch}'.")
                    status["state"] = "failed"
                    return

            status["checked_out_branch"] = checkout_branch
            status["current_branch"] = checkout_branch
            current_branch = checkout_branch

        pull_cmd = ["git", "pull", remote]
        if target_branch:
            pull_cmd.append(target_branch)
        pull_result = _run_command(pull_cmd, timeout=120)
        _append_step({
            "step": "git_pull",
            "success": pull_result["success"],
            "output": pull_result["stdout"],
            "error": pull_result["stderr"] if not pull_result["success"] else None,
            "remote": remote,
            "branch": target_branch or current_branch,
        })
        if not pull_result["success"]:
            errors.append("Falha no git pull.")
            status["state"] = "failed"
            return

        diff_result = _run_command(["git", "diff", "--name-only", "HEAD@{1}", "HEAD"], timeout=15)
        changed_files: List[str] = []
        if diff_result["success"] and diff_result["stdout"]:
            changed_files = [
                line.strip()
                for line in diff_result["stdout"].splitlines()
                if line.strip()
            ]

        _append_step({
            "step": "git_diff_summary",
            "success": diff_result["success"],
            "output": diff_result["stdout"],
            "error": diff_result["stderr"] if not diff_result["success"] else None,
        })

        frontend_changed = any(
            f.startswith("src/") or f.startswith("public/") or
            f in ["package.json", "vite.config.js", "index.html"]
            for f in changed_files
        )
        backend_changed = any(f.startswith("beckend/") for f in changed_files)

        _append_step({
            "step": "detect_changes",
            "success": True,
            "frontend_changed": frontend_changed,
            "backend_changed": backend_changed,
            "changed_files": changed_files,
        })

        if frontend_changed:
            if "package.json" in changed_files:
                npm_install = _run_command(["npm", "install"], timeout=300)
                _append_step({
                    "step": "npm_install",
                    "success": npm_install["success"],
                    "output": npm_install["stdout"],
                    "error": npm_install["stderr"] if not npm_install["success"] else None,
                })
                if not npm_install["success"]:
                    errors.append("Falha ao instalar dependências do frontend.")

            build_result = _run_command(["npm", "run", "build"], timeout=300)
            _append_step({
                "step": "frontend_build",
                "success": build_result["success"],
                "output": build_result["stdout"][-500:] if build_result["stdout"] else "",
                "error": build_result["stderr"] if not build_result["success"] else None,
            })
            if build_result["success"]:
                dist_dir = PROJECT_ROOT / "dist"
                web_dir = BACKEND_DIR / "web"
                if dist_dir.exists():
                    if web_dir.exists():
                        shutil.rmtree(web_dir)
                    shutil.copytree(dist_dir, web_dir)
                    _append_step({
                        "step": "copy_build",
                        "success": True,
                        "message": "Build copiado para beckend/web",
                    })
            else:
                errors.append("Falha no build do frontend.")

        if backend_changed and "beckend/requirements.txt" in changed_files:
            pip_result = _run_command(
                ["bash", "-c", "cd beckend && source venv/bin/activate && pip install -r requirements.txt"],
                timeout=300,
            )
            _append_step({
                "step": "pip_install",
                "success": pip_result["success"],
                "output": pip_result["stdout"],
                "error": pip_result["stderr"] if not pip_result["success"] else None,
            })
            if not pip_result["success"]:
                errors.append("Falha ao instalar dependências do backend.")

        if errors:
            status["state"] = "failed"
            return

        status["state"] = "waiting_restart"
        status["completed"] = True
        status["finished_at"] = datetime.now().isoformat()
        status["frontend_changed"] = frontend_changed
        status["backend_changed"] = backend_changed
        _append_step({
            "step": "restart_services",
            "success": True,
            "message": "Reinício dos serviços agendado; pode levar alguns segundos.",
        })
        _trigger_restart_async()
    except Exception as exc:
        logger.exception("Erro durante job de atualização %s", job_id)
        errors.append(str(exc))
        steps.append({
            "step": "exception",
            "success": False,
            "error": str(exc),
        })
        status["state"] = "failed"
    finally:
        status["errors"] = errors
        status["steps"] = steps
        status.setdefault("finished_at", datetime.now().isoformat())
        status["completed"] = status.get("state") == "waiting_restart"
        _record_update_status(job_id, status)



@router.get("/service/status", response_model=APIResponse[dict])
async def get_service_status(
    current_user: UserModel = Depends(get_current_active_user),
) -> APIResponse[dict]:
    """Retorna o status detalhado de todos os serviços."""
    _check_admin(current_user)

    services = ["tiktok-backend", "tiktok-scheduler"]
    services_status = {}

    for service in services:
        # Pegar status do systemctl
        status_cmd = _run_command(
            ["systemctl", "is-active", f"{service}.service"],
            timeout=5
        )
        active_state = status_cmd["stdout"].strip()

        # Pegar informações detalhadas
        show_cmd = _run_command(
            ["systemctl", "show", f"{service}.service", "--no-page"],
            timeout=5
        )

        # Parse das informações
        info = {}
        if show_cmd["success"]:
            for line in show_cmd["stdout"].split("\n"):
                if "=" in line:
                    key, value = line.split("=", 1)
                    info[key] = value

        # Determinar status visual
        if active_state == "active":
            status = "running"
            color = "green"
        elif active_state == "inactive":
            status = "stopped"
            color = "gray"
        elif active_state == "failed":
            status = "failed"
            color = "red"
        elif active_state == "activating":
            status = "starting"
            color = "yellow"
        elif active_state == "deactivating":
            status = "stopping"
            color = "orange"
        else:
            status = "unknown"
            color = "gray"

        services_status[service] = {
            "name": service,
            "status": status,
            "color": color,
            "active_state": active_state,
            "load_state": info.get("LoadState", "unknown"),
            "sub_state": info.get("SubState", "unknown"),
            "main_pid": info.get("MainPID", "0"),
            "memory": info.get("MemoryCurrent", "0"),
            "uptime": info.get("ActiveEnterTimestamp", ""),
        }

    return success_response(
        data={
            "services": services_status,
            "timestamp": _run_command(["date", "+%s"], timeout=2)["stdout"].strip(),
        }
    )


@router.post("/service/{action}", response_model=APIResponse[dict])
async def manage_service(
    action: str,
    current_user: UserModel = Depends(get_current_active_user),
) -> APIResponse[dict]:
    """Gerencia serviços (start, stop, restart)."""
    _check_admin(current_user)

    valid_actions = ["start", "stop", "restart", "status"]
    if action not in valid_actions:
        raise_http_error(
            status.HTTP_400_BAD_REQUEST,
            error="invalid_action",
            message=f"Ação inválida. Use: {', '.join(valid_actions)}"
        )

    if not MANAGE_SH.exists():
        raise_http_error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            error="manage_script_not_found",
            message="Script manage.sh não encontrado"
        )

    logger.info(f"User {current_user.username} executando: manage.sh all {action}")
    result, sudo_failed = _run_manage_command(["all", action], timeout=60)

    response = success_response(
        message=f"Comando '{action}' executado",
        data={
            "action": action,
            "output": result["stdout"],
            "success": result["success"],
            "error": result["stderr"] if not result["success"] else None,
        }
    )

    if sudo_failed:
        response.data["sudo_config_required"] = True
        response.data["hint"] = "Execute sudo bash setup_sudo.sh para configurar sudo sem senha para manage.sh"

    return response


@router.get("/git/status", response_model=APIResponse[dict])
async def get_git_status(
    current_user: UserModel = Depends(get_current_active_user),
) -> APIResponse[dict]:
    """Retorna o status do repositório git."""
    _check_admin(current_user)

    # Git status
    status_result = _run_command(["git", "status", "--porcelain", "-b"], timeout=10)

    # Current branch
    branch_result = _run_command(["git", "rev-parse", "--abbrev-ref", "HEAD"], timeout=5)
    current_branch = branch_result["stdout"].strip() if branch_result["success"] else "unknown"

    # Last commit
    log_result = _run_command(
        ["git", "log", "-1", "--pretty=format:%H|%an|%ae|%at|%s"],
        timeout=5
    )

    last_commit = None
    if log_result["success"] and log_result["stdout"]:
        parts = log_result["stdout"].split("|")
        if len(parts) == 5:
            last_commit = {
                "hash": parts[0][:7],
                "author": parts[1],
                "email": parts[2],
                "timestamp": int(parts[3]),
                "message": parts[4],
            }

    # Check for updates
    fetch_result = _run_command(["git", "fetch", "origin", current_branch], timeout=30)

    behind_result = _run_command(
        ["git", "rev-list", "--count", f"HEAD..origin/{current_branch}"],
        timeout=10
    )
    commits_behind = 0
    if behind_result["success"]:
        try:
            commits_behind = int(behind_result["stdout"].strip())
        except ValueError:
            pass

    return success_response(
        data={
            "branch": current_branch,
            "status": status_result["stdout"],
            "last_commit": last_commit,
            "commits_behind": commits_behind,
            "has_updates": commits_behind > 0,
            "clean": "nothing to commit" in status_result["stdout"].lower(),
        }
    )


@router.get("/git/log", response_model=APIResponse[dict])
async def get_git_log(
    current_user: UserModel = Depends(get_current_active_user),
    limit: int = 10,
) -> APIResponse[dict]:
    """Retorna os últimos commits."""
    _check_admin(current_user)

    result = _run_command(
        ["git", "log", f"-{limit}", "--pretty=format:%H|%an|%ae|%at|%s"],
        timeout=10
    )

    commits = []
    if result["success"] and result["stdout"]:
        for line in result["stdout"].strip().split("\n"):
            parts = line.split("|")
            if len(parts) == 5:
                commits.append({
                    "hash": parts[0][:7],
                    "full_hash": parts[0],
                    "author": parts[1],
                    "email": parts[2],
                    "timestamp": int(parts[3]),
                    "message": parts[4],
                })

    return success_response(data={"commits": commits})


@router.get("/git/branches", response_model=APIResponse[dict])
async def list_git_branches(
    refresh: bool = False,
    current_user: UserModel = Depends(get_current_active_user),
) -> APIResponse[dict]:
    """Lista branches locais e remotos disponíveis."""
    _check_admin(current_user)

    steps = []

    if refresh:
        fetch = _run_command(["git", "fetch", "--all", "--prune"], timeout=120)
        steps.append({
            "step": "git_fetch",
            "success": fetch["success"],
            "output": fetch["stdout"],
            "error": fetch["stderr"] if not fetch["success"] else None,
        })
        if not fetch["success"]:
            return success_response(
                message="Falha ao atualizar branches",
                data={"steps": steps, "branches": None, "completed": False}
            )

    current_branch_cmd = _run_command(["git", "rev-parse", "--abbrev-ref", "HEAD"], timeout=5)
    current_branch = current_branch_cmd["stdout"].strip() if current_branch_cmd["success"] else "unknown"

    local_cmd = _run_command(
        [
            "git",
            "for-each-ref",
            "--format=%(refname:short)|%(objectname:short)|%(committerdate:iso8601)|%(subject)",
            "refs/heads",
        ],
        timeout=10,
    )
    remote_cmd = _run_command(
        [
            "git",
            "for-each-ref",
            "--format=%(refname:short)|%(objectname:short)|%(committerdate:iso8601)|%(subject)",
            "refs/remotes",
        ],
        timeout=10,
    )

    locals_list = _parse_branch_list(local_cmd["stdout"]) if local_cmd["success"] else []
    remotes_list = [
        item for item in _parse_branch_list(remote_cmd["stdout"]) if not item["name"].endswith("/HEAD")
    ] if remote_cmd["success"] else []

    return success_response(
        data={
            "current_branch": current_branch,
            "locals": locals_list,
            "remotes": remotes_list,
            "steps": steps,
        }
    )


@router.get("/git/config", response_model=APIResponse[dict])
async def get_git_config(
    current_user: UserModel = Depends(get_current_active_user),
) -> APIResponse[dict]:
    """Retorna configuração do Git (remote URL)."""
    _check_admin(current_user)

    # Listar remotes
    remotes_result = _run_command(["git", "remote", "-v"], timeout=5)

    remotes = {}
    if remotes_result["success"]:
        for line in remotes_result["stdout"].strip().split("\n"):
            if line:
                parts = line.split()
                if len(parts) >= 2:
                    name = parts[0]
                    url = parts[1]
                    if name not in remotes:
                        remotes[name] = url

    # Pegar branch atual
    branch_result = _run_command(["git", "rev-parse", "--abbrev-ref", "HEAD"], timeout=5)
    current_branch = branch_result["stdout"].strip() if branch_result["success"] else "unknown"

    return success_response(
        data={
            "remotes": remotes,
            "current_branch": current_branch,
        }
    )


@router.post("/git/config", response_model=APIResponse[dict])
async def update_git_config(
    config: GitConfigRequest,
    current_user: UserModel = Depends(get_current_active_user),
) -> APIResponse[dict]:
    """Atualiza a URL do remote Git."""
    _check_admin(current_user)

    logger.info(f"User {current_user.username} atualizando Git remote: {config.remote_name} -> {config.remote_url}")

    # Verificar se o remote existe
    check_result = _run_command(
        ["git", "remote", "get-url", config.remote_name],
        timeout=5
    )

    if check_result["success"]:
        # Remote existe, atualizar URL
        result = _run_command(
            ["git", "remote", "set-url", config.remote_name, config.remote_url],
            timeout=10
        )
        action = "atualizada"
    else:
        # Remote não existe, adicionar
        result = _run_command(
            ["git", "remote", "add", config.remote_name, config.remote_url],
            timeout=10
        )
        action = "adicionada"

    if not result["success"]:
        raise_http_error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            error="git_config_failed",
            message=f"Falha ao configurar remote: {result['stderr']}"
        )

    return success_response(
        message=f"URL do remote '{config.remote_name}' {action} com sucesso",
        data={
            "remote_name": config.remote_name,
            "remote_url": config.remote_url,
        }
    )


@router.post("/git/checkout", response_model=APIResponse[dict])
async def checkout_branch(
    request: GitCheckoutRequest,
    current_user: UserModel = Depends(get_current_active_user),
) -> APIResponse[dict]:
    """Altera o branch do repositório local."""
    _check_admin(current_user)

    target_branch = request.branch.strip()
    if not target_branch:
        raise_http_error(
            status.HTTP_400_BAD_REQUEST,
            error="invalid_branch",
            message="Informe o nome do branch que deseja utilizar."
        )

    steps = []
    errors = []

    status_result = _run_command(["git", "status", "--porcelain"], timeout=10)
    working_tree_dirty = status_result["success"] and status_result["stdout"].strip()

    if working_tree_dirty and not request.force:
        raise_http_error(
            status.HTTP_409_CONFLICT,
            error="uncommitted_changes",
            message="Há alterações locais não commitadas. Use force=true para permitir o checkout com stash automático."
        )

    if working_tree_dirty:
        stash = _run_command(["git", "stash"], timeout=30)
        steps.append({
            "step": "git_stash",
            "success": stash["success"],
            "output": stash["stdout"],
            "error": stash["stderr"] if not stash["success"] else None,
        })
        if not stash["success"]:
            errors.append("Falha ao executar git stash")
            return success_response(
                message="Checkout cancelado",
                data={"steps": steps, "errors": errors, "completed": False}
            )

    if request.fetch:
        fetch = _run_command(["git", "fetch", "--all", "--prune"], timeout=120)
        steps.append({
            "step": "git_fetch",
            "success": fetch["success"],
            "output": fetch["stdout"],
            "error": fetch["stderr"] if not fetch["success"] else None,
        })
        if not fetch["success"]:
            errors.append("Falha ao atualizar referências remotas")
            return success_response(
                message="Checkout cancelado",
                data={"steps": steps, "errors": errors, "completed": False}
            )

    checkout = _run_command(["git", "checkout", target_branch], timeout=60)
    steps.append({
        "step": "git_checkout",
        "success": checkout["success"],
        "output": checkout["stdout"],
        "error": checkout["stderr"] if not checkout["success"] else None,
    })

    if not checkout["success"]:
        # Tenta criar branch local acompanhando remoto
        remote_branch = target_branch if "/" in target_branch else f"origin/{target_branch}"
        local_branch = target_branch.split("/", 1)[1] if "/" in target_branch else target_branch
        create = _run_command(
            ["git", "checkout", "-b", local_branch, remote_branch],
            timeout=60
        )
        steps.append({
            "step": "git_checkout_track",
            "success": create["success"],
            "output": create["stdout"],
            "error": create["stderr"] if not create["success"] else None,
        })
        if not create["success"]:
            errors.append(f"Não foi possível trocar para o branch '{target_branch}'")
            return success_response(
                message="Checkout falhou",
                data={"steps": steps, "errors": errors, "completed": False}
            )

    current_branch_cmd = _run_command(["git", "rev-parse", "--abbrev-ref", "HEAD"], timeout=5)
    current_branch = current_branch_cmd["stdout"].strip() if current_branch_cmd["success"] else "unknown"

    status_after = _run_command(["git", "status", "--short"], timeout=10)

    steps.append({
        "step": "git_status",
        "success": status_after["success"],
        "output": status_after["stdout"],
    })

    return success_response(
        message=f"Branch ativo: {current_branch}",
        data={
            "steps": steps,
            "errors": errors,
            "completed": True,
            "current_branch": current_branch,
        }
    )


@router.post("/update", response_model=APIResponse[dict])
async def update_system(
    request: UpdateRequest,
    background_tasks: BackgroundTasks,
    current_user: UserModel = Depends(get_current_active_user),
) -> APIResponse[dict]:
    """
    Agenda a atualização do sistema a partir do GitHub e retorna o status inicial.
    """
    _check_admin(current_user)

    job_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    status = {
        "job_id": job_id,
        "request": request.model_dump(),
        "created_at": datetime.now().isoformat(),
        "state": "scheduled",
        "steps": [],
        "errors": [],
        "completed": False,
    }
    _record_update_status(job_id, status)

    background_tasks.add_task(_run_update_job, job_id, request.model_dump())

    return success_response(
        message="Atualização agendada. Acompanhe o status pelo endpoint /api/maintenance/update/status.",
        data={
            "job_id": job_id,
            "status": status,
        }
    )


@router.get("/update/status", response_model=APIResponse[dict])
async def get_update_status(
    job_id: Optional[str] = Query(None, description="Identificador do job de atualização"),
    current_user: UserModel = Depends(get_current_active_user),
) -> APIResponse[dict]:
    """Retorna o status da atualização mais recente ou de um job específico."""
    _check_admin(current_user)

    status_dir = _ensure_update_status_dir()
    target = status_dir / f"{job_id}.json" if job_id else status_dir / "latest.json"

    if not target.exists():
        return success_response(data={"job_id": job_id, "status": None})

    status_data = _read_json(target) or {}
    return success_response(data={"job_id": status_data.get("job_id"), "status": status_data})


@router.post("/backup/create", response_model=APIResponse[dict])
async def create_backup(
    current_user: UserModel = Depends(get_current_active_user),
) -> APIResponse[dict]:
    """Cria um backup do projeto (exceto vídeos e perfis)."""
    _check_admin(current_user)

    try:
        archive_path = _create_project_backup()
    except Exception as exc:
        logger.exception("Falha ao criar backup")
        raise_http_error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            error="backup_failed",
            message=str(exc),
        )

    stat = archive_path.stat()
    created_at = datetime.fromtimestamp(stat.st_mtime).isoformat()
    download_url = f"/api/maintenance/backup/download?file={archive_path.name}"

    return success_response(
        message="Backup criado com sucesso",
        data={
            "filename": archive_path.name,
            "size": stat.st_size,
            "created_at": created_at,
            "path": str(archive_path),
            "download_url": download_url,
            "preserved_directories": sorted(PRESERVE_DIRS),
        },
    )


@router.get("/backup/list", response_model=APIResponse[dict])
async def list_backups(
    current_user: UserModel = Depends(get_current_active_user),
) -> APIResponse[dict]:
    """Lista backups disponíveis."""
    _check_admin(current_user)

    backup_dir = _ensure_backups_dir()
    backups = []
    for path in sorted(backup_dir.glob("*.tar.gz"), key=lambda p: p.stat().st_mtime, reverse=True):
        stat = path.stat()
        backups.append({
            "filename": path.name,
            "size": stat.st_size,
            "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        })

    return success_response(data={"backups": backups})


@router.get("/backup/download")
async def download_backup(
    file: str = Query(..., description="Nome do arquivo de backup"),
    current_user: UserModel = Depends(get_current_active_user),
):
    """Baixa um backup existente."""
    _check_admin(current_user)

    backup_dir = _ensure_backups_dir()
    safe_name = Path(file).name
    target = backup_dir / safe_name
    if not target.exists() or not target.is_file():
        raise_http_error(
            status.HTTP_404_NOT_FOUND,
            error="backup_not_found",
            message="Backup não encontrado",
        )

    return FileResponse(
        target,
        media_type="application/gzip",
        filename=target.name,
    )


@router.delete("/backup/delete", response_model=APIResponse[dict])
async def delete_backup(
    file: str = Query(..., description="Nome do arquivo de backup a excluir"),
    current_user: UserModel = Depends(get_current_active_user),
) -> APIResponse[dict]:
    """Remove um arquivo de backup existente."""
    _check_admin(current_user)

    backup_dir = _ensure_backups_dir()
    safe_name = Path(file).name
    target = backup_dir / safe_name

    if not target.exists() or not target.is_file():
        raise_http_error(
            status.HTTP_404_NOT_FOUND,
            error="backup_not_found",
            message="Backup não encontrado",
        )

    try:
        target.unlink()
    except Exception as exc:
        raise_http_error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            error="backup_delete_failed",
            message=str(exc),
        )

    return success_response(
        message="Backup removido com sucesso",
        data={"filename": safe_name},
    )


@router.post("/backup/restore", response_model=APIResponse[dict])
async def restore_backup(
    background_tasks: BackgroundTasks,
    uploaded_file: UploadFile = File(...),
    current_user: UserModel = Depends(get_current_active_user),
) -> APIResponse[dict]:
    """
    Restaura o sistema a partir de um backup enviado.
    Após restaurar os arquivos, executa obrigatoriamente:
    - npm run build (frontend)
    - manage.sh all restart (serviços backend/scheduler)
    """
    _check_admin(current_user)

    if not uploaded_file.filename:
        raise_http_error(
            status.HTTP_400_BAD_REQUEST,
            error="invalid_backup",
            message="Nome de arquivo inválido",
        )

    backup_dir = _ensure_backups_dir()
    safe_name = Path(uploaded_file.filename).name
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    archive_path = backup_dir / f"upload-{timestamp}-{safe_name}"

    try:
        with archive_path.open("wb") as dest:
            while True:
                chunk = await uploaded_file.read(1024 * 1024)
                if not chunk:
                    break
                dest.write(chunk)
    finally:
        await uploaded_file.close()

    job_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    status = {
        "job_id": job_id,
        "archive": archive_path.name,
        "created_at": datetime.now().isoformat(),
        "state": "scheduled",
        "steps": [],
        "errors": [],
        "completed": False,
    }
    _record_restore_status(job_id, status)

    background_tasks.add_task(_run_restore_job, job_id, archive_path)

    return success_response(
        message="Restauração agendada. Acompanhe o status pelo endpoint /api/maintenance/backup/restore/status.",
        data={
            "job_id": job_id,
            "status": status,
        },
    )


@router.get("/backup/restore/status", response_model=APIResponse[dict])
async def get_restore_status(
    job_id: Optional[str] = Query(None, description="Identificador do job de restauração"),
    current_user: UserModel = Depends(get_current_active_user),
) -> APIResponse[dict]:
    """Retorna o status da restauração mais recente ou de um job específico."""
    _check_admin(current_user)

    status_dir = _ensure_restore_status_dir()
    target = status_dir / f"{job_id}.json" if job_id else status_dir / "latest.json"

    if not target.exists():
        return success_response(
            data={
                "job_id": job_id,
                "status": None,
            }
        )

    status_data = _read_json(target) or {}
    return success_response(
        data={
            "job_id": status_data.get("job_id"),
            "status": status_data,
        }
    )


@router.get("/logs/tail", response_model=APIResponse[dict])
async def tail_logs(
    current_user: UserModel = Depends(get_current_active_user),
    service: str = "backend",
    lines: int = 50,
) -> APIResponse[dict]:
    """Retorna as últimas linhas dos logs."""
    _check_admin(current_user)

    log_file = None
    if service == "backend":
        log_file = BACKEND_DIR / "logs" / "backend.log"
    elif service == "scheduler":
        log_file = BACKEND_DIR / "logs" / "scheduler.log"
    elif service == "backend-error":
        log_file = BACKEND_DIR / "logs" / "backend-error.log"
    elif service == "scheduler-error":
        log_file = BACKEND_DIR / "logs" / "scheduler-error.log"
    else:
        raise_http_error(
            status.HTTP_400_BAD_REQUEST,
            error="invalid_service",
            message="Serviço inválido"
        )

    if not log_file or not log_file.exists():
        return success_response(data={"logs": "", "service": service})

    try:
        result = _run_command(["tail", f"-n{lines}", str(log_file)], timeout=10)
        return success_response(
            data={
                "logs": result["stdout"],
                "service": service,
                "lines": lines,
            }
        )
    except Exception as e:
        raise_http_error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            error="log_read_failed",
            message=str(e)
        )


@router.post("/reinstall", response_model=APIResponse[dict])
async def complete_reinstall(
    current_user: UserModel = Depends(get_current_active_user),
) -> APIResponse[dict]:
    """
    Reinstalação completa do sistema:
    - Atualiza código do GitHub
    - LIMPA todos os dados do usuário
    - Reinicia serviços
    """
    _check_admin(current_user)

    logger.warning(f"User {current_user.username} iniciando REINSTALAÇÃO COMPLETA - TODOS OS DADOS SERÃO APAGADOS!")

    steps = []
    errors = []

    # 1. Git stash + pull
    logger.info("Limpando mudanças locais...")
    stash_result = _run_command(["git", "stash"], cwd=PROJECT_ROOT, timeout=30)
    steps.append({
        "step": "git_stash",
        "success": True,
        "message": "Mudanças locais guardadas"
    })

    remote, target_branch, current_branch = _resolve_git_pull_target()
    pull_cmd = ["git", "pull", remote]
    if target_branch:
        pull_cmd.append(target_branch)

    pull_result = _run_command(pull_cmd, cwd=PROJECT_ROOT, timeout=120)
    steps.append({
        "step": "git_pull",
        "success": pull_result["success"],
        "output": pull_result["stdout"],
        "error": pull_result["stderr"] if not pull_result["success"] else None,
        "remote": remote,
        "branch": target_branch or current_branch,
    })

    if not pull_result["success"]:
        errors.append("Falha no git pull")

    # 2. LIMPAR DADOS DO USUÁRIO
    logger.warning("LIMPANDO TODOS OS DADOS DO USUÁRIO...")

    # Limpar vídeos
    videos_dir = PROJECT_ROOT / "videos"
    if videos_dir.exists():
        shutil.rmtree(videos_dir, ignore_errors=True)
        videos_dir.mkdir(parents=True, exist_ok=True)
        steps.append({"step": "clean_videos", "success": True, "message": "Vídeos apagados"})

    # Limpar posted
    posted_dir = PROJECT_ROOT / "posted"
    if posted_dir.exists():
        shutil.rmtree(posted_dir, ignore_errors=True)
        posted_dir.mkdir(parents=True, exist_ok=True)
        steps.append({"step": "clean_posted", "success": True, "message": "Histórico de posts apagado"})

    # Limpar profiles (Chrome)
    profiles_dir = PROJECT_ROOT / "profiles"
    if profiles_dir.exists():
        shutil.rmtree(profiles_dir, ignore_errors=True)
        profiles_dir.mkdir(parents=True, exist_ok=True)
        steps.append({"step": "clean_profiles", "success": True, "message": "Perfis do Chrome apagados"})

    # Limpar state
    state_dir = PROJECT_ROOT / "state"
    if state_dir.exists():
        # Manter estrutura mas limpar conteúdo
        for item in state_dir.glob("*"):
            if item.is_file():
                item.unlink()
        steps.append({"step": "clean_state", "success": True, "message": "Arquivos de estado limpos"})

    # 3. Build do frontend
    logger.info("Fazendo build do frontend...")
    build_result = _run_command(["npm", "run", "build"], cwd=PROJECT_ROOT, timeout=300)
    steps.append({
        "step": "frontend_build",
        "success": build_result["success"],
        "output": build_result["stdout"][-500:] if build_result["stdout"] else "",
    })

    if not build_result["success"]:
        errors.append("Falha no build do frontend")

    # 4. Reiniciar serviços (com sudo)
    logger.info("Reiniciando serviços...")
    restart_result, sudo_failed = _run_manage_command(["all", "restart"], timeout=60)

    if sudo_failed:
        logger.warning("Falha ao executar manage.sh com sudo - execute sudo bash setup_sudo.sh")

    steps.append({
        "step": "restart_services",
        "success": restart_result["success"],
        "output": restart_result["stdout"],
        "error": restart_result["stderr"] if not restart_result["success"] else None,
        "sudo_config_required": sudo_failed,
        "message": "Serviços reiniciados" if restart_result["success"] else "Falha ao reiniciar - configure sudo com setup_sudo.sh",
    })

    if not restart_result["success"]:
        error_msg = "Falha ao reiniciar serviços - você pode precisar reiniciar manualmente"
        if sudo_failed:
            error_msg += " (execute sudo bash setup_sudo.sh)"
        errors.append(error_msg)

    completed = len(errors) == 0
    message = "Reinstalação completa concluída" if completed else "Reinstalação completada com erros"

    logger.info(f"Reinstalação completa finalizada. Sucesso: {completed}")

    return success_response(
        message=message,
        data={
            "steps": steps,
            "errors": errors,
            "completed": completed,
        }
    )


@router.post("/migrate-to-simple", response_model=APIResponse[dict])
async def migrate_to_simple_system(
    current_user: UserModel = Depends(get_current_active_user),
) -> APIResponse[dict]:
    """
    Migra para o sistema simplificado:
    1. Faz backup dos arquivos originais
    2. Substitui driver.py, cookies.py, uploader.py pelos simplificados
    3. Reinicia serviços
    """
    _check_admin(current_user)

    logger.info(f"User {current_user.username} iniciando MIGRAÇÃO PARA SISTEMA SIMPLIFICADO")

    steps = []
    errors = []

    # 1. Verificar se arquivos simplificados existem
    simple_files = {
        "driver_simple.py": BACKEND_DIR / "src" / "driver_simple.py",
        "cookies_simple.py": BACKEND_DIR / "src" / "cookies_simple.py",
        "uploader_simple.py": BACKEND_DIR / "src" / "uploader_simple.py",
    }

    for name, path in simple_files.items():
        if not path.exists():
            errors.append(f"Arquivo {name} não encontrado. Execute git pull primeiro.")
            return success_response(
                message="Migração cancelada - arquivos simplificados não encontrados",
                data={"steps": steps, "errors": errors, "completed": False}
            )

    steps.append({
        "step": "check_files",
        "success": True,
        "message": "Arquivos simplificados encontrados"
    })

    # 2. Criar backup dos arquivos originais
    backup_files = {
        "driver.py": BACKEND_DIR / "src" / "driver.py",
        "cookies.py": BACKEND_DIR / "src" / "cookies.py",
        "uploader.py": BACKEND_DIR / "src" / "uploader.py",
    }

    for name, path in backup_files.items():
        backup_path = path.parent / f"{path.stem}_old_backup{path.suffix}"
        if path.exists() and not backup_path.exists():
            try:
                shutil.copy2(path, backup_path)
                logger.info(f"Backup criado: {backup_path}")
            except Exception as e:
                errors.append(f"Falha ao criar backup de {name}: {str(e)}")
                return success_response(
                    message="Migração cancelada - falha no backup",
                    data={"steps": steps, "errors": errors, "completed": False}
                )

    steps.append({
        "step": "backup",
        "success": True,
        "message": "Backup dos arquivos originais criado"
    })

    # 3. Substituir arquivos pelos simplificados
    for simple_name, simple_path in simple_files.items():
        target_name = simple_name.replace("_simple", "")
        target_path = simple_path.parent / target_name

        try:
            shutil.copy2(simple_path, target_path)
            logger.info(f"Arquivo substituído: {target_path}")
        except Exception as e:
            errors.append(f"Falha ao substituir {target_name}: {str(e)}")
            return success_response(
                message="Migração falhou - erro ao substituir arquivos",
                data={"steps": steps, "errors": errors, "completed": False}
            )

    steps.append({
        "step": "replace_files",
        "success": True,
        "message": "Arquivos substituídos com sucesso",
        "replaced": ["driver.py", "cookies.py", "uploader.py"]
    })

    # 4. Reiniciar serviços
    logger.info("Reiniciando serviços com código simplificado...")
    restart_result, sudo_failed = _run_manage_command(["all", "restart"], timeout=60)

    steps.append({
        "step": "restart_services",
        "success": restart_result["success"],
        "output": restart_result["stdout"],
        "error": restart_result["stderr"] if not restart_result["success"] else None,
        "sudo_config_required": sudo_failed,
    })

    if not restart_result["success"]:
        error_msg = "Falha ao reiniciar serviços"
        if sudo_failed:
            error_msg += " - execute sudo bash setup_sudo.sh no servidor"
        errors.append(error_msg)

    completed = len(errors) == 0
    message = "Migração para sistema simplificado concluída! Monitore os logs." if completed else "Migração completada com erros"

    logger.info(f"Migração para sistema simplificado finalizada. Sucesso: {completed}")

    return success_response(
        message=message,
        data={
            "steps": steps,
            "errors": errors,
            "completed": completed,
            "backup_location": "beckend/src/*_old_backup.py",
            "next_steps": [
                "Monitore os logs para verificar funcionamento",
                "Procure por ausência de 'Lock global adquirido'",
                "Uploads devem completar em ~50s (antes: 3-5min)",
                "Se houver problemas, use rollback"
            ]
        }
    )


@router.post("/rollback-simple", response_model=APIResponse[dict])
async def rollback_from_simple_system(
    current_user: UserModel = Depends(get_current_active_user),
) -> APIResponse[dict]:
    """
    Faz rollback do sistema simplificado para o sistema original.
    Restaura arquivos do backup *_old_backup.py
    """
    _check_admin(current_user)

    logger.info(f"User {current_user.username} iniciando ROLLBACK DO SISTEMA SIMPLIFICADO")

    steps = []
    errors = []

    # 1. Verificar se backups existem
    backup_files = {
        "driver_old_backup.py": BACKEND_DIR / "src" / "driver_old_backup.py",
        "cookies_old_backup.py": BACKEND_DIR / "src" / "cookies_old_backup.py",
        "uploader_old_backup.py": BACKEND_DIR / "src" / "uploader_old_backup.py",
    }

    for name, path in backup_files.items():
        if not path.exists():
            errors.append(f"Backup {name} não encontrado")

    if errors:
        return success_response(
            message="Rollback cancelado - backups não encontrados",
            data={"steps": steps, "errors": errors, "completed": False}
        )

    steps.append({
        "step": "check_backups",
        "success": True,
        "message": "Backups encontrados"
    })

    # 2. Restaurar arquivos do backup
    target_files = {
        "driver_old_backup.py": "driver.py",
        "cookies_old_backup.py": "cookies.py",
        "uploader_old_backup.py": "uploader.py",
    }

    for backup_name, target_name in target_files.items():
        backup_path = BACKEND_DIR / "src" / backup_name
        target_path = BACKEND_DIR / "src" / target_name

        try:
            shutil.copy2(backup_path, target_path)
            logger.info(f"Arquivo restaurado: {target_path}")
        except Exception as e:
            errors.append(f"Falha ao restaurar {target_name}: {str(e)}")
            return success_response(
                message="Rollback falhou",
                data={"steps": steps, "errors": errors, "completed": False}
            )

    steps.append({
        "step": "restore_files",
        "success": True,
        "message": "Arquivos originais restaurados",
        "restored": ["driver.py", "cookies.py", "uploader.py"]
    })

    # 3. Reiniciar serviços
    logger.info("Reiniciando serviços com código original...")
    restart_result, sudo_failed = _run_manage_command(["all", "restart"], timeout=60)

    steps.append({
        "step": "restart_services",
        "success": restart_result["success"],
        "output": restart_result["stdout"],
        "error": restart_result["stderr"] if not restart_result["success"] else None,
        "sudo_config_required": sudo_failed,
    })

    if not restart_result["success"]:
        error_msg = "Falha ao reiniciar serviços"
        if sudo_failed:
            error_msg += " - execute sudo bash setup_sudo.sh no servidor"
        errors.append(error_msg)

    completed = len(errors) == 0
    message = "Rollback concluído! Sistema voltou ao estado original." if completed else "Rollback completado com erros"

    logger.info(f"Rollback do sistema simplificado finalizado. Sucesso: {completed}")

    return success_response(
        message=message,
        data={
            "steps": steps,
            "errors": errors,
            "completed": completed,
        }
    )

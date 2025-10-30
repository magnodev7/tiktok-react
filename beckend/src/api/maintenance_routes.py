"""Rotas de manutenção e gerenciamento do sistema."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Optional, Tuple, List
import logging

from fastapi import APIRouter, Depends, HTTPException, status
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


class ServiceActionRequest(BaseModel):
    action: str  # start, stop, restart, status


class UpdateRequest(BaseModel):
    force: bool = False


class GitConfigRequest(BaseModel):
    remote_url: str
    remote_name: str = "origin"


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
    result = _run_command(["bash", str(MANAGE_SH), "all", action], timeout=60)

    return success_response(
        message=f"Comando '{action}' executado",
        data={
            "action": action,
            "output": result["stdout"],
            "success": result["success"],
            "error": result["stderr"] if not result["success"] else None,
        }
    )


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


@router.post("/update", response_model=APIResponse[dict])
async def update_system(
    request: UpdateRequest,
    current_user: UserModel = Depends(get_current_active_user),
) -> APIResponse[dict]:
    """
    Atualiza o sistema a partir do GitHub:
    1. Faz git pull
    2. Detecta arquivos alterados
    3. Se frontend mudou: executa npm run build
    4. Se backend mudou: reinicia serviços
    """
    _check_admin(current_user)

    steps = []
    errors = []

    # 1. Verificar se há mudanças locais não commitadas
    status_result = _run_command(["git", "status", "--porcelain"], timeout=10)
    if status_result["success"] and status_result["stdout"].strip():
        if not request.force:
            raise_http_error(
                status.HTTP_409_CONFLICT,
                error="uncommitted_changes",
                message="Há alterações locais não commitadas. Use force=true para sobrescrever."
            )
        # Faz stash das mudanças locais
        stash_result = _run_command(["git", "stash"], timeout=30)
        steps.append({
            "step": "stash",
            "success": stash_result["success"],
            "message": "Mudanças locais guardadas temporariamente"
        })

    # 2. Git pull
    logger.info(f"User {current_user.username} iniciando git pull")
    pull_result = _run_command(["git", "pull", "origin"], timeout=120)
    steps.append({
        "step": "git_pull",
        "success": pull_result["success"],
        "output": pull_result["stdout"],
        "error": pull_result["stderr"] if not pull_result["success"] else None,
    })

    if not pull_result["success"]:
        errors.append("Falha no git pull")
        return success_response(
            message="Atualização falhou",
            data={"steps": steps, "errors": errors, "completed": False}
        )

    # 3. Detectar arquivos alterados
    changed_files = []
    for line in pull_result["stdout"].split("\n"):
        line = line.strip()
        if line and "|" in line:
            file_path = line.split("|")[0].strip()
            changed_files.append(file_path)

    frontend_changed = any(
        f.startswith("src/") or f.startswith("public/") or
        f in ["package.json", "vite.config.js", "index.html"]
        for f in changed_files
    )
    backend_changed = any(
        f.startswith("beckend/") for f in changed_files
    )

    steps.append({
        "step": "detect_changes",
        "success": True,
        "frontend_changed": frontend_changed,
        "backend_changed": backend_changed,
        "changed_files": changed_files,
    })

    # 4. Build do frontend se necessário
    if frontend_changed:
        logger.info("Frontend alterado, executando build...")

        # Instalar dependências se package.json mudou
        if "package.json" in changed_files:
            npm_install = _run_command(["npm", "install"], timeout=300)
            steps.append({
                "step": "npm_install",
                "success": npm_install["success"],
                "message": "Dependências do frontend instaladas"
            })
            if not npm_install["success"]:
                errors.append("Falha ao instalar dependências")

        # Build
        build_result = _run_command(["npm", "run", "build"], timeout=300)
        steps.append({
            "step": "frontend_build",
            "success": build_result["success"],
            "output": build_result["stdout"][-500:] if build_result["stdout"] else "",
        })

        if not build_result["success"]:
            errors.append("Falha no build do frontend")
        else:
            # Copiar para beckend/web
            dist_dir = PROJECT_ROOT / "dist"
            web_dir = BACKEND_DIR / "web"

            if dist_dir.exists():
                import shutil
                if web_dir.exists():
                    shutil.rmtree(web_dir)
                shutil.copytree(dist_dir, web_dir)
                steps.append({
                    "step": "copy_build",
                    "success": True,
                    "message": "Build copiado para beckend/web"
                })

    # 5. Reiniciar backend se necessário
    if backend_changed:
        logger.info("Backend alterado, reiniciando serviços...")

        # Verificar se requirements.txt mudou
        if "beckend/requirements.txt" in changed_files:
            # Instalar dependências Python
            pip_result = _run_command(
                ["bash", "-c", "cd beckend && source venv/bin/activate && pip install -r requirements.txt"],
                timeout=300
            )
            steps.append({
                "step": "pip_install",
                "success": pip_result["success"],
                "message": "Dependências Python instaladas"
            })

        # Reiniciar serviços
        restart_result = _run_command(
            ["bash", str(MANAGE_SH), "all", "restart"],
            timeout=60
        )
        steps.append({
            "step": "restart_services",
            "success": restart_result["success"],
            "output": restart_result["stdout"],
        })

        if not restart_result["success"]:
            errors.append("Falha ao reiniciar serviços")

    completed = len(errors) == 0
    message = "Sistema atualizado com sucesso" if completed else "Atualização completada com erros"

    return success_response(
        message=message,
        data={
            "steps": steps,
            "errors": errors,
            "completed": completed,
            "frontend_changed": frontend_changed,
            "backend_changed": backend_changed,
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

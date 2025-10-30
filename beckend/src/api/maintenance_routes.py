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

    pull_result = _run_command(["git", "pull", "origin"], cwd=PROJECT_ROOT, timeout=120)
    steps.append({
        "step": "git_pull",
        "success": pull_result["success"],
        "output": pull_result["stdout"],
        "error": pull_result["stderr"] if not pull_result["success"] else None,
    })

    if not pull_result["success"]:
        errors.append("Falha no git pull")

    # 2. LIMPAR DADOS DO USUÁRIO
    logger.warning("LIMPANDO TODOS OS DADOS DO USUÁRIO...")

    import shutil

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
    import shutil
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
    import shutil
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

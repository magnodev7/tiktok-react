"""Rotas de vídeos, uploads e planner."""

from __future__ import annotations

import json
import os
import shutil
import logging
from pathlib import Path
from typing import List, Optional, Set, Tuple

import datetime as dt
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from src.auth import (
    APIKeyModel,
    get_current_active_user,
    get_current_user_or_api_key,
    get_db,
)
from src.models import User as UserModel
from src.repositories import TikTokAccountRepository
from src.scheduler import TikTokScheduler  # apenas anotação
from src.planner import plan_all_accounts, preview_schedule
from src import log_service
from src.timezone_utils import get_app_timezone, now as tz_now

from .schemas import APIResponse
from .utils import raise_http_error, success_response
from .models import PostNowRequest, ScheduleUpdate, RescheduleVideoRequest
from src.scheduler import _update_sidecars_for


logger = logging.getLogger(__name__)

router = APIRouter(tags=["videos"])

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_VIDEOS_DIR = PROJECT_ROOT / "videos"
DEFAULT_POSTED_DIR = PROJECT_ROOT / "posted"
DEFAULT_USERDATA_DIR = PROJECT_ROOT / "profiles"
DEFAULT_STATE_DIR = PROJECT_ROOT / "state"


def _project_path(raw: Optional[str], default: Path) -> Path:
    """
    Normaliza caminhos configurados para sempre ficarem dentro do projeto.
    Se o caminho não for absoluto, trata como relativo à raiz do projeto.
    Também evita que arquivos sejam salvos em subpastas de src/.
    """
    if not raw:
        return default

    candidate = Path(raw).expanduser()
    if not candidate.is_absolute():
        candidate = (PROJECT_ROOT / candidate).resolve()
    else:
        candidate = candidate.resolve()

    src_root = (PROJECT_ROOT / "src").resolve()
    try:
        # Python 3.9+: evita salvar dentro de src/
        if candidate.is_relative_to(src_root):
            return default
    except AttributeError:
        if str(candidate).startswith(str(src_root)):
            return default
    except ValueError:
        # Caminho fora do projeto, permitido
        pass

    return candidate


def _ensure_dir(path: Path, fallback: Path) -> Path:
    try:
        path.mkdir(parents=True, exist_ok=True)
        return path
    except OSError as exc:
        if path.resolve() == fallback.resolve():
            raise
        logger.warning("Não foi possível usar diretório %s (%s); usando fallback %s", path, exc, fallback)
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


def _env_path(*keys: str, default: Path) -> Path:
    for key in keys:
        raw = os.getenv(key)
        if raw:
            return _project_path(raw, default)
    return default


VIDEOS_DIR = _ensure_dir(_env_path("BASE_VIDEOS_DIR", "BASE_VIDEO_DIR", default=DEFAULT_VIDEOS_DIR), DEFAULT_VIDEOS_DIR)
POSTED_DIR = _ensure_dir(_env_path("BASE_POSTED_DIR", "BASE_POST_DIR", default=DEFAULT_POSTED_DIR), DEFAULT_POSTED_DIR)
USERDATA_DIR = _ensure_dir(_project_path(os.getenv("BASE_USERDATA_DIR"), DEFAULT_USERDATA_DIR), DEFAULT_USERDATA_DIR)
STATE_DIR = _ensure_dir(_project_path(os.getenv("BASE_STATE_DIR"), DEFAULT_STATE_DIR), DEFAULT_STATE_DIR)

SCHEDULES_JSON = STATE_DIR / "schedules.json"
LOGS_JSON = STATE_DIR / "logs.json"
APP_TZ = get_app_timezone()  # Usa America/Sao_Paulo por padrão

if not SCHEDULES_JSON.exists():
    SCHEDULES_JSON.write_text(json.dumps([], ensure_ascii=False), encoding="utf-8")

if not LOGS_JSON.exists():
    LOGS_JSON.write_text(json.dumps({"logs": []}, ensure_ascii=False), encoding="utf-8")


def _add_log(message: str, level: str = "info", user_id: Optional[int] = None, account_name: Optional[str] = None) -> None:
    log_service.add_log(message=message, level=level, user_id=user_id, account_name=account_name, module="api-videos")


def _normalise_hhmm(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    raw = value.strip()
    if not raw:
        return None
    try:
        # Suporta datetime-local (YYYY-MM-DDTHH:MM[ss])
        dt_local = dt.datetime.fromisoformat(raw)
        return dt_local.strftime("%H:%M")
    except Exception:
        pass
    candidates = [raw]
    if len(raw) == 8 and raw.count(":") == 2:
        candidates.append(raw[:5])
    if len(raw) == 2 and raw.isdigit():
        candidates.append(f"{int(raw):02d}:00")
    for test in candidates:
        if len(test) == 5 and test[2] == ":" and test[:2].isdigit() and test[3:].isdigit():
            hh, mm = int(test[:2]), int(test[3:])
            if 0 <= hh < 24 and 0 <= mm < 60:
                return f"{hh:02d}:{mm:02d}"
    return None


def _acc_dir(base: Path, account: str) -> Path:
    d = base / account
    d.mkdir(parents=True, exist_ok=True)
    return d


def _read_schedules() -> List[str]:
    try:
        data = json.loads(SCHEDULES_JSON.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and "schedules" in data:
            return [str(x) for x in data["schedules"]]
    except Exception:
        pass
    default = ["08:00", "10:00", "12:00", "14:00", "16:00", "18:00", "20:00", "22:00"]
    SCHEDULES_JSON.write_text(json.dumps(default, ensure_ascii=False, indent=2), encoding="utf-8")
    return default


def _write_schedules(arr: List[str]) -> None:
    clean = []
    for x in arr:
        x = str(x).strip()
        if len(x) == 5 and x[2] == ":" and x[:2].isdigit() and x[3:].isdigit():
            clean.append(x)
    SCHEDULES_JSON.write_text(json.dumps(clean, ensure_ascii=False, indent=2), encoding="utf-8")


def _occupied_slots_for_date(account: str, date_ymd: str) -> Set[str]:
    acc_dir = _acc_dir(VIDEOS_DIR, account)
    taken: Set[str] = set()
    for f in acc_dir.glob("*.mp4"):
        meta = f.with_suffix(".json")
        if meta.exists():
            try:
                data = json.loads(meta.read_text(encoding="utf-8"))
            except Exception:
                data = {}
            scheduled_at = data.get("scheduled_at")
            if scheduled_at:
                try:
                    dti = dt.datetime.fromisoformat(scheduled_at)
                    if dti.tzinfo:
                        dti = dti.astimezone(APP_TZ)
                    else:
                        dti = dti.replace(tzinfo=APP_TZ)
                    if dti.strftime("%Y-%m-%d") == date_ymd:
                        taken.add(dti.strftime("%H:%M"))
                except Exception:
                    pass
        legacy_meta = f.with_suffix(".meta.json")
        if legacy_meta.exists():
            try:
                data = json.loads(legacy_meta.read_text(encoding="utf-8"))
                slot = (data.get("schedule_time") or "").strip()
                if len(slot) == 5:
                    taken.add(slot)
            except Exception:
                pass
    return taken


def _find_next_free_slot(account: str, schedules: List[str]) -> Tuple[str, str]:
    now_local = dt.datetime.now(APP_TZ)
    ordered = sorted(set(schedules))
    for d in range(0, 31):
        day = (now_local + dt.timedelta(days=d))
        ymd = day.strftime("%Y-%m-%d")
        taken = _occupied_slots_for_date(account, ymd)
        for hhmm in ordered:
            if d == 0 and hhmm <= now_local.strftime("%H:%M"):
                continue
            if hhmm not in taken:
                return ymd, hhmm
    tomorrow = (now_local + dt.timedelta(days=1)).strftime("%Y-%m-%d")
    return tomorrow, (ordered[0] if ordered else "08:00")


def _find_next_free_slot_for_account(account_name: str, account_id: int, db: Session) -> Tuple[str, str]:
    from src.repositories import PostingScheduleRepository

    schedules = PostingScheduleRepository.get_active_schedules(db, account_id)
    time_slots = [s.time_slot for s in schedules] or ["08:00", "10:00", "12:00", "14:00", "16:00", "18:00", "20:00", "22:00"]

    now_local = dt.datetime.now(APP_TZ)
    ordered = sorted(set(time_slots))

    for d in range(0, 31):
        day = (now_local + dt.timedelta(days=d))
        ymd = day.strftime("%Y-%m-%d")
        taken = _occupied_slots_for_date(account_name, ymd)

        for hhmm in ordered:
            if d == 0 and hhmm <= now_local.strftime("%H:%M"):
                continue
            if hhmm not in taken:
                return ymd, hhmm

    tomorrow = (now_local + dt.timedelta(days=1)).strftime("%Y-%m-%d")
    return tomorrow, (ordered[0] if ordered else "08:00")


def _videos_handler(account: str) -> dict:
    if not account or not account.strip():
        raise HTTPException(status_code=400, detail="Nome da conta é obrigatório")
    acc = account.strip()
    vdir = _acc_dir(VIDEOS_DIR, acc)
    files = [f.name for f in sorted(vdir.glob("*.mp4")) if f.is_file()]
    return {"account": acc, "videos": files}


def _scheduled_handler(account: str) -> dict:
    if not account or not account.strip():
        raise HTTPException(status_code=400, detail="Nome da conta é obrigatório")

    acc = account.strip()
    vdir = _acc_dir(VIDEOS_DIR, acc)
    items = []

    for f in sorted(vdir.glob("*.mp4")):
        meta = f.with_suffix(".json")
        if meta.exists():
            try:
                data = json.loads(meta.read_text(encoding="utf-8"))
            except Exception:
                data = {}
            scheduled_at = data.get("scheduled_at")
            schedule_time = data.get("schedule_time")
            timezone = data.get("timezone")
            when = scheduled_at or schedule_time
            if when:
                items.append(
                    {
                        "video_path": f.name,
                        "status": data.get("status", "pending"),
                        "when": when,
                        "scheduled_at": scheduled_at,
                        "schedule_time": schedule_time,
                        "timezone": timezone,
                        "description": data.get("description") or data.get("caption") or "",
                        "hashtags": data.get("hashtags") or "",
                        "uploaded_at": data.get("uploaded_at"),
                        "account": acc,
                    }
                )

    return {"account": acc, "scheduled_videos": items}


def _safe_move(src: Path, dst_dir: Path) -> Path:
    dst_dir.mkdir(parents=True, exist_ok=True)
    target = dst_dir / src.name
    if target.exists():
        stem = src.stem
        suf = src.suffix
        target = dst_dir / f"{stem}_{tz_now().strftime('%Y%m%d%H%M%S')}{suf}"
    src.replace(target)
    return target


def _sidecars(p: Path):
    root = p.with_suffix("")
    return [root.with_suffix(".json"), root.with_suffix(".meta.json"), root.with_suffix(".txt")]


async def _upload_handler(
    video: UploadFile,
    description: Optional[str],
    hashtags: Optional[str],
    account: str,
    schedule_time: Optional[str],
    delete_after: Optional[str],
    scheduled_at_iso: Optional[str],
    db: Session,
) -> dict:
    if not account or not account.strip():
        raise_http_error(status.HTTP_400_BAD_REQUEST, error="account_required", message="Nome da conta é obrigatório")

    acc = account.strip()
    vdir = _acc_dir(VIDEOS_DIR, acc)

    dst = vdir / video.filename
    _add_log(f"Salvando vídeo em: {dst}", account_name=acc)
    with dst.open("wb") as out:
        shutil.copyfileobj(video.file, out)

    schedules = _read_schedules()
    final_hhmm: Optional[str] = None
    final_iso: Optional[str] = None

    if scheduled_at_iso:
        try:
            dti = dt.datetime.fromisoformat(scheduled_at_iso)
            if not dti.tzinfo:
                dti = dti.replace(tzinfo=APP_TZ)
            else:
                dti = dti.astimezone(APP_TZ)
            final_iso = dti.isoformat()
            final_hhmm = dti.strftime("%H:%M")
        except Exception:
            pass

    schedule_time = _normalise_hhmm(schedule_time)

    if not final_iso and schedule_time:
        wanted = schedule_time
        for d in range(0, 31):
            day = (dt.datetime.now(APP_TZ) + dt.timedelta(days=d)).strftime("%Y-%m-%d")
            taken = _occupied_slots_for_date(acc, day)
            if d == 0 and wanted <= dt.datetime.now(APP_TZ).strftime("%H:%M"):
                continue
            if wanted not in taken:
                hh, mm = map(int, wanted.split(":"))
                local_dt = dt.datetime.fromisoformat(f"{day}T{hh:02d}:{mm:02d}:00").replace(tzinfo=APP_TZ)
                final_iso = local_dt.isoformat()
                final_hhmm = wanted
                break

    if not final_iso:
        account_obj = TikTokAccountRepository.get_by_name(db, acc) if db else None
        if account_obj:
            ymd, hhmm = _find_next_free_slot_for_account(acc, account_obj.id, db)
            _add_log(f"Usando horários do banco de dados para conta '{acc}' (ID: {account_obj.id})", account_name=acc)
        else:
            ymd, hhmm = _find_next_free_slot(acc, schedules)
            _add_log(f"Conta '{acc}' não encontrada no banco, usando horários legados", account_name=acc)

        local_dt = dt.datetime.fromisoformat(f"{ymd}T{hhmm}:00").replace(tzinfo=APP_TZ)
        final_iso = local_dt.isoformat()
        final_hhmm = hhmm

    unified_metadata = {
        "title": None,
        "description": (description or "").strip() or None,
        "caption": (description or "").strip() or None,
        "hashtags": (hashtags or "").strip() or None,
        "keywords": [],
        "scheduled_at": final_iso,
        "schedule_time": final_hhmm,
        "timezone": str(APP_TZ),
        "account": acc,
        "status": "pending",
        "uploaded_at": tz_now().isoformat(),
        "posted_at": None,
        "delete_after_post": str(delete_after).lower() == "true",
        "priority": 0,
        "source": "api",
        "ai_generated": False,
        "ai_model": None,
        "workflow_id": None,
        "video_duration": None,
        "video_size": None,
        "retry_count": 0,
        "last_error": None,
    }

    unified_path = dst.with_suffix(".json")
    unified_path.write_text(json.dumps(unified_metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    _add_log(f"Metadados unificados salvos: {unified_path.name} • {final_hhmm} • {final_iso}", account_name=acc)

    return {
        "saved": video.filename,
        "meta": {
            "caption": unified_metadata["caption"],
            "hashtags": unified_metadata["hashtags"],
            "schedule_time": final_hhmm,
            "scheduled_at": final_iso,
            "delete_after": unified_metadata["delete_after_post"],
            "uploaded_at": unified_metadata["uploaded_at"],
            "account": acc,
        },
    }


@router.get("/api/videos", response_model=APIResponse[dict])
@router.get("/videos", response_model=APIResponse[dict])
async def api_videos(
    account: str = Query(..., description="Nome da conta TikTok (obrigatório)"),
    auth_data: Tuple[Optional[UserModel], Optional[APIKeyModel]] = Depends(get_current_user_or_api_key),
) -> APIResponse[dict]:
    return success_response(data=_videos_handler(account))


@router.get("/api/scheduled", response_model=APIResponse[dict])
@router.get("/scheduled", response_model=APIResponse[dict])
async def api_scheduled(
    account: str = Query(..., description="Nome da conta TikTok (obrigatório)"),
    auth_data: Tuple[Optional[UserModel], Optional[APIKeyModel]] = Depends(get_current_user_or_api_key),
) -> APIResponse[dict]:
    return success_response(data=_scheduled_handler(account))


@router.get("/api/schedules", response_model=APIResponse[dict])
@router.get("/schedules", response_model=APIResponse[dict])
async def get_schedules(
    auth_data: Tuple[Optional[UserModel], Optional[APIKeyModel]] = Depends(get_current_user_or_api_key),
) -> APIResponse[dict]:
    return success_response(data={"schedules": _read_schedules()})


@router.post("/api/schedules", response_model=APIResponse[dict])
@router.post("/schedules", response_model=APIResponse[dict])
async def set_schedules(
    data: ScheduleUpdate,
    auth_data: Tuple[Optional[UserModel], Optional[APIKeyModel]] = Depends(get_current_user_or_api_key),
) -> APIResponse[dict]:
    _write_schedules(data.schedules)
    _add_log(f"Horários atualizados (legado UI): {len(data.schedules)} itens")
    return success_response(message="Horários atualizados", data={"count": len(data.schedules)})


@router.post("/api/upload", response_model=APIResponse[dict])
@router.post("/upload", response_model=APIResponse[dict])
async def api_upload(
    video: UploadFile = File(...),
    account: str = Form(..., description="Nome da conta TikTok (obrigatório)"),
    description: Optional[str] = Form(None),
    hashtags: Optional[str] = Form(None),
    schedule_time: Optional[str] = Form(None),
    scheduled_at: Optional[str] = Form(None),
    delete_after: Optional[str] = Form("false"),
    user_or_key: Tuple[Optional[UserModel], Optional[APIKeyModel]] = Depends(get_current_user_or_api_key),
    db: Session = Depends(get_db),
) -> APIResponse[dict]:
    user, api_key_obj = user_or_key
    if api_key_obj and "upload" not in (api_key_obj.permissions or []):
        raise_http_error(status.HTTP_403_FORBIDDEN, error="missing_permission", message="API Key does not have 'upload' permission")

    payload = await _upload_handler(
        video=video,
        description=description,
        hashtags=hashtags,
        account=account,
        schedule_time=schedule_time,
        delete_after=delete_after,
        scheduled_at_iso=scheduled_at,
        db=db,
    )
    return success_response(data=payload)


@router.post("/api/post_now", response_model=APIResponse[dict])
@router.post("/post_now", response_model=APIResponse[dict])
async def post_now(
    request: PostNowRequest,
    current_user: UserModel = Depends(get_current_active_user),
) -> APIResponse[dict]:
    if not request.account or not request.account.strip():
        raise_http_error(status.HTTP_400_BAD_REQUEST, error="account_required", message="Nome da conta é obrigatório")

    _add_log(f"Tentando postar agora: {request.video_path} (conta: {request.account})", user_id=current_user.id, account_name=request.account)
    video_path = _acc_dir(VIDEOS_DIR, request.account.strip()) / request.video_path
    if not video_path.exists():
        raise_http_error(status.HTTP_404_NOT_FOUND, error="video_not_found", message="Vídeo não encontrado")
    _add_log(f"[SIMULADO] Vídeo postado com sucesso: {request.video_path}", user_id=current_user.id, account_name=request.account)
    return success_response(message="Postagem simulada com sucesso")


@router.delete("/api/videos/{account}/{filename}", response_model=APIResponse[dict])
@router.delete("/videos/{account}/{filename}", response_model=APIResponse[dict])
async def delete_video(
    account: str,
    filename: str,
    mode: str = Query("move", pattern="^(move|trash|hard)$"),
    current_user: UserModel = Depends(get_current_active_user),
) -> APIResponse[dict]:
    if not account or not account.strip():
        raise_http_error(status.HTTP_400_BAD_REQUEST, error="account_required", message="Nome da conta é obrigatório")

    acc = account.strip()
    vdir = _acc_dir(VIDEOS_DIR, acc)
    target = vdir / filename

    if not target.exists() or target.suffix.lower() != ".mp4":
        raise_http_error(status.HTTP_404_NOT_FOUND, error="video_not_found", message="Vídeo não encontrado")

    try:
        if mode == "hard":
            sidecars = [p for p in _sidecars(target) if p.exists()]
            for s in sidecars:
                try:
                    s.unlink()
                except Exception as exc:
                    _add_log(f"Falha ao remover sidecar {s.name}: {exc}", level="warning", account_name=acc, user_id=current_user.id)
            target.unlink()
            _add_log(f"[DEL HARD] {acc}/{filename}", account_name=acc, user_id=current_user.id)
            return success_response(data={"mode": mode, "file": filename})

        dest_dir = POSTED_DIR / acc if mode == "move" else STATE_DIR / "trash" / acc
        dest_dir.mkdir(parents=True, exist_ok=True)

        for s in _sidecars(target):
            if s.exists():
                try:
                    _safe_move(s, dest_dir)
                except Exception as exc:
                    _add_log(f"Falha ao mover sidecar {s.name}: {exc}", level="warning", account_name=acc, user_id=current_user.id)

        moved_main = _safe_move(target, dest_dir)
        tag = "POSTED" if mode == "move" else "TRASH"
        _add_log(f"[DEL {tag}] {acc}/{filename} -> {moved_main}", account_name=acc, user_id=current_user.id)
        return success_response(data={"mode": mode, "file": filename})
    except HTTPException:
        raise
    except Exception as exc:
        raise_http_error(status.HTTP_500_INTERNAL_SERVER_ERROR, error="delete_failed", message=str(exc))


@router.post("/api/videos/{account}/{filename}/reschedule", response_model=APIResponse[dict])
@router.post("/videos/{account}/{filename}/reschedule", response_model=APIResponse[dict])
async def reschedule_video(
    account: str,
    filename: str,
    payload: RescheduleVideoRequest,
    current_user: UserModel = Depends(get_current_active_user),
) -> APIResponse[dict]:
    if not account or not account.strip():
        raise_http_error(status.HTTP_400_BAD_REQUEST, error="account_required", message="Nome da conta é obrigatório")

    acc = account.strip()
    vdir = _acc_dir(VIDEOS_DIR, acc)
    mp4_name = filename if filename.endswith(".mp4") else f"{filename}.mp4"
    video_path = vdir / mp4_name

    if not video_path.exists():
        raise_http_error(status.HTTP_404_NOT_FOUND, error="video_not_found", message="Vídeo não encontrado")

    target_dt = payload.new_datetime
    if target_dt.tzinfo is None:
        target_dt = target_dt.replace(tzinfo=APP_TZ)
    else:
        target_dt = target_dt.astimezone(APP_TZ)

    if target_dt < dt.datetime.now(APP_TZ) - dt.timedelta(minutes=10):
        raise_http_error(status.HTTP_400_BAD_REQUEST, error="past_datetime", message="A nova data/hora já passou")

    new_hhmm = target_dt.strftime("%H:%M")
    iso_utc = target_dt.astimezone(dt.timezone.utc).isoformat()

    try:
        _update_sidecars_for(str(video_path), new_hhmm, iso_utc, lambda msg: _add_log(msg, account_name=acc))
    except Exception as exc:
        raise_http_error(status.HTTP_500_INTERNAL_SERVER_ERROR, error="update_failed", message=str(exc))

    json_path = video_path.with_suffix(".json")
    if json_path.exists():
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
        except Exception:
            data = {}
        data["scheduled_at"] = iso_utc
        data["schedule_time"] = new_hhmm
        data["status"] = "pending"
        data["posted_at"] = None
        json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    _add_log(
        f"Horário do vídeo '{mp4_name}' atualizado para {target_dt.strftime('%Y-%m-%d %H:%M:%S')} (conta {acc})",
        account_name=acc,
        user_id=current_user.id,
    )

    return success_response(
        message="Horário atualizado",
        data={
            "video": mp4_name,
            "scheduled_at": iso_utc,
            "schedule_time": new_hhmm,
        },
    )


@router.get("/schedule/preview", response_model=APIResponse[dict])
async def schedule_preview(
    account: str = Query(..., description="Nome da conta TikTok (obrigatório)"),
    auth_data: Tuple[Optional[UserModel], Optional[APIKeyModel]] = Depends(get_current_user_or_api_key),
) -> APIResponse[dict]:
    if not account or not account.strip():
        raise_http_error(status.HTTP_400_BAD_REQUEST, error="account_required", message="Nome da conta é obrigatório")
    return success_response(data=preview_schedule(account.strip()))


@router.post("/schedule/plan", response_model=APIResponse[dict])
async def schedule_plan_all(
    auth_data: Tuple[Optional[UserModel], Optional[APIKeyModel]] = Depends(get_current_user_or_api_key),
) -> APIResponse[dict]:
    summary = plan_all_accounts()
    return success_response(data={"summary": summary}, message="Planejamento executado")

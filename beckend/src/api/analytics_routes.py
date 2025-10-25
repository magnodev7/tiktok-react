"""Rotas de analytics consumidas pelo painel React."""

from __future__ import annotations

import json
import os
import logging
import threading
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.analytics import VideoAnalytics
from src.auth import get_current_active_user
from src.database import get_db
from src.models import TikTokAccount, TikTokAccountMetric, User as UserModel
from src.repositories import (
    TikTokAccountMetricsRepository,
    TikTokAccountRepository,
)
from src.services.tiktok_scraper import TikTokScraper, TikTokScraperError, refresh_account_metrics

from .schemas import APIResponse, TikTokAccountMetricPayload
from .utils import raise_http_error, success_response
from .models import TikTokPinVideoRequest


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_POSTED_DIR = BASE_DIR / "posted"


def _ensure_dir(path: Path, fallback: Path) -> Path:
    try:
        path.mkdir(parents=True, exist_ok=True)
        return path
    except OSError as exc:
        if path.resolve() == fallback.resolve():
            raise
        logger.warning("Não foi possível usar diretório de posted %s (%s); usando fallback %s", path, exc, fallback)
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


POSTED_DIR = _ensure_dir(Path(os.getenv("BASE_POSTED_DIR") or DEFAULT_POSTED_DIR), DEFAULT_POSTED_DIR)

DEFAULT_STATE_DIR = BASE_DIR / "state"
STATE_DIR = _ensure_dir(Path(os.getenv("BASE_STATE_DIR") or DEFAULT_STATE_DIR), DEFAULT_STATE_DIR)
PINNED_VIDEOS_FILE = STATE_DIR / "pinned_videos.json"
MAX_PINNED_VIDEOS = 3
_PINNED_LOCK = threading.Lock()


def _read_pinned_data() -> Dict[str, List[dict]]:
    with _PINNED_LOCK:
        if not PINNED_VIDEOS_FILE.exists():
            return {}
        try:
            return json.loads(PINNED_VIDEOS_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            logger.warning("Arquivo pinned_videos.json corrompido. Recriando estrutura vazia.")
            return {}


def _write_pinned_data(data: Dict[str, List[dict]]) -> None:
    with _PINNED_LOCK:
        PINNED_VIDEOS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _get_pinned_videos(account_name: str) -> List[dict]:
    data = _read_pinned_data()
    return data.get(account_name, [])


def _set_pinned_videos(account_name: str, videos: List[dict]) -> None:
    data = _read_pinned_data()
    if videos:
        data[account_name] = videos
    elif account_name in data:
        del data[account_name]
    _write_pinned_data(data)


def _analytics_instance() -> VideoAnalytics:
    return VideoAnalytics(base_video_dir=str(POSTED_DIR))


def _ensure_account_access(
    db: Session,
    account_name: str,
    current_user: UserModel,
) -> TikTokAccount:
    account = TikTokAccountRepository.get_by_name(db, account_name)
    if not account:
        raise_http_error(404, error="account_not_found", message="Conta TikTok não encontrada")

    if account.user_id != current_user.id and not current_user.is_admin:
        raise_http_error(403, error="forbidden", message="Você não tem acesso a esta conta")

    return account


def _serialize_metric(account_name: str, metric: TikTokAccountMetric) -> TikTokAccountMetricPayload:
    extra = metric.extra or {}
    return TikTokAccountMetricPayload(
        account_name=account_name,
        captured_at=metric.captured_at,
        followers=metric.followers,
        following=metric.following,
        likes=metric.likes,
        videos=metric.videos,
        friend_count=metric.friend_count,
        heart=metric.heart,
        digg_count=metric.digg_count,
        verified=metric.verified,
        private_account=metric.private_account,
        region=metric.region,
        signature=metric.signature,
        profile_pic=metric.profile_pic,
        social_links=metric.social_links or [],
        nickname=extra.get("nickname"),
        sec_uid=extra.get("sec_uid"),
        comment_setting=extra.get("comment_setting"),
        source=extra.get("source"),
    )


def _format_response_video(video: Dict[str, Any], is_pinned: bool) -> Dict[str, Any]:
    payload = dict(video)
    payload["is_pinned"] = is_pinned
    return payload


@router.get(
    "/accounts/{account_name}/recent-videos",
    response_model=APIResponse[dict],
)
async def get_recent_videos(
    account_name: str,
    limit: int = Query(3, ge=1, le=9, description="Quantidade de itens a retornar"),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user),
) -> APIResponse[dict]:
    account = _ensure_account_access(db, account_name, current_user)

    pinned_raw = [dict(video) for video in _get_pinned_videos(account.account_name)]
    pinned_ids = {str(video.get("id")) for video in pinned_raw if video.get("id")}

    scraper = TikTokScraper()
    try:
        fetched = scraper.fetch_recent_posts(
            account.account_name,
            count=max(limit + len(pinned_ids), 9),
            account_name=account.account_name,
        )
    except TikTokScraperError as exc:
        logger.warning("Falha ao buscar posts recentes de %s: %s", account.account_name, exc)
        fetched = []

    fetched_by_id = {str(item.get("id")): item for item in fetched if item.get("id")}
    now_iso = datetime.now(timezone.utc).isoformat()

    updated_pinned: List[Dict[str, Any]] = []
    changed = False
    for entry in pinned_raw:
        video_id = str(entry.get("id"))
        merged = dict(entry)
        match = fetched_by_id.get(video_id)
        if match:
            for key, value in match.items():
                if value is not None and merged.get(key) != value:
                    merged[key] = value
                    changed = True
        if not merged.get("pinned_at"):
            merged["pinned_at"] = now_iso
            changed = True
        merged.pop("is_pinned", None)
        updated_pinned.append(merged)

    if changed:
        _set_pinned_videos(account.account_name, updated_pinned)

    available_unpinned = [
        item
        for item in fetched
        if str(item.get("id")) not in pinned_ids and not item.get("is_pinned_item")
    ]
    slots_remaining = max(limit - len(updated_pinned), 0)
    recent_unpinned = available_unpinned[:slots_remaining]

    videos_response = [
        _format_response_video(video, True) for video in updated_pinned
    ] + [
        _format_response_video(video, False) for video in recent_unpinned
    ]

    return success_response(
        data={
            "videos": videos_response,
            "meta": {
                "limit": limit,
                "pinned_count": len(updated_pinned),
                "fetched_count": len(fetched),
            },
        }
    )


@router.post(
    "/accounts/{account_name}/recent-videos/pin",
    response_model=APIResponse[dict],
)
async def pin_recent_video(
    account_name: str,
    payload: TikTokPinVideoRequest,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user),
) -> APIResponse[dict]:
    account = _ensure_account_access(db, account_name, current_user)

    pinned = _get_pinned_videos(account.account_name)
    if any(str(video.get("id")) == payload.video_id for video in pinned):
        return success_response(
            data={"pinned": [_format_response_video(video, True) for video in pinned]},
            message="Vídeo já estava fixado",
        )

    if len(pinned) >= MAX_PINNED_VIDEOS:
        raise_http_error(
            400,
            error="pin_limit_reached",
            message=f"Limite de {MAX_PINNED_VIDEOS} vídeos fixados atingido.",
        )

    scraper = TikTokScraper()
    try:
        fetched = scraper.fetch_recent_posts(
            account.account_name,
            count=12,
            account_name=account.account_name,
        )
    except TikTokScraperError as exc:
        raise_http_error(502, error="tiktok_fetch_failed", message=str(exc))

    match = next((item for item in fetched if str(item.get("id")) == payload.video_id), None)
    if not match:
        raise_http_error(404, error="video_not_found", message="Vídeo não encontrado entre os mais recentes.")

    pinned_video = dict(match)
    pinned_video["pinned_at"] = datetime.now(timezone.utc).isoformat()
    pinned.append(pinned_video)
    _set_pinned_videos(account.account_name, pinned)

    return success_response(
        message="Vídeo fixado com sucesso.",
        data={"pinned": [_format_response_video(video, True) for video in pinned]},
    )


@router.delete(
    "/accounts/{account_name}/recent-videos/pin/{video_id}",
    response_model=APIResponse[dict],
)
async def unpin_recent_video(
    account_name: str,
    video_id: str,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user),
) -> APIResponse[dict]:
    account = _ensure_account_access(db, account_name, current_user)

    pinned = _get_pinned_videos(account.account_name)
    updated = [video for video in pinned if str(video.get("id")) != video_id]

    if len(updated) == len(pinned):
        raise_http_error(404, error="pin_not_found", message="Vídeo não estava fixado.")

    _set_pinned_videos(account.account_name, updated)

    return success_response(
        message="Vídeo removido dos fixados.",
        data={"pinned": [_format_response_video(video, True) for video in updated]},
    )


@router.get("/summary", response_model=APIResponse[dict])
async def get_analytics_summary(
    account: Optional[str] = Query(None, description="Nome da conta (opcional - None = todas)"),
    days_back: int = Query(30, ge=1, le=365, description="Período de análise em dias"),
    current_user: UserModel = Depends(get_current_active_user),
) -> APIResponse[dict]:
    analytics = _analytics_instance()
    report = analytics.generate_summary_report(account=account, days_back=days_back)
    return success_response(data=report)


@router.get("/ai-performance", response_model=APIResponse[dict])
async def get_ai_performance(
    account: Optional[str] = Query(None, description="Nome da conta (opcional - None = todas)"),
    days_back: int = Query(30, ge=1, le=365, description="Período de análise em dias"),
    current_user: UserModel = Depends(get_current_active_user),
) -> APIResponse[dict]:
    analytics = _analytics_instance()
    stats = analytics.analyze_ai_performance(account=account, days_back=days_back)
    return success_response(data={model: asdict(stat) for model, stat in stats.items()})


@router.get("/workflows", response_model=APIResponse[dict])
async def get_workflow_stats(
    account: Optional[str] = Query(None, description="Nome da conta (opcional - None = todas)"),
    days_back: int = Query(30, ge=1, le=365, description="Período de análise em dias"),
    current_user: UserModel = Depends(get_current_active_user),
) -> APIResponse[dict]:
    analytics = _analytics_instance()
    stats = analytics.analyze_workflow_performance(account=account, days_back=days_back)
    return success_response(data={wf_id: asdict(stat) for wf_id, stat in stats.items()})


@router.get("/sources", response_model=APIResponse[dict])
async def get_source_stats(
    account: Optional[str] = Query(None, description="Nome da conta (opcional - None = todas)"),
    days_back: int = Query(30, ge=1, le=365, description="Período de análise em dias"),
    current_user: UserModel = Depends(get_current_active_user),
) -> APIResponse[dict]:
    analytics = _analytics_instance()
    stats = analytics.analyze_by_source(account=account, days_back=days_back)
    return success_response(data={source: asdict(stat) for source, stat in stats.items()})


@router.get("/alerts", response_model=APIResponse[dict])
async def get_alerts(
    account: Optional[str] = Query(None, description="Nome da conta (opcional - None = todas)"),
    current_user: UserModel = Depends(get_current_active_user),
) -> APIResponse[dict]:
    analytics = _analytics_instance()
    alerts = analytics.detect_issues(account=account)
    return success_response(data={"total_alerts": len(alerts), "alerts": alerts})


@router.get(
    "/accounts/{account_name}/metrics",
    response_model=APIResponse[Optional[TikTokAccountMetricPayload]],
)
async def get_latest_account_metrics(
    account_name: str,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user),
) -> APIResponse[Optional[TikTokAccountMetricPayload]]:
    account = _ensure_account_access(db, account_name, current_user)
    metric = TikTokAccountMetricsRepository.get_latest(db, account.id)
    if not metric:
        return success_response(data=None, message="Nenhuma métrica coletada ainda")
    return success_response(data=_serialize_metric(account.account_name, metric))


@router.get(
    "/accounts/{account_name}/metrics/history",
    response_model=APIResponse[List[TikTokAccountMetricPayload]],
)
async def get_account_metrics_history(
    account_name: str,
    days: Optional[int] = Query(None, ge=1, le=365, description="Filtra últimos N dias"),
    limit: int = Query(90, ge=1, le=1000, description="Número máximo de registros"),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user),
) -> APIResponse[List[TikTokAccountMetricPayload]]:
    account = _ensure_account_access(db, account_name, current_user)
    history = TikTokAccountMetricsRepository.list_history(
        db,
        account.id,
        days_back=days,
        limit=limit,
    )
    payload = [_serialize_metric(account.account_name, metric) for metric in history]
    return success_response(data=payload)


@router.post(
    "/accounts/{account_name}/metrics/refresh",
    response_model=APIResponse[TikTokAccountMetricPayload],
)
async def refresh_account_metrics_endpoint(
    account_name: str,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user),
) -> APIResponse[TikTokAccountMetricPayload]:
    account = _ensure_account_access(db, account_name, current_user)

    try:
        metric, _profile = refresh_account_metrics(db, account)
    except TikTokScraperError as exc:
        raise_http_error(502, error="tiktok_scraper_error", message=str(exc))

    return success_response(data=_serialize_metric(account.account_name, metric))

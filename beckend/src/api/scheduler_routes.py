"""Rotas para consultar o estado atual do scheduler."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.auth import get_current_active_user
from src.database import get_db
from src.models import User as UserModel
from src.repositories import TikTokAccountRepository
from src import scheduler_state

from .schemas import APIResponse, SchedulerStatusResponse
from .utils import success_response


router = APIRouter(tags=["scheduler"])


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def _format_entry(raw: dict) -> SchedulerStatusResponse:
    return SchedulerStatusResponse(
        account_name=raw.get("account_name", ""),
        status=raw.get("status") or "unknown",
        due_count=int(raw.get("due_count") or 0),
        next_due_at=_parse_dt(raw.get("next_due_at")),
        current_slot=_parse_dt(raw.get("current_slot")),
        last_tick_at=_parse_dt(raw.get("last_tick_at")),
        last_started_at=_parse_dt(raw.get("last_started_at")),
        last_completed_at=_parse_dt(raw.get("last_completed_at")),
        message=raw.get("message"),
        updated_at=_parse_dt(raw.get("updated_at")) or datetime.utcnow(),
    )


@router.get("/api/scheduler/status", response_model=APIResponse[List[SchedulerStatusResponse]])
async def get_scheduler_status(
    account: Optional[str] = None,
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> APIResponse[List[SchedulerStatusResponse]]:
    """
    Retorna o estado do scheduler por conta.

    - Usuários comuns enxergam apenas suas contas ativas.
    - Administradores enxergam todas as contas.
    - É possível filtrar por `account` (account_name).
    """
    raw_state = scheduler_state.get_state(account_name=account)

    if current_user.is_admin:
        entries = list(raw_state.values())
    else:
        accounts = TikTokAccountRepository.list_by_user(db, current_user.id, active_only=True)
        allowed = {acc.account_name for acc in accounts}
        entries = [
            entry for name, entry in raw_state.items()
            if name in allowed
        ]

    statuses = [_format_entry(entry) for entry in entries if entry]
    statuses.sort(key=lambda s: (s.account_name or "").lower())

    return success_response(data=statuses)

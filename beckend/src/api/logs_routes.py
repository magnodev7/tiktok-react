"""Rotas para consulta de logs."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query

from src.auth import get_current_active_user
from src.models import User as UserModel
from src import log_service

from .schemas import APIResponse
from .utils import success_response


router = APIRouter(tags=["logs"])


def _fetch_logs(current_user: Optional[UserModel], limit: int, account: Optional[str]):
    if current_user and current_user.is_admin:
        return log_service.get_logs_for_admin(account_name=account, limit=limit)
    if current_user:
        return log_service.get_logs_for_user(user_id=current_user.id, account_name=account, limit=limit)
    return []


@router.get("/api/logs", response_model=APIResponse[dict])
@router.get("/logs", response_model=APIResponse[dict])
async def get_logs(
    limit: int = Query(50, ge=1, le=200),
    account: Optional[str] = Query(None),
    current_user: UserModel = Depends(get_current_active_user),
) -> APIResponse[dict]:
    logs = _fetch_logs(current_user, limit, account)
    return success_response(data={"logs": logs})

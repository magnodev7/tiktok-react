"""Rotas para consulta de logs."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query, status

from src.auth import get_current_active_user
from src.models import User as UserModel
from src import log_service

from .schemas import APIResponse
from .utils import raise_http_error, success_response


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


@router.delete("/api/logs", response_model=APIResponse[dict])
@router.delete("/logs", response_model=APIResponse[dict])
async def clear_logs(
    account: Optional[str] = Query(None),
    current_user: UserModel = Depends(get_current_active_user),
) -> APIResponse[dict]:
    if not current_user.is_admin:
        raise_http_error(
            status.HTTP_403_FORBIDDEN,
            error="forbidden",
            message="Apenas administradores podem limpar os logs",
        )

    result = log_service.clear_logs(account_name=account)
    message = "Logs removidos com sucesso"
    if account:
        message += f" para a conta '{account}'"

    return success_response(message=message, data=result)

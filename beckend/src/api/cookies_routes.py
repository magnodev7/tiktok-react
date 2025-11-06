"""Rotas para validação de cookies de contas TikTok."""

from fastapi import APIRouter, Depends, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from src.auth import get_current_active_user, get_db
from src.models import User as UserModel
from src.repositories import TikTokAccountRepository
from src.services.cookie_validation import validate_account_cookies

from .schemas import (
    CookieValidationAPIResponse,
    CookieValidationRequest,
    CookieValidationResponse,
)
from .utils import raise_http_error, success_response


router = APIRouter(prefix="/api/cookies", tags=["cookies"])


@router.post("/validate", response_model=CookieValidationAPIResponse)
async def validate_cookies(
    request: CookieValidationRequest,
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> CookieValidationAPIResponse:
    account = TikTokAccountRepository.get_by_name(db, request.account_name)
    if not account:
        raise_http_error(
            status.HTTP_404_NOT_FOUND,
            error="account_not_found",
            message="Conta TikTok não encontrada.",
        )

    if account.user_id != current_user.id and not current_user.is_admin:
        raise_http_error(
            status.HTTP_403_FORBIDDEN,
            error="forbidden",
            message="Você não tem permissão para validar esta conta.",
        )

    try:
        result = await run_in_threadpool(
            validate_account_cookies,
            account.account_name,
            request.visible,
            request.test_mode,
        )
    except Exception as exc:
        raise_http_error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            error="validation_failed",
            message=f"Erro ao executar teste de cookies: {exc}",
        )

    if not isinstance(result, dict):
        raise_http_error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            error="invalid_response",
            message="Retorno inesperado do validador de cookies.",
        )

    if result.get("status") != "success":
        raise_http_error(
            status.HTTP_400_BAD_REQUEST,
            error="invalid_cookies",
            message=result.get("message") or "Cookies inválidos.",
        )

    payload = CookieValidationResponse(
        status="success",
        message=result.get("message") or "Sessão válida.",
        profile_url=result.get("profile_url"),
        title=result.get("title"),
    )
    return success_response(data=payload, message=payload.message)

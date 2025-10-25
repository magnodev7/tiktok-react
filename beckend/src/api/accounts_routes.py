"""Rotas relacionadas a contas TikTok e horários de postagem."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from src.auth import (
    get_current_active_user,
    get_db,
)
from src.models import TikTokAccount as TikTokAccountModel
from src.repositories import TikTokAccountMetricsRepository, TikTokAccountRepository

from .. import log_service
from .schemas import APIResponse
from .models import TikTokAccountCreate, TikTokAccountPublic, TikTokAccountUpdate
from .utils import raise_http_error, success_response


router = APIRouter(prefix="/api/tiktok-accounts", tags=["tiktok-accounts"])


def _add_log(message: str, level: str = "info", account_name: Optional[str] = None, user_id: Optional[int] = None) -> None:
    log_service.add_log(message=message, level=level, account_name=account_name, user_id=user_id, module="api-accounts")


def _ensure_account_owner(account: TikTokAccountModel, current_user: TikTokAccountModel) -> None:
    if account.user_id != current_user.id:
        raise_http_error(status.HTTP_403_FORBIDDEN, error="forbidden", message="Você não tem permissão para acessar esta conta")


@router.get("", response_model=APIResponse[List[TikTokAccountPublic]])
async def list_tiktok_accounts(
    active_only: bool = Query(False, description="Listar apenas contas ativas"),
    current_user: TikTokAccountModel = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> APIResponse[List[TikTokAccountPublic]]:
    accounts = TikTokAccountRepository.list_by_user(db, current_user.id, active_only)

    payload = []
    for account in accounts:
        dto = TikTokAccountPublic.from_orm(account)
        latest_metric = TikTokAccountMetricsRepository.get_latest(db, account.id)
        if latest_metric:
            dto.profile_pic = latest_metric.profile_pic
            dto.profile_pic_updated_at = latest_metric.captured_at
            nickname = latest_metric.extra.get("nickname") if latest_metric.extra else None
            if nickname and not dto.display_name:
                dto.display_name = nickname
        payload.append(dto.model_dump())

    return success_response(data=payload)


@router.post("", response_model=APIResponse[TikTokAccountPublic])
async def create_tiktok_account(
    request: TikTokAccountCreate,
    current_user: TikTokAccountModel = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> APIResponse[TikTokAccountPublic]:
    existing = TikTokAccountRepository.get_by_name(db, request.account_name)
    if existing:
        raise_http_error(status.HTTP_400_BAD_REQUEST, error="account_exists", message=f"Já existe uma conta com o nome '{request.account_name}'")

    account = TikTokAccountRepository.create(
        db,
        user_id=current_user.id,
        account_name=request.account_name,
        display_name=request.display_name,
        description=request.description,
        cookies_data=request.cookies_data,
        is_default=request.is_default,
    )

    _add_log(
        f"Nova conta TikTok criada: {request.account_name} (usuário: {current_user.username})",
        account_name=request.account_name,
        user_id=current_user.id,
    )
    return success_response(data=TikTokAccountPublic.from_orm(account))


@router.get("/{account_id}", response_model=APIResponse[TikTokAccountPublic])
async def get_tiktok_account(
    account_id: int,
    current_user: TikTokAccountModel = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> APIResponse[TikTokAccountPublic]:
    account = TikTokAccountRepository.get_by_id(db, account_id)
    if not account:
        raise_http_error(status.HTTP_404_NOT_FOUND, error="account_not_found", message="Conta não encontrada")

    _ensure_account_owner(account, current_user)
    return success_response(data=TikTokAccountPublic.from_orm(account))


@router.put("/{account_id}", response_model=APIResponse[TikTokAccountPublic])
async def update_tiktok_account(
    account_id: int,
    request: TikTokAccountUpdate,
    current_user: TikTokAccountModel = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> APIResponse[TikTokAccountPublic]:
    account = TikTokAccountRepository.get_by_id(db, account_id)
    if not account:
        raise_http_error(status.HTTP_404_NOT_FOUND, error="account_not_found", message="Conta não encontrada")

    _ensure_account_owner(account, current_user)

    success = TikTokAccountRepository.update(
        db,
        account_id,
        display_name=request.display_name,
        description=request.description,
        cookies_data=request.cookies_data,
        is_active=request.is_active,
        is_default=request.is_default,
    )
    if not success:
        raise_http_error(status.HTTP_500_INTERNAL_SERVER_ERROR, error="account_update_failed", message="Erro ao atualizar conta")

    updated_account = TikTokAccountRepository.get_by_id(db, account_id)
    _add_log(
        f"Conta TikTok atualizada: {updated_account.account_name} (usuário: {current_user.username})",
        account_name=updated_account.account_name,
        user_id=current_user.id,
    )
    return success_response(data=TikTokAccountPublic.from_orm(updated_account))


@router.delete("/{account_id}", response_model=APIResponse[dict])
async def delete_tiktok_account(
    account_id: int,
    current_user: TikTokAccountModel = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> APIResponse[dict]:
    account = TikTokAccountRepository.get_by_id(db, account_id)
    if not account:
        raise_http_error(status.HTTP_404_NOT_FOUND, error="account_not_found", message="Conta não encontrada")

    _ensure_account_owner(account, current_user)

    success = TikTokAccountRepository.delete(db, account_id, remove_files=True)
    if not success:
        raise_http_error(
            status.HTTP_400_BAD_REQUEST,
            error="delete_blocked",
            message="Não é possível remover a última conta ativa. Crie outra conta antes de remover esta.",
        )

    _add_log(
        f"Conta TikTok e arquivos removidos: {account.account_name} (usuário: {current_user.username})",
        account_name=account.account_name,
        user_id=current_user.id,
    )
    return success_response(message=f"Conta '{account.account_name}' removida com sucesso")


@router.patch("/{account_id}/set-default", response_model=APIResponse[dict])
async def set_default_tiktok_account(
    account_id: int,
    current_user: TikTokAccountModel = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> APIResponse[dict]:
    account = TikTokAccountRepository.get_by_id(db, account_id)
    if not account:
        raise_http_error(status.HTTP_404_NOT_FOUND, error="account_not_found", message="Conta não encontrada")

    _ensure_account_owner(account, current_user)

    success = TikTokAccountRepository.update(db, account_id, is_default=True)
    if not success:
        raise_http_error(status.HTTP_500_INTERNAL_SERVER_ERROR, error="account_update_failed", message="Erro ao definir conta como padrão")

    _add_log(
        f"Conta TikTok '{account.account_name}' definida como padrão (usuário: {current_user.username})",
        account_name=account.account_name,
        user_id=current_user.id,
    )
    return success_response(message=f"Conta '{account.account_name}' definida como padrão")


@router.patch("/{account_id}/activate", response_model=APIResponse[dict])
async def activate_tiktok_account(
    account_id: int,
    current_user: TikTokAccountModel = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> APIResponse[dict]:
    account = TikTokAccountRepository.get_by_id(db, account_id)
    if not account:
        raise_http_error(status.HTTP_404_NOT_FOUND, error="account_not_found", message="Conta não encontrada")

    _ensure_account_owner(account, current_user)

    success = TikTokAccountRepository.update(db, account_id, is_active=True)
    if not success:
        raise_http_error(status.HTTP_500_INTERNAL_SERVER_ERROR, error="account_update_failed", message="Erro ao ativar conta")

    _add_log(
        f"Conta TikTok '{account.account_name}' ativada (usuário: {current_user.username})",
        account_name=account.account_name,
        user_id=current_user.id,
    )
    return success_response(message=f"Conta '{account.account_name}' ativada com sucesso")


@router.patch("/{account_id}/deactivate", response_model=APIResponse[dict])
async def deactivate_tiktok_account(
    account_id: int,
    current_user: TikTokAccountModel = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> APIResponse[dict]:
    account = TikTokAccountRepository.get_by_id(db, account_id)
    if not account:
        raise_http_error(status.HTTP_404_NOT_FOUND, error="account_not_found", message="Conta não encontrada")

    _ensure_account_owner(account, current_user)

    success = TikTokAccountRepository.update(db, account_id, is_active=False)
    if not success:
        raise_http_error(status.HTTP_500_INTERNAL_SERVER_ERROR, error="account_update_failed", message="Erro ao desativar conta")

    _add_log(
        f"Conta TikTok '{account.account_name}' desativada (usuário: {current_user.username})",
        account_name=account.account_name,
        user_id=current_user.id,
    )
    return success_response(message=f"Conta '{account.account_name}' desativada com sucesso")


@router.post("/{account_id}/update-cookies", response_model=APIResponse[dict])
async def update_account_cookies(
    account_id: int,
    cookies_data: Union[Dict[str, Any], List[Dict[str, Any]]] = Body(...),
    current_user: TikTokAccountModel = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> APIResponse[dict]:
    """Atualiza os cookies de uma conta TikTok.

    O usuário deve exportar cookies do navegador pessoal usando uma extensão
    como 'EditThisCookie' ou 'Cookie-Editor' e colar aqui.
    """
    account = TikTokAccountRepository.get_by_id(db, account_id)
    if not account:
        raise_http_error(status.HTTP_404_NOT_FOUND, error="account_not_found", message="Conta não encontrada")

    _ensure_account_owner(account, current_user)

    # Valida formato dos cookies
    cookies_list = None
    if isinstance(cookies_data, dict) and "cookies" in cookies_data:
        cookies_list = cookies_data["cookies"]
    elif isinstance(cookies_data, list):
        cookies_list = cookies_data
    else:
        raise_http_error(
            status.HTTP_400_BAD_REQUEST,
            error="invalid_cookies_format",
            message="Formato de cookies inválido. Envie um array de cookies ou objeto com chave 'cookies'."
        )

    if not cookies_list or not isinstance(cookies_list, list) or len(cookies_list) == 0:
        raise_http_error(
            status.HTTP_400_BAD_REQUEST,
            error="empty_cookies",
            message="Lista de cookies está vazia"
        )

    # Valida que cada cookie tem pelo menos 'name' e 'value'
    for idx, cookie in enumerate(cookies_list):
        if not isinstance(cookie, dict):
            raise_http_error(
                status.HTTP_400_BAD_REQUEST,
                error="invalid_cookie_format",
                message=f"Cookie na posição {idx} não é um objeto válido"
            )
        if "name" not in cookie or "value" not in cookie:
            raise_http_error(
                status.HTTP_400_BAD_REQUEST,
                error="missing_cookie_fields",
                message=f"Cookie na posição {idx} não possui 'name' ou 'value'"
            )

    # Prepara dados para salvar (garante que está no formato correto)
    cookies_to_save = {"cookies": cookies_list}

    # Atualiza cookies no banco
    success = TikTokAccountRepository.update(
        db,
        account_id,
        cookies_data=cookies_to_save,
    )

    if not success:
        raise_http_error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            error="cookies_update_failed",
            message="Erro ao atualizar cookies"
        )

    _add_log(
        f"Cookies atualizados para conta '{account.account_name}' ({len(cookies_list)} cookies) - usuário: {current_user.username}",
        account_name=account.account_name,
        user_id=current_user.id,
    )

    return success_response(
        message=f"Cookies atualizados com sucesso para '{account.account_name}' ({len(cookies_list)} cookies)",
        data={"cookies_count": len(cookies_list)}
    )

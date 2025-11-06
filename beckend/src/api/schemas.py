"""
Modelos Pydantic compartilhados para respostas da API.
"""

from __future__ import annotations

from datetime import datetime
from typing import Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field # type: ignore


T = TypeVar("T")

class APIResponse(BaseModel, Generic[T]):
    """Envelope padrão de sucesso."""

    success: bool = Field(True, description="Indica se a operação foi concluída com êxito.")
    data: Optional[T] = Field(None, description="Carga útil da resposta.")
    message: Optional[str] = Field(None, description="Mensagem informativa opcional.")

class APIError(BaseModel):
    """Envelope padrão para erros."""

    success: bool = Field(False, description="Sempre falso em respostas de erro.")
    error: str = Field(..., description="Código curto do erro.")
    message: str = Field(..., description="Descrição legível do erro.")


# Modelo de solicitação para a validação de cookies
class CookieValidationRequest(BaseModel):
    account_name: str
    visible: bool = False
    test_mode: bool = False

# Modelo de resposta para a validação de cookies
class CookieValidationResponse(BaseModel):
    """Resposta da validação de cookies."""
    status: str
    message: str
    profile_url: Optional[str] = None
    title: Optional[str] = None

# Resultado da validação de cookies encapsulado no modelo APIResponse
class CookieValidationAPIResponse(APIResponse[CookieValidationResponse]):
    """Envelope do endpoint de validação de cookies."""
    data: Optional[CookieValidationResponse] = Field(
        None,
        description="Resultado da validação dos cookies.",
    )



class TikTokAccountMetricPayload(BaseModel):
    """Representa uma fotografia de métricas da conta TikTok."""

    account_name: str
    captured_at: datetime
    followers: Optional[int] = None
    following: Optional[int] = None
    likes: Optional[int] = None
    videos: Optional[int] = None
    friend_count: Optional[int] = None
    heart: Optional[int] = None
    digg_count: Optional[int] = None
    verified: bool = False
    private_account: bool = False
    region: Optional[str] = None
    signature: Optional[str] = None
    profile_pic: Optional[str] = None
    social_links: List[str] = Field(default_factory=list)
    nickname: Optional[str] = None
    sec_uid: Optional[str] = None
    comment_setting: Optional[int] = None
    source: Optional[str] = None

"""
Modelos Pydantic compartilhados para respostas da API.
"""

from __future__ import annotations

from datetime import datetime
from typing import Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field


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

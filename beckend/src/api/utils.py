"""
Utilidades auxiliares para construção de respostas e manipulação de erros.
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import HTTPException, status

from .schemas import APIError, APIResponse


def success_response(data: Any = None, message: Optional[str] = None) -> APIResponse[Any]:
    """Gera envelope de sucesso padronizado."""
    return APIResponse(success=True, data=data, message=message)


def raise_http_error(
    http_status: int,
    *,
    error: str,
    message: str,
) -> None:
    """Atalho para lançar HTTPException com payload padronizado."""
    raise HTTPException(
        status_code=http_status,
        detail=APIError(success=False, error=error, message=message).model_dump(),
    )


def extract_error_payload(exc: HTTPException) -> APIError:
    """Normaliza payload de erro para o handler global."""
    if isinstance(exc.detail, dict):
        return APIError(**exc.detail)
    if isinstance(exc.detail, str):
        return APIError(success=False, error="http_error", message=exc.detail)
    return APIError(success=False, error="http_error", message=str(exc.detail))

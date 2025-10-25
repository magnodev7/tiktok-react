"""Coleção de roteadores e utilidades da API FastAPI.

Este pacote encapsula as rotas públicas da aplicação,
expondo utilidades compartilhadas (schemas, helpers)
sem alterar módulos críticos do scheduler.
"""

from .router import get_api_router  # noqa: F401

"""
Constrói o roteador principal da API.
"""

from fastapi import APIRouter

from . import (
    auth_routes,
    accounts_routes,
    analytics_routes,
    videos_routes,
    logs_routes,
    maintenance_routes,
)


def get_api_router() -> APIRouter:
    """Retorna um APIRouter com todos os módulos registrados."""
    api_router = APIRouter()

    api_router.include_router(auth_routes.router)
    api_router.include_router(accounts_routes.router)
    api_router.include_router(analytics_routes.router)
    api_router.include_router(videos_routes.router)
    api_router.include_router(logs_routes.router)
    api_router.include_router(maintenance_routes.router)

    return api_router

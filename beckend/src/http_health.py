# src/http_health.py - ponto de entrada FastAPI modernizado

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from src.api import get_api_router
from src.api.schemas import APIError
from src.api.utils import extract_error_payload
from src.database import SessionLocal, init_db
from src.auth import ensure_admin_exists
from src.routes import posting_schedules


app = FastAPI(title="TikTok Scheduler API")


@app.on_event("startup")
async def startup_event() -> None:
    """Inicializa banco de dados e garante usuário admin."""
    init_db()
    try:
        db = SessionLocal()
        try:
            ensure_admin_exists(db)
        finally:
            db.close()
    except Exception as exc:  # pragma: no cover - log apenas em runtime
        print(f"⚠️ Erro ao garantir usuário admin: {exc}")


BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = Path(os.getenv("FRONTEND_DIR") or (BASE_DIR / "web"))
FRONTEND_DIR.mkdir(parents=True, exist_ok=True)

USERDATA_DIR = Path(os.getenv("BASE_USERDATA_DIR") or (BASE_DIR / "user_data"))
USERDATA_DIR.mkdir(parents=True, exist_ok=True)


app.mount("/ui", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="ui")
assets_dir = FRONTEND_DIR / "assets"
if assets_dir.exists():
    app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

app.mount("/user_data", StaticFiles(directory=str(USERDATA_DIR)), name="user_data")


def _frontend_entry_response():
    idx = FRONTEND_DIR / "index.html"
    return FileResponse(idx) if idx.exists() else {"message": "Frontend não empacotado"}


@app.get("/", include_in_schema=False)
def root():
    return _frontend_entry_response()


cors_origins = os.getenv("CORS_ALLOW_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in cors_origins if origin.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(get_api_router())
app.include_router(posting_schedules.router)


@app.get("/{full_path:path}", include_in_schema=False)
async def serve_spa(full_path: str):
    """Retorna o index.html para rotas do frontend (SPA) após o build."""
    candidate = FRONTEND_DIR / full_path
    if candidate.is_file():
        return FileResponse(candidate)
    return _frontend_entry_response()


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
    payload = extract_error_payload(exc)
    return JSONResponse(status_code=exc.status_code, content=payload.model_dump())


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    message = "Erro de validação"
    if exc.errors():
        message = exc.errors()[0].get("msg", message)
    payload = APIError(success=False, error="validation_error", message=message)
    return JSONResponse(status_code=422, content=payload.model_dump())


@app.get("/health")
async def healthcheck() -> dict:
    return {"status": "ok"}

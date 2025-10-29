"""
⚠️ AVISO: Configurações LEGADAS (globais, não isoladas por conta)

Sistema moderno usa:
- PostgreSQL para horários por conta (PostingSchedule model)
- AccountStorage para cookies isolados por conta
- TikTokAccount model para configurações por conta

Mantido apenas para compatibilidade com código antigo.
"""

import os
import platform

# -------------------------
# Utilidades
# -------------------------
def _env_bool(key: str, default: bool = False) -> bool:
    v = os.getenv(key)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "on")

def _valid_hhmm(s: str) -> bool:
    s = (s or "").strip()
    return len(s) == 5 and s[2] == ":" and s[:2].isdigit() and s[3:].isdigit()

# -------------------------
# Credenciais / Cookies
# -------------------------
# ⚠️ DEPRECADO: COOKIES_FILE é global (não isolado por conta)
# Use AccountStorage.save_cookies(account_name, cookies) para cookies isolados
COOKIES_FILE = os.getenv("COOKIES_FILE", "tiktok_cookies.json")

# (Não recomendado: mantenha vazio e use cookies)
TIKTOK_USER = os.getenv("TIKTOK_USER", "")
TIKTOK_PASS = os.getenv("TIKTOK_PASS", "")

# -------------------------
# Pastas base (persistentes no projeto)
# -------------------------
# Diretório base do projeto (um nível acima de beckend/)
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _resolve_project_path(raw: str, default: str) -> str:
    """
    Normaliza caminhos relativos para a raiz do projeto.
    Evita salvar dados dentro de src/ quando um caminho relativo é fornecido.
    """
    if not raw:
        return default

    candidate = os.path.expanduser(raw.strip())
    if not os.path.isabs(candidate):
        candidate = os.path.join(_PROJECT_ROOT, candidate)
    candidate = os.path.abspath(candidate)

    try:
        src_root = os.path.join(_PROJECT_ROOT, "src")
        if os.path.commonpath([candidate, src_root]) == src_root:
            return default
    except Exception:
        # Em sistemas que não suportam commonpath adequadamente, faz verificação manual
        if os.path.abspath(candidate).startswith(os.path.abspath(os.path.join(_PROJECT_ROOT, "src"))):
            return default

    return candidate

# IMPORTANTE: profiles/ persiste logins do Chrome entre execuções
BASE_USER_DATA_DIR = _resolve_project_path(os.getenv("BASE_USER_DATA_DIR"), os.path.join(_PROJECT_ROOT, "profiles"))
BASE_VIDEO_DIR = _resolve_project_path(os.getenv("BASE_VIDEO_DIR"), os.path.join(_PROJECT_ROOT, "videos"))
BASE_POSTED_DIR = _resolve_project_path(os.getenv("BASE_POSTED_DIR"), os.path.join(_PROJECT_ROOT, "posted"))

ACCOUNTS_FILE = os.getenv("ACCOUNTS_FILE", "accounts.json")
CONFIG_FILE = os.getenv("CONFIG_FILE", "admin_config.json")
CONFIG_USER_FILE = os.getenv("CONFIG_USER_FILE", "user_config.json")

# -------------------------
# Horários padrão (lista de HH:MM)
# ⚠️ DEPRECADO: SCHEDULES é global (não isolado por conta)
# Use PostingSchedule model no banco de dados para horários por conta
# Pode ser sobrescrito por env SCHEDULES="08:00,12:00,18:07"
# -------------------------
_DEFAULT_SCHEDULES = [
    "08:00", "10:00", "12:00", "14:00",
    "16:00", "18:00", "20:00", "22:00", "09:23"
]

_env_sched = os.getenv("SCHEDULES")
if _env_sched:
    parts = [p.strip() for p in _env_sched.replace(";", ",").split(",") if p.strip()]
    _parsed = [p for p in parts if _valid_hhmm(p)]
    SCHEDULES = _parsed or _DEFAULT_SCHEDULES
else:
    SCHEDULES = _DEFAULT_SCHEDULES

# -------------------------
# Modo de postagem / teste
# -------------------------
# POST_HEADFUL mantém perfil/fingerprint estável (habilitado por padrão)
POST_HEADFUL = _env_bool("POST_HEADFUL", True)

# TEST_MODE=True não posta de verdade (default False para publicar normalmente)
TEST_MODE = _env_bool("TEST_MODE", False)

# -------------------------
# Limites e conteúdo
# -------------------------
MAX_CAPTION_CHARS = 2000

BRAND_TAGS = ["#novadigital", "#conteudobrasil"]
EXTRA_HASHTAGS = []

DEFAULT_CTA = "Siga para mais conteúdos diários."

# Após postar, excluir arquivo (default True). Se False, mover para posted/
DELETE_AFTER_POST = _env_bool("DELETE_AFTER_POST", True)

# -------------------------
# User-Agent
# -------------------------
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/114.0.0.0 Safari/537.36"
)

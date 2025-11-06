import sys
from pathlib import Path

import pytest
from fastapi import HTTPException

PROJECT_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = PROJECT_ROOT / "beckend"
for entry in (BACKEND_ROOT, BACKEND_ROOT / "src"):
    path_str = str(entry)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from src.api.accounts_routes import _ensure_required_cookies


def test_ensure_required_cookies_accepts_valid_payload():
    cookies = [
        {"name": "sessionid", "value": "abc"},
        {"name": "sessionid_ss", "value": "def"},
        {"name": "passport_csrf_token", "value": "ghi"},
        {"name": "passport_csrf_token_default", "value": "xyz"},
        {"name": "other", "value": "jkl"},
    ]

    # Não deve lançar exceção
    _ensure_required_cookies(cookies)


def test_ensure_required_cookies_rejects_missing_essentials():
    cookies = [
        {"name": "other", "value": "123"},
        {"name": "something", "value": "456"},
    ]

    with pytest.raises(HTTPException) as excinfo:
        _ensure_required_cookies(cookies)

    detail = excinfo.value.detail
    assert detail["error"] == "missing_required_cookies"
    assert "sessionid" in detail["message"]

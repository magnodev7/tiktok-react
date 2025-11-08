"""
Persistência leve do estado do scheduler por conta.

Utilizado para expor para o frontend quando o scheduler está ativo/processando,
qual o próximo horário previsto e metadados úteis sem depender de logs
de polling contínuo.
"""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional, Any


STATE_DIR = Path(os.getenv("BASE_STATE_DIR", "./state"))
STATE_DIR.mkdir(parents=True, exist_ok=True)
STATE_FILE = STATE_DIR / "scheduler_state.json"

_lock = threading.Lock()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_state() -> Dict[str, dict]:
    if not STATE_FILE.exists():
        return {}
    try:
        raw = STATE_FILE.read_text(encoding="utf-8")
        data = json.loads(raw)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {}


def _save_state(state: Dict[str, dict]) -> None:
    tmp_path = STATE_FILE.with_suffix(".tmp")
    tmp_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp_path.replace(STATE_FILE)


def update_state(
    account_name: str,
    *,
    status: Optional[str] = None,
    next_due_at: Optional[str] = None,
    due_count: Optional[int] = None,
    last_tick_at: Optional[str] = None,
    last_started_at: Optional[str] = None,
    last_completed_at: Optional[str] = None,
    message: Optional[str] = None,
    current_slot: Optional[str] = None,
) -> None:
    """Atualiza (ou cria) o estado da conta."""
    if not account_name:
        return

    with _lock:
        state = _load_state()
        entry = state.get(account_name, {})

        entry.setdefault("account_name", account_name)
        if status is not None:
            entry["status"] = status
        if next_due_at is not None or "next_due_at" not in entry:
            entry["next_due_at"] = next_due_at
        if due_count is not None:
            entry["due_count"] = due_count
        if last_tick_at is not None:
            entry["last_tick_at"] = last_tick_at
        if last_started_at is not None:
            entry["last_started_at"] = last_started_at
        if last_completed_at is not None:
            entry["last_completed_at"] = last_completed_at
        if message is not None:
            entry["message"] = message
        if current_slot is not None or "current_slot" not in entry:
            entry["current_slot"] = current_slot

        entry["updated_at"] = _now_iso()

        state[account_name] = entry
        _save_state(state)


def clear_state(account_name: str) -> None:
    """Remove estado da conta (ex.: scheduler parado)."""
    if not account_name:
        return
    with _lock:
        state = _load_state()
        if account_name in state:
            del state[account_name]
            _save_state(state)


def get_state(account_name: Optional[str] = None) -> Dict[str, dict]:
    """Recupera o estado de todas as contas ou de uma específica."""
    with _lock:
        state = _load_state()

    if account_name:
        entry = state.get(account_name)
        return {account_name: entry} if entry else {}
    return state


def merge_update(account_name: str, **fields: Any) -> None:
    """Atualização genérica preservando dados existentes."""
    update_state(account_name, **fields)

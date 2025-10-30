"""
Serviço de Logs Isolados por Usuário/Conta
Salva logs tanto no banco de dados quanto no arquivo JSON (backup/legado)
"""

import json
from json import JSONDecodeError
import os
import uuid
import datetime as dt
from pathlib import Path
from typing import Optional, List
from contextlib import contextmanager

# Configuração
STATE_DIR = Path(__file__).resolve().parent.parent / "state"
STATE_DIR.mkdir(parents=True, exist_ok=True)
LOGS_JSON = STATE_DIR / "logs.json"

# Cria arquivo base se não existir
if not LOGS_JSON.exists():
    LOGS_JSON.write_text(json.dumps({"logs": []}, ensure_ascii=False), encoding="utf-8")


@contextmanager
def get_db_session():
    """Context manager para sessão do banco"""
    from src.database import SessionLocal
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        db.rollback()
        print(f"[log_service] Erro no banco: {e}")
        raise
    finally:
        db.close()


def add_log(
    message: str,
    level: str = "info",
    user_id: Optional[int] = None,
    account_name: Optional[str] = None,
    module: Optional[str] = None,
    extra_data: Optional[dict] = None
):
    """
    Adiciona log ao sistema (banco de dados + arquivo JSON backup)

    Args:
        message: Mensagem do log
        level: Nível do log (debug, info, warning, error, critical)
        user_id: ID do usuário (opcional, para isolamento)
        account_name: Nome da conta TikTok (opcional, para filtrar por conta)
        module: Módulo que gerou o log (scheduler, uploader, etc)
        extra_data: Dados adicionais em formato dict

    Comportamento:
        - Salva no banco de dados (isolado por user_id + account_name)
        - Salva no arquivo JSON (backup/legado)
        - Em caso de erro no banco, continua salvando no JSON
    """

    timestamp_iso = dt.datetime.now(dt.timezone.utc).isoformat()

    # ===== 1. Salva no banco de dados (PRIORITÁRIO) =====
    try:
        from src.repositories import SystemLogRepository

        with get_db_session() as db:
            SystemLogRepository.create(
                db=db,
                message=message,
                level=level,
                user_id=user_id,
                account_name=account_name,
                module=module,
                extra_data=extra_data
            )
    except ImportError:
        # Sistema ainda não tem a tabela/repositório, usa apenas JSON
        pass
    except Exception as e:
        # Erro ao salvar no banco, continua com JSON (não quebra o sistema)
        print(f"[log_service] ⚠️ Erro ao salvar no banco (usando JSON): {e}")

    # ===== 2. Salva no arquivo JSON (BACKUP/LEGADO) =====
    payload = {
        "timestamp": timestamp_iso,
        "message": message,
        "level": level,
        "user_id": user_id,
        "account_name": account_name,
        "module": module
    }

    try:
        raw = LOGS_JSON.read_text(encoding="utf-8")
        try:
            data = json.loads(raw)
            if not isinstance(data, dict):
                raise ValueError("logs.json não é um objeto JSON válido")
        except (JSONDecodeError, ValueError):
            print("[log_service] ⚠️ logs.json corrompido — recriando arquivo.")
            data = {"logs": []}

        data.setdefault("logs", []).append(payload)

        # Mantém apenas últimos 200 logs no JSON (performance)
        if len(data["logs"]) > 200:
            data["logs"] = data["logs"][-200:]

        # Escrita atômica com arquivo temporário exclusivo (evita condição de corrida)
        tmp_name = f"{LOGS_JSON.name}.{uuid.uuid4().hex}.tmp"
        tmp_path = LOGS_JSON.parent / tmp_name
        tmp_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp_path, LOGS_JSON)

    except PermissionError:
        # Fallback para /tmp se não tiver permissão
        fb = Path("/tmp/tiktok_logs.json")
        try:
            if not fb.exists():
                fb.write_text(json.dumps({"logs": []}, ensure_ascii=False), encoding="utf-8")
            try:
                data = json.loads(fb.read_text(encoding="utf-8"))
            except JSONDecodeError:
                data = {"logs": []}
            data.setdefault("logs", []).append(payload)
            if len(data["logs"]) > 200:
                data["logs"] = data["logs"][-200:]
            fb.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as ee:
            print(f"[log_service] ❌ Falha também no fallback /tmp: {ee}")

    except Exception as e:
        print(f"[log_service] ❌ Erro ao salvar log no JSON: {e}")


def get_logs_for_user(
    user_id: int,
    account_name: Optional[str] = None,
    limit: int = 50,
    level: Optional[str] = None
) -> List[dict]:
    """
    Busca logs de um usuário específico (APENAS seus logs)

    Args:
        user_id: ID do usuário
        account_name: Filtrar por conta específica (opcional)
        limit: Número máximo de logs
        level: Filtrar por nível (opcional)

    Returns:
        Lista de logs do usuário
    """
    try:
        from src.repositories import SystemLogRepository

        with get_db_session() as db:
            logs = SystemLogRepository.get_by_user(
                db=db,
                user_id=user_id,
                limit=limit,
                account_name=account_name,
                level=level
            )
            return [
                {
                    "id": log.id,
                    "created_at": log.created_at.isoformat(),  # ✅ CORRIGIDO
                    "message": log.message,
                    "level": log.level.value if hasattr(log.level, 'value') else str(log.level),
                    "account_name": log.account_name,
                    "module": log.module
                }
                for log in logs
            ]
    except Exception as e:
        print(f"[log_service] ⚠️ Erro ao buscar logs do banco: {e}")
        # Fallback: busca do JSON (menos preciso)
        return _get_logs_from_json(account_name=account_name, limit=limit)


def get_logs_for_admin(
    account_name: Optional[str] = None,
    limit: int = 50,
    level: Optional[str] = None
) -> List[dict]:
    """
    Busca TODOS os logs (apenas para admins)

    Args:
        account_name: Filtrar por conta específica (opcional)
        limit: Número máximo de logs
        level: Filtrar por nível (opcional)

    Returns:
        Lista de todos os logs
    """
    try:
        from src.repositories import SystemLogRepository

        with get_db_session() as db:
            if account_name:
                logs = SystemLogRepository.get_by_account(db=db, account_name=account_name, limit=limit)
            else:
                logs = SystemLogRepository.get_all(db=db, limit=limit, level=level)

            return [
                {
                    "id": log.id,
                    "created_at": log.created_at.isoformat(),  # ✅ CORRIGIDO
                    "message": log.message,
                    "level": log.level.value if hasattr(log.level, 'value') else str(log.level),
                    "account_name": log.account_name,
                    "module": log.module,
                    "user_id": log.user_id
                }
                for log in logs
            ]
    except Exception as e:
        print(f"[log_service] ⚠️ Erro ao buscar logs do banco: {e}")
        # Fallback: busca do JSON
        return _get_logs_from_json(account_name=account_name, limit=limit)


def _get_logs_from_json(account_name: Optional[str] = None, limit: int = 50) -> List[dict]:
    """Fallback: busca logs do arquivo JSON (menos preciso)"""
    try:
        data = json.loads(LOGS_JSON.read_text(encoding="utf-8"))
        logs = data.get("logs", [])

        # Filtra por conta se especificado
        if account_name:
            filtered = []
            acc_lower = account_name.lower()
            for log in logs:
                # Verifica campo direto ou mensagem
                if log.get("account_name") == account_name:
                    filtered.append(log)
                    continue

                msg = log.get("message", "").lower()
                if (f"[{acc_lower}]" in msg or
                    f"conta: {acc_lower}" in msg or
                    f"account: {acc_lower}" in msg):
                    filtered.append(log)
            return filtered[-limit:]

        return logs[-limit:]

    except Exception as e:
        print(f"[log_service] ❌ Erro ao ler logs do JSON: {e}")
        return []


def clear_logs(account_name: Optional[str] = None) -> dict:
    """
    Limpa logs do banco de dados e do arquivo JSON.

    Args:
        account_name: se informado, remove apenas logs dessa conta.

    Returns:
        Dict com contagem do que foi removido.
    """
    removed_db = 0
    removed_json = 0

    try:
        from src.repositories import SystemLogRepository

        with get_db_session() as db:
            if account_name:
                removed_db = SystemLogRepository.delete_by_account(db, account_name)
            else:
                removed_db = SystemLogRepository.delete_all(db)
    except Exception as exc:
        print(f"[log_service] ❌ Erro ao limpar logs no banco: {exc}")
        raise

    try:
        if LOGS_JSON.exists():
            raw = LOGS_JSON.read_text(encoding="utf-8")
            try:
                data = json.loads(raw)
                if not isinstance(data, dict):
                    data = {"logs": []}
            except (JSONDecodeError, ValueError):
                data = {"logs": []}

            logs = data.get("logs", [])
            if account_name:
                filtered = [log for log in logs if log.get("account_name") != account_name]
            else:
                filtered = []

            removed_json = len(logs) - len(filtered)
            data["logs"] = filtered

            tmp_name = f"{LOGS_JSON.name}.{uuid.uuid4().hex}.tmp"
            tmp_path = LOGS_JSON.parent / tmp_name
            tmp_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            os.replace(tmp_path, LOGS_JSON)
        else:
            LOGS_JSON.write_text(json.dumps({"logs": []}, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as exc:
        print(f"[log_service] ⚠️ Falha ao limpar logs do arquivo JSON: {exc}")

    return {"removed_db": removed_db, "removed_json": removed_json}

"""
⚠️ AVISO: Este módulo contém funções LEGADAS

Sistema moderno usa:
- src/account_storage.py (AccountStorage)
- src/repositories.py (TikTokAccountRepository)

Mantido apenas para compatibilidade com código antigo.
"""

import os
from .config import BASE_USER_DATA_DIR, BASE_VIDEO_DIR, BASE_POSTED_DIR, ACCOUNTS_FILE

# resolve diretórios por conta + criação

def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)

def account_dirs(account: str):
    user_data = os.path.join(BASE_USER_DATA_DIR, account)
    videos    = os.path.join(BASE_VIDEO_DIR, account)
    posted    = os.path.join(BASE_POSTED_DIR, account)
    for p in (user_data, videos, posted):
        ensure_dir(p)
    return user_data, videos, posted

def ensure_base():
    ensure_dir(BASE_USER_DATA_DIR)
    ensure_dir(BASE_VIDEO_DIR)
    ensure_dir(BASE_POSTED_DIR)

def load_accounts():
    """
    ⚠️ DEPRECADO: Use TikTokAccountRepository.list_by_user() do banco de dados

    Esta função é mantida apenas para compatibilidade com código legado.
    O sistema moderno usa PostgreSQL para gerenciar contas.
    """
    if os.path.exists(ACCOUNTS_FILE):
        try:
            import json
            with open(ACCOUNTS_FILE, "r") as f:
                accounts = json.load(f)
                if accounts:
                    return accounts
        except:
            pass

    # Não retorna mais "default" como fallback
    # Se não há contas no arquivo, retorna lista vazia
    print("⚠️ AVISO: Nenhuma conta encontrada em accounts.json")
    print("💡 Use a interface web para gerenciar contas: /tiktok-accounts")
    return []

def save_accounts(accounts):
    """
    ⚠️ DEPRECADO: Use TikTokAccountRepository.create() do banco de dados

    Esta função é mantida apenas para compatibilidade com código legado.
    O sistema moderno usa PostgreSQL para gerenciar contas.
    """
    import json
    print("⚠️ AVISO: save_accounts() está deprecada")
    print("💡 Use TikTokAccountRepository.create() para criar contas")
    with open(ACCOUNTS_FILE, "w") as f:
        json.dump(accounts, f)

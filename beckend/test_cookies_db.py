#!/usr/bin/env python3
"""
Testa se os cookies do banco podem ser carregados corretamente
"""
import sys
sys.path.insert(0, 'src')

from database import SessionLocal
from repositories import TikTokAccountRepository

def test_cookies_from_db():
    """Verifica se os cookies estão no banco e no formato correto"""
    print("🔍 Testando cookies do banco de dados...")

    db = SessionLocal()
    account = TikTokAccountRepository.get_by_name(db, 'novadigitalbra')

    if not account:
        print("❌ Conta não encontrada")
        db.close()
        return False

    if not account.cookies_data:
        print("❌ Cookies não encontrados")
        db.close()
        return False

    cookies = account.cookies_data
    print(f"✅ Encontrados cookies no banco")
    print(f"📊 Tipo: {type(cookies)}")
    print(f"📊 Quantidade: {len(cookies) if isinstance(cookies, (dict, list)) else 'N/A'}")

    if isinstance(cookies, dict):
        print(f"📋 Formato: Dict (nome:valor)")
        print(f"🔑 Cookies críticos:")
        critical = ['sessionid', 'sessionid_ss', 'msToken', 's_v_web_id']
        for key in critical:
            status = "✅" if key in cookies else "❌"
            print(f"   {status} {key}")

    elif isinstance(cookies, list):
        print(f"📋 Formato: Lista")
        print(f"🔑 Primeiro cookie: {cookies[0] if cookies else 'N/A'}")

    db.close()
    return True

if __name__ == "__main__":
    success = test_cookies_from_db()
    sys.exit(0 if success else 1)

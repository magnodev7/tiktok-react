#!/usr/bin/env python3
"""
Script para debugar login no TikTok com cookies
"""
import sys
sys.path.insert(0, 'src')

from driver import build_driver
from database import SessionLocal
from repositories import TikTokAccountRepository
import time

def test_tiktok_login():
    """Testa login no TikTok com cookies do banco"""
    print("🔧 Iniciando teste de login...")

    # Busca cookies do banco
    db = SessionLocal()
    account = TikTokAccountRepository.get_by_name(db, 'novadigitalbra')

    if not account or not account.cookies_data:
        print("❌ Cookies não encontrados no banco")
        db.close()
        return False

    print(f"✅ Encontrados {len(account.cookies_data)} cookies")
    db.close()

    # Cria driver
    driver = build_driver()

    try:
        # Vai para TikTok primeiro
        print("🌐 Acessando TikTok...")
        driver.get("https://www.tiktok.com")
        time.sleep(3)

        # Adiciona cookies
        print("🍪 Adicionando cookies...")
        for name, value in account.cookies_data.items():
            try:
                cookie_dict = {
                    'name': name,
                    'value': str(value),
                    'domain': '.tiktok.com'
                }
                driver.add_cookie(cookie_dict)
                print(f"  ✅ {name}")
            except Exception as e:
                print(f"  ❌ {name}: {e}")

        # Recarrega página
        print("🔄 Recarregando página...")
        driver.get("https://www.tiktok.com")
        time.sleep(5)

        # Verifica se está logado
        print("🔍 Verificando login...")
        current_url = driver.current_url
        page_source = driver.page_source[:500]

        print(f"📍 URL atual: {current_url}")
        print(f"📄 Início da página: {page_source[:200]}...")

        # Tenta acessar o Studio
        print("🎬 Tentando acessar Creator Studio...")
        driver.get("https://www.tiktok.com/creator-center/upload")
        time.sleep(5)

        current_url = driver.current_url
        print(f"📍 URL após Creator Studio: {current_url}")

        if "login" in current_url.lower():
            print("❌ Redirecionou para login - cookies inválidos")
            return False
        else:
            print("✅ Login bem-sucedido!")
            return True

    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        driver.quit()

if __name__ == "__main__":
    success = test_tiktok_login()
    sys.exit(0 if success else 1)

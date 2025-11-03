#!/usr/bin/env python3
# test_cookies.py - Teste isolado de cookies para TikTok
import os
import sys
import time
from pathlib import Path

# Adiciona o diretório src ao path (garante que funcione)
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    from src.scheduler import TikTokScheduler  # ← ABSOLUTO: Adiciona 'src.'
    from src.cookies import load_cookies_for_account
    from src.driver import get_fresh_driver, is_session_alive
except ImportError as e:
    print(f"❌ Erro de import: {e}")
    print("💡 Dica: Certifique-se de que está rodando do diretório 'beckend/' e instale dependências com 'pip3 install -r requirements.txt'")
    sys.exit(1)

# Configurações do teste
ACCOUNT_NAME = os.getenv("ACCOUNT_NAME", "novadigitalbra").strip() or "novadigitalbra"
VISIBLE = os.getenv("VISIBLE", "false").lower() in ("1", "true", "yes", "on")
TEST_MODE = os.getenv("TEST_MODE", "false").lower() == "true"

def main():
    print(f"🧪 Iniciando teste de cookies para conta: @{ACCOUNT_NAME}")
    print(f"   Visível: {VISIBLE}, Modo Teste: {TEST_MODE}")

    # Inicializa scheduler (só para pegar paths e logger)
    scheduler = TikTokScheduler(
        account_name=ACCOUNT_NAME,
        logger=print,  # Usa print como logger para simplicidade
        visible=False  # Scheduler não precisa ser visible
    )
    scheduler.initial_setup()

    # Cria driver fresco
    print("🔧 Criando driver Chrome...")
    driver = get_fresh_driver(
        None,
        profile_base_dir=scheduler.USER_DATA_DIR,
        account_name=ACCOUNT_NAME,
        headless=not VISIBLE,
    )

    try:
        # Testa se sessão já existe/alive
        if is_session_alive(driver):
            print("✅ Sessão Chrome já viva — pulando criação nova.")

        # Carrega e testa cookies
        print(f"🍪 Carregando cookies para @{ACCOUNT_NAME}...")
        ok = load_cookies_for_account(driver, ACCOUNT_NAME)
        print(f"   Resultado do load_cookies: {ok}")

        if ok:
            print("🧪 Testando sessão: Navegando para perfil...")
            driver.get(f"https://www.tiktok.com/@{ACCOUNT_NAME}")
            time.sleep(5)  # Aguarda load

            current_url = driver.current_url.lower()
            print(f"   URL atual: {current_url}")
            if "login" in current_url or "sign" in current_url:
                print("❌ Sessão inválida: Redirecionou para login.")
            else:
                print("✅ Sessão VÁLIDA: Perfil carregou sem redirecionar!")
                # Opcional: Printa title para mais debug
                print(f"   Título da página: {driver.title[:50]}...")
        else:
            print("❌ load_cookies_for_account retornou False — cookies inválidos/ausentes.")
            print("💡 Verifique o storage de cookies (ex.: state/accounts/novadigitalbra_cookies.json)")
            try:
                cookie_names = [c.get("name") for c in driver.get_cookies()]
                print(f"   Cookies carregados no driver: {cookie_names}")
            except Exception as debug_err:
                print(f"   ⚠️ Falha ao ler cookies do driver: {debug_err}")

            try:
                current_url = driver.current_url
                print(f"   URL atual após tentativa: {current_url}")
                page_snippet = driver.page_source[:500].replace("\n", " ")
                print(f"   Trecho da página: {page_snippet} ...")
                screenshot_path = Path(__file__).parent / "cookies_debug.png"
                if driver.save_screenshot(str(screenshot_path)):
                    print(f"   📸 Screenshot salvo em: {screenshot_path}")
            except Exception as debug_err:
                print(f"   ⚠️ Falha ao coletar debug adicional: {debug_err}")

    except Exception as e:
        print(f"⚠️ Erro durante o teste: {e}")
        import traceback
        traceback.print_exc()

    finally:
        print("🧹 Limpando driver...")
        driver.quit()
        print("✅ Teste concluído!")

if __name__ == "__main__":
    main()

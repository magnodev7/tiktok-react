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

# Função para obter o nome da conta dinamicamente
def get_account_name():
    # Define o diretório correto onde as pastas das contas são armazenadas
    accounts_dir = Path("/home/magnod/work/tiktok-react/beckend/user_data/")
    
    # Verifica se o diretório existe
    if not accounts_dir.exists():
        print(f"❌ Diretório de contas não encontrado: {accounts_dir}")
        sys.exit(1)
    
    # Lista as pastas dentro do diretório de contas e retorna a primeira encontrada
    account_folders = [folder.name for folder in accounts_dir.iterdir() if folder.is_dir()]
    
    if account_folders:
        # Usamos a primeira pasta encontrada como nome da conta
        return account_folders[0]
    else:
        print("❌ Nenhuma conta encontrada no diretório de contas.")
        sys.exit(1)

# Configurações do teste
ACCOUNT_NAME = os.getenv("ACCOUNT_NAME") or get_account_name()  # Dinâmico, busca no diretório
VISIBLE = os.getenv("VISIBLE", "false").lower() in ("1", "true", "yes", "on")
TEST_MODE = os.getenv("TEST_MODE", "false").lower() == "true"
TEMP_PROFILE = os.getenv("TEMP_PROFILE", "false").lower() in ("1", "true", "yes", "on")

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
    base_dir = None if (TEMP_PROFILE or TEST_MODE) else scheduler.USER_DATA_DIR
    driver = get_fresh_driver(
        None,
        profile_base_dir=base_dir,
        account_name=ACCOUNT_NAME,
        headless=not VISIBLE,
        force_temp_profile=TEMP_PROFILE or TEST_MODE,
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
            print("💡 Verifique o storage de cookies (ex.: user_data/accounts/novadigitalbra_cookies.json)")
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

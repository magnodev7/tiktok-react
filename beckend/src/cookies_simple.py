"""
Sistema SIMPLIFICADO de cookies para TikTok
Baseado no tiktok_bot que funciona sem falhas

Mudanças vs cookies.py (573 linhas):
- 90% mais simples (~50 linhas vs 573)
- Sem sistema de normalização complexo
- Sem localStorage/sessionStorage
- Sem CDP fallbacks
- Sem markers de cookies inválidos
- Carrega direto do arquivo ou banco
"""
import json
import time
import logging
from typing import Optional, List, Dict, Any
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

logger = logging.getLogger("cookies_simple")


def load_cookies_simple(
    driver: WebDriver,
    account_name: str,
    base_url: str = "https://www.tiktok.com"
) -> bool:
    """
    Carrega cookies de forma SIMPLES (como tiktok_bot).

    Args:
        driver: WebDriver do Selenium
        account_name: Nome da conta TikTok
        base_url: URL base do TikTok

    Returns:
        True se login bem-sucedido, False caso contrário
    """
    logger.info(f"🔍 Carregando cookies para: {account_name}")
    print(f"🔍 Carregando cookies para: {account_name}")

    # 1. Busca cookies do banco de dados
    from .account_storage import AccountStorage
    storage = AccountStorage()
    auth_bundle = storage.get_latest_cookies(account_name)

    if not auth_bundle:
        logger.error(f"❌ Cookies não encontrados: {account_name}")
        print(f"❌ Cookies não encontrados: {account_name}")
        return False

    # 2. Extrai lista de cookies (suporta formato direto ou com chave "cookies")
    if isinstance(auth_bundle, dict) and "cookies" in auth_bundle:
        cookies_list = auth_bundle["cookies"]
    elif isinstance(auth_bundle, list):
        cookies_list = auth_bundle
    else:
        logger.error(f"❌ Formato de cookies inválido: {account_name}")
        print(f"❌ Formato de cookies inválido: {account_name}")
        return False

    # 3. Navega para TikTok
    try:
        logger.info(f"🌐 Navegando para {base_url}...")
        print(f"🌐 Navegando para {base_url}...")
        driver.set_page_load_timeout(30)
        driver.get(base_url)
        time.sleep(2)
    except Exception as e:
        logger.error(f"❌ Erro ao navegar: {e}")
        print(f"❌ Erro ao navegar: {e}")
        return False

    # 4. Limpa cookies existentes
    try:
        driver.delete_all_cookies()
    except:
        pass

    # 5. Adiciona cookies (SIMPLES - remove apenas campos problemáticos)
    logger.info(f"🍪 Adicionando {len(cookies_list)} cookies...")
    print(f"🍪 Adicionando {len(cookies_list)} cookies...")

    cookies_added = 0
    for cookie in cookies_list:
        try:
            # Remove campos que o Selenium não aceita (como tiktok_bot)
            cookie_clean = dict(cookie)
            cookie_clean.pop('sameSite', None)
            cookie_clean.pop('expiry', None)
            cookie_clean.pop('expirationDate', None)
            cookie_clean.pop('hostOnly', None)
            cookie_clean.pop('storeId', None)

            driver.add_cookie(cookie_clean)
            cookies_added += 1
        except Exception as e:
            # Ignora cookies que falharem (não trava por causa de 1 cookie)
            logger.debug(f"Cookie {cookie.get('name')} falhou: {e}")
            continue

    logger.info(f"🍪 {cookies_added}/{len(cookies_list)} cookies adicionados")
    print(f"🍪 {cookies_added}/{len(cookies_list)} cookies adicionados")

    # 6. Recarrega página com cookies
    logger.info("🔄 Recarregando com cookies...")
    print("🔄 Recarregando com cookies...")
    try:
        driver.refresh()
        time.sleep(3)
    except Exception as e:
        logger.warning(f"⚠️ Erro ao recarregar: {e}")
        print(f"⚠️ Erro ao recarregar: {e}")

    # 7. Verifica se está logado (procura ícone de upload)
    logger.info("✅ Verificando login...")
    print("✅ Verificando login...")

    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-e2e='upload-icon']"))
        )
        logger.info(f"✅ Login bem-sucedido: {account_name}")
        print(f"✅ Login bem-sucedido: {account_name}")
        return True
    except:
        # Tenta ir direto para /upload
        try:
            driver.get("https://www.tiktok.com/upload")
            time.sleep(2)
            WebDriverWait(driver, 8).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-e2e='upload-icon']"))
            )
            logger.info(f"✅ Login bem-sucedido (via /upload): {account_name}")
            print(f"✅ Login bem-sucedido (via /upload): {account_name}")
            return True
        except:
            logger.error(f"❌ Login falhou: {account_name}")
            print(f"❌ Login falhou: {account_name}")
            return False


def save_cookies_simple(driver: WebDriver, account_name: str) -> bool:
    """
    Salva cookies de forma SIMPLES.

    Args:
        driver: WebDriver do Selenium
        account_name: Nome da conta TikTok

    Returns:
        True se salvou com sucesso
    """
    try:
        cookies = driver.get_cookies()

        # Salva no formato simples (apenas cookies, sem localStorage/sessionStorage)
        payload = {"cookies": cookies}

        from .account_storage import AccountStorage
        storage = AccountStorage()
        cookies_path = storage.save_cookies(account_name, payload)

        logger.info(f"✅ Cookies salvos: {cookies_path}")
        print(f"✅ Cookies salvos: {cookies_path}")
        return True
    except Exception as e:
        logger.error(f"❌ Erro ao salvar cookies: {e}")
        print(f"❌ Erro ao salvar cookies: {e}")
        return False

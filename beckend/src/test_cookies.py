# src/test_cookies.py
import time

from src.cookies import load_cookies_for_account
from src.driver import get_fresh_driver, is_session_alive


def validate_cookies_for_account(account_name: str, visible: bool = False, test_mode: bool = False) -> dict:
    """
    Executa o fluxo completo de validação de cookies para uma conta.
    Retorna um dicionário serializável com status/mensagem e metadados opcionais.
    """
    driver = None
    try:
        driver = get_fresh_driver(
            None,
            profile_base_dir=None,
            account_name=account_name,
            headless=not visible,
        )

        if is_session_alive(driver):
            print("✅ Sessão Chrome já viva — pulando criação nova.")

        print(f"🍪 Carregando cookies para @{account_name}...")
        ok = load_cookies_for_account(driver, account_name)
        if not ok:
            return {"status": "error", "message": "Cookies inválidos ou ausentes."}

        driver.get(f"https://www.tiktok.com/@{account_name}")
        time.sleep(5)
        current_url = (driver.current_url or "").lower()
        if any(keyword in current_url for keyword in ("login", "sign")):
            return {"status": "error", "message": "Sessão inválida: redirecionou para tela de login."}

        return {
            "status": "success",
            "message": "Sessão válida.",
            "profile_url": current_url,
            "title": (driver.title or "")[:80],
        }
    except Exception as exc:  # pragma: no cover - Selenium falhas imprevisíveis
        return {"status": "error", "message": f"Erro durante o teste: {exc}"}
    finally:
        if driver is not None:
            try:
                driver.quit()
            except Exception:
                pass

import json
import time
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Iterable, List
from urllib.parse import urlparse

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.common.exceptions import TimeoutException, WebDriverException

from datetime import datetime, timezone

from .account_storage import AccountStorage

logger = logging.getLogger("cookies")


def _normalise_domain(raw: Optional[str]) -> str:
    """Normalise cookie domain so Selenium/Chrome accept it."""
    if not raw:
        return ".tiktok.com"

    domain = raw.strip()
    if not domain:
        return ".tiktok.com"

    if domain.startswith("http://") or domain.startswith("https://"):
        domain = urlparse(domain).netloc or domain

    # Remove leading dots just to reapply a single canonical dot afterwards
    domain = domain.lstrip(".")

    if not domain:
        return ".tiktok.com"

    # TikTok usa múltiplos subdomínios, mas o ponto inicial garante abrangência
    if not domain.startswith("."):
        domain = f".{domain}"

    return domain


def _coerce_same_site(value: Optional[Any]) -> Optional[str]:
    if value is None:
        return None

    mapping = {
        "unspecified": None,
        "no_restriction": "None",
        "none": "None",
        "lax": "Lax",
        "strict": "Strict",
    }

    stringified = str(value).strip().lower()
    return mapping.get(stringified, None)


def _normalise_cookie_entry(cookie: Dict[str, Any]) -> Dict[str, Any]:
    """Converte a estrutura de cookie (possivelmente heterogênea) no formato aceito pelo Selenium."""
    normalised: Dict[str, Any] = {}

    name = cookie.get("name")
    value = cookie.get("value")
    if not name or value is None:
        return {}

    normalised["name"] = str(name)
    normalised["value"] = str(value)

    normalised["domain"] = _normalise_domain(cookie.get("domain"))
    normalised["path"] = cookie.get("path") or "/"

    same_site = _coerce_same_site(
        cookie.get("sameSite")
        or cookie.get("same_site")
        or cookie.get("same_site_policy")
    )
    if same_site:
        normalised["sameSite"] = same_site

    secure = cookie.get("secure")
    if secure is None:
        # Cookies de autenticação do TikTok são sempre "secure"
        secure = True
    normalised["secure"] = bool(secure)

    http_only = cookie.get("httpOnly")
    if http_only is not None:
        normalised["httpOnly"] = bool(http_only)

    expires = cookie.get("expires", cookie.get("expiry"))
    if expires:
        try:
            # Aceita int/float/string representando timestamp em segundos
            normalised["expiry"] = int(float(expires))
        except (TypeError, ValueError):
            pass

    # Remove campos que costumam quebrar a API do Selenium
    for noisy in ("expirationDate", "hostOnly", "creation_utc", "priority"):
        if noisy in normalised:
            normalised.pop(noisy, None)

    return normalised


def _flatten_cookie_collection(raw: Any) -> List[Dict[str, Any]]:
    """Extrai entradas de cookies de estruturas aninhadas ou formatos exportados."""
    flat: List[Dict[str, Any]] = []
    stack: List[Any] = [raw]

    while stack:
        current = stack.pop()
        if current is None:
            continue
        if isinstance(current, list):
            stack.extend(current)
            continue
        if isinstance(current, dict):
            # Formato direto
            value = current.get("value")
            if current.get("name") and not isinstance(value, (list, dict)):
                flat.append(current)

            # Formatos "cookies": [...]
            candidate = current.get("cookies")
            if candidate is not None:
                stack.append(candidate)

            # Alguns exportadores aninham os cookies dentro do campo value (ex.: EditThisCookie)
            if isinstance(value, (list, dict)):
                stack.append(value)

            continue

    return flat


def _set_cookie_via_cdp(driver: WebDriver, cookie: Dict[str, Any], base_url: str) -> bool:
    """Fallback para injetar cookies via CDP quando add_cookie falha."""
    try:
        driver.execute_cdp_cmd("Network.enable", {})
        domain = cookie["domain"].lstrip(".") or "www.tiktok.com"
        payload = {
            "name": cookie["name"],
            "value": cookie["value"],
            "domain": domain,
            "path": cookie.get("path", "/"),
            "secure": cookie.get("secure", False),
            "httpOnly": cookie.get("httpOnly", False),
        }

        same_site = cookie.get("sameSite")
        if same_site:
            payload["sameSite"] = same_site

        expiry = cookie.get("expiry")
        if expiry:
            payload["expires"] = int(expiry)

        # Quando o domínio é genérico (.tiktok.com), o CDP exige uma URL de contexto
        cookie_url = base_url
        if domain:
            cookie_url = f"https://{domain.strip('/')}/"
        payload.setdefault("url", cookie_url)

        driver.execute_cdp_cmd("Network.setCookie", payload)
        return True
    except Exception as e:
        logger.debug(f"CDP setCookie falhou para {cookie.get('name')}: {e}")
        return False


def _account_cookie_marker(account_name: str) -> Path:
    storage = AccountStorage()
    structure = storage.get_account_structure(account_name)
    structure["cookies"].mkdir(parents=True, exist_ok=True)
    return structure["cookies"] / "cookies_invalid.json"


def mark_cookies_invalid(account_name: str, reason: str) -> None:
    marker = _account_cookie_marker(account_name)
    payload = {
        "account": account_name,
        "reason": reason,
        "marked_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        marker.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        logger.debug("Não foi possível gravar marker de cookies inválidos", exc_info=True)


def clear_cookies_invalid_marker(account_name: str) -> None:
    marker = _account_cookie_marker(account_name)
    if marker.exists():
        try:
            marker.unlink()
        except Exception:
            logger.debug("Não foi possível remover marker de cookies inválidos", exc_info=True)


def cookies_marked_invalid(account_name: str) -> bool:
    marker = _account_cookie_marker(account_name)
    return marker.exists()


def _cookies_expired(cookies_list: List[Dict[str, Any]]) -> bool:
    now_ts = int(datetime.now(timezone.utc).timestamp())
    expiries = [int(cookie.get("expiry")) for cookie in cookies_list if cookie.get("expiry")]
    if expiries and min(expiries) <= now_ts:
        return True
    return False

def load_cookies_for_account(
    driver: WebDriver,
    account_name: str,
    base_url: str = "https://www.tiktok.com/"
) -> bool:
    from .account_storage import AccountStorage

    base_url = (base_url or "").strip() or "https://www.tiktok.com/"
    if not account_name or not account_name.strip():
        logger.error("❌ ERRO: account_name é obrigatório")
        print("❌ ERRO: account_name é obrigatório")
        return False

    logger.info(f"🔍 Tentando carregar cookies para conta: {account_name}")
    print(f"🔍 Tentando carregar cookies para conta: {account_name}")

    storage = AccountStorage()
    cookies_data = storage.get_latest_cookies(account_name)

    if not cookies_data:
        logger.error(f"❌ Cookies não encontrados para conta: {account_name}")
        print(f"❌ Cookies não encontrados para conta: {account_name}")
        return False

    # Tenta navegar para o TikTok
    initial_timeout = False
    try:
        logger.info(f"🌐 Navegando para {base_url}...")
        print(f"🌐 Navegando para {base_url}...")
        driver.set_page_load_timeout(60)
        driver.get(base_url)
        logger.info(f"✅ Página carregada: {driver.current_url}")
        print(f"✅ Página carregada: {driver.current_url}")

        current_after_first_load = driver.current_url.lower()
        already_logged = "login" not in current_after_first_load and "tiktok.com" in current_after_first_load

        # Se já está logado, apenas reforça scripts anti-detecção e persiste cookies mais recentes
        if already_logged:
            logger.info(f"🔁 Sessão já ativa para '{account_name}', pulando reinjeção de cookies")
            print(f"🔁 Sessão já ativa para '{account_name}', pulando reinjeção de cookies")
            try:
                driver.execute_script(
                    "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
                )
                driver.execute_script("window.navigator.chrome = {runtime: {}}")
                driver.execute_script("delete navigator.__proto__.webdriver")
            except Exception:
                pass
            save_cookies_for_account(driver, account_name)
            return True

        try:
            driver.delete_all_cookies()
        except Exception:
            pass

        # Executa scripts anti-detecção APÓS navegar para TikTok
        logger.info("🛡️ Aplicando scripts anti-detecção...")
        print("🛡️ Aplicando scripts anti-detecção...")
        try:
            driver.execute_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
            driver.execute_script("window.navigator.chrome = {runtime: {}}")
            driver.execute_script("delete navigator.__proto__.webdriver")
            logger.info("✅ Scripts anti-detecção aplicados")
            print("✅ Scripts anti-detecção aplicados")
        except Exception as e:
            logger.warning(f"⚠️ Falha ao aplicar scripts anti-detecção: {e}")
            print(f"⚠️ Falha ao aplicar scripts anti-detecção: {e}")
            # Continua mesmo se falhar

    except TimeoutException as e:
        initial_timeout = True
        logger.warning(f"⏱️ Timeout ao carregar {base_url} (prosseguindo mesmo assim): {e}")
        print(f"⏱️ Timeout ao carregar {base_url} (prosseguindo mesmo assim): {e}")
    except WebDriverException as e:
        logger.error(f"❌ Erro WebDriver ao carregar página: {e}")
        print(f"❌ Erro WebDriver ao carregar página: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Erro inesperado ao carregar página: {e}")
        print(f"❌ Erro inesperado ao carregar página: {e}")
        return False

    if initial_timeout:
        try:
            driver.execute_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
            driver.execute_script("window.navigator.chrome = {runtime: {}}")
            driver.execute_script("delete navigator.__proto__.webdriver")
        except Exception as e:
            logger.warning(f"⚠️ Falha ao aplicar scripts anti-detecção após timeout: {e}")
            print(f"⚠️ Falha ao aplicar scripts anti-detecção após timeout: {e}")

    # Parse cookies
    cookies_list: List[Dict[str, Any]] = []
    if isinstance(cookies_data, dict) and "cookies" in cookies_data:
        cookies_list = _flatten_cookie_collection(cookies_data["cookies"])
    elif isinstance(cookies_data, list):
        cookies_list = _flatten_cookie_collection(cookies_data)
    elif isinstance(cookies_data, dict):
        cookies_list = [
            {"name": name, "value": str(value), "domain": ".tiktok.com"}
            for name, value in cookies_data.items()
        ]

    if not cookies_list:
        logger.error(f"❌ Formato de cookies inválido para: {account_name}")
        print(f"❌ Formato de cookies inválido para: {account_name}")
        return False

    if _cookies_expired(cookies_list):
        reason = "cookies expirados"
        logger.error(f"❌ Cookies expirados para conta: {account_name}")
        print(f"❌ Cookies expirados para conta: {account_name}")
        mark_cookies_invalid(account_name, reason)
        return False

    # Adiciona cookies
    logger.info(f"🍪 Adicionando {len(cookies_list)} cookies...")
    print(f"🍪 Adicionando {len(cookies_list)} cookies...")
    cookies_added = 0
    cookies_failed = 0

    for idx, original_cookie in enumerate(cookies_list, 1):
        try:
            cookie = _normalise_cookie_entry(original_cookie)
            if not cookie:
                continue

            try:
                driver.add_cookie(cookie)
                added = True
            except WebDriverException as e:
                logger.warning(
                    f"⚠️ Erro ao adicionar cookie #{idx} '{cookie.get('name', 'unknown')}': {e}"
                )
                print(
                    f"⚠️ Erro ao adicionar cookie #{idx} '{cookie.get('name', 'unknown')}': {e}"
                )
                added = _set_cookie_via_cdp(driver, cookie, base_url)

            if added:
                cookies_added += 1
                if idx % 10 == 0:
                    logger.info(f"  ✓ {idx}/{len(cookies_list)} cookies adicionados...")
                    print(f"  ✓ {idx}/{len(cookies_list)} cookies adicionados...")
            else:
                cookies_failed += 1
                logger.warning(
                    f"⚠️ Cookie #{idx} '{cookie.get('name', 'unknown')}' não pôde ser aplicado"
                )
                print(
                    f"⚠️ Cookie #{idx} '{cookie.get('name', 'unknown')}' não pôde ser aplicado"
                )
        except Exception as e:
            cookies_failed += 1
            logger.warning(f"⚠️ Erro inesperado ao preparar cookie #{idx}: {e}")
            print(f"⚠️ Erro inesperado ao preparar cookie #{idx}: {e}")

    logger.info(f"🍪 Cookies: {cookies_added} adicionados, {cookies_failed} falharam")
    print(f"🍪 Cookies: {cookies_added} adicionados, {cookies_failed} falharam")

    # Navega novamente para a página inicial (não apenas refresh)
    second_timeout = False
    try:
        logger.info(f"🔄 Navegando novamente para {base_url} com cookies...")
        print(f"🔄 Navegando novamente para {base_url} com cookies...")
        driver.get(base_url)

        # Aplica scripts anti-detecção novamente
        try:
            driver.execute_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
            driver.execute_script("window.navigator.chrome = {runtime: {}}")
            driver.execute_script("delete navigator.__proto__.webdriver")
        except Exception:
            pass  # Não loga erro, apenas tenta

        time.sleep(3)
        logger.info(f"✅ Página carregada com cookies: {driver.current_url}")
        print(f"✅ Página carregada com cookies: {driver.current_url}")
    except TimeoutException as e:
        second_timeout = True
        logger.warning(f"⏱️ Timeout ao navegar com cookies (prosseguindo com validação): {e}")
        print(f"⏱️ Timeout ao navegar com cookies (prosseguindo com validação): {e}")
    except WebDriverException as e:
        logger.error(f"❌ Erro ao navegar com cookies: {e}")
        print(f"❌ Erro ao navegar com cookies: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Erro inesperado ao navegar com cookies: {e}")
        print(f"❌ Erro inesperado ao navegar com cookies: {e}")
        return False

    # Verifica se está logado
    current_url = driver.current_url.lower()
    is_logged_in = "login" not in current_url and "tiktok.com" in current_url

    if is_logged_in:
        logger.info(f"✅ Login bem-sucedido para conta: {account_name}")
        print(f"✅ Login bem-sucedido para conta: {account_name}")
        try:
            save_cookies_for_account(driver, account_name)
            clear_cookies_invalid_marker(account_name)
        except Exception as e:
            logger.warning(f"⚠️ Falha ao persistir cookies atualizados para '{account_name}': {e}")
    else:
        reason = "timeout parcial" if (initial_timeout or second_timeout) else "redirecionado para login"
        logger.error(f"❌ Falha no login para conta: {account_name} (URL atual: {current_url}) [{reason}]")
        print(f"❌ Falha no login para conta: {account_name} (URL atual: {current_url}) [{reason}]")
        mark_cookies_invalid(account_name, reason)

    return is_logged_in


def save_cookies_for_account(driver: WebDriver, account_name: str) -> Optional[Path]:
    from .account_storage import AccountStorage

    if not account_name or not account_name.strip():
        print("❌ ERRO: account_name é obrigatório")
        return None

    try:
        cookies = driver.get_cookies()
        storage = AccountStorage()
        cookies_path = storage.save_cookies(account_name, cookies)
        print(f"✅ Cookies salvos para conta '{account_name}': {cookies_path}")
        return cookies_path
    except Exception as e:
        print(f"❌ Erro ao salvar cookies para '{account_name}': {e}")
        return None

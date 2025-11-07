"""
Driver SIMPLIFICADO para Chrome
Baseado no tiktok_bot que funciona sem falhas

Mudanças vs driver.py (481 linhas):
- 80% mais simples (~100 linhas vs 481)
- SEM sistema de locks (threading.Lock, fcntl)
- SEM perfis persistentes (usa temporários)
- SEM limpeza de processos
- SEM runtime profiles
- Chrome gerencia seus próprios locks nativamente!
"""
import os
import tempfile
import uuid
from pathlib import Path
from typing import Optional

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import (
    InvalidSessionIdException,
    WebDriverException,
    SessionNotCreatedException,
)
from webdriver_manager.chrome import ChromeDriverManager


def _is_remote() -> bool:
    """Verifica se deve usar Selenium Grid remoto"""
    return bool(os.getenv("SELENIUM_HUB_URL"))


def _build_chrome_options(headless: bool = True) -> Options:
    """
    Configuração SIMPLES do Chrome (como tiktok_bot).

    Args:
        headless: Se True, executa em modo headless

    Returns:
        Opções configuradas do Chrome
    """
    opts = Options()

    # Opções essenciais (mínimo necessário)
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-blink-features=AutomationControlled")

    # Headless moderno
    if headless:
        opts.add_argument("--headless=new")

    # User-Agent realista
    opts.add_argument(
        "user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    # Preferências básicas
    prefs = {
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False,
    }
    opts.add_experimental_option("prefs", prefs)
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)

    # Page load strategy mais rápido
    opts.page_load_strategy = "eager"

    return opts


def _resolve_profile_dir(
    profile_base_dir: Optional[str],
    force_temp: bool = False,
) -> Path:
    """
    Resolve diretório de perfil. Sempre cria diretório exclusivo quando necessário.
    """
    if force_temp or not profile_base_dir:
        temp_profile = Path(tempfile.mkdtemp(prefix="chrome-profile-"))
        return temp_profile

    base = Path(profile_base_dir)
    temp_env = os.getenv("TEMP_PROFILE") == "1"
    if temp_env:
        runtime = Path(tempfile.mkdtemp(prefix="chrome-runtime-", dir=str(base)))
        return runtime

    base.mkdir(parents=True, exist_ok=True)
    return base


def build_driver(
    account_name: Optional[str] = None,
    profile_base_dir: Optional[str] = None,
    headless: bool = True,
    force_temp_profile: bool = False,
    use_profile_dir: bool = True,
) -> webdriver.Chrome:
    """
    Cria driver do Chrome de forma SIMPLES (como tiktok_bot).

    Args:
        headless: Se True, executa em modo headless

    Returns:
        WebDriver configurado

    Raises:
        Exception: Se falhar ao criar driver
    """
    profile_dir: Optional[Path] = None
    if use_profile_dir:
        profile_dir = _resolve_profile_dir(
            profile_base_dir,
            force_temp_profile or _is_remote(),
        )

    if _is_remote():
        hub_url = os.getenv("SELENIUM_HUB_URL", "http://selenium:4444").rstrip("/") + "/wd/hub"
        print(f"🌐 Usando Selenium Grid: {hub_url}")

        opts = _build_chrome_options(headless)

        if profile_dir:
            opts.add_argument(f"--user-data-dir={profile_dir}")
            print(f"📁 Chrome user-data-dir: {profile_dir}")

        driver = webdriver.Remote(
            command_executor=hub_url,
            options=opts,
        )
    else:
        # Ambiente local
        print("🔧 Usando Chrome local")

        opts = _build_chrome_options(headless)

        if profile_dir:
            opts.add_argument(f"--user-data-dir={profile_dir}")
            print(f"📁 Chrome user-data-dir: {profile_dir}")

        # Usa webdriver-manager para garantir versão compatível
        driver_path = os.getenv("CHROMEDRIVER_PATH")
        if not driver_path:
            driver_path = ChromeDriverManager(driver_version="141.0.7390.0").install()
            print(f"📦 ChromeDriver: {driver_path}")

        service = Service(driver_path)

        # Força Chrome instalado (não Flatpak)
        chrome_binary = os.getenv("CHROME_BINARY", "/opt/google/chrome/chrome")
        if os.path.isfile(chrome_binary):
            opts.binary_location = chrome_binary
            print(f"📌 Chrome: {chrome_binary}")

        driver = webdriver.Chrome(service=service, options=opts)

    # Scripts anti-detecção (executados logo após criar driver)
    try:
        driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        driver.execute_script("window.navigator.chrome = {runtime: {}}")
    except:
        pass

    # Timeouts razoáveis (não extremos como 180s)
    try:
        driver.set_page_load_timeout(60)
        driver.implicitly_wait(0)
    except:
        pass

    print(f"✅ Chrome criado (session: {driver.session_id})")
    return driver


def is_session_alive(driver: Optional[webdriver.Chrome]) -> bool:
    """
    Verifica se a sessão do WebDriver está viva.

    Args:
        driver: WebDriver a verificar

    Returns:
        True se sessão está viva, False caso contrário
    """
    if driver is None:
        return False

    try:
        _ = driver.session_id
        driver.execute_script("return 1")
        return True
    except (InvalidSessionIdException, WebDriverException):
        return False


def get_or_create_driver(
    existing: Optional[webdriver.Chrome] = None,
    headless: bool = True
) -> webdriver.Chrome:
    """
    Reaproveita driver existente se válido, senão cria novo.

    Args:
        existing: Driver existente (pode ser None)
        headless: Se True, cria em modo headless

    Returns:
        WebDriver válido
    """
    # Se existe e está vivo, reutiliza
    if is_session_alive(existing):
        return existing

    # Senão, encerra o antigo e cria novo
    if existing is not None:
        try:
            existing.quit()
        except:
            pass

    return build_driver(headless=headless)


def get_fresh_driver(
    existing: Optional[webdriver.Chrome] = None,
    profile_base_dir: Optional[str] = None,
    account_name: Optional[str] = None,
    headless: bool = True,
    force_temp_profile: bool = False,
) -> webdriver.Chrome:
    """
    Compatibilidade com código antigo: sempre cria driver novo.

    Args:
        existing: Driver existente (será fechado se não for None)
        profile_base_dir: Ignorado (para compatibilidade)
        account_name: Ignorado (para compatibilidade)

    Returns:
        WebDriver novo
    """
    # Fecha driver antigo se existir
    if existing is not None:
        try:
            existing.quit()
        except:
            pass

    try:
        return build_driver(
            account_name=account_name,
            profile_base_dir=profile_base_dir,
            headless=headless,
            force_temp_profile=force_temp_profile,
            use_profile_dir=not force_temp_profile,
        )
    except SessionNotCreatedException as exc:
        message = str(exc)
        if "user data directory is already in use" in message.lower():
            runtime_dir = (
                Path(profile_base_dir) / "runtime" / f"session-{uuid.uuid4().hex}"
                if profile_base_dir
                else None
            )
            print("⚠️ Perfil em uso; criando runtime temporário para evitar conflito.")
            return build_driver(
                account_name=account_name,
                profile_base_dir=str(runtime_dir) if runtime_dir else None,
                headless=headless,
                force_temp_profile=True,
                use_profile_dir=False,
            )
        raise

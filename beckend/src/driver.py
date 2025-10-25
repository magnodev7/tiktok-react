# src/driver.py - Versão OTIMIZADA para VPS + TikTok + Chrome Local
import os
import time
import tempfile
import shutil
import uuid
import signal
import subprocess
import fcntl
from selenium import webdriver  # pyright: ignore[reportMissingImports]
from selenium.webdriver.chrome.options import Options  # pyright: ignore[reportMissingImports]
from selenium.webdriver.chrome.service import Service  # pyright: ignore[reportMissingImports]
from selenium.common.exceptions import ( # pyright: ignore[reportMissingImports]
    SessionNotCreatedException,
    WebDriverException,
    InvalidSessionIdException,
)  # pyright: ignore[reportMissingImports]
from webdriver_manager.chrome import ChromeDriverManager  # pyright: ignore[reportMissingImports]
from typing import Optional, List

def _is_remote() -> bool:
    return bool(os.getenv("SELENIUM_HUB_URL"))

def _hub_url() -> str:
    # Endpoint do Grid; sempre acrescente /wd/hub
    return os.getenv("SELENIUM_HUB_URL", "http://selenium:4444").rstrip("/") + "/wd/hub"

def _remote_options_full(user_data_dir: Optional[str] = None) -> Options:
    opts = Options()

    # Opções essenciais para ambiente headless em container
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")  # Evita crashes em container
    opts.add_argument("--disable-gpu")
    opts.add_argument("--disable-extensions")
    opts.add_argument("--disable-infobars")
    opts.add_argument("--disable-notifications")
    opts.add_argument("--disable-popup-blocking")
    opts.add_argument("--disable-default-apps")
    opts.add_argument("--disable-features=VizDisplayCompositor")
    opts.add_argument("--disable-features=IsolateOrigins,site-per-process")
    opts.add_argument("--disable-software-rasterizer")
    opts.add_argument("--disable-setuid-sandbox")
    opts.add_argument("--disable-accelerated-2d-canvas")
    opts.add_argument("--remote-debugging-pipe")

    # Anti-detecção do TikTok
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)

    # Configurações visuais e de navegação
    opts.add_argument("--headless=chrome")  # Headless antigo costuma ser mais estável
    opts.add_argument("--window-size=1920,1080")  # Tamanho consistente
    opts.add_argument("--lang=pt-BR")
    opts.add_argument("--no-first-run")
    opts.add_argument("--no-service-autorun")
    opts.add_argument("--password-store=basic")

    if user_data_dir:
        opts.add_argument(f"--user-data-dir={user_data_dir}")
    else:
        opts.add_argument("--user-data-dir=/tmp/chrome-user-data")

    # User-Agent realista para evitar detecção
    opts.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )

    # Preferências do Chrome
    prefs = {
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False,
        "profile.default_content_setting_values.notifications": 2,
        "profile.default_content_settings.popups": 0,
        "profile.managed_default_content_settings.images": 1,
        "profile.default_content_setting_values.media_stream": 1,
    }
    opts.add_experimental_option("prefs", prefs)
    opts.page_load_strategy = "eager"

    return opts

REUSE_PROFILE = os.getenv("PERSIST_CHROME_PROFILE", "1").lower() in ("1", "true", "yes", "on")


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def _collect_profile_processes(targets: List[str]) -> List[int]:
    try:
        output = subprocess.check_output(["ps", "-eo", "pid,args"], text=True)
    except Exception:
        return []

    pids: List[int] = []
    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split(maxsplit=1)
        if len(parts) != 2:
            continue
        pid_str, cmd = parts
        if not any(t in cmd for t in targets):
            continue
        if "chrome" not in cmd and "chromedriver" not in cmd:
            continue
        try:
            pid = int(pid_str)
        except ValueError:
            continue
        if pid == os.getpid():
            continue
        pids.append(pid)
    return pids


def _cleanup_conflicting_processes(profile_dir: Optional[str]) -> None:
    if not profile_dir:
        return

    parent = os.path.dirname(profile_dir.rstrip(os.sep))
    grandparent = os.path.dirname(parent) if parent else ""
    targets = [profile_dir]
    if parent:
        targets.append(parent)
    if grandparent:
        targets.append(grandparent)
    victims = _collect_profile_processes(targets)

    if not victims:
        return

    print(f"🧹 Encerrando {len(victims)} processos presos (cleanup abrangente)")
    for sig in (signal.SIGTERM, signal.SIGKILL):
        remaining: List[int] = []
        for pid in victims:
            try:
                os.kill(pid, sig)
            except ProcessLookupError:
                continue
            except PermissionError:
                remaining.append(pid)
                continue
            else:
                remaining.append(pid)
        time.sleep(0.5)
        victims = [pid for pid in remaining if _pid_alive(pid)]
        if not victims:
            break


def _clear_profile_locks(profile_dir: Optional[str]) -> None:
    if not profile_dir:
        return
    for lock_name in ("SingletonLock", "SingletonCookie", "SingletonSocket"):
        lock_path = os.path.join(profile_dir, lock_name)
        if os.path.exists(lock_path):
            try:
                os.remove(lock_path)
            except Exception:
                pass


def _is_runtime_profile(path: Optional[str]) -> bool:
    if not path:
        return False
    parent = os.path.dirname(path.rstrip(os.sep))
    return os.path.basename(parent) == "runtime"


def _lock_scope_for(profile_dir: str) -> str:
    if _is_runtime_profile(profile_dir):
        return os.path.dirname(os.path.dirname(profile_dir.rstrip(os.sep)))
    return profile_dir


def _cleanup_runtime_dir(profile_dir: Optional[str]) -> None:
    if not _is_runtime_profile(profile_dir):
        return
    try:
        shutil.rmtree(profile_dir, ignore_errors=True)
    except Exception:
        pass


def _acquire_profile_lock(lock_scope: str):
    lock_path = os.path.join(lock_scope, ".chrome-profile.lock")
    os.makedirs(lock_scope, exist_ok=True)
    lock_file = open(lock_path, "a+")
    try:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
    except Exception:
        lock_file.close()
        raise
    return lock_file


def _release_lock_handle(lock_file) -> None:
    if not lock_file:
        return
    try:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
    except Exception:
        pass
    try:
        lock_file.close()
    except Exception:
        pass


def _release_profile_lock(driver) -> None:
    if driver is None:
        return
    lock_file = getattr(driver, "_profile_lock", None)
    if not lock_file:
        return
    _release_lock_handle(lock_file)
    try:
        delattr(driver, "_profile_lock")
    except Exception:
        pass


def release_driver_lock(driver) -> None:
    """Expose lock release for callers that manage the driver lifecycle."""
    _release_profile_lock(driver)


def _resolve_profile_dir(profile_base_dir: Optional[str], remote: bool, account_name: Optional[str] = None) -> str:
    """
    Gera caminho de profile isolado por conta (perfil persistente).

    Estrutura:
    - Local com REUSE_PROFILE=True: ./profiles/{account_name}/ (persistente, isolado por conta)
    - Local sem REUSE_PROFILE: /tmp/chrome-user-data-{uuid} (temporário)
    - Remoto: /tmp/chrome-user-data-{uuid} (temporário)

    Args:
        profile_base_dir: Diretório base (legado, não usado na nova estrutura)
        remote: Se True, usa perfil temporário remoto
        account_name: Nome da conta TikTok (usado para isolar perfis)
    """
    # Calcula diretório raiz do projeto (um nível acima de beckend/)
    _PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    if remote:
        # Remoto: sempre temporário
        suffix = uuid.uuid4().hex
        return f"/tmp/chrome-user-data-{suffix}"

    # Local: usa perfil persistente isolado por conta se REUSE_PROFILE=True
    if REUSE_PROFILE and account_name:
        # Cria ./profiles/{account_name}/ no projeto root
        profiles_dir = os.path.join(_PROJECT_ROOT, "profiles")
        os.makedirs(profiles_dir, exist_ok=True)

        account_profile_dir = os.path.join(profiles_dir, account_name)
        os.makedirs(account_profile_dir, exist_ok=True)

        runtime_root = os.path.join(account_profile_dir, "runtime")
        os.makedirs(runtime_root, exist_ok=True)

        runtime_dir = os.path.join(runtime_root, uuid.uuid4().hex)
        os.makedirs(runtime_dir, exist_ok=True)

        return runtime_dir

    # Fallback: perfil temporário (apagado ao encerrar)
    suffix = uuid.uuid4().hex
    base = profile_base_dir or tempfile.gettempdir()
    os.makedirs(base, exist_ok=True)
    return tempfile.mkdtemp(prefix=f"chrome-user-data-{suffix}-", dir=base)


def build_driver(profile_base_dir: Optional[str] = None, account_name: Optional[str] = None):
    """Constrói e retorna uma instância do WebDriver.
    Em modo remoto, conecta-se ao Selenium Grid.
    Em modo local, usa o ChromeDriver local.

    Args:
        profile_base_dir: Diretório base (legado, não usado)
        account_name: Nome da conta TikTok (usado para isolar perfis em ./profiles/{account_name}/)
    """
    remote = _is_remote()
    profile_dir = _resolve_profile_dir(profile_base_dir, remote, account_name)
    lock_scope = _lock_scope_for(profile_dir)
    lock_handle = None
    driver = None
    try:
        lock_handle = _acquire_profile_lock(lock_scope)
        _cleanup_conflicting_processes(profile_dir)
        _clear_profile_locks(profile_dir)

        if remote:
            hub = _hub_url()
            opts = _remote_options_full(profile_dir)

            max_retries = 3
            for attempt in range(1, max_retries + 1):
                try:
                    print(f"📁 (remote) user-data-dir: {profile_dir}")
                    driver = webdriver.Remote(
                        command_executor=hub,
                        options=opts,
                    )

                    # Scripts anti-detecção executados IMEDIATAMENTE após criar o driver
                    try:
                        driver.execute_script(
                            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
                        )
                        driver.execute_script("window.navigator.chrome = {runtime: {}}")
                        driver.execute_script("delete navigator.__proto__.webdriver")
                    except Exception:
                        # Mesmo que falhe, segue
                        pass

                    # Espera curta para estabilizar
                    time.sleep(2)

                    break

                except (SessionNotCreatedException, WebDriverException) as e:
                    print(f"⚠️ Tentativa {attempt} falhou: {str(e)}")
                    if attempt < max_retries:
                        time.sleep(3)
                    else:
                        raise Exception(
                            f"Falha ao criar sessão remota após {max_retries} tentativas: {str(e)}"
                        ) from e
        else:
            # Modo local: usa Chrome instalado no sistema com webdriver-manager
            print("🔧 Usando Chrome local com webdriver-manager...")
            print(f"📁 user-data-dir: {profile_dir}")

            # SEMPRE usar webdriver-manager para garantir versão compatível
            # Ignora /usr/bin/chromedriver que pode ser apenas um wrapper
            driver_path = os.getenv("CHROMEDRIVER_PATH")
            if not driver_path:
                # Força download/uso do chromedriver correto via webdriver-manager
                driver_path = ChromeDriverManager(driver_version="141.0.7390.0").install()
                print(f"📦 ChromeDriver instalado em: {driver_path}")

            log_path = os.path.join(profile_dir, "chromedriver.log")
            service = Service(driver_path, log_output=log_path)

            opts = _remote_options_full(profile_dir)

            # Deixar Selenium encontrar Chrome automaticamente via PATH
            # Apenas definir binary_location se CHROME_BINARY estiver explicitamente setado
            chrome_binary = os.getenv("CHROME_BINARY")
            if not chrome_binary:
                for candidate in (
                    "/opt/google/chrome/chrome",
                    "/usr/bin/google-chrome",
                    "/usr/bin/google-chrome-stable",
                    "/usr/bin/chromium-browser",
                    "/snap/bin/chromium",
                    "/snap/chromium/current/usr/lib/chromium-browser/chrome",
                ):
                    if os.path.isfile(candidate):
                        chrome_binary = candidate
                        break
            if chrome_binary and os.path.isfile(chrome_binary):
                opts.binary_location = chrome_binary
                print(f"📌 Chrome binary definido: {chrome_binary}")

            driver = webdriver.Chrome(service=service, options=opts)

            # Scripts anti-detecção
            try:
                driver.execute_script(
                    "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
                )
                driver.execute_script("window.navigator.chrome = {runtime: {}}")
                driver.execute_script("delete navigator.__proto__.webdriver")
            except Exception:
                pass

            time.sleep(2)

        if driver is None:
            raise RuntimeError("Falha ao criar driver do Chrome")

        setattr(driver, "_profile_lock", lock_handle)
        setattr(driver, "_profile_lock_scope", lock_scope)
        setattr(driver, "_profile_dir", profile_dir)
        try:
            driver.set_page_load_timeout(180)
        except Exception:
            pass
        try:
            driver.implicitly_wait(0)
            executor = getattr(driver, "command_executor", None)
            if executor and hasattr(executor, "_client_config"):
                executor._client_config.timeout = 300  # type: ignore[attr-defined]
        except Exception:
            pass
        return driver

    except Exception:
        if lock_handle:
            _release_lock_handle(lock_handle)
        _cleanup_runtime_dir(profile_dir)
        raise


def is_session_alive(driver: Optional[webdriver.Remote]) -> bool:
    """Valida se a sessão WebDriver ainda está viva."""
    if driver is None:
        return False
    try:
        _ = driver.session_id
        driver.execute_script("return 1")
        return True
    except (InvalidSessionIdException, WebDriverException):
        return False

def get_fresh_driver(existing: Optional[webdriver.Remote], profile_base_dir: Optional[str] = None, account_name: Optional[str] = None) -> webdriver.Remote:
    """Reaproveita o driver se a sessão estiver viva; caso contrário, recria.

    Args:
        existing: Instância existente do driver (se houver)
        profile_base_dir: Diretório base (legado, não usado)
        account_name: Nome da conta TikTok (usado para isolar perfis em ./profiles/{account_name}/)
    """
    if is_session_alive(existing):
        return existing
    old_profile = getattr(existing, "_profile_dir", None)
    if existing is not None:
        try:
            existing.quit()
        except Exception:
            pass
        _release_profile_lock(existing)
    if old_profile:
        basename = os.path.basename(old_profile.rstrip(os.sep))
        is_temp_profile = basename.startswith("chrome-user-data-")
        is_runtime_profile = _is_runtime_profile(old_profile)
        if is_runtime_profile:
            _cleanup_runtime_dir(old_profile)
        elif not REUSE_PROFILE or is_temp_profile:
            try:
                shutil.rmtree(old_profile, ignore_errors=True)
            except Exception:
                pass
        else:
            # remove possíveis locks deixados pelo Chrome
            for lock_name in ("SingletonLock", "SingletonCookie", "SingletonSocket"):
                lock_path = os.path.join(old_profile, lock_name)
                if os.path.exists(lock_path):
                    try:
                        os.remove(lock_path)
                    except Exception:
                        pass
    return build_driver(profile_base_dir=profile_base_dir, account_name=account_name)

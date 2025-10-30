# src/uploader.py - Versão FINAL e OTIMIZADA com sessão fresca + cookies locais
import os
import time
import json
from datetime import datetime


from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    StaleElementReferenceException,
    ElementClickInterceptedException,
    WebDriverException,
    InvalidSessionIdException,
)

# Helpers de driver (precisam existir no src/driver.py)
from src.driver import get_fresh_driver, is_session_alive, release_driver_lock
from typing import Dict, List, Optional, Set, Tuple


WAIT_SHORT = 8
WAIT_MED   = 25
WAIT_LONG  = 55

STUDIO_URL   = "https://www.tiktok.com/tiktokstudio/upload?from=creator_center"
CREATOR_URLS = [
    "https://www.tiktok.com/creator-center/upload",
    "https://www.tiktok.com/creator-center/content/post",
]
CLASSIC_URL  = "https://www.tiktok.com/upload"
BASE_URL     = "https://www.tiktok.com"

COOKIES_FILE = os.getenv("TIKTOK_COOKIES_FILE", "tiktok_cookies.json")  # raiz do projeto


def _now() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _wait_js_ready(driver, timeout=30):
    WebDriverWait(driver, timeout).until(
        lambda d: d.execute_script("return document.readyState") == "complete"
    )


def _visible(driver, locator, timeout=WAIT_MED):
    return WebDriverWait(driver, timeout).until(
        EC.visibility_of_element_located(locator)
    )


def _present(driver, locator, timeout=WAIT_MED):
    return WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located(locator)
    )


def _any_of(driver, conditions: List, timeout=WAIT_MED):
    return WebDriverWait(driver, timeout).until(
        EC.any_of(*conditions)
    )


def _dump(driver, out_dir, stem):
    try:
        os.makedirs(out_dir, exist_ok=True)
        html = driver.page_source
        png  = os.path.join(out_dir, f"{stem}.png")
        htm  = os.path.join(out_dir, f"{stem}.html")
        with open(htm, "w", encoding="utf-8") as f:
            f.write(html)
        driver.save_screenshot(png)
        return htm, png
    except Exception:
        return None, None


def _load_cookies_from_file(path: str) -> Optional[List[dict]]:
    """
    Suporta:
      - arquivo contendo uma lista de cookies (padrão do Chrome/DevTools)
      - arquivo contendo um dict com chave 'cookies' (formato exportado de libs)
    """
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and "cookies" in data and isinstance(data["cookies"], list):
            return data["cookies"]
        # formato desconhecido
        return None
    except Exception:
        return None


def _sanitize_cookie_dict(c: dict) -> dict:
    """
    Normaliza campos essenciais aceitos pelo Selenium.
    Ignora atributos problemáticos (sameSite/lax/priority etc.) se presentes.
    """
    d = {
        "name":  c.get("name"),
        "value": c.get("value"),
        "path":  c.get("path", "/"),
        "secure": bool(c.get("secure", True)),
        "httpOnly": bool(c.get("httpOnly", False)),
    }
    # domínio: se vier sem ponto inicial, tudo bem
    if "domain" in c and c["domain"]:
        d["domain"] = c["domain"]
    # expiry opcional (inteiro timestamp)
    if "expiry" in c and isinstance(c["expiry"], (int, float)):
        d["expiry"] = int(c["expiry"])
    return d


def _sanitize_text_for_chrome(text: str) -> str:
    """
    Remove ou substitui caracteres fora do BMP (Basic Multilingual Plane)
    que causam erro no ChromeDriver.

    ChromeDriver só suporta caracteres Unicode U+0000 a U+FFFF (BMP).
    Emojis e outros caracteres acima de U+FFFF causam erro.
    """
    if not text:
        return text

    # Filtra caracteres que estão no BMP (U+0000 a U+FFFF)
    sanitized = ''.join(char if ord(char) <= 0xFFFF else '' for char in text)
    return sanitized


class TikTokUploader:
    """
    Responsável por:
      - garantir sessão WebDriver válida (recria se necessário);
      - (re)aplicar cookies do TikTok a partir de tiktok_cookies.json (raiz do projeto);
      - abrir a página de upload (robusto, com fallbacks);
      - enviar o arquivo;
      - garantir audiência "Everyone";
      - clicar Publish / Post;
      - resolver o popup "Continue to post".
    """

    PUBLISH_BUTTON_XPATHS = [
        "//button[@data-e2e='post_video_button' and not(@disabled)]",
        "//button[@data-e2e='post_button' and not(@disabled)]",
        "//button[@type='submit' and contains(normalize-space(.), 'Post')]",
        "//button[@type='submit' and contains(normalize-space(.), 'Publicar')]",
        "//div[@role='button' and contains(normalize-space(.), 'Post') and not(@disabled)]",
        "//div[@role='button' and contains(normalize-space(.), 'Publicar') and not(@disabled)]",
        "//button[contains(@class, 'btn-post')]",
        "//button[contains(@class, 'publish')]",
        "//button[not(@disabled) and not(@data-e2e='discard_post_button') and (contains(normalize-space(.), 'Post') or contains(normalize-space(.), 'Publicar'))]",
    ]

    SUCCESS_KEYWORDS = [
        "uploaded successfully",
        "upload successful",
        "post successful",
        "postado com sucesso",
        "publicado com sucesso",
        "upload concluído",
        "upload complete",
        "has been posted",
        "foi publicado",
        "successful",
    ]

    PROCESSING_KEYWORDS = [
        "being processed",
        "is processing",
        "processing",
        "processando",
        "em processamento",
        "scheduled",
        "em breve",
    ]

    UPLOAD_SUCCESS_KEYWORDS = [
        "upload complete",
        "upload successful",
        "upload success",
        "uploaded",
        "upload concluído",
        "upload concluido",
        "upload concluido!",
        "upload finalizado",
        "processado",
        "processamento concluído",
        "ready to post",
    ]

    UPLOAD_FAILURE_KEYWORDS = [
        "upload failed",
        "falha no upload",
        "upload fail",
        "upload error",
        "erro de upload",
        "upload canceled",
        "upload cancelado",
        "upload interrompido",
    ]

    MIN_VIDEO_SIZE_BYTES = 200 * 1024  # 200 KB (configurável, evita uploads vazios)

    def __init__(
        self,
        driver,
        logger=print,
        debug_dir="/tmp",
        cookies_path: str = COOKIES_FILE,
        account_name: str = None,
        reuse_existing_session: bool = False,
    ):
        self.driver = driver
        self.log = logger
        self.debug_dir = debug_dir
        self.cookies_path = cookies_path
        self.account_name = account_name  # se fornecido, usa cookies do banco de dados
        # Quando o scheduler já autenticou a sessão momentos antes, reaproveitamos
        # os cookies sem tentar reinserir imediatamente. Isso evita múltiplas
        # chamadas consecutivas de login/cookies que estavam causando timeouts
        # recorrentes no Chrome headless.
        self.reuse_existing_session = reuse_existing_session
        self._initial_session_id = getattr(driver, "session_id", None)
        self._current_session_id = self._initial_session_id
        self._cookies_applied = reuse_existing_session

    # -----------------------------
    # 0) Cookies
    # -----------------------------
    def _apply_cookies(self) -> bool:
        """
        Abre o domínio base e injeta cookies.
        Se account_name for fornecido, usa cookies do banco de dados.
        Caso contrário, usa arquivo local.
        """
        # Prioridade 1: Cookies do banco de dados (se account_name fornecido)
        if self.account_name:
            try:
                from src.cookies import load_cookies_for_account
                success = load_cookies_for_account(self.driver, self.account_name, BASE_URL)
                if success:
                    self._cookies_applied = True
                    return True
                else:
                    self.log(f"⚠️ Falha ao carregar cookies do banco para: {self.account_name}")
            except Exception as e:
                self.log(f"⚠️ Erro ao carregar cookies do banco: {e}")

        # Prioridade 2: Cookies de arquivo (fallback)
        cookies = _load_cookies_from_file(self.cookies_path)
        if not cookies:
            self.log(f"ℹ️ Arquivo de cookies não encontrado ou inválido: {self.cookies_path} (seguindo sem cookies)")
            return False

        try:
            # Precisa estar no domínio para conseguir setar cookies
            self.driver.set_page_load_timeout(30)
            self.driver.get(BASE_URL)
            _wait_js_ready(self.driver, timeout=20)
            try:
                self.driver.delete_all_cookies()
            except Exception:
                pass
            try:
                self.driver.execute_script(
                    "window.localStorage.clear(); window.sessionStorage.clear();"
                )
            except Exception:
                pass
        except Exception as e:
            self.log(f"⚠️ Falha ao abrir domínio base para aplicar cookies: {e}")
            return False

        ok = 0
        for c in cookies:
            try:
                ck = _sanitize_cookie_dict(c)
                if not ck.get("name") or ck.get("value") is None:
                    continue
                # Se o cookie for de outro domínio, o Chrome/Selenium pode recusar;
                # nesse caso, tentamos sem especificar 'domain' (aplica no atual).
                try:
                    self.driver.add_cookie(ck)
                except Exception:
                    ck2 = ck.copy()
                    ck2.pop("domain", None)
                    self.driver.add_cookie(ck2)
                ok += 1
            except Exception:
                continue

        if ok:
            try:
                self.driver.refresh()
                _wait_js_ready(self.driver, timeout=20)
            except Exception:
                pass
            self._cookies_applied = True
            self.log(f"🍪 Cookies aplicados ({ok} itens)")
            return True

        self.log("⚠️ Nenhum cookie aplicado (provavelmente incompatíveis com o domínio atual)")
        return False

    # -----------------------------
    # 1) Navegação robusta ao upload
    # -----------------------------
    def _go_to_upload(self) -> bool:
        # 🔒 Garante que a sessão está viva antes de navegar
        self.driver = get_fresh_driver(getattr(self, "driver", None), profile_base_dir=self.debug_dir)

        # Se a sessão mudou (driver foi recriado), precisamos reaplicar cookies
        session_id = getattr(self.driver, "session_id", None)
        if session_id != self._current_session_id:
            self._current_session_id = session_id
            if session_id != self._initial_session_id:
                self._cookies_applied = False
                self._initial_session_id = session_id
        elif self.reuse_existing_session:
            # Sessão é a mesma autenticada pelo scheduler (_ensure_logged)
            self._cookies_applied = True

        # Aplica cookies (se ainda não aplicado nesta instância)
        if not self._cookies_applied:
            self._apply_cookies()

        urls = [STUDIO_URL, *CREATOR_URLS, CLASSIC_URL]
        for attempt in range(1, 4):
            login_redirected = False

            for url in urls:
                try:
                    self.log(f"🌐 Acessando: {url} (tentativa {attempt}/3)")
                    self.driver.set_page_load_timeout(60)
                    self.driver.get(url)
                    _wait_js_ready(self.driver, timeout=30)

                    # Se cair em login, aborta (cookies quebrados/expirados)
                    if "login" in self.driver.current_url or "signin" in self.driver.current_url:
                        self.log("🔒 Redirecionado para login; tentando reforçar sessão…")
                        login_redirected = True
                        continue

                    # Espera input de arquivo ou área de upload/preview
                    cand = _any_of(
                        self.driver,
                        [
                            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='file']")),
                            EC.presence_of_element_located((By.CSS_SELECTOR, "[class*='upload'], [data-e2e*='upload']")),
                            EC.presence_of_element_located((By.CSS_SELECTOR, "[class*='preview'], [data-e2e*='preview']")),
                        ],
                        timeout=WAIT_MED
                    )
                    if cand:
                        # Rola topo para minimizar overlays
                        try:
                            self.driver.execute_script("window.scrollTo(0,0);")
                        except Exception:
                            pass
                        return True

                except TimeoutException:
                    self.log("⏳ Timeout de carregamento; tentando URL alternativa…")

                except (InvalidSessionIdException, WebDriverException) as e:
                    # Sessão pode ter morrido entre execuções; recria e tenta de novo
                    msg = str(e)
                    if isinstance(e, InvalidSessionIdException) or "invalid session id" in msg.lower():
                        self.log("♻️ Sessão Selenium inválida. Recriando driver e tentando novamente…")
                        current_driver = getattr(self, "driver", None)
                        try:
                            if is_session_alive(current_driver):
                                current_driver.quit()
                        except Exception:
                            pass
                        finally:
                            try:
                                release_driver_lock(current_driver)
                            except Exception:
                                pass
                        self.driver = get_fresh_driver(None, profile_base_dir=self.debug_dir)
                        # Reaplica cookies ao recriar
                        self._cookies_applied = False
                        self._apply_cookies()
                        time.sleep(1)
                        continue
                    else:
                        self.log(f"⚠️ Erro de navegação: {e}; reintentando…")

            if login_redirected:
                self._cookies_applied = False
                if not self._apply_cookies():
                    return False
                # pequena pausa para garantir persistência dos cookies aplicados
                time.sleep(2)
                continue

            time.sleep(2)

        self.log("❌ Não consegui abrir a tela de upload.")
        _dump(self.driver, self.debug_dir, f"upload_open_fail_{_now()}")
        return False

    # -----------------------------
    # 2) Upload do arquivo
    # -----------------------------
    def _send_file(self, video_path: str) -> bool:
        # o input pode estar em shadow/oculto; normalmente existe no DOM
        try:
            inp = _present(self.driver, (By.CSS_SELECTOR, "input[type='file']"), timeout=WAIT_MED)
        except TimeoutException:
            # tenta achar por XPath alternativa
            try:
                inp = _present(self.driver, (By.XPATH, "//input[@type='file']"), timeout=WAIT_SHORT)
            except TimeoutException:
                self.log("❌ Não encontrei input[type=file].")
                _dump(self.driver, self.debug_dir, f"nofileinput_{_now()}")
                return False

        abs_path = os.path.abspath(video_path)
        inp.send_keys(abs_path)
        self.log(f"⬆️ Vídeo enviado: {abs_path}")

        # Sinais de processamento/preview
        try:
            _any_of(
                self.driver,
                [
                    EC.visibility_of_element_located((By.CSS_SELECTOR, "[class*='preview']")),
                    EC.visibility_of_element_located((By.XPATH, "//*[contains(text(),'Processing') or contains(text(),'processando') or contains(text(),'Preview')]")),
                    EC.presence_of_element_located((By.CSS_SELECTOR, "video, canvas")),
                ],
                timeout=WAIT_MED
            )
            self.log("🎬 Preview/processamento detectado")
        except TimeoutException:
            self.log("⚠️ Sem preview evidente; seguindo mesmo assim.")
        if not self._wait_upload_ready():
            stem = f"upload_failed_{_now()}"
            h, p = _dump(self.driver, self.debug_dir, stem)
            self.log(f"❌ Upload não ficou pronto: dump em {h} / {p}")
            return False
        return True

    def _wait_upload_ready(self, timeout: int = 180, max_timeout: int = 900) -> bool:
        """
        Observa o status do cartão principal no Studio para confirmar
        se o upload foi concluído ou falhou.
        """
        start_ts = time.time()
        deadline = start_ts + timeout
        hard_deadline = start_ts + max_timeout
        last_status: Optional[str] = None
        last_status_ts = start_ts

        while time.time() < deadline:
            try:
                status_nodes = self.driver.find_elements(
                    By.XPATH,
                    "//div[@data-e2e='upload_status_container']//div[contains(@class,'info-status')]"
                )
            except Exception:
                status_nodes = []

            texts = []
            for node in status_nodes:
                try:
                    txt = node.text.strip()
                    if txt:
                        texts.append(txt)
                except StaleElementReferenceException:
                    continue

            joined = " | ".join(texts) if texts else ""
            if joined and joined != last_status:
                self.log(f"ℹ️ Status de upload: {joined}")
                last_status = joined
                last_status_ts = time.time()
                # Enquanto houver progresso recente, estende o deadline (até o limite hard)
                deadline = min(hard_deadline, last_status_ts + timeout)

            if texts:
                joined_lower = joined.lower()
                if any(keyword.lower() in joined_lower for keyword in self.UPLOAD_FAILURE_KEYWORDS):
                    return False
                if any(keyword.lower() in joined_lower for keyword in self.UPLOAD_SUCCESS_KEYWORDS):
                    return True

            # Também verificamos toasts
            toasts = self._collect_toast_texts()
            if toasts:
                toast_lower = " | ".join(toasts).lower()
                if any(k.lower() in toast_lower for k in self.UPLOAD_FAILURE_KEYWORDS):
                    self.log(f"⚠️ Toast reportou falha de upload: {' | '.join(toasts)}")
                    return False
                if any(k.lower() in toast_lower for k in self.UPLOAD_SUCCESS_KEYWORDS):
                    self.log("✅ Upload confirmado via toast")
                    return True

            time.sleep(2)

        self.log("⚠️ Timeout aguardando status do upload")
        return False

    def _reset_failed_upload(self) -> bool:
        """Tenta recuperar a tela de upload após uma falha."""
        selectors = [
            "//button[contains(., 'Replace')]",
            "//button[contains(., 'Retry')]",
            "//button[contains(., 'Tentar novamente')]",
        ]

        for selector in selectors:
            try:
                buttons = self.driver.find_elements(By.XPATH, selector)
            except Exception:
                buttons = []

            for btn in buttons:
                try:
                    if btn.is_displayed() and btn.is_enabled():
                        self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
                        time.sleep(0.2)
                        try:
                            btn.click()
                        except Exception:
                            self.driver.execute_script("arguments[0].click();", btn)
                        self.log("🔁 Cliquei em botão de reenvio (Replace/Retry)")
                        time.sleep(1)
                        return True
                except StaleElementReferenceException:
                    continue

        # Se não houver botão específico, recarrega a página
        try:
            self.driver.refresh()
            _wait_js_ready(self.driver, timeout=30)
            self.log("🔁 Tela de upload recarregada para nova tentativa")
            return True
        except Exception as exc:
            self.log(f"⚠️ Falha ao recarregar tela de upload: {exc}")
            return False

    # -----------------------------
    # 3) Preencher descrição
    # -----------------------------
    def _fill_description(self, text: str):
        # Sanitiza texto para remover caracteres fora do BMP
        text = _sanitize_text_for_chrome(text)

        # campo contenteditable no Studio
        candidates = [
            (By.CSS_SELECTOR, "div[contenteditable='true']"),
            (By.XPATH, "//div[@contenteditable='true']"),
            (By.CSS_SELECTOR, "textarea"),
        ]
        box = None
        for loc in candidates:
            try:
                box = _visible(self.driver, loc, timeout=WAIT_SHORT)
                if box: break
            except TimeoutException:
                continue
        if box:
            try:
                self.driver.execute_script("arguments[0].innerHTML = '';", box)
            except Exception:
                try:
                    box.clear()
                except Exception:
                    pass
            for ch in text:
                box.send_keys(ch)
                time.sleep(0.01)
            self.log("📝 Descrição preenchida")
        else:
            self.log("⚠️ Não achei campo de descrição; prosseguindo")

    # -----------------------------
    # 4) Garantir audiência pública (sem abrir dropdown à toa)
    # -----------------------------
    def _ensure_public_audience(self):
        # Detecta se já está em "Everyone/Para todos" usando data-e2e e texto
        public_indicators = [
            (By.XPATH, "//*[(@data-e2e='audience-selector' or contains(@class,'select') or contains(@class,'selector')) and (.//text()[contains(.,'Everyone') or contains(.,'Para todos')])]"),
            (By.XPATH, "//div[@data-e2e='view-permission' and contains(.,'Everyone')]"),
        ]
        for loc in public_indicators:
            try:
                summary = _visible(self.driver, loc, timeout=10)
                if summary:
                    self.log("🔧 Audiência já está em 'Everyone'")
                    return
            except TimeoutException:
                pass

        # Abre o seletor apenas se necessário
        openers = [
            (By.XPATH, "//div[@data-e2e='audience-selector']"),
            (By.XPATH, "//*[contains(text(),'Who can watch this video') or contains(text(),'Quem pode assistir')]/following::div[@role='combobox' or contains(@class,'select')][1]"),
            (By.XPATH, "//div[contains(@class,'select')]//div[contains(@class,'value') or contains(@class,'selected')]"),
        ]
        opener = None
        for loc in openers:
            try:
                opener = _visible(self.driver, loc, timeout=10)
                if opener:
                    try:
                        opener.click()
                    except Exception:
                        self.driver.execute_script("arguments[0].click();", opener)
                    time.sleep(1)
                    self.log("🔍 Dropdown de audiência aberto")
                    break
            except TimeoutException:
                continue

        if not opener:
            self.log("⚠️ Não encontrei o seletor de audiência; prosseguindo sem alteração.")
            return

        # Seleciona "Everyone / Para todos"
        opts = [
            (By.XPATH, "//div[@data-e2e='everyone-option' or @role='option' or @role='menuitem' or @role='listitem'][.//text()[contains(.,'Everyone') or contains(.,'Para todos')]]"),
            (By.XPATH, "//*[contains(@data-e2e,'option') and (contains(.,'Everyone') or contains(.,'Para todos'))]"),
        ]
        for loc in opts:
            try:
                opt = _visible(self.driver, loc, timeout=10)
                if opt:
                    try:
                        opt.click()
                    except Exception:
                        self.driver.execute_script("arguments[0].click();", opt)
                    self.log("🔧 Audiência definida para Público")
                    return
            except TimeoutException:
                continue

        self.log("ℹ️ Não consegui alterar audiência (seguindo assim).")

    # -----------------------------
    # 5) Botão de “Post/Publish”
    # -----------------------------
    def _find_publish_button(self):
        """Encontra o botão de publicação com múltiplos seletores atualizados."""
        for selector in self.PUBLISH_BUTTON_XPATHS:
            try:
                btn = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, selector))
                )
                if btn and btn.is_enabled():
                    return btn
            except TimeoutException:
                continue
        
        return None

    def _dismiss_exit_modal_if_present(self) -> bool:
        """Detecta o modal 'Are you sure you want to exit?' e clica em Cancel."""
        try:
            WebDriverWait(self.driver, 2).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//div[contains(@class,'modal') and contains(., 'Are you sure you want to exit')]")
                )
            )
        except TimeoutException:
            return False

        try:
            cancel = WebDriverWait(self.driver, 2).until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[contains(normalize-space(.), 'Cancel') or contains(normalize-space(.), 'Cancelar')]")
                )
            )
            cancel.click()
            self.log("ℹ️ Modal de saída detectado e cancelado")
            return True
        except TimeoutException:
            # Se não achou botão, tenta apertar ESC
            try:
                self.driver.switch_to.active_element.send_keys(Keys.ESCAPE)
            except Exception:
                pass
            return True

    def _click_publish(self) -> bool:
        """Tenta clicar no botão de publicação."""
        try:
            btn = self._find_publish_button()
            if not btn:
                self.log("❌ Não encontrei o botão de publicação")
                return False

            # Rola até o botão
            self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
            time.sleep(0.5)
            
            # Tenta clicar de várias formas
            for _ in range(3):
                try:
                    btn.click()
                    time.sleep(0.5)
                    if self._dismiss_exit_modal_if_present():
                        self.log("ℹ️ Modal de saída interceptou clique; tentando novamente…")
                        btn = self._find_publish_button()
                        if not btn:
                            self.log("❌ Botão de publicação sumiu após fechar modal")
                            return False
                        continue
                    self.log("🖱️ Clique de publicação enviado")
                    return True
                except (ElementClickInterceptedException, StaleElementReferenceException):
                    try:
                        self.driver.execute_script("arguments[0].click();", btn)
                        time.sleep(0.5)
                        if self._dismiss_exit_modal_if_present():
                            self.log("ℹ️ Modal de saída interceptou clique (JS); tentando novamente…")
                            btn = self._find_publish_button()
                            if not btn:
                                self.log("❌ Botão de publicação sumiu após fechar modal (JS)")
                                return False
                            continue
                        self.log("🖱️ Clique JS de publicação enviado")
                        return True
                    except Exception:
                        time.sleep(1)

            self.log("❌ Falha ao clicar no botão de publicação")
            return False
            
        except Exception as e:
            self.log(f"⚠️ Erro ao clicar no botão de publicação: {e}")
            return False

    # -----------------------------
    # 6) Pop-up “Continue to post?”
    # -----------------------------
    def _handle_continue_dialog(self) -> bool:
        """Lida com o modal de confirmação de publicação."""
        try:
            # Espera o modal aparecer (ou não)
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located(
                    (By.XPATH,
                     "//div[contains(@class, 'modal') or contains(@class, 'dialog')]//button[contains(., 'Post') or contains(., 'Publicar') or contains(., 'Continue') or contains(., 'Continuar')]"
                    )
                )
            )
        except TimeoutException:
            return True  # não apareceu

        selectors = [
            "//button[contains(., 'Post') and not(@disabled)]",
            "//button[contains(., 'Publicar') and not(@disabled)]",
            "//button[contains(., 'Continue') and not(@disabled)]",
            "//button[contains(., 'Continuar') and not(@disabled)]",
            "//div[@role='button' and contains(., 'Post')]",
            "//div[@role='button' and contains(., 'Publicar')]",
        ]
        
        for selector in selectors:
            try:
                btn = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, selector))
                )
                btn.click()
                self.log("✅ Modal de confirmação resolvido")
                return True
            except TimeoutException:
                continue
        
        self.log("⚠️ Modal presente mas sem botão clicável.")
        return False

    # -----------------------------
    # 7) Confirmação de publicação
    # -----------------------------
    def _collect_toast_texts(self) -> List[str]:
        """Retorna texto dos toasts do novo sistema (Sonner)."""
        texts: List[str] = []
        try:
            for toast in self.driver.find_elements(By.CSS_SELECTOR, "[data-sonner-toast]"):
                content = toast.text.strip()
                if content:
                    texts.append(content)
        except Exception:
            pass
        return texts

    def _publish_button_still_visible(self) -> bool:
        """Verifica se o botão de publicar ainda está acessível/visível."""
        try:
            for selector in self.PUBLISH_BUTTON_XPATHS:
                elements = self.driver.find_elements(By.XPATH, selector)
                for element in elements:
                    try:
                        if element.is_displayed():
                            return True
                    except StaleElementReferenceException:
                        continue
            return False
        except Exception:
            return False

    def _has_keyword(self, source: List[str], keywords: List[str]) -> bool:
        lowered = [text.lower() for text in source]
        for keyword in keywords:
            if keyword.lower() in "".join(lowered):
                return True
        return False

    def _confirm_posted(self) -> bool:
        """Confirma se o vídeo foi publicado com base em múltiplos sinais."""
        deadline = time.time() + 120  # dá tempo para processamento/renderizações novas
        last_log: Optional[str] = None

        while time.time() < deadline:
            try:
                current_url = self.driver.current_url
            except Exception:
                current_url = ""

            if "/post" in current_url or "/content" in current_url:
                return True

            toasts = self._collect_toast_texts()
            if toasts:
                if self._has_keyword(toasts, self.SUCCESS_KEYWORDS):
                    self.log("✅ Toast de sucesso detectado")
                    return True
                if self._has_keyword(toasts, self.PROCESSING_KEYWORDS):
                    msg = "ℹ️ TikTok sinalizou processamento; aguardando confirmação final..."
                    if last_log != msg:
                        self.log(msg)
                        last_log = msg

            if not self._publish_button_still_visible():
                # Botão sumiu; considerado sucesso
                self.log("✅ Botão de publicação não está mais visível")
                return True

            time.sleep(2)

        self.log("⚠️ Tempo excedido aguardando confirmação de publicação")
        return False

    # -----------------------------
    # API pública
    # -----------------------------
    def post_video(self, video_path: str, description: str) -> bool:
        # 🔒 Antes de tudo, garanta uma sessão viva (protege contra sessão zumbi)
        self.driver = get_fresh_driver(getattr(self, "driver", None), profile_base_dir=self.debug_dir)
        # (Re)aplica cookies se for um driver recém-criado
        if not self._cookies_applied:
            self._apply_cookies()

        if not os.path.isfile(video_path):
            self.log(f"❌ Arquivo de vídeo não encontrado: {video_path}")
            return False

        size_bytes = os.path.getsize(video_path)
        if size_bytes < self.MIN_VIDEO_SIZE_BYTES:
            self.log(f"❌ Vídeo muito pequeno ({size_bytes} bytes). Abortando upload e mantendo arquivo na fila.")
            return False

        # 1) ir para upload
        if not self._go_to_upload():
            self.log("❌ Falha ao abrir tela de upload.")
            return False

        # 2) enviar arquivo (com tentativas extras se necessário)
        upload_ok = False
        for attempt in range(1, 4):
            if self._send_file(video_path):
                upload_ok = True
                break

            if attempt >= 3:
                break

            self.log(f"🔁 Upload falhou (tentativa {attempt}/3). Preparando nova tentativa…")
            if not self._reset_failed_upload():
                break

        if not upload_ok:
            self.log("❌ Upload não pôde ser concluído após múltiplas tentativas.")
            return False

        # 3) descrição
        self._fill_description(description)

        # 4) audiência = Everyone (sem travar no select)
        self._ensure_public_audience()

        # 5) publicar
        if not self._click_publish():
            stem = f"publish_not_found_{_now()}"
            h, p = _dump(self.driver, self.debug_dir, stem)
            self.log(f"🧪 Dump salvo: {h} / {p}")
            return False

        # 6) lidar com popup “Continue to post?”
        if not self._handle_continue_dialog():
            stem = f"cm_unhandled_{_now()}"
            h, p = _dump(self.driver, self.debug_dir, stem)
            self.log(f"🧪 Dump salvo: {h} / {p}")
            return False

        # 7) confirmar
        if self._confirm_posted():
            return True

        # 8) *retry leve*: clica de novo e espera curto + dump
        self.log("⚠️ Sem confirmação; reenviando clique de Post e aguardando curto…")
        self._click_publish()
        if self._confirm_posted():
            return True

        stem = f"publish_unconfirmed_{_now()}"
        h, p = _dump(self.driver, self.debug_dir, stem)
        self.log(f"🧪 Dump salvo: {h} / {p}")
        return False

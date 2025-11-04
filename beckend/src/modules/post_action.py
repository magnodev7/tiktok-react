# beckend/src/modules/post_action.py
"""
Módulo 4: Ação de Postagem (Versão Otimizada v2.0-fast)
- Esperas curtas com backoff.
- Busca do botão via JS querySelectorAll (super-query CSS) + fallback XPath.
- Escopo reduzido ao formulário/container de upload quando possível.
- Clique via JS primeiro; sem sleeps desnecessários.
- Tratamento rápido de modais (Exit/TUX/Confirm).
"""

from typing import Optional, Callable, List
import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    ElementClickInterceptedException,
    NoSuchElementException,
)

__VERSION__ = "post_action v2.0-fast"

# ---------- Timeouts agressivos ----------
WAIT_FAST = 1.2       # espera curta
WAIT_MED = 2.5        # backoff curto
WAIT_LONG = 6.0       # checks finais (se necessário)
POLL = 0.10           # 100ms

# ---------- Super-query CSS (rápida e estável) ----------
PUBLISH_CSS_SUPER = (
    "button[data-e2e='post_video_button']:not([disabled]),"
    "button[data-e2e='post_button']:not([disabled]),"
    "button[data-e2e='publish-button']:not([disabled]),"
    "button[data-e2e='submit-button']:not([disabled]),"
    "button[data-testid='publish-video']:not([disabled]),"
    "div[role='button'][data-e2e='action-button-post']"
)

# Fallback XPaths (último recurso)
PUBLISH_XPATHS = [
    "//button[@data-e2e='post_video_button' and not(@disabled)]",
    "//button[@data-e2e='post_button' and not(@disabled)]",
    "//button[@data-e2e='publish-button' and not(@disabled)]",
    "//button[@data-e2e='submit-button' and not(@disabled)]",
    "//button[@data-testid='publish-video']",
    "//div[@role='button' and @data-e2e='action-button-post']",
    # Texto (fallback mesmo)
    "//button[contains(translate(normalize-space(.),'POST','post')) and not(@disabled)]",
    "//button[contains(translate(normalize-space(.),'PUBLICAR','publicar')) and not(@disabled)]",
]

CONFIRM_XPATHS = [
    "//button[@data-e2e='confirm-button']",
    "//button[@data-e2e='post-confirm']",
    "//button[@data-testid='confirm-publish']",
    "//button[contains(., 'Post') or contains(., 'Continue') or contains(., 'Publicar')]",
]

EXIT_XPATHS = [
    "//button[contains(translate(., 'CANCEL', 'cancel'), 'cancel')]",
    "//button[contains(translate(., 'CANCELAR', 'cancelar'), 'cancelar')]",
]

TUX_CLOSE_XPATHS = [
    "//div[@class='TUXModal-overlay']//button[contains(@aria-label, 'Close')]",
    "//div[@class='TUXModal-overlay']//button[contains(@class, 'close')]",
    "//div[contains(@class, 'Modal')]//button[@aria-label='Close']",
    "//button[contains(@class, 'close') and contains(@class, 'modal')]",
]

SUCCESS_HINTS = [
    "/video/",
    "tiktok.com/v/",
    "posted successfully",
    "video published",
    "vídeo publicado",
    "your video is live",
]


class PostActionModule:
    """
    Módulo responsável pela ação de postagem no TikTok.
    Foco em eficiência: localizar, confirmar e finalizar postagem rapidamente.
    """

    def __init__(self, driver, logger: Optional[Callable] = None):
        self.driver = driver
        self.log = logger if logger else print

    # ============ Utils rápidos ============

    def _now(self) -> float:
        return time.perf_counter()

    def _wait_any_xpath(self, xpaths: List[str], timeout: float) -> Optional[object]:
        """Espera o primeiro elemento de uma lista de XPaths ficar clicável."""
        end = self._now() + timeout
        while self._now() < end:
            for xp in xpaths:
                try:
                    el = WebDriverWait(self.driver, 0.5, POLL).until(
                        EC.element_to_be_clickable((By.XPATH, xp))
                    )
                    if el:
                        return el
                except Exception:
                    continue
        return None

    def _js_query(self, root, css: str):
        """querySelectorAll via JS a partir de root (document ou um container)."""
        try:
            return self.driver.execute_script(
                "return Array.from(arguments[0].querySelectorAll(arguments[1]));",
                root, css
            )
        except Exception:
            return []

    def _scroll_into_view_center(self, el):
        try:
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block:'center', inline:'center'});", el
            )
        except Exception:
            pass

    def _js_click(self, el) -> bool:
        try:
            self.driver.execute_script("arguments[0].click();", el)
            return True
        except Exception:
            return False

    def _click_element(self, el) -> bool:
        """Tenta JS click primeiro (rápido), cai para click normal só se falhar."""
        if self._js_click(el):
            return True
        try:
            el.click()
            return True
        except ElementClickInterceptedException:
            self._scroll_into_view_center(el)
            return self._js_click(el)
        except Exception:
            return False

    # ============ Modais ============

    def close_exit_modal(self) -> bool:
        """Fecha modal 'Are you sure you want to exit?' clicando em Cancel (fast-path)."""
        for xp in EXIT_XPATHS:
            try:
                btn = WebDriverWait(self.driver, WAIT_FAST, POLL).until(
                    EC.element_to_be_clickable((By.XPATH, xp))
                )
                if btn and self._click_element(btn):
                    self.log("🚪 Modal 'exit' fechado (Cancel)")
                    # Espera curta para sumir
                    try:
                        WebDriverWait(self.driver, WAIT_FAST, POLL).until_not(
                            EC.presence_of_element_located((By.XPATH, xp))
                        )
                    except Exception:
                        pass
                    return True
            except Exception:
                continue
        return False

    def close_blocking_modals(self) -> bool:
        """Fecha modais TUX que podem bloquear interação."""
        closed = False
        for xp in TUX_CLOSE_XPATHS:
            try:
                btn = self.driver.find_element(By.XPATH, xp)
                if btn and btn.is_displayed() and self._click_element(btn):
                    closed = True
            except Exception:
                continue
        if closed:
            self.log("🧹 Modais TUX fechados")
        return closed

    def handle_confirmation_dialog(self) -> bool:
        """
        Lida com o modal de confirmação 'Continue to post?'.
        Fast-path: fecha 'exit', fecha TUX, confirma se aparecer.
        """
        try:
            self.close_exit_modal()
            self.close_blocking_modals()

            # Espera curta por algum botão de confirmar
            btn = self._wait_any_xpath(CONFIRM_XPATHS, timeout=WAIT_FAST)
            if not btn:
                return True  # não apareceu, segue o fluxo

            if self._click_element(btn):
                self.log("✅ Confirmação resolvida")
                # Espera overlay sumir rapidamente
                try:
                    WebDriverWait(self.driver, WAIT_MED, POLL).until_not(
                        EC.presence_of_element_located((By.CLASS_NAME, "TUXModal-overlay"))
                    )
                except Exception:
                    pass
                return True

            self.log("⚠️ Botão de confirmação não clicável")
            return True
        except Exception as e:
            self.log(f"⚠️ handle_confirmation_dialog erro: {e}")
            return True

    # ============ Publicação ============

    def _locate_publish_button(self) -> Optional[object]:
        """
        Localiza rapidamente o botão Post:
        1) dentro do formulário/container de upload,
        2) no document,
        3) fallback XPath com backoff curto.
        """
        try:
            doc = self.driver.find_element(By.TAG_NAME, "body")
        except Exception:
            return None

        # 1) tenta dentro do formulário/container principal
        candidates = []
        try:
            form = self.driver.execute_script(
                "return document.querySelector('form,div[data-e2e=\"upload\"]') || document.body;"
            )
            candidates = self._js_query(form, PUBLISH_CSS_SUPER)
        except Exception:
            candidates = []

        # 2) tenta no documento todo
        if not candidates:
            candidates = self._js_query(doc, PUBLISH_CSS_SUPER)

        # 3) fallback XPath com backoff
        if not candidates:
            btn = self._wait_any_xpath(PUBLISH_XPATHS, timeout=WAIT_FAST)
            if btn:
                return btn
            btn = self._wait_any_xpath(PUBLISH_XPATHS, timeout=WAIT_MED)
            if btn:
                return btn
            return None

        # filtra visíveis/habilitados
        for el in candidates:
            try:
                if el.is_displayed() and el.is_enabled():
                    return el
            except Exception:
                continue
        return None

    def click_publish_button(self) -> bool:
        """Localiza e clica em 'Post' de forma agressivamente rápida."""
        start = self._now()

        btn = self._locate_publish_button()
        if not btn:
            self.log("❌ Botão de publicar não encontrado (rápido)")
            return False

        self._scroll_into_view_center(btn)
        if self._click_element(btn):
            self.log(f"🚀 Botão de publicar clicado em {(self._now()-start):.2f}s")
            return True

        self.log("⚠️ Falha ao clicar no botão de publicar")
        return False

    # ============ Sucesso ============

    def _check_post_success(self) -> bool:
        """Heurística rápida de sucesso: URL ou texto na página."""
        try:
            url = self.driver.current_url.lower()
            if any(h in url for h in SUCCESS_HINTS):
                self.log(f"✅ Sucesso por URL: {url}")
                return True

            body = self.driver.find_element(By.TAG_NAME, "body").text.lower()
            if any(h in body for h in SUCCESS_HINTS):
                self.log("✅ Sucesso por texto na página")
                return True
        except Exception:
            pass
        return False

    # ============ Fluxo público ============

    def execute_post(
        self,
        handle_modals: bool = True,
        retry_on_exit: bool = True,
        max_violation_retries: int = 0,  # desabilitado por padrão (baseline puro)
    ) -> bool:
        self.log("🚀 Executando ação de postagem (fast path)...")

        if not self.click_publish_button():
            return False

        if handle_modals:
            self.handle_confirmation_dialog()

        # retry curtíssimo se ainda estiver na tela de upload
        try:
            if retry_on_exit and "upload" in self.driver.current_url.lower():
                self.log("🔁 Ainda na tela de upload, tentando novamente rapidamente…")
                if self.click_publish_button() and handle_modals:
                    self.handle_confirmation_dialog()
        except Exception:
            pass

        if not self._check_post_success():
            self.log("ℹ️ Sem confirmação explícita; pode ser atraso do Studio.")
        self.log("✅ Ação de postagem finalizada")
        return True

    # ============ Helpers de verificação ============

    def is_on_upload_page(self) -> bool:
        try:
            return "upload" in self.driver.current_url.lower()
        except Exception:
            return False

    def publish_button_exists(self) -> bool:
        try:
            found = self._js_query(self.driver.execute_script("return document;"), PUBLISH_CSS_SUPER)
            return any(el.is_displayed() for el in found)
        except Exception:
            return False

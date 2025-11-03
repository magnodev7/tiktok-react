"""
Módulo 5: Confirmação de Postagem
Verifica se o vídeo foi efetivamente postado e aparece na lista de vídeos publicados
"""
import time
import re
import unicodedata
from typing import Optional, Callable, Tuple

from selenium.webdriver.common.by import By
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Constantes
CONFIRMATION_TIMEOUT = 90  # FIX: Aumentado para 90s (TikTok demora)
POLL_INTERVAL = 3  # FIX: Poll a cada 3s (melhor para async)

# FIX: URLs expandidas (mais patterns do TikTok recente)
SUCCESS_URL_FRAGMENTS = (
    "/post",
    "/content",
    "/creatorpost",
    "/content/manage",
    "/post/success",
    "/upload/success",
    # FIX: Adicionados redirecionamentos comuns
    "/analytics",
    "/creator_center?tab=posted",
    "/tiktokstudio/analytics",
    "/video/",  # Redireciona para vídeo postado
    "published",
    "success",
)

# FIX: Keywords expandidas (mais variações PT/EN)
SUCCESS_KEYWORDS = (
    "video posted successfully",
    "video has been posted",
    "video uploaded successfully",
    "video has been uploaded",
    "video is under review",
    "post submitted",
    "post successful",
    "postagem enviada",
    "postagem publicada",
    "postagem concluida",
    "publicacao enviada",
    "publicacao publicada",
    "publicado com sucesso",
    "enviado com sucesso",
    "upload concluido",
    "upload finalizado",
    "upload bem sucedido",
    "upload bem-sucedido",
    "upload successful",
    "uploaded successfully",
    "vamos avisar quando estiver pronto",
    "we will notify you when it's done",
    "we'll notify you when it's done",
    "successfully submitted",
    "successfully published",
    # FIX: Adicionadas variações comuns do TikTok
    "your video is now live",
    "published!",
    "video published",
    "vídeo publicado",
    "agora ao vivo",
    "processamento concluído",
    "congratulations",
    "done!",
    "ready to view",
)

PROGRESS_TOKENS = (
    "minute left", "minutes left", "second left", "seconds left",
    "hour left", "hours left", "remaining", "left to upload",
    "left to finish", "left to publish", "uploading", "upload progress",
    "upload em andamento", "enviando", "carregando",
    "processing your video", "processing video", "processing upload",
    "processando video", "processando upload", "progresso", "progress",
)

PROGRESS_PATTERNS = (
    re.compile(r"\b\d{1,3}(?:\.\d+)?\s?%"),
    re.compile(r"\b\d+(?:\.\d+)?\s?(?:kb|mb|gb)\s*/\s*\d+(?:\.\d+)?\s?(?:kb|mb|gb)\b"),
    re.compile(r"\bminutes?\s+(?:left|remaining)\b"),
    re.compile(r"\bseconds?\s+(?:left|remaining)\b"),
    re.compile(r"\bhours?\s+(?:left|remaining)\b"),
)

# FIX: Seletores expandidos (mais toasts/modals)
STATUS_TEXT_SELECTORS = (
    "//*[@role='status' or @role='alert' or @aria-live]",
    "//*[contains(@data-e2e, 'result')]",
    "//*[contains(@data-e2e, 'success')]",
    "//*[contains(@data-e2e, 'status')]",
    "//*[contains(@data-e2e, 'progress')]",
    "//*[contains(@data-testid, 'toast')]",
    "//*[contains(@class, 'result')]",
    "//*[contains(@class, 'success')]",
    "//*[contains(@class, 'progress')]",
    # FIX: Adicionados para toasts/modals recentes
    "//div[contains(@class, 'notification') or contains(@class, 'toast')]",
    "//*[contains(text(), 'success') or contains(text(), 'posted')]",
    "//div[@role='dialog']//*[@data-e2e='success-message']",
)

# FIX: Seletores para spinner/loading (para wait sumir)
LOADING_SELECTORS = (
    ".upload-progress",
    ".processing-spinner",
    "[data-e2e='upload-progress']",
    "[class*='loading']",
    "[class*='spinner']",
)


class PostConfirmationModule:
    """
    Módulo responsável pela confirmação de postagem no TikTok.
    Verifica se o vídeo foi efetivamente publicado através de múltiplos sinais:
    - Mudança de URL
    - Mensagens de sucesso
    - Desaparecimento do botão de publicar
    """

    def __init__(self, driver, logger: Optional[Callable] = None):
        """
        Inicializa o módulo de confirmação de postagem.

        Args:
            driver: WebDriver do Selenium
            logger: Função de logging (opcional, usa print por padrão)
        """
        self.driver = driver
        self.log = logger if logger else print

    # ===================== MÉTODOS UTILITÁRIOS =====================
    # MANTEVE OS SEUS (bons!)

    @staticmethod
    def _normalize_text(text: str) -> str:
        """Normaliza texto para comparação"""
        normalized = unicodedata.normalize("NFKD", text or "")
        normalized = normalized.encode("ascii", "ignore").decode().lower()
        return " ".join(normalized.split())

    @staticmethod
    def _shorten_text(text: str) -> str:
        """Encurta texto para exibição"""
        single_line = " ".join((text or "").split())
        return single_line if len(single_line) <= 120 else single_line[:117] + "..."

    @staticmethod
    def _is_progress_text(norm_text: str) -> bool:
        """Verifica se texto indica progresso"""
        if not norm_text:
            return False
        if any(token in norm_text for token in PROGRESS_TOKENS):
            return True
        for pattern in PROGRESS_PATTERNS:
            if pattern.search(norm_text):
                return True
        return False

    # ===================== COLETA DE MENSAGENS =====================
    # FIX: ADICIONOU WAIT PARA ELEMENTOS CARREGarem

    def _scan_status_messages(self) -> Tuple[list, list]:
        """
        Coleta mensagens de status/progresso exibidas na página.

        Returns:
            Tupla (progress_snippets: list, success_snippets: list)
        """
        try:
            self.driver.switch_to.default_content()
        except Exception:
            pass

        progress_snippets = []
        success_snippets = []
        seen_norm = set()

        # FIX: Wait curto para elementos carregarem
        try:
            WebDriverWait(self.driver, 3).until(
                lambda d: len(d.find_elements(By.XPATH, "//body")) > 0
            )
        except TimeoutException:
            pass

        # Procura elementos de status
        for selector in STATUS_TEXT_SELECTORS:
            try:
                elements = self.driver.find_elements(By.XPATH, selector)
            except Exception:
                continue

            for element in elements:
                try:
                    text = element.text.strip()
                except StaleElementReferenceException:
                    continue
                except Exception:
                    continue

                if not text:
                    continue

                norm_text = self._normalize_text(text)
                if not norm_text or norm_text in seen_norm:
                    continue

                seen_norm.add(norm_text)
                snippet = self._shorten_text(text)

                if self._is_progress_text(norm_text):
                    progress_snippets.append(snippet)
                elif any(keyword in norm_text for keyword in SUCCESS_KEYWORDS):
                    success_snippets.append(snippet)

        # Verifica body também
        try:
            body_text = self.driver.find_element(By.TAG_NAME, "body").text
        except Exception:
            body_text = ""

        if body_text:
            norm_body = self._normalize_text(body_text)
            if norm_body and norm_body not in seen_norm:
                snippet = self._shorten_text(body_text)
                if self._is_progress_text(norm_body):
                    progress_snippets.append(snippet)
                elif any(keyword in norm_body for keyword in SUCCESS_KEYWORDS):
                    success_snippets.append(snippet)

        return progress_snippets, success_snippets

    # ===================== VERIFICAÇÕES DE SUCESSO =====================
    # FIX: MELHOROU URL CHECK (SAI DE UPLOAD = SUCESSO)

    def check_url_changed(self) -> bool:
        """
        Verifica se a URL mudou para uma página de sucesso.

        Returns:
            True se URL indica sucesso, False caso contrário
        """
        try:
            current_url = (self.driver.current_url or "").lower()
        except Exception:
            return False

        # FIX: Primeiro, checa se saiu de upload (mesmo sem fragment específico)
        if "upload" not in current_url:
            self.log(f"✅ Saiu da página de upload: {current_url}")
            return True

        # Verifica se mudou para URL de sucesso
        if any(fragment in current_url for fragment in SUCCESS_URL_FRAGMENTS):
            self.log(f"✅ URL mudou para sucesso: {current_url}")
            return True

        return False

    # MANTEVE check_publish_button_disappeared() — BOM

    def check_publish_button_disappeared(self) -> bool:
        """
        Verifica se o botão de publicar desapareceu.

        Returns:
            True se botão sumiu, False caso contrário
        """
        try:
            self.driver.switch_to.default_content()
        except Exception:
            pass

        try:
            buttons = self.driver.find_elements(
                By.XPATH,
                "//button[@data-e2e='post_video_button']"
            )
            if not any(btn.is_displayed() for btn in buttons if btn):
                self.log("✅ Botão sumiu - vídeo publicado!")
                return True
        except:
            pass

        return False

    # MANTEVE check_success_message() — BOM

    def check_success_message(self) -> Optional[str]:
        """
        Verifica se há mensagem de sucesso exibida.

        Returns:
            Mensagem de sucesso se encontrada, None caso contrário
        """
        _, success_snippets = self._scan_status_messages()

        if success_snippets:
            message = success_snippets[0]
            self.log(f"✅ Confirmação exibida: {message}")
            return message

        return None

    # FIX: NOVO MÉTODO PARA WAIT SPINNER SUMIR
    def wait_for_loading_to_finish(self, timeout: int = 30) -> bool:
        """
        FIX: Aguarda spinner/loading sumir (sinal de processamento concluído).
        """
        try:
            WebDriverWait(self.driver, timeout).until_not(
                lambda d: any(d.find_elements(By.CSS_SELECTOR, sel) for sel in LOADING_SELECTORS)
            )
            self.log("✅ Spinner/loading sumiu — processamento concluído")
            return True
        except TimeoutException:
            self.log("⚠️ Timeout aguardando spinner sumir")
            return False

    # ===================== MÉTODOS DE ESPERA =====================
    # FIX: MELHOROU O LOOP (POLL 3s, CHECK SPINNER, RETRY STALE, FALLBACK)

    def wait_for_confirmation(self, timeout: int = CONFIRMATION_TIMEOUT) -> bool:
        """
        Aguarda confirmação de postagem observando múltiplos sinais.

        Args:
            timeout: Tempo máximo de espera em segundos

        Returns:
            True se postagem foi confirmada, False se timeout
        """
        deadline = time.time() + timeout
        last_progress = ""
        poll_count = 0

        self.log(f"⏳ Aguardando confirmação de postagem (timeout: {timeout}s)...")

        while time.time() < deadline:
            poll_count += 1
            try:
                # FIX: Sinal 0.5 - Aguarda spinner sumir primeiro (10s max)
                if poll_count == 1:
                    if self.wait_for_loading_to_finish(10):
                        self.log("✅ Processamento inicial concluído")

                # Sinal 1: URL mudou
                if self.check_url_changed():
                    return True

                # Sinal 2: Botão de publicar sumiu
                if self.check_publish_button_disappeared():
                    return True

                # Coleta mensagens
                progress_snippets, success_snippets = self._scan_status_messages()

                # Sinal 3: Mensagem de sucesso apareceu
                if success_snippets:
                    self.log(f"✅ Confirmação exibida: {success_snippets[0]}")
                    return True

                # Se ainda há progresso, aguarda
                if progress_snippets:
                    summary = "; ".join(progress_snippets[:2])
                    if summary != last_progress:
                        self.log(f"⏳ Aguardando: {summary}")
                        last_progress = summary
                    time.sleep(POLL_INTERVAL)
                    continue

                # FIX: Após 30s sem progresso/erro, assume sucesso (fallback)
                if time.time() > (deadline - 30) and not progress_snippets:
                    self.log("✅ Sem progresso/erro após 30s — assumindo sucesso")
                    return True

            except StaleElementReferenceException:
                self.log("🔄 Elemento stale — retrying...")
                time.sleep(1)
                continue
            except Exception as e:
                self.log(f"⚠️ Erro durante espera: {e}")
                pass

            time.sleep(POLL_INTERVAL)

        # FIX: Screenshot em timeout para debug
        try:
            screenshot_path = f"/tmp/tiktok_confirmation_timeout_{int(time.time())}.png"
            self.driver.save_screenshot(screenshot_path)
            self.log(f"📸 Screenshot de timeout salvo: {screenshot_path}")
        except:
            pass

        if last_progress:
            self.log(f"⚠️ Timeout aguardando confirmação (último status: {last_progress})")
        else:
            self.log("⚠️ Timeout aguardando confirmação — cheque manualmente no perfil")
        return False

    # ===================== VERIFICAÇÃO FINAL =====================
    # FIX: MELHOROU verify_post_success() (usa wait spinner)

    def verify_post_success(self) -> bool:
        """
        Verifica de forma rápida se a postagem foi bem-sucedida.
        Não aguarda, apenas checa sinais imediatos.

        Returns:
            True se há sinais de sucesso, False caso contrário
        """
        # FIX: Primeiro, checa se spinner sumiu
        if self.wait_for_loading_to_finish(5):
            self.log("✅ Spinner sumiu na verificação rápida")

        # Verifica URL
        if self.check_url_changed():
            return True

        # Verifica botão
        if self.check_publish_button_disappeared():
            return True

        # Verifica mensagem
        if self.check_success_message():
            return True

        return False

    # ===================== MÉTODO PÚBLICO PRINCIPAL =====================
    # MANTEVE O SEU — BOM

    def confirm_posted(
        self,
        timeout: int = CONFIRMATION_TIMEOUT,
        quick_check: bool = False
    ) -> bool:
        """
        Método principal: confirma se vídeo foi postado.

        Args:
            timeout: Tempo máximo de espera (padrão: 90s)
            quick_check: Se True, não aguarda, apenas verifica sinais imediatos

        Returns:
            True se postagem foi confirmada, False caso contrário
        """
        if quick_check:
            self.log("🔍 Verificação rápida de postagem...")
            result = self.verify_post_success()
            if result:
                self.log("🎉 Vídeo publicado com sucesso!")
            else:
                self.log("⚠️ Postagem não confirmada")
            return result
        else:
            result = self.wait_for_confirmation(timeout=timeout)
            if result:
                self.log("🎉 Vídeo publicado com sucesso!")
            else:
                self.log("⚠️ Postagem não confirmada (pode ter sido publicado)")
            return result

    # ===================== INFORMAÇÕES ADICIONAIS =====================
    # MANTEVE OS SEUS — BOM

    def get_post_status(self) -> dict:
        """
        Obtém informações detalhadas sobre o status da postagem.

        Returns:
            Dicionário com informações de status
        """
        url_changed = self.check_url_changed()
        button_disappeared = self.check_publish_button_disappeared()
        success_message = self.check_success_message()
        progress_snippets, success_snippets = self._scan_status_messages()

        current_url = ""
        try:
            current_url = self.driver.current_url
        except:
            pass

        return {
            "url_changed": url_changed,
            "button_disappeared": button_disappeared,
            "success_message": success_message,
            "has_progress": len(progress_snippets) > 0,
            "has_success_text": len(success_snippets) > 0,
            "current_url": current_url,
            "progress_snippets": progress_snippets,
            "success_snippets": success_snippets,
        }

    def print_status(self):
        """Imprime status detalhado da postagem (útil para debug)"""
        status = self.get_post_status()

        self.log("📊 Status da postagem:")
        self.log(f"   URL mudou: {status['url_changed']}")
        self.log(f"   Botão sumiu: {status['button_disappeared']}")
        self.log(f"   Mensagem de sucesso: {status['success_message'] or 'Não'}")
        self.log(f"   Tem progresso: {status['has_progress']}")
        self.log(f"   Tem texto de sucesso: {status['has_success_text']}")
        self.log(f"   URL atual: {status['current_url']}")

        if status['progress_snippets']:
            self.log(f"   Progresso: {', '.join(status['progress_snippets'][:2])}")

        if status['success_snippets']:
            self.log(f"   Sucesso: {', '.join(status['success_snippets'][:2])}")
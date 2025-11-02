"""
Módulo 5: Confirmação de Postagem
Verifica se o vídeo foi efetivamente postado e aparece na lista de vídeos publicados
"""
import time
import re
import unicodedata
from typing import Optional, Callable, Tuple

from selenium.webdriver.common.by import By
from selenium.common.exceptions import StaleElementReferenceException

# Constantes
CONFIRMATION_TIMEOUT = 60  # segundos

SUCCESS_URL_FRAGMENTS = (
    "/post",
    "/content",
    "/creatorpost",
    "/content/manage",
    "/post/success",
    "/upload/success",
)

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

        # Verifica se não está mais na página de upload
        if not current_url or "upload" not in current_url:
            # Verifica se mudou para URL de sucesso
            if any(fragment in current_url for fragment in SUCCESS_URL_FRAGMENTS):
                self.log("✅ URL mudou - vídeo publicado!")
                return True

        return False

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

    # ===================== MÉTODOS DE ESPERA =====================

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

        self.log(f"⏳ Aguardando confirmação de postagem (timeout: {timeout}s)...")

        while time.time() < deadline:
            try:
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
                    time.sleep(3)
                    continue

            except Exception as e:
                self.log(f"⚠️ Erro durante espera: {e}")
                pass

            time.sleep(2)

        # Timeout
        if last_progress:
            self.log(f"⚠️ Timeout aguardando confirmação (último status: {last_progress})")
        else:
            self.log("⚠️ Timeout aguardando confirmação")
        return False

    # ===================== VERIFICAÇÃO FINAL =====================

    def verify_post_success(self) -> bool:
        """
        Verifica de forma rápida se a postagem foi bem-sucedida.
        Não aguarda, apenas checa sinais imediatos.

        Returns:
            True se há sinais de sucesso, False caso contrário
        """
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

    def confirm_posted(
        self,
        timeout: int = CONFIRMATION_TIMEOUT,
        quick_check: bool = False
    ) -> bool:
        """
        Método principal: confirma se vídeo foi postado.

        Args:
            timeout: Tempo máximo de espera (padrão: 60s)
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

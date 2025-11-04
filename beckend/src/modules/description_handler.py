"""
Módulo 2: Tratamento da Descrição (Versão Otimizada v2.3.1 - Fix Import)
Lida exclusivamente com a criação, edição e formatação da descrição do vídeo
Otimizações: Timeout 3s em locate, 2 retries max, no relocate em verify (cache sempre), JS simplificado sem blur/sleep, handle single locate.
"""
import re
import time  # Fix: Adicionado para time.time()
import unicodedata
from typing import Optional, Callable, Tuple

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# Constantes
WAIT_SHORT = 3  # Reduzido para eficiência
MAX_LENGTH = 2200

DESCRIPTION_SELECTORS = [
    (By.CSS_SELECTOR, "div[data-e2e='description-input']"),
    (By.CSS_SELECTOR, "div[data-e2e='caption-input']"),
    (By.CSS_SELECTOR, "div[contenteditable='true'][placeholder*='add description']"),
    (By.CSS_SELECTOR, "div[contenteditable='true'][placeholder*='description']"),
    (By.CSS_SELECTOR, "div[contenteditable='true'][placeholder*='add caption']"),
    (By.CSS_SELECTOR, "div[contenteditable='true'][role='textbox'][aria-label*='add description']"),
    (By.CSS_SELECTOR, "div[contenteditable='true'][aria-label*='description']"),
    (By.CSS_SELECTOR, "div[class*='caption-editor'] div[contenteditable='true']"),
    (By.CSS_SELECTOR, "div[class*='description-field']"),
    (By.CSS_SELECTOR, "textarea[placeholder*='add description']"),
    (By.CSS_SELECTOR, "textarea[placeholder*='description']"),
    (By.XPATH, "//div[@contenteditable='true' and contains(@placeholder, 'description')]"),
    (By.XPATH, "//div[contains(@class, 'caption') and @contenteditable='true']"),
]


class DescriptionModule:
    """
    Módulo responsável pelo tratamento de descrições de vídeos no TikTok.
    Gerencia validação, formatação, sanitização e preenchimento do campo de descrição.
    """

    def __init__(self, driver, logger: Optional[Callable[[str], None]] = None):
        """
        Inicializa o módulo de descrição.

        Args:
            driver: WebDriver do Selenium
            logger: Função de logging (opcional, usa print por padrão)
        """
        self.driver = driver
        self.log = logger if logger else print
        self._cached_field = None  # Cache para eficiência

    # ===================== VALIDAÇÃO E SANITIZAÇÃO =====================

    @staticmethod
    def sanitize_description(text: str) -> str:
        """
        Sanitiza texto da descrição removendo problemáticos (regex otimizado).

        Args:
            text: Texto original

        Returns:
            Sanitizado
        """
        if not text:
            return ""

        # Remove emojis BMP+ (U+10000+)
        sanitized = re.sub(r'[\U00010000-\U0010FFFF]', '', text)

        # Remove control chars (exceto \n\t)
        sanitized = re.sub(r'[\x00-\x1F\x7F]', '', sanitized)

        # Remove espaços extras
        sanitized = re.sub(r'\s+', ' ', sanitized).strip()

        return sanitized

    @staticmethod
    def validate_description_length(text: str, max_length: int = MAX_LENGTH) -> Tuple[bool, str]:
        """
        Valida e ajusta comprimento (mantém palavras).

        Args:
            text: Texto
            max_length: Máximo

        Returns:
            (válido, ajustado)
        """
        if not text:
            return True, ""

        if len(text) <= max_length:
            return True, text

        truncated = text[:max_length]
        last_space = truncated.rfind(' ')
        if last_space > max_length // 2:
            truncated = truncated[:last_space]

        truncated = truncated.rstrip('.,!?;:') + '...'
        return False, truncated

    def prepare_description(self, text: str) -> str:
        """
        Prepare (sanitize + validate).

        Args:
            text: Original

        Returns:
            Preparado
        """
        if not text:
            return ""

        sanitized = self.sanitize_description(text)
        is_valid, adjusted = self.validate_description_length(sanitized)

        if not is_valid:
            self.log(f"⚠️ Truncada de {len(sanitized)} para {len(adjusted)} chars")

        return adjusted

    # ===================== LOCALIZAÇÃO DO CAMPO =====================

    def _wait_visible(self, by: By, value: str, timeout: int = WAIT_SHORT) -> Optional[object]:
        """Espera visível (EC reativo, 3s)"""
        try:
            return WebDriverWait(self.driver, timeout).until(
                EC.visibility_of_element_located((by, value))
            )
        except TimeoutException:
            return None

    def find_description_field(self, timeout: int = WAIT_SHORT, use_cache: bool = True) -> Optional[object]:
        """
        Localiza campo (cache + 2 retries, timeout 3s).

        Args:
            timeout: Máximo (3s)
            use_cache: Usa cache

        Returns:
            Elemento ou None
        """
        if use_cache and self._cached_field:
            try:
                self.driver.execute_script("arguments[0].scrollIntoView();", self._cached_field)
                if self._wait_visible(By.ID, self._cached_field.id, timeout=0.5):
                    self.log("✅ Cache hit")
                    return self._cached_field
            except:
                pass

        deadline = time.time() + timeout
        retries = 2  # Reduzido para eficiência

        for retry in range(retries):
            for by, value in DESCRIPTION_SELECTORS:
                field = self._wait_visible(by, value, timeout=min(1, deadline - time.time()))  # 1s per selector
                if field:
                    self._cached_field = field
                    label = value.split('[')[-1].rstrip(']') if '[' in value else value
                    self.log(f"✅ Encontrado: {label}")
                    return field

            if retry < retries - 1:
                self.log(f"🔄 Retry {retry+1}/2...")
                time.sleep(0.5)  # Backoff curto

        self.log("⚠️ Não encontrado após 2 retries")
        self._cached_field = None
        return None

    # ===================== PREENCHIMENTO =====================

    def _fill_via_javascript(self, field, text: str) -> bool:
        """
        Preenche via JS simplificado (sem blur, dispatch composto).

        Args:
            field: Elemento
            text: Texto

        Returns:
            True se sucesso
        """
        try:
            self.driver.execute_script(
                """
                const el = arguments[0];
                el.focus();
                el.innerText = arguments[1];
                el.dispatchEvent(new InputEvent('input', { bubbles: true, composed: true }));
                el.dispatchEvent(new Event('change', { bubbles: true, composed: true }));
                """,
                field,
                text,
            )
            self.log(f"📝 JS preenchido ({len(text)} chars)")
            return True
        except Exception as e:
            self.log(f"⚠️ Falha JS: {e}")
            return False

    def _fill_via_sendkeys(self, field, text: str) -> bool:
        """
        Fallback send_keys (clear rápido).

        Args:
            field: Elemento
            text: Texto

        Returns:
            True se sucesso
        """
        try:
            field.clear()
            field.send_keys(text)
            self.log(f"📝 Send_keys preenchido ({len(text)} chars)")
            return True
        except Exception as e:
            self.log(f"⚠️ Falha send_keys: {e}")
            return False

    def fill_description(self, text: str, required: bool = False) -> bool:
        """
        Preenche (cache + 3s timeout).

        Args:
            text: Preparado
            required: Falha se não

        Returns:
            True se preenchido
        """
        prepared_text = self.prepare_description(text)
        if not prepared_text:
            self.log("ℹ️ Vazia, pulando")
            return True

        field = self.find_description_field(timeout=3, use_cache=True)
        if not field:
            if required:
                self.log("❌ Campo não encontrado (required=True)")
                return False
            self.log("⚠️ Campo não encontrado (continuando)")
            return True

        # JS primeiro, fallback send_keys
        if self._fill_via_javascript(field, prepared_text):
            return True

        if self._fill_via_sendkeys(field, prepared_text):
            return True

        if required:
            self.log("❌ Falha ambos (required=True)")
            return False
        self.log("⚠️ Falha preenchimento (continuando)")
        return True

    # ===================== VERIFICAÇÃO =====================

    def verify_description_filled(self, expected_text: str) -> bool:
        """
        Verifica (usa cache sempre, partial regex 0.8 overlap ou top 3 words).

        Args:
            expected_text: Esperado

        Returns:
            True se match
        """
        try:
            # No relocate – usa cache ou quick find
            if self._cached_field:
                field = self._cached_field
            else:
                field = self.find_description_field(timeout=2, use_cache=False)
            if not field:
                return False

            # Get text (rápido)
            try:
                current_text = field.text.strip()
            except:
                try:
                    current_text = field.get_attribute('innerText').strip()
                except:
                    current_text = self.driver.execute_script("return arguments[0].innerText;", field).strip()

            # Partial: 80% len + top 3 words intersection (regex para velocidade)
            expected_norm = re.sub(r'\s+', ' ', self._normalize_text(expected_text)).strip()
            current_norm = re.sub(r'\s+', ' ', self._normalize_text(current_text)).strip()
            
            words_expected = expected_norm.split()[:3]  # Top 3 words
            if current_norm == expected_norm or (len(current_norm) >= 0.8 * len(expected_norm) and any(re.search(r'\b' + re.escape(w) + r'\b', current_norm) for w in words_expected)):
                self.log("✅ Verificado (partial)")
                return True

            self.log(f"⚠️ Difere")
            self.log(f"   Esperado: {expected_norm[:100]}...")
            self.log(f"   Atual: {current_norm[:100]}...")
            return False

        except Exception as e:
            self.log(f"⚠️ Erro verificação: {e}")
            return False

    @staticmethod
    def _normalize_text(text: str) -> str:
        """Normalize para match (lower, no accents)"""
        normalized = unicodedata.normalize("NFKD", text or "")
        normalized = normalized.encode("ascii", "ignore").decode().lower()
        return normalized

    def clear_description(self) -> bool:
        """
        Limpa (usa cache, JS rápido).

        Returns:
            True se limpou
        """
        field = self._cached_field if self._cached_field else self.find_description_field(timeout=2, use_cache=False)
        if not field:
            return False

        try:
            self.driver.execute_script(
                """
                const el = arguments[0];
                el.focus();
                el.innerText = '';
                el.dispatchEvent(new InputEvent('input', { bubbles: true, composed: true }));
                """,
                field,
            )
            self.log("✅ Limpo (JS)")
            return True
        except:
            try:
                field.clear()
                self.log("✅ Limpo (clear)")
                return True
            except Exception as e:
                self.log(f"⚠️ Erro clear: {e}")
                return False

    # ===================== MÉTODO PÚBLICO PRINCIPAL =====================

    def handle_description(self, text: str, required: bool = False, verify: bool = False) -> bool:
        """
        Fluxo completo (single locate + fill + verify opcional).

        Args:
            text: Texto
            required: Falha se não preencher
            verify: Verifica match

        Returns:
            True se sucesso
        """
        if not self.fill_description(text, required=required):
            return False

        if verify and text:
            return self.verify_description_filled(text)

        return True
"""
Módulo 2: Tratamento da Descrição
Lida exclusivamente com a criação, edição e formatação da descrição do vídeo
"""
import time
from typing import Optional, Callable

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# Constantes
WAIT_MED = 15

DESCRIPTION_SELECTORS = [
    "div[data-e2e='caption-editor'] div[contenteditable='true']",
    "div[contenteditable='true'][data-placeholder]",
    "div[contenteditable='true'][role='textbox']",
    "div[contenteditable='true'][aria-label*='caption']",
    "div[contenteditable='true'][aria-label*='description']",
    "textarea[placeholder*='caption']",
    "textarea[placeholder*='description']",
]


class DescriptionModule:
    """
    Módulo responsável pelo tratamento de descrições de vídeos no TikTok.
    Gerencia validação, formatação, sanitização e preenchimento do campo de descrição.
    """

    def __init__(self, driver, logger: Optional[Callable] = None):
        """
        Inicializa o módulo de descrição.

        Args:
            driver: WebDriver do Selenium
            logger: Função de logging (opcional, usa print por padrão)
        """
        self.driver = driver
        self.log = logger if logger else print

    # ===================== VALIDAÇÃO E SANITIZAÇÃO =====================

    @staticmethod
    def sanitize_description(text: str) -> str:
        """
        Sanitiza texto da descrição removendo caracteres problemáticos.

        Args:
            text: Texto original da descrição

        Returns:
            Texto sanitizado
        """
        if not text:
            return ""

        # Remove emojis fora do BMP (Chrome não suporta bem)
        # BMP = Basic Multilingual Plane (U+0000 a U+FFFF)
        sanitized = ''.join(char if ord(char) <= 0xFFFF else '' for char in text)

        # Remove caracteres de controle (exceto newline, tab)
        sanitized = ''.join(
            char for char in sanitized
            if char in '\n\t' or ord(char) >= 32
        )

        # Remove espaços extras
        sanitized = ' '.join(sanitized.split())

        return sanitized.strip()

    @staticmethod
    def validate_description_length(text: str, max_length: int = 2200) -> tuple[bool, str]:
        """
        Valida e ajusta o comprimento da descrição.

        Args:
            text: Texto da descrição
            max_length: Tamanho máximo permitido (TikTok permite ~2200 caracteres)

        Returns:
            Tupla (válido: bool, texto_ajustado: str)
        """
        if not text:
            return True, ""

        if len(text) <= max_length:
            return True, text

        # Trunca mantendo palavras inteiras
        truncated = text[:max_length]
        last_space = truncated.rfind(' ')

        if last_space > 0:
            truncated = truncated[:last_space]

        truncated = truncated.rstrip('.,!?;:') + '...'
        return False, truncated

    def prepare_description(self, text: str) -> str:
        """
        Prepara descrição para uso (sanitiza e valida).

        Args:
            text: Texto original

        Returns:
            Texto preparado e pronto para uso
        """
        if not text:
            return ""

        # Sanitiza
        sanitized = self.sanitize_description(text)

        # Valida comprimento
        is_valid, adjusted = self.validate_description_length(sanitized)

        if not is_valid:
            self.log(f"⚠️ Descrição truncada de {len(sanitized)} para {len(adjusted)} caracteres")

        return adjusted

    # ===================== LOCALIZAÇÃO DO CAMPO =====================

    def _wait_visible(self, by, value, timeout=WAIT_MED):
        """Espera elemento ficar visível"""
        return WebDriverWait(self.driver, timeout).until(
            EC.visibility_of_element_located((by, value))
        )

    def find_description_field(self, timeout: int = 10):
        """
        Localiza o campo de descrição na página.

        Args:
            timeout: Tempo máximo de busca em segundos

        Returns:
            Elemento do campo de descrição ou None se não encontrado
        """
        for selector in DESCRIPTION_SELECTORS:
            try:
                field = self._wait_visible(By.CSS_SELECTOR, selector, timeout=timeout)
                if field:
                    self.log(f"✅ Campo de descrição encontrado: {selector}")
                    return field
            except TimeoutException:
                continue
            except Exception as e:
                self.log(f"⚠️ Erro ao buscar seletor {selector}: {e}")
                continue

        self.log("⚠️ Campo de descrição não encontrado")
        return None

    # ===================== PREENCHIMENTO =====================

    def _fill_via_javascript(self, field, text: str) -> bool:
        """
        Preenche campo usando JavaScript (método mais rápido e confiável).

        Args:
            field: Elemento do campo
            text: Texto a preencher

        Returns:
            True se preencheu com sucesso, False caso contrário
        """
        try:
            self.driver.execute_script(
                """
                arguments[0].focus();
                arguments[0].innerText = arguments[1];
                arguments[0].dispatchEvent(new InputEvent('input', { bubbles: true }));
                arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
                """,
                field,
                text,
            )
            self.log(f"📝 Descrição preenchida via JavaScript ({len(text)} chars)")
            return True
        except Exception as e:
            self.log(f"⚠️ Falha ao preencher via JavaScript: {e}")
            return False

    def _fill_via_sendkeys(self, field, text: str) -> bool:
        """
        Preenche campo usando send_keys (fallback mais lento).

        Args:
            field: Elemento do campo
            text: Texto a preencher

        Returns:
            True se preencheu com sucesso, False caso contrário
        """
        try:
            field.clear()
            field.send_keys(text)
            self.log(f"📝 Descrição preenchida via send_keys ({len(text)} chars)")
            return True
        except Exception as e:
            self.log(f"⚠️ Falha ao preencher via send_keys: {e}")
            return False

    def fill_description(self, text: str, required: bool = False) -> bool:
        """
        Preenche o campo de descrição do vídeo.

        Args:
            text: Texto da descrição
            required: Se True, retorna False se não conseguir preencher
                     Se False, continua mesmo sem preencher (opcional)

        Returns:
            True se preencheu ou se não era required, False caso contrário
        """
        # Prepara texto
        prepared_text = self.prepare_description(text)

        if not prepared_text:
            self.log("ℹ️ Descrição vazia, pulando preenchimento")
            return True

        # Localiza campo
        field = self.find_description_field(timeout=10)

        if not field:
            if required:
                self.log("❌ Campo de descrição não encontrado (required=True)")
                return False
            else:
                self.log("⚠️ Campo de descrição não encontrado (continuando sem descrição)")
                return True

        # Tenta preencher (JavaScript primeiro, send_keys como fallback)
        if self._fill_via_javascript(field, prepared_text):
            time.sleep(1)
            return True

        if self._fill_via_sendkeys(field, prepared_text):
            time.sleep(1)
            return True

        # Se chegou aqui, falhou em ambos os métodos
        if required:
            self.log("❌ Falha ao preencher descrição (required=True)")
            return False
        else:
            self.log("⚠️ Não consegui preencher descrição (continuando)")
            return True

    # ===================== VERIFICAÇÃO =====================

    def verify_description_filled(self, expected_text: str) -> bool:
        """
        Verifica se a descrição foi preenchida corretamente.

        Args:
            expected_text: Texto esperado

        Returns:
            True se descrição está correta, False caso contrário
        """
        try:
            field = self.find_description_field(timeout=5)
            if not field:
                return False

            # Obtém texto atual do campo
            try:
                current_text = field.text.strip()
            except:
                try:
                    current_text = field.get_attribute('innerText').strip()
                except:
                    return False

            # Compara (ignora espaços extras)
            expected_normalized = ' '.join(expected_text.split())
            current_normalized = ' '.join(current_text.split())

            if current_normalized == expected_normalized:
                self.log("✅ Descrição verificada e correta")
                return True
            else:
                self.log(f"⚠️ Descrição diferente do esperado")
                self.log(f"   Esperado: {expected_normalized[:100]}...")
                self.log(f"   Atual: {current_normalized[:100]}...")
                return False

        except Exception as e:
            self.log(f"⚠️ Erro ao verificar descrição: {e}")
            return False

    def clear_description(self) -> bool:
        """
        Limpa o campo de descrição.

        Returns:
            True se limpou com sucesso, False caso contrário
        """
        try:
            field = self.find_description_field(timeout=5)
            if not field:
                return False

            # Limpa via JavaScript
            try:
                self.driver.execute_script(
                    """
                    arguments[0].focus();
                    arguments[0].innerText = '';
                    arguments[0].dispatchEvent(new InputEvent('input', { bubbles: true }));
                    """,
                    field,
                )
                self.log("✅ Descrição limpa")
                return True
            except:
                pass

            # Fallback: clear()
            try:
                field.clear()
                self.log("✅ Descrição limpa (via clear)")
                return True
            except:
                pass

            return False

        except Exception as e:
            self.log(f"⚠️ Erro ao limpar descrição: {e}")
            return False

    # ===================== MÉTODO PÚBLICO PRINCIPAL =====================

    def handle_description(self, text: str, required: bool = False, verify: bool = False) -> bool:
        """
        Método principal: gerencia todo o fluxo de descrição.
        1. Prepara texto (sanitiza e valida)
        2. Localiza campo
        3. Preenche
        4. Verifica (opcional)

        Args:
            text: Texto da descrição
            required: Se True, falha se não conseguir preencher
            verify: Se True, verifica se foi preenchido corretamente

        Returns:
            True se todo o fluxo foi bem-sucedido, False caso contrário
        """
        # Preenche
        if not self.fill_description(text, required=required):
            return False

        # Verifica se solicitado
        if verify and text:
            return self.verify_description_filled(text)

        return True

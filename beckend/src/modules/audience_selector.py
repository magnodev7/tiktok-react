# beckend/src/modules/audience_selector.py
"""
Módulo 3: Seleção de Audiência (Versão Otimizada v2.1)
Define o público-alvo (público, privado, amigos) e aplica as configurações.

Mudanças v2.1:
- Corrigido bug de slice booleano em _get_audience_texts (causava "slice step cannot be zero").
- Corrigidos atalhos set_public/set_friends_only/set_private para chamarem set_audience.
- Adicionado alias de retrocompatibilidade set_audiences(...).
- Mantido fluxo, seletores e logs. Pequenos ajustes em regex.
"""

import re
import time
from enum import Enum
from typing import Optional, Callable, List

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# ===== Constantes =====
WAIT_SHORT = 3  # Reduzido para eficiência

AUDIENCE_SELECTORS = [
    (By.CSS_SELECTOR, "div[data-e2e='privacy-selector']"),
    (By.CSS_SELECTOR, "div[data-e2e='audience-selector']"),
    (By.CSS_SELECTOR, "div[class*='audience-dropdown']"),
    (By.CSS_SELECTOR, "div[class*='privacy-menu']"),
    (By.CSS_SELECTOR, "button[aria-label*='audience']"),
    (By.CSS_SELECTOR, "button[aria-label*='privacy']"),
    (By.CSS_SELECTOR, "div[role='button'][data-e2e*='privacy']"),
    (By.XPATH, "//div[contains(@aria-label, 'Who can view') or contains(@aria-label, 'Quem pode assistir')]"),
    (By.XPATH, "//div[contains(text(), 'Who can view') or contains(text(), 'Quem pode assistir')]"),
]

OPTION_SELECTORS = {
    "public": [
        (By.XPATH, "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'everyone') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'public') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'todo mundo')]"),
        (By.CSS_SELECTOR, "[data-e2e*='public']"),
    ],
    "friends": [
        (By.XPATH, "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'friends') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'amigos') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'friends only')]"),
        (By.CSS_SELECTOR, "[data-e2e*='friends']"),
    ],
    "private": [
        (By.XPATH, "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'private') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'privado') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'only you')]"),
        (By.CSS_SELECTOR, "[data-e2e*='private']"),
    ],
}

class AudienceType(Enum):
    """Tipos de audiência disponíveis no TikTok"""
    PUBLIC = "public"          # Todos podem ver
    FRIENDS = "friends"        # Apenas amigos
    PRIVATE = "private"        # Apenas você


# Textos por tipo (multi-idioma / variações)
AUDIENCE_TEXTS = {
    AudienceType.PUBLIC: [
        "everyone", "public", "para todos", "público", "todo mundo",
        "all", "view all", "qualquer pessoa", "todos"
    ],
    AudienceType.FRIENDS: [
        "friends", "amigos", "friends only", "só amigos", "somente amigos",
        "apenas amigos", "apenas seguidores que te seguem", "seguidores que te seguem de volta"
    ],
    AudienceType.PRIVATE: [
        "private", "privado", "only you", "só você", "somente você",
        "apenas você", "me only"
    ],
}


class AudienceModule:
    """
    Módulo responsável pela seleção de audiência do vídeo no TikTok.
    Gerencia a configuração de quem pode visualizar o vídeo postado.
    """

    def __init__(self, driver, logger: Optional[Callable[[str], None]] = None):
        """
        Inicializa o módulo de audiência.

        Args:
            driver: WebDriver do Selenium
            logger: Função de logging (opcional, usa print por padrão)
        """
        self.driver = driver
        self.log = logger if logger else print
        self._cached_page_text = ""  # Cache para eficiência em detect/verify

    # ===================== MÉTODOS UTILITÁRIOS =====================

    def _wait_clickable(self, by: By, value: str, timeout: int = WAIT_SHORT) -> Optional[object]:
        """Espera elemento clicável (EC reativo)"""
        try:
            return WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((by, value))
            )
        except TimeoutException:
            return None

    @staticmethod
    def _normalize_text(text: str) -> str:
        """Normaliza texto para comparação (lowercase, sem espaços extras)"""
        return re.sub(r'\s+', ' ', text.lower().strip())

    def _get_page_text(self, refresh: bool = False) -> str:
        """Obtém texto da página (cache se não refresh)"""
        if not refresh and self._cached_page_text:
            return self._cached_page_text

        try:
            selectors = [
                "//div[contains(@data-e2e, 'audience') or contains(@data-e2e, 'privacy')]",
                "//*[contains(@class, 'audience') or contains(@class, 'privacy')]",
                "//*[contains(text(), 'Who can') or contains(text(), 'Quem pode')]",
                "//body",  # Fallback body
            ]
            page_text = ""
            for selector in selectors:
                elements = self.driver.find_elements(By.XPATH, selector)
                for element in elements:
                    try:
                        page_text += " " + element.text
                    except Exception:
                        pass
            self._cached_page_text = self._normalize_text(page_text)
            return self._cached_page_text
        except Exception as e:
            self.log(f"⚠️ Erro ao obter texto da página: {e}")
            return ""

    # ===================== DETECÇÃO DE AUDIÊNCIA ATUAL =====================

    def detect_current_audience(self) -> Optional[AudienceType]:
        """
        Detecta audiência atual (partial regex, cache de texto).

        Returns:
            Tipo ou None
        """
        page_text = self._get_page_text(refresh=True)

        if not page_text:
            self.log("⚠️ Texto da página vazio – não detectado")
            return None

        # Partial match com regex (sem \b rígido, para não perder variações)
        for audience_type in AudienceType:
            texts = self._get_audience_texts(audience_type)
            pattern = "(" + "|".join(re.escape(t) for t in texts) + ")"
            if re.search(pattern, page_text, re.IGNORECASE):
                self.log(f"🔍 Detectado: {audience_type.value}")
                return audience_type

        self.log("⚠️ Não detectado – texto não match")
        return None

    def _get_audience_texts(self, audience_type: AudienceType) -> List[str]:
        """
        Textos por tipo (multi-idioma, partial).
        """
        return AUDIENCE_TEXTS.get(audience_type, [])

    # ===================== SELEÇÃO DE AUDIÊNCIA =====================

    def _find_audience_selector(self) -> Optional[object]:
        """
        Localiza dropdown de audiência (EC clickable, 3s).
        """
        for by, value in AUDIENCE_SELECTORS:
            element = self._wait_clickable(by, value, timeout=3)
            if element:
                self.log("✅ Selector de audiência encontrado")
                return element

        self.log("⚠️ Selector não encontrado")
        return None

    def _click_audience_option(self, audience_type: AudienceType) -> bool:
        """
        Clica na opção (partial XPath, EC 3s).
        """
        texts = self._get_audience_texts(audience_type)
        if not texts:
            self.log(f"⚠️ Sem textos configurados para: {audience_type.value}")
            return False

        conditions = [
            f"contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{t.lower()}')"
            for t in texts
        ]
        xpath = f"//*[{' or '.join(conditions)}]"

        try:
            option = self._wait_clickable(By.XPATH, xpath, timeout=3)
            if not option:
                raise TimeoutException("Opção não clicável no timeout")
            option.click()
            self.log(f"✅ Opção clicada: {audience_type.value}")
            time.sleep(0.5)  # Sync mínimo
            return True
        except TimeoutException:
            self.log(f"⚠️ Opção '{audience_type.value}' não encontrada")
            return False
        except Exception as e:
            self.log(f"⚠️ Erro clique: {e}")
            return False

    def set_audience(self, audience_type: AudienceType, required: bool = False) -> bool:
        """
        Define audiência (EC + partial).
        """
        current = self.detect_current_audience()
        if current == audience_type:
            self.log(f"✅ Já em '{audience_type.value}'")
            return True

        selector = self._find_audience_selector()
        if not selector:
            if required:
                self.log("❌ Selector não encontrado (required=True)")
                return False
            self.log("ℹ️ Selector não encontrado (continuando)")
            return True

        try:
            selector.click()
            time.sleep(0.5)
        except Exception as e:
            self.log(f"⚠️ Erro abrir dropdown: {e}")
            if required:
                return False
            return True

        if self._click_audience_option(audience_type):
            return True

        if required:
            return False
        self.log("⚠️ Não selecionado (continuando)")
        return True

    # ===================== ATALHOS =====================

    def set_public(self, required: bool = False) -> bool:
        """Atalho público."""
        return self.set_audience(AudienceType.PUBLIC, required=required)

    def set_friends_only(self, required: bool = False) -> bool:
        """Atalho amigos."""
        return self.set_audience(AudienceType.FRIENDS, required=required)

    def set_private(self, required: bool = False) -> bool:
        """Atalho privado."""
        return self.set_audience(AudienceType.PRIVATE, required=required)

    # ===================== VERIFICAÇÃO =====================

    def verify_audience(self, expected: AudienceType) -> bool:
        """
        Verifica (usa cache texto, partial regex).
        """
        page_text = self._get_page_text(refresh=True)

        if not page_text:
            self.log("⚠️ Texto vazio – não verificado")
            return False

        texts = self._get_audience_texts(expected)
        if not texts:
            self.log(f"⚠️ Sem textos para verificação de '{expected.value}'")
            return False

        pattern = "(" + "|".join(re.escape(t) for t in texts) + ")"
        if re.search(pattern, page_text, re.IGNORECASE):
            self.log(f"✅ Verificado: {expected.value}")
            return True

        self.log(f"⚠️ Incorreto: esperado '{expected.value}', texto: '{page_text[:120]}...'")
        return False

    # ===================== MÉTODO PÚBLICO PRINCIPAL =====================

    def handle_audience(self, audience_type: AudienceType = AudienceType.PUBLIC, required: bool = False, verify: bool = False) -> bool:
        """
        Fluxo completo (detect + set + verify opcional).
        """
        self.log(f"🎯 Configurando: {audience_type.value}")

        if not self.set_audience(audience_type, required=required):
            return False

        if verify:
            return self.verify_audience(audience_type)

        return True

    # ===================== RETROCOMPAT =====================

    def set_audiences(self, audience_type: AudienceType, required: bool = False, verify: bool = False) -> bool:
        """
        Alias legado para compatibilidade com testes antigos.
        """
        ok = self.set_audience(audience_type, required=required)
        if ok and verify:
            return self.verify_audience(audience_type)
        return ok

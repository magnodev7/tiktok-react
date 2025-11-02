"""
Módulo 3: Seleção de Audiência
Define o público-alvo (público, privado, restrito etc.) e aplica as configurações
"""
import time
from enum import Enum
from typing import Optional, Callable

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# Constantes
WAIT_SHORT = 5


class AudienceType(Enum):
    """Tipos de audiência disponíveis no TikTok"""
    PUBLIC = "public"          # Todos podem ver
    FRIENDS = "friends"        # Apenas amigos
    PRIVATE = "private"        # Apenas você
    # MUTUAL_FOLLOWERS = "mutual_followers"  # Seguidores mútuos (se TikTok suportar)


class AudienceModule:
    """
    Módulo responsável pela seleção de audiência de vídeos no TikTok.
    Gerencia a configuração de quem pode visualizar o vídeo postado.
    """

    def __init__(self, driver, logger: Optional[Callable] = None):
        """
        Inicializa o módulo de audiência.

        Args:
            driver: WebDriver do Selenium
            logger: Função de logging (opcional, usa print por padrão)
        """
        self.driver = driver
        self.log = logger if logger else print

        # Mapeamento de tipos para textos esperados no TikTok (multi-idioma)
        self._audience_text_map = {
            AudienceType.PUBLIC: [
                "everyone", "para todos", "público", "public",
                "todo mundo", "todos", "publico"
            ],
            AudienceType.FRIENDS: [
                "friends", "amigos", "friends only", "só amigos",
                "somente amigos"
            ],
            AudienceType.PRIVATE: [
                "private", "privado", "only you", "só você",
                "somente você", "apenas você"
            ],
        }

    # ===================== MÉTODOS UTILITÁRIOS =====================

    def _wait_element(self, by, value, timeout=WAIT_SHORT):
        """Espera elemento aparecer"""
        return WebDriverWait(self.driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )

    def _wait_clickable(self, by, value, timeout=WAIT_SHORT):
        """Espera elemento ficar clicável"""
        return WebDriverWait(self.driver, timeout).until(
            EC.element_to_be_clickable((by, value))
        )

    @staticmethod
    def _normalize_text(text: str) -> str:
        """Normaliza texto para comparação (lowercase, sem espaços extras)"""
        return ' '.join(text.lower().split())

    # ===================== DETECÇÃO DE AUDIÊNCIA ATUAL =====================

    def _get_audience_texts(self, audience_type: AudienceType) -> list[str]:
        """
        Retorna lista de textos possíveis para um tipo de audiência.

        Args:
            audience_type: Tipo de audiência

        Returns:
            Lista de strings possíveis (normalizadas)
        """
        return [
            self._normalize_text(text)
            for text in self._audience_text_map.get(audience_type, [])
        ]

    def detect_current_audience(self) -> Optional[AudienceType]:
        """
        Detecta qual é a audiência atualmente selecionada.

        Returns:
            Tipo de audiência atual ou None se não conseguir detectar
        """
        try:
            # Procura elementos que possam indicar a seleção atual
            selectors = [
                "//*[contains(@data-e2e, 'audience')]",
                "//*[contains(text(), 'Who can watch')]",
                "//*[contains(text(), 'Quem pode assistir')]",
                "//*[contains(@class, 'audience')]",
                "//*[contains(@class, 'privacy')]",
            ]

            page_text = ""
            for selector in selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for elem in elements:
                        try:
                            page_text += " " + elem.text
                        except:
                            pass
                except:
                    pass

            normalized_page = self._normalize_text(page_text)

            # Tenta identificar qual audiência está ativa
            for audience_type, texts in self._audience_text_map.items():
                for text in texts:
                    if self._normalize_text(text) in normalized_page:
                        self.log(f"🔍 Audiência detectada: {audience_type.value}")
                        return audience_type

            self.log("⚠️ Não foi possível detectar audiência atual")
            return None

        except Exception as e:
            self.log(f"⚠️ Erro ao detectar audiência: {e}")
            return None

    # ===================== SELEÇÃO DE AUDIÊNCIA =====================

    def _find_audience_selector(self) -> Optional[any]:
        """
        Localiza o botão/dropdown de seleção de audiência.

        Returns:
            Elemento do seletor ou None se não encontrado
        """
        # Seletores conhecidos para o controle de audiência
        selectors = [
            "//div[@data-e2e='audience-selector']",
            "//div[contains(@data-e2e, 'privacy')]",
            "//div[contains(text(), 'Who can watch')]",
            "//div[contains(text(), 'Quem pode assistir')]",
            "//button[contains(@aria-label, 'audience')]",
            "//button[contains(@aria-label, 'privacy')]",
        ]

        for selector in selectors:
            try:
                element = self._wait_clickable(By.XPATH, selector, timeout=WAIT_SHORT)
                if element:
                    self.log(f"✅ Seletor de audiência encontrado")
                    return element
            except TimeoutException:
                continue
            except Exception:
                continue

        self.log("⚠️ Seletor de audiência não encontrado")
        return None

    def _click_audience_option(self, audience_type: AudienceType) -> bool:
        """
        Clica na opção de audiência desejada no dropdown aberto.

        Args:
            audience_type: Tipo de audiência desejado

        Returns:
            True se clicou com sucesso, False caso contrário
        """
        audience_texts = self._get_audience_texts(audience_type)

        # Cria XPath que procura por qualquer um dos textos possíveis
        conditions = [f"contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{text}')"
                      for text in audience_texts]
        xpath = f"//*[{' or '.join(conditions)}]"

        try:
            option = self._wait_clickable(By.XPATH, xpath, timeout=WAIT_SHORT)
            option.click()
            self.log(f"✅ Audiência selecionada: {audience_type.value}")
            return True
        except TimeoutException:
            self.log(f"⚠️ Opção de audiência '{audience_type.value}' não encontrada")
            return False
        except Exception as e:
            self.log(f"⚠️ Erro ao clicar em audiência: {e}")
            return False

    def set_audience(self, audience_type: AudienceType, required: bool = False) -> bool:
        """
        Define o tipo de audiência do vídeo.

        Args:
            audience_type: Tipo de audiência desejado
            required: Se True, retorna False se não conseguir definir

        Returns:
            True se definiu ou se não era required, False caso contrário
        """
        # Verifica se já está na audiência desejada
        current = self.detect_current_audience()
        if current == audience_type:
            self.log(f"✅ Audiência já está configurada como '{audience_type.value}'")
            return True

        # Localiza seletor
        selector = self._find_audience_selector()
        if not selector:
            if required:
                self.log(f"❌ Seletor de audiência não encontrado (required=True)")
                return False
            else:
                self.log("ℹ️ Seletor não encontrado (continuando sem alteração)")
                return True

        # Abre dropdown
        try:
            selector.click()
            time.sleep(1)
        except Exception as e:
            self.log(f"⚠️ Erro ao abrir seletor de audiência: {e}")
            if required:
                return False
            else:
                return True

        # Seleciona opção
        if self._click_audience_option(audience_type):
            time.sleep(1)
            return True
        else:
            if required:
                return False
            else:
                self.log("⚠️ Não consegui selecionar audiência (continuando)")
                return True

    # ===================== ATALHOS PARA TIPOS COMUNS =====================

    def set_public(self, required: bool = False) -> bool:
        """
        Atalho: Define audiência como pública (todos podem ver).

        Args:
            required: Se True, retorna False se não conseguir

        Returns:
            True se definiu ou não era required, False caso contrário
        """
        return self.set_audience(AudienceType.PUBLIC, required=required)

    def set_friends_only(self, required: bool = False) -> bool:
        """
        Atalho: Define audiência como apenas amigos.

        Args:
            required: Se True, retorna False se não conseguir

        Returns:
            True se definiu ou não era required, False caso contrário
        """
        return self.set_audience(AudienceType.FRIENDS, required=required)

    def set_private(self, required: bool = False) -> bool:
        """
        Atalho: Define audiência como privada (apenas você).

        Args:
            required: Se True, retorna False se não conseguir

        Returns:
            True se definiu ou não era required, False caso contrário
        """
        return self.set_audience(AudienceType.PRIVATE, required=required)

    # ===================== VERIFICAÇÃO =====================

    def verify_audience(self, expected: AudienceType) -> bool:
        """
        Verifica se a audiência está configurada corretamente.

        Args:
            expected: Tipo de audiência esperado

        Returns:
            True se está correto, False caso contrário
        """
        current = self.detect_current_audience()

        if current == expected:
            self.log(f"✅ Audiência verificada: {expected.value}")
            return True
        elif current is None:
            self.log(f"⚠️ Não foi possível verificar audiência")
            return False
        else:
            self.log(f"⚠️ Audiência incorreta: esperado '{expected.value}', atual '{current.value}'")
            return False

    # ===================== MÉTODO PÚBLICO PRINCIPAL =====================

    def handle_audience(
        self,
        audience_type: AudienceType = AudienceType.PUBLIC,
        required: bool = False,
        verify: bool = False
    ) -> bool:
        """
        Método principal: gerencia todo o fluxo de seleção de audiência.
        1. Detecta audiência atual
        2. Define nova audiência (se necessário)
        3. Verifica (opcional)

        Args:
            audience_type: Tipo de audiência desejado (padrão: PUBLIC)
            required: Se True, falha se não conseguir definir
            verify: Se True, verifica se foi configurado corretamente

        Returns:
            True se todo o fluxo foi bem-sucedido, False caso contrário
        """
        self.log(f"🎯 Configurando audiência: {audience_type.value}")

        # Define audiência
        if not self.set_audience(audience_type, required=required):
            return False

        # Verifica se solicitado
        if verify:
            return self.verify_audience(audience_type)

        return True

"""
Módulo 4: Ação de Postagem
Executa o clique/trigger para iniciar a postagem efetiva na plataforma
Gerencia modais de confirmação e bloqueios
"""
import time
from typing import Optional, Callable

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    ElementClickInterceptedException,
)

# Constantes
WAIT_SHORT = 3
WAIT_MED = 5


# Seletores robustos para o botão de publicar (ordem de prioridade)
PUBLISH_BUTTON_SELECTORS = [
    # Seletores data-e2e (mais confiáveis)
    "//button[@data-e2e='post_video_button' and not(@disabled)]",
    "//button[@data-e2e='post_button' and not(@disabled)]",
    "//button[@data-e2e='publish-button' and not(@disabled)]",
    "//button[@data-e2e='submit-button' and not(@disabled)]",

    # Seletores por texto (vários idiomas)
    "//button[contains(translate(normalize-space(.), 'POST', 'post'), 'post') and not(@disabled)]",
    "//button[contains(translate(normalize-space(.), 'PUBLICAR', 'publicar'), 'publicar') and not(@disabled)]",
    "//button[contains(translate(normalize-space(.), 'PUBLISH', 'publish'), 'publish') and not(@disabled)]",
    "//button[contains(translate(normalize-space(.), 'SUBMIT', 'submit'), 'submit') and not(@disabled)]",
    "//button[contains(translate(normalize-space(.), 'ENVIAR', 'enviar'), 'enviar') and not(@disabled)]",

    # Seletores genéricos por classe/tipo
    "//button[contains(@class, 'post') and not(@disabled)]",
    "//button[contains(@class, 'submit') and not(@disabled)]",
    "//button[contains(@class, 'publish') and not(@disabled)]",
    "//button[@type='submit' and not(@disabled)]",

    # Seletores por hierarquia (último recurso)
    "//div[contains(@class, 'publish')]//button[not(@disabled)]",
    "//div[contains(@class, 'submit')]//button[not(@disabled)]",
    "//form//button[@type='submit' and not(@disabled)]",
]

# Seletores para modais de confirmação
CONFIRMATION_BUTTON_SELECTORS = [
    "//button[contains(., 'Post') or contains(., 'Continue') or contains(., 'Publicar')]",
    "//button[contains(., 'Confirm') or contains(., 'Confirmar')]",
    "//button[@data-e2e='confirm-button']",
    "//button[@data-e2e='post-confirm']",
]

# Seletores para modal "Are you sure you want to exit?"
EXIT_MODAL_SELECTORS = [
    "//button[contains(translate(., 'CANCEL', 'cancel'), 'cancel')]",
    "//button[contains(translate(., 'CANCELAR', 'cancelar'), 'cancelar')]",
]

# Seletores para fechar modais TUX
CLOSE_MODAL_SELECTORS = [
    "//div[@class='TUXModal-overlay']//button[contains(@aria-label, 'Close')]",
    "//div[@class='TUXModal-overlay']//button[contains(@class, 'close')]",
    "//div[contains(@class, 'Modal')]//button[@aria-label='Close']",
    "//button[contains(@class, 'close') and contains(@class, 'modal')]",
]


class PostActionModule:
    """
    Módulo responsável pela ação de postagem no TikTok.
    Gerencia o clique no botão de publicar e lida com modais de confirmação.
    """

    def __init__(self, driver, logger: Optional[Callable] = None):
        """
        Inicializa o módulo de ação de postagem.

        Args:
            driver: WebDriver do Selenium
            logger: Função de logging (opcional, usa print por padrão)
        """
        self.driver = driver
        self.log = logger if logger else print

    # ===================== MÉTODOS UTILITÁRIOS =====================

    def _wait_clickable(self, by, value, timeout=WAIT_MED):
        """Espera elemento ficar clicável"""
        return WebDriverWait(self.driver, timeout).until(
            EC.element_to_be_clickable((by, value))
        )

    def _scroll_to_element(self, element):
        """Rola a página até o elemento"""
        try:
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});",
                element
            )
            time.sleep(0.5)
        except Exception as e:
            self.log(f"⚠️ Erro ao rolar até elemento: {e}")

    def _click_element(self, element) -> bool:
        """
        Tenta clicar em elemento (normal primeiro, JavaScript como fallback).

        Returns:
            True se clicou com sucesso, False caso contrário
        """
        # Tenta clique normal
        try:
            element.click()
            return True
        except ElementClickInterceptedException:
            # Fallback: JavaScript click
            try:
                self.driver.execute_script("arguments[0].click();", element)
                return True
            except Exception as e:
                self.log(f"⚠️ Falha ao clicar (JS): {e}")
                return False
        except Exception as e:
            self.log(f"⚠️ Falha ao clicar: {e}")
            return False

    # ===================== DETECÇÃO DE VIOLAÇÕES =====================

    def detect_content_violation(self) -> bool:
        """
        Detecta se TikTok rejeitou o vídeo por violação de conteúdo.

        Returns:
            True se violação detectada, False caso contrário
        """
        violation_keywords = [
            "violation reason",
            "unoriginal",
            "low-quality",
            "violação",
            "baixa qualidade",
            "content that is just imported or copied",
            "conteúdo importado",
            "conteúdo copiado",
        ]

        try:
            page_text = self.driver.find_element(By.TAG_NAME, "body").text.lower()
            violation_detected = any(keyword in page_text for keyword in violation_keywords)

            if violation_detected:
                self.log("⚠️ ========================================")
                self.log("⚠️ TIKTOK REJEITOU O VÍDEO!")
                self.log("⚠️ Motivo: Conteúdo não-original ou baixa qualidade")
                self.log("⚠️ Solução: Trocar o vídeo por conteúdo original")
                self.log("⚠️ ========================================")

                # Salva screenshot do aviso
                try:
                    screenshot_path = f"/tmp/tiktok_violation_warning_{int(time.time())}.png"
                    self.driver.save_screenshot(screenshot_path)
                    self.log(f"📸 Screenshot do aviso salvo: {screenshot_path}")
                except:
                    pass

                return True

            return False

        except Exception as e:
            self.log(f"⚠️ Erro ao detectar violação: {e}")
            return False

    # ===================== GERENCIAMENTO DE MODAIS =====================

    def close_exit_modal(self) -> bool:
        """
        Fecha modal "Are you sure you want to exit?" clicando em Cancel.

        Returns:
            True se modal foi fechado, False se não havia modal
        """
        for selector in EXIT_MODAL_SELECTORS:
            try:
                button = self.driver.find_element(By.XPATH, selector)
                if button.is_displayed():
                    button.click()
                    self.log("🚪 Modal 'exit' fechado - clicado em Cancel")
                    time.sleep(2)
                    return True
            except:
                continue

        return False

    def close_blocking_modals(self) -> bool:
        """
        Fecha modais TUX que podem estar bloqueando a interação.

        Returns:
            True se algum modal foi fechado, False caso contrário
        """
        for selector in CLOSE_MODAL_SELECTORS:
            try:
                button = self.driver.find_element(By.XPATH, selector)
                if button.is_displayed():
                    button.click()
                    self.log("🚪 Modal TUX fechado")
                    time.sleep(1)
                    return True
            except:
                continue

        return False

    def handle_confirmation_dialog(self) -> bool:
        """
        Lida com modal de confirmação "Continue to post?".
        Fecha modais de bloqueio primeiro, depois confirma postagem.

        Returns:
            True se lidou com sucesso ou modal não apareceu, False se falhou
        """
        try:
            # PASSO 1: Verifica e fecha modal "exit" se existir
            self.close_exit_modal()

            # PASSO 2: Fecha modais TUX que podem estar bloqueando
            self.close_blocking_modals()

            # PASSO 3: Aguarda modal de confirmação aparecer (ou não)
            try:
                WebDriverWait(self.driver, WAIT_MED).until(
                    EC.presence_of_element_located(
                        (By.XPATH, CONFIRMATION_BUTTON_SELECTORS[0])
                    )
                )
            except TimeoutException:
                # Modal não apareceu (tudo bem)
                return True

            # PASSO 4: Clica no botão de confirmar
            for selector in CONFIRMATION_BUTTON_SELECTORS:
                try:
                    confirm_btn = self._wait_clickable(By.XPATH, selector, timeout=WAIT_SHORT)

                    if self._click_element(confirm_btn):
                        self.log("✅ Modal de confirmação resolvido")
                        time.sleep(3)

                        # DEBUG: Screenshot após clicar
                        try:
                            screenshot_path = f"/tmp/tiktok_after_confirm_{int(time.time())}.png"
                            self.driver.save_screenshot(screenshot_path)
                            self.log(f"📸 Screenshot após confirmação: {screenshot_path}")
                        except:
                            pass

                        # Aguarda modal fechar
                        try:
                            WebDriverWait(self.driver, WAIT_MED).until_not(
                                EC.visibility_of_element_located((By.CLASS_NAME, "TUXModal-overlay"))
                            )
                            self.log("✅ Modal TUX fechou")
                        except:
                            pass

                        return True

                except TimeoutException:
                    continue
                except Exception:
                    continue

            # Se chegou aqui, não encontrou botão de confirmar
            self.log("⚠️ Botão de confirmação não encontrado")
            return True  # Não falha por isso

        except Exception as e:
            self.log(f"⚠️ Erro no modal de confirmação: {e}")
            # Tenta fallback com JavaScript
            try:
                buttons = self.driver.find_elements(
                    By.XPATH,
                    "//button[contains(., 'Post') or contains(., 'Continue') or contains(., 'Publicar')]"
                )
                if buttons:
                    self.driver.execute_script("arguments[0].click();", buttons[0])
                    self.log("✅ Modal resolvido via JS (fallback)")
                    time.sleep(3)
            except:
                pass
            return True  # Não falha por isso

    # ===================== AÇÃO DE PUBLICAR =====================

    def click_publish_button(self) -> bool:
        """
        Localiza e clica no botão de publicar.

        Returns:
            True se clicou com sucesso, False caso contrário
        """
        # Rola até o final da página
        try:
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
        except:
            pass

        self.log(f"🔍 Procurando botão de publicar ({len(PUBLISH_BUTTON_SELECTORS)} seletores)...")

        for idx, selector in enumerate(PUBLISH_BUTTON_SELECTORS, 1):
            try:
                button = self._wait_clickable(By.XPATH, selector, timeout=WAIT_SHORT)

                # Rola até o botão
                self._scroll_to_element(button)

                # Clica
                if self._click_element(button):
                    self.log(f"🚀 Botão de publicar clicado (seletor #{idx})")
                    time.sleep(3)
                    return True

            except TimeoutException:
                continue
            except Exception as e:
                self.log(f"⚠️ Erro ao tentar seletor #{idx}: {e}")
                continue

        self.log("❌ Botão de publicar não encontrado")

        # DEBUG: Salva screenshot
        try:
            screenshot_path = f"/tmp/tiktok_publish_button_not_found_{int(time.time())}.png"
            self.driver.save_screenshot(screenshot_path)
            self.log(f"📸 Screenshot salvo: {screenshot_path}")
        except:
            pass

        return False

    # ===================== MÉTODO PÚBLICO PRINCIPAL =====================

    def execute_post(self, handle_modals: bool = True, retry_on_exit: bool = True) -> bool:
        """
        Método principal: executa toda a ação de postagem.
        1. Clica no botão de publicar
        2. Lida com modais de confirmação (se habilitado)
        3. Detecta violações de conteúdo
        4. Retenta se modal "exit" foi fechado (se habilitado)

        Args:
            handle_modals: Se True, lida com modais de confirmação
            retry_on_exit: Se True, retenta publicar após fechar modal exit

        Returns:
            True se postagem foi iniciada, False caso contrário
        """
        self.log("🚀 Executando ação de postagem...")

        # Clica em publicar
        if not self.click_publish_button():
            return False

        # Lida com modais
        if handle_modals:
            if not self.handle_confirmation_dialog():
                self.log("⚠️ Falha ao lidar com modal de confirmação")

        # Verifica violação de conteúdo
        if self.detect_content_violation():
            self.log("❌ Vídeo rejeitado por violação de conteúdo")
            return False

        # Retenta se modal "exit" foi fechado
        if retry_on_exit:
            try:
                # Verifica se ainda está na página de upload (não publicou)
                if "upload" in self.driver.current_url.lower():
                    self.log("🔁 Ainda na página de upload, tentando publicar novamente...")
                    if self.click_publish_button():
                        self.log("✅ Segundo clique em publicar executado")
                        time.sleep(2)
                        # Tenta lidar com modal de novo
                        if handle_modals:
                            self.handle_confirmation_dialog()
            except:
                pass

        self.log("✅ Ação de postagem concluída")
        return True

    # ===================== VERIFICAÇÕES AUXILIARES =====================

    def is_on_upload_page(self) -> bool:
        """
        Verifica se ainda está na página de upload.

        Returns:
            True se está na página de upload, False caso contrário
        """
        try:
            current_url = self.driver.current_url.lower()
            return "upload" in current_url
        except:
            return False

    def publish_button_exists(self) -> bool:
        """
        Verifica se o botão de publicar ainda existe na página.

        Returns:
            True se botão existe, False caso contrário
        """
        try:
            buttons = self.driver.find_elements(
                By.XPATH,
                "//button[@data-e2e='post_video_button']"
            )
            return any(btn.is_displayed() for btn in buttons if btn)
        except:
            return False

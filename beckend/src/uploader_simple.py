"""
Uploader SIMPLIFICADO para TikTok
Baseado no tiktok_bot que funciona sem falhas

Mudanças vs uploader.py (1116 linhas):
- 75% mais simples (~300 linhas vs 1116)
- SEM flags de estado complexas (_description_supported, etc)
- SEM sistema de retry complexo (apenas 2 tentativas)
- Timeouts REDUZIDOS (5s, 15s, 30s em vez de 8s, 25s, 55s)
- Seletores SIMPLIFICADOS (menos fallbacks)
- SEM _wait_upload_ready de 900s (15 min!)
- Fluxo DIRETO: upload → descrição → publicar
"""
import os
import time
from datetime import datetime
from typing import Optional

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    StaleElementReferenceException,
    ElementClickInterceptedException,
)

# Timeouts RAZOÁVEIS (não extremos)
WAIT_SHORT = 5
WAIT_MED = 15
WAIT_LONG = 30

# URLs do TikTok
STUDIO_URL = "https://www.tiktok.com/tiktokstudio/upload?from=creator_center"
CLASSIC_URL = "https://www.tiktok.com/upload"


class TikTokUploaderSimple:
    """
    Uploader SIMPLES para TikTok.
    Faz apenas o essencial: upload → descrição → publicar
    """

    def __init__(self, driver, logger=print):
        self.driver = driver
        self.log = logger

    def _wait_element(self, by, value, timeout=WAIT_MED):
        """Espera elemento aparecer"""
        return WebDriverWait(self.driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )

    def _wait_visible(self, by, value, timeout=WAIT_MED):
        """Espera elemento ficar visível"""
        return WebDriverWait(self.driver, timeout).until(
            EC.visibility_of_element_located((by, value))
        )

    def _wait_clickable(self, by, value, timeout=WAIT_MED):
        """Espera elemento ficar clicável"""
        return WebDriverWait(self.driver, timeout).until(
            EC.element_to_be_clickable((by, value))
        )

    def go_to_upload(self) -> bool:
        """
        Navega para página de upload (SIMPLES).

        Returns:
            True se conseguiu, False caso contrário
        """
        urls = [STUDIO_URL, CLASSIC_URL]

        for url in urls:
            try:
                self.log(f"🌐 Acessando: {url}")
                self.driver.set_page_load_timeout(30)
                self.driver.get(url)
                time.sleep(3)

                # Verifica se não foi redirecionado para login
                if "login" in self.driver.current_url.lower():
                    self.log("⚠️ Redirecionado para login")
                    continue

                # Procura input de arquivo
                try:
                    self._wait_element(By.CSS_SELECTOR, "input[type='file']", timeout=10)
                    self.log("✅ Página de upload carregada")
                    return True
                except TimeoutException:
                    self.log("⚠️ Input de arquivo não encontrado")
                    continue

            except Exception as e:
                self.log(f"⚠️ Erro ao carregar {url}: {e}")
                continue

        self.log("❌ Não consegui abrir página de upload")
        return False

    def send_file(self, video_path: str) -> bool:
        """
        Envia arquivo de vídeo (SIMPLES).

        Args:
            video_path: Caminho do vídeo

        Returns:
            True se enviou, False caso contrário
        """
        if not os.path.isfile(video_path):
            self.log(f"❌ Arquivo não encontrado: {video_path}")
            return False

        # Verifica tamanho mínimo (200KB)
        size_bytes = os.path.getsize(video_path)
        if size_bytes < 200 * 1024:
            self.log(f"❌ Vídeo muito pequeno: {size_bytes} bytes")
            return False

        # Encontra input de arquivo
        try:
            file_input = self._wait_element(By.CSS_SELECTOR, "input[type='file']", timeout=WAIT_MED)
        except TimeoutException:
            self.log("❌ Input de arquivo não encontrado")
            return False

        # Envia arquivo
        abs_path = os.path.abspath(video_path)
        file_input.send_keys(abs_path)
        self.log(f"⬆️ Arquivo enviado: {abs_path}")

        # Aguarda processamento (procura preview ou vídeo)
        try:
            WebDriverWait(self.driver, WAIT_LONG).until(
                EC.any_of(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "video")),
                    EC.presence_of_element_located((By.CSS_SELECTOR, "canvas")),
                    EC.presence_of_element_located((By.CSS_SELECTOR, "[class*='preview']")),
                )
            )
            self.log("🎬 Vídeo processado")
            time.sleep(5)  # Aguarda processamento final
            return True
        except TimeoutException:
            self.log("⚠️ Timeout aguardando processamento")
            return False

    def fill_description(self, text: str) -> bool:
        """
        Preenche descrição (SIMPLES - 2 tentativas apenas).

        Args:
            text: Texto da descrição

        Returns:
            True se preencheu, False caso contrário
        """
        if not text:
            return True

        # Remove emojis fora do BMP (Chrome não suporta)
        text = ''.join(char if ord(char) <= 0xFFFF else '' for char in text)

        # Seletores mais comuns (ordem de prioridade)
        selectors = [
            "div[data-e2e='caption-editor'] div[contenteditable='true']",
            "div[contenteditable='true'][data-placeholder]",
            "div[contenteditable='true'][role='textbox']",
        ]

        for selector in selectors:
            try:
                field = self._wait_visible(By.CSS_SELECTOR, selector, timeout=10)

                # Método 1: JavaScript (mais rápido)
                try:
                    self.driver.execute_script(
                        """
                        arguments[0].focus();
                        arguments[0].innerText = arguments[1];
                        arguments[0].dispatchEvent(new InputEvent('input', { bubbles: true }));
                        """,
                        field,
                        text,
                    )
                    self.log(f"📝 Descrição preenchida ({len(text)} chars)")
                    time.sleep(1)
                    return True
                except:
                    pass

                # Método 2: send_keys (fallback)
                try:
                    field.clear()
                    field.send_keys(text)
                    self.log(f"📝 Descrição preenchida via send_keys")
                    time.sleep(1)
                    return True
                except:
                    pass

            except TimeoutException:
                continue

        self.log("⚠️ Campo de descrição não encontrado (continuando sem descrição)")
        return True  # Não falha por causa da descrição

    def set_audience_public(self) -> bool:
        """
        Define audiência como pública (SIMPLES).

        Returns:
            True sempre (não trava se não achar)
        """
        try:
            # Verifica se já está em "Everyone"
            try:
                self._wait_element(
                    By.XPATH,
                    "//*[contains(text(), 'Everyone') or contains(text(), 'Para todos')]",
                    timeout=5
                )
                self.log("🔧 Audiência já é pública")
                return True
            except TimeoutException:
                pass

            # Tenta abrir seletor e escolher "Everyone"
            selectors = [
                "//div[@data-e2e='audience-selector']",
                "//div[contains(text(), 'Who can watch')]",
            ]

            for selector in selectors:
                try:
                    opener = self._wait_clickable(By.XPATH, selector, timeout=5)
                    opener.click()
                    time.sleep(1)

                    # Seleciona "Everyone"
                    option = self._wait_clickable(
                        By.XPATH,
                        "//*[contains(text(), 'Everyone') or contains(text(), 'Para todos')]",
                        timeout=5
                    )
                    option.click()
                    self.log("🔧 Audiência definida como pública")
                    return True
                except:
                    continue

            self.log("ℹ️ Não consegui alterar audiência (seguindo sem alteração)")
            return True  # Não falha por causa disso

        except Exception as e:
            self.log(f"⚠️ Erro ao definir audiência: {e} (continuando)")
            return True

    def click_publish(self) -> bool:
        """
        Clica no botão de publicar (SIMPLES).

        Returns:
            True se clicou, False caso contrário
        """
        # Rola até o final da página
        try:
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
        except:
            pass

        # Seletores do botão (ordem de prioridade)
        publish_selectors = [
            "//button[@data-e2e='post_video_button' and not(@disabled)]",
            "//button[@data-e2e='post_button' and not(@disabled)]",
            "//button[contains(normalize-space(.), 'Post') and not(@disabled)]",
            "//button[contains(normalize-space(.), 'Publicar') and not(@disabled)]",
        ]

        for selector in publish_selectors:
            try:
                btn = self._wait_clickable(By.XPATH, selector, timeout=5)

                # Rola até o botão
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'center'});", btn
                )
                time.sleep(0.5)

                # Tenta clicar
                try:
                    btn.click()
                except:
                    self.driver.execute_script("arguments[0].click();", btn)

                self.log("🚀 Botão de publicar clicado")
                time.sleep(3)
                return True

            except TimeoutException:
                continue
            except ElementClickInterceptedException:
                # Tenta JS click se normal falhar
                try:
                    self.driver.execute_script("arguments[0].click();", btn)
                    self.log("🚀 Botão de publicar clicado (via JS)")
                    time.sleep(3)
                    return True
                except:
                    continue

        self.log("❌ Botão de publicar não encontrado")
        return False

    def handle_confirmation_dialog(self) -> bool:
        """
        Lida com modal de confirmação "Continue to post?" (SIMPLES).

        Returns:
            True se lidou ou não apareceu, False se falhou
        """
        try:
            # Espera modal aparecer (ou não)
            WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//button[contains(., 'Post') or contains(., 'Continue')]")
                )
            )

            # Clica no botão de confirmar
            confirm_btn = self._wait_clickable(
                By.XPATH,
                "//button[contains(., 'Post') or contains(., 'Continue') or contains(., 'Publicar')]",
                timeout=5
            )
            confirm_btn.click()
            self.log("✅ Modal de confirmação resolvido")
            time.sleep(2)
            return True

        except TimeoutException:
            # Modal não apareceu (tudo bem)
            return True
        except Exception as e:
            self.log(f"⚠️ Erro no modal de confirmação: {e}")
            return True  # Não falha por causa disso

    def confirm_posted(self) -> bool:
        """
        Confirma se vídeo foi publicado (SIMPLES).

        Returns:
            True se publicou, False caso contrário
        """
        # Aguarda até 60s para confirmação
        deadline = time.time() + 60

        while time.time() < deadline:
            try:
                # Verifica se mudou de URL (sinal de sucesso)
                current_url = self.driver.current_url.lower()
                if "/post" in current_url or "/content" in current_url:
                    self.log("✅ URL mudou - vídeo publicado!")
                    return True

                # Verifica se botão de publicar sumiu
                buttons = self.driver.find_elements(By.XPATH, "//button[@data-e2e='post_video_button']")
                if not any(btn.is_displayed() for btn in buttons if btn):
                    self.log("✅ Botão sumiu - vídeo publicado!")
                    return True

            except:
                pass

            time.sleep(2)

        self.log("⚠️ Timeout aguardando confirmação")
        return False

    def post_video(self, video_path: str, description: str = "") -> bool:
        """
        Publica vídeo completo (SIMPLES - fluxo direto).

        Args:
            video_path: Caminho do vídeo
            description: Descrição do vídeo

        Returns:
            True se publicou, False caso contrário
        """
        self.log(f"📹 Iniciando publicação: {os.path.basename(video_path)}")

        # 1. Vai para página de upload
        if not self.go_to_upload():
            return False

        # 2. Envia arquivo (com 1 retry se falhar)
        if not self.send_file(video_path):
            self.log("🔁 Tentando enviar novamente...")
            time.sleep(3)
            if not self.send_file(video_path):
                self.log("❌ Falha no upload após retry")
                return False

        # 3. Preenche descrição
        if description:
            self.fill_description(description)

        # 4. Define audiência como pública
        self.set_audience_public()

        # 5. Clica em publicar
        if not self.click_publish():
            return False

        # 6. Lida com modal de confirmação
        self.handle_confirmation_dialog()

        # 7. Confirma publicação
        if self.confirm_posted():
            self.log("🎉 Vídeo publicado com sucesso!")
            return True
        else:
            self.log("⚠️ Publicação não confirmada (pode ter sido publicado)")
            return False

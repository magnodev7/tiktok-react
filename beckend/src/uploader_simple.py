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
import re
import time
import unicodedata
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
    NoSuchElementException,
)

# Timeouts RAZOÁVEIS (não extremos)
WAIT_SHORT = 5
WAIT_MED = 15
WAIT_LONG = 30

# URLs do TikTok
STUDIO_URL = "https://www.tiktok.com/tiktokstudio/upload?from=creator_center"
CLASSIC_URL = "https://www.tiktok.com/upload"

FILE_INPUT_SELECTORS = [
    (By.CSS_SELECTOR, "input[type='file']"),
    (By.CSS_SELECTOR, "input[accept*='video']"),
    (By.CSS_SELECTOR, "input[name='file']"),
    (By.CSS_SELECTOR, "[data-e2e='upload-input']"),
    (By.CSS_SELECTOR, "[data-e2e='file-input']"),
    (By.CSS_SELECTOR, "[data-testid='upload-input']"),
    (By.CSS_SELECTOR, "[data-e2e='upload-card'] input[type='file']"),
    (By.CSS_SELECTOR, "[data-e2e='upload-area'] input[type='file']"),
    (By.CSS_SELECTOR, "div[role='button'] input[type='file']"),
    (By.CSS_SELECTOR, "label input[type='file']"),
    (By.XPATH, "//input[@type='file']"),
    (By.XPATH, "//input[contains(@accept, 'video')]"),
    (By.XPATH, "//input[@name='file']"),
]

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
    "minute left",
    "minutes left",
    "second left",
    "seconds left",
    "hour left",
    "hours left",
    "remaining",
    "left to upload",
    "left to finish",
    "left to publish",
    "uploading",
    "upload progress",
    "upload em andamento",
    "enviando",
    "carregando",
    "processing your video",
    "processing video",
    "processing upload",
    "processando video",
    "processando upload",
    "progresso",
    "progress",
)

PROGRESS_PATTERNS = (
    re.compile(r"\b\d{1,3}(?:\.\d+)?\s?%"),
    re.compile(r"\b\d+(?:\.\d+)?\s?(?:kb|mb|gb)\s*/\s*\d+(?:\.\d+)?\s?(?:kb|mb|gb)\b"),
    re.compile(r"\bminutes?\s+(?:left|remaining)\b"),
    re.compile(r"\bseconds?\s+(?:left|remaining)\b"),
    re.compile(r"\bhours?\s+(?:left|remaining)\b"),
)


class TikTokUploader:
    """
    Uploader SIMPLIFICADO para TikTok (versão compatível).
    Mantém interface do sistema antigo mas com código simplificado.
    Faz apenas o essencial: upload → descrição → publicar
    """

    @staticmethod
    def _normalize_text(text: str) -> str:
        normalized = unicodedata.normalize("NFKD", text or "")
        normalized = normalized.encode("ascii", "ignore").decode().lower()
        return " ".join(normalized.split())

    @staticmethod
    def _shorten_text(text: str) -> str:
        single_line = " ".join((text or "").split())
        return single_line if len(single_line) <= 120 else single_line[:117] + "..."

    @staticmethod
    def _is_progress_text(norm_text: str) -> bool:
        if not norm_text:
            return False
        if any(token in norm_text for token in PROGRESS_TOKENS):
            return True
        for pattern in PROGRESS_PATTERNS:
            if pattern.search(norm_text):
                return True
        return False

    def __init__(
        self,
        driver,
        logger=None,
        debug_dir=None,
        cookies_path=None,
        account_name=None,
        reuse_existing_session=True,
        **kwargs  # Ignora outros parâmetros para compatibilidade
    ):
        self.driver = driver
        self.log = logger.info if logger and hasattr(logger, 'info') else (logger if logger else print)
        self.account_name = account_name
        # Ignora debug_dir, cookies_path, reuse_existing_session (compatibilidade)
        self._file_input_context = None

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

    def _scan_status_messages(self):
        """Coleta mensagens de status/progresso exibidas na página."""
        try:
            self.driver.switch_to.default_content()
        except Exception:
            pass

        progress_snippets = []
        success_snippets = []
        seen_norm = set()

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

    def _wait_upload_completion(self, timeout: int = 300) -> bool:
        """Espera upload finalizar observando mensagens de progresso."""
        deadline = time.time() + max(timeout, 30)
        last_progress = ""

        while time.time() < deadline:
            progress_snippets, success_snippets = self._scan_status_messages()

            if progress_snippets:
                summary = "; ".join(progress_snippets[:2])
                if summary != last_progress:
                    self.log(f"⏳ Upload em andamento: {summary}")
                    last_progress = summary
                time.sleep(4)
                continue

            if success_snippets and last_progress:
                self.log(f"ℹ️ Status após upload: {success_snippets[0]}")

            self.log("✅ Upload finalizado (nenhum indicador de progresso)")
            return True

        if last_progress:
            self.log(f"⚠️ Timeout aguardando upload finalizar (último status: {last_progress})")
        else:
            self.log("⚠️ Timeout aguardando upload finalizar")
        return False

    def _switch_to_context(self, frame_index: Optional[int]) -> bool:
        """Seleciona página principal ou iframe para procurar o input de upload."""
        try:
            self.driver.switch_to.default_content()
        except Exception:
            pass

        if frame_index is None:
            return True

        try:
            frames = self.driver.find_elements(By.TAG_NAME, "iframe")
        except Exception:
            return False

        if frame_index < 0 or frame_index >= len(frames):
            return False

        try:
            self.driver.switch_to.frame(frames[frame_index])
            return True
        except Exception:
            try:
                self.driver.switch_to.default_content()
            except Exception:
                pass
            return False

    def _scan_for_file_input(self, timeout: int = WAIT_MED) -> bool:
        """
        Procura input de upload na página principal e iframes.
        Atualiza self._file_input_context quando encontra.
        """
        deadline = time.time() + max(timeout, WAIT_SHORT)

        while time.time() < deadline:
            try:
                self.driver.switch_to.default_content()
            except Exception:
                pass

            try:
                frames = self.driver.find_elements(By.TAG_NAME, "iframe")
                frame_indices = list(range(len(frames)))
            except Exception:
                frame_indices = []

            context_candidates = [None] + frame_indices

            for frame_index in context_candidates:
                if not self._switch_to_context(frame_index):
                    continue

                for by, value in FILE_INPUT_SELECTORS:
                    try:
                        element = self.driver.find_element(by, value)
                    except NoSuchElementException:
                        continue
                    except Exception:
                        continue

                    if element:
                        label = "principal" if frame_index is None else f"iframe[{frame_index}]"
                        self._file_input_context = {
                            "frame_index": frame_index,
                            "by": by,
                            "value": value,
                        }
                        self.log(f"✅ Campo de upload localizado ({label}) com seletor: {value}")
                        try:
                            self.driver.switch_to.default_content()
                        except Exception:
                            pass
                        return True

                try:
                    self.driver.switch_to.default_content()
                except Exception:
                    pass

            time.sleep(1)

        try:
            self.driver.switch_to.default_content()
        except Exception:
            pass

        self._file_input_context = None
        return False

    def _resolve_file_input(self, timeout: int = WAIT_MED):
        """
        Retorna elemento do input de upload. Mantém o driver no contexto correto;
        caller deve voltar ao default_content após utilizar.
        """
        attempts = 2
        for _ in range(attempts):
            if not self._file_input_context:
                if not self._scan_for_file_input(timeout=timeout):
                    time.sleep(1)
                    continue

            context = self._file_input_context or {}
            frame_index = context.get("frame_index")
            by = context.get("by")
            value = context.get("value")

            if by is None or value is None:
                self._file_input_context = None
                continue

            if not self._switch_to_context(frame_index):
                self._file_input_context = None
                time.sleep(1)
                continue

            try:
                element = WebDriverWait(self.driver, WAIT_SHORT).until(
                    EC.presence_of_element_located((by, value))
                )
                return element
            except TimeoutException:
                self._file_input_context = None
                try:
                    self.driver.switch_to.default_content()
                except Exception:
                    pass
                time.sleep(1)
                continue
            except Exception:
                self._file_input_context = None
                try:
                    self.driver.switch_to.default_content()
                except Exception:
                    pass
                time.sleep(1)
                continue

        try:
            self.driver.switch_to.default_content()
        except Exception:
            pass

        return None

    def go_to_upload(self) -> bool:
        """
        Navega para página de upload (SIMPLES).

        Returns:
            True se conseguiu, False caso contrário
        """
        self._file_input_context = None
        urls = [STUDIO_URL, CLASSIC_URL]

        for url in urls:
            try:
                self.log(f"🌐 Acessando: {url}")
                self.driver.set_page_load_timeout(30)
                self.driver.get(url)
                time.sleep(5)

                # Verifica se não foi redirecionado para login
                if "login" in self.driver.current_url.lower():
                    self.log("⚠️ Redirecionado para login")
                    continue

                if self._scan_for_file_input(timeout=WAIT_MED):
                    return True

                # DEBUG: Salva screenshot e título para investigação
                try:
                    screenshot_path = f"/tmp/tiktok_upload_page_{int(time.time())}.png"
                    self.driver.save_screenshot(screenshot_path)
                    self.log(f"📸 Screenshot salvo: {screenshot_path}")

                    page_title = self.driver.title
                    self.log(f"📄 Título da página: {page_title}")
                except Exception as e:
                    self.log(f"⚠️ Erro ao salvar debug: {e}")

                self.log("⚠️ Input de arquivo não encontrado com nenhum seletor")
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

        abs_path = os.path.abspath(video_path)
        sent = False

        for attempt in range(2):
            upload_input = self._resolve_file_input(timeout=WAIT_MED)
            if not upload_input:
                if attempt == 0:
                    self.log("⚠️ Input de upload não encontrado; tentando novamente...")
                    time.sleep(2)
                    continue
                self.log("❌ Input de arquivo não encontrado")
                return False

            try:
                try:
                    self.driver.execute_script(
                        "arguments[0].style.display = 'block'; arguments[0].removeAttribute('hidden');",
                        upload_input,
                    )
                except Exception:
                    pass

                try:
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", upload_input)
                except Exception:
                    pass

                upload_input.send_keys(abs_path)
                self.log(f"⬆️ Arquivo enviado: {abs_path}")
                sent = True
                break
            except Exception as e:
                self.log(f"⚠️ Falha ao enviar arquivo (tentativa {attempt + 1}): {e}")
                self._file_input_context = None
                time.sleep(2)
            finally:
                try:
                    self.driver.switch_to.default_content()
                except Exception:
                    pass

        if not sent:
            self.log("❌ Falha ao enviar arquivo de vídeo")
            return False

        # Aguarda processamento (procura preview ou vídeo)
        try:
            WebDriverWait(self.driver, WAIT_LONG).until(
                EC.any_of(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "video")),
                    EC.presence_of_element_located((By.CSS_SELECTOR, "canvas")),
                    EC.presence_of_element_located((By.CSS_SELECTOR, "[class*='preview']")),
                )
            )
            self.log("🎬 Vídeo processado (preview disponível)")
        except TimeoutException:
            self.log("⚠️ Timeout aguardando processamento inicial")
            return False

        time.sleep(3)

        if not self._wait_upload_completion(timeout=240):
            return False

        return True

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
        deadline = time.time() + 60
        last_progress = ""

        while time.time() < deadline:
            try:
                try:
                    current_url = (self.driver.current_url or "").lower()
                except Exception:
                    current_url = ""

                if current_url and "upload" not in current_url:
                    if any(fragment in current_url for fragment in SUCCESS_URL_FRAGMENTS):
                        self.log("✅ URL mudou - vídeo publicado!")
                        return True

                try:
                    self.driver.switch_to.default_content()
                except Exception:
                    pass

                buttons = self.driver.find_elements(By.XPATH, "//button[@data-e2e='post_video_button']")
                if not any(btn.is_displayed() for btn in buttons if btn):
                    self.log("✅ Botão sumiu - vídeo publicado!")
                    return True

                progress_snippets, success_snippets = self._scan_status_messages()

                if progress_snippets:
                    summary = "; ".join(progress_snippets[:2])
                    if summary != last_progress:
                        self.log(f"⏳ Aguardando confirmação: {summary}")
                        last_progress = summary
                    time.sleep(3)
                    continue

                if success_snippets:
                    self.log(f"✅ Confirmação exibida: {success_snippets[0]}")
                    return True

            except Exception:
                pass

            time.sleep(2)

        if last_progress:
            self.log(f"⚠️ Timeout aguardando confirmação (último status: {last_progress})")
        else:
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

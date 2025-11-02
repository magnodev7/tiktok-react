"""
Módulo 1: Upload e Validação do Vídeo
Responsável por enviar o vídeo e validar formato, tamanho e integridade
"""
import os
import time
import re
import unicodedata
from typing import Optional, Callable

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    StaleElementReferenceException,
)

# Constantes
WAIT_SHORT = 5
WAIT_MED = 15
WAIT_LONG = 30

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

SUCCESS_KEYWORDS = (
    "video posted successfully", "video has been posted",
    "video uploaded successfully", "video has been uploaded",
    "video is under review", "post submitted", "post successful",
    "postagem enviada", "postagem publicada", "postagem concluida",
    "publicacao enviada", "publicacao publicada", "publicado com sucesso",
    "enviado com sucesso", "upload concluido", "upload finalizado",
    "upload bem sucedido", "upload bem-sucedido", "upload successful",
    "uploaded successfully", "vamos avisar quando estiver pronto",
    "we will notify you when it's done", "we'll notify you when it's done",
    "successfully submitted", "successfully published",
)


class VideoUploadModule:
    """
    Módulo responsável pelo upload e validação de vídeos no TikTok.
    Gerencia toda a lógica de navegação, localização do campo de upload,
    envio do arquivo e validação do processamento.
    """

    def __init__(self, driver, logger: Optional[Callable] = None):
        """
        Inicializa o módulo de upload.

        Args:
            driver: WebDriver do Selenium
            logger: Função de logging (opcional, usa print por padrão)
        """
        self.driver = driver
        self.log = logger if logger else print
        self._file_input_context = None

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
        """Verifica se texto indica progresso de upload"""
        if not norm_text:
            return False
        if any(token in norm_text for token in PROGRESS_TOKENS):
            return True
        for pattern in PROGRESS_PATTERNS:
            if pattern.search(norm_text):
                return True
        return False

    def _wait_element(self, by, value, timeout=WAIT_MED):
        """Espera elemento aparecer"""
        return WebDriverWait(self.driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )

    # ===================== VALIDAÇÃO DE ARQUIVO =====================

    def validate_video_file(self, video_path: str) -> bool:
        """
        Valida se o arquivo de vídeo existe e atende aos requisitos.

        Args:
            video_path: Caminho do arquivo de vídeo

        Returns:
            True se válido, False caso contrário
        """
        # Verifica existência
        if not os.path.isfile(video_path):
            self.log(f"❌ Arquivo não encontrado: {video_path}")
            return False

        # Verifica tamanho mínimo (200KB)
        size_bytes = os.path.getsize(video_path)
        if size_bytes < 200 * 1024:
            self.log(f"❌ Vídeo muito pequeno: {size_bytes} bytes (mínimo: 200KB)")
            return False

        # Verifica extensão
        _, ext = os.path.splitext(video_path)
        valid_extensions = ['.mp4', '.mov', '.avi', '.webm', '.mkv', '.flv']
        if ext.lower() not in valid_extensions:
            self.log(f"⚠️ Extensão incomum: {ext} (pode não ser aceita)")

        self.log(f"✅ Arquivo validado: {os.path.basename(video_path)} ({size_bytes / (1024*1024):.2f} MB)")
        return True

    # ===================== NAVEGAÇÃO E LOCALIZAÇÃO =====================

    def _switch_to_context(self, frame_index: Optional[int]) -> bool:
        """Seleciona página principal ou iframe"""
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
        Retorna elemento do input de upload.
        Mantém o driver no contexto correto.
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

    def navigate_to_upload_page(self) -> bool:
        """
        Navega para a página de upload do TikTok.

        Returns:
            True se conseguiu navegar e encontrou campo de upload, False caso contrário
        """
        self._file_input_context = None
        urls = [STUDIO_URL, CLASSIC_URL]

        for url in urls:
            try:
                self.log(f"🌐 Acessando: {url}")
                self.driver.set_page_load_timeout(30)
                self.driver.get(url)
                time.sleep(5)

                current_url = self.driver.current_url
                self.log(f"🔍 URL atual: {current_url}")

                # Verifica se não foi redirecionado para login
                if "login" in current_url.lower():
                    self.log("⚠️ Redirecionado para login")
                    continue

                if self._scan_for_file_input(timeout=WAIT_MED):
                    return True

                # DEBUG: Salva screenshot se não encontrou
                try:
                    screenshot_path = f"/tmp/tiktok_upload_page_{int(time.time())}.png"
                    self.driver.save_screenshot(screenshot_path)
                    self.log(f"📸 Screenshot salvo: {screenshot_path}")
                    page_title = self.driver.title
                    self.log(f"📄 Título da página: {page_title}")
                except:
                    pass

                self.log("⚠️ Input de arquivo não encontrado")
                continue

            except Exception as e:
                self.log(f"⚠️ Erro ao carregar {url}: {e}")
                continue

        self.log("❌ Não consegui abrir página de upload")
        return False

    # ===================== UPLOAD E MONITORAMENTO =====================

    def _scan_status_messages(self):
        """Coleta mensagens de status/progresso exibidas na página"""
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

    def wait_upload_completion(self, timeout: int = 300) -> bool:
        """
        Espera o upload ser processado pelo TikTok.

        Args:
            timeout: Tempo máximo de espera em segundos

        Returns:
            True se upload finalizou, False se timeout
        """
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

            self.log("✅ Upload finalizado")
            return True

        if last_progress:
            self.log(f"⚠️ Timeout aguardando upload (último status: {last_progress})")
        else:
            self.log("⚠️ Timeout aguardando upload finalizar")
        return False

    def send_video_file(self, video_path: str, retry: bool = True) -> bool:
        """
        Envia o arquivo de vídeo para o TikTok.

        Args:
            video_path: Caminho absoluto ou relativo do vídeo
            retry: Se True, tenta novamente em caso de falha

        Returns:
            True se enviou com sucesso, False caso contrário
        """
        # Valida arquivo antes de enviar
        if not self.validate_video_file(video_path):
            return False

        abs_path = os.path.abspath(video_path)
        attempts = 2 if retry else 1
        sent = False

        for attempt in range(attempts):
            upload_input = self._resolve_file_input(timeout=WAIT_MED)
            if not upload_input:
                if attempt == 0:
                    self.log("⚠️ Input de upload não encontrado; tentando novamente...")
                    time.sleep(2)
                    continue
                self.log("❌ Input de arquivo não encontrado")
                return False

            try:
                # Torna input visível (pode estar oculto)
                try:
                    self.driver.execute_script(
                        "arguments[0].style.display = 'block'; arguments[0].removeAttribute('hidden');",
                        upload_input,
                    )
                except Exception:
                    pass

                # Rola até o input
                try:
                    self.driver.execute_script(
                        "arguments[0].scrollIntoView({block: 'center'});",
                        upload_input
                    )
                except Exception:
                    pass

                # Envia arquivo
                upload_input.send_keys(abs_path)
                self.log(f"⬆️ Arquivo enviado: {os.path.basename(abs_path)}")
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

        # Aguarda processamento inicial (preview aparecer)
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

        # Aguarda upload completar
        if not self.wait_upload_completion(timeout=240):
            return False

        return True

    # ===================== MÉTODO PÚBLICO PRINCIPAL =====================

    def upload_video(self, video_path: str) -> bool:
        """
        Método principal: realiza todo o fluxo de upload.
        1. Valida arquivo
        2. Navega para página de upload
        3. Envia arquivo
        4. Aguarda processamento

        Args:
            video_path: Caminho do arquivo de vídeo

        Returns:
            True se todo o fluxo foi bem-sucedido, False caso contrário
        """
        self.log(f"📹 Iniciando upload: {os.path.basename(video_path)}")

        # Navega para página de upload
        if not self.navigate_to_upload_page():
            return False

        # Envia arquivo com retry automático
        if not self.send_video_file(video_path, retry=True):
            return False

        self.log("✅ Upload concluído com sucesso")
        return True

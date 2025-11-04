"""
Módulo 1: Upload e Validação do Vídeo (Versão Otimizada v2.4 - Fix Partial Match & UI Check)
Responsável por enviar o vídeo e validar formato, tamanho e integridade
Fixes: Partial match keywords, stall para 90%+, EC para UI pós-upload ("description", "hashtags").
"""
import os
import time
import re
import unicodedata
import subprocess
from typing import Optional, Callable, Tuple, Set
from contextlib import contextmanager

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

STATUS_TEXT_SELECTORS = [
    (By.XPATH, "//*[@role='status' or @role='alert' or @aria-live]"),
    (By.XPATH, "//*[contains(@data-e2e, 'result')]"),
    (By.XPATH, "//*[contains(@data-e2e, 'success')]"),
    (By.XPATH, "//*[contains(@data-e2e, 'status')]"),
    (By.XPATH, "//*[contains(@data-e2e, 'progress')]"),
    (By.XPATH, "//*[contains(@data-testid, 'toast')]"),
    (By.XPATH, "//*[contains(@class, 'result')]"),
    (By.XPATH, "//*[contains(@class, 'success')]"),
    (By.XPATH, "//*[contains(@class, 'progress')]"),
]

# Novo: Seletores para UI pós-upload (do screenshot)
POST_UPLOAD_SELECTORS = [
    (By.CSS_SELECTOR, "[data-e2e='description-input']"),
    (By.CSS_SELECTOR, "[data-e2e='hashtag-input']"),
    (By.CSS_SELECTOR, "[class*='description']"),
    (By.CSS_SELECTOR, "[class*='hashtags']"),
    (By.CSS_SELECTOR, "[class*='edit-cover']"),
]

PROGRESS_TOKENS: Set[str] = {
    "minute left", "minutes left", "second left", "seconds left",
    "hour left", "hours left", "remaining", "left to upload",
    "left to finish", "left to publish", "uploading", "upload progress",
    "upload em andamento", "enviando", "carregando",
    "processing your video", "processing video", "processing upload",
    "processando video", "processando upload", "progresso", "progress",
}

SUCCESS_KEYWORDS: Set[str] = {
    # Expandidos com partials do screenshot/logs
    "uploaded", "upload finalizado", "upload concluido", "upload bem sucedido",
    "video uploaded successfully", "video has been uploaded", "video is under review",
    "post submitted", "post successful", "postagem enviada", "postagem publicada",
    "publicacao enviada", "publicacao publicada", "publicado com sucesso",
    "enviado com sucesso", "upload successful", "uploaded successfully",
    "vamos avisar quando estiver pronto", "we will notify you when it's done",
    "successfully submitted", "successfully published", "checking in progress",
    "replace", "details", "description", "hashtags", "mention", "cover edit",
}

PROGRESS_PATTERNS = (
    re.compile(r"\b\d{1,3}(?:\.\d+)?\s?%"),
    re.compile(r"\b\d+(?:\.\d+)?\s?(?:kb|mb|gb)\s*/\s*\d+(?:\.\d+)?\s?(?:kb|mb|gb)\b"),
    re.compile(r"\bminutes?\s+(?:left|remaining)\b"),
    re.compile(r"\bseconds?\s+(?:left|remaining)\b"),
    re.compile(r"\bhours?\s+(?:left|remaining)\b"),
)


class VideoUploadModule:
    """
    Módulo responsável pelo upload e validação de vídeos no TikTok.
    Gerencia toda a lógica de navegação, localização do campo de upload,
    envio do arquivo e validação do processamento.
    """

    def __init__(self, driver, logger: Optional[Callable[[str], None]] = None):
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
        """Verifica se texto indica progresso de upload (otimizado com set)"""
        if not norm_text:
            return False
        if PROGRESS_TOKENS & set(norm_text.split()):  # O(1) interseção
            return True
        for pattern in PROGRESS_PATTERNS:
            if pattern.search(norm_text):
                return True
        return False

    @staticmethod
    def _has_success_partial(norm_text: str, keywords: Set[str]) -> bool:
        """Partial match para keywords (não só split)"""
        return any(kw in norm_text for kw in keywords)

    def _wait_element(self, by, value, timeout=WAIT_MED):
        """Espera elemento aparecer"""
        return WebDriverWait(self.driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )

    @contextmanager
    def _frame_context(self, frame_index: Optional[int]):
        """Context manager para switch de frames, auto-reseta para default."""
        try:
            if frame_index is not None:
                frames = self.driver.find_elements(By.TAG_NAME, "iframe")
                if 0 <= frame_index < len(frames):
                    self.driver.switch_to.frame(frames[frame_index])
            yield
        except Exception as e:
            self.log(f"⚠️ Erro no frame {frame_index}: {e}")
        finally:
            try:
                self.driver.switch_to.default_content()
            except Exception:
                pass

    # ===================== VALIDAÇÃO DE ARQUIVO =====================

    def validate_video_file(self, video_path: str) -> Tuple[bool, str]:
        """
        Valida se o arquivo de vídeo existe e atende aos requisitos (avançada com duração opcional).

        Args:
            video_path: Caminho do arquivo de vídeo

        Returns:
            Tuple[bool, str]: (válido, mensagem de erro/sucesso)
        """
        # Verifica existência
        if not os.path.isfile(video_path):
            return False, f"Arquivo não encontrado: {video_path}"

        # Verifica tamanho mínimo (200KB)
        size_bytes = os.path.getsize(video_path)
        if size_bytes < 200 * 1024:
            return False, f"Vídeo muito pequeno: {size_bytes} bytes (mínimo: 200KB)"

        # Verifica extensão
        _, ext = os.path.splitext(video_path)
        valid_extensions = {'.mp4', '.mov', '.avi', '.webm', '.mkv', '.flv'}
        if ext.lower() not in valid_extensions:
            return False, f"Extensão inválida: {ext} (aceitas: {', '.join(valid_extensions)})"

        # Check duração (opcional, via ffprobe se disponível)
        duration_msg = ""
        try:
            result = subprocess.run(
                ['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration', '-of', 'csv=p=0', video_path],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                duration = float(result.stdout.strip())
                if duration > 600:  # 10min
                    return False, f"Duração excessiva: {duration/60:.1f}min (máx 10min)"
                duration_msg = f" (duração: {duration/60:.1f}min)"
        except (subprocess.TimeoutExpired, FileNotFoundError, ValueError):
            # Não quebra; log só
            pass

        msg = f"✅ Arquivo validado: {os.path.basename(video_path)} ({size_bytes / (1024*1024):.2f} MB{duration_msg})"
        self.log(msg)
        return True, msg

    # ===================== NAVEGAÇÃO E LOCALIZAÇÃO =====================

    def _scan_for_file_input(self, timeout: int = WAIT_MED) -> bool:
        """
        Procura input de upload na página principal e iframes (otimizado: limite frames, sleeps menores).
        Atualiza self._file_input_context quando encontra.
        """
        deadline = time.time() + max(timeout, WAIT_SHORT)
        frame_indices = [None]  # Priorize main primeiro
        try:
            frames = self.driver.find_elements(By.TAG_NAME, "iframe")
            frame_indices.extend(range(min(2, len(frames))))  # Limite a 2 frames para eficiência
        except Exception:
            pass

        while time.time() < deadline:
            for frame_index in frame_indices:
                with self._frame_context(frame_index):
                    for by, value in FILE_INPUT_SELECTORS:
                        try:
                            element = self.driver.find_element(by, value)
                            if element:
                                label = "principal" if frame_index is None else f"iframe[{frame_index}]"
                                self._file_input_context = {
                                    "frame_index": frame_index,
                                    "by": by,
                                    "value": value,
                                }
                                self.log(f"✅ Campo de upload localizado ({label}) com seletor: {value}")
                                return True
                        except NoSuchElementException:
                            continue
                        except (StaleElementReferenceException, TimeoutException):
                            continue  # Específicos para flakiness

                time.sleep(0.5)  # Reduzido de 1s para eficiência
            time.sleep(1)  # Outer sleep menor

        self._file_input_context = None
        return False

    def _resolve_file_input(self, timeout: int = WAIT_MED):
        """
        Retorna elemento do input de upload (usa context manager).
        Mantém o driver no contexto correto.
        """
        attempts = 2
        for _ in range(attempts):
            if not self._file_input_context:
                if not self._scan_for_file_input(timeout=timeout):
                    time.sleep(1)
                    continue

            context = self._file_input_context
            frame_index = context.get("frame_index")
            by = context.get("by")
            value = context.get("value")

            if by is None or value is None:
                self._file_input_context = None
                continue

            with self._frame_context(frame_index):
                try:
                    element = WebDriverWait(self.driver, WAIT_SHORT).until(
                        EC.presence_of_element_located((by, value))
                    )
                    return element
                except (TimeoutException, NoSuchElementException):
                    self._file_input_context = None
                    time.sleep(1)
                    continue

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
                time.sleep(3)  # Reduzido de 5s para eficiência

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
                except Exception:
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
        """Coleta mensagens de status/progresso exibidas na página (usa context manager)"""
        with self._frame_context(None):  # Default content
            progress_snippets = []
            success_snippets = []
            seen_norm = set()

            for by, value in STATUS_TEXT_SELECTORS:  # Já como tuples
                try:
                    elements = self.driver.find_elements(by, value)
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
                    elif self._has_success_partial(norm_text, SUCCESS_KEYWORDS):  # Partial match
                        success_snippets.append(snippet)

            # Verifica body também (fallback crítico)
            try:
                body_text = self.driver.find_element(By.TAG_NAME, "body").text
                if body_text:
                    norm_body = self._normalize_text(body_text)
                    if norm_body and norm_body not in seen_norm:
                        snippet = self._shorten_text(body_text)
                        if self._is_progress_text(norm_body):
                            progress_snippets.append(snippet)
                        elif self._has_success_partial(norm_body, SUCCESS_KEYWORDS):
                            success_snippets.append(snippet)
            except Exception:
                pass

            return progress_snippets, success_snippets

    def wait_upload_completion(self, timeout: int = 300) -> bool:
        """
        Espera o upload ser processado pelo TikTok (fallback prioritário + stall 90%+).

        Args:
            timeout: Tempo máximo de espera em segundos

        Returns:
            True se upload finalizado, False se timeout
        """
        deadline = time.time() + max(timeout, 30)
        last_progress = ""
        last_progress_time = time.time()
        stall_threshold = 20  # Segundos sem mudança em 90%+ = sucesso

        while time.time() < deadline:
            progress_snippets, success_snippets = self._scan_status_messages()  # Prioritário: texto sempre

            if success_snippets:
                self.log(f"ℹ️ Status após upload: {success_snippets[0]}")
                self.log("✅ Upload finalizado")
                return True

            if progress_snippets:
                summary = "; ".join(progress_snippets[:2])
                current_time = time.time()
                # Check stall para 90%+
                if re.search(r"\b9\d{1,2}%", summary):  # >=90%
                    if summary != last_progress:
                        self.log(f"⏳ Upload em andamento: {summary}")
                        last_progress = summary
                        last_progress_time = current_time
                    elif current_time - last_progress_time > stall_threshold:
                        self.log(f"✅ Upload estagnado >{stall_threshold}s em 90%+ (assumindo sucesso: {summary})")
                        return True
                else:
                    if summary != last_progress:
                        self.log(f"⏳ Upload em andamento: {summary}")
                        last_progress = summary
                        last_progress_time = current_time
                continue

            # UI Check: Elementos pós-upload (ex.: description field)
            try:
                wait = WebDriverWait(self.driver, 5)
                post_ui_ec = [EC.presence_of_element_located(sel) for sel in POST_UPLOAD_SELECTORS]
                post_elem = wait.until(EC.any_of(*post_ui_ec))
                self.log(f"✅ UI pós-upload detectada: {post_elem.tag_name} (pronto para edição)")
                return True
            except TimeoutException:
                pass

            time.sleep(2)  # Sleep reduzido

        # Scan final melhorado
        self.log("⚠️ Timeout atingido; scan final para confirmação...")
        _, success_snippets = self._scan_status_messages()
        if success_snippets or self._has_success_partial(self.driver.find_element(By.TAG_NAME, "body").text, SUCCESS_KEYWORDS):
            self.log(f"✅ Upload detectado no scan final")
            return True

        if last_progress:
            self.log(f"⚠️ Timeout aguardando upload (último status: {last_progress})")
        else:
            self.log("⚠️ Timeout aguardando upload finalizar (nenhum progresso detectado)")
        return False

    def send_video_file(self, video_path: str, retry: bool = True) -> bool:
        """
        Envia o arquivo de vídeo para o TikTok (com backoff simples).

        Args:
            video_path: Caminho absoluto ou relativo do vídeo
            retry: Se True, tenta novamente em caso de falha

        Returns:
            True se enviou com sucesso, False caso contrário
        """
        # Valida arquivo antes de enviar (agora com tuple)
        valid, msg = self.validate_video_file(video_path)
        if not valid:
            self.log(f"❌ {msg}")
            return False

        abs_path = os.path.abspath(video_path)
        attempts = 2 if retry else 1
        backoff = [2, 4]  # Sleeps crescentes

        for attempt in range(attempts):
            upload_input = self._resolve_file_input(timeout=WAIT_MED)
            if not upload_input:
                if attempt < attempts - 1:
                    self.log(f"⚠️ Input não encontrado; retry em {backoff[attempt]}s...")
                    time.sleep(backoff[attempt])
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
                break

            except Exception as e:
                self.log(f"⚠️ Falha ao enviar arquivo (tentativa {attempt + 1}): {e}")
                self._file_input_context = None
                if attempt < attempts - 1:
                    time.sleep(backoff[attempt])
            finally:
                with self._frame_context(None):  # Reset via context
                    pass

        else:  # No break: falhou todas tentativas
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

        time.sleep(2)  # Reduzido de 3s

        # Aguarda upload completar (agora com UI check)
        if not self.wait_upload_completion(timeout=300):
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
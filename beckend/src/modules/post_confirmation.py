# -*- coding: utf-8 -*-
"""
Módulo 5: Confirmação de Postagem (v4.1)
- Evita falsos positivos: 'Checking in progress...' NÃO é sucesso.
- Sinais fortes para PUBLISHED: URL de vídeo, sumiço do botão de postar, hard success text.
- Poll 1s, probing antecipado em 70% e FORÇADO após 60s.
- Early-exit estrito: fora de upload + botão de postar ausente.
- API compatível: wait_for_confirmation(timeout)->bool e confirm_posted()->ConfirmationResult.
"""

import time
import re
import unicodedata
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Callable, Tuple, List, Dict

from selenium.webdriver.common.by import By
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait

# ===================== Configs =====================

CONFIRMATION_TIMEOUT = 90
POLL_INTERVAL = 1.0
PROBING_THRESHOLD = 0.7
PROBING_MAX_WAIT = 12
EARLY_EXIT_THRESHOLD = 50
FORCE_PROBE_AFTER = 60  # <- NOVO: força probing após 60s

SUCCESS_URL_FRAGMENTS = (
    "/post",
    "/content",
    "/creatorpost",
    "/content/manage",
    "/post/success",
    "/upload/success",
    "/analytics",
    "/creator_center?tab=posted",
    "/tiktokstudio/analytics",
    "/video/",
    "published",
    "success",
)

HARD_SUCCESS_KEYWORDS = (
    "video posted successfully",
    "video has been posted",
    "video uploaded successfully",
    "video has been uploaded",
    "post successful",
    "successfully submitted",
    "successfully published",
    "your video is now live",
    "published!",
    "video published",
    "vídeo publicado",
    "publicado com sucesso",
    "upload concluido",
    "upload finalizado",
    "upload bem sucedido",
    "upload bem-sucedido",
    "ready to view",
    "congratulations",
    "done!",
)

SUBMITTED_KEYWORDS = (
    "post submitted",
    "postagem enviada",
    "publicacao enviada",
    "we will notify you when it's done",
    "we'll notify you when it's done",
    "vamos avisar quando estiver pronto",
    "checking in progress",
    "verificação em andamento",
    "checando em andamento",
    "video is under review",
    "processing your video",
    "processando video",
)

PROGRESS_TOKENS = (
    "minute left", "minutes left", "second left", "seconds left",
    "hour left", "hours left", "remaining", "left to upload",
    "left to finish", "left to publish", "uploading", "upload progress",
    "upload em andamento", "enviando", "carregando",
    "processing video", "processing upload",
    "processando upload", "progresso", "progress",
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
    "//div[contains(@class, 'notification') or contains(@class, 'toast')]",
    "//*[contains(text(), 'success') or contains(text(), 'posted')]",
    "//div[@role='dialog']//*[@data-e2e='success-message']",
)

LOADING_SELECTORS = (
    ".upload-progress",
    ".processing-spinner",
    "[data-e2e='upload-progress']",
    "[class*='loading']",
    "[class*='spinner']",
)

# ===================== Estados & Resultado =====================

class ConfirmationStatus(Enum):
    UNKNOWN = "unknown"
    SUBMITTED = "submitted"
    PUBLISHED = "published"

@dataclass
class ConfirmationSignals:
    url_changed: bool = False
    left_upload: bool = False
    video_url_detected: bool = False
    publish_button_disappeared: bool = False
    hard_success_text: Optional[str] = None
    submitted_text: Optional[str] = None
    progress_snippets: List[str] = field(default_factory=list)
    success_snippets: List[str] = field(default_factory=list)
    current_url: str = ""
    progress_percentage: float = 0.0

@dataclass
class ConfirmationResult:
    status: ConfirmationStatus
    signals: ConfirmationSignals
    reason: str

    def is_published(self) -> bool:
        return self.status == ConfirmationStatus.PUBLISHED

    def is_submitted(self) -> bool:
        return self.status == ConfirmationStatus.SUBMITTED

# ===================== Módulo =====================

class PostConfirmationModule:
    def __init__(self, driver, logger: Optional[Callable] = None):
        self.driver = driver
        self.log = logger if logger else print
        self._cached_signals: Optional[ConfirmationSignals] = None
        self._expected_title: Optional[str] = None
        self._username: Optional[str] = None

    # Contexto (opcional)
    def set_context(self, expected_title: Optional[str] = None, username: Optional[str] = None):
        self._expected_title = expected_title
        self._username = username

    # Utils
    @staticmethod
    def _normalize_text(content: str) -> str:
        normalized = unicodedata.normalize("NFKD", content or "")
        normalized = normalized.encode("ascii", "ignore").decode().lower()
        return " ".join(normalized.split())

    @staticmethod
    def _shorten_text(text: str) -> str:
        single_line = " ".join((text or "").split())
        return single_line if len(single_line) <= 120 else single_line[:117] + "..."

    @staticmethod
    def _is_progress_text(norm_text: str) -> Tuple[bool, float]:
        if not norm_text:
            return False, 0.0
        if any(token in norm_text for token in PROGRESS_TOKENS):
            return True, 0.0
        for pattern in PROGRESS_PATTERNS:
            match = pattern.search(norm_text)
            if match:
                if '%' in match.group():
                    try:
                        pct_match = re.search(r'(\d+(?:\.\d+)?)%', match.group())
                        pct = float(pct_match.group(1)) if pct_match else 0.0
                        return True, pct
                    except ValueError:
                        return True, 0.0
                return True, 0.0
        return False, 0.0

    def _now_url(self) -> str:
        try:
            return (self.driver.current_url or "").lower()
        except Exception:
            return ""

    # Coleta
    def _scan_status_messages(self, refresh: bool = False) -> Tuple[List[str], List[str], Optional[str], Optional[str], float]:
        if not refresh and self._cached_signals:
            return (
                self._cached_signals.progress_snippets,
                self._cached_signals.success_snippets,
                self._cached_signals.hard_success_text,
                self._cached_signals.submitted_text,
                self._cached_signals.progress_percentage,
            )

        try:
            self.driver.switch_to.default_content()
        except Exception:
            pass

        progress_snippets: List[str] = []
        success_snippets: List[str] = []
        hard_success_text: Optional[str] = None
        submitted_text: Optional[str] = None
        progress_pct_sum = 0.0
        pct_count = 0

        try:
            WebDriverWait(self.driver, 1).until(lambda d: len(d.find_elements(By.XPATH, "//body")) > 0)
        except TimeoutException:
            pass

        def _classify_text(raw: str):
            nonlocal hard_success_text, submitted_text, progress_pct_sum, pct_count
            text = (raw or "").strip()
            if not text:
                return
            norm = self._normalize_text(text)
            if not norm:
                return
            snippet = self._shorten_text(text)

            if any(k in norm for k in HARD_SUCCESS_KEYWORDS):
                success_snippets.append(snippet)
                if hard_success_text is None:
                    hard_success_text = snippet
            elif any(k in norm for k in SUBMITTED_KEYWORDS):
                success_snippets.append(snippet)
                if submitted_text is None:
                    submitted_text = snippet
            else:
                is_progress, pct = self._is_progress_text(norm)
                if is_progress:
                    progress_snippets.append(snippet)
                    if pct > 0:
                        progress_pct_sum += pct
                        pct_count += 1

        for selector in STATUS_TEXT_SELECTORS:
            try:
                for el in self.driver.find_elements(By.XPATH, selector):
                    try:
                        _classify_text(el.text)
                    except StaleElementReferenceException:
                        continue
                    except Exception:
                        continue
            except Exception:
                continue

        try:
            body_text = self.driver.find_element(By.TAG_NAME, "body").text
            _classify_text(body_text)
        except Exception:
            pass

        avg_pct = (progress_pct_sum / pct_count) if pct_count > 0 else 0.0

        if not refresh:
            self._cached_signals = ConfirmationSignals(
                progress_snippets=progress_snippets,
                success_snippets=success_snippets,
                hard_success_text=hard_success_text,
                submitted_text=submitted_text,
                progress_percentage=avg_pct,
            )

        return progress_snippets, success_snippets, hard_success_text, submitted_text, avg_pct

    # Checks
    def check_url_changed(self) -> Tuple[bool, bool, bool]:
        url = self._now_url()
        left_upload = "upload" not in url
        video_url_detected = "/video/" in url or "tiktok.com/v/" in url
        url_changed = left_upload or any(f in url for f in SUCCESS_URL_FRAGMENTS)
        if left_upload:
            self.log(f"✅ Saiu da página de upload: {url}")
        if video_url_detected:
            self.log(f"✅ URL de vídeo detectada: {url}")
        return url_changed, left_upload, video_url_detected

    def check_publish_button_disappeared(self) -> bool:
        try:
            self.driver.switch_to.default_content()
        except Exception:
            pass
        try:
            buttons = self.driver.find_elements(By.XPATH, "//button[@data-e2e='post_video_button']")
            if not any(btn.is_displayed() for btn in buttons if btn):
                self.log("✅ Botão 'Publicar' ausente")
                return True
        except Exception:
            pass
        return False

    def wait_for_loading_to_finish(self, timeout: int = 10) -> bool:
        try:
            WebDriverWait(self.driver, timeout).until_not(
                lambda d: any(d.find_elements(By.CSS_SELECTOR, sel) for sel in LOADING_SELECTORS)
            )
            self.log("✅ Loading sumiu")
            return True
        except TimeoutException:
            self.log("⚠️ Timeout aguardando loading")
            return False

    # Probing
    def _probe_creator_center_posted(self, max_wait: int = PROBING_MAX_WAIT) -> bool:
        """Abre o Creator Center (tab=posted) e tenta detectar cards e navegar para um /video/."""
        try:
            target = "https://www.tiktok.com/tiktokstudio?tab=posted"
            self.log("🔎 Probing Creator Center (tab=posted)...")
            self.driver.get(target)

            end = time.time() + max_wait
            found_any = False
            while time.time() < end:
                try:
                    links = self.driver.find_elements(By.XPATH, "//a[contains(@href, '/video/')]")
                    if links:
                        found_any = True
                        try:
                            links[0].click()
                            time.sleep(1.5)
                        except Exception:
                            pass
                        url = self._now_url()
                        if "/video/" in url:
                            self.log("✅ Navegou para URL de vídeo via Creator Center.")
                            return True
                    # fallback: cards sem link direto, mas lista existe
                    cards = self.driver.find_elements(By.CSS_SELECTOR, "[data-e2e='post-list'] a, div[class*='post-card'], div[class*='video-item']")
                    if cards:
                        found_any = True
                        # ausência do botão de postar já será capturada no próximo scan
                        return True
                except Exception:
                    pass
                time.sleep(1)

            if not found_any:
                self.log("ℹ️ Creator Center sem cards/links ainda.")
            return False
        except Exception as e:
            self.log(f"⚠️ Probing falhou: {e}")
            return False

    # Decisão
    def _decide_status(self, signals: ConfirmationSignals, strict: bool) -> ConfirmationResult:
        strong = signals.video_url_detected or signals.publish_button_disappeared or signals.hard_success_text
        if strong:
            return ConfirmationResult(
                status=ConfirmationStatus.PUBLISHED,
                signals=signals,
                reason="Sinais fortes: URL de vídeo ou botão ausente ou texto de sucesso.",
            )
        partial = signals.left_upload and signals.submitted_text
        if partial:
            return ConfirmationResult(
                status=ConfirmationStatus.SUBMITTED,
                signals=signals,
                reason="Saiu de upload + submitted/review – não deletar ainda.",
            )
        return ConfirmationResult(
            status=ConfirmationStatus.UNKNOWN,
            signals=signals,
            reason="Sem sinais suficientes.",
        )

    # API principal
    def confirm_posted(self, timeout: int = CONFIRMATION_TIMEOUT, strict: bool = True, quick_check: bool = False) -> ConfirmationResult:
        if quick_check:
            return self._quick_confirm(strict=strict)

        start = time.time()
        deadline = start + timeout
        probe_done_pct = False
        probe_done_force = False
        last_progress = ""

        self.log(f"⏳ Aguardando confirmação (timeout: {timeout}s, strict={strict})...")

        while True:
            now = time.time()
            if now >= deadline:
                break
            remaining = deadline - now

            try:
                progress_snips, success_snips, hard_text, submitted_text, avg_pct = self._scan_status_messages(refresh=True)
                url_changed, left_upload, video_url_detected = self.check_url_changed()
                button_gone = self.check_publish_button_disappeared()

                signals = ConfirmationSignals(
                    url_changed=url_changed,
                    left_upload=left_upload,
                    video_url_detected=video_url_detected,
                    publish_button_disappeared=button_gone,
                    hard_success_text=hard_text,
                    submitted_text=submitted_text,
                    progress_snippets=progress_snips,
                    success_snippets=success_snips,
                    current_url=self._now_url(),
                    progress_percentage=avg_pct,
                )

                result = self._decide_status(signals, strict=strict)
                if result.is_published():
                    self.log("🎉 Vídeo PUBLICADO (sinal forte).")
                    return result

                # probing por % (70%+)
                if (not probe_done_pct) and avg_pct > PROBING_THRESHOLD:
                    probe_done_pct = True
                    if self._probe_creator_center_posted(max_wait=min(PROBING_MAX_WAIT, int(remaining))):
                        # re-scan imediato
                        continue

                # probing forçado após FORCE_PROBE_AFTER
                if (not probe_done_force) and (now - start) >= FORCE_PROBE_AFTER:
                    probe_done_force = True
                    if self._probe_creator_center_posted(max_wait=min(PROBING_MAX_WAIT, int(remaining))):
                        continue

                # early-exit estrito perto do fim: fora de upload + sem botão
                if (now > (deadline - EARLY_EXIT_THRESHOLD)) and left_upload and button_gone:
                    self.log("✅ Early-exit: fora de upload + botão ausente.")
                    return ConfirmationResult(
                        status=ConfirmationStatus.PUBLISHED,
                        signals=signals,
                        reason="Early-exit: fora de upload + botão ausente.",
                    )

                if progress_snips:
                    summary = "; ".join(progress_snips[:2])
                    if summary != last_progress:
                        self.log(f"⏳ Aguardando: {summary} ({avg_pct:.0f}%)")
                        last_progress = summary

            except StaleElementReferenceException:
                self.log("🔄 Stale – retrying...")
            except Exception as e:
                self.log(f"⚠️ Erro aguardando: {e}")

            time.sleep(min(POLL_INTERVAL, remaining))

        # Timeout: snapshot final
        try:
            screenshot_path = f"/tmp/tiktok_confirmation_timeout_{int(time.time())}.png"
            self.driver.save_screenshot(screenshot_path)
            self.log(f"📸 Screenshot timeout: {screenshot_path}")
        except Exception:
            pass

        # Re-scan final
        progress_snips, success_snips, hard_text, submitted_text, avg_pct = self._scan_status_messages(refresh=True)
        url_changed, left_upload, video_url_detected = self.check_url_changed()
        button_gone = self.check_publish_button_disappeared()
        signals = ConfirmationSignals(
            url_changed=url_changed,
            left_upload=left_upload,
            video_url_detected=video_url_detected,
            publish_button_disappeared=button_gone,
            hard_success_text=hard_text,
            submitted_text=submitted_text,
            progress_snippets=progress_snips,
            success_snippets=success_snips,
            current_url=self._now_url(),
            progress_percentage=avg_pct,
        )
        result = self._decide_status(signals, strict=strict)

        if result.is_published():
            self.log("🎉 PUBLICADO no timeout.")
        elif result.is_submitted():
            self.log("ℹ️ SUBMITTED no timeout.")
        else:
            self.log("⚠️ UNKNOWN no timeout.")

        return result

    def _quick_confirm(self, strict: bool) -> ConfirmationResult:
        if self._cached_signals:
            s = self._cached_signals
        else:
            progress_snips, success_snips, hard_text, submitted_text, avg_pct = self._scan_status_messages(refresh=True)
            url_changed, left_upload, video_url_detected = self.check_url_changed()
            button_gone = self.check_publish_button_disappeared()
            s = ConfirmationSignals(
                url_changed=url_changed,
                left_upload=left_upload,
                video_url_detected=video_url_detected,
                publish_button_disappeared=button_gone,
                hard_success_text=hard_text,
                submitted_text=submitted_text,
                progress_snippets=progress_snips,
                success_snippets=success_snips,
                current_url=self._now_url(),
                progress_percentage=avg_pct,
            )
            self._cached_signals = s
        return self._decide_status(s, strict=strict)

    def get_post_status(self) -> Dict[str, object]:
        if self._cached_signals:
            s = self._cached_signals
        else:
            progress_snips, success_snips, hard_text, submitted_text, avg_pct = self._scan_status_messages(refresh=True)
            url_changed, left_upload, video_url_detected = self.check_url_changed()
            button_gone = self.check_publish_button_disappeared()
            s = ConfirmationSignals(
                url_changed=url_changed,
                left_upload=left_upload,
                video_url_detected=video_url_detected,
                publish_button_disappeared=button_gone,
                hard_success_text=hard_text,
                submitted_text=submitted_text,
                progress_snippets=progress_snips,
                success_snippets=success_snips,
                current_url=self._now_url(),
                progress_percentage=avg_pct,
            )
            self._cached_signals = s
        return {
            "url_changed": s.url_changed,
            "left_upload": s.left_upload,
            "video_url_detected": s.video_url_detected,
            "publish_button_disappeared": s.publish_button_disappeared,
            "hard_success_text": s.hard_success_text,
            "submitted_text": s.submitted_text,
            "has_progress": len(s.progress_snippets) > 0,
            "has_success_text": len(s.success_snippets) > 0,
            "progress_percentage": s.progress_percentage,
            "current_url": s.current_url,
            "progress_snippets": s.progress_snippets[:5],
            "success_snippets": s.success_snippets[:5],
        }

    def print_status(self):
        s = self.get_post_status()
        self.log("📊 Status da postagem:")
        self.log(f"   URL mudou: {s['url_changed']} | Saiu de upload: {s['left_upload']} | Vídeo URL: {s['video_url_detected']}")
        self.log(f"   Botão sumiu: {s['publish_button_disappeared']}")
        self.log(f"   Hard success: {s['hard_success_text'] or '—'}")
        self.log(f"   Submitted: {s['submitted_text'] or '—'} | Progresso: {s['progress_percentage']:.0f}%")
        self.log(f"   Tem progresso: {s['has_progress']} | Tem texto sucesso: {s['has_success_text']}")
        self.log(f"   URL atual: {s['current_url']}")
        if s['progress_snippets']:
            self.log(f"   Progresso: {', '.join(s['progress_snippets'])}")
        if s['success_snippets']:
            self.log(f"   Sucesso: {', '.join(s['success_snippets'])}")

    # Wrapper legado
    def wait_for_confirmation(self, timeout: int = CONFIRMATION_TIMEOUT) -> bool:
        result = self.confirm_posted(timeout=timeout, strict=True, quick_check=False)
        return result.is_published()

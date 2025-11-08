# -*- coding: utf-8 -*-
"""
Módulo auxiliar para verificar se o vídeo recém postado apareceu no Creator Center.
Usa heurísticas no próprio navegador (sem APIs externas) para validar o cartão.
"""
from __future__ import annotations

import time
import unicodedata
from typing import Callable, List, Optional, Sequence, Set

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException, WebDriverException

TARGET_URL = "https://www.tiktok.com/tiktokstudio?tab=posted"


class PostPublishVerifier:
    """
    Verifica se o vídeo recém postado aparece no Creator Center (tab=posted).
    Útil para evitar falsos positivos quando o TikTok não publica de fato.
    """

    def __init__(self, driver, logger: Optional[Callable[[str], None]] = None):
        self.driver = driver
        self.log = logger if logger else print

    # ===== Utils =====
    @staticmethod
    def _normalize(text: Optional[str]) -> str:
        normalized = unicodedata.normalize("NFKD", (text or "").strip())
        normalized = normalized.encode("ascii", "ignore").decode().lower()
        return " ".join(normalized.split())

    @staticmethod
    def _build_signature(description: Optional[str], fallback: Optional[str]) -> List[str]:
        base = PostPublishVerifier._normalize(description) or PostPublishVerifier._normalize(fallback)
        tokens = [tok for tok in base.split() if len(tok) > 3]
        if not tokens:
            return []
        # limita aos primeiros 10 tokens relevantes
        seen: List[str] = []
        for tok in tokens:
            if tok not in seen:
                seen.append(tok)
            if len(seen) >= 10:
                break
        return seen

    @staticmethod
    def _score_candidate(signature: Sequence[str], candidate_text: str) -> int:
        if not signature:
            return 0
        candidate_tokens: Set[str] = set(PostPublishVerifier._normalize(candidate_text).split())
        return sum(1 for tok in signature if tok in candidate_tokens)

    def _collect_candidate_texts(self, max_items: int = 8) -> List[str]:
        texts: List[str] = []
        selectors = [
            "//a[contains(@href, '/video/')]",
            "//*[@data-e2e='post-list']//*[self::a or self::div]",
            "//*[contains(@class,'post-card') or contains(@class,'video-item')]",
        ]
        for selector in selectors:
            try:
                elements = self.driver.find_elements(By.XPATH, selector)
            except WebDriverException:
                continue
            for el in elements:
                try:
                    txt = el.text.strip()
                except Exception:
                    txt = ""
                if txt:
                    texts.append(txt)
                if len(texts) >= max_items:
                    return texts
        return texts

    # ===== Public API =====
    def verify_recent_post(
        self,
        expected_description: Optional[str],
        fallback_name: Optional[str],
        timeout: int = 60,
        wait_between_checks: int = 5,
    ) -> bool:
        signature = self._build_signature(expected_description, fallback_name)
        if not signature:
            self.log("ℹ️ Sem assinatura de verificação – pulando verificador externo.")
            return False

        deadline = time.time() + max(10, timeout)
        attempt = 0
        while time.time() < deadline:
            attempt += 1
            try:
                self.driver.get(TARGET_URL)
                WebDriverWait(self.driver, 5).until(
                    lambda d: len(d.find_elements(By.XPATH, "//body")) > 0
                )
            except TimeoutException:
                self.log("⚠️ Verificador: timeout carregando Creator Center.")
            except Exception as exc:
                self.log(f"⚠️ Verificador: erro ao abrir Creator Center: {exc}")
                time.sleep(wait_between_checks)
                continue

            candidates = self._collect_candidate_texts()
            for text in candidates:
                score = self._score_candidate(signature, text)
                needed = max(1, min(len(signature), 3))
                if score >= needed:
                    self.log("✅ Verificador externo encontrou o vídeo no Creator Center.")
                    return True

            self.log(f"ℹ️ Verificador não encontrou correspondência (tentativa {attempt}).")
            time.sleep(wait_between_checks)

        self.log("⚠️ Verificador externo não encontrou o vídeo; possível falha de publicação.")
        return False

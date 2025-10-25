"""Utilitário de scraping de perfis TikTok.

Adaptado do script `Scraper/TikTok.py`, removendo efeitos colaterais
e estruturando o retorno para uso no backend.
"""

from __future__ import annotations

import logging
import re
import urllib.parse
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import hashlib
import random
from typing import Any, Dict, List, Optional, Sequence, Tuple

import requests
from bs4 import BeautifulSoup
from requests.cookies import RequestsCookieJar
from urllib.parse import urlencode

from sqlalchemy.orm import Session

from src.models import TikTokAccount, TikTokAccountMetric
from src.repositories import TikTokAccountMetricsRepository
from src.account_storage import AccountStorage


logger = logging.getLogger(__name__)


API_USER_DETAIL_URL = "https://www.tiktok.com/api/user/detail/"
API_POST_ITEM_LIST_URL = "https://www.tiktok.com/api/post/item_list/"
SIGNER_SCRIPT_PATH = Path(__file__).resolve().parent.parent / "scripts" / "tiktok_signer.js"


class TikTokScraperError(RuntimeError):
    """Erro genérico do scraper."""


@dataclass
class TikTokProfileData:
    """Estrutura normalizada com métricas essenciais do perfil."""

    user_id: str
    unique_id: str
    nickname: str
    followers: Optional[int]
    following: Optional[int]
    likes: Optional[int]
    videos: Optional[int]
    friend_count: Optional[int]
    heart: Optional[int]
    digg_count: Optional[int]
    verified: bool
    private_account: bool
    region: Optional[str]
    signature: str
    profile_pic: Optional[str]
    sec_uid: Optional[str]
    comment_setting: Optional[int]
    social_links: List[str]
    source: str
    raw: Dict[str, Any]


def _safe_int(value: Any) -> Optional[int]:
    try:
        if value is None:
            return None
        if isinstance(value, bool):  # evita True -> 1
            return int(value)
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def _safe_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes"}
    return bool(value)


def _merge_social_links(*lists: Sequence[str]) -> List[str]:
    seen = set()
    merged: List[str] = []
    for candidate_list in lists:
        for entry in candidate_list or []:
            normalized = entry.strip()
            if normalized and normalized not in seen:
                seen.add(normalized)
                merged.append(normalized)
    return merged


class TikTokScraper:
    """Cliente simples para recuperar métricas públicas de perfis TikTok."""

    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )

    def __init__(self, session: Optional[requests.Session] = None) -> None:
        self.session = session or requests.Session()
        self.session.headers.setdefault("User-Agent", self.USER_AGENT)

    # ------------------------------------------------------------------
    # API fallback
    # ------------------------------------------------------------------
    def _fetch_user_info_via_api(
        self, identifier: str, headers: Dict[str, str]
    ) -> Tuple[Optional[Dict[str, Any]], List[str]]:
        if identifier.startswith("@"):
            identifier = identifier[1:]

        params = {
            "uniqueId": identifier,
            "device_id": "1234567890",
        }

        try:
            response = self.session.get(
                API_USER_DETAIL_URL,
                headers=headers,
                params=params,
                timeout=10,
            )
            if response.status_code != 200:
                return None, []

            data = response.json()
            user_info = data.get("userInfo") or {}
            user = user_info.get("user") or {}
            stats = user_info.get("stats") or {}

            if not user:
                return None, []

            fallback = lambda key: f"No {key} found"
            info_from_api: Dict[str, Any] = {
                "user_id": user.get("id", fallback("user_id")),
                "unique_id": user.get("uniqueId", fallback("unique_id")),
                "nickname": user.get("nickname", fallback("nickname")),
                "verified": user.get("verified", False),
                "privateAccount": user.get("privateAccount", False),
                "region": user.get("region", fallback("region")),
                "followers": stats.get("followerCount"),
                "following": stats.get("followingCount"),
                "likes": stats.get("heartCount"),
                "videos": stats.get("videoCount"),
                "friendCount": stats.get("friendCount"),
                "heart": stats.get("heart"),
                "diggCount": stats.get("diggCount"),
                "secUid": user.get("secUid"),
                "commentSetting": user.get("commentSetting"),
                "signature": user.get("signature", ""),
                "profile_pic": user.get("avatarLarger"),
            }

            social_links: List[str] = []
            bio_link = user.get("bioLink")
            if isinstance(bio_link, dict):
                link = bio_link.get("link")
                if link:
                    clean_link = link.replace("\\u002F", "/")
                    social_links.append(f"Link: {clean_link} - {clean_link}")

            return info_from_api, social_links
        except Exception as exc:  # pragma: no cover - fallback
            logger.debug("Falha ao acessar API pública do TikTok: %s", exc)
            return None, []

    # ------------------------------------------------------------------
    # HTML parsing helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _extract_patterns(html: str) -> Dict[str, Any]:
        patterns = {
            "user_id": r'"webapp.user-detail":{"userInfo":{"user":{"id":"(\d+)"',
            "unique_id": r'"uniqueId":"(.*?)"',
            "nickname": r'"nickname":"(.*?)"',
            "followers": r'"followerCount":(\d+)',
            "following": r'"followingCount":(\d+)',
            "likes": r'"heartCount":(\d+)',
            "videos": r'"videoCount":(\d+)',
            "signature": r'"signature":"(.*?)"',
            "verified": r'"verified":(true|false)',
            "secUid": r'"secUid":"(.*?)"',
            "commentSetting": r'"commentSetting":(\d+)',
            "privateAccount": r'"privateAccount":(true|false)',
            "region": r'"ttSeller":false,"region":"([^"]*)"',
            "heart": r'"heart":(\d+)',
            "diggCount": r'"diggCount":(\d+)',
            "friendCount": r'"friendCount":(\d+)',
            "profile_pic": r'"avatarLarger":"(.*?)"',
        }

        info: Dict[str, Any] = {}
        for key, pattern in patterns.items():
            match = re.search(pattern, html)
            if match:
                info[key] = match.group(1)

        return info

    @staticmethod
    def _extract_social_links(html: str, bio_text: str) -> List[str]:
        social_links: List[str] = []

        link_urls = re.findall(
            r'href="(https://www\\.tiktok\\.com/link/v2\?[^"]*?scene=bio_url[^"]*?target=([^"&]+))"',
            html,
        )
        for full_url, target in link_urls:
            target_decoded = urllib.parse.unquote(target)
            text_pattern = rf'href="{re.escape(full_url)}"[^>]*>.*?<span[^>]*SpanLink[^>]*>([^<]+)</span>'
            text_match = re.search(text_pattern, html, re.DOTALL)
            link_text = text_match.group(1) if text_match else target_decoded
            entry = f"Link: {link_text} - {target_decoded}"
            if entry not in social_links:
                social_links.append(entry)

        span_links = re.findall(r'<span[^>]*class="[^\"]*SpanLink[^\"]*">([^<]+)</span>', html)
        for span_text in span_links:
            if "." in span_text and " " not in span_text:
                entry = f"Link: {span_text} - {span_text}"
                if entry not in social_links:
                    social_links.append(entry)

        all_targets = re.findall(r'scene=bio_url[^"]*?target=([^"&]+)', html)
        for target in all_targets:
            target_decoded = urllib.parse.unquote(target)
            text_pattern = rf'target={re.escape(target)}[^>]*>.*?<span[^>]*>([^<]+)</span>'
            text_match = re.search(text_pattern, html, re.DOTALL)
            link_text = text_match.group(1) if text_match else target_decoded
            entry = f"Link: {link_text} - {target_decoded}"
            if entry not in social_links:
                social_links.append(entry)

        bio_link_pattern = r'"bioLink":{"link":"([^"]+)","risk":(\d+)}'
        for link, _ in re.findall(bio_link_pattern, html):
            clean_link = link.replace("\\u002F", "/")
            entry = f"💎 **{clean_link}**: `{clean_link}`"
            if entry not in social_links:
                social_links.append(entry)

        shared_links_pattern = r'"shareUrl":"([^"]+)"'
        for shared_url in re.findall(shared_links_pattern, html):
            clean_url = shared_url.replace("\\u002F", "/")
            entry = f"💎 **{clean_url}**: `{clean_url}`"
            if entry not in social_links:
                social_links.append(entry)

        share_links_div_pattern = re.compile(
            r'<div[^>]*class="[^\"]*DivShareLinks[^\"]*"[^>]*>(.*?)</div>', re.DOTALL
        )
        for div_match in share_links_div_pattern.finditer(html):
            div_content = div_match.group(1)
            div_links = re.finditer(
                r'<a[^>]*href="[^"]*scene=bio_url[^"]*target=([^"&]+)"[^>]*>.*?<span[^>]*class="[^\"]*SpanLink[^\"]*">([^<]+)</span>',
                div_content,
                re.DOTALL,
            )
            for link_match in div_links:
                target = urllib.parse.unquote(link_match.group(1))
                link_text = link_match.group(2)
                entry = f"💎 **{link_text}**: `{target}`"
                if entry not in social_links:
                    social_links.append(entry)

        bio = bio_text or ""
        social_patterns = {
            "Instagram": r'[iI][gG]:\s*@?([a-zA-Z0-9._]+)',
            "Snapchat": r'([sS][cC]|[sS]napchat):\s*@?([a-zA-Z0-9._]+)',
            "Twitter/X": r'([tT]witter|[xX]):\s*@?([a-zA-Z0-9._]+)',
            "Facebook": r'[fF][bB]:\s*@?([a-zA-Z0-9._]+)',
            "YouTube": r'([yY][tT]|[yY]outube):\s*@?([a-zA-Z0-9._]+)',
            "Telegram": r'[tT]elegram:\s*@?([a-zA-Z0-9._]+)',
        }

        for label, pattern in social_patterns.items():
            match = re.search(pattern, bio)
            if match:
                username = match.group(2) if len(match.groups()) > 1 else match.group(1)
                prefix = "@" if label in {"Instagram", "Twitter/X", "Telegram"} else ""
                entry = f"{label}: {prefix}{username}"
                if entry not in social_links:
                    social_links.append(entry)

        email_match = re.search(r'[\w.+-]+@[\w-]+\.[\w.-]+', bio)
        if email_match:
            entry = f"Email: {email_match.group(0)}"
            if entry not in social_links:
                social_links.append(entry)

        return social_links

    # ------------------------------------------------------------------
    # Público
    # ------------------------------------------------------------------
    def fetch_profile(self, identifier: str, *, by_id: bool = False) -> TikTokProfileData:
        identifier = identifier.strip()
        if not identifier:
            raise TikTokScraperError("identifier cannot be empty")

        if by_id:
            url = f"https://www.tiktok.com/@{identifier}"
        else:
            if identifier.startswith("@"):
                identifier = identifier[1:]
            url = f"https://www.tiktok.com/@{identifier}"

        headers = {"User-Agent": self.USER_AGENT}

        response = self.session.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            raise TikTokScraperError(f"TikTok returned status {response.status_code}")

        html_content = response.text

        try:
            soup = BeautifulSoup(html_content, "lxml")
        except Exception:
            soup = BeautifulSoup(html_content, "html.parser")

        info = self._extract_patterns(html_content)

        # Fallback para API quando dados cruciais não aparecem no HTML
        if not info.get("user_id") or not info.get("unique_id"):
            api_info, api_links = self._fetch_user_info_via_api(identifier, headers)
            if not api_info:
                raise TikTokScraperError("Unable to extract TikTok profile information")
            info.update(api_info)
            social_links = _merge_social_links(self._extract_social_links(html_content, info.get("signature", "")), api_links)
            source = "api"
        else:
            social_links = self._extract_social_links(html_content, info.get("signature", ""))
            api_info, api_links = self._fetch_user_info_via_api(identifier, headers)
            info.update(api_info or {})
            social_links = _merge_social_links(social_links, api_links)
            source = "html"

        # Normalização de campos numéricos/booleanos
        profile_pic = info.get("profile_pic")
        if isinstance(profile_pic, str):
            profile_pic = profile_pic.replace("\\u002F", "/")

        signature = info.get("signature") or ""
        if not isinstance(signature, str):
            signature = str(signature)

        data = TikTokProfileData(
            user_id=str(info.get("user_id", "")),
            unique_id=str(info.get("unique_id", identifier)),
            nickname=str(info.get("nickname", "")),
            followers=_safe_int(info.get("followers")),
            following=_safe_int(info.get("following")),
            likes=_safe_int(info.get("likes")),
            videos=_safe_int(info.get("videos")),
            friend_count=_safe_int(info.get("friendCount")),
            heart=_safe_int(info.get("heart")),
            digg_count=_safe_int(info.get("diggCount")),
            verified=_safe_bool(info.get("verified")),
            private_account=_safe_bool(info.get("privateAccount")),
            region=info.get("region"),
            signature=signature.replace("\\n", "\n"),
            profile_pic=profile_pic,
            sec_uid=info.get("secUid"),
            comment_setting=_safe_int(info.get("commentSetting")),
            social_links=social_links,
            source=source,
            raw=info,
        )
        return data

    # ------------------------------------------------------------------
    # Conteúdo publicado
    # ------------------------------------------------------------------
    def _normalize_post_item(self, item: Dict[str, Any], account_name: str) -> Dict[str, Any]:
        stats = item.get("stats") or {}
        video_info = item.get("video") or {}

        created_at = None
        try:
            timestamp = int(item.get("createTime", 0))
            created_at = datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()
        except (TypeError, ValueError):
            created_at = None

        cover_url = video_info.get("cover") or video_info.get("dynamicCover") or video_info.get("originCover")
        if isinstance(cover_url, dict):
            cover_url = cover_url.get("url_list", [None])[0]

        duration = None
        try:
            duration = int(video_info.get("duration"))
        except (TypeError, ValueError):
            duration = None

        author = item.get("author") or {}
        return {
            "id": str(item.get("id")),
            "description": item.get("desc") or "",
            "create_time": created_at,
            "duration": duration,
            "like_count": _safe_int(stats.get("diggCount")),
            "comment_count": _safe_int(stats.get("commentCount")),
            "share_count": _safe_int(stats.get("shareCount")),
            "play_count": _safe_int(stats.get("playCount")),
            "collect_count": _safe_int(stats.get("collectCount")),
            "cover_url": cover_url,
            "permalink": f"https://www.tiktok.com/@{account_name}/video/{item.get('id')}",
            "author": {
                "nickname": author.get("nickname"),
                "unique_id": author.get("uniqueId"),
                "avatar_thumb": author.get("avatarThumb"),
                "avatar_medium": author.get("avatarMedium"),
                "avatar_larger": author.get("avatarLarger"),
            },
            "stats": {
                "diggCount": stats.get("diggCount"),
                "commentCount": stats.get("commentCount"),
                "shareCount": stats.get("shareCount"),
                "playCount": stats.get("playCount"),
                "collectCount": stats.get("collectCount"),
            },
            "is_pinned_item": bool(item.get("isPinnedItem")),
        }

    def _load_account_cookies(self, account_name: str) -> Tuple[Optional[RequestsCookieJar], Optional[str]]:
        """
        Carrega cookies salvos da conta para serem reutilizados em chamadas autenticadas.
        Retorna (cookie_jar, ms_token)
        """
        if not account_name:
            return None, None

        storage = AccountStorage()
        cookies_data = storage.get_latest_cookies(account_name)
        if not cookies_data:
            return None, None

        jar = RequestsCookieJar()
        ms_token = None

        def _push_cookie(name: str, value: Any, domain: Optional[str], path: Optional[str]) -> None:
            if not name or value is None:
                return
            jar.set(name, str(value), domain=domain or ".tiktok.com", path=path or "/")

        if isinstance(cookies_data, dict):
            # Formato simples {name: value}
            for name, value in cookies_data.items():
                _push_cookie(name, value, ".tiktok.com", "/")
                if name == "msToken":
                    ms_token = str(value)
        elif isinstance(cookies_data, list):
            for entry in cookies_data:
                if not isinstance(entry, dict):
                    continue
                name = entry.get("name")
                value = entry.get("value")
                domain = entry.get("domain")
                path = entry.get("path")
                _push_cookie(name, value, domain, path)
                if name == "msToken":
                    ms_token = str(value)
        else:
            # Estruturas mais complexas: tenta converter
            try:
                for entry in cookies_data:  # type: ignore[assignment]
                    name = entry.get("name")
                    value = entry.get("value")
                    domain = entry.get("domain")
                    path = entry.get("path")
                    _push_cookie(name, value, domain, path)
                    if name == "msToken":
                        ms_token = str(value)
            except Exception:
                return None, None

        return jar, ms_token

    def _generate_x_bogus(self, url: str) -> Optional[str]:
        if not SIGNER_SCRIPT_PATH.exists():
            logger.debug("Script de assinatura X-Bogus não encontrado em %s", SIGNER_SCRIPT_PATH)
            return None

        try:
            result = subprocess.run(
                ["node", str(SIGNER_SCRIPT_PATH), url, self.USER_AGENT],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
        except FileNotFoundError:
            logger.warning("Node.js não disponível para gerar X-Bogus.")
            return None
        except subprocess.TimeoutExpired:
            logger.warning("Geração do X-Bogus excedeu o tempo limite para %s", url)
            return None

        if result.returncode != 0:
            stderr = (result.stderr or "").strip()
            logger.debug("Falha ao gerar X-Bogus (rc=%s): %s", result.returncode, stderr)
            return None

        signature = (result.stdout or "").strip()
        if not signature:
            return None
        return signature

    def fetch_recent_posts(self, identifier: str, *, count: int = 9, account_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Recupera posts recentes públicos de um perfil TikTok.

        Args:
            identifier: username (com ou sem @) ou user id
            count: quantidade de vídeos a buscar (máx 30)
        """
        identifier = identifier.strip()
        if not identifier:
            raise TikTokScraperError("identifier cannot be empty")

        if identifier.startswith("@"):
            identifier = identifier[1:]

        headers = {
            "User-Agent": self.USER_AGENT,
            "Referer": f"https://www.tiktok.com/@{identifier}",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        }

        profile_info, _ = self._fetch_user_info_via_api(identifier, headers)
        if not profile_info or not profile_info.get("secUid"):
            raise TikTokScraperError("Unable to resolve TikTok secUid for profile")

        sec_uid = profile_info["secUid"]
        unique_id = profile_info.get("unique_id", identifier)
        cookie_jar, ms_token = (None, None)
        if account_name:
            cookie_jar, ms_token = self._load_account_cookies(account_name)

        # Garante consistência do device_id para não alterar assinatura com chamadas subsequentes
        device_seed = hashlib.md5(unique_id.encode("utf-8")).hexdigest()
        device_id = str(int(device_seed[:14], 16))

        base_params: Dict[str, Any] = {
            "aid": "1988",
            "app_language": "pt-BR",
            "app_name": "tiktok_web",
            "browser_language": "pt-BR",
            "browser_name": "Mozilla",
            "browser_online": "true",
            "browser_platform": "Win32",
            "browser_version": self.USER_AGENT.split("Chrome/")[-1],
            "channel": "tiktok_web",
            "cookie_enabled": "true",
            "count": str(min(max(count, 1), 30)),
            "cursor": "0",
            "device_id": device_id,
            "device_platform": "web_pc",
            "focus_state": "true",
            "from_page": "user",
            "history_len": "3",
            "is_fullscreen": "false",
            "is_page_visible": "true",
            "language": "pt",
            "os": "windows",
            "priority_region": "",
            "referer": "",
            "region": "BR",
            "screen_height": "1080",
            "screen_width": "1920",
            "tz_name": "America/Sao_Paulo",
            "uniqueId": unique_id,
            "secUid": sec_uid,
        }

        if ms_token:
            base_params["msToken"] = ms_token
        else:
            # Param obrigatório quando deslogado; usar token sintético re-gerado
            base_params["msToken"] = "".join(random.choices("abcdefghijklmnopqrstuvwxyz0123456789", k=107))

        query_without_signature = urlencode(base_params)
        url_for_signature = f"{API_POST_ITEM_LIST_URL}?{query_without_signature}"
        x_bogus = self._generate_x_bogus(url_for_signature)
        final_query = f"{query_without_signature}&X-Bogus={urllib.parse.quote_plus(x_bogus)}" if x_bogus else query_without_signature
        final_url = f"{API_POST_ITEM_LIST_URL}?{final_query}"

        session = requests.Session()
        session.headers.update(headers)
        if cookie_jar:
            session.cookies.update(cookie_jar)

        try:
            response = session.get(final_url, timeout=15)
        except requests.RequestException as exc:
            raise TikTokScraperError(f"HTTP error contacting TikTok: {exc}") from exc

        if response.status_code != 200:
            raise TikTokScraperError(f"TikTok post list returned status {response.status_code}")

        payload = response.json()
        items = payload.get("itemList") or []
        if not items and payload.get("statusCode") not in (0, None):
            raise TikTokScraperError(f"TikTok API returned error: {payload.get('status_msg') or payload.get('statusCode')}")

        normalized: List[Dict[str, Any]] = []
        for item in items:
            try:
                normalized.append(self._normalize_post_item(item, unique_id))
            except Exception as exc:  # pragma: no cover - falhas de parsing são ignoradas
                logger.debug("Falha ao normalizar post TikTok %s: %s", item.get("id"), exc)
                continue

        return normalized


def capture_account_metrics(scraper: TikTokScraper, identifier: str) -> TikTokProfileData:
    """Wrapper que normaliza exceções para o serviço do backend."""

    try:
        return scraper.fetch_profile(identifier)
    except requests.RequestException as exc:
        raise TikTokScraperError(f"HTTP error contacting TikTok: {exc}") from exc
    except Exception as exc:
        raise TikTokScraperError(str(exc)) from exc


def refresh_account_metrics(db: Session, account: TikTokAccount) -> Tuple[TikTokAccountMetric, TikTokProfileData]:
    """Coleta métricas do TikTok e persiste a última fotografia."""

    scraper = TikTokScraper()
    profile = capture_account_metrics(scraper, account.account_name)

    record = TikTokAccountMetricsRepository.create(
        db,
        account_id=account.id,
        followers=profile.followers,
        following=profile.following,
        likes=profile.likes,
        videos=profile.videos,
        friend_count=profile.friend_count,
        heart=profile.heart,
        digg_count=profile.digg_count,
        verified=profile.verified,
        private_account=profile.private_account,
        region=profile.region,
        signature=profile.signature,
        profile_pic=profile.profile_pic,
        social_links=profile.social_links,
        extra={
            "sec_uid": profile.sec_uid,
            "comment_setting": profile.comment_setting,
            "nickname": profile.nickname,
            "source": profile.source,
            "raw": profile.raw,
        },
    )

    return record, profile

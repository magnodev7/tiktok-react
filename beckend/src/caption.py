# src/caption.py
import os
import re
import json
import unicodedata


from typing import Dict, List, Optional, Set, Tuple
from .config import (

    BRAND_TAGS,
    EXTRA_HASHTAGS,
    MAX_CAPTION_CHARS,
    DEFAULT_CTA,
)

# Stopwords PT-BR (curto e objetivo)
_PT_SW = {
    "a","o","as","os","um","uma","de","da","do","das","dos","e","ou","que","em",
    "no","na","nos","nas","para","por","com","sem","sobre","ao","à","às","aos",
    "se","sua","seu","suas","seus","meu","minha","meus","minhas","teu","tua",
    "teus","tuas","isso","isto","aquilo","um","uma","uns","umas","já","até",
    "mais","menos","muito","pouco","como","quando","onde","porque","porquê"
}

def _strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn")

def _tokenize_pt(text: str) -> List[str]:
    text = _strip_accents(text.lower())
    text = re.sub(r"[^a-z0-9\s-]", " ", text)
    parts = re.split(r"[\s\-_.]+", text)
    toks = [p for p in parts if p and p not in _PT_SW and len(p) >= 3]
    return toks

def _title_from_filename(path: str) -> str:
    base = os.path.splitext(os.path.basename(path))[0]
    # normaliza espaços
    nice = re.sub(r"[_\-]+", " ", base).strip()
    # deixa a primeira letra de cada palavra maiúscula (sem exageros)
    return " ".join(w.capitalize() if len(w) > 2 else w for w in nice.split())

def _hashtagize(token: str) -> str:
    token = _strip_accents(token.lower())
    token = re.sub(r"[^a-z0-9]", "", token)
    if not token:
        return ""
    return f"#{token}"

def _build_hashtags(
    tokens: List[str],
    extra: Optional[List[str]] = None,
    max_tags: int = 8
) -> List[str]:
    seen = set()
    out: List[str] = []

    # 1) tokens individuais
    for t in tokens:
        ht = _hashtagize(t)
        if ht and ht not in seen:
            out.append(ht); seen.add(ht)
        if len(out) >= max_tags:
            break

    # 2) bigramas simples (ex.: justica + brasil -> #justicabrasil)
    if len(out) < max_tags:
        for i in range(len(tokens)-1):
            ht = _hashtagize(tokens[i] + tokens[i+1])
            if ht and ht not in seen:
                out.append(ht); seen.add(ht)
            if len(out) >= max_tags:
                break

    # 3) tags de marca e extras de config
    for ht in BRAND_TAGS + (EXTRA_HASHTAGS or []) + (extra or []):
        h = ht if ht.startswith("#") else f"#{_strip_accents(ht).lower()}"
        h = re.sub(r"[^#a-z0-9]", "", h)
        if h and h not in seen:
            out.append(h); seen.add(h)
        if len(out) >= max_tags:
            break

    return out[:max_tags]

def _load_sidecar(path: str) -> Tuple[Optional[str], List[str], Optional[str]]:
    """
    Lê arquivos ao lado do vídeo:
      - <video>.txt      -> texto livre (semente de legenda)
      - <video>.meta.json -> { "caption": "...", "hashtags": ["#x"], "cta": "..." }
    Retorna: (caption_seed, hashtags_extra, cta)
    """
    root, _ = os.path.splitext(path)
    caption_seed = None
    hashtags_extra: List[str] = []
    cta = None

    txt = root + ".txt"
    if os.path.exists(txt):
        try:
            with open(txt, "r", encoding="utf-8") as f:
                caption_seed = f.read().strip()
        except:
            pass

    meta = root + ".meta.json"
    if os.path.exists(meta):
        try:
            with open(meta, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                if isinstance(data.get("caption"), str):
                    caption_seed = (caption_seed or "") + "\n" + data["caption"]
                if isinstance(data.get("cta"), str):
                    cta = data["cta"].strip()
                if isinstance(data.get("hashtags"), list):
                    for h in data["hashtags"]:
                        if isinstance(h, str):
                            hashtags_extra.append(h.strip())
        except:
            pass

    return caption_seed, hashtags_extra, cta

def build_caption_for_video(
    video_path: str,
    override_keywords: Optional[List[str]] = None,
    cta: Optional[str] = None,
    extra_tags: Optional[List[str]] = None,
    max_hashtags: int = 8,
) -> str:
    """
    Gera legenda + hashtags a partir do arquivo do vídeo.
    Regras:
      - Primeira linha: frase curta com as palavras-chave principais.
      - Depois: CTA (opcional).
      - Última linha: hashtags relevantes.
      - Corta em MAX_CAPTION_CHARS.
    """
    title = _title_from_filename(video_path)

    side_caption, side_tags, side_cta = _load_sidecar(video_path)
    if not cta:
        cta = side_cta or DEFAULT_CTA

    # keywords
    base_tokens = _tokenize_pt(title)
    if side_caption:
        base_tokens += _tokenize_pt(side_caption)
    if override_keywords:
        base_tokens += [t for t in override_keywords if t]

    # dedup preservando ordem
    seen = set()
    tokens = []
    for t in base_tokens:
        if t not in seen:
            tokens.append(t)
            seen.add(t)

    # legenda (primeira linha -> gancho com KW)
    if side_caption:
        # usa até 120 chars da semente como linha 1, início com KW do título
        hook_kw = " ".join(tokens[:3])
        first_line = (hook_kw + " — " + side_caption.strip()).strip()
    else:
        first_line = title

    # hashtags
    hashtags = _build_hashtags(tokens, extra=(extra_tags or []) + side_tags, max_tags=max_hashtags)

    parts = [first_line]
    if cta:
        parts.append(cta)
    if hashtags:
        parts.append(" ".join(hashtags))

    caption = "\n".join([p for p in parts if p]).strip()

    if len(caption) > MAX_CAPTION_CHARS:
        caption = caption[:MAX_CAPTION_CHARS].rstrip()

    return caption

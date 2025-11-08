#!/usr/bin/env python3
"""
CLI utilitario para confirmar se o ultimo video aparece no Creator Center.
Usa o mesmo verificador inteligente integrado ao fluxo de postagem.
"""

import argparse
import sys
from typing import Optional

from src.driver import build_driver  # type: ignore
try:  # Compatibilidade com versoes sem release_driver_lock
    from src.driver import release_driver_lock  # type: ignore
except Exception:  # pragma: no cover - fallback
    release_driver_lock = None
from src.modules.post_verifier import PostPublishVerifier
from src.paths import account_dirs


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Confere publicacao recente no Creator Center.")
    parser.add_argument("--account", required=True, help="Nome da conta TikTok configurada no sistema.")
    parser.add_argument(
        "--description",
        default="",
        help="Descricao utilizada no post (melhora a precisao da busca).",
    )
    parser.add_argument(
        "--video-name",
        default=None,
        help="Nome do arquivo ou rotulo do video (fallback para geracao da assinatura).",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="Tempo maximo (s) consultando o Creator Center.",
    )
    parser.add_argument(
        "--visible",
        action="store_true",
        help="Abre o Chrome visivel (util para depuracao).",
    )
    return parser


def run_cli(args: Optional[argparse.Namespace] = None) -> int:
    ns = args or _build_parser().parse_args()
    user_dir, _, _ = account_dirs(ns.account)
    fallback_label = ns.video_name or ns.account

    driver = None
    try:
        driver = build_driver(
            account_name=ns.account,
            profile_base_dir=user_dir,
            headless=not ns.visible,
            force_temp_profile=False,
            use_profile_dir=True,
        )
        verifier = PostPublishVerifier(driver, logger=lambda msg: print(f"[verifier] {msg}"))
        ok = verifier.verify_recent_post(
            expected_description=ns.description,
            fallback_name=fallback_label,
            timeout=ns.timeout,
            wait_between_checks=5,
        )
        if ok:
            print("SUCCESS: video confirmado no Creator Center.")
            return 0
        print("WARNING: video nao encontrado - revisar postagem.")
        return 1
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass
            if release_driver_lock:
                try:
                    release_driver_lock(driver)  # type: ignore
                except Exception:
                    pass


def main() -> int:
    parser = _build_parser()
    return run_cli(parser.parse_args())


if __name__ == "__main__":
    sys.exit(main())

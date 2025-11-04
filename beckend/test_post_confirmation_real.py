#!/usr/bin/env python3
# test_post_confirmation_real.py - Teste REAL do Módulo PostConfirmationModule com Selenium
# Publica (TRIGGER_POST) e confirma a postagem medindo eficiência real. Exporta métricas em JSONL.

import os
import sys
import time
import json
import datetime as dt
from pathlib import Path
from typing import Dict, Optional
import traceback
import getpass
import socket

# ───────────────── helpers ─────────────────
def _bool_env(v: Optional[str], default: bool = False) -> bool:
    if v is None:
        return default
    return str(v).strip().lower() in ("1", "true", "yes", "on", "y", "t")

def _resolve_video_path(raw: str, base: str) -> str:
    """Resolve VIDEO_PATH sem duplicar diretório-base (evita videos/videos/...)."""
    rawp = Path(raw)
    if rawp.is_absolute():
        return str(rawp)
    raw_norm  = rawp.as_posix().lstrip("./")
    base_norm = Path(base).as_posix().rstrip("/").lstrip("./")
    if raw_norm == base_norm or raw_norm.startswith(base_norm + "/"):
        return str(Path(raw))
    return str(Path(base) / rawp)

def _stem_title_from_path(video_path: str) -> str:
    """Extrai um título plausível a partir do nome do arquivo (sem extensão)."""
    stem = Path(video_path).stem
    return stem.strip()[:80] if stem else ""

# ───────────────── .env (python-dotenv) ─────────────────
def _find_and_load_dotenv():
    try:
        from dotenv import load_dotenv, find_dotenv
    except Exception:
        return None
    here = Path(__file__).resolve()
    candidates = [
        here.parent / ".env",
        here.parent / "beckend" / ".env",
        here.parent.parent / ".env",
    ]
    for c in candidates:
        if c.exists():
            load_dotenv(dotenv_path=str(c), override=False)
            return c
    p = find_dotenv(usecwd=True)
    if p:
        load_dotenv(dotenv_path=p, override=False)
        return Path(p)
    return None

_DOTENV_PATH = _find_and_load_dotenv()

# ───────────────── Bootstrap de PATHs ─────────────────
HERE = Path(__file__).resolve().parent
CANDIDATES = [
    HERE / "beckend" / "src",
    HERE / "src",
    HERE.parent / "beckend" / "src",
]
added = False
for p in CANDIDATES:
    if (p / "modules").exists():
        # Queremos que 'src' esteja no sys.path, não apenas seu pai
        sys.path.insert(0, str(p))
        added = True
        break
if not added:
    print("❌ Não encontrei a pasta 'src'. Verifique a estrutura do projeto.")
    print("   Tentativas:", ", ".join(str(c) for c in CANDIDATES))
    sys.exit(1)

# ───────────────── Imports do projeto ─────────────────
try:
    # Módulo 5
    from src.modules.post_confirmation import (
        PostConfirmationModule,
        CONFIRMATION_TIMEOUT,
        SUCCESS_URL_FRAGMENTS,
        HARD_SUCCESS_KEYWORDS,  # usaremos no quick-check
    )
    # Módulo 4 (para disparar postagem)
    from src.modules.post_action import PostActionModule, __VERSION__ as POST_ACTION_VER
    from src.driver import get_fresh_driver, is_session_alive
    from src.cookies import load_cookies_for_account
    from src.scheduler import TikTokScheduler
    from src.modules.video_upload import VideoUploadModule
except ImportError as e:
    print(f"❌ Erro de import: {e}")
    sys.exit(1)

# ───────────────── Configs do .env + fallbacks ─────────────────
ACCOUNT_NAME = os.getenv("ACCOUNT_NAME", "mundoparalelodm").strip() or "mundoparalelodm"

# visibilidade: prioriza TIKTOK_BROWSER_VISIBLE, senão VISIBLE
VISIBLE = _bool_env(os.getenv("TIKTOK_BROWSER_VISIBLE", None),
                    default=_bool_env(os.getenv("VISIBLE", "true")))

BASE_VIDEO_DIR = os.getenv("BASE_VIDEO_DIR", "./videos").strip() or "./videos"
BASE_POSTED_DIR = os.getenv("BASE_POSTED_DIR", "./posted").strip() or "./posted"
RAW_VIDEO_PATH = os.getenv("VIDEO_PATH", "./videos/Vídeo 287.mp4").strip()
VIDEO_PATH = _resolve_video_path(RAW_VIDEO_PATH, BASE_VIDEO_DIR)

AUTO_YES = _bool_env(os.getenv("AUTO_YES", "0"))
FAST_CATCHUP = os.getenv("TIKTOK_FAST_CATCHUP_SECONDS", "3")

# Por padrão disparamos a postagem para validar confirmação end-to-end
TRIGGER_POST = _bool_env(os.getenv("TRIGGER_POST", "1"))

# Thresholds de performance
TARGET_CONFIRM_QUICK = float(os.getenv("TARGET_CONFIRM_QUICK", "1.0"))   # s
TARGET_CONFIRM_WAIT  = float(os.getenv("TARGET_CONFIRM_WAIT", "90.0"))   # s
TARGET_TOTAL         = float(os.getenv("TARGET_TOTAL_CONFIRM", "95.0"))  # s
FAIL_ON_SLOW         = _bool_env(os.getenv("FAIL_ON_SLOW", "1"))

# Estágios
STAGES = ["auth", "setup_page", "trigger_post", "confirm_quick", "confirm_wait", "total"]

def measure_time(func, *args, **kwargs):
    start = time.perf_counter()
    result = func(*args, **kwargs)
    end = time.perf_counter()
    return result, (end - start)

# ───────────────── Versão rápida do check (sem esperas) ─────────────────
def verify_post_success_quick_no_wait(module: PostConfirmationModule) -> bool:
    """
    Checagem ultrarrápida: sem aguardar spinner. Deve rodar < 1s.
    Sinais: saiu de /upload, URL de sucesso, botão 'Post' sumiu, mensagem explícita de sucesso.
    """
    from selenium.webdriver.common.by import By as _By  # local para evitar import global
    try:
        # 1) URL não é upload
        try:
            url = (module.driver.current_url or "").lower()
            if "upload" not in url:
                module.log(f"✅ (quick) Saiu de upload: {url}")
                return True
        except Exception:
            pass

        # 2) Fragments de sucesso
        try:
            url = (module.driver.current_url or "").lower()
            if any(frag in url for frag in SUCCESS_URL_FRAGMENTS):
                module.log(f"✅ (quick) URL sucesso: {url}")
                return True
        except Exception:
            pass

        # 3) Botão 'Post' sumiu
        try:
            buttons = module.driver.find_elements(
                _By.XPATH, "//button[@data-e2e='post_video_button']"
            )
            if not any(btn.is_displayed() for btn in buttons if btn):
                module.log("✅ (quick) Botão sumiu")
                return True
        except Exception:
            pass

        # 4) Mensagem explícita de sucesso (usa HARD_SUCCESS_KEYWORDS)
        try:
            body = module.driver.find_element(_By.TAG_NAME, "body").text
            if body:
                norm = module._normalize_text(body)
                if any(k in norm for k in HARD_SUCCESS_KEYWORDS):
                    module.log("✅ (quick) Texto de sucesso no body")
                    return True
        except Exception:
            pass

        return False
    except Exception:
        return False

# ───────────────── Tester ─────────────────
class PostConfirmationTester:
    def __init__(self, account_name: str, visible: bool, video_path: str, trigger_post: bool):
        self.account_name = account_name
        self.visible = visible
        self.video_path = video_path
        self.trigger_post = trigger_post
        self.logger = print
        self.metrics: Dict[str, float] = {stage: 0.0 for stage in STAGES}
        self.driver = None
        self.scheduler = None
        self.upload_module = None
        self.action_module: Optional[PostActionModule] = None
        self.confirm_module: Optional[PostConfirmationModule] = None

    def setup(self):
        print(f"🔧 Configurando Driver REAL (headless={not self.visible})...")
        self.scheduler = TikTokScheduler(account_name=self.account_name, logger=self.logger, visible=False)
        self.scheduler.initial_setup()

        self.driver = get_fresh_driver(
            None,
            profile_base_dir=self.scheduler.USER_DATA_DIR,
            account_name=self.account_name,
            headless=not self.visible,
        )

        alive, _ = measure_time(is_session_alive, self.driver)
        print(f"   Sessão Chrome: {'✅ Viva — pulando criação nova' if alive else '⚠️ Nova sessão'}")

        print(f"🍪 Carregando cookies para @{self.account_name}...")
        cookies_loaded, duration_auth = measure_time(load_cookies_for_account, self.driver, self.account_name)
        self.metrics["auth"] = duration_auth
        print(f"   Cookies: {'✅ Carregados' if cookies_loaded else '❌ Falha'} | Tempo: {duration_auth:.2f}s")
        if not cookies_loaded:
            print("❌ Cookies ausentes. Rode test_cookies.py primeiro!")
            self.cleanup()
            sys.exit(1)

        print("🧪 Validando sessão: Navegando para perfil...")
        self.driver.get(f"https://www.tiktok.com/@{self.account_name}")
        time.sleep(3)
        current_url = self.driver.current_url.lower()
        if "login" in current_url or "sign" in current_url:
            print("❌ Sessão inválida: Redirecionou para login.")
            self._save_debug_screenshot("auth_fail")
            self.cleanup()
            sys.exit(1)
        print("✅ Sessão VÁLIDA: Perfil OK!")

        print("🧪 Navegando para página de upload (edição ativa para gatilhar/confirmar)...")
        self.upload_module = VideoUploadModule(driver=self.driver, logger=self.logger)
        nav_success, duration_nav = measure_time(self.upload_module.navigate_to_upload_page)
        self.metrics["setup_page"] = duration_nav

        if nav_success:
            if os.path.isfile(self.video_path):
                uploaded, _ = measure_time(self.upload_module.send_video_file, self.video_path, retry=True)
                if uploaded:
                    print("✅ Upload dummy OK – página de edição ativa")
                else:
                    print("⚠️ Upload falhou; tente manualmente garantir a página de edição")
            else:
                print(f"ℹ️ Sem arquivo de vídeo em {self.video_path}; assumindo modo de edição já ativo")
        else:
            print("⚠️ Navegação falhou; continue manualmente na tela de edição antes de rodar o teste.")

        self.action_module  = PostActionModule(driver=self.driver, logger=self.logger)
        self.confirm_module = PostConfirmationModule(driver=self.driver, logger=self.logger)

        # **Contexto para confirmação forte**:
        # - username: o @ da conta
        # - expected_title: tenta inferir do arquivo, caso o caption não esteja disponível
        inferred_title = _stem_title_from_path(self.video_path)
        self.confirm_module.set_context(expected_title=inferred_title or None,
                                        username=self.account_name)

        print("✅ Setup completo (PostConfirmationModule pronto)")

    # ───────────────── Trigger de postagem ─────────────────
    def trigger_post_now(self) -> bool:
        print("🧪 Disparando postagem (TRIGGER_POST=1)...")
        start = time.perf_counter()
        try:
            ok_click = self.action_module.click_publish_button()
            if not ok_click:
                print("❌ Não conseguiu clicar em Publicar.")
                self._save_debug_screenshot("trigger_click_fail")
                self.metrics["trigger_post"] = time.perf_counter() - start
                return False

            _ = self.action_module.handle_confirmation_dialog()
            self.metrics["trigger_post"] = time.perf_counter() - start
            print(f"   Resultado: ✅ Disparado | Tempo: {self.metrics['trigger_post']:.2f}s")
            return True
        except Exception as e:
            self.metrics["trigger_post"] = time.perf_counter() - start
            print(f"⚠️ Erro ao disparar postagem: {e}")
            self._save_debug_screenshot("trigger_error")
            return False

    # ───────────────── Testes ─────────────────
    def test_quick_confirm(self) -> bool:
        print("🧪 Verificação rápida (sem espera longa)...")
        ok, duration = measure_time(verify_post_success_quick_no_wait, self.confirm_module)
        self.metrics["confirm_quick"] = duration
        print(f"   Resultado: {'✅ Indícios de sucesso' if ok else '⚠️ Inconclusivo'} | Tempo: {duration:.2f}s")
        return ok

    def test_wait_confirm(self) -> bool:
        print(f"🧪 Aguardando confirmação (timeout={CONFIRMATION_TIMEOUT}s)...")
        ok, duration = measure_time(self.confirm_module.wait_for_confirmation, CONFIRMATION_TIMEOUT)
        self.metrics["confirm_wait"] = duration
        print(f"   Resultado: {'✅ Confirmado' if ok else '❌ Timeout/Não confirmado'} | Tempo: {duration:.2f}s")
        if not ok:
            self._save_debug_screenshot("confirm_timeout")
        return ok

    def run_full_test(self) -> bool:
        start_total = time.perf_counter()

        # Dispara postagem antes de confirmar
        if TRIGGER_POST:
            if not self.trigger_post_now():
                return False
        else:
            print("⏭️ TRIGGER_POST=0 — não disparar postagem, apenas confirmar.")
            self.metrics["trigger_post"] = 0.0

        # Quick check participa do SLA, mas não determina sucesso
        _ = self.test_quick_confirm()

        # Espera completa (critério de sucesso)
        ok_wait = self.test_wait_confirm()

        self.metrics["total"] = time.perf_counter() - start_total

        # ----- Relatório -----
        print("\n🧭 Versões:")
        print("   PostAction:", POST_ACTION_VER)
        if _DOTENV_PATH:
            print(f"📄 .env carregado de: {_DOTENV_PATH}")
        print(f"📁 BASE_VIDEO_DIR={BASE_VIDEO_DIR} | BASE_POSTED_DIR={BASE_POSTED_DIR} | FAST_CATCHUP={FAST_CATCHUP}s")
        print(f"🧯 TRIGGER_POST={'ON' if TRIGGER_POST else 'OFF'}")

        print("\n📊 MÉTRICAS DE EFICIÊNCIA (REAL):")
        print("| Etapa              | Tempo (s) |")
        print("|--------------------|-----------|")
        for stage in STAGES:
            print(f"| {stage:<18} | {self.metrics.get(stage, 0.0):>7.2f} |")

        self._export_metrics_jsonl()

        # ----- Thresholds -----
        slow = []
        if self.metrics["confirm_quick"] > TARGET_CONFIRM_QUICK:
            slow.append(f"confirm_quick>{TARGET_CONFIRM_QUICK}s (got {self.metrics['confirm_quick']:.2f}s)")
        if self.metrics["confirm_wait"] > TARGET_CONFIRM_WAIT:
            slow.append(f"confirm_wait>{TARGET_CONFIRM_WAIT}s (got {self.metrics['confirm_wait']:.2f}s)")
        if self.metrics["total"] > TARGET_TOTAL:
            slow.append(f"total>{TARGET_TOTAL}s (got {self.metrics['total']:.2f}s)")

        print(f"\n🎯 Targets: quick≤{TARGET_CONFIRM_QUICK}s, wait≤{TARGET_CONFIRM_WAIT}s, total≤{TARGET_TOTAL}s")
        if slow and FAIL_ON_SLOW:
            raise AssertionError("Performance abaixo do alvo: " + ", ".join(slow))
        elif slow:
            print("⚠️ Lento:", ", ".join(slow))
        else:
            print("🚀 Excelente! Todos os alvos dentro do limite.")

        return ok_wait

    # ── utils ──
    def _export_metrics_jsonl(self):
        out = {
            "when": dt.datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "host": socket.gethostname(),
            "user": getpass.getuser(),
            "account": self.account_name,
            "visible": self.visible,
            "modules": {
                "post_action": POST_ACTION_VER,
            },
            "metrics": self.metrics,
            "targets": {
                "confirm_quick": TARGET_CONFIRM_QUICK,
                "confirm_wait": TARGET_CONFIRM_WAIT,
                "total": TARGET_TOTAL,
            },
            "env": {
                "BASE_VIDEO_DIR": BASE_VIDEO_DIR,
                "BASE_POSTED_DIR": BASE_POSTED_DIR,
                "VIDEO_PATH": VIDEO_PATH,
                "FAST_CATCHUP": FAST_CATCHUP,
                "VISIBLE": self.visible,
                "TRIGGER_POST": TRIGGER_POST,
            },
        }
        path = HERE / "perf_post_confirmation.jsonl"
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(out, ensure_ascii=False) + "\n")
        print(f"📦 Métricas anexadas em {path.resolve()}")

    def _save_debug_screenshot(self, prefix: str):
        try:
            ts = int(time.time())
            screenshot_path = HERE / f"{prefix}_debug_{ts}.png"
            self.driver.save_screenshot(str(screenshot_path))
            print(f"   📸 Screenshot: {screenshot_path}")
        except Exception as e:
            print(f"   ⚠️ Screenshot falhou: {e}")

    def cleanup(self):
        if self.driver:
            print("🧹 Fechando driver...")
            try:
                self.driver.quit()
            except:
                pass
        print("🧹 Cleanup concluído")

# ───────────────── Main ─────────────────
def main():
    print(f"🧪 TESTE REAL do PostConfirmationModule para @{ACCOUNT_NAME}")
    print(f"   Visível: {VISIBLE}, Vídeo: {VIDEO_PATH}")
    print("⚠️  Este teste publica e confirma a postagem." if TRIGGER_POST else "⚠️  Este teste verifica a confirmação sem publicar.")
    if not AUTO_YES:
        input("Pressione Enter para continuar...")

    tester = PostConfirmationTester(ACCOUNT_NAME, VISIBLE, VIDEO_PATH, TRIGGER_POST)
    try:
        tester.setup()
        success = tester.run_full_test()
        print(f"\n{'✅' if success else '❌'} Teste REAL {'concluído com sucesso!' if success else 'com falhas.'}")
    except KeyboardInterrupt:
        print("\n⏹️ Teste interrompido pelo usuário.")
    except Exception as e:
        print(f"⚠️ Erro durante o teste REAL: {e}")
        traceback.print_exc()
        tester._save_debug_screenshot("error")
    finally:
        tester.cleanup()
        print("✅ Script finalizado!")

if __name__ == "__main__":
    from selenium.webdriver.common.by import By  # noqa: E402 (usado pelo quick-check)
    main()

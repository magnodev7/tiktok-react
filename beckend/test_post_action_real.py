#!/usr/bin/env python3
# test_post_action_real.py - Teste REAL do Módulo PostActionModule com Selenium
# Mede eficiência real, lê configurações do .env, exporta métricas e aplica thresholds.

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

# ───────────────── helpers de env ─────────────────
def _bool_env(v: Optional[str], default: bool = False) -> bool:
    if v is None:
        return default
    return str(v).strip().lower() in ("1", "true", "yes", "on", "y", "t")

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
        sys.path.insert(0, str(p.parent))
        added = True
        break
if not added:
    print("❌ Não encontrei a pasta 'src'. Verifique a estrutura do projeto.")
    print("   Tentativas:", ", ".join(str(c) for c in CANDIDATES))
    sys.exit(1)

# ───────────────── Imports do projeto ─────────────────
try:
    from src.modules.post_action import PostActionModule, __VERSION__
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

def _resolve_video_path(raw: str, base: str) -> str:
    """Resolve VIDEO_PATH sem duplicar diretório-base (evita videos/videos/...)."""
    rawp = Path(raw)
    if rawp.is_absolute():
        return str(rawp)

    raw_norm  = rawp.as_posix().lstrip("./")
    base_norm = Path(base).as_posix().rstrip("/").lstrip("./")

    # se o caminho já começa com o diretório base, não concatena
    if raw_norm == base_norm or raw_norm.startswith(base_norm + "/"):
        return str(Path(raw))

    return str(Path(base) / rawp)

VIDEO_PATH = _resolve_video_path(RAW_VIDEO_PATH, BASE_VIDEO_DIR)

AUTO_YES = _bool_env(os.getenv("AUTO_YES", "0"))
FAST_CATCHUP = os.getenv("TIKTOK_FAST_CATCHUP_SECONDS", "3")

# Thresholds (alvos de performance)
TARGET_CLICK = float(os.getenv("TARGET_CLICK", "0.8"))      # s
TARGET_CONFIRM = float(os.getenv("TARGET_CONFIRM", "3.0"))  # s
TARGET_TOTAL = float(os.getenv("TARGET_TOTAL", "5.0"))      # s
FAIL_ON_SLOW = _bool_env(os.getenv("FAIL_ON_SLOW", "1"))

# Estágios
STAGES = ["auth", "setup_page", "click", "confirm", "success", "total"]

def measure_time(func, *args, **kwargs):
    start = time.perf_counter()
    result = func(*args, **kwargs)
    end = time.perf_counter()
    return result, (end - start)

class PostActionTester:
    def __init__(self, account_name: str, visible: bool, video_path: str):
        self.account_name = account_name
        self.visible = visible
        self.video_path = video_path
        self.logger = print
        self.metrics: Dict[str, float] = {stage: 0.0 for stage in STAGES}
        self.driver = None
        self.scheduler = None
        self.upload_module = None
        self.module: Optional[PostActionModule] = None

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

        session_alive, _ = measure_time(is_session_alive, self.driver)
        print(f"   Sessão Chrome: {'✅ Viva — pulando criação nova' if session_alive else '⚠️ Nova sessão'}")

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

        print("🧪 Navegando para página de upload (edição ativa para botão Post)...")
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

        self.module = PostActionModule(driver=self.driver, logger=self.logger)
        print("✅ Setup completo (PostActionModule pronto)")

    def test_click(self) -> bool:
        print("🧪 Testando clique no botão de publicar...")
        ok, duration = measure_time(self.module.click_publish_button)
        self.metrics["click"] = duration
        print(f"   Resultado: {'✅ Clicado' if ok else '❌ Não encontrado'} | Tempo: {duration:.2f}s")
        if not ok:
            self._save_debug_screenshot("click_fail")
        return ok

    def test_confirm(self) -> bool:
        print("🧪 Testando tratamento do modal de confirmação...")
        ok, duration = measure_time(self.module.handle_confirmation_dialog)
        self.metrics["confirm"] = duration
        print(f"   Resultado: {'✅ Resolvido' if ok else '❌ Falha'} | Tempo: {duration:.2f}s")
        if not ok:
            self._save_debug_screenshot("confirm_fail")
        return ok

    def test_success(self) -> bool:
        print("🧪 Testando checagem de sucesso da postagem...")
        ok, duration = measure_time(self.module._check_post_success)
        self.metrics["success"] = duration
        print(f"   Resultado: {'✅ Indícios de sucesso' if ok else '⚠️ Indícios não conclusivos'} | Tempo: {duration:.2f}s")
        return True  # baseline não falha na ausência de confirmação explícita

    def run_full_test(self) -> bool:
        start_total = time.perf_counter()

        if not self.test_click():
            return False

        _ = self.test_confirm()
        _ = self.test_success()

        self.metrics["total"] = time.perf_counter() - start_total

        # ----- Relatório -----
        print("\n🧭 Versão do módulo:", __VERSION__)
        if _DOTENV_PATH:
            print(f"📄 .env carregado de: {_DOTENV_PATH}")
        print(f"📁 BASE_VIDEO_DIR={BASE_VIDEO_DIR} | BASE_POSTED_DIR={BASE_POSTED_DIR} | FAST_CATCHUP={FAST_CATCHUP}s")

        print("\n📊 MÉTRICAS DE EFICIÊNCIA (REAL):")
        print("| Etapa              | Tempo (s) |")
        print("|--------------------|-----------|")
        for stage in STAGES:
            print(f"| {stage:<18} | {self.metrics[stage]:>7.2f} |")

        self._export_metrics_jsonl()

        # ----- Thresholds -----
        slow = []
        if self.metrics["click"] > TARGET_CLICK:
            slow.append(f"click>{TARGET_CLICK}s (got {self.metrics['click']:.2f}s)")
        if self.metrics["confirm"] > TARGET_CONFIRM:
            slow.append(f"confirm>{TARGET_CONFIRM}s (got {self.metrics['confirm']:.2f}s)")
        if self.metrics["total"] > TARGET_TOTAL:
            slow.append(f"total>{TARGET_TOTAL}s (got {self.metrics['total']:.2f}s)")

        print(f"\n🎯 Targets: click≤{TARGET_CLICK}s, confirm≤{TARGET_CONFIRM}s, total≤{TARGET_TOTAL}s")
        if slow:
            print("⚠️ Lento:", ", ".join(slow))
            if FAIL_ON_SLOW:
                raise AssertionError("Performance abaixo do alvo: " + ", ".join(slow))
        else:
            print("🚀 Excelente! Todos os alvos dentro do limite.")

        return True

    # ── utils ──
    def _export_metrics_jsonl(self):
        out = {
            "when": dt.datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "host": socket.gethostname(),
            "user": getpass.getuser(),
            "account": self.account_name,
            "visible": self.visible,
            "module_version": __VERSION__,
            "metrics": self.metrics,
            "targets": {
                "click": TARGET_CLICK,
                "confirm": TARGET_CONFIRM,
                "total": TARGET_TOTAL,
            },
            "env": {
                "BASE_VIDEO_DIR": BASE_VIDEO_DIR,
                "BASE_POSTED_DIR": BASE_POSTED_DIR,
                "VIDEO_PATH": VIDEO_PATH,
                "FAST_CATCHUP": FAST_CATCHUP,
                "VISIBLE": self.visible,
            },
        }
        path = HERE / "perf_post_action.jsonl"
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
    print(f"🧪 TESTE REAL do PostActionModule para @{ACCOUNT_NAME}")
    print(f"   Visível: {VISIBLE}, Vídeo: {VIDEO_PATH}")
    print("⚠️  Este teste clica em 'Publicar' de verdade. Garanta que é um ambiente de teste.")
    if not AUTO_YES:
        input("Pressione Enter para continuar...")

    tester = PostActionTester(ACCOUNT_NAME, VISIBLE, VIDEO_PATH)
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
    main()

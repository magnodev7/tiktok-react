#!/usr/bin/env python3
# test_video_upload_real_fixed.py - Teste REAL com COOKIES/AUTH integrado
# Mede eficiência com vídeo real + sessão logada. Use conta de TESTE!
import os
import sys
import time
from pathlib import Path
from typing import Dict, Any
import traceback

# Adiciona o diretório src ao path
sys.path.insert(0, str(Path(__file__).parent / "beckend" / "src"))

try:
    from src.modules.video_upload import VideoUploadModule
    from src.driver import get_fresh_driver, is_session_alive  # Correção: src.driver, não driver_simple
    from src.cookies import load_cookies_for_account  # Do seu test_cookies.py
    from src.scheduler import TikTokScheduler  # Para USER_DATA_DIR, como no test_cookies
except ImportError as e:
    print(f"❌ Erro de import: {e}")
    print("💡 Dica: Verifique paths e requirements.txt")
    sys.exit(1)

# Configs
ACCOUNT_NAME = os.getenv("ACCOUNT_NAME", "mundoparalelodm").strip() or "mundoparalelodm"
VISIBLE = os.getenv("VISIBLE", "true").lower() in ("1", "true", "yes", "on")  # True para debug
VIDEO_PATH = os.getenv("VIDEO_PATH", "./videos/Vídeo 287.mp4")
if not VIDEO_PATH or not os.path.isfile(VIDEO_PATH):
    print(f"❌ VIDEO_PATH inválido: {VIDEO_PATH}")
    sys.exit(1)

# Constantes
STAGES = ["auth", "validate", "navigate", "send", "wait_completion", "total"]

def measure_time(func, *args, **kwargs):
    start = time.perf_counter()
    result = func(*args, **kwargs)
    end = time.perf_counter()
    return result, (end - start)

class VideoUploadTester:
    def __init__(self, account_name: str, visible: bool, video_path: str):
        self.account_name = account_name
        self.visible = visible
        self.video_path = video_path
        self.logger = print
        self.metrics: Dict[str, float] = {stage: 0.0 for stage in STAGES}
        self.driver = None
        self.module = None
        self.scheduler = None  # Para paths de cookies
    
    def setup(self):
        print(f"🔧 Configurando Driver REAL (headless={not self.visible})...")
        self.scheduler = TikTokScheduler(account_name=self.account_name, logger=self.logger, visible=False)
        self.scheduler.initial_setup()
        
        # Correção: Usa get_fresh_driver com parâmetros corretos
        self.driver = get_fresh_driver(
            None,
            profile_base_dir=self.scheduler.USER_DATA_DIR,
            account_name=self.account_name,
            headless=not self.visible,
        )
        
        # ✅ NOVO: Checa se sessão já está viva (como no test_cookies.py)
        session_alive, _ = measure_time(is_session_alive, self.driver)
        print(f"   Sessão Chrome: {'✅ Viva — pulando criação nova' if session_alive else '⚠️ Nova sessão'}")
        
        # ✅ Carrega cookies para auth
        print(f"🍪 Carregando cookies para @{self.account_name}...")
        cookies_loaded, duration_auth = measure_time(load_cookies_for_account, self.driver, self.account_name)
        self.metrics["auth"] = duration_auth
        print(f"   Cookies: {'✅ Carregados' if cookies_loaded else '❌ Falha'} | Tempo: {duration_auth:.2f}s")
        
        if not cookies_loaded:
            print("❌ Cookies ausentes/inválidos. Rode test_cookies.py primeiro!")
            self.cleanup()
            sys.exit(1)
        
        # ✅ Valida sessão navegando para perfil
        print("🧪 Validando sessão: Navegando para perfil...")
        self.driver.get(f"https://www.tiktok.com/@{self.account_name}")
        time.sleep(3)  # Aguarda load
        current_url = self.driver.current_url.lower()
        if "login" in current_url or "sign" in current_url:
            print("❌ Sessão inválida: Redirecionou para login.")
            self._save_debug_screenshot("auth_fail")
            self.cleanup()
            sys.exit(1)
        print("✅ Sessão VÁLIDA: Perfil OK!")
        
        self.module = VideoUploadModule(driver=self.driver, logger=self.logger)
        print(f"✅ Setup completo - Vídeo: {os.path.basename(self.video_path)}")
    
    def test_validate(self) -> bool:
        print(f"🧪 Testando validação: {os.path.basename(self.video_path)}")
        result, duration = measure_time(self.module.validate_video_file, self.video_path)
        self.metrics["validate"] = duration
        print(f"   Resultado: {'✅ Válido' if result else '❌ Inválido'} | Tempo: {duration:.2f}s")
        return result
    
    def test_navigate(self) -> bool:
        print("🧪 Testando navegação para página de upload...")
        result, duration = measure_time(self.module.navigate_to_upload_page)
        self.metrics["navigate"] = duration
        print(f"   Resultado: {'✅ Sucesso' if result else '❌ Falha'} | Tempo: {duration:.2f}s")
        if result:
            print(f"   URL final: {self.driver.current_url}")
        else:
            self._save_debug_screenshot("navigate_fail")
            # NOVO: Retry uma vez
            print("🔄 Tentando retry na navegação...")
            time.sleep(2)
            result_retry, duration_retry = measure_time(self.module.navigate_to_upload_page)
            if result_retry:
                print("✅ Retry OK!")
                self.metrics["navigate"] += duration_retry
                return True
        return result
    
    def test_send(self) -> bool:
        print(f"🧪 Testando envio REAL: {os.path.basename(self.video_path)}")
        result_send, duration_send = measure_time(self.module.send_video_file, self.video_path, retry=True)
        self.metrics["send"] = duration_send
        
        if result_send:
            print(f"   Envio: ✅ OK | Tempo: {duration_send:.2f}s")
            result_wait, duration_wait = measure_time(self.module.wait_upload_completion, timeout=300)
            self.metrics["wait_completion"] = duration_wait
            print(f"   Espera: {'✅ Concluído' if result_wait else '⚠️ Timeout'} | Tempo: {duration_wait:.2f}s")
            return result_send and result_wait
        else:
            print(f"   Envio: ❌ Falha | Tempo: {duration_send:.2f}s")
            self._save_debug_screenshot("send_fail")
            return False
    
    def run_full_test(self) -> bool:
        start_total = time.perf_counter()
        
        if not self.test_validate():
            return False
        
        if not self.test_navigate():
            return False
        
        if not self.test_send():
            return False
        
        end_total = time.perf_counter()
        self.metrics["total"] = end_total - start_total
        
        print(f"\n📊 MÉTRICAS DE EFICIÊNCIA (REAL + AUTH):")
        print("| Etapa              | Tempo (s) |")
        print("|--------------------|-----------|")
        for stage in STAGES:
            print(f"| {stage:<18} | {self.metrics[stage]:>7.2f} |")
        
        total_time = self.metrics["total"]
        print(f"\n🎯 Eficiência Geral: {total_time:.2f}s (inclui auth)")
        if total_time < 180:
            print("🚀 Excelente! (<3min)")
        elif total_time < 300:
            print("✅ Bom! (3-5min)")
        else:
            print("⚠️ Otimizar (ex.: polling em wait)")
        
        return True
    
    def _save_debug_screenshot(self, prefix: str):
        try:
            timestamp = int(time.time())
            screenshot_path = Path(__file__).parent / f"{prefix}_debug_{timestamp}.png"
            self.driver.save_screenshot(str(screenshot_path))
            print(f"   📸 Screenshot: {screenshot_path}")
        except Exception as e:
            print(f"   ⚠️ Screenshot falhou: {e}")
    
    def cleanup(self):
        if self.driver:
            self.driver.quit()
        print("🧹 Cleanup OK")

def main():
    print(f"🧪 TESTE REAL + AUTH para @{ACCOUNT_NAME} | Vídeo: {VIDEO_PATH}")
    print("⚠️ UPLOAD REAL! Conta teste. Ctrl+C para cancelar.")
    input("Enter para continuar...")
    
    tester = VideoUploadTester(ACCOUNT_NAME, VISIBLE, VIDEO_PATH)
    
    try:
        tester.setup()
        success = tester.run_full_test()
        print(f"\n{'✅' if success else '❌'} Teste {'sucesso!' if success else 'falhas.'}")
        if not success:
            print("💡 Cheque screenshots/logs/TikTok.")
    except KeyboardInterrupt:
        print("\n⏹️ Interrompido.")
    except Exception as e:
        print(f"⚠️ Erro: {e}")
        traceback.print_exc()
        if tester.driver:
            tester._save_debug_screenshot("error")
    finally:
        tester.cleanup()
        print("✅ Finalizado!")

if __name__ == "__main__":
    main()
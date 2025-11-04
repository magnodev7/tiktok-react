#!/usr/bin/env python3
# test_description_handler_real_fixed.py - Teste REAL fixado para estado pós-upload
# Mede eficiência com texto real. Use após setup ou com upload dummy.
import os
import sys
import time
from pathlib import Path
from typing import Dict, Any
import traceback

# Adiciona o diretório src ao path
sys.path.insert(0, str(Path(__file__).parent / "beckend" / "src"))

try:
    from src.modules.description_handler import DescriptionModule
    from src.driver import get_fresh_driver, is_session_alive
    from src.cookies import load_cookies_for_account
    from src.scheduler import TikTokScheduler
    from src.modules.video_upload import VideoUploadModule
except ImportError as e:
    print(f"❌ Erro de import: {e}")
    print("💡 Dica: Verifique paths e requirements.txt")
    sys.exit(1)

# Configs
ACCOUNT_NAME = os.getenv("ACCOUNT_NAME", "mundoparalelodm").strip() or "mundoparalelodm"
VISIBLE = os.getenv("VISIBLE", "true").lower() in ("1", "true", "yes", "on")
DESCRIPTION_TEXT = os.getenv("DESCRIPTION_TEXT", "Meu vídeo #viral 🚀 com emojis e texto longo para teste de sanitização e truncamento se necessário.")
VIDEO_PATH = os.getenv("VIDEO_PATH", "./videos/Vídeo 287.mp4")  # Use real ou dummy para upload

# Constantes
STAGES = ["auth", "setup_page", "prepare", "fill", "verify", "handle_full", "total"]

def measure_time(func, *args, **kwargs):
    start = time.perf_counter()
    result = func(*args, **kwargs)
    end = time.perf_counter()
    return result, (end - start)

class DescriptionHandlerTester:
    def __init__(self, account_name: str, visible: bool, desc_text: str, video_path: str):
        self.account_name = account_name
        self.visible = visible
        self.desc_text = desc_text
        self.video_path = video_path
        self.logger = print
        self.metrics: Dict[str, float] = {stage: 0.0 for stage in STAGES}
        self.driver = None
        self.module = None
        self.scheduler = None
        self.upload_module = None
    
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
        
        # Checa sessão
        session_alive, _ = measure_time(is_session_alive, self.driver)
        print(f"   Sessão Chrome: {'✅ Viva' if session_alive else '⚠️ Nova'}")
        
        # Carrega cookies
        print(f"🍪 Carregando cookies para @{self.account_name}...")
        cookies_loaded, duration_auth = measure_time(load_cookies_for_account, self.driver, self.account_name)
        self.metrics["auth"] = duration_auth
        print(f"   Cookies: {'✅ Carregados' if cookies_loaded else '❌ Falha'} | Tempo: {duration_auth:.2f}s")
        
        if not cookies_loaded:
            print("❌ Cookies inválidos. Rode test_cookies.py!")
            self.cleanup()
            sys.exit(1)
        
        # Valida sessão
        print("🧪 Validando sessão: Navegando para perfil...")
        self.driver.get(f"https://www.tiktok.com/@{self.account_name}")
        time.sleep(3)
        current_url = self.driver.current_url.lower()
        if "login" in current_url or "sign" in current_url:
            print("❌ Sessão inválida.")
            self._save_debug_screenshot("auth_fail")
            self.cleanup()
            sys.exit(1)
        print("✅ Sessão VÁLIDA!")
        
        # FIX: Setup página de edição (upload dummy para ativar campo descrição)
        print("🧪 Setup página de edição (upload dummy)...")
        self.upload_module = VideoUploadModule(driver=self.driver, logger=self.logger)
        nav_success, duration_nav = measure_time(self.upload_module.navigate_to_upload_page)
        self.metrics["setup_page"] = duration_nav
        
        if nav_success:
            # Upload dummy (use vídeo real ou skip se já em edição)
            if os.path.isfile(self.video_path):
                upload_success, duration_upload = measure_time(self.upload_module.send_video_file, self.video_path, retry=True)
                if upload_success:
                    print("✅ Upload dummy OK – campo descrição ativo")
                else:
                    print("⚠️ Upload falhou; tentando manual para edição")
                    self.driver.refresh()
                    time.sleep(5)
            else:
                print("⚠️ Sem vídeo; assumindo edição manual (rode upload primeiro)")
        else:
            print("⚠️ Navegação falhou; use página manual de upload")
        
        self.module = DescriptionModule(driver=self.driver, logger=self.logger)
        print(f"✅ Setup completo - Texto: '{self.desc_text[:50]}...'")
    
    def test_prepare(self) -> bool:
        print(f"🧪 Testando preparação: '{self.desc_text[:50]}...'")
        result, duration = measure_time(self.module.prepare_description, self.desc_text)
        self.metrics["prepare"] = duration
        print(f"   Resultado: '{result[:50]}...' | Tempo: {duration:.2f}s | Len: {len(result)}")
        return bool(result)
    
    def test_fill(self) -> bool:
        print("🧪 Testando preenchimento...")
        prepared = self.module.prepare_description(self.desc_text)
        result, duration = measure_time(self.module.fill_description, prepared, required=True)
        self.metrics["fill"] = duration
        print(f"   Resultado: {'✅ Preenchido' if result else '❌ Falha'} | Tempo: {duration:.2f}s")
        if not result:
            self._save_debug_screenshot("fill_fail")
        return result
    
    def test_verify(self) -> bool:
        print("🧪 Testando verificação...")
        result, duration = measure_time(self.module.verify_description_filled, self.desc_text)
        self.metrics["verify"] = duration
        print(f"   Resultado: {'✅ Verificado' if result else '❌ Difere'} | Tempo: {duration:.2f}s")
        return result
    
    def test_handle_full(self) -> bool:
        print("🧪 Testando fluxo completo...")
        # Limpa antes
        self.module.clear_description()
        result, duration = measure_time(self.module.handle_description, self.desc_text, required=True, verify=True)
        self.metrics["handle_full"] = duration
        print(f"   Resultado: {'✅ Sucesso' if result else '❌ Falha'} | Tempo: {duration:.2f}s")
        return result
    
    def run_full_test(self) -> bool:
        start_total = time.perf_counter()
        
        if not self.test_prepare():
            return False
        
        if not self.test_fill():
            return False
        
        if not self.test_verify():
            return False
        
        # Limpa e full
        self.module.clear_description()
        if not self.test_handle_full():
            return False
        
        end_total = time.perf_counter()
        self.metrics["total"] = end_total - start_total
        
        print(f"\n📊 MÉTRICAS DE EFICIÊNCIA (REAL):")
        print("| Etapa              | Tempo (s) |")
        print("|--------------------|-----------|")
        for stage in STAGES:
            print(f"| {stage:<18} | {self.metrics[stage]:>7.2f} |")
        
        total_time = self.metrics["total"]
        print(f"\n🎯 Eficiência Geral: {total_time:.2f}s")
        if total_time < 5:
            print("🚀 Excelente! (<5s)")
        elif total_time < 10:
            print("✅ Bom! (5-10s)")
        else:
            print("⚠️ Lento (>10s) – Otimizar waits/JS")
        
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
    print(f"🧪 TESTE REAL do DescriptionModule para @{ACCOUNT_NAME} | Texto: '{DESCRIPTION_TEXT[:50]}...'")
    print("⚠️ Preenche REAL! Rode após upload ou com VIDEO_PATH. Ctrl+C cancelar.")
    input("Enter para continuar...")
    
    tester = DescriptionHandlerTester(ACCOUNT_NAME, VISIBLE, DESCRIPTION_TEXT, VIDEO_PATH)
    
    try:
        tester.setup()
        success = tester.run_full_test()
        print(f"\n{'✅' if success else '❌'} Teste {'sucesso!' if success else 'falhas.'}")
        if not success:
            print("💡 Cheque screenshots/logs/TikTok (campo preenchido?).")
            tester._save_debug_screenshot("error")
    
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
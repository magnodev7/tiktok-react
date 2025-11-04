#!/usr/bin/env python3
# test_audience_selector_real.py - Teste REAL do Módulo AudienceModule com Selenium
# Mede eficiência com configuração real. ATENÇÃO: Use após upload (página de edição ativa).
# Requer: Conta logada, página em /upload ou studio/upload.
import os
import sys
import time
from pathlib import Path
from typing import Dict, Any
from enum import Enum
import traceback

# Adiciona o diretório src ao path
sys.path.insert(0, str(Path(__file__).parent / "beckend" / "src"))

try:
    from src.modules.audience_selector import AudienceModule, AudienceType
    from src.driver import get_fresh_driver, is_session_alive
    from src.cookies import load_cookies_for_account
    from src.scheduler import TikTokScheduler
    from src.modules.video_upload import VideoUploadModule  # Para navegar e ativar página de edição
except ImportError as e:
    print(f"❌ Erro de import: {e}")
    print("💡 Dica: Verifique paths e requirements.txt")
    sys.exit(1)

# Configurações do teste (REAL)
ACCOUNT_NAME = os.getenv("ACCOUNT_NAME", "mundoparalelodm").strip() or "mundoparalelodm"
VISIBLE = os.getenv("VISIBLE", "true").lower() in ("1", "true", "yes", "on")
AUDIENCE_TYPE = os.getenv("AUDIENCE_TYPE", "PUBLIC").upper()  # PUBLIC, FRIENDS, PRIVATE
VIDEO_PATH = os.getenv("VIDEO_PATH", "./videos/Vídeo 287.mp4")  # Para ativar edição

# Constantes para medição de eficiência
STAGES = ["auth", "setup_page", "detect", "set", "verify", "handle_full", "total"]

def measure_time(func, *args, **kwargs):
    """Medidor de tempo - retorna (resultado, tempo_segundos)"""
    start = time.perf_counter()
    result = func(*args, **kwargs)
    end = time.perf_counter()
    return result, (end - start)

class AudienceSelectorTester:
    """Classe para orquestrar testes REAL do módulo"""
    
    def __init__(self, account_name: str, visible: bool, audience_type: AudienceType, video_path: str):
        self.account_name = account_name
        self.visible = visible
        self.audience_type = audience_type
        self.video_path = video_path
        self.logger = print
        self.metrics: Dict[str, float] = {stage: 0.0 for stage in STAGES}
        self.driver = None
        self.module = None
        self.scheduler = None
        self.upload_module = None  # Para setup página
    
    def setup(self):
        """Configura driver REAL e módulo"""
        print(f"🔧 Configurando Driver REAL (headless={not self.visible})...")
        self.scheduler = TikTokScheduler(account_name=self.account_name, logger=self.logger, visible=False)
        self.scheduler.initial_setup()
        
        self.driver = get_fresh_driver(
            None,
            profile_base_dir=self.scheduler.USER_DATA_DIR,
            account_name=self.account_name,
            headless=not self.visible,
        )
        
        # Checa se sessão viva
        session_alive, _ = measure_time(is_session_alive, self.driver)
        print(f"   Sessão Chrome: {'✅ Viva — pulando criação nova' if session_alive else '⚠️ Nova sessão'}")
        
        # Carrega cookies
        print(f"🍪 Carregando cookies para @{self.account_name}...")
        cookies_loaded, duration_auth = measure_time(load_cookies_for_account, self.driver, self.account_name)
        self.metrics["auth"] = duration_auth
        print(f"   Cookies: {'✅ Carregados' if cookies_loaded else '❌ Falha'} | Tempo: {duration_auth:.2f}s")
        
        if not cookies_loaded:
            print("❌ Cookies ausentes. Rode test_cookies.py primeiro!")
            self.cleanup()
            sys.exit(1)
        
        # Valida sessão navegando para perfil
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
        
        # Setup: Navega para upload e ativa edição (para ter selector de audiência)
        print("🧪 Navegando para página de upload para teste de audiência...")
        self.upload_module = VideoUploadModule(driver=self.driver, logger=self.logger)
        nav_success, duration_nav = measure_time(self.upload_module.navigate_to_upload_page)
        self.metrics["setup_page"] = duration_nav
        
        if nav_success:
            if os.path.isfile(self.video_path):
                upload_success, duration_upload = measure_time(self.upload_module.send_video_file, self.video_path, retry=True)
                if upload_success:
                    print("✅ Upload dummy OK – selector de audiência ativo")
                else:
                    print("⚠️ Upload falhou; tentando manual para edição")
                    self.driver.refresh()
                    time.sleep(5)
            else:
                print("⚠️ Sem vídeo; assumindo edição manual (rode upload primeiro)")
        else:
            print("⚠️ Navegação falhou; use página manual de upload")
        
        self.module = AudienceModule(driver=self.driver, logger=self.logger)
        print(f"✅ Setup completo - Tipo: {self.audience_type.value}")
    
    def test_detect(self) -> bool:
        """Testa detect_current_audience"""
        print("🧪 Testando detecção de audiência atual...")
        result, duration = measure_time(self.module.detect_current_audience)
        self.metrics["detect"] = duration
        print(f"   Resultado: {'✅ Detectado: ' + str(result) if result else '❌ Não detectado'} | Tempo: {duration:.2f}s")
        return result is not None
    
    def test_set(self) -> bool:
        """Testa set_audience (com required=True)"""
        print(f"🧪 Testando set_audience para {self.audience_type.value}...")
        result, duration = measure_time(self.module.set_audience, self.audience_type, required=True)
        self.metrics["set"] = duration
        print(f"   Resultado: {'✅ Definido' if result else '❌ Falha'} | Tempo: {duration:.2f}s")
        if not result:
            self._save_debug_screenshot("set_fail")
        return result
    
    def test_verify(self) -> bool:
        """Testa verify_audience"""
        print(f"🧪 Testando verify_audience para {self.audience_type.value}...")
        result, duration = measure_time(self.module.verify_audience, self.audience_type)
        self.metrics["verify"] = duration
        print(f"   Resultado: {'✅ Verificado' if result else '❌ Difere'} | Tempo: {duration:.2f}s")
        return result
    
    def test_handle_full(self) -> bool:
        """Teste end-to-end: handle_audience (full flow)"""
        print(f"🧪 Testando fluxo completo: handle_audience para {self.audience_type.value}...")
        result, duration = measure_time(self.module.handle_audience, self.audience_type, required=True, verify=True)
        self.metrics["handle_full"] = duration
        print(f"   Resultado: {'✅ Sucesso' if result else '❌ Falha'} | Tempo: {duration:.2f}s")
        return result
    
    def run_full_test(self) -> bool:
        """Teste end-to-end: detect + set + verify + full handle"""
        start_total = time.perf_counter()
        
        if not self.test_detect():
            return False
        
        if not self.test_set():
            return False
        
        if not self.test_verify():
            return False
        
        # Reset para full (muda para PUBLIC, depois volta)
        self.module.set_audiences(AudienceType.PUBLIC)
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
            print("🚀 Excelente! (<5s - eficiente)")
        elif total_time < 10:
            print("✅ Bom! (5-10s - otimizável)")
        else:
            print("⚠️ Lento (>10s) - Foque em locate/retries")
        
        return True
    
    def _save_debug_screenshot(self, prefix: str):
        """Salva screenshot para debug"""
        try:
            timestamp = int(time.time())
            screenshot_path = Path(__file__).parent / f"{prefix}_debug_{timestamp}.png"
            self.driver.save_screenshot(str(screenshot_path))
            print(f"   📸 Screenshot: {screenshot_path}")
        except Exception as e:
            print(f"   ⚠️ Screenshot falhou: {e}")
    
    def cleanup(self):
        """Limpa recursos REAL"""
        if self.driver:
            print("🧹 Fechando driver...")
            self.driver.quit()
        print("🧹 Cleanup concluído")

def main():
    try:
        audience_str = AUDIENCE_TYPE
        if audience_str not in ["PUBLIC", "FRIENDS", "PRIVATE"]:
            print(f"❌ AUDIENCE_TYPE inválido: {audience_str}. Use PUBLIC, FRIENDS ou PRIVATE.")
            sys.exit(1)
        audience_type = AudienceType[audience_str]
    except KeyError:
        print(f"❌ AUDIENCE_TYPE inválido: {AUDIENCE_TYPE}")
        sys.exit(1)
    
    print(f"🧪 TESTE REAL do AudienceModule para @{ACCOUNT_NAME}")
    print(f"   Visível: {VISIBLE}, Tipo: {audience_type.value}, Vídeo: {VIDEO_PATH}")
    print("⚠️  Configura audiência REAL no TikTok! Use após upload. Ctrl+C para cancelar.")
    input("Pressione Enter para continuar...")
    
    tester = AudienceSelectorTester(ACCOUNT_NAME, VISIBLE, audience_type, VIDEO_PATH)
    
    try:
        tester.setup()
        success = tester.run_full_test()
        print(f"\n{'✅' if success else '❌'} Teste REAL {'concluído com sucesso!' if success else 'com falhas.'}")
        
        if not success:
            print("💡 Debug: Verifique screenshots, logs e TikTok (audiência configurada?).")
            tester._save_debug_screenshot("error")
    
    except KeyboardInterrupt:
        print("\n⏹️ Teste interrompido pelo usuário.")
    except Exception as e:
        print(f"⚠️ Erro durante o teste REAL: {e}")
        traceback.print_exc()
        if tester.driver:
            tester._save_debug_screenshot("error")
    
    finally:
        tester.cleanup()
        print("✅ Script finalizado!")

if __name__ == "__main__":
    main()
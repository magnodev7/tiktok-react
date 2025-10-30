#!/usr/bin/env python3
"""
Script de teste para o sistema SIMPLIFICADO de upload

Testa:
- driver_simple.py (100 linhas vs 481)
- cookies_simple.py (50 linhas vs 573)
- uploader_simple.py (300 linhas vs 1116)

Uso:
    python3 test_simple_uploader.py <account_name> <video_path> [description]

Exemplo:
    python3 test_simple_uploader.py minha_conta video.mp4 "Meu vídeo #fyp"
"""
import sys
import os
import time
from pathlib import Path

# Adiciona src ao path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from driver_simple import build_driver_simple, get_or_create_driver
from cookies_simple import load_cookies_simple
from uploader_simple import TikTokUploaderSimple


def test_simple_upload(account_name: str, video_path: str, description: str = ""):
    """
    Testa upload completo com sistema simplificado.

    Args:
        account_name: Nome da conta TikTok
        video_path: Caminho do vídeo
        description: Descrição do vídeo

    Returns:
        True se sucesso, False caso contrário
    """
    print("=" * 60)
    print("🧪 TESTE DO SISTEMA SIMPLIFICADO DE UPLOAD")
    print("=" * 60)
    print(f"📱 Conta: {account_name}")
    print(f"📹 Vídeo: {video_path}")
    print(f"📝 Descrição: {description[:50]}..." if len(description) > 50 else description)
    print("=" * 60)

    driver = None
    success = False

    try:
        # 1. Cria driver SIMPLES (sem locks, sem perfis persistentes)
        print("\n🔧 PASSO 1: Criando driver...")
        start_time = time.time()
        driver = build_driver_simple(headless=True)
        driver_time = time.time() - start_time
        print(f"✅ Driver criado em {driver_time:.2f}s")

        # 2. Carrega cookies SIMPLES (sem normalização complexa)
        print("\n🍪 PASSO 2: Carregando cookies...")
        start_time = time.time()
        cookies_ok = load_cookies_simple(driver, account_name)
        cookies_time = time.time() - start_time

        if not cookies_ok:
            print(f"❌ Falha ao carregar cookies em {cookies_time:.2f}s")
            return False
        print(f"✅ Cookies carregados em {cookies_time:.2f}s")

        # 3. Upload SIMPLES (sem retry complexo, timeouts menores)
        print("\n📤 PASSO 3: Fazendo upload...")
        start_time = time.time()

        uploader = TikTokUploaderSimple(driver)
        upload_ok = uploader.post_video(video_path, description)

        upload_time = time.time() - start_time

        if upload_ok:
            print(f"✅ Upload completo em {upload_time:.2f}s")
            success = True
        else:
            print(f"❌ Upload falhou após {upload_time:.2f}s")
            success = False

        # Tira screenshot final
        screenshot_path = f"test_simple_upload_{account_name}_{int(time.time())}.png"
        try:
            driver.save_screenshot(screenshot_path)
            print(f"📸 Screenshot salvo: {screenshot_path}")
        except:
            pass

    except KeyboardInterrupt:
        print("\n⚠️ Interrompido pelo usuário")
        success = False

    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        success = False

    finally:
        # Fecha driver
        if driver:
            print("\n🔚 Encerrando driver...")
            try:
                # Aguarda 5s antes de fechar (para debug visual se não headless)
                time.sleep(5)
                driver.quit()
                print("✅ Driver encerrado")
            except Exception as e:
                print(f"⚠️ Erro ao encerrar driver: {e}")

    print("\n" + "=" * 60)
    if success:
        print("🎉 TESTE PASSOU - Sistema simplificado funciona!")
    else:
        print("❌ TESTE FALHOU - Verificar logs acima")
    print("=" * 60)

    return success


def main():
    """Função principal"""
    if len(sys.argv) < 3:
        print("Uso: python3 test_simple_uploader.py <account_name> <video_path> [description]")
        print("\nExemplo:")
        print('  python3 test_simple_uploader.py minha_conta video.mp4 "Meu vídeo #fyp"')
        sys.exit(1)

    account_name = sys.argv[1]
    video_path = sys.argv[2]
    description = sys.argv[3] if len(sys.argv) > 3 else ""

    # Verifica se vídeo existe
    if not os.path.isfile(video_path):
        print(f"❌ Arquivo não encontrado: {video_path}")
        sys.exit(1)

    # Executa teste
    success = test_simple_upload(account_name, video_path, description)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

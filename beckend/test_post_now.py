#!/usr/bin/env python3
"""
Script para forçar postagem imediata de um vídeo
"""
import sys
sys.path.insert(0, 'src')

from src.driver import build_driver
from src.database import SessionLocal
from src.repositories import TikTokAccountRepository
from src.cookies import load_cookies_for_account
import time
import os
from pathlib import Path

def post_video_now():
    """Força postagem de um vídeo agora"""
    print("=" * 60)
    print("🎬 TESTE DE POSTAGEM MANUAL")
    print("=" * 60)

    account_name = "novadigitalbra"
    video_dir = Path("./videos") / account_name

    # Lista vídeos disponíveis
    if not video_dir.exists():
        print(f"❌ Diretório não existe: {video_dir}")
        return False

    videos = list(video_dir.glob("*.mp4"))
    if not videos:
        print(f"❌ Nenhum vídeo encontrado em: {video_dir}")
        return False

    video_file = videos[0]
    print(f"📹 Vídeo selecionado: {video_file.name}")
    print(f"📊 Tamanho: {video_file.stat().st_size / 1024 / 1024:.2f} MB")

    # Busca metadados
    json_file = video_file.with_suffix('.json')
    if json_file.exists():
        import json
        with open(json_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
            print(f"📝 Título: {metadata.get('title', 'N/A')}")
            hashtags = metadata.get('hashtags', [])
            if isinstance(hashtags, list):
                print(f"🏷️  Tags: {', '.join(hashtags)}")
            else:
                print(f"🏷️  Tags: {hashtags}")

    print("\n" + "=" * 60)
    print("🔧 INICIANDO SELENIUM E LOGIN")
    print("=" * 60)

    # Cria driver
    driver = build_driver()

    try:
        # Faz login
        print(f"🔐 Fazendo login como: {account_name}")
        login_success = load_cookies_for_account(driver, account_name)

        if not login_success:
            print("❌ Falha no login!")
            return False

        print("✅ Login bem-sucedido!")

        # Acessa Creator Studio
        print("\n" + "=" * 60)
        print("🎬 ACESSANDO CREATOR STUDIO")
        print("=" * 60)

        upload_url = "https://www.tiktok.com/creator-center/upload"
        print(f"🌐 Navegando para: {upload_url}")
        driver.get(upload_url)
        time.sleep(5)

        current_url = driver.current_url
        print(f"📍 URL atual: {current_url}")

        if "login" in current_url.lower():
            print("❌ Redirecionou para login - autenticação falhou")
            return False

        print("✅ Página de upload carregada!")

        # Procura input de arquivo
        print("\n" + "=" * 60)
        print("📤 PROCURANDO INPUT DE UPLOAD")
        print("=" * 60)

        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC

        try:
            # Aguarda input de arquivo aparecer
            file_input = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='file']"))
            )
            print("✅ Input de arquivo encontrado!")

            # Envia arquivo
            print(f"📤 Enviando arquivo: {video_file}")
            file_input.send_keys(str(video_file.absolute()))
            print("✅ Arquivo enviado!")

            # Aguarda upload
            print("⏳ Aguardando processamento do upload...")
            time.sleep(10)

            # Tenta encontrar campos de texto
            print("\n" + "=" * 60)
            print("📝 PREENCHENDO METADADOS")
            print("=" * 60)

            # Aguarda um pouco mais
            time.sleep(5)

            print("✅ Upload em processo!")
            print("\n⚠️  MODO MANUAL ATIVADO")
            print("👉 O vídeo foi enviado, mas você precisa:")
            print("   1. Verificar o título e descrição")
            print("   2. Adicionar hashtags se necessário")
            print("   3. Configurar privacidade")
            print("   4. Clicar em 'Postar'")
            print("\n⏸️  Mantendo navegador aberto por 60 segundos...")

            time.sleep(60)

            print("✅ Teste concluído!")
            return True

        except Exception as e:
            print(f"❌ Erro ao fazer upload: {e}")
            import traceback
            traceback.print_exc()
            return False

    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        print("\n🔒 Fechando navegador...")
        driver.quit()

if __name__ == "__main__":
    success = post_video_now()
    sys.exit(0 if success else 1)

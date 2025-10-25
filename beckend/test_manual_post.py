#!/usr/bin/env python3
"""
Script de teste manual para forçar o post de um vídeo.
Usado para testar a criação da pasta profiles/ e persistência de login.
"""
import sys
from pathlib import Path
from src.scheduler import TikTokScheduler

def main():
    print("🧪 TESTE MANUAL: Forçando post de vídeo...")
    print("=" * 60)

    scheduler = TikTokScheduler(account_name="novadigitalbra")

    # Coleta vídeos pending
    video_dir = Path(scheduler.VIDEO_DIR)
    pending_videos = []

    for f in sorted(video_dir.glob("*.mp4")):
        meta_path = f.with_suffix(".json")
        if meta_path.exists():
            import json
            try:
                with open(meta_path) as fp:
                    meta = json.load(fp)
                    if meta.get("status") != "posted" and not meta.get("posted_at"):
                        pending_videos.append(f)
            except:
                pass

    if not pending_videos:
        print("❌ Nenhum vídeo pending encontrado!")
        return 1

    # Pega o primeiro vídeo pending
    video_path = pending_videos[0]
    print(f"\n📹 Vídeo selecionado: {video_path.name}")
    print(f"📂 Path completo: {video_path}")

    # Verifica se pasta profiles existe ANTES
    profiles_dir = Path("./profiles/novadigitalbra")
    print(f"\n🔍 Verificando profiles ANTES do post:")
    print(f"   Existe? {profiles_dir.exists()}")

    # Força o post
    print(f"\n🚀 Iniciando post forçado...")
    try:
        success = scheduler._post_one(str(video_path))
        if success:
            print(f"\n✅ Post concluído com sucesso!")
        else:
            print(f"\n⚠️ Post retornou False (pode ter falhado)")
    except Exception as e:
        print(f"\n❌ Erro durante post: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Verifica se pasta profiles existe DEPOIS
    print(f"\n🔍 Verificando profiles DEPOIS do post:")
    print(f"   Existe? {profiles_dir.exists()}")
    if profiles_dir.exists():
        print(f"   Conteúdo:")
        for item in profiles_dir.rglob("*"):
            if item.is_file():
                size = item.stat().st_size
                print(f"      {item.relative_to(profiles_dir)} ({size} bytes)")

    print("\n" + "=" * 60)
    print("✅ TESTE CONCLUÍDO!")
    return 0

if __name__ == "__main__":
    sys.exit(main())

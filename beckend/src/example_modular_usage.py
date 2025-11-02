"""
Exemplo de uso da arquitetura modular do TikTok Uploader

Este script demonstra:
1. Uso básico do uploader modular (compatível com versão antiga)
2. Uso avançado com controle granular por módulo
3. Testes individuais de módulos
"""
import os
import sys

# Adiciona diretório atual ao path para imports
sys.path.insert(0, os.path.dirname(__file__))

from uploader_modular import TikTokUploader
from modules.description_handler import DescriptionModule
from modules.audience_selector import AudienceModule, AudienceType
from modules.file_manager import FileManagerModule


def exemplo_basico(driver):
    """
    Exemplo básico: uso simples do uploader (compatível com código antigo)
    """
    print("\n" + "="*80)
    print("EXEMPLO 1: Uso Básico (Compatível com Código Antigo)")
    print("="*80)

    # Cria uploader (mesma interface da versão antiga)
    uploader = TikTokUploader(
        driver=driver,
        logger=print,
        account_name="teste"
    )

    # Posta vídeo com um único método
    video_path = "/path/to/video.mp4"
    description = "Descrição do vídeo #viral"

    success = uploader.post_video(
        video_path=video_path,
        description=description
    )

    if success:
        print("✅ Vídeo postado com sucesso!")

        # Finaliza (move para pasta 'posted')
        uploader.finalize_successful_post(
            video_path=video_path,
            posted_dir="/posted/teste"
        )
    else:
        print("❌ Falha ao postar vídeo")

        # Limpa lock
        uploader.cleanup_failed_post(video_path)


def exemplo_avancado(driver):
    """
    Exemplo avançado: controle granular etapa por etapa
    """
    print("\n" + "="*80)
    print("EXEMPLO 2: Uso Avançado (Controle Granular)")
    print("="*80)

    uploader = TikTokUploader(driver, logger=print)

    video_path = "/path/to/video.mp4"

    # ETAPA 1: Upload
    print("\n🔹 Etapa 1: Upload do vídeo")
    if not uploader.go_to_upload():
        print("❌ Falha ao acessar página de upload")
        return False

    if not uploader.send_file(video_path):
        print("❌ Falha no upload")
        return False

    # ETAPA 2: Descrição
    print("\n🔹 Etapa 2: Descrição")
    description_text = "Meu vídeo incrível #viral #tiktok"
    uploader.fill_description(description_text)

    # ETAPA 3: Audiência (usando módulo diretamente)
    print("\n🔹 Etapa 3: Audiência")
    uploader.audience_module.handle_audience(
        audience_type=AudienceType.PUBLIC,
        required=False,
        verify=True
    )

    # ETAPA 4: Publicar
    print("\n🔹 Etapa 4: Publicar")
    if not uploader.click_publish():
        print("❌ Falha ao clicar em publicar")
        return False

    # ETAPA 5: Modais
    print("\n🔹 Etapa 5: Lidar com modais")
    uploader.handle_confirmation_dialog()

    # ETAPA 6: Verificar violações
    print("\n🔹 Etapa 6: Verificar violações")
    if uploader.post_action_module.detect_content_violation():
        print("❌ Vídeo rejeitado por violação de conteúdo")
        return False

    # ETAPA 7: Confirmar postagem
    print("\n🔹 Etapa 7: Confirmar postagem")
    if uploader.confirm_posted():
        print("✅ Vídeo confirmado como postado!")

        # Imprime status detalhado
        uploader.print_status()
        return True
    else:
        print("⚠️ Postagem não confirmada")
        return False


def exemplo_modulos_individuais(driver):
    """
    Exemplo: testando módulos individualmente
    """
    print("\n" + "="*80)
    print("EXEMPLO 3: Testes de Módulos Individuais")
    print("="*80)

    # MÓDULO DE DESCRIÇÃO
    print("\n📝 Testando DescriptionModule:")
    desc_module = DescriptionModule(driver, logger=print)

    # Testa sanitização
    dirty_text = "Texto com emoji 🚀 e caracteres\x00 inválidos"
    clean_text = desc_module.sanitize_description(dirty_text)
    print(f"  Original: {repr(dirty_text)}")
    print(f"  Limpo: {repr(clean_text)}")

    # Testa validação de comprimento
    long_text = "a" * 3000
    is_valid, adjusted = desc_module.validate_description_length(long_text)
    print(f"  Texto longo: {len(long_text)} chars")
    print(f"  Válido: {is_valid}")
    print(f"  Ajustado: {len(adjusted)} chars")

    # MÓDULO DE AUDIÊNCIA
    print("\n👥 Testando AudienceModule:")
    audience_module = AudienceModule(driver, logger=print)

    # Detecta audiência atual
    current = audience_module.detect_current_audience()
    print(f"  Audiência atual: {current}")

    # MÓDULO DE GERENCIAMENTO DE ARQUIVOS
    print("\n📁 Testando FileManagerModule:")
    fm = FileManagerModule(logger=print)

    # Testa operações com JSON
    test_data = {"title": "Meu vídeo", "tags": ["viral", "tiktok"]}
    json_path = "/tmp/test_metadata.json"

    if fm.write_json(json_path, test_data):
        print(f"  JSON escrito: {json_path}")

        read_data = fm.read_json(json_path)
        print(f"  JSON lido: {read_data}")

        fm.delete_json(json_path)
        print(f"  JSON deletado")

    # Testa listagem de vídeos
    videos_dir = "/videos/teste"
    if os.path.isdir(videos_dir):
        videos = fm.list_videos_in_directory(videos_dir)
        print(f"  Vídeos encontrados: {len(videos)}")
        for video in videos[:3]:  # Mostra primeiros 3
            size_mb = fm.get_file_size_mb(video)
            print(f"    - {os.path.basename(video)} ({size_mb} MB)")


def exemplo_migracao_gradual():
    """
    Exemplo: migração gradual do código antigo para modular
    """
    print("\n" + "="*80)
    print("EXEMPLO 4: Migração Gradual")
    print("="*80)

    # Configuração flexível via variável de ambiente
    USE_MODULAR = os.getenv("USE_MODULAR_UPLOADER", "false").lower() == "true"

    print(f"USE_MODULAR_UPLOADER={USE_MODULAR}")

    if USE_MODULAR:
        print("✅ Usando uploader_modular.py (nova arquitetura)")
        from uploader_modular import TikTokUploader
    else:
        print("⚠️ Usando uploader.py (versão antiga)")
        from uploader import TikTokUploader

    # Código funciona com ambas as versões!
    # (assumindo que driver está disponível)
    # uploader = TikTokUploader(driver, logger=print)
    # uploader.post_video("/path/to/video.mp4", "Descrição")


def exemplo_controle_fino():
    """
    Exemplo: controle fino de cada módulo
    """
    print("\n" + "="*80)
    print("EXEMPLO 5: Controle Fino por Módulo")
    print("="*80)

    # Simula controle fino sem driver (apenas demonstração)

    print("\n1️⃣ Upload Module:")
    print("   - Valida arquivo antes de enviar")
    print("   - Localiza campo em main page ou iframes")
    print("   - Monitora progresso em tempo real")
    print("   - Aguarda processamento completo")

    print("\n2️⃣ Description Module:")
    print("   - Remove emojis inválidos automaticamente")
    print("   - Trunca texto se > 2200 chars")
    print("   - Tenta JavaScript primeiro, send_keys como fallback")
    print("   - Pode verificar se foi preenchido corretamente")

    print("\n3️⃣ Audience Module:")
    print("   - Detecta audiência atual")
    print("   - Suporta: PUBLIC, FRIENDS, PRIVATE")
    print("   - Multi-idioma (PT, EN, ES)")
    print("   - Pode verificar após definir")

    print("\n4️⃣ Post Action Module:")
    print("   - 15+ seletores robustos para botão publicar")
    print("   - Fecha modais de bloqueio automaticamente")
    print("   - Detecta violações de conteúdo")
    print("   - Retry automático se necessário")
    print("   - Salva screenshots de debug")

    print("\n5️⃣ Confirmation Module:")
    print("   - Verifica URL mudou")
    print("   - Verifica botão sumiu")
    print("   - Detecta mensagens de sucesso")
    print("   - Monitora progresso com timeout")
    print("   - Fornece status detalhado")

    print("\n6️⃣ File Manager Module:")
    print("   - Operações seguras com JSON")
    print("   - Move/copia vídeos")
    print("   - Gerencia locks de postagem")
    print("   - Limpa arquivos após falha/sucesso")
    print("   - Lista vídeos em diretórios")


def main():
    """
    Função principal para demonstração
    """
    print("\n" + "="*80)
    print("DEMONSTRAÇÃO: Arquitetura Modular TikTok Uploader")
    print("="*80)

    print("\nEste script demonstra 5 formas de usar a arquitetura modular:")
    print("  1. Uso básico (compatível com código antigo)")
    print("  2. Uso avançado (controle granular)")
    print("  3. Testes de módulos individuais")
    print("  4. Migração gradual")
    print("  5. Controle fino por módulo")

    print("\n⚠️ NOTA: Exemplos 1, 2 e 3 requerem WebDriver ativo")
    print("         Rodando apenas exemplos 4 e 5 (sem WebDriver)")

    # Exemplos que não precisam de driver
    exemplo_migracao_gradual()
    exemplo_controle_fino()

    print("\n" + "="*80)
    print("✅ Demonstração concluída!")
    print("="*80)

    print("\n📚 Para mais informações, consulte:")
    print("   - beckend/src/modules/README.md")
    print("   - beckend/src/uploader_modular.py")


if __name__ == "__main__":
    # Se você tiver um WebDriver ativo, pode rodar todos os exemplos:
    #
    # from driver_simple import build_driver
    # driver = build_driver(headless=True)
    # exemplo_basico(driver)
    # exemplo_avancado(driver)
    # exemplo_modulos_individuais(driver)
    # driver.quit()

    # Por enquanto, roda apenas exemplos sem WebDriver
    main()

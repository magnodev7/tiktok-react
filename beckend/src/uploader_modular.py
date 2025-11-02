"""
Uploader MODULAR para TikTok
Refatoração do uploader.py usando arquitetura modular

MUDANÇAS:
- 6 módulos independentes (upload, description, audience, post_action, confirmation, file_manager)
- Mesma interface pública (100% compatível com código existente)
- Fácil manutenção e testes individuais por módulo
- Separação clara de responsabilidades
"""
import os
from typing import Optional

# Importa módulos especializados
from modules.video_upload import VideoUploadModule
from modules.description_handler import DescriptionModule
from modules.audience_selector import AudienceModule, AudienceType
from modules.post_action import PostActionModule
from modules.post_confirmation import PostConfirmationModule
from modules.file_manager import FileManagerModule


class TikTokUploader:
    """
    Uploader MODULAR para TikTok.
    Mantém interface compatível com sistema antigo, mas usa arquitetura modular internamente.

    Módulos:
    1. VideoUploadModule - Upload e validação
    2. DescriptionModule - Tratamento de descrição
    3. AudienceModule - Seleção de audiência
    4. PostActionModule - Ação de postagem
    5. PostConfirmationModule - Confirmação de postagem
    6. FileManagerModule - Gerenciamento de arquivos
    """

    def __init__(
        self,
        driver,
        logger=None,
        debug_dir=None,
        cookies_path=None,
        account_name=None,
        reuse_existing_session=True,
        **kwargs  # Ignora outros parâmetros para compatibilidade
    ):
        """
        Inicializa o uploader modular.

        Args:
            driver: WebDriver do Selenium
            logger: Logger (opcional)
            debug_dir: Ignorado (compatibilidade)
            cookies_path: Ignorado (compatibilidade)
            account_name: Nome da conta (opcional)
            reuse_existing_session: Ignorado (compatibilidade)
            **kwargs: Ignorados (compatibilidade)
        """
        self.driver = driver
        self.log = logger.info if logger and hasattr(logger, 'info') else (logger if logger else print)
        self.account_name = account_name

        # Inicializa módulos
        self.upload_module = VideoUploadModule(driver, logger=self.log)
        self.description_module = DescriptionModule(driver, logger=self.log)
        self.audience_module = AudienceModule(driver, logger=self.log)
        self.post_action_module = PostActionModule(driver, logger=self.log)
        self.confirmation_module = PostConfirmationModule(driver, logger=self.log)
        self.file_manager = FileManagerModule(logger=self.log)

        # Compatibilidade com código antigo
        self._file_input_context = None

    # ===================== MÉTODOS PÚBLICOS (Interface Compatível) =====================

    def go_to_upload(self) -> bool:
        """
        Navega para página de upload.
        DELEGADO para VideoUploadModule.

        Returns:
            True se conseguiu, False caso contrário
        """
        return self.upload_module.navigate_to_upload_page()

    def send_file(self, video_path: str) -> bool:
        """
        Envia arquivo de vídeo.
        DELEGADO para VideoUploadModule.

        Args:
            video_path: Caminho do vídeo

        Returns:
            True se enviou, False caso contrário
        """
        return self.upload_module.send_video_file(video_path, retry=True)

    def fill_description(self, text: str) -> bool:
        """
        Preenche descrição.
        DELEGADO para DescriptionModule.

        Args:
            text: Texto da descrição

        Returns:
            True se preencheu ou não era obrigatório, False caso contrário
        """
        return self.description_module.fill_description(text, required=False)

    def set_audience_public(self) -> bool:
        """
        Define audiência como pública.
        DELEGADO para AudienceModule.

        Returns:
            True sempre (não trava se não achar)
        """
        return self.audience_module.set_public(required=False)

    def click_publish(self) -> bool:
        """
        Clica no botão de publicar.
        DELEGADO para PostActionModule.

        Returns:
            True se clicou, False caso contrário
        """
        return self.post_action_module.click_publish_button()

    def handle_confirmation_dialog(self) -> bool:
        """
        Lida com modal de confirmação.
        DELEGADO para PostActionModule.

        Returns:
            True se lidou ou não apareceu, False se falhou
        """
        return self.post_action_module.handle_confirmation_dialog()

    def confirm_posted(self) -> bool:
        """
        Confirma se vídeo foi publicado.
        DELEGADO para PostConfirmationModule.

        Returns:
            True se publicou, False caso contrário
        """
        return self.confirmation_module.confirm_posted(timeout=60, quick_check=False)

    # ===================== MÉTODO PRINCIPAL =====================

    def post_video(self, video_path: str, description: str = "") -> bool:
        """
        Publica vídeo completo (fluxo modular).

        Args:
            video_path: Caminho do vídeo
            description: Descrição do vídeo

        Returns:
            True se publicou, False caso contrário
        """
        self.log(f"📹 Iniciando publicação: {os.path.basename(video_path)}")

        # MÓDULO 1: Upload e Validação
        self.log("🔹 Etapa 1/6: Upload do vídeo")
        if not self.go_to_upload():
            self.log("❌ Falha ao acessar página de upload")
            return False

        if not self.send_file(video_path):
            self.log("🔁 Tentando enviar novamente...")
            if not self.send_file(video_path):
                self.log("❌ Falha no upload após retry")
                return False

        # MÓDULO 2: Tratamento da Descrição
        self.log("🔹 Etapa 2/6: Preenchimento da descrição")
        if description:
            self.fill_description(description)
        else:
            self.log("ℹ️ Sem descrição fornecida")

        # MÓDULO 3: Seleção de Audiência
        self.log("🔹 Etapa 3/6: Configuração de audiência")
        self.set_audience_public()

        # MÓDULO 4: Ação de Postagem
        self.log("🔹 Etapa 4/6: Publicação")
        if not self.click_publish():
            self.log("❌ Falha ao clicar em publicar")
            return False

        # MÓDULO 4.5: Gerenciamento de Modais
        self.log("🔹 Etapa 4.5/6: Gerenciamento de modais")
        self.handle_confirmation_dialog()

        # MÓDULO 4.6: Detecção de Violações
        self.log("🔹 Etapa 4.6/6: Verificação de violações")
        if self.post_action_module.detect_content_violation():
            self.log("❌ Vídeo rejeitado por violação de conteúdo")
            return False

        # MÓDULO 4.7: Retry se modal "exit" foi fechado
        if self.post_action_module.is_on_upload_page():
            self.log("🔁 Ainda na página de upload, tentando publicar novamente...")
            if self.click_publish():
                self.log("✅ Segundo clique em publicar executado")
                self.handle_confirmation_dialog()

        # MÓDULO 5: Confirmação de Postagem
        self.log("🔹 Etapa 5/6: Confirmação de postagem")
        if self.confirm_posted():
            self.log("🎉 Vídeo publicado com sucesso!")
            return True
        else:
            self.log("⚠️ Publicação não confirmada (pode ter sido publicado)")
            return False

    # ===================== MÉTODOS AUXILIARES PÚBLICOS =====================

    def get_post_status(self) -> dict:
        """
        Obtém status detalhado da postagem.
        DELEGADO para PostConfirmationModule.

        Returns:
            Dicionário com informações de status
        """
        return self.confirmation_module.get_post_status()

    def print_status(self):
        """
        Imprime status detalhado (debug).
        DELEGADO para PostConfirmationModule.
        """
        self.confirmation_module.print_status()

    # ===================== MÉTODOS PARA GERENCIAMENTO DE ARQUIVOS =====================

    def create_lock(self, video_path: str) -> bool:
        """
        Cria lock de postagem.
        DELEGADO para FileManagerModule.
        """
        return self.file_manager.create_lock(video_path)

    def remove_lock(self, video_path: str) -> bool:
        """
        Remove lock de postagem.
        DELEGADO para FileManagerModule.
        """
        return self.file_manager.remove_lock(video_path)

    def finalize_successful_post(self, video_path: str, posted_dir: str) -> bool:
        """
        Finaliza postagem bem-sucedida movendo para pasta 'posted'.
        DELEGADO para FileManagerModule.
        """
        return self.file_manager.finalize_successful_post(
            video_path=video_path,
            posted_dir=posted_dir,
            keep_original=False
        )

    def cleanup_failed_post(self, video_path: str) -> bool:
        """
        Limpa arquivos de postagem que falhou.
        DELEGADO para FileManagerModule.
        """
        return self.file_manager.cleanup_failed_post(video_path)

    # ===================== COMPATIBILIDADE COM CÓDIGO LEGADO =====================

    # Propriedades/métodos que código antigo pode usar
    @property
    def _wait_element(self):
        """Compatibilidade: acesso ao método do módulo de upload"""
        return self.upload_module._wait_element

    @property
    def _wait_visible(self):
        """Compatibilidade: acesso ao método do módulo de descrição"""
        return self.description_module._wait_visible

    @property
    def _wait_clickable(self):
        """Compatibilidade: acesso ao método do módulo de ação"""
        return self.post_action_module._wait_clickable

    # Métodos estáticos para compatibilidade
    @staticmethod
    def _normalize_text(text: str) -> str:
        """Compatibilidade: normalização de texto"""
        from modules.video_upload import VideoUploadModule
        return VideoUploadModule._normalize_text(text)

    @staticmethod
    def _shorten_text(text: str) -> str:
        """Compatibilidade: encurtamento de texto"""
        from modules.video_upload import VideoUploadModule
        return VideoUploadModule._shorten_text(text)


# ===================== FUNÇÕES DE COMPATIBILIDADE =====================

def create_uploader(driver, logger=None, account_name=None, **kwargs):
    """
    Factory function para criar uploader.
    Facilita migração de código antigo.

    Args:
        driver: WebDriver
        logger: Logger (opcional)
        account_name: Nome da conta
        **kwargs: Argumentos adicionais ignorados

    Returns:
        Instância de TikTokUploader
    """
    return TikTokUploader(
        driver=driver,
        logger=logger,
        account_name=account_name,
        **kwargs
    )

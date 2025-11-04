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
import time
from typing import Optional

# Importa módulos especializados
from .modules.video_upload import VideoUploadModule
from .modules.description_handler import DescriptionModule
from .modules.audience_selector import AudienceModule, AudienceType
from .modules.post_action import PostActionModule
from .modules.post_confirmation import (
    PostConfirmationModule,
    CONFIRMATION_TIMEOUT,
    ConfirmationStatus,
)
from .modules.file_manager import FileManagerModule
from .modules.duplicate_protection import DuplicateProtectionModule


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
    7. DuplicateProtectionModule - Proteção contra duplicatas
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
        self.duplicate_protection = DuplicateProtectionModule(logger=self.log)

        # Compatibilidade com código antigo
        self._file_input_context = None

    # ===================== MÉTODOS PÚBLICOS (Interface Compatível) =====================

    def go_to_upload(self) -> bool:
        """Navega para página de upload (VideoUploadModule)."""
        return self.upload_module.navigate_to_upload_page()

    def send_file(self, video_path: str) -> bool:
        """Envia arquivo de vídeo (VideoUploadModule)."""
        return self.upload_module.send_video_file(video_path, retry=True)

    def fill_description(self, text: str) -> bool:
        """Preenche descrição (DescriptionModule)."""
        return self.description_module.fill_description(text, required=False)

    def set_audience_public(self) -> bool:
        """Define audiência pública (AudienceModule)."""
        return self.audience_module.set_public(required=False)

    def click_publish(self) -> bool:
        """Clica em publicar (PostActionModule)."""
        return self.post_action_module.click_publish_button()

    def handle_confirmation_dialog(self) -> bool:
        """Lida com modal de confirmação (PostActionModule)."""
        return self.post_action_module.handle_confirmation_dialog()

    def confirm_posted(self) -> bool:
        """
        Compatibilidade LEGACY: retorna bool.
        Internamente, usa wait_for_confirmation (estrito) do Módulo 5.
        """
        return self.confirmation_module.wait_for_confirmation(timeout=CONFIRMATION_TIMEOUT)

    # ===================== MÉTODO PRINCIPAL =====================

    def post_video(self, video_path: str, description: str = "", posted_dir: Optional[str] = None) -> bool:
        """
        Publica vídeo completo (fluxo modular com proteção contra duplicatas).

        Args:
            video_path: Caminho do vídeo
            description: Descrição do vídeo
            posted_dir: Diretório posted (para verificação de duplicatas)

        Returns:
            True se publicou, False caso contrário
        """
        self.log(f"📹 Iniciando publicação: {os.path.basename(video_path)}")
        if not posted_dir:
            posted_dir = "./posted"

        # MÓDULO 0: Proteção contra Duplicatas (VERIFICAÇÃO PRÉVIA)
        self.log("🔹 Etapa 0/7: Verificação de duplicatas")
        can_post, reason = self.duplicate_protection.can_post_video(video_path, posted_dir)
        if not can_post:
            self.log(f"❌ Vídeo bloqueado: {reason}")
            return False

        # MÓDULO 0.5: Cria lock de postagem (PROTEÇÃO ATÔMICA)
        if not self.duplicate_protection.create_posting_lock(video_path):
            self.log("❌ Falha ao criar lock (race condition detectada)")
            return False

        try:
            # MÓDULO 1: Upload e Validação
            self.log("🔹 Etapa 1/7: Upload do vídeo")
            if not self.go_to_upload():
                self.log("❌ Falha ao acessar página de upload")
                self.duplicate_protection.remove_posting_lock(video_path)
                return False

            if not self.send_file(video_path):
                self.log("🔁 Tentando enviar novamente...")
                if not self.send_file(video_path):
                    self.log("❌ Falha no upload após retry")
                    self.duplicate_protection.remove_posting_lock(video_path)
                    return False

            # MÓDULO 2: Tratamento da Descrição
            self.log("🔹 Etapa 2/7: Preenchimento da descrição")
            if description:
                self.fill_description(description)
            else:
                self.log("ℹ️ Sem descrição fornecida")

            # MÓDULO 3: Seleção de Audiência
            self.log("🔹 Etapa 3/7: Configuração de audiência")
            self.set_audience_public()

            # MÓDULO 4: Ação de Postagem
            self.log("🔹 Etapa 4/7: Publicação")
            if not self.click_publish():
                self.log("❌ Falha ao clicar em publicar")
                self.duplicate_protection.remove_posting_lock(video_path)
                return False

            # MÓDULO 4.5: Gerenciamento de Modais
            self.log("🔹 Etapa 4.5/7: Gerenciamento de modais")
            self.handle_confirmation_dialog()

            # MÓDULO 4.6: Detecção de Violações
            self.log("🔹 Etapa 4.6/7: Verificação de violações")
            if hasattr(self.post_action_module, "detect_content_violation") and self.post_action_module.detect_content_violation():
                self.log("❌ Vídeo rejeitado por violação de conteúdo")
                self.duplicate_protection.remove_posting_lock(video_path)
                return False

            # MÓDULO 4.7: Retry se ainda estiver na tela de upload
            if hasattr(self.post_action_module, "is_on_upload_page") and self.post_action_module.is_on_upload_page():
                self.log("🔁 Ainda na página de upload, tentando publicar novamente...")
                if self.click_publish():
                    self.log("✅ Segundo clique em publicar executado")
                    self.handle_confirmation_dialog()

            # Pequeno buffer de estabilidade da UI
            self.log("⏳ Aguardando confirmação final do TikTok...")
            time.sleep(5)

            # MÓDULO 5: Confirmação de Postagem (ESTRITA)
            self.log("🔹 Etapa 5/7: Confirmação de postagem")
            # Usa API nova (ConfirmationResult). Se não existir, cai para o wrapper bool.
            result = None
            if hasattr(self.confirmation_module, "confirm_posted"):
                try:
                    result = self.confirmation_module.confirm_posted(timeout=CONFIRMATION_TIMEOUT, strict=True, quick_check=False)
                except TypeError:
                    # Versões antigas podem ter assinatura diferente
                    result = self.confirmation_module.confirm_posted(timeout=CONFIRMATION_TIMEOUT)
            # Fallback legacy
            if result is None or not hasattr(result, "status"):
                ok_bool = self.confirmation_module.wait_for_confirmation(timeout=CONFIRMATION_TIMEOUT)
                if ok_bool:
                    result_status = ConfirmationStatus.PUBLISHED
                else:
                    result_status = ConfirmationStatus.UNKNOWN
            else:
                result_status = result.status

            if result_status == ConfirmationStatus.PUBLISHED:
                self.log("🎉 Vídeo publicado com sucesso!")

                # MÓDULO 6: Marca como postado e remove lock
                self.log("🔹 Etapa 6/7: Finalização")
                self.duplicate_protection.finalize_post_operation(
                    video_path=video_path,
                    success=True,
                    mark_as_posted=True,
                    remove_lock=True
                )
                return True

            elif result_status == ConfirmationStatus.SUBMITTED:
                self.log("ℹ️ Post submetido/under review — não mover/deletar ainda.")
                self.duplicate_protection.remove_posting_lock(video_path)
                return False

            else:  # UNKNOWN
                self.log("⚠️ Publicação não confirmada (UNKNOWN).")
                self.duplicate_protection.remove_posting_lock(video_path)
                return False

        except Exception as e:
            self.log(f"❌ Erro durante postagem: {e}")
            self.duplicate_protection.remove_posting_lock(video_path)
            return False

    # ===================== MÉTODOS AUXILIARES PÚBLICOS =====================

    def get_post_status(self) -> dict:
        """Status detalhado da postagem (PostConfirmationModule)."""
        return self.confirmation_module.get_post_status()

    def print_status(self):
        """Imprime status detalhado (debug)."""
        self.confirmation_module.print_status()

    # ===================== GERENCIAMENTO DE ARQUIVOS =====================

    def create_lock(self, video_path: str) -> bool:
        """Cria lock (FileManagerModule)."""
        return self.file_manager.create_lock(video_path)

    def remove_lock(self, video_path: str) -> bool:
        """Remove lock (FileManagerModule)."""
        return self.file_manager.remove_lock(video_path)

    def finalize_successful_post(self, video_path: str, posted_dir: str) -> bool:
        """Finaliza postagem movendo para 'posted' (FileManagerModule)."""
        return self.file_manager.finalize_successful_post(
            video_path=video_path,
            posted_dir=posted_dir,
            keep_original=False
        )

    def cleanup_failed_post(self, video_path: str) -> bool:
        """Limpa artefatos de falha (FileManagerModule)."""
        return self.file_manager.cleanup_failed_post(video_path)

    # ===================== COMPATIBILIDADE COM CÓDIGO LEGADO =====================

    @property
    def _wait_element(self):
        """Compatibilidade: método do módulo de upload"""
        return self.upload_module._wait_element

    @property
    def _wait_visible(self):
        """Compatibilidade: método do módulo de descrição"""
        return self.description_module._wait_visible

    @property
    def _wait_clickable(self):
        """Compatibilidade: método do módulo de ação"""
        return self.post_action_module._wait_clickable

    @staticmethod
    def _normalize_text(text: str) -> str:
        """Compatibilidade: normalização de texto"""
        from .modules.video_upload import VideoUploadModule
        return VideoUploadModule._normalize_text(text)

    @staticmethod
    def _shorten_text(text: str) -> str:
        """Compatibilidade: encurtamento de texto"""
        from .modules.video_upload import VideoUploadModule
        return VideoUploadModule._shorten_text(text)


# ===================== FUNÇÃO FACTORY =====================

def create_uploader(driver, logger=None, account_name=None, **kwargs):
    """
    Factory function para criar uploader (compatibilidade).
    """
    return TikTokUploader(
        driver=driver,
        logger=logger,
        account_name=account_name,
        **kwargs
    )

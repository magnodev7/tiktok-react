"""
Módulos do sistema de postagem TikTok
Arquitetura modular para facilitar manutenção e testes
"""

from .video_upload import VideoUploadModule
from .description_handler import DescriptionModule
from .audience_selector import AudienceModule
from .post_action import PostActionModule
from .post_confirmation import PostConfirmationModule
from .file_manager import FileManagerModule
from .duplicate_protection import DuplicateProtectionModule

__all__ = [
    "VideoUploadModule",
    "DescriptionModule",
    "AudienceModule",
    "PostActionModule",
    "PostConfirmationModule",
    "FileManagerModule",
    "DuplicateProtectionModule",
]

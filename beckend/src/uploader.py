"""
uploader.py - Wrapper de compatibilidade para uploader_modular

MIGRAÇÃO COMPLETA PARA ARQUITETURA MODULAR

Este arquivo é um wrapper/alias que importa a versão modular.
Mantém 100% de compatibilidade com código existente.

Para código novo, use diretamente:
    from uploader_modular import TikTokUploader

Histórico:
- uploader.py (original): 1032 linhas monolíticas
- uploader_modular.py (novo): 400 linhas + 7 módulos independentes
- uploader.py (este arquivo): 15 linhas (wrapper)

Data da migração: 2025-11-02
"""

# Importa TUDO da versão modular
from uploader_modular import *  # noqa: F401, F403

# Mantém compatibilidade total
TikTokUploader = TikTokUploader  # noqa: F405
create_uploader = create_uploader  # noqa: F405

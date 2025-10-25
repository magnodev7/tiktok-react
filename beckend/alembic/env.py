"""Alembic environment configuration - Configuração Profissional"""

from logging.config import fileConfig
import os
import sys
from pathlib import Path

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# ==========================================
# Configuração de Path e Imports
# ==========================================

# Adiciona o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Importa a Base do SQLAlchemy
from src.database import Base

# ⚠️ IMPORTANTE: Importar TODOS os models aqui para que o Alembic os detecte
# Isso garante que todas as tabelas sejam consideradas nas migrações
from src.models import (
    User,
    APIKey,
    Schedule,
    VideoUploadLog,
    TikTokAccount,
    PostingSchedule,
    SystemLog,  # Novo modelo de logs
    # Adicione novos models aqui conforme necessário
)

# ==========================================
# Configuração do Alembic
# ==========================================

# Config object do Alembic (valores do alembic.ini)
config = context.config

# Sobrescreve a URL do banco de dados com variável de ambiente
# Prioridade: DATABASE_URL (env) > alembic.ini > fallback padrão
database_url = os.getenv("DATABASE_URL")

if not database_url:
    # Tenta pegar do alembic.ini
    database_url = config.get_main_option("sqlalchemy.url")

if not database_url or database_url.strip() == "":
    # Fallback: tenta detectar ambiente
    if os.path.exists("/.dockerenv"):
        # Rodando no Docker
        database_url = "postgresql://tiktok:tiktok123@postgres:5432/tiktok_db"
    else:
        # Rodando localmente
        database_url = "postgresql://tiktok:tiktok123@localhost:5432/tiktok_db"

    print(f"⚠️  DATABASE_URL não configurada. Usando fallback: {database_url}")

config.set_main_option("sqlalchemy.url", database_url)

# Configuração de logging do Python
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# MetaData alvo para autogenerate (detecta mudanças nos models)
target_metadata = Base.metadata

# ==========================================
# Funções de Migração
# ==========================================

def run_migrations_offline() -> None:
    """
    Executa migrações em modo 'offline'.
    
    Gera scripts SQL sem conexão ao banco.
    Útil para ambientes sem acesso direto ao banco de dados.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,  # Detecta mudanças de tipo de coluna
        compare_server_default=True,  # Detecta mudanças de valores default
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Executa migrações em modo 'online'.
    
    Conecta ao banco de dados e executa as migrações diretamente.
    Modo padrão para desenvolvimento e produção.
    """
    
    # Configuração do engine com connection pooling desabilitado
    # (recomendado para migrações)
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,  # Detecta mudanças de tipo de coluna
            compare_server_default=True,  # Detecta mudanças de valores default
            render_as_batch=False,  # Desabilitado (apenas para SQLite)
        )

        with context.begin_transaction():
            context.run_migrations()


# ==========================================
# Execução
# ==========================================

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

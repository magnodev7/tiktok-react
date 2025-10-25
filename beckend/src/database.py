"""
Configuração do banco de dados PostgreSQL com SQLAlchemy
"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()


def get_db_url():
    """
    Obtém a URL do banco de dados com fallback inteligente

    Prioridade:
    1. Variável de ambiente DATABASE_URL
    2. Detecta se está no Docker
    3. Usa localhost como fallback
    """
    db_url = os.getenv("DATABASE_URL")

    if not db_url:
        # Detecta se está rodando no Docker
        if os.path.exists("/.dockerenv"):
            db_url = "postgresql://tiktok:tiktok123@postgres:5432/tiktok_db"
        else:
            db_url = "postgresql://tiktok:tiktok123@localhost:5432/tiktok_db"

    return db_url


# URL de conexão do banco de dados
DATABASE_URL = get_db_url()

# Engine do SQLAlchemy
# Para ambiente de produção, usar pool de conexões adequado
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # Verifica conexões antes de usar
    echo=False,  # Mude para True para debug SQL
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base para os models
Base = declarative_base()


# Dependency para FastAPI
def get_db():
    """
    Dependency que fornece uma sessão de banco de dados
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Inicializa o banco de dados criando todas as tabelas
    """
    import src.models  # Importa os models para registrar
    Base.metadata.create_all(bind=engine)

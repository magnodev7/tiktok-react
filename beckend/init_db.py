#!/usr/bin/env python3
"""
Script de Inicialização Robusta do Banco de Dados
==================================================

Este script garante que o banco de dados seja inicializado corretamente
em qualquer ambiente (desenvolvimento, produção, Docker, VPS, etc.).

Uso:
    python init_db.py [--reset]

Opções:
    --reset: Remove todas as tabelas e recria do zero (CUIDADO!)

Autor: Sistema TikTok React
Data: 2025-10
"""

import os
import sys
import time
import argparse
from pathlib import Path

# Adiciona o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import OperationalError, ProgrammingError
from alembic.config import Config
from alembic import command

from src.database import Base, get_db_url
from src.models import User, APIKey, Schedule, VideoUploadLog, TikTokAccount, PostingSchedule, SystemLog


def print_status(message: str, status: str = "info"):
    """Imprime mensagem formatada com status"""
    colors = {
        "info": "\033[94m",      # Azul
        "success": "\033[92m",   # Verde
        "warning": "\033[93m",   # Amarelo
        "error": "\033[91m",     # Vermelho
        "reset": "\033[0m"       # Reset
    }

    symbols = {
        "info": "ℹ",
        "success": "✓",
        "warning": "⚠",
        "error": "✗"
    }

    color = colors.get(status, colors["info"])
    symbol = symbols.get(status, "•")

    print(f"{color}{symbol} {message}{colors['reset']}")


def wait_for_database(engine, max_retries=30, delay=2):
    """Aguarda o banco de dados ficar disponível"""
    print_status("Aguardando banco de dados ficar disponível...", "info")

    for i in range(max_retries):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print_status("Banco de dados está disponível!", "success")
            return True
        except OperationalError as e:
            if i < max_retries - 1:
                print_status(
                    f"Tentativa {i + 1}/{max_retries} falhou. Tentando novamente em {delay}s...",
                    "warning"
                )
                time.sleep(delay)
            else:
                print_status(
                    f"Não foi possível conectar ao banco após {max_retries} tentativas",
                    "error"
                )
                print_status(f"Erro: {str(e)}", "error")
                return False

    return False


def check_alembic_version(engine):
    """Verifica se a tabela alembic_version existe"""
    inspector = inspect(engine)
    return 'alembic_version' in inspector.get_table_names()


def get_current_revision(engine):
    """Obtém a revisão atual do Alembic"""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version_num FROM alembic_version LIMIT 1"))
            row = result.fetchone()
            return row[0] if row else None
    except (OperationalError, ProgrammingError):
        return None


def reset_database(engine):
    """Remove todas as tabelas e recria do zero"""
    print_status("⚠️  RESETANDO BANCO DE DADOS - TODOS OS DADOS SERÃO PERDIDOS!", "warning")
    print_status("Aguardando 3 segundos... (Ctrl+C para cancelar)", "warning")
    time.sleep(3)

    try:
        # Drop alembic_version table
        with engine.connect() as conn:
            conn.execute(text("DROP TABLE IF EXISTS alembic_version CASCADE"))
            conn.commit()

        # Drop all tables
        Base.metadata.drop_all(bind=engine)
        print_status("Todas as tabelas foram removidas", "success")

    except Exception as e:
        print_status(f"Erro ao resetar banco: {str(e)}", "error")
        return False

    return True


def run_migrations():
    """Executa as migrações do Alembic"""
    try:
        # Configura o Alembic
        alembic_cfg = Config("alembic.ini")

        print_status("Executando migrações do Alembic...", "info")
        command.upgrade(alembic_cfg, "head")
        print_status("Migrações executadas com sucesso!", "success")

        return True

    except Exception as e:
        print_status(f"Erro ao executar migrações: {str(e)}", "error")
        return False


def create_initial_data(engine):
    """Cria dados iniciais se necessário"""
    from sqlalchemy.orm import Session

    try:
        with Session(engine) as session:
            # Verifica se já existe um usuário admin
            admin_exists = session.execute(
                text("SELECT 1 FROM users WHERE is_admin = true LIMIT 1")
            ).fetchone()

            if not admin_exists:
                print_status("Criando usuário admin padrão...", "info")
                from src.auth import get_password_hash

                session.execute(text("""
                    INSERT INTO users (username, email, full_name, hashed_password, is_admin, role)
                    VALUES (:username, :email, :full_name, :password, true, 'admin')
                """), {
                    "username": "admin",
                    "email": "admin@tiktok.local",
                    "full_name": "Administrador",
                    "password": get_password_hash("admin123")
                })
                session.commit()
                print_status("Usuário admin criado (username: admin, password: admin123)", "success")
                print_status("⚠️  IMPORTANTE: Altere a senha do admin após o primeiro login!", "warning")
            else:
                print_status("Usuário admin já existe", "info")

        return True

    except Exception as e:
        print_status(f"Erro ao criar dados iniciais: {str(e)}", "error")
        return False


def verify_database_schema(engine):
    """Verifica a integridade do schema do banco"""
    print_status("Verificando schema do banco de dados...", "info")

    inspector = inspect(engine)
    tables = inspector.get_table_names()

    expected_tables = [
        'users', 'api_keys', 'tiktok_accounts', 'schedules',
        'posting_schedules', 'video_upload_logs', 'system_logs',
        'user_preferences', 'alembic_version'
    ]

    missing_tables = [t for t in expected_tables if t not in tables]

    if missing_tables:
        print_status(f"Tabelas faltando: {', '.join(missing_tables)}", "error")
        return False

    print_status(f"Schema verificado: {len(tables)} tabelas encontradas", "success")
    return True


def main():
    """Função principal"""
    parser = argparse.ArgumentParser(description='Inicializa o banco de dados do TikTok React')
    parser.add_argument('--reset', action='store_true', help='Reseta o banco de dados (REMOVE TODOS OS DADOS)')
    args = parser.parse_args()

    print("\n" + "="*60)
    print("  INICIALIZAÇÃO DO BANCO DE DADOS - TikTok React")
    print("="*60 + "\n")

    # Obtém a URL do banco
    db_url = get_db_url()
    print_status(f"URL do banco: {db_url.split('@')[1] if '@' in db_url else db_url}", "info")

    # Cria engine
    try:
        engine = create_engine(db_url, echo=False)
    except Exception as e:
        print_status(f"Erro ao criar engine: {str(e)}", "error")
        sys.exit(1)

    # Aguarda banco estar disponível
    if not wait_for_database(engine):
        print_status("Falha ao conectar ao banco de dados", "error")
        sys.exit(1)

    # Reset se solicitado
    if args.reset:
        if not reset_database(engine):
            sys.exit(1)

    # Verifica se precisa executar migrações
    has_alembic = check_alembic_version(engine)
    current_revision = get_current_revision(engine)

    if not has_alembic or current_revision is None:
        print_status("Banco de dados vazio ou sem migrações. Executando setup inicial...", "info")
    else:
        print_status(f"Revisão atual do Alembic: {current_revision}", "info")

    # Executa migrações
    if not run_migrations():
        print_status("Falha ao executar migrações", "error")
        sys.exit(1)

    # Verifica schema
    if not verify_database_schema(engine):
        print_status("Schema do banco está incompleto ou inválido", "error")
        sys.exit(1)

    # Cria dados iniciais
    if not create_initial_data(engine):
        print_status("Aviso: Falha ao criar dados iniciais", "warning")

    print("\n" + "="*60)
    print_status("BANCO DE DADOS INICIALIZADO COM SUCESSO!", "success")
    print("="*60 + "\n")

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print_status("\n\nOperação cancelada pelo usuário", "warning")
        sys.exit(1)
    except Exception as e:
        print_status(f"\n\nErro inesperado: {str(e)}", "error")
        import traceback
        traceback.print_exc()
        sys.exit(1)

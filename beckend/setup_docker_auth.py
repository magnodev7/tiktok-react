#!/usr/bin/env python3
"""
Script de configuração para Docker com autenticação
"""

import os
import sys
import secrets
from pathlib import Path

def generate_jwt_secret():
    """Gera uma chave JWT segura"""
    return secrets.token_urlsafe(32)

def create_env_file():
    """Cria arquivo .env para Docker"""
    env_file = Path(".env")
    
    if env_file.exists():
        print("⚠️  Arquivo .env já existe. Fazendo backup...")
        backup_file = Path(".env.backup")
        env_file.rename(backup_file)
        print(f"✅ Backup criado: {backup_file}")
    
    # Gera chave JWT segura
    jwt_secret = generate_jwt_secret()
    
    env_content = f"""# Configurações de Autenticação
JWT_SECRET_KEY={jwt_secret}
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Configurações de Segurança
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123

# Configurações do Sistema (já existentes)
BASE_VIDEOS_DIR=./videos
BASE_POSTED_DIR=./posted
BASE_USERDATA_DIR=./user_data
BASE_STATE_DIR=./state
FRONTEND_DIR=./web
"""
    
    with open(env_file, 'w', encoding='utf-8') as f:
        f.write(env_content)
    
    print(f"✅ Arquivo .env criado com chave JWT segura")
    return jwt_secret

def create_directories():
    """Cria diretórios necessários"""
    directories = [
        "videos",
        "posted",
        "user_data",
        "state",
        "users"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✅ Diretório criado: {directory}")
    
    # Corrige permissões dos diretórios
    try:
        import os
        os.chmod("users", 0o777)
        os.chmod("state", 0o777)
        print("✅ Permissões dos diretórios corrigidas")
    except Exception as e:
        print(f"⚠️  Erro ao corrigir permissões: {e}")
        print("   As permissões serão configuradas automaticamente no container")

def main():
    print("🐳 Configurando TikTok Scheduler com Autenticação para Docker")
    print("=" * 60)
    
    # Verifica se está no diretório correto
    if not Path("docker-compose.yml").exists():
        print("❌ Execute este script no diretório raiz do projeto")
        sys.exit(1)
    
    # Cria diretórios
    print("\n📁 Criando diretórios...")
    create_directories()
    
    # Cria arquivo .env
    print("\n🔐 Configurando autenticação...")
    jwt_secret = create_env_file()
    
    # Instruções
    print("\n🚀 Próximos passos:")
    print("1. Execute: docker compose down --volumes")
    print("2. Execute: docker compose up --build")
    print("3. Acesse: http://localhost:8082/login")
    print("4. Faça login com: admin / admin123")
    
    print("\n🔒 Configurações de segurança:")
    print(f"- Chave JWT gerada: {jwt_secret[:20]}...")
    print("- Usuário admin: admin")
    print("- Senha admin: admin123 (ALTERE EM PRODUÇÃO!)")
    
    print("\n⚠️  IMPORTANTE para produção:")
    print("- Altere a senha do admin após o primeiro login")
    print("- Use HTTPS em produção")
    print("- Configure firewall adequadamente")
    print("- Faça backup do diretório ./users/")
    
    print("\n✨ Sistema configurado para Docker com sucesso!")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Script de configuração inicial do sistema de autenticação
"""

import os
import sys
from pathlib import Path

def main():
    print("🔐 Configurando sistema de autenticação TikTok Scheduler")
    print("=" * 50)
    
    # Verifica se está no diretório correto
    if not Path("src/auth.py").exists():
        print("❌ Execute este script no diretório raiz do projeto")
        sys.exit(1)
    
    # Cria diretório de usuários se não existir
    users_dir = Path("users")
    users_dir.mkdir(exist_ok=True)
    print(f"✅ Diretório de usuários criado: {users_dir}")
    
    # Verifica se o arquivo de usuários existe
    users_file = users_dir / "users.json"
    if not users_file.exists():
        print("ℹ️  Arquivo de usuários não encontrado. Será criado automaticamente no primeiro acesso.")
    
    # Verifica variáveis de ambiente
    print("\n📋 Verificando configurações:")
    
    jwt_secret = os.getenv("JWT_SECRET_KEY")
    if not jwt_secret or jwt_secret == "your-super-secret-jwt-key-change-this-in-production":
        print("⚠️  JWT_SECRET_KEY não configurado ou usando valor padrão")
        print("   Configure uma chave secreta forte em produção!")
    else:
        print("✅ JWT_SECRET_KEY configurado")
    
    admin_user = os.getenv("ADMIN_USERNAME", "admin")
    admin_pass = os.getenv("ADMIN_PASSWORD", "admin123")
    print(f"✅ Usuário admin padrão: {admin_user}")
    print(f"⚠️  Senha admin padrão: {admin_pass} (ALTERE EM PRODUÇÃO!)")
    
    # Instruções
    print("\n🚀 Próximos passos:")
    print("1. Instale as dependências: pip install -r requirements.txt")
    print("2. Configure as variáveis de ambiente (copie config.env.example)")
    print("3. Execute o servidor: python -m uvicorn src.http_health:app --reload")
    print("4. Acesse: http://localhost:8000/login")
    print("5. Faça login com as credenciais admin padrão")
    
    print("\n🔒 Segurança:")
    print("- Altere a senha do admin após o primeiro login")
    print("- Configure JWT_SECRET_KEY forte em produção")
    print("- Use HTTPS em produção")
    print("- Configure firewall adequadamente")
    
    print("\n✨ Sistema de autenticação configurado com sucesso!")

if __name__ == "__main__":
    main()

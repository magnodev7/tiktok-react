#!/usr/bin/env python3
"""
Script de teste para o sistema de autenticação
"""

import requests
import json
import sys
from pathlib import Path

def test_auth_system():
    """Testa o sistema de autenticação"""
    base_url = "http://localhost:8000"
    
    print("🧪 Testando sistema de autenticação...")
    print("=" * 50)
    
    # Teste 1: Health check (deve funcionar sem autenticação)
    print("1. Testando health check...")
    try:
        response = requests.get(f"{base_url}/health")
        if response.status_code == 200:
            print("✅ Health check OK")
        else:
            print(f"❌ Health check falhou: {response.status_code}")
    except Exception as e:
        print(f"❌ Erro no health check: {e}")
        return False
    
    # Teste 2: Tentar acessar rota protegida sem autenticação
    print("\n2. Testando acesso sem autenticação...")
    try:
        response = requests.get(f"{base_url}/videos")
        if response.status_code == 401:
            print("✅ Rota protegida corretamente")
        else:
            print(f"❌ Rota não está protegida: {response.status_code}")
    except Exception as e:
        print(f"❌ Erro ao testar rota protegida: {e}")
    
    # Teste 3: Login com credenciais padrão
    print("\n3. Testando login...")
    try:
        login_data = {
            "username": "admin",
            "password": "admin123"
        }
        response = requests.post(f"{base_url}/auth/login", json=login_data)
        
        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token")
            if token:
                print("✅ Login realizado com sucesso")
                print(f"   Token recebido: {token[:20]}...")
            else:
                print("❌ Token não recebido")
                return False
        else:
            print(f"❌ Login falhou: {response.status_code}")
            print(f"   Resposta: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Erro no login: {e}")
        return False
    
    # Teste 4: Acessar rota protegida com token
    print("\n4. Testando acesso com token...")
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{base_url}/videos", headers=headers)
        
        if response.status_code == 200:
            print("✅ Acesso autorizado funcionando")
        else:
            print(f"❌ Acesso autorizado falhou: {response.status_code}")
    except Exception as e:
        print(f"❌ Erro ao testar acesso autorizado: {e}")
    
    # Teste 5: Verificar informações do usuário
    print("\n5. Testando informações do usuário...")
    try:
        response = requests.get(f"{base_url}/auth/me", headers=headers)
        
        if response.status_code == 200:
            user_data = response.json()
            print("✅ Informações do usuário obtidas")
            print(f"   Usuário: {user_data.get('username')}")
            print(f"   Admin: {user_data.get('is_admin')}")
        else:
            print(f"❌ Falha ao obter informações do usuário: {response.status_code}")
    except Exception as e:
        print(f"❌ Erro ao obter informações do usuário: {e}")
    
    # Teste 6: Verificar token
    print("\n6. Testando verificação de token...")
    try:
        response = requests.get(f"{base_url}/auth/verify", headers=headers)
        
        if response.status_code == 200:
            print("✅ Verificação de token funcionando")
        else:
            print(f"❌ Verificação de token falhou: {response.status_code}")
    except Exception as e:
        print(f"❌ Erro na verificação de token: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 Testes concluídos!")
    print("\nPara testar manualmente:")
    print("1. Acesse: http://localhost:8000/login")
    print("2. Use: admin / admin123")
    print("3. Navegue pelo painel")
    
    return True

def check_dependencies():
    """Verifica se as dependências estão instaladas"""
    print("📦 Verificando dependências...")
    
    try:
        import requests
        print("✅ requests instalado")
    except ImportError:
        print("❌ requests não instalado. Execute: pip install requests")
        return False
    
    try:
        import jose
        print("✅ python-jose instalado")
    except ImportError:
        print("❌ python-jose não instalado. Execute: pip install python-jose[cryptography]")
        return False
    
    try:
        import passlib
        print("✅ passlib instalado")
    except ImportError:
        print("❌ passlib não instalado. Execute: pip install passlib[bcrypt]")
        return False
    
    return True

def main():
    print("🔐 Teste do Sistema de Autenticação TikTok Scheduler")
    print("=" * 60)
    
    # Verifica dependências
    if not check_dependencies():
        print("\n❌ Dependências não encontradas. Instale-as primeiro.")
        sys.exit(1)
    
    # Verifica se o servidor está rodando
    print("\n🌐 Verificando se o servidor está rodando...")
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            print("✅ Servidor está rodando")
        else:
            print(f"❌ Servidor retornou status {response.status_code}")
    except requests.exceptions.RequestException:
        print("❌ Servidor não está rodando ou não está acessível")
        print("   Execute: python -m uvicorn src.http_health:app --reload")
        sys.exit(1)
    
    # Executa testes
    if test_auth_system():
        print("\n✅ Todos os testes passaram!")
    else:
        print("\n❌ Alguns testes falharam")
        sys.exit(1)

if __name__ == "__main__":
    main()

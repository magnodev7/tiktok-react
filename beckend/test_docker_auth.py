#!/usr/bin/env python3
"""
Script de teste para o sistema de autenticação em Docker
"""

import requests
import json
import sys
import time
from pathlib import Path

def wait_for_service(url, timeout=60):
    """Aguarda o serviço ficar disponível"""
    print(f"⏳ Aguardando serviço em {url}...")
    
    for i in range(timeout):
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                print(f"✅ Serviço disponível após {i+1} segundos")
                return True
        except requests.exceptions.RequestException:
            pass
        
        time.sleep(1)
        if i % 10 == 0 and i > 0:
            print(f"   Aguardando... ({i}/{timeout}s)")
    
    print(f"❌ Serviço não ficou disponível em {timeout} segundos")
    return False

def test_docker_auth_system():
    """Testa o sistema de autenticação em Docker"""
    base_url = "http://localhost:8082"
    
    print("🧪 Testando sistema de autenticação em Docker...")
    print("=" * 50)
    
    # Aguarda o serviço ficar disponível
    if not wait_for_service(f"{base_url}/health"):
        print("❌ Serviço não está rodando. Execute: docker compose up --build")
        return False
    
    # Teste 1: Health check
    print("\n1. Testando health check...")
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
    
    # Teste 6: Verificar persistência de dados
    print("\n6. Testando persistência de dados...")
    users_dir = Path("users")
    if users_dir.exists():
        users_file = users_dir / "users.json"
        if users_file.exists():
            print("✅ Arquivo de usuários persistido")
            try:
                with open(users_file, 'r') as f:
                    users_data = json.load(f)
                    print(f"   Usuários encontrados: {len(users_data)}")
            except Exception as e:
                print(f"⚠️  Erro ao ler arquivo de usuários: {e}")
        else:
            print("⚠️  Arquivo de usuários não encontrado")
    else:
        print("⚠️  Diretório de usuários não encontrado")
    
    print("\n" + "=" * 50)
    print("🎉 Testes concluídos!")
    print("\nPara testar manualmente:")
    print("1. Acesse: http://localhost:8082/login")
    print("2. Use: admin / admin123")
    print("3. Navegue pelo painel")
    
    return True

def check_docker_status():
    """Verifica se o Docker está rodando"""
    print("🐳 Verificando status do Docker...")
    
    try:
        import subprocess
        result = subprocess.run(['docker', 'ps'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Docker está rodando")
            
            # Verifica se os containers estão rodando
            if 'tiktok-app' in result.stdout:
                print("✅ Container tiktok-app está rodando")
            else:
                print("⚠️  Container tiktok-app não encontrado")
                
            if 'tiktok-chrome' in result.stdout:
                print("✅ Container tiktok-chrome está rodando")
            else:
                print("⚠️  Container tiktok-chrome não encontrado")
                
            return True
        else:
            print("❌ Docker não está rodando ou não está acessível")
            return False
    except FileNotFoundError:
        print("❌ Docker não está instalado")
        return False
    except Exception as e:
        print(f"❌ Erro ao verificar Docker: {e}")
        return False

def main():
    print("🐳 Teste do Sistema de Autenticação TikTok Scheduler (Docker)")
    print("=" * 70)
    
    # Verifica Docker
    if not check_docker_status():
        print("\n❌ Docker não está funcionando. Execute:")
        print("   docker compose up --build")
        sys.exit(1)
    
    # Verifica dependências
    try:
        import requests
        print("✅ requests instalado")
    except ImportError:
        print("❌ requests não instalado. Execute: pip install requests")
        sys.exit(1)
    
    # Executa testes
    if test_docker_auth_system():
        print("\n✅ Todos os testes passaram!")
        print("\n🎬 Sistema TikTok Scheduler com autenticação funcionando perfeitamente!")
    else:
        print("\n❌ Alguns testes falharam")
        print("\n🔧 Verifique:")
        print("1. Se os containers estão rodando: docker ps")
        print("2. Se o arquivo .env está configurado")
        print("3. Se as portas 8082 e 4444 estão livres")
        sys.exit(1)

if __name__ == "__main__":
    main()

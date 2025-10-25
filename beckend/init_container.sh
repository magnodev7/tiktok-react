#!/bin/bash

# Script de inicialização do container
# Este script roda dentro do container para configurar permissões

echo "🔧 Configurando permissões do container..."

# Cria diretórios se não existirem
mkdir -p /app/users
mkdir -p /app/state

# Configura permissões
chmod 777 /app/users 2>/dev/null || true
chmod 777 /app/state 2>/dev/null || true

# Tenta corrigir ownership (se possível)
chown -R appuser:appuser /app/users 2>/dev/null || true
chown -R appuser:appuser /app/state 2>/dev/null || true

echo "✅ Permissões configuradas"
echo "📁 Diretórios:"
ls -la /app/ | grep -E "(users|state)"

# Testa permissões
echo "🧪 Testando permissões..."
python3 test_permissions.py 2>/dev/null || echo "⚠️  Teste de permissões não disponível"

# Executa o comando original
exec "$@"

#!/bin/bash

# Script para corrigir permissões do diretório users

echo "🔧 Corrigindo permissões do diretório users..."

# Cria o diretório se não existir
mkdir -p users

# Corrige permissões
chmod 755 users
chmod 644 users/users.json 2>/dev/null || true

# Corrige ownership (se necessário)
if [ "$EUID" -eq 0 ]; then
    echo "⚠️  Executando como root, ajustando ownership..."
    chown -R 1000:1000 users 2>/dev/null || true
fi

echo "✅ Permissões corrigidas!"
echo "📁 Diretório users: $(ls -la users/ 2>/dev/null || echo 'vazio')"

#!/bin/bash

# Script para iniciar TikTok Scheduler com autenticação em Docker

echo "🎬 TikTok Scheduler com Autenticação - Docker"
echo "=============================================="

# Verifica se Docker está instalado
if ! command -v docker &> /dev/null; then
    echo "❌ Docker não está instalado"
    exit 1
fi

# Verifica se Docker Compose está instalado
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose não está instalado"
    exit 1
fi

# Verifica se o arquivo .env existe
if [ ! -f ".env" ]; then
    echo "⚠️  Arquivo .env não encontrado"
    echo "🔧 Executando configuração inicial..."
    
    if [ -f "setup_docker_auth.py" ]; then
        python3 setup_docker_auth.py
    else
        echo "❌ Script de configuração não encontrado"
        exit 1
    fi
fi

# Verifica se os diretórios existem
echo "📁 Verificando diretórios..."
mkdir -p videos/default posted/default user_data/default state users

# Para containers existentes
echo "🛑 Parando containers existentes..."
docker compose down --volumes

# Constrói e executa
echo "🚀 Construindo e iniciando containers..."
docker compose up --build

echo "✅ Sistema iniciado!"
echo "🌐 Acesse: http://localhost:8082/login"
echo "👤 Login: admin / admin123"

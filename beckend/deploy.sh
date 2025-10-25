#!/bin/bash

# Script de Deploy para VPS
# Uso: ./deploy.sh

set -e  # Para em caso de erro

# Configurações
VPS_IP="167.234.231.63"
VPS_USER="ubuntu"
SSH_KEY="$(pwd)/ssh-key-2025-09-05.key"
REMOTE_DIR="/home/ubuntu/tiktok"
LOCAL_DIR="$HOME/Works/tiktok"

echo "🚀 Iniciando deploy para VPS..."
echo "📍 IP: $VPS_IP"
echo "👤 Usuário: $VPS_USER"
echo ""

# 1. Criar diretório no servidor
echo "📁 Criando diretório no servidor..."
ssh -i "$SSH_KEY" "$VPS_USER@$VPS_IP" "mkdir -p $REMOTE_DIR"

# 2. Transferir arquivos (excluindo diretórios pesados)
echo "📦 Transferindo arquivos..."
rsync -avz --progress \
  -e "ssh -i $SSH_KEY" \
  --exclude='videos/' \
  --exclude='posted/' \
  --exclude='user_data/' \
  --exclude='state/*.db*' \
  --exclude='__pycache__/' \
  --exclude='*.pyc' \
  --exclude='*.log' \
  --exclude='.env' \
  --exclude='venv/' \
  --exclude='env/' \
  "$LOCAL_DIR/" \
  "$VPS_USER@$VPS_IP:$REMOTE_DIR/"

echo ""
echo "✅ Arquivos transferidos com sucesso!"
echo ""
echo "🔧 Próximos passos:"
echo "1. Conecte na VPS: ssh -i $SSH_KEY $VPS_USER@$VPS_IP"
echo "2. Entre no diretório: cd $REMOTE_DIR"
echo "3. Execute o script de setup: ./setup_vps.sh"
echo ""

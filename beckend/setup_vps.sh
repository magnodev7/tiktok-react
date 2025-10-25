#!/bin/bash

# Script de Setup para VPS
# Execute este script na VPS após transferir os arquivos

set -e

echo "🔧 Configurando ambiente na VPS..."
echo ""

# 1. Atualizar sistema
echo "📦 Atualizando sistema..."
sudo apt update && sudo apt upgrade -y

# 2. Instalar dependências do sistema
echo "📦 Instalando dependências do sistema..."
sudo apt install -y \
  python3 \
  python3-pip \
  python3-venv \
  nginx \
  postgresql \
  postgresql-contrib \
  chromium-browser \
  chromium-chromedriver \
  git \
  supervisor

# 3. Criar ambiente virtual Python
echo "🐍 Criando ambiente virtual Python..."
python3 -m venv venv
source venv/bin/activate

# 4. Instalar dependências Python
echo "📚 Instalando dependências Python..."
pip install --upgrade pip
pip install -r requirements.txt

# 5. Criar diretórios necessários
echo "📁 Criando diretórios..."
mkdir -p videos posted user_data state logs

# 6. Configurar PostgreSQL
echo "🗄️ Configurando PostgreSQL..."
sudo -u postgres psql -c "CREATE DATABASE tiktok_scheduler;" || echo "Database já existe"
sudo -u postgres psql -c "CREATE USER tiktok_user WITH PASSWORD 'tiktok_pass_2025';" || echo "Usuário já existe"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE tiktok_scheduler TO tiktok_user;"

# 7. Copiar arquivo de ambiente
echo "⚙️ Configurando variáveis de ambiente..."
if [ ! -f .env ]; then
  cat > .env << 'EOF'
# Database
DATABASE_URL=postgresql://tiktok_user:tiktok_pass_2025@localhost/tiktok_scheduler

# Application
TZ=America/Sao_Paulo
FRONTEND_DIR=/home/ubuntu/tiktok/web

# Security
SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')
JWT_SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')

# Paths
BASE_VIDEOS_DIR=/home/ubuntu/tiktok/videos
BASE_POSTED_DIR=/home/ubuntu/tiktok/posted
BASE_USERDATA_DIR=/home/ubuntu/tiktok/user_data
BASE_STATE_DIR=/home/ubuntu/tiktok/state
EOF
  echo "✅ Arquivo .env criado"
else
  echo "⚠️ Arquivo .env já existe, pulando..."
fi

# 8. Executar migrações do banco de dados
echo "🗄️ Executando migrações..."
alembic upgrade head

# 9. Configurar Systemd Service
echo "⚙️ Configurando serviço systemd..."
sudo tee /etc/systemd/system/tiktok-scheduler.service > /dev/null << 'EOF'
[Unit]
Description=TikTok Scheduler Application
After=network.target postgresql.service

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/tiktok
Environment="PATH=/home/ubuntu/tiktok/venv/bin"
ExecStart=/home/ubuntu/tiktok/venv/bin/python3 tiktok_scheduler.py --cli
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 10. Configurar Nginx
echo "🌐 Configurando Nginx..."
sudo tee /etc/nginx/sites-available/tiktok-scheduler > /dev/null << 'EOF'
server {
    listen 80;
    server_name _;

    client_max_body_size 100M;

    location / {
        proxy_pass http://127.0.0.1:8082;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

# Ativar site Nginx
sudo ln -sf /etc/nginx/sites-available/tiktok-scheduler /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl restart nginx

# 11. Habilitar e iniciar serviços
echo "🚀 Habilitando serviços..."
sudo systemctl daemon-reload
sudo systemctl enable tiktok-scheduler
sudo systemctl start tiktok-scheduler
sudo systemctl enable nginx

# 12. Verificar status
echo ""
echo "✅ Setup concluído!"
echo ""
echo "📊 Status dos serviços:"
sudo systemctl status tiktok-scheduler --no-pager -l | head -20
echo ""
echo "🌐 Nginx:"
sudo systemctl status nginx --no-pager | head -10
echo ""
echo "🔗 Acesse a aplicação em: http://$VPS_IP"
echo ""
echo "📝 Comandos úteis:"
echo "  - Ver logs: sudo journalctl -u tiktok-scheduler -f"
echo "  - Reiniciar: sudo systemctl restart tiktok-scheduler"
echo "  - Parar: sudo systemctl stop tiktok-scheduler"
echo ""

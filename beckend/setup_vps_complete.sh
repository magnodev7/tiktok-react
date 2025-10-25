#!/bin/bash

# Script de Setup Completo para VPS com Traefik
# Execute este script na VPS após transferir os arquivos

set -e

echo "🔧 Configurando ambiente completo na VPS..."
echo ""

# 1. Criar ambiente virtual Python
if [ ! -d "venv" ]; then
  echo "🐍 Criando ambiente virtual Python..."
  python3 -m venv venv
fi

source venv/bin/activate

# 2. Instalar dependências Python
echo "📚 Instalando dependências Python..."
pip install --upgrade pip
pip install -r requirements.txt

# 3. Criar diretórios necessários
echo "📁 Criando diretórios..."
mkdir -p videos posted user_data state logs

# 4. Configurar PostgreSQL (limpar e recriar)
echo "🗄️ Configurando PostgreSQL..."
sudo -u postgres psql -c "DROP DATABASE IF EXISTS tiktok_scheduler;"
sudo -u postgres psql -c "CREATE DATABASE tiktok_scheduler;"
sudo -u postgres psql -c "DROP ROLE IF EXISTS tiktok_user;"
sudo -u postgres psql -c "CREATE USER tiktok_user WITH PASSWORD 'tiktok_pass_2025';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE tiktok_scheduler TO tiktok_user;"
sudo -u postgres psql -c "ALTER DATABASE tiktok_scheduler OWNER TO tiktok_user;"

# 5. Configurar variáveis de ambiente
echo "⚙️ Configurando variáveis de ambiente..."
cat > .env << 'EOF'
# Database
DATABASE_URL=postgresql://tiktok_user:tiktok_pass_2025@localhost/tiktok_scheduler

# Application
TZ=America/Sao_Paulo
FRONTEND_DIR=/home/ubuntu/tiktok/web

# Security - ALTERE ESTAS CHAVES EM PRODUÇÃO!
SECRET_KEY=tiktok_secret_key_$(date +%s)_random
JWT_SECRET_KEY=jwt_secret_key_$(date +%s)_random

# Paths
BASE_VIDEOS_DIR=/home/ubuntu/tiktok/videos
BASE_POSTED_DIR=/home/ubuntu/tiktok/posted
BASE_USERDATA_DIR=/home/ubuntu/tiktok/user_data
BASE_STATE_DIR=/home/ubuntu/tiktok/state
EOF

# 6. Inicializar banco de dados (criar tabelas do zero)
echo "🗄️ Inicializando banco de dados..."
python3 - <<'PYEOF'
from src.database import init_db
print("Criando tabelas...")
init_db()
print("✅ Tabelas criadas com sucesso!")
PYEOF

# 7. Configurar Systemd Service
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
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# 8. Configurar Traefik
echo "🌐 Configurando Traefik..."
sudo mkdir -p /srv/traefik

# Criar configuração do Traefik
sudo tee /srv/traefik/traefik.yml > /dev/null << 'EOF'
api:
  dashboard: true
  insecure: true

entryPoints:
  web:
    address: ":80"
  websecure:
    address: ":443"

providers:
  file:
    directory: /srv/traefik/dynamic
    watch: true

log:
  level: INFO
EOF

# Criar diretório de configurações dinâmicas
sudo mkdir -p /srv/traefik/dynamic

# Criar configuração dinâmica para o TikTok Scheduler
sudo tee /srv/traefik/dynamic/tiktok-scheduler.yml > /dev/null << 'EOF'
http:
  routers:
    tiktok-scheduler:
      rule: "PathPrefix(`/`)"
      service: tiktok-scheduler
      entryPoints:
        - web

  services:
    tiktok-scheduler:
      loadBalancer:
        servers:
          - url: "http://127.0.0.1:8082"
EOF

# Criar serviço do Traefik
sudo tee /etc/systemd/system/traefik.service > /dev/null << 'EOF'
[Unit]
Description=Traefik Reverse Proxy
After=network.target

[Service]
Type=simple
User=root
ExecStart=/usr/local/bin/traefik --configFile=/srv/traefik/traefik.yml
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Baixar Traefik se não existir
if [ ! -f /usr/local/bin/traefik ]; then
  echo "📥 Baixando Traefik..."
  sudo wget -O /tmp/traefik.tar.gz https://github.com/traefik/traefik/releases/download/v2.11.0/traefik_v2.11.0_linux_amd64.tar.gz
  sudo tar -xzf /tmp/traefik.tar.gz -C /tmp/
  sudo mv /tmp/traefik /usr/local/bin/
  sudo chmod +x /usr/local/bin/traefik
  sudo rm -f /tmp/traefik.tar.gz
fi

# 9. Habilitar e iniciar serviços
echo "🚀 Habilitando serviços..."
sudo systemctl daemon-reload
sudo systemctl enable tiktok-scheduler
sudo systemctl restart tiktok-scheduler
sudo systemctl enable traefik
sudo systemctl restart traefik

# 10. Verificar status
echo ""
echo "✅ Setup concluído!"
echo ""
echo "📊 Status dos serviços:"
echo ""
echo "🎯 TikTok Scheduler:"
sudo systemctl status tiktok-scheduler --no-pager -l | head -15
echo ""
echo "🌐 Traefik:"
sudo systemctl status traefik --no-pager -l | head -15
echo ""
echo "🔗 Acesse a aplicação em: http://$(curl -s ifconfig.me)"
echo "🔗 Traefik Dashboard: http://$(curl -s ifconfig.me):8080"
echo ""
echo "📝 Comandos úteis:"
echo "  - Ver logs TikTok: sudo journalctl -u tiktok-scheduler -f"
echo "  - Ver logs Traefik: sudo journalctl -u traefik -f"
echo "  - Reiniciar TikTok: sudo systemctl restart tiktok-scheduler"
echo "  - Reiniciar Traefik: sudo systemctl restart traefik"
echo ""

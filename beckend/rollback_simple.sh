#!/bin/bash
# Script de ROLLBACK para voltar ao sistema antigo

set -e

echo "=========================================="
echo "⏪ ROLLBACK PARA SISTEMA ANTIGO"
echo "=========================================="
echo ""

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Verifica se backup existe
if [ ! -f "src/driver_old_backup.py" ]; then
    echo -e "${RED}❌ Backup não encontrado!${NC}"
    echo -e "${YELLOW}Tente: git checkout HEAD~1 src/driver.py src/cookies.py src/uploader.py${NC}"
    exit 1
fi

# 1. Para serviço
echo -e "${YELLOW}🛑 Parando serviço...${NC}"
pkill -f scheduler_daemon || true
sudo systemctl stop tiktok-scheduler 2>/dev/null || true
docker-compose stop scheduler 2>/dev/null || true
sleep 3
echo -e "${GREEN}✅ Serviço parado${NC}"

# 2. Restaura backup
echo ""
echo -e "${YELLOW}📦 Restaurando arquivos originais...${NC}"
cp src/driver_old_backup.py src/driver.py
cp src/cookies_old_backup.py src/cookies.py
cp src/uploader_old_backup.py src/uploader.py
echo -e "${GREEN}✅ Arquivos restaurados${NC}"

# 3. Reinicia
echo ""
echo -e "${YELLOW}🚀 Reiniciando serviço...${NC}"
if command -v systemctl &> /dev/null && systemctl list-unit-files | grep -q tiktok-scheduler; then
    sudo systemctl start tiktok-scheduler
    echo -e "${GREEN}✅ Serviço reiniciado${NC}"
elif [ -f "../docker-compose.yml" ]; then
    docker-compose up -d scheduler
    echo -e "${GREEN}✅ Serviço reiniciado${NC}"
else
    python3 start_scheduler.py &
    echo -e "${GREEN}✅ Serviço reiniciado${NC}"
fi

echo ""
echo -e "${GREEN}✅ ROLLBACK CONCLUÍDO!${NC}"
echo "Sistema voltou para versão anterior."
echo ""

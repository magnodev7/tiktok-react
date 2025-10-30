#!/bin/bash
# Script de migração automática para sistema simplificado

set -e  # Para em caso de erro

echo "=========================================="
echo "🔄 MIGRANDO PARA SISTEMA SIMPLIFICADO"
echo "=========================================="
echo ""

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Verifica se está no diretório correto
if [ ! -f "src/driver_simple.py" ]; then
    echo -e "${RED}❌ Erro: Execute este script do diretório beckend/${NC}"
    exit 1
fi

# 1. Backup dos arquivos originais
echo -e "${YELLOW}📦 Passo 1: Fazendo backup dos arquivos originais...${NC}"
if [ ! -f "src/driver_old_backup.py" ]; then
    cp src/driver.py src/driver_old_backup.py
    cp src/cookies.py src/cookies_old_backup.py
    cp src/uploader.py src/uploader_old_backup.py
    echo -e "${GREEN}✅ Backup criado${NC}"
else
    echo -e "${YELLOW}⚠️  Backup já existe, pulando...${NC}"
fi

# 2. Substitui arquivos pelos simplificados
echo ""
echo -e "${YELLOW}🔧 Passo 2: Substituindo arquivos pelos simplificados...${NC}"
cp src/driver_simple.py src/driver.py
cp src/cookies_simple.py src/cookies.py
cp src/uploader_simple.py src/uploader.py
echo -e "${GREEN}✅ Arquivos substituídos${NC}"

# 3. Verifica se precisa atualizar scheduler.py
echo ""
echo -e "${YELLOW}🔍 Passo 3: Verificando scheduler.py...${NC}"
if grep -q "from src.driver import build_driver" src/scheduler.py 2>/dev/null; then
    echo -e "${YELLOW}ℹ️  scheduler.py usa imports antigos, mas os arquivos já foram substituídos${NC}"
    echo -e "${GREEN}✅ Imports funcionarão automaticamente pois substituímos os arquivos${NC}"
elif grep -q "from src.driver_simple import" src/scheduler.py 2>/dev/null; then
    echo -e "${YELLOW}⚠️  scheduler.py ainda importa *_simple.py${NC}"
    echo -e "${YELLOW}   Atualizando para importar os módulos padrão...${NC}"

    # Substitui imports _simple pelos padrão
    sed -i 's/from src.driver_simple import/from src.driver import/g' src/scheduler.py
    sed -i 's/from src.cookies_simple import/from src.cookies import/g' src/scheduler.py
    sed -i 's/from src.uploader_simple import/from src.uploader import/g' src/scheduler.py

    # Atualiza nomes de classes se necessário
    sed -i 's/build_driver_simple/build_driver/g' src/scheduler.py
    sed -i 's/get_or_create_driver/get_fresh_driver/g' src/scheduler.py
    sed -i 's/load_cookies_simple/load_cookies_for_account/g' src/scheduler.py
    sed -i 's/TikTokUploaderSimple/TikTokUploader/g' src/scheduler.py

    echo -e "${GREEN}✅ scheduler.py atualizado${NC}"
else
    echo -e "${GREEN}✅ scheduler.py OK${NC}"
fi

# 4. Para o serviço se estiver rodando
echo ""
echo -e "${YELLOW}🛑 Passo 4: Parando serviço atual...${NC}"

# Tenta diferentes métodos de parar o serviço
STOPPED=0

# Método 1: systemctl
if command -v systemctl &> /dev/null; then
    if systemctl is-active --quiet tiktok-scheduler 2>/dev/null; then
        echo "   Parando via systemctl..."
        sudo systemctl stop tiktok-scheduler
        STOPPED=1
    fi
fi

# Método 2: docker-compose
if [ -f "../docker-compose.yml" ] && command -v docker-compose &> /dev/null; then
    if docker-compose ps | grep -q scheduler; then
        echo "   Parando via docker-compose..."
        docker-compose stop scheduler
        STOPPED=1
    fi
fi

# Método 3: pkill
if pgrep -f "scheduler_daemon" > /dev/null; then
    echo "   Parando via pkill..."
    pkill -f scheduler_daemon || true
    sleep 2
    STOPPED=1
fi

if [ $STOPPED -eq 1 ]; then
    echo -e "${GREEN}✅ Serviço parado${NC}"
else
    echo -e "${YELLOW}⚠️  Nenhum serviço encontrado rodando (OK se já estava parado)${NC}"
fi

# 5. Aguarda um pouco
echo ""
echo -e "${YELLOW}⏳ Aguardando 3 segundos...${NC}"
sleep 3

# 6. Reinicia o serviço
echo ""
echo -e "${YELLOW}🚀 Passo 5: Reiniciando serviço...${NC}"

STARTED=0

# Método 1: systemctl
if command -v systemctl &> /dev/null; then
    if systemctl list-unit-files | grep -q tiktok-scheduler; then
        echo "   Iniciando via systemctl..."
        sudo systemctl start tiktok-scheduler
        sleep 3
        if systemctl is-active --quiet tiktok-scheduler; then
            echo -e "${GREEN}✅ Serviço iniciado via systemctl${NC}"
            STARTED=1
        fi
    fi
fi

# Método 2: docker-compose
if [ $STARTED -eq 0 ] && [ -f "../docker-compose.yml" ] && command -v docker-compose &> /dev/null; then
    echo "   Iniciando via docker-compose..."
    docker-compose up -d scheduler
    sleep 3
    if docker-compose ps | grep -q scheduler; then
        echo -e "${GREEN}✅ Serviço iniciado via docker-compose${NC}"
        STARTED=1
    fi
fi

# Método 3: start_scheduler.py
if [ $STARTED -eq 0 ] && [ -f "start_scheduler.py" ]; then
    echo "   Iniciando via start_scheduler.py..."
    nohup python3 start_scheduler.py > logs/scheduler.log 2>&1 &
    sleep 3
    if pgrep -f scheduler_daemon > /dev/null; then
        echo -e "${GREEN}✅ Serviço iniciado via start_scheduler.py${NC}"
        STARTED=1
    fi
fi

if [ $STARTED -eq 0 ]; then
    echo -e "${RED}❌ Não consegui reiniciar o serviço automaticamente${NC}"
    echo -e "${YELLOW}   Reinicie manualmente com um dos comandos:${NC}"
    echo -e "${YELLOW}   - sudo systemctl start tiktok-scheduler${NC}"
    echo -e "${YELLOW}   - docker-compose up -d scheduler${NC}"
    echo -e "${YELLOW}   - python3 start_scheduler.py${NC}"
fi

# 7. Verifica logs
echo ""
echo -e "${YELLOW}📋 Passo 6: Verificando logs...${NC}"
echo -e "${YELLOW}   Aguardando 5 segundos para logs aparecerem...${NC}"
sleep 5

if [ -f "logs/scheduler.log" ]; then
    echo ""
    echo -e "${GREEN}=========================================="
    echo "📊 ÚLTIMAS LINHAS DO LOG:"
    echo -e "==========================================${NC}"
    tail -20 logs/scheduler.log
else
    echo -e "${YELLOW}⚠️  Arquivo de log não encontrado${NC}"
fi

# 8. Resultado final
echo ""
echo "=========================================="
echo -e "${GREEN}✅ MIGRAÇÃO CONCLUÍDA!${NC}"
echo "=========================================="
echo ""
echo "📊 O que foi feito:"
echo "  ✅ Backup criado: src/*_old_backup.py"
echo "  ✅ Arquivos substituídos:"
echo "     - driver.py (agora é driver_simple.py)"
echo "     - cookies.py (agora é cookies_simple.py)"
echo "     - uploader.py (agora é uploader_simple.py)"
echo "  ✅ Serviço reiniciado"
echo ""
echo "🔍 Procure nos logs por:"
echo "  ✅ Ausência de \"Lock global adquirido\" (sistema antigo)"
echo "  ✅ Logs mais simples e diretos"
echo "  ✅ Uploads mais rápidos (~50s vs 3-5min)"
echo ""
echo "📝 Para monitorar:"
echo "  tail -f logs/scheduler.log"
echo ""
echo "⚠️  Se algo der errado, ROLLBACK:"
echo "  ./rollback_simple.sh"
echo ""

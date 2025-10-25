#!/bin/bash
#
# Script para limpar o projeto removendo dados de usuário, cache e builds
# Mantém apenas o código-fonte limpo pronto para deploy
#

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}════════════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}  🧹 LIMPEZA DO PROJETO - TIKTOK REACT${NC}"
echo -e "${CYAN}════════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${YELLOW}Este script vai remover:${NC}"
echo "  - node_modules/ (dependências Node.js)"
echo "  - dist/ (build do frontend)"
echo "  - venv/ (ambiente virtual Python)"
echo "  - profiles/ (perfis de usuário do Chrome)"
echo "  - user_data/ (dados de usuário)"
echo "  - __pycache__/ (cache Python)"
echo "  - *.pyc (arquivos compilados Python)"
echo "  - .pytest_cache/ (cache de testes)"
echo "  - .vite/ (cache do Vite)"
echo "  - logs/*.log (arquivos de log)"
echo "  - posted/* (vídeos postados)"
echo "  - videos/* (vídeos agendados)"
echo "  - state/*.json, state/*.db (estado da aplicação)"
echo "  - package-lock.json (lock do npm)"
echo ""
read -p "Deseja continuar? [y/N] " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Operação cancelada."
    exit 1
fi
echo ""

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Contador de arquivos/diretórios removidos
REMOVED_COUNT=0

# Função para remover com feedback
remove_item() {
    local item="$1"
    if [ -e "$item" ]; then
        rm -rf "$item"
        echo -e "${GREEN}✓${NC} Removido: $item"
        REMOVED_COUNT=$((REMOVED_COUNT + 1))
    fi
}

# ═══════════════════════════════════════════════════════════════
# FRONTEND
# ═══════════════════════════════════════════════════════════════
echo -e "${YELLOW}▶${NC} Limpando frontend..."

remove_item "node_modules"
remove_item "dist"
remove_item ".vite"
remove_item "package-lock.json"
remove_item "profiles"

# ═══════════════════════════════════════════════════════════════
# BACKEND
# ═══════════════════════════════════════════════════════════════
echo -e "${YELLOW}▶${NC} Limpando backend..."

cd beckend

# Ambiente virtual e cache Python
remove_item "venv"
remove_item "__pycache__"
remove_item ".pytest_cache"

# Cache Python em subdiretórios
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
echo -e "${GREEN}✓${NC} Removidos: arquivos .pyc e __pycache__"

# Dados de usuário
remove_item "profiles"
remove_item "user_data"
remove_item "src/user_data"

# Logs
if [ -d "logs" ]; then
    rm -f logs/*.log* 2>/dev/null || true
    echo -e "${GREEN}✓${NC} Limpos: logs/*.log*"
fi

# Vídeos e postados
if [ -d "posted" ]; then
    rm -rf posted/* 2>/dev/null || true
    echo -e "${GREEN}✓${NC} Limpos: posted/*"
fi

if [ -d "videos" ]; then
    # Manter a estrutura mas remover conteúdo
    find videos -mindepth 1 -delete 2>/dev/null || true
    echo -e "${GREEN}✓${NC} Limpos: videos/*"
fi

if [ -d "src/videos" ]; then
    find src/videos -mindepth 1 -delete 2>/dev/null || true
    echo -e "${GREEN}✓${NC} Limpos: src/videos/*"
fi

if [ -d "src/posted" ]; then
    find src/posted -mindepth 1 -delete 2>/dev/null || true
    echo -e "${GREEN}✓${NC} Limpos: src/posted/*"
fi

# Estado da aplicação (manter estrutura, remover dados)
if [ -d "state" ]; then
    rm -f state/*.json state/*.db 2>/dev/null || true
    echo -e "${GREEN}✓${NC} Limpos: state/*.json, state/*.db"
fi

if [ -d "src/state" ]; then
    rm -f src/state/*.json src/state/*.db 2>/dev/null || true
    echo -e "${GREEN}✓${NC} Limpos: src/state/*.json, src/state/*.db"
fi

# Cookies e sessões
remove_item "tiktok_cookies.json"
remove_item "*.session"

cd ..

# ═══════════════════════════════════════════════════════════════
# ARQUIVOS TEMPORÁRIOS E CACHE
# ═══════════════════════════════════════════════════════════════
echo -e "${YELLOW}▶${NC} Removendo arquivos temporários..."

# Remover arquivos de backup
find . -type f \( -name "*.bak" -o -name "*.backup" -o -name "*~" \) -delete 2>/dev/null || true
echo -e "${GREEN}✓${NC} Removidos: arquivos de backup"

# Remover arquivos de sistema
find . -type f -name ".DS_Store" -delete 2>/dev/null || true
echo -e "${GREEN}✓${NC} Removidos: .DS_Store"

# ═══════════════════════════════════════════════════════════════
# CRIAR DIRETÓRIOS VAZIOS NECESSÁRIOS
# ═══════════════════════════════════════════════════════════════
echo -e "${YELLOW}▶${NC} Recriando estrutura de diretórios..."

mkdir -p beckend/logs
mkdir -p beckend/posted
mkdir -p beckend/videos
mkdir -p beckend/state
mkdir -p beckend/src/videos
mkdir -p beckend/src/posted
mkdir -p beckend/src/state

# Criar .gitkeep para manter diretórios vazios no git
touch beckend/logs/.gitkeep
touch beckend/posted/.gitkeep
touch beckend/videos/.gitkeep
touch beckend/state/.gitkeep
touch beckend/src/videos/.gitkeep
touch beckend/src/posted/.gitkeep
touch beckend/src/state/.gitkeep

echo -e "${GREEN}✓${NC} Estrutura de diretórios recriada"

# ═══════════════════════════════════════════════════════════════
# RESUMO
# ═══════════════════════════════════════════════════════════════
echo ""
echo -e "${GREEN}════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  ✅ LIMPEZA CONCLUÍDA!${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════════════════${NC}"
echo ""
echo "Tamanho do projeto após limpeza:"
du -sh . 2>/dev/null | cut -f1 | xargs -I {} echo -e "  ${CYAN}{}${NC}"
echo ""
echo -e "${YELLOW}Projeto limpo e pronto para:${NC}"
echo "  ✓ Commit no Git"
echo "  ✓ Deploy em VPS"
echo "  ✓ Backup"
echo "  ✓ Compartilhamento"
echo ""
echo -e "${CYAN}Para instalar dependências novamente:${NC}"
echo -e "  ${GREEN}Frontend:${NC} npm install"
echo -e "  ${GREEN}Backend:${NC}  cd beckend && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
echo ""

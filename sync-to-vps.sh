#!/bin/bash
#
# ════════════════════════════════════════════════════════════════════════════
#  SCRIPT DE SINCRONIZAÇÃO PARA VPS - TIKTOK REACT
# ════════════════════════════════════════════════════════════════════════════
#
#  Envia o projeto para a VPS usando rsync (rápido e eficiente)
#  Ignora automaticamente: node_modules, venv, dist, etc.
#
#  Uso:
#    ./sync-to-vps.sh
#
# ════════════════════════════════════════════════════════════════════════════

set -e

# ════════════════════════════════════════════════════════════════════════════
# CONFIGURAÇÕES - EDITE AQUI
# ════════════════════════════════════════════════════════════════════════════

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

VPS_HOST="167.234.231.63"
VPS_USER="ubuntu"
SSH_KEY="$SCRIPT_DIR/ssh-key-2025-09-05.key"
REMOTE_DIR="/home/ubuntu/tiktok-react"

# ════════════════════════════════════════════════════════════════════════════

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

print_header() {
    echo ""
    echo -e "${BOLD}${CYAN}════════════════════════════════════════════════════════════════${NC}"
    echo -e "${BOLD}${CYAN}  $1${NC}"
    echo -e "${BOLD}${CYAN}════════════════════════════════════════════════════════════════${NC}"
    echo ""
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# ════════════════════════════════════════════════════════════════════════════
# VERIFICAÇÕES
# ════════════════════════════════════════════════════════════════════════════

print_header "SYNC TO VPS - TIKTOK REACT"

# Verificar se rsync está instalado
if ! command -v rsync &> /dev/null; then
    print_error "rsync não está instalado"
    print_info "Instale com: sudo apt install -y rsync"
    exit 1
fi

# Verificar se a chave SSH existe
if [ ! -f "$SSH_KEY" ]; then
    print_error "Chave SSH não encontrada: $SSH_KEY"
    exit 1
fi

# Verificar permissões da chave SSH
chmod 600 "$SSH_KEY" 2>/dev/null || true

print_success "Verificações concluídas"

# ════════════════════════════════════════════════════════════════════════════
# INFORMAÇÕES
# ════════════════════════════════════════════════════════════════════════════

echo ""
print_info "VPS: ${VPS_USER}@${VPS_HOST}"
print_info "Destino: ${REMOTE_DIR}"
print_info "SSH Key: ${SSH_KEY}"
echo ""

# ════════════════════════════════════════════════════════════════════════════
# TESTAR CONEXÃO SSH
# ════════════════════════════════════════════════════════════════════════════

print_info "Testando conexão SSH..."
if ssh -i "$SSH_KEY" -o ConnectTimeout=10 -o StrictHostKeyChecking=no "${VPS_USER}@${VPS_HOST}" "echo 'Conexão OK'" &>/dev/null; then
    print_success "Conexão SSH OK"
else
    print_error "Não foi possível conectar na VPS"
    print_info "Verifique:"
    print_info "  1. IP da VPS está correto: ${VPS_HOST}"
    print_info "  2. Usuário está correto: ${VPS_USER}"
    print_info "  3. Chave SSH está correta: ${SSH_KEY}"
    print_info "  4. Firewall permite SSH (porta 22)"
    exit 1
fi

# ════════════════════════════════════════════════════════════════════════════
# SINCRONIZAR ARQUIVOS
# ════════════════════════════════════════════════════════════════════════════

print_header "SINCRONIZANDO ARQUIVOS"

print_info "Enviando arquivos para VPS (isso pode demorar alguns minutos)..."
echo ""

# rsync com opções otimizadas
rsync -avz --progress \
    -e "ssh -i ${SSH_KEY} -o StrictHostKeyChecking=no" \
    --exclude='node_modules/' \
    --exclude='venv/' \
    --exclude='env/' \
    --exclude='beckend/venv/' \
    --exclude='beckend/env/' \
    --exclude='beckend/backup/' \
    --exclude='dist/' \
    --exclude='beckend/web/' \
    --exclude='__pycache__/' \
    --exclude='*.pyc' \
    --exclude='.git/' \
    --exclude='*.log' \
    --exclude='logs/' \
    --exclude='beckend/logs/' \
    --exclude='beckend/uploads/' \
    --exclude='beckend/videos/' \
    --exclude='beckend/posted/' \
    --exclude='beckend/state/' \
    --exclude='beckend/postgres_data/' \
    --exclude='test-results/' \
    --exclude='playwright-report/' \
    --exclude='.vscode/' \
    --exclude='.idea/' \
    --exclude='*.key' \
    --exclude='*.pem' \
    --exclude='.DS_Store' \
    --exclude='*.sql' \
    --exclude='*.dump' \
    --exclude='backup_*' \
    ./ "${VPS_USER}@${VPS_HOST}:${REMOTE_DIR}/"

if [ $? -eq 0 ]; then
    echo ""
    print_success "Arquivos sincronizados com sucesso!"
else
    echo ""
    print_error "Erro ao sincronizar arquivos"
    exit 1
fi

# ════════════════════════════════════════════════════════════════════════════
# VERIFICAR ARQUIVOS
# ════════════════════════════════════════════════════════════════════════════

print_header "VERIFICANDO ARQUIVOS NA VPS"

print_info "Listando arquivos principais..."
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "${VPS_USER}@${VPS_HOST}" << 'EOF'
cd /home/ubuntu/tiktok-react
echo "Arquivos no diretório raiz:"
ls -lah | head -20
echo ""
echo "Arquivos no beckend:"
ls -lah beckend/ | head -15
echo ""
echo "Scripts executáveis:"
ls -lah *.sh 2>/dev/null || echo "Nenhum script .sh encontrado"
ls -lah beckend/*.sh 2>/dev/null || echo "Nenhum script .sh no beckend"
EOF

print_success "Verificação concluída"

# ════════════════════════════════════════════════════════════════════════════
# INSTRUÇÕES FINAIS
# ════════════════════════════════════════════════════════════════════════════

print_header "PRÓXIMOS PASSOS"

echo -e "${BOLD}Para executar o deploy na VPS:${NC}"
echo ""
echo -e "${CYAN}1. Conectar na VPS:${NC}"
echo -e "   ${GREEN}ssh -i ${SSH_KEY} ${VPS_USER}@${VPS_HOST}${NC}"
echo ""
echo -e "${CYAN}2. Entrar no diretório:${NC}"
echo -e "   ${GREEN}cd ${REMOTE_DIR}${NC}"
echo ""
echo -e "${CYAN}3. Executar deploy:${NC}"
echo -e "   ${GREEN}./deploy.sh${NC}"
echo ""
echo -e "${CYAN}4. Ou execute tudo de uma vez (modo automático):${NC}"
echo -e "   ${GREEN}ssh -i ${SSH_KEY} ${VPS_USER}@${VPS_HOST} \"cd ${REMOTE_DIR} && chmod +x deploy.sh && ./deploy.sh\"${NC}"
echo ""

print_success "Projeto sincronizado com sucesso! 🎉"
echo ""

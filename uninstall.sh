#!/bin/bash
#
# ════════════════════════════════════════════════════════════════════════════
#  SCRIPT DE UNINSTALL - TIKTOK REACT
# ════════════════════════════════════════════════════════════════════════════
#
#  Remove TUDO que o deploy.sh instalou:
#  - Serviços systemd (API + Agendador)
#  - Containers Docker (PostgreSQL)
#  - Ambiente virtual Python
#  - node_modules
#  - Build do frontend
#  - Logs e dados temporários
#
#  Uso:
#    ./uninstall.sh              # Remove tudo
#    ./uninstall.sh --keep-data  # Mantém dados do banco
#
# ════════════════════════════════════════════════════════════════════════════

set -e

# ════════════════════════════════════════════════════════════════════════════
# CONFIGURAÇÕES
# ════════════════════════════════════════════════════════════════════════════

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BACKEND_DIR="$SCRIPT_DIR/beckend"

# Flags
KEEP_DATA=false

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# ════════════════════════════════════════════════════════════════════════════
# FUNÇÕES HELPER
# ════════════════════════════════════════════════════════════════════════════

print_header() {
    echo ""
    echo -e "${BOLD}${RED}════════════════════════════════════════════════════════════════${NC}"
    echo -e "${BOLD}${RED}  $1${NC}"
    echo -e "${BOLD}${RED}════════════════════════════════════════════════════════════════${NC}"
    echo ""
}

print_step() {
    echo -e "${BOLD}${CYAN}▶${NC} ${BOLD}$1${NC}"
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

confirm() {
    read -p "$(echo -e ${RED}⚠${NC} $1 [y/N]: )" -n 1 -r
    echo
    [[ $REPLY =~ ^[Yy]$ ]]
}

# ════════════════════════════════════════════════════════════════════════════
# FUNÇÕES DE UNINSTALL
# ════════════════════════════════════════════════════════════════════════════

uninstall_services() {
    print_header "REMOVENDO SERVIÇOS SYSTEMD"

    cd "$BACKEND_DIR"

    if [ -f "manage.sh" ] && [ -f "venv/bin/activate" ]; then
        source venv/bin/activate 2>/dev/null || true

        print_step "Parando serviços..."
        ./manage.sh all stop 2>/dev/null || true
        print_success "Serviços parados"

        print_step "Removendo serviços do systemd..."
        ./manage.sh all uninstall 2>/dev/null || true
        print_success "Serviços removidos"
    else
        print_info "Serviços não encontrados ou já removidos"
    fi
}

uninstall_docker() {
    print_header "REMOVENDO CONTAINERS DOCKER"

    cd "$BACKEND_DIR"

    if [ -f "docker-compose.yml" ]; then
        print_step "Parando containers..."
        docker-compose down 2>/dev/null || true
        print_success "Containers parados"

        if [ "$KEEP_DATA" = false ]; then
            print_step "Removendo volumes (dados do PostgreSQL)..."
            docker-compose down -v 2>/dev/null || true
            print_success "Volumes removidos"
        else
            print_info "Mantendo volumes de dados (--keep-data)"
        fi
    else
        print_info "docker-compose.yml não encontrado"
    fi
}

cleanup_files() {
    print_header "REMOVENDO ARQUIVOS E DIRETÓRIOS"

    cd "$SCRIPT_DIR"

    # Remover venv
    if [ -d "beckend/venv" ]; then
        print_step "Removendo ambiente virtual Python..."
        rm -rf beckend/venv
        print_success "venv removido"
    fi

    # Remover node_modules
    if [ -d "node_modules" ]; then
        print_step "Removendo node_modules..."
        rm -rf node_modules
        print_success "node_modules removido"
    fi

    # Remover dist/build
    if [ -d "dist" ]; then
        print_step "Removendo build do frontend..."
        rm -rf dist
        print_success "dist removido"
    fi

    if [ -d "beckend/web" ]; then
        print_step "Removendo beckend/web..."
        rm -rf beckend/web
        print_success "beckend/web removido"
    fi

    # Remover logs
    if [ -d "beckend/logs" ]; then
        print_step "Removendo logs..."
        rm -rf beckend/logs
        print_success "Logs removidos"
    fi

    # Remover __pycache__
    print_step "Removendo cache Python..."
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete 2>/dev/null || true
    print_success "Cache Python removido"

    # Remover uploads/videos (se não for manter dados)
    if [ "$KEEP_DATA" = false ]; then
        if [ -d "beckend/uploads" ]; then
            print_step "Removendo uploads..."
            rm -rf beckend/uploads
            print_success "Uploads removidos"
        fi

        if [ -d "beckend/videos" ]; then
            print_step "Removendo videos..."
            rm -rf beckend/videos
            print_success "Videos removidos"
        fi

        if [ -d "beckend/posted" ]; then
            print_step "Removendo posted..."
            rm -rf beckend/posted
            print_success "Posted removidos"
        fi

        if [ -d "beckend/state" ]; then
            print_step "Removendo state..."
            rm -rf beckend/state
            print_success "State removido"
        fi
    else
        print_info "Mantendo dados de uploads/videos (--keep-data)"
    fi
}

show_cleanup_status() {
    print_header "VERIFICANDO LIMPEZA"

    echo -e "${BOLD}Status dos componentes:${NC}"
    echo ""

    # Serviços
    if systemctl list-units --all | grep -q "tiktok-"; then
        print_warning "Alguns serviços ainda existem"
    else
        print_success "Nenhum serviço systemd encontrado"
    fi

    # Docker
    if docker ps -a | grep -q postgres; then
        print_warning "Container PostgreSQL ainda existe"
    else
        print_success "Nenhum container encontrado"
    fi

    # Arquivos
    local files_remaining=0
    [ -d "beckend/venv" ] && ((files_remaining++))
    [ -d "node_modules" ] && ((files_remaining++))
    [ -d "dist" ] && ((files_remaining++))
    [ -d "beckend/web" ] && ((files_remaining++))

    if [ $files_remaining -gt 0 ]; then
        print_warning "$files_remaining diretórios ainda existem"
    else
        print_success "Todos os diretórios foram removidos"
    fi

    echo ""
}

# ════════════════════════════════════════════════════════════════════════════
# PARSING DE ARGUMENTOS
# ════════════════════════════════════════════════════════════════════════════

show_help() {
    echo "Uso: $0 [OPÇÕES]"
    echo ""
    echo "Opções:"
    echo "  --keep-data      Mantém dados do PostgreSQL e uploads"
    echo "  --help           Mostra esta ajuda"
    echo ""
    echo "Exemplos:"
    echo "  $0               # Remove tudo"
    echo "  $0 --keep-data   # Remove tudo exceto dados"
    exit 0
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --keep-data)
                KEEP_DATA=true
                shift
                ;;
            --help|-h)
                show_help
                ;;
            *)
                print_error "Opção desconhecida: $1"
                show_help
                ;;
        esac
    done
}

# ════════════════════════════════════════════════════════════════════════════
# FUNÇÃO PRINCIPAL
# ════════════════════════════════════════════════════════════════════════════

main() {
    # Clear screen se TERM estiver configurado
    if [ -n "$TERM" ] && [ "$TERM" != "dumb" ]; then
        clear 2>/dev/null || true
    fi

    echo -e "${BOLD}${RED}"
    echo "╔═══════════════════════════════════════════════════════════════════╗"
    echo "║                                                                   ║"
    echo "║           🗑️   UNINSTALL - TIKTOK REACT  🗑️                       ║"
    echo "║                                                                   ║"
    echo "╚═══════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"

    print_info "Diretório: $SCRIPT_DIR"
    echo ""

    # Parsing de argumentos
    parse_args "$@"

    # Confirmação
    if [ "$KEEP_DATA" = true ]; then
        print_warning "Modo: Manter dados (PostgreSQL + uploads)"
    else
        print_warning "Modo: Remover TUDO (incluindo dados!)"
    fi
    echo ""

    if ! confirm "Tem certeza que deseja desinstalar?"; then
        print_warning "Uninstall cancelado"
        exit 0
    fi

    echo ""

    # Executar uninstall
    uninstall_services
    uninstall_docker
    cleanup_files
    show_cleanup_status

    print_header "UNINSTALL CONCLUÍDO"

    echo -e "${BOLD}O que foi removido:${NC}"
    echo -e "${GREEN}✓${NC} Serviços systemd (tiktok-api, tiktok-scheduler)"
    echo -e "${GREEN}✓${NC} Containers Docker (PostgreSQL)"
    if [ "$KEEP_DATA" = false ]; then
        echo -e "${GREEN}✓${NC} Volumes Docker (dados do banco)"
    fi
    echo -e "${GREEN}✓${NC} Ambiente virtual Python (beckend/venv)"
    echo -e "${GREEN}✓${NC} node_modules"
    echo -e "${GREEN}✓${NC} Build do frontend (dist, beckend/web)"
    echo -e "${GREEN}✓${NC} Logs e cache"
    if [ "$KEEP_DATA" = false ]; then
        echo -e "${GREEN}✓${NC} Uploads, videos e state"
    fi
    echo ""

    print_success "Sistema limpo! Você pode executar ./deploy.sh novamente para reinstalar."
}

# ════════════════════════════════════════════════════════════════════════════
# EXECUÇÃO
# ════════════════════════════════════════════════════════════════════════════

# Trap para capturar erros
trap 'print_error "Erro na linha $LINENO"; exit 1' ERR

# Executar
main "$@"

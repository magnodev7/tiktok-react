#!/bin/bash
# Script de gerenciamento do TikTok Scheduler
# Uso: ./manage.sh [backend|scheduler|all] [start|stop|restart|status|logs|install]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

BACKEND_SERVICE="tiktok-backend.service"
SCHEDULER_SERVICE="tiktok-scheduler.service"

# Cores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo "ℹ️  $1"
}

# Função para gerar arquivos de serviço dinamicamente
generate_service_files() {
    local current_user=$(whoami)
    local backend_dir="$SCRIPT_DIR"
    local venv_python="$backend_dir/venv/bin/python"

    print_info "Gerando arquivos de serviço para usuário: $current_user"
    print_info "Diretório backend: $backend_dir"

    # Criar diretório de logs se não existir
    mkdir -p "$backend_dir/logs"

    # Garantir que o usuário atual tenha permissões nos logs
    # (necessário porque systemd pode criar arquivos como root)
    touch "$backend_dir/logs/backend.log" "$backend_dir/logs/backend-error.log" \
          "$backend_dir/logs/scheduler.log" "$backend_dir/logs/scheduler-error.log" 2>/dev/null || true
    chmod 644 "$backend_dir/logs"/*.log 2>/dev/null || true

    # Se os arquivos pertencerem a root, corrigir com sudo
    if [ -f "$backend_dir/logs/scheduler.log" ] && [ "$(stat -c %U "$backend_dir/logs/scheduler.log" 2>/dev/null)" = "root" ]; then
        print_warning "Corrigindo permissões de logs (arquivos pertencem a root)..."
        sudo chown -R $current_user:$current_user "$backend_dir/logs/" || print_error "Não foi possível corrigir permissões. Execute: sudo chown -R $current_user:$current_user $backend_dir/logs/"
    fi

    # Gerar tiktok-backend.service
    cat > "$BACKEND_SERVICE" <<EOF
[Unit]
Description=TikTok Scheduler - Backend API (FastAPI)
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=simple
User=$current_user
Group=$current_user
WorkingDirectory=$backend_dir
Environment="PATH=$backend_dir/venv/bin:/usr/local/bin:/usr/bin:/bin"

# Comando para iniciar o backend
ExecStart=$venv_python -m uvicorn src.http_health:app --host 0.0.0.0 --port 8082

# Restart automático
Restart=always
RestartSec=10

# Logs
StandardOutput=append:$backend_dir/logs/backend.log
StandardError=append:$backend_dir/logs/backend-error.log

# Limites
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
EOF

    # Gerar tiktok-scheduler.service
    cat > "$SCHEDULER_SERVICE" <<EOF
[Unit]
Description=TikTok Scheduler - Daemon de Agendamento
After=network.target postgresql.service tiktok-backend.service
Wants=postgresql.service
Requires=tiktok-backend.service

[Service]
Type=simple
User=$current_user
Group=$current_user
WorkingDirectory=$backend_dir
Environment="PATH=$backend_dir/venv/bin:/usr/local/bin:/usr/bin:/bin"
Environment="DISPLAY=:0"

# Comando para iniciar o scheduler
ExecStart=$venv_python start_scheduler.py start

# Comando para parar gracefully
ExecStop=$venv_python start_scheduler.py stop

# Restart automático
Restart=always
RestartSec=10

# Logs
StandardOutput=append:$backend_dir/logs/scheduler.log
StandardError=append:$backend_dir/logs/scheduler-error.log

# Tempo para shutdown graceful
TimeoutStopSec=30

# Limites
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
EOF

    print_success "Arquivos de serviço gerados com sucesso"
}

# Função para instalar serviços systemd
install_services() {
    print_info "Instalando serviços systemd..."

    # Gerar arquivos de serviço dinamicamente
    generate_service_files

    # Copia arquivos de serviço
    sudo cp "$BACKEND_SERVICE" /etc/systemd/system/
    sudo cp "$SCHEDULER_SERVICE" /etc/systemd/system/

    # Recarrega systemd
    sudo systemctl daemon-reload

    # Habilita serviços para iniciar no boot
    sudo systemctl enable "$BACKEND_SERVICE"
    sudo systemctl enable "$SCHEDULER_SERVICE"

    print_success "Serviços instalados e habilitados para iniciar no boot"
    print_info "Use './manage.sh all start' para iniciar os serviços"
}

# Função para desinstalar serviços
uninstall_services() {
    print_info "Desinstalando serviços systemd..."

    # Para serviços
    sudo systemctl stop "$BACKEND_SERVICE" 2>/dev/null || true
    sudo systemctl stop "$SCHEDULER_SERVICE" 2>/dev/null || true

    # Desabilita serviços
    sudo systemctl disable "$BACKEND_SERVICE" 2>/dev/null || true
    sudo systemctl disable "$SCHEDULER_SERVICE" 2>/dev/null || true

    # Remove arquivos
    sudo rm -f "/etc/systemd/system/$BACKEND_SERVICE"
    sudo rm -f "/etc/systemd/system/$SCHEDULER_SERVICE"

    # Recarrega systemd
    sudo systemctl daemon-reload

    print_success "Serviços desinstalados"
}

# Função para gerenciar um serviço
manage_service() {
    local service=$1
    local action=$2

    case $action in
        start)
            print_info "Iniciando $service..."
            sudo systemctl start "$service"
            print_success "$service iniciado"
            ;;
        stop)
            print_info "Parando $service..."
            sudo systemctl stop "$service"
            print_success "$service parado"
            ;;
        restart)
            print_info "Reiniciando $service..."
            sudo systemctl restart "$service"
            print_success "$service reiniciado"
            ;;
        status)
            sudo systemctl status "$service" --no-pager -l
            ;;
        logs)
            sudo journalctl -u "$service" -f --no-pager
            ;;
        *)
            print_error "Ação inválida: $action"
            exit 1
            ;;
    esac
}

# Verifica argumentos
if [ $# -lt 2 ]; then
    echo "Uso: $0 [backend|scheduler|all] [start|stop|restart|status|logs|install|uninstall]"
    echo ""
    echo "Componentes:"
    echo "  backend    - Backend HTTP (FastAPI na porta 8082)"
    echo "  scheduler  - Daemon de agendamento de postagens"
    echo "  all        - Ambos os componentes"
    echo ""
    echo "Ações:"
    echo "  install    - Instala serviços systemd e habilita no boot"
    echo "  uninstall  - Remove serviços systemd"
    echo "  start      - Inicia o(s) serviço(s)"
    echo "  stop       - Para o(s) serviço(s)"
    echo "  restart    - Reinicia o(s) serviço(s)"
    echo "  status     - Mostra status do(s) serviço(s)"
    echo "  logs       - Mostra logs em tempo real"
    echo ""
    echo "Exemplos:"
    echo "  $0 all install       # Instala ambos os serviços"
    echo "  $0 all start         # Inicia ambos os serviços"
    echo "  $0 backend status    # Status do backend"
    echo "  $0 scheduler logs    # Logs do scheduler em tempo real"
    exit 1
fi

COMPONENT=$1
ACTION=$2

# Ações especiais
if [ "$ACTION" = "install" ]; then
    install_services
    exit 0
fi

if [ "$ACTION" = "uninstall" ]; then
    uninstall_services
    exit 0
fi

# Gerencia serviços
case $COMPONENT in
    backend)
        manage_service "$BACKEND_SERVICE" "$ACTION"
        ;;
    scheduler)
        manage_service "$SCHEDULER_SERVICE" "$ACTION"
        ;;
    all)
        if [ "$ACTION" = "logs" ]; then
            print_info "Mostrando logs de ambos os serviços..."
            sudo journalctl -u "$BACKEND_SERVICE" -u "$SCHEDULER_SERVICE" -f --no-pager
        else
            manage_service "$BACKEND_SERVICE" "$ACTION"
            manage_service "$SCHEDULER_SERVICE" "$ACTION"
        fi
        ;;
    *)
        print_error "Componente inválido: $COMPONENT"
        exit 1
        ;;
esac

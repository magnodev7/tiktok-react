#!/bin/bash
#
# ════════════════════════════════════════════════════════════════════════════
#  SCRIPT DE DEPLOY AUTOMÁTICO - TIKTOK REACT (macOS)
# ════════════════════════════════════════════════════════════════════════════
#
#  Este script realiza o deploy completo da aplicação TikTok React em macOS
#
#  Passos executados:
#  1. ✅ Verificação de dependências (Docker Desktop, Python, Node, Nginx)
#  2. ✅ Setup do PostgreSQL (Docker Compose)
#  3. ✅ Setup do Backend (venv, requirements, migrações)
#  4. ✅ Setup dos Serviços (API + Agendador via launchd)
#  5. ✅ Build do Frontend (React + Vite)
#  6. ✅ Configuração do Nginx (reverse proxy)
#  7. ✅ Verificação final e testes
#
#  Uso:
#    ./deploy_macos.sh                 # Deploy completo
#    ./deploy_macos.sh --skip-db       # Pula setup do banco
#    ./deploy_macos.sh --skip-fe       # Pula build do frontend
#    ./deploy_macos.sh --skip-nginx    # Pula configuração do Nginx
#    ./deploy_macos.sh --dev           # Modo desenvolvimento
#    ./deploy_macos.sh --help          # Mostra ajuda
#
# ════════════════════════════════════════════════════════════════════════════

set -e  # Para na primeira falha

# ════════════════════════════════════════════════════════════════════════════
# CONFIGURAÇÕES
# ════════════════════════════════════════════════════════════════════════════

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BACKEND_DIR="$SCRIPT_DIR/beckend"
FRONTEND_DIR="$SCRIPT_DIR"

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Flags
SKIP_DB=false
SKIP_FE=false
SKIP_NGINX=false
DEV_MODE=false

# ════════════════════════════════════════════════════════════════════════════
# FUNÇÕES HELPER
# ════════════════════════════════════════════════════════════════════════════

print_header() {
    echo ""
    echo -e "${BOLD}${CYAN}════════════════════════════════════════════════════════════════${NC}"
    echo -e "${BOLD}${CYAN}  $1${NC}"
    echo -e "${BOLD}${CYAN}════════════════════════════════════════════════════════════════${NC}"
    echo ""
}

print_step() {
    echo -e "${BOLD}${MAGENTA}▶${NC} ${BOLD}$1${NC}"
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

print_command() {
    echo -e "${CYAN}  →${NC} $1"
}

# Função de confirmação
confirm() {
    read -p "$(echo -e ${YELLOW}⚠${NC} $1 [y/N]: )" -n 1 -r
    echo
    [[ $REPLY =~ ^[Yy]$ ]]
}

# ════════════════════════════════════════════════════════════════════════════
# VERIFICAÇÃO DE DEPENDÊNCIAS
# ════════════════════════════════════════════════════════════════════════════

check_dependencies() {
    print_header "VERIFICANDO E INSTALANDO DEPENDÊNCIAS DO SISTEMA (macOS)"

    # ═══════════════════════════════════════════════════════════════
    # HOMEBREW
    # ═══════════════════════════════════════════════════════════════
    print_step "Verificando Homebrew..."
    if command -v brew &> /dev/null; then
        local brew_version=$(brew --version | head -n1)
        print_success "Homebrew instalado: $brew_version"
    else
        print_warning "Homebrew não encontrado. Instalando..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

        # Adicionar brew ao PATH
        if [[ $(uname -m) == 'arm64' ]]; then
            # Apple Silicon
            echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
            eval "$(/opt/homebrew/bin/brew shellenv)"
        else
            # Intel Mac
            echo 'eval "$(/usr/local/bin/brew shellenv)"' >> ~/.zprofile
            eval "$(/usr/local/bin/brew shellenv)"
        fi

        print_success "Homebrew instalado com sucesso!"
    fi

    # ═══════════════════════════════════════════════════════════════
    # DOCKER DESKTOP
    # ═══════════════════════════════════════════════════════════════
    print_step "Verificando Docker..."
    if command -v docker &> /dev/null && docker ps &> /dev/null; then
        local docker_version=$(docker --version | cut -d ' ' -f3 | tr -d ',')
        print_success "Docker instalado e rodando: $docker_version"
    else
        print_warning "Docker não está rodando ou não instalado"

        if ! command -v docker &> /dev/null; then
            print_info "Instalando Docker Desktop via Homebrew..."
            brew install --cask docker
            print_success "Docker Desktop instalado!"
        fi

        print_warning "Por favor, inicie o Docker Desktop manualmente"
        print_info "1. Abra o Docker Desktop na pasta Applications"
        print_info "2. Aguarde até que o Docker esteja rodando (ícone na barra superior)"
        print_info "3. Pressione ENTER para continuar..."
        read

        # Aguardar Docker ficar pronto
        local max_wait=60
        local count=0
        while ! docker ps &> /dev/null; do
            echo -n "."
            sleep 2
            count=$((count + 1))
            if [ $count -gt $max_wait ]; then
                print_error "Docker não iniciou após ${max_wait} tentativas"
                exit 1
            fi
        done
        echo ""
        print_success "Docker está rodando!"
    fi

    # ═══════════════════════════════════════════════════════════════
    # DOCKER COMPOSE
    # ═══════════════════════════════════════════════════════════════
    print_step "Verificando Docker Compose..."

    if docker compose version &> /dev/null; then
        local compose_version=$(docker compose version --short 2>/dev/null || docker compose version | grep -oE 'v[0-9]+\.[0-9]+\.[0-9]+')
        print_success "Docker Compose instalado: $compose_version"
    else
        print_error "Docker Compose não encontrado (deveria vir com Docker Desktop)"
        print_info "Reinstale o Docker Desktop"
        exit 1
    fi

    # ═══════════════════════════════════════════════════════════════
    # PYTHON 3.8+
    # ═══════════════════════════════════════════════════════════════
    print_step "Verificando Python 3..."
    if command -v python3 &> /dev/null; then
        local python_version=$(python3 --version | cut -d ' ' -f2)
        local python_major=$(echo $python_version | cut -d'.' -f1)
        local python_minor=$(echo $python_version | cut -d'.' -f2)

        # Verificar se é Python 3.8 ou superior
        if [ "$python_major" -ge 3 ] && [ "$python_minor" -ge 8 ]; then
            print_success "Python 3 instalado: $python_version (OK)"
        else
            print_warning "Python $python_version é muito antigo (necessário 3.8+)"
            print_info "Instalando Python 3.11 via Homebrew..."
            brew install python@3.11
            print_success "Python atualizado!"
        fi
    else
        print_warning "Python 3 não encontrado. Instalando..."
        brew install python@3.11
        local python_version=$(python3 --version | cut -d ' ' -f2)
        print_success "Python 3 instalado: $python_version"
    fi

    # ═══════════════════════════════════════════════════════════════
    # PIP
    # ═══════════════════════════════════════════════════════════════
    print_step "Verificando pip..."
    if command -v pip3 &> /dev/null || python3 -m pip --version &> /dev/null 2>&1; then
        print_success "pip instalado"
    else
        print_warning "pip não encontrado. Instalando..."
        python3 -m ensurepip --upgrade
        print_success "pip instalado"
    fi

    # ═══════════════════════════════════════════════════════════════
    # NODE.JS 20+
    # ═══════════════════════════════════════════════════════════════
    print_step "Verificando Node.js..."
    if command -v node &> /dev/null; then
        local node_version=$(node --version | cut -d'v' -f2 | cut -d'.' -f1)
        local node_full=$(node --version)

        if [ "$node_version" -lt 20 ]; then
            print_warning "Node.js $node_full instalado (versão antiga, necessário v20+)"
            print_info "Atualizando Node.js para versão 20..."

            # No macOS, usar brew para atualizar
            brew upgrade node || brew install node@20

            node_full=$(node --version)
            print_success "Node.js atualizado para: $node_full"
        else
            print_success "Node.js instalado: $node_full (OK)"
        fi
    else
        print_warning "Node.js não encontrado. Instalando Node.js 20..."
        brew install node@20
        # Adicionar ao PATH se necessário
        echo 'export PATH="/opt/homebrew/opt/node@20/bin:$PATH"' >> ~/.zprofile
        export PATH="/opt/homebrew/opt/node@20/bin:$PATH"
        local node_full=$(node --version)
        print_success "Node.js instalado: $node_full"
    fi

    # ═══════════════════════════════════════════════════════════════
    # NPM
    # ═══════════════════════════════════════════════════════════════
    print_step "Verificando npm..."
    if command -v npm &> /dev/null; then
        local npm_version=$(npm --version)
        print_success "npm instalado: $npm_version"
    else
        print_error "npm não encontrado (deveria vir com Node.js)"
        exit 1
    fi

    echo ""
    print_success "✅ Todas as dependências estão instaladas e atualizadas!"
    echo ""
}

# ════════════════════════════════════════════════════════════════════════════
# SETUP DO POSTGRESQL (DOCKER)
# ════════════════════════════════════════════════════════════════════════════

setup_database() {
    if [ "$SKIP_DB" = true ]; then
        print_warning "Pulando setup do banco de dados (--skip-db)"
        return
    fi

    print_header "CONFIGURANDO POSTGRESQL (DOCKER)"

    cd "$BACKEND_DIR"

    # Verifica se docker-compose.yml existe
    if [ ! -f "docker-compose.yml" ]; then
        print_error "docker-compose.yml não encontrado em $BACKEND_DIR"
        exit 1
    fi

    print_step "Parando containers existentes..."
    docker compose down 2>/dev/null || true
    print_success "Containers parados"

    print_step "Iniciando PostgreSQL..."
    docker compose up -d postgres

    print_step "Aguardando PostgreSQL ficar pronto..."
    local max_attempts=30
    local attempt=0
    while [ $attempt -lt $max_attempts ]; do
        if docker compose exec -T postgres pg_isready -U tiktok &>/dev/null; then
            print_success "PostgreSQL está pronto!"
            break
        fi
        attempt=$((attempt + 1))
        echo -n "."
        sleep 2
    done

    if [ $attempt -eq $max_attempts ]; then
        print_error "PostgreSQL não ficou pronto após ${max_attempts} tentativas"
        exit 1
    fi

    print_success "PostgreSQL configurado e rodando"
}

# ════════════════════════════════════════════════════════════════════════════
# SETUP DO BACKEND
# ════════════════════════════════════════════════════════════════════════════

setup_backend() {
    print_header "CONFIGURANDO BACKEND"

    cd "$BACKEND_DIR"

    # Criar ambiente virtual
    print_step "Criando ambiente virtual Python..."
    if [ ! -d "venv" ] || [ ! -f "venv/bin/activate" ]; then
        print_info "Criando ambiente virtual..."
        if python3 -m venv venv; then
            print_success "Ambiente virtual pronto"
        else
            print_error "Falha ao criar o ambiente virtual"
            exit 1
        fi
    else
        print_info "Ambiente virtual já existe"
    fi

    if [ ! -f "venv/bin/activate" ]; then
        print_error "Ambiente virtual inválido (venv/bin/activate ausente)"
        exit 1
    fi

    # Ativar venv
    print_step "Ativando ambiente virtual..."
    source venv/bin/activate
    print_success "Ambiente virtual ativado"

    # Instalar dependências
    print_step "Instalando dependências Python..."
    pip install --upgrade pip setuptools wheel
    pip install -r requirements.txt
    print_success "Dependências instaladas"

    # Configurar permissões
    print_step "Configurando permissões..."
    chmod +x manage.sh 2>/dev/null || true
    chmod +x init_db.py 2>/dev/null || true
    chmod +x setup_database.sh 2>/dev/null || true
    print_success "Permissões configuradas"

    # Executar migrações
    print_step "Executando migrações do banco de dados..."
    export DATABASE_URL="postgresql://tiktok:tiktok123@localhost:5432/tiktok_db"
    python init_db.py
    print_success "Migrações concluídas"

    # Criar diretórios necessários no projeto root
    print_step "Criando diretórios necessários..."
    mkdir -p "$SCRIPT_DIR/videos" "$SCRIPT_DIR/posted" "$SCRIPT_DIR/profiles" "$SCRIPT_DIR/state"

    # Criar arquivos JSON iniciais se não existirem
    if [ ! -f "$SCRIPT_DIR/state/schedules.json" ]; then
        echo '[]' > "$SCRIPT_DIR/state/schedules.json"
        print_info "Arquivo schedules.json criado"
    fi

    if [ ! -f "$SCRIPT_DIR/state/logs.json" ]; then
        echo '{"logs": []}' > "$SCRIPT_DIR/state/logs.json"
        print_info "Arquivo logs.json criado"
    fi

    print_success "Diretórios e arquivos iniciais criados com sucesso"

    print_success "Backend configurado com sucesso!"
}

# ════════════════════════════════════════════════════════════════════════════
# SETUP DOS SERVIÇOS (LAUNCHD - macOS)
# ════════════════════════════════════════════════════════════════════════════

setup_services() {
    print_header "CONFIGURANDO SERVIÇOS (LaunchAgents - macOS)"

    cd "$BACKEND_DIR"

    if [ ! -f "manage.sh" ]; then
        print_error "manage.sh não encontrado"
        exit 1
    fi

    source venv/bin/activate

    # No macOS, vamos criar os serviços usando launchd
    local LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
    mkdir -p "$LAUNCH_AGENTS_DIR"

    # Obter o caminho completo do Python do venv
    local PYTHON_PATH="$BACKEND_DIR/venv/bin/python"
    local UVICORN_PATH="$BACKEND_DIR/venv/bin/uvicorn"

    # ═══════════════════════════════════════════════════════════════
    # SERVIÇO DA API
    # ═══════════════════════════════════════════════════════════════
    print_step "Criando serviço da API..."

    cat > "$LAUNCH_AGENTS_DIR/com.tiktok.api.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.tiktok.api</string>

    <key>ProgramArguments</key>
    <array>
        <string>$UVICORN_PATH</string>
        <string>src.http_health:app</string>
        <string>--host</string>
        <string>0.0.0.0</string>
        <string>--port</string>
        <string>8082</string>
    </array>

    <key>WorkingDirectory</key>
    <string>$BACKEND_DIR</string>

    <key>EnvironmentVariables</key>
    <dict>
        <key>DATABASE_URL</key>
        <string>postgresql://tiktok:tiktok123@localhost:5432/tiktok_db</string>
        <key>PATH</key>
        <string>$BACKEND_DIR/venv/bin:/usr/local/bin:/usr/bin:/bin</string>
    </dict>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <true/>

    <key>StandardOutPath</key>
    <string>$BACKEND_DIR/logs/api.log</string>

    <key>StandardErrorPath</key>
    <string>$BACKEND_DIR/logs/api.error.log</string>
</dict>
</plist>
EOF

    # ═══════════════════════════════════════════════════════════════
    # SERVIÇO DO SCHEDULER
    # ═══════════════════════════════════════════════════════════════
    print_step "Criando serviço do Scheduler..."

    cat > "$LAUNCH_AGENTS_DIR/com.tiktok.scheduler.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.tiktok.scheduler</string>

    <key>ProgramArguments</key>
    <array>
        <string>$PYTHON_PATH</string>
        <string>start_scheduler.py</string>
    </array>

    <key>WorkingDirectory</key>
    <string>$BACKEND_DIR</string>

    <key>EnvironmentVariables</key>
    <dict>
        <key>DATABASE_URL</key>
        <string>postgresql://tiktok:tiktok123@localhost:5432/tiktok_db</string>
        <key>PATH</key>
        <string>$BACKEND_DIR/venv/bin:/usr/local/bin:/usr/bin:/bin</string>
        <key>PYTHONPATH</key>
        <string>$BACKEND_DIR</string>
    </dict>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <true/>

    <key>StandardOutPath</key>
    <string>$BACKEND_DIR/logs/scheduler.log</string>

    <key>StandardErrorPath</key>
    <string>$BACKEND_DIR/logs/scheduler.error.log</string>
</dict>
</plist>
EOF

    # Criar diretório de logs
    mkdir -p "$BACKEND_DIR/logs"

    # Carregar os serviços
    print_step "Carregando serviços..."
    launchctl unload "$LAUNCH_AGENTS_DIR/com.tiktok.api.plist" 2>/dev/null || true
    launchctl unload "$LAUNCH_AGENTS_DIR/com.tiktok.scheduler.plist" 2>/dev/null || true

    launchctl load "$LAUNCH_AGENTS_DIR/com.tiktok.api.plist"
    launchctl load "$LAUNCH_AGENTS_DIR/com.tiktok.scheduler.plist"

    print_success "Serviços carregados!"

    sleep 3

    print_step "Verificando status dos serviços..."
    if launchctl list | grep com.tiktok.api > /dev/null; then
        print_success "API está rodando"
    else
        print_warning "API pode não ter iniciado. Verifique: launchctl list | grep tiktok"
    fi

    if launchctl list | grep com.tiktok.scheduler > /dev/null; then
        print_success "Scheduler está rodando"
    else
        print_warning "Scheduler pode não ter iniciado. Verifique: launchctl list | grep tiktok"
    fi

    print_success "Configuração dos serviços concluída!"
    print_info "Para ver logs: tail -f $BACKEND_DIR/logs/api.log"
    print_info "Para parar: launchctl unload ~/Library/LaunchAgents/com.tiktok.*.plist"
    print_info "Para iniciar: launchctl load ~/Library/LaunchAgents/com.tiktok.*.plist"
}

# ════════════════════════════════════════════════════════════════════════════
# BUILD DO FRONTEND
# ════════════════════════════════════════════════════════════════════════════

setup_frontend() {
    if [ "$SKIP_FE" = true ]; then
        print_warning "Pulando build do frontend (--skip-fe)"
        return
    fi

    print_header "CONFIGURANDO FRONTEND"

    cd "$FRONTEND_DIR"

    # Verificar se package.json existe
    if [ ! -f "package.json" ]; then
        print_error "package.json não encontrado em $FRONTEND_DIR"
        exit 1
    fi

    print_step "Instalando dependências do Node.js..."
    # Remover package-lock.json para evitar problemas com native bindings
    rm -f package-lock.json
    npm install
    print_success "Dependências do frontend instaladas"

    print_step "Executando build do frontend..."
    npx vite build
    print_success "Build do frontend concluído"

    # Copiar build para o backend
    if [ -d "dist" ]; then
        print_step "Copiando build para o backend..."
        rm -rf "$BACKEND_DIR/web"
        cp -r dist "$BACKEND_DIR/web"
        print_success "Build copiado para beckend/web/"
    fi

    print_success "Frontend configurado com sucesso!"
}

# ════════════════════════════════════════════════════════════════════════════
# SETUP DO NGINX (macOS)
# ════════════════════════════════════════════════════════════════════════════

setup_nginx() {
    if [ "$SKIP_NGINX" = true ]; then
        print_warning "Pulando configuração do Nginx (--skip-nginx)"
        return
    fi

    print_header "CONFIGURANDO NGINX (macOS)"

    # Verificar se Nginx está instalado
    print_step "Verificando instalação do Nginx..."
    if ! command -v nginx &> /dev/null; then
        print_warning "Nginx não está instalado. Instalando via Homebrew..."
        brew install nginx
        print_success "Nginx instalado"
    else
        print_success "Nginx já está instalado"
    fi

    # Detectar IP do servidor (macOS)
    print_step "Detectando IP do servidor..."
    local SERVER_IP=$(ipconfig getifaddr en0 2>/dev/null || echo "localhost")
    print_info "IP detectado: $SERVER_IP"

    # Perguntar sobre domínio
    local DOMAIN=""
    local USE_DOMAIN=false

    if [ -t 0 ]; then  # Verifica se está em terminal interativo
        echo ""
        echo -ne "${CYAN}?${NC} Você tem um domínio configurado? [y/N]: "
        read -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo -ne "${CYAN}?${NC} Digite o domínio (ex: app.exemplo.com): "
            read DOMAIN
            if [ -n "$DOMAIN" ]; then
                USE_DOMAIN=true
                print_info "Domínio configurado: $DOMAIN"
            fi
        fi
    fi

    # Criar configuração do Nginx
    print_step "Criando configuração do Nginx..."

    # No macOS com Homebrew, o nginx.conf geralmente fica em /opt/homebrew/etc/nginx
    local NGINX_CONF_DIR="/opt/homebrew/etc/nginx"
    if [ ! -d "$NGINX_CONF_DIR" ]; then
        NGINX_CONF_DIR="/usr/local/etc/nginx"
    fi

    local NGINX_SERVERS_DIR="$NGINX_CONF_DIR/servers"
    mkdir -p "$NGINX_SERVERS_DIR"

    local NGINX_SITE_CONF="$NGINX_SERVERS_DIR/tiktok.conf"

    if [ "$USE_DOMAIN" = true ]; then
        # Configuração com domínio
        cat > "$NGINX_SITE_CONF" <<EOF
# Configuração HTTP (IP e Domínio)
server {
    listen 80;
    server_name $SERVER_IP $DOMAIN;

    # Logs
    access_log $NGINX_CONF_DIR/logs/tiktok-access.log;
    error_log $NGINX_CONF_DIR/logs/tiktok-error.log;

    # Tamanho máximo de upload (para vídeos)
    client_max_body_size 500M;

    # Proxy para a aplicação
    location / {
        proxy_pass http://localhost:8082;
        proxy_http_version 1.1;

        # Headers para WebSocket e proxy reverso
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;

        # Timeouts para uploads longos
        proxy_connect_timeout 600;
        proxy_send_timeout 600;
        proxy_read_timeout 600;
        send_timeout 600;
    }
}
EOF
        print_info "Configuração criada para domínio: $DOMAIN"
    else
        # Configuração apenas com IP
        cat > "$NGINX_SITE_CONF" <<EOF
# Configuração HTTP (somente IP)
server {
    listen 8080;
    server_name $SERVER_IP localhost;

    # Logs
    access_log $NGINX_CONF_DIR/logs/tiktok-access.log;
    error_log $NGINX_CONF_DIR/logs/tiktok-error.log;

    # Tamanho máximo de upload (para vídeos)
    client_max_body_size 500M;

    # Proxy para a aplicação
    location / {
        proxy_pass http://localhost:8082;
        proxy_http_version 1.1;

        # Headers para WebSocket e proxy reverso
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;

        # Timeouts para uploads longos
        proxy_connect_timeout 600;
        proxy_send_timeout 600;
        proxy_read_timeout 600;
        send_timeout 600;
    }
}
EOF
        print_info "Configuração criada para IP: $SERVER_IP (porta 8080)"
        print_warning "No macOS, porta 80 requer sudo. Usando porta 8080."
    fi

    # Garantir que o diretório de logs existe
    mkdir -p "$NGINX_CONF_DIR/logs"

    # Verificar se a diretiva 'include servers/*;' está no nginx.conf
    print_step "Verificando configuração principal do Nginx..."
    if ! grep -q "include.*servers/\*" "$NGINX_CONF_DIR/nginx.conf"; then
        print_info "Adicionando include para servers..."
        # Backup do nginx.conf
        cp "$NGINX_CONF_DIR/nginx.conf" "$NGINX_CONF_DIR/nginx.conf.backup"

        # Adicionar include antes do último '}'
        sed -i.bak '/^[[:space:]]*}[[:space:]]*$/i\    include servers/*;' "$NGINX_CONF_DIR/nginx.conf"
        print_success "Include adicionado ao nginx.conf"
    fi

    # Desabilitar servidor padrão que escuta na porta 8080 (evita conflitos)
    print_step "Desabilitando servidor padrão do Nginx..."
    if grep -q "listen.*8080" "$NGINX_CONF_DIR/nginx.conf" && ! grep -q "# Servidor padrão desativado" "$NGINX_CONF_DIR/nginx.conf"; then
        print_info "Comentando servidor padrão do nginx.conf..."
        # Criar backup se ainda não existir
        [ ! -f "$NGINX_CONF_DIR/nginx.conf.backup" ] && cp "$NGINX_CONF_DIR/nginx.conf" "$NGINX_CONF_DIR/nginx.conf.backup"

        # Comentar o bloco server padrão usando perl (mais confiável que sed para múltiplas linhas)
        perl -i -pe 'BEGIN{undef $/;} s/    server \{[^}]*listen\s+8080[^}]*\}/    # Servidor padrão desativado - usando configuração em servers\/tiktok.conf\n    #$&/smg' "$NGINX_CONF_DIR/nginx.conf"
        print_success "Servidor padrão desabilitado"
    else
        print_info "Servidor padrão já está desabilitado ou não existe"
    fi

    # Testar configuração
    print_step "Testando configuração do Nginx..."
    if nginx -t 2>&1 | grep -q "successful"; then
        print_success "Configuração válida"
    else
        print_error "Configuração inválida! Revise o arquivo $NGINX_SITE_CONF"
        return 1
    fi

    # Reiniciar Nginx usando brew services
    print_step "Reiniciando Nginx..."
    brew services restart nginx
    print_success "Nginx reiniciado"

    # Informações finais
    echo ""
    print_success "Nginx configurado com sucesso!"
    if [ "$USE_DOMAIN" = true ]; then
        print_info "Acesse: http://$DOMAIN"
    else
        print_info "Acesse: http://localhost:8080 ou http://$SERVER_IP:8080"
    fi
    echo ""
}

# ════════════════════════════════════════════════════════════════════════════
# VERIFICAÇÃO FINAL
# ════════════════════════════════════════════════════════════════════════════

final_verification() {
    print_header "VERIFICAÇÃO FINAL"

    print_step "Verificando PostgreSQL..."
    if docker ps | grep postgres > /dev/null; then
        print_success "PostgreSQL rodando"
    else
        print_error "PostgreSQL não está rodando"
    fi

    print_step "Verificando API..."
    if launchctl list | grep com.tiktok.api > /dev/null; then
        print_success "API rodando"
    else
        print_warning "API pode não estar rodando (verificar com: launchctl list | grep tiktok)"
    fi

    print_step "Verificando Scheduler..."
    if launchctl list | grep com.tiktok.scheduler > /dev/null; then
        print_success "Scheduler rodando"
    else
        print_warning "Scheduler pode não estar rodando (verificar com: launchctl list | grep tiktok)"
    fi

    print_step "Verificando build do frontend..."
    if [ -d "$BACKEND_DIR/web" ]; then
        print_success "Build do frontend encontrado"
    else
        print_warning "Build do frontend não encontrado"
    fi

    print_step "Verificando Nginx..."
    if brew services list | grep nginx | grep started > /dev/null; then
        print_success "Nginx rodando"
    else
        print_warning "Nginx pode não estar rodando (verificar com: brew services list)"
    fi

    echo ""
}

# ════════════════════════════════════════════════════════════════════════════
# EXIBIR INFORMAÇÕES FINAIS
# ════════════════════════════════════════════════════════════════════════════

show_final_info() {
    print_header "DEPLOY CONCLUÍDO COM SUCESSO! 🎉"

    # Detectar IP para mostrar nas informações
    local SERVER_IP=$(ipconfig getifaddr en0 2>/dev/null || echo "localhost")
    local ACCESS_URL="http://localhost:8080"

    # Se Nginx não foi configurado, usar localhost:8082
    if [ "$SKIP_NGINX" = true ]; then
        ACCESS_URL="http://localhost:8082"
    fi

    echo -e "${BOLD}Informações importantes:${NC}"
    echo ""
    echo -e "${GREEN}✓${NC} PostgreSQL:    ${CYAN}postgresql://localhost:5432/tiktok_db${NC}"
    echo -e "${GREEN}✓${NC} API Backend:   ${CYAN}http://localhost:8082${NC}"
    echo -e "${GREEN}✓${NC} Documentação:  ${CYAN}http://localhost:8082/docs${NC}"
    echo -e "${GREEN}✓${NC} Frontend:      ${CYAN}Build em beckend/web/${NC}"

    if [ "$SKIP_NGINX" = false ]; then
        echo -e "${GREEN}✓${NC} Aplicação:     ${CYAN}${ACCESS_URL}${NC}"
    fi

    echo ""
    echo -e "${BOLD}Credenciais padrão:${NC}"
    echo -e "  Username: ${CYAN}admin${NC}"
    echo -e "  Password: ${CYAN}admin123${NC}"
    echo -e "  ${YELLOW}⚠  Altere a senha após o primeiro login!${NC}"
    echo ""
    echo -e "${BOLD}Comandos úteis (macOS):${NC}"
    echo -e "  ${CYAN}launchctl list | grep tiktok${NC}              # Ver status dos serviços"
    echo -e "  ${CYAN}tail -f ~/work/tiktok-react/beckend/logs/api.log${NC}     # Ver logs da API"
    echo -e "  ${CYAN}tail -f ~/work/tiktok-react/beckend/logs/scheduler.log${NC} # Ver logs do Scheduler"
    echo -e "  ${CYAN}docker compose logs -f postgres${NC}           # Logs do PostgreSQL"
    echo -e "  ${CYAN}brew services list${NC}                        # Ver serviços do Homebrew"

    if [ "$SKIP_NGINX" = false ]; then
        echo -e "  ${CYAN}brew services restart nginx${NC}               # Reiniciar Nginx"
        echo -e "  ${CYAN}tail -f /opt/homebrew/etc/nginx/logs/tiktok-error.log${NC}  # Logs do Nginx"
    fi

    echo ""
    echo -e "${BOLD}Para parar os serviços:${NC}"
    echo -e "  ${CYAN}launchctl unload ~/Library/LaunchAgents/com.tiktok.api.plist${NC}"
    echo -e "  ${CYAN}launchctl unload ~/Library/LaunchAgents/com.tiktok.scheduler.plist${NC}"
    echo -e "  ${CYAN}brew services stop nginx${NC}"
    echo -e "  ${CYAN}docker compose down${NC}  # (no diretório beckend/)"

    echo ""
    echo -e "${BOLD}Próximos passos:${NC}"
    echo -e "  1. Acesse ${CYAN}${ACCESS_URL}${NC}"
    echo -e "  2. Faça login com as credenciais padrão"
    echo -e "  3. ${YELLOW}Altere a senha do admin${NC}"
    echo -e "  4. Configure suas contas TikTok"
    echo -e "  5. Comece a agendar vídeos!"
    echo ""
}

# ════════════════════════════════════════════════════════════════════════════
# PARSING DE ARGUMENTOS
# ════════════════════════════════════════════════════════════════════════════

show_help() {
    echo "Uso: $0 [OPÇÕES]"
    echo ""
    echo "Opções:"
    echo "  --skip-db        Pula o setup do banco de dados"
    echo "  --skip-fe        Pula o build do frontend"
    echo "  --skip-nginx     Pula a configuração do Nginx"
    echo "  --dev            Modo desenvolvimento (não instala serviços launchd nem nginx)"
    echo "  --help           Mostra esta ajuda"
    echo ""
    echo "Exemplos:"
    echo "  $0                    # Deploy completo"
    echo "  $0 --skip-db          # Deploy sem recriar o banco"
    echo "  $0 --skip-nginx       # Deploy sem configurar Nginx"
    echo "  $0 --dev              # Deploy em modo desenvolvimento"
    exit 0
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --skip-db)
                SKIP_DB=true
                shift
                ;;
            --skip-fe)
                SKIP_FE=true
                shift
                ;;
            --skip-nginx)
                SKIP_NGINX=true
                shift
                ;;
            --dev)
                DEV_MODE=true
                SKIP_NGINX=true  # Em modo dev, não configura nginx
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
    # Clear screen
    clear 2>/dev/null || true

    echo -e "${BOLD}${CYAN}"
    echo "╔═══════════════════════════════════════════════════════════════════╗"
    echo "║                                                                   ║"
    echo "║       🚀  DEPLOY AUTOMÁTICO - TIKTOK REACT (macOS)  🚀            ║"
    echo "║                                                                   ║"
    echo "╚═══════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"

    print_info "Diretório do projeto: $SCRIPT_DIR"
    print_info "Backend: $BACKEND_DIR"
    print_info "Frontend: $FRONTEND_DIR"
    echo ""

    # Parsing de argumentos
    parse_args "$@"

    print_info "Iniciando deploy automático para macOS..."
    echo ""
    sleep 2

    # Execução dos passos
    check_dependencies
    setup_database
    setup_backend

    if [ "$DEV_MODE" = false ]; then
        setup_services
    else
        print_warning "Modo desenvolvimento - serviços launchd não instalados"
        print_info "Para rodar manualmente:"
        print_command "cd beckend && source venv/bin/activate"
        print_command "uvicorn src.main:app --reload --host 0.0.0.0 --port 8082"
    fi

    setup_frontend
    setup_nginx
    final_verification
    show_final_info

    print_success "Deploy concluído com sucesso! 🎉"
}

# ════════════════════════════════════════════════════════════════════════════
# EXECUÇÃO
# ════════════════════════════════════════════════════════════════════════════

# Trap para capturar erros
trap 'print_error "Erro na linha $LINENO. Deploy falhou!"; exit 1' ERR

# Executar
main "$@"

#!/bin/bash
#
# ════════════════════════════════════════════════════════════════════════════
#  SCRIPT DE DEPLOY AUTOMÁTICO - TIKTOK REACT
# ════════════════════════════════════════════════════════════════════════════
#
#  Este script realiza o deploy completo da aplicação TikTok React em:
#  - VPS (Ubuntu/Debian)
#  - Máquina Local (Linux)
#
#  Passos executados:
#  1. ✅ Verificação de dependências (Docker, Python, Node, Nginx)
#  2. ✅ Setup do PostgreSQL (Docker Compose)
#  3. ✅ Setup do Backend (venv, requirements, migrações)
#  4. ✅ Setup dos Serviços (API + Agendador)
#  5. ✅ Build do Frontend (React + Vite)
#  6. ✅ Configuração do Nginx (reverse proxy)
#  7. ✅ Verificação final e testes
#
#  Uso:
#    ./deploy.sh                 # Deploy completo
#    ./deploy.sh --skip-db       # Pula setup do banco
#    ./deploy.sh --skip-fe       # Pula build do frontend
#    ./deploy.sh --skip-nginx    # Pula configuração do Nginx
#    ./deploy.sh --dev           # Modo desenvolvimento
#    ./deploy.sh --help          # Mostra ajuda
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

# Detecta distribuição (Ubuntu vs Debian)
OS_ID=$(source /etc/os-release && echo "${ID}")
OS_ID_LIKE=$(source /etc/os-release && echo "${ID_LIKE}")
UBUNTU_CODENAME=$(source /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
IS_UBUNTU=false
IS_DEBIAN=false
if [[ "${OS_ID}" == "ubuntu" || "${OS_ID_LIKE}" == *"ubuntu"* ]]; then
    IS_UBUNTU=true
fi
if [[ "${OS_ID}" == "debian" || "${OS_ID_LIKE}" == *"debian"* ]]; then
    IS_DEBIAN=true
fi

# Python bin a ser usado para venv (setado em check_dependencies)
PYBIN=""

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
# INSTALADOR RESILIENTE DE PYTHON
# ════════════════════════════════════════════════════════════════════════════

_install_python_resiliente() {
    # Tenta instalar Python 3.11; se indisponível, tenta 3.10; se falhar, tenta 3.12.
    # Último recurso: pyenv. Ao final, define PYBIN com o binário a ser usado na venv.
    local TARGET="3.11"
    local FALLBACKS=("3.10" "3.12")
    local ARCH="$(dpkg --print-architecture 2>/dev/null || echo unknown)"
    local CODENAME="$UBUNTU_CODENAME"

    print_info "Detectado: codename=${CODENAME:-desconhecido} arch=$ARCH"

    _install_via_apt() {
        local ver="$1"
        print_info "Tentando instalar Python ${ver} via APT..."
        sudo apt-get update -qq
        sudo apt-get install -y "python${ver}" "python${ver}-venv" "python${ver}-dev" python3-pip && return 0
        return 1
    }

    _ensure_deadsnakes() {
        if ! grep -Rq "ppa.launchpad.net/deadsnakes/ppa" /etc/apt/sources.list /etc/apt/sources.list.d 2>/dev/null; then
            print_info "Adicionando PPA deadsnakes..."
            sudo apt-get update -qq
            sudo apt-get install -y software-properties-common
            sudo add-apt-repository -y ppa:deadsnakes/ppa
        fi
    }

    # Ubuntu 20.04 geralmente precisa do deadsnakes
    if [ "$IS_UBUNTU" = true ] && [ "$CODENAME" = "focal" ]; then
        _ensure_deadsnakes
    fi

    # 1) Tenta 3.11
    if _install_via_apt "$TARGET"; then
        PYBIN="$(command -v python${TARGET})"
    else
        print_warning "python${TARGET} indisponível nos repositórios atuais."
        # 2) Tenta fallbacks
        for v in "${FALLBACKS[@]}"; do
            if _install_via_apt "$v"; then
                PYBIN="$(command -v python${v})"
                break
            fi
        done
    fi

    # 3) pyenv, último recurso
    if [ -z "$PYBIN" ]; then
        print_warning "Pacotes APT indisponíveis para Python 3.11/3.10/3.12. Partindo para pyenv..."
        sudo apt-get update -qq
        sudo apt-get install -y make build-essential libssl-dev zlib1g-dev \
            libbz2-dev libreadline-dev libsqlite3-dev curl llvm libncursesw5-dev \
            xz-utils tk-dev libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev git

        if [ ! -d "$HOME/.pyenv" ]; then
            git clone https://github.com/pyenv/pyenv.git "$HOME/.pyenv"
        fi

        export PYENV_ROOT="$HOME/.pyenv"
        export PATH="$PYENV_ROOT/bin:$PATH"
        eval "$(pyenv init -)"

        for vfull in "3.11.9" "3.10.14"; do
            if pyenv install -s "$vfull"; then
                pyenv global "$vfull"
                PYBIN="$(command -v python3)"
                break
            fi
        done

        if [ -z "$PYBIN" ]; then
            print_error "Falha ao instalar Python via pyenv."
            exit 1
        fi
    fi

    print_success "Python selecionado para venv: $($PYBIN --version 2>/dev/null)"

    # Limpa funções auxiliares para evitar efeitos colaterais
    unset -f _install_via_apt >/dev/null 2>&1 || true
    unset -f _ensure_deadsnakes >/dev/null 2>&1 || true
}

# ════════════════════════════════════════════════════════════════════════════
# VERIFICAÇÃO DE DEPENDÊNCIAS
# ════════════════════════════════════════════════════════════════════════════

check_dependencies() {
    print_header "VERIFICANDO E INSTALANDO DEPENDÊNCIAS DO SISTEMA"

    local needs_update=false

    update_apt_if_needed() {
        if [ "$needs_update" = false ]; then
            print_info "Atualizando cache de pacotes apt..."
            sudo apt update -qq
            needs_update=true
        fi
    }

    # ── DOCKER ───────────────────────────────────────────────────────────────
    print_step "Verificando Docker..."
    if command -v docker &> /dev/null; then
        local docker_version=$(docker --version | cut -d ' ' -f3 | tr -d ',')
        print_success "Docker instalado: $docker_version"
    else
        print_warning "Docker não encontrado. Instalando..."
        update_apt_if_needed
        sudo apt install -y ca-certificates curl gnupg lsb-release
        sudo install -m 0755 -d /etc/apt/keyrings
        curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg --yes 2>/dev/null || true
        sudo chmod a+r /etc/apt/keyrings/docker.gpg
        echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
          | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
        sudo apt update -qq
        sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
        sudo systemctl start docker
        sudo systemctl enable docker
        sudo usermod -aG docker $USER
        print_info "Aplicando permissões do grupo docker..."
        sudo chmod 666 /var/run/docker.sock || true
        print_success "Docker instalado com sucesso!"
    fi

    # ── DOCKER COMPOSE ───────────────────────────────────────────────────────
    print_step "Verificando Docker Compose..."
    is_docker_compose_valid() {
        if ! command -v docker-compose &> /dev/null; then return 1; fi
        local out; out=$(docker-compose --version 2>/dev/null) || return 1
        if [[ "$out" == *"vbuild"* ]] || [[ ${#out} -lt 20 ]]; then return 1; fi
        if [[ "$out" =~ v2\. ]] || [[ "$out" =~ v1\.29 ]]; then return 0; fi
        return 1
    }
    if is_docker_compose_valid; then
        local compose_version; compose_version=$(docker-compose --version | awk '{print $3}' | tr -d ',')
        print_success "Docker Compose válido instalado: v$compose_version"
    else
        print_warning "Docker Compose ausente, inválido ou desatualizado. Reinstalando..."
        sudo rm -f /usr/bin/docker-compose /usr/local/bin/docker-compose
        local compose_version
        compose_version=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep 'tag_name' | cut -d\" -f4)
        if [ -z "$compose_version" ]; then
            print_error "Falha ao obter a versão mais recente do Docker Compose"
            exit 1
        fi
        print_info "Instalando Docker Compose $compose_version..."
        sudo curl -L "https://github.com/docker/compose/releases/download/${compose_version}/docker-compose-$(uname -s)-$(uname -m)" \
            -o /usr/local/bin/docker-compose
        sudo chmod +x /usr/local/bin/docker-compose
        sudo ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose
        print_success "Docker Compose instalado: $compose_version"
    fi
    if ! docker compose version &> /dev/null; then
        update_apt_if_needed
        sudo apt install -y docker-compose-plugin 2>/dev/null || true
    fi

    # ── PYTHON (resiliente: 3.11 preferido) ──────────────────────────────────
    print_step "Verificando Python (3.11 preferido)..."
    if command -v python3.11 >/dev/null 2>&1; then
        PYBIN="$(command -v python3.11)"
        print_success "Python 3.11 disponível: $($PYBIN --version)"
    else
        _install_python_resiliente
    fi

    # ── PIP e VENV ──────────────────────────────────────────────────────────
    print_step "Verificando pip/venv..."
    if ! "$PYBIN" -m pip --version >/dev/null 2>&1; then
        update_apt_if_needed
        sudo apt install -y python3-pip || true
    fi
    if ! "$PYBIN" -m venv -h >/dev/null 2>&1; then
        local MM; MM="$($PYBIN -V | awk '{print $2}' | cut -d'.' -f1,2)"
        update_apt_if_needed
        sudo apt install -y "python${MM}-venv" || sudo apt install -y python3-venv || true
    fi
    print_success "pip/venv OK com $($PYBIN -V)"

    # ── NODE.JS 20+ ─────────────────────────────────────────────────────────
    print_step "Verificando Node.js..."
    if command -v node &> /dev/null; then
        local node_major; node_major=$(node -v | tr -d 'v' | cut -d'.' -f1)
        local node_full; node_full=$(node -v)
        if [ "$node_major" -lt 20 ]; then
            print_warning "Node.js $node_full instalado (precisa v20+). Atualizando..."
            sudo apt remove -y nodejs npm 2>/dev/null || true
            curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
            sudo apt install -y nodejs
            node_full=$(node -v)
            print_success "Node.js atualizado: $node_full"
        else
            print_success "Node.js instalado: $node_full"
        fi
    else
        print_warning "Node.js não encontrado. Instalando Node.js 20..."
        curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
        sudo apt install -y nodejs
        local node_full; node_full=$(node -v)
        print_success "Node.js instalado: $node_full"
    fi

    # ── NPM ─────────────────────────────────────────────────────────────────
    print_step "Verificando npm..."
    if command -v npm &> /dev/null; then
        local npm_version=$(npm --version)
        print_success "npm instalado: $npm_version"
    else
        print_warning "npm não encontrado. Instalando..."
        sudo apt install -y npm
        local npm_version=$(npm --version)
        print_success "npm instalado: $npm_version"
    fi

    # ── GOOGLE CHROME (Selenium) ────────────────────────────────────────────
    print_step "Verificando Google Chrome..."
    if command -v google-chrome &> /dev/null; then
        local chrome_version; chrome_version=$(google-chrome --version 2>/dev/null || true)
        print_success "Google Chrome instalado: ${chrome_version:-versão desconhecida}"
    else
        print_warning "Google Chrome não encontrado. Instalando..."
        update_apt_if_needed

        # Repositório Chrome (forma compatível com 20.04+)
        sudo install -m 0755 -d /etc/apt/keyrings
        curl -fsSL https://dl.google.com/linux/linux_signing_key.pub | sudo gpg --dearmor -o /etc/apt/keyrings/google-linux.gpg
        sudo chmod a+r /etc/apt/keyrings/google-linux.gpg
        sudo tee /etc/apt/sources.list.d/google-chrome.list <<'EOF' >/dev/null
### THIS FILE IS AUTOMATICALLY CONFIGURED
# You may comment out this entry, but any other modifications may be lost.
deb [arch=amd64 signed-by=/etc/apt/keyrings/google-linux.gpg] http://dl.google.com/linux/chrome/deb/ stable main
EOF
        sudo apt update -qq
        sudo apt install -y google-chrome-stable || print_warning "Falha ao instalar Google Chrome. Instale manualmente se precisar do Selenium."
        if command -v google-chrome &> /dev/null; then
            chrome_version=$(google-chrome --version 2>/dev/null || true)
            print_success "Google Chrome instalado: ${chrome_version:-versão desconhecida}"
        else
            print_warning "Chrome ainda indisponível."
        fi
    fi

    # ── FERRAMENTAS EXTRAS ──────────────────────────────────────────────────
    print_step "Verificando ferramentas adicionais..."
    local extra_tools=("curl" "git" "build-essential")
    local missing_tools=()
    for tool in "${extra_tools[@]}"; do
        if ! dpkg -l | grep -q "^ii  $tool "; then
            missing_tools+=("$tool")
        fi
    done
    if [ ${#missing_tools[@]} -gt 0 ]; then
        print_info "Instalando ferramentas adicionais: ${missing_tools[*]}"
        update_apt_if_needed
        sudo apt install -y "${missing_tools[@]}"
        print_success "Ferramentas adicionais instaladas"
    else
        print_success "Todas as ferramentas adicionais estão instaladas"
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

    if [ ! -f "docker-compose.yml" ]; then
        print_error "docker-compose.yml não encontrado em $BACKEND_DIR"
        exit 1
    fi

    print_step "Parando containers existentes..."
    docker-compose down 2>/dev/null || true
    print_success "Containers parados"

    print_step "Iniciando PostgreSQL..."
    docker-compose up -d postgres

    print_step "Aguardando PostgreSQL ficar pronto..."
    local max_attempts=30
    local attempt=0
    while [ $attempt -lt $max_attempts ]; do
        if docker-compose exec -T postgres pg_isready -U tiktok &>/dev/null; then
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

    # Criar ambiente virtual com PYBIN detectado
    print_step "Criando ambiente virtual Python..."
    if [ -z "$PYBIN" ]; then
        # fallback extremo: usa python3 padrão
        PYBIN="$(command -v python3 || true)"
    fi
    if [ -z "$PYBIN" ]; then
        print_error "Python não encontrado no PATH."
        exit 1
    fi

    if [ ! -d "venv" ] || [ ! -f "venv/bin/activate" ]; then
        print_info "Criando ou reparando ambiente virtual com $($PYBIN -V)..."
        if "$PYBIN" -m venv venv; then
            print_success "Ambiente virtual pronto"
        else
            print_warning "Falha ao criar o ambiente virtual. Instalando suporte a venv..."
            if command -v apt-get &>/dev/null; then
                sudo apt-get update -qq || true
                local MM; MM="$($PYBIN -V | awk '{print $2}' | cut -d'.' -f1,2)"
                sudo apt-get install -y "python${MM}-venv" || sudo apt-get install -y python3-venv || true
            fi
            "$PYBIN" -m venv venv || { print_error "Falha ao preparar o ambiente virtual"; exit 1; }
            print_success "Ambiente virtual pronto após instalar venv"
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
    # shellcheck source=/dev/null
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
# SETUP DOS SERVIÇOS (API + AGENDADOR)
# ════════════════════════════════════════════════════════════════════════════

setup_services() {
    print_header "CONFIGURANDO SERVIÇOS SYSTEMD"

    cd "$BACKEND_DIR"

    if [ ! -f "manage.sh" ]; then
        print_error "manage.sh não encontrado"
        exit 1
    fi

    source venv/bin/activate

    print_step "Instalando serviços (API + Agendador)..."
    ./manage.sh all install || true
    print_success "Serviços instalados e habilitados"

    print_step "Iniciando serviços..."
    ./manage.sh all start || print_warning "Serviços podem não ter iniciado corretamente"

    sleep 3

    print_step "Verificando status dos serviços..."
    ./manage.sh all status || print_warning "Verifique os serviços manualmente com: cd beckend && ./manage.sh all status"

    print_success "Configuração dos serviços concluída!"
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

    if [ ! -f "package.json" ]; then
        print_error "package.json não encontrado em $FRONTEND_DIR"
        exit 1
    fi

    print_step "Instalando dependências do Node.js..."
    rm -f package-lock.json
    npm install
    print_success "Dependências do frontend instaladas"

    print_step "Executando build do frontend..."
    npx vite build
    print_success "Build do frontend concluído"

    if [ -d "dist" ]; then
        print_step "Copiando build para o backend..."
        rm -rf "$BACKEND_DIR/web"
        cp -r dist "$BACKEND_DIR/web"
        print_success "Build copiado para beckend/web/"
    fi

    print_success "Frontend configurado com sucesso!"
}

# ════════════════════════════════════════════════════════════════════════════
# SETUP DO NGINX
# ════════════════════════════════════════════════════════════════════════════

setup_nginx() {
    if [ "$SKIP_NGINX" = true ]; then
        print_warning "Pulando configuração do Nginx (--skip-nginx)"
        return
    fi

    print_header "CONFIGURANDO NGINX"

    print_step "Verificando instalação do Nginx..."
    if ! command -v nginx &> /dev/null; then
        print_warning "Nginx não está instalado. Instalando..."
        sudo apt update
        sudo apt install -y nginx
        print_success "Nginx instalado"
    else
        print_success "Nginx já está instalado"
    fi

    print_step "Detectando IP do servidor..."
    local SERVER_IP
    SERVER_IP=$(hostname -I | awk '{print $1}')
    if [ -z "$SERVER_IP" ]; then
        SERVER_IP=$(curl -s ifconfig.me 2>/dev/null || echo "localhost")
    fi
    print_info "IP detectado: $SERVER_IP"

    local DOMAIN=""
    local USE_DOMAIN=false

    if [ -t 0 ]; then
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

    print_step "Criando configuração do Nginx..."
    local NGINX_CONF="/tmp/tiktok-nginx-$$.conf"

    if [ "$USE_DOMAIN" = true ]; then
        cat > "$NGINX_CONF" <<EOF
# Configuração HTTP (IP e Domínio)
server {
    listen 80;
    listen [::]:80;
    server_name $SERVER_IP $DOMAIN;

    access_log /var/log/nginx/tiktok-access.log;
    error_log /var/log/nginx/tiktok-error.log;

    client_max_body_size 500M;

    location / {
        proxy_pass http://localhost:8082;
        proxy_http_version 1.1;

        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;

        proxy_connect_timeout 600;
        proxy_send_timeout 600;
        proxy_read_timeout 600;
        send_timeout 600;
    }
}
EOF
        print_info "Configuração criada para domínio: $DOMAIN"
        print_info "Para habilitar HTTPS, execute: sudo certbot --nginx -d $DOMAIN"
    else
        cat > "$NGINX_CONF" <<EOF
# Configuração HTTP (somente IP)
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name $SERVER_IP _;

    access_log /var/log/nginx/tiktok-access.log;
    error_log /var/log/nginx/tiktok-error.log;

    client_max_body_size 500M;

    location / {
        proxy_pass http://localhost:8082;
        proxy_http_version 1.1;

        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;

        proxy_connect_timeout 600;
        proxy_send_timeout 600;
        proxy_read_timeout 600;
        send_timeout 600;
    }
}
EOF
        print_info "Configuração criada para IP: $SERVER_IP"
    fi

    print_step "Instalando configuração..."
    sudo cp "$NGINX_CONF" /etc/nginx/sites-available/tiktok
    rm -f "$NGINX_CONF"

    if [ ! -L /etc/nginx/sites-enabled/tiktok ]; then
        sudo ln -sf /etc/nginx/sites-available/tiktok /etc/nginx/sites-enabled/tiktok
        print_success "Site habilitado"
    else
        print_info "Site já está habilitado"
    fi

    if [ -L /etc/nginx/sites-enabled/default ]; then
        print_step "Removendo configuração default..."
        sudo rm -f /etc/nginx/sites-enabled/default
        print_success "Configuração default removida"
    fi

    print_step "Testando configuração do Nginx..."
    if sudo nginx -t; then
        print_success "Configuração válida"
    else
        print_error "Configuração inválida! Revise o arquivo /etc/nginx/sites-available/tiktok"
        return 1
    fi

    print_step "Reiniciando Nginx..."
    sudo systemctl restart nginx
    sudo systemctl enable nginx
    print_success "Nginx reiniciado e habilitado"

    if [ "$USE_DOMAIN" = true ]; then
        echo ""
        print_step "Configurando SSL/HTTPS com Let's Encrypt..."

        if ! command -v certbot &> /dev/null; then
            print_info "Instalando Certbot..."
            sudo apt update
            sudo apt install -y certbot python3-certbot-nginx
            print_success "Certbot instalado"
        else
            if ! dpkg -l | grep -q python3-certbot-nginx; then
                print_info "Instalando plugin Nginx do Certbot..."
                sudo apt update
                sudo apt install -y python3-certbot-nginx
                print_success "Plugin Nginx do Certbot instalado"
            else
                print_success "Certbot já instalado"
            fi
        fi

        echo ""
        echo -ne "${CYAN}?${NC} Deseja configurar SSL/HTTPS agora? [Y/n]: "
        read -n 1 -r
        echo ""

        if [[ ! $REPLY =~ ^[Nn]$ ]]; then
            print_info "Configurando certificado SSL para $DOMAIN..."
            print_warning "Certifique-se que o DNS do domínio está apontando para este servidor!"
            echo ""

            echo -ne "${CYAN}?${NC} Digite seu email para notificações do Let's Encrypt: "
            read LE_EMAIL

            if [ -n "$LE_EMAIL" ]; then
                print_info "Obtendo certificado SSL..."
                sudo certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos --email "$LE_EMAIL" --redirect

                if [ $? -eq 0 ]; then
                    print_success "SSL configurado com sucesso!"
                    print_info "Acesse: https://$DOMAIN"

                    echo ""
                    print_step "Configurando renovação automática do certificado..."
                    if sudo systemctl is-enabled certbot.timer &>/dev/null; then
                        print_success "Timer de renovação já está habilitado"
                    else
                        sudo systemctl enable certbot.timer
                        print_success "Timer de renovação habilitado"
                    fi
                    if sudo systemctl is-active certbot.timer &>/dev/null; then
                        print_success "Timer de renovação está ativo"
                    else
                        sudo systemctl start certbot.timer
                        print_success "Timer de renovação iniciado"
                    fi
                    print_info "Testando processo de renovação..."
                    if sudo certbot renew --dry-run &>/dev/null; then
                        print_success "Teste de renovação passou!"
                    else
                        print_warning "Teste de renovação falhou, mas certificado está instalado"
                    fi
                    sudo mkdir -p /etc/letsencrypt/renewal-hooks/post
                    echo '#!/bin/bash' | sudo tee /etc/letsencrypt/renewal-hooks/post/nginx-reload.sh > /dev/null
                    echo 'systemctl reload nginx' | sudo tee -a /etc/letsencrypt/renewal-hooks/post/nginx-reload.sh > /dev/null
                    sudo chmod +x /etc/letsencrypt/renewal-hooks/post/nginx-reload.sh
                    print_success "Hook de pós-renovação configurado (reload Nginx)"

                    echo ""
                    print_success "✅ Renovação automática configurada!"
                    print_info "Certificado será renovado automaticamente a cada 90 dias"
                    print_info "Próxima verificação: $(sudo systemctl list-timers certbot.timer | grep certbot.timer | awk '{print $1, $2}')"
                else
                    print_error "Falha ao configurar SSL"
                    print_warning "Verifique se o DNS está correto e tente manualmente:"
                    print_info "sudo certbot --nginx -d $DOMAIN"
                fi
            else
                print_warning "Email não fornecido. SSL não configurado."
                print_info "Configure manualmente depois: sudo certbot --nginx -d $DOMAIN"
            fi
        else
            print_warning "SSL não configurado agora."
            print_info "Para configurar depois: sudo certbot --nginx -d $DOMAIN"
        fi
    fi

    echo ""
    print_success "Nginx configurado com sucesso!"
    if [ "$USE_DOMAIN" = true ]; then
        print_info "Acesse: http://$DOMAIN (ou https:// se configurou SSL)"
    else
        print_info "Acesse: http://$SERVER_IP"
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
    if systemctl is-active --quiet tiktok-api 2>/dev/null; then
        print_success "API rodando"
    else
        print_warning "API pode não estar rodando (verificar com: systemctl status tiktok-api)"
    fi

    print_step "Verificando Agendador..."
    if systemctl is-active --quiet tiktok-scheduler 2>/dev/null; then
        print_success "Agendador rodando"
    else
        print_warning "Agendador pode não estar rodando (verificar com: systemctl status tiktok-scheduler)"
    fi

    print_step "Verificando build do frontend..."
    if [ -d "$BACKEND_DIR/web" ]; then
        print_success "Build do frontend encontrado"
    else
        print_warning "Build do frontend não encontrado"
    fi

    print_step "Verificando Nginx..."
    if systemctl is-active --quiet nginx 2>/dev/null; then
        print_success "Nginx rodando"
    else
        print_warning "Nginx pode não estar rodando (verificar com: systemctl status nginx)"
    fi

    echo ""
}

# ════════════════════════════════════════════════════════════════════════════
# EXIBIR INFORMAÇÕES FINAIS
# ════════════════════════════════════════════════════════════════════════════

show_final_info() {
    print_header "DEPLOY CONCLUÍDO COM SUCESSO! 🎉"

    local SERVER_IP=$(hostname -I | awk '{print $1}' 2>/dev/null || echo "localhost")
    local ACCESS_URL="http://$SERVER_IP"
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
    echo -e "${BOLD}Comandos úteis:${NC}"
    echo -e "  ${CYAN}cd beckend && ./manage.sh all status${NC}     # Ver status dos serviços"
    echo -e "  ${CYAN}cd beckend && ./manage.sh all restart${NC}    # Reiniciar serviços"
    echo -e "  ${CYAN}cd beckend && ./manage.sh all logs${NC}       # Ver logs"
    echo -e "  ${CYAN}docker-compose logs -f postgres${NC}          # Logs do PostgreSQL"

    if [ "$SKIP_NGINX" = false ]; then
        echo -e "  ${CYAN}sudo systemctl status nginx${NC}              # Status do Nginx"
        echo -e "  ${CYAN}sudo tail -f /var/log/nginx/tiktok-error.log${NC}  # Logs do Nginx"
    fi

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
    echo "  --dev            Modo desenvolvimento (não instala serviços systemd nem nginx)"
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
            --skip-db)     SKIP_DB=true; shift ;;
            --skip-fe)     SKIP_FE=true; shift ;;
            --skip-nginx)  SKIP_NGINX=true; shift ;;
            --dev)         DEV_MODE=true; SKIP_NGINX=true; shift ;;
            --help|-h)     show_help ;;
            *)             print_error "Opção desconhecida: $1"; show_help ;;
        esac
    done
}

# ════════════════════════════════════════════════════════════════════════════
# FUNÇÃO PRINCIPAL
# ════════════════════════════════════════════════════════════════════════════

main() {
    if [ -n "$TERM" ] && [ "$TERM" != "dumb" ]; then
        clear 2>/dev/null || true
    fi

    echo -e "${BOLD}${CYAN}"
    echo "╔═══════════════════════════════════════════════════════════════════╗"
    echo "║                                                                   ║"
    echo "║           🚀  DEPLOY AUTOMÁTICO - TIKTOK REACT  🚀                ║"
    echo "║                                                                   ║"
    echo "╚═══════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"

    print_info "Diretório do projeto: $SCRIPT_DIR"
    print_info "Backend: $BACKEND_DIR"
    print_info "Frontend: $FRONTEND_DIR"
    echo ""

    parse_args "$@"

    print_info "Iniciando deploy automático..."
    echo ""
    sleep 2

    check_dependencies
    setup_database
    setup_backend

    if [ "$DEV_MODE" = false ]; then
        setup_services
    else
        print_warning "Modo desenvolvimento - serviços systemd não instalados"
        print_info "Para rodar manualmente:"
        print_command "cd beckend && source venv/bin/activate"
        print_command "uvicorn src.main:app --reload --host 0.0.0.0 --port 8000"
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

trap 'print_error "Erro na linha $LINENO. Deploy falhou!"; exit 1' ERR
main "$@"

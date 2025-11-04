#!/bin/bash
#
# ════════════════════════════════════════════════════════════════════════════
#  SCRIPT DE DEPLOY AUTOMÁTICO - TIKTOK REACT (DEBIAN)
# ════════════════════════════════════════════════════════════════════════════
#
#  Suporte: Debian 12 (bookworm), Debian 11 (bullseye). Fallback pyenv em versões antigas.
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
#    ./deploy_debian.sh                 # Deploy completo
#    ./deploy_debian.sh --skip-db       # Pula setup do banco
#    ./deploy_debian.sh --skip-fe       # Pula build do frontend
#    ./deploy_debian.sh --skip-nginx    # Pula configuração do Nginx
#    ./deploy_debian.sh --dev           # Modo desenvolvimento
#    ./deploy_debian.sh --help          # Mostra ajuda
#
# ════════════════════════════════════════════════════════════════════════════

set -e

# ────────────────────────────────────────────────────────────────────────────
# CONFIG
# ────────────────────────────────────────────────────────────────────────────
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BACKEND_DIR="$SCRIPT_DIR/beckend"
FRONTEND_DIR="$SCRIPT_DIR"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'
MAGENTA='\033[0;35m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

SKIP_DB=false; SKIP_FE=false; SKIP_NGINX=false; DEV_MODE=false

. /etc/os-release
OS_ID="${ID:-debian}"
OS_LIKE="${ID_LIKE:-debian}"
CODENAME="${VERSION_CODENAME:-$(echo "$VERSION" | awk '{print tolower($1)}')}"
IS_DEBIAN=true

PYBIN=""

# ────────────────────────────────────────────────────────────────────────────
# UI helpers
# ────────────────────────────────────────────────────────────────────────────
print_header(){ echo -e "\n${BOLD}${CYAN}════════════════════════════════════════════════════════════════${NC}\n${BOLD}${CYAN}  $1${NC}\n${BOLD}${CYAN}════════════════════════════════════════════════════════════════${NC}\n"; }
print_step(){ echo -e "${BOLD}${MAGENTA}▶${NC} ${BOLD}$1${NC}"; }
print_info(){ echo -e "${BLUE}ℹ${NC} $1"; }
print_success(){ echo -e "${GREEN}✓${NC} $1"; }
print_warning(){ echo -e "${YELLOW}⚠${NC} $1"; }
print_error(){ echo -e "${RED}✗${NC} $1"; }
print_command(){ echo -e "${CYAN}  →${NC} $1"; }

# ────────────────────────────────────────────────────────────────────────────
# Python (Debian-first): 3.11 direto no bookworm, backports no bullseye, pyenv fallback
# ────────────────────────────────────────────────────────────────────────────
_install_python_resiliente_debian() {
  print_info "Debian codename: ${CODENAME:-desconhecido}"

  _apt_install_py () {
    local ver="$1"
    sudo apt-get update -qq
    sudo apt-get install -y "python${ver}" "python${ver}-venv" "python${ver}-dev" python3-pip && return 0
    return 1
  }

  # Bookworm: python3.11 já está no main
  if [[ "$CODENAME" == "bookworm" ]]; then
    if _apt_install_py "3.11"; then
      PYBIN="$(command -v python3.11)"
      print_success "Python via APT: $($PYBIN -V)"
      return 0
    fi
    print_warning "Falha ao instalar python3.11 no bookworm, tentando 3.10..."
    if _apt_install_py "3.10"; then
      PYBIN="$(command -v python3.10)"; print_success "Python via APT: $($PYBIN -V)"; return 0
    fi
  fi

  # Bullseye: tentar backports (3.11 costuma estar disponível)
  if [[ "$CODENAME" == "bullseye" ]]; then
    print_info "Habilitando bullseye-backports…"
    echo "deb http://deb.debian.org/debian bullseye-backports main" | sudo tee /etc/apt/sources.list.d/bullseye-backports.list >/dev/null
    sudo apt-get update -qq

    if sudo apt-get -t bullseye-backports install -y python3.11 python3.11-venv python3.11-dev python3-pip; then
      PYBIN="$(command -v python3.11)"; print_success "Python via backports: $($PYBIN -V)"; return 0
    fi
    print_warning "python3.11 indisponível em backports, tentando 3.10…"
    if sudo apt-get -t bullseye-backports install -y python3.10 python3.10-venv python3.10-dev python3-pip; then
      PYBIN="$(command -v python3.10)"; print_success "Python via backports: $($PYBIN -V)"; return 0
    fi
  fi

  # Outras releases (buster/stretch) ou se tudo falhar: pyenv
  print_warning "Pacotes APT adequados indisponíveis. Usando pyenv…"
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
  print_success "Python via pyenv: $($PYBIN -V)"
}

# ────────────────────────────────────────────────────────────────────────────
# Dependências (Debian)
# ────────────────────────────────────────────────────────────────────────────
check_dependencies() {
  print_header "VERIFICANDO E INSTALANDO DEPENDÊNCIAS (DEBIAN)"

  # ── Docker
  print_step "Verificando Docker…"
  if command -v docker >/dev/null 2>&1; then
    print_success "Docker instalado: $(docker --version | awk '{print $3}' | tr -d ',')"
  else
    print_warning "Instalando Docker…"
    sudo apt-get update -qq
    sudo apt-get install -y ca-certificates curl gnupg lsb-release
    sudo install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/debian/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    sudo chmod a+r /etc/apt/keyrings/docker.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian ${CODENAME} stable" \
      | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null
    sudo apt-get update -qq
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    sudo systemctl enable --now docker
    sudo usermod -aG docker "$USER" || true
    sudo chmod 666 /var/run/docker.sock || true
    print_success "Docker instalado."
  fi

  # ── Docker Compose (binário v2 compat)
  print_step "Verificando Docker Compose…"
  if command -v docker-compose >/dev/null 2>&1; then
    out=$(docker-compose --version 2>/dev/null || true)
    if [[ "$out" =~ v2\. || "$out" =~ v1\.29 ]]; then
      print_success "docker-compose OK: $(echo "$out" | awk '{print $3}' | tr -d ',')"
    else
      NEED_INSTALL=true
    fi
  else
    NEED_INSTALL=true
  fi
  if [ "${NEED_INSTALL:-false}" = true ]; then
    print_warning "Instalando docker-compose (binário)…"
    sudo rm -f /usr/local/bin/docker-compose /usr/bin/docker-compose
    LATEST=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep tag_name | cut -d\" -f4)
    sudo curl -L "https://github.com/docker/compose/releases/download/${LATEST}/docker-compose-$(uname -s)-$(uname -m)" \
      -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    sudo ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose
    print_success "docker-compose instalado: ${LATEST}"
  fi
  if ! docker compose version >/dev/null 2>&1; then
    sudo apt-get install -y docker-compose-plugin || true
  fi

  # ── Python
  print_step "Verificando Python (3.11 preferido)…"
  if command -v python3.11 >/dev/null 2>&1; then
    PYBIN="$(command -v python3.11)"; print_success "Python disponível: $($PYBIN -V)"
  else
    _install_python_resiliente_debian
  fi

  # pip/venv
  print_step "Verificando pip/venv…"
  if ! "$PYBIN" -m pip --version >/dev/null 2>&1; then
    sudo apt-get install -y python3-pip || true
  fi
  if ! "$PYBIN" -m venv -h >/dev/null 2>&1; then
    MM="$($PYBIN -V | awk '{print $2}' | cut -d'.' -f1,2)"
    sudo apt-get install -y "python${MM}-venv" || sudo apt-get install -y python3-venv || true
  fi
  print_success "pip/venv OK com $($PYBIN -V)"

  # ── Node.js 20+
  print_step "Verificando Node.js…"
  if command -v node >/dev/null 2>&1; then
    MAJ=$(node -v | tr -d 'v' | cut -d'.' -f1)
    if [ "$MAJ" -lt 20 ]; then
      print_warning "Atualizando para Node 20…"
      sudo apt-get remove -y nodejs npm || true
      curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
      sudo apt-get install -y nodejs
    fi
  else
    print_warning "Instalando Node 20…"
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
    sudo apt-get install -y nodejs
  fi
  print_success "Node: $(node -v) | npm: $(npm -v)"

  # ── Google Chrome (Selenium)
  print_step "Verificando Google Chrome…"
  if command -v google-chrome >/dev/null 2>&1; then
    print_success "Chrome: $(google-chrome --version 2>/dev/null || echo instalado)"
  else
    print_warning "Instalando Google Chrome…"
    sudo install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://dl.google.com/linux/linux_signing_key.pub | sudo gpg --dearmor -o /etc/apt/keyrings/google-linux.gpg
    sudo chmod a+r /etc/apt/keyrings/google-linux.gpg
    sudo tee /etc/apt/sources.list.d/google-chrome.list <<'EOF' >/dev/null
### THIS FILE IS AUTOMATICALLY CONFIGURED
# You may comment out this entry, but any other modifications may be lost.
deb [arch=amd64 signed-by=/etc/apt/keyrings/google-linux.gpg] http://dl.google.com/linux/chrome/deb/ stable main
EOF
    sudo apt-get update -qq
    sudo apt-get install -y google-chrome-stable || print_warning "Falha ao instalar Chrome. Instale manualmente se precisar do Selenium."
    command -v google-chrome >/dev/null 2>&1 && print_success "Chrome: $(google-chrome --version)"
  fi

  # ── Extras
  print_step "Verificando ferramentas adicionais…"
  sudo apt-get install -y curl git build-essential
  print_success "Extras OK."

  echo; print_success "✅ Dependências Debian prontas!"; echo
}

# ────────────────────────────────────────────────────────────────────────────
# PostgreSQL (Docker)
# ────────────────────────────────────────────────────────────────────────────
setup_database() {
  $SKIP_DB && { print_warning "Pulando setup do banco (--skip-db)"; return; }
  print_header "CONFIGURANDO POSTGRESQL (DOCKER)"
  cd "$BACKEND_DIR"
  [ -f docker-compose.yml ] || { print_error "docker-compose.yml não encontrado em $BACKEND_DIR"; exit 1; }

  print_step "Parando containers…"; docker-compose down || true
  print_step "Iniciando PostgreSQL…"; docker-compose up -d postgres

  print_step "Aguardando PostgreSQL…"
  for i in {1..30}; do
    if docker-compose exec -T postgres pg_isready -U tiktok >/dev/null 2>&1; then
      print_success "PostgreSQL pronto!"; break
    fi; sleep 2
    [ "$i" = 30 ] && { print_error "PostgreSQL não ficou pronto."; exit 1; }
  done
  print_success "PostgreSQL rodando."
}

# ────────────────────────────────────────────────────────────────────────────
# Backend
# ────────────────────────────────────────────────────────────────────────────
setup_backend() {
  print_header "CONFIGURANDO BACKEND"
  cd "$BACKEND_DIR"

  print_step "Criando venv…"
  [ -n "$PYBIN" ] || PYBIN="$(command -v python3 || true)"
  [ -n "$PYBIN" ] || { print_error "Python não encontrado."; exit 1; }

  if [ ! -d venv ] || [ ! -f venv/bin/activate ]; then
    "$PYBIN" -m venv venv || {
      MM="$($PYBIN -V | awk '{print $2}' | cut -d'.' -f1,2)"
      sudo apt-get install -y "python${MM}-venv" || sudo apt-get install -y python3-venv || true
      "$PYBIN" -m venv venv
    }
    print_success "Venv criada."
  else
    print_info "Venv já existe."
  fi

  # shellcheck disable=SC1091
  source venv/bin/activate
  print_step "Instalando dependências Python…"
  pip install --upgrade pip setuptools wheel
  pip install -r requirements.txt
  print_success "Dependências ok."

  print_step "Permissões…"
  chmod +x manage.sh init_db.py setup_database.sh 2>/dev/null || true

  print_step "Migrações…"
  export DATABASE_URL="postgresql://tiktok:tiktok123@localhost:5432/tiktok_db"
  python init_db.py
  print_success "Migrações feitas."

  print_step "Estrutura de dados…"
  mkdir -p "$SCRIPT_DIR/videos" "$SCRIPT_DIR/posted" "$SCRIPT_DIR/profiles" "$SCRIPT_DIR/state"
  [ -f "$SCRIPT_DIR/state/schedules.json" ] || echo '[]' > "$SCRIPT_DIR/state/schedules.json"
  [ -f "$SCRIPT_DIR/state/logs.json" ] || echo '{"logs": []}' > "$SCRIPT_DIR/state/logs.json"
  print_success "Backend pronto."
}

# ────────────────────────────────────────────────────────────────────────────
# Serviços systemd
# ────────────────────────────────────────────────────────────────────────────
setup_services() {
  print_header "CONFIGURANDO SERVIÇOS SYSTEMD"
  cd "$BACKEND_DIR"
  [ -f manage.sh ] || { print_error "manage.sh não encontrado"; exit 1; }
  source venv/bin/activate
  print_step "Instalando serviços…"; ./manage.sh all install || true
  print_step "Iniciando…"; ./manage.sh all start || print_warning "Cheque manualmente."
  sleep 2
  print_step "Status…"; ./manage.sh all status || print_warning "Use: cd beckend && ./manage.sh all status"
  print_success "Serviços configurados."
}

# ────────────────────────────────────────────────────────────────────────────
# Frontend
# ────────────────────────────────────────────────────────────────────────────
setup_frontend() {
  $SKIP_FE && { print_warning "Pulando frontend (--skip-fe)"; return; }
  print_header "CONFIGURANDO FRONTEND"
  cd "$FRONTEND_DIR"
  [ -f package.json ] || { print_error "package.json não encontrado em $FRONTEND_DIR"; exit 1; }
  print_step "Instalando dependências…"; rm -f package-lock.json; npm install
  print_step "Build…"; npx vite build
  if [ -d dist ]; then
    print_step "Copiando build…"; rm -rf "$BACKEND_DIR/web"; cp -r dist "$BACKEND_DIR/web"
  fi
  print_success "Frontend pronto."
}

# ────────────────────────────────────────────────────────────────────────────
# Nginx
# ────────────────────────────────────────────────────────────────────────────
setup_nginx() {
  $SKIP_NGINX && { print_warning "Pulando Nginx (--skip-nginx)"; return; }
  print_header "CONFIGURANDO NGINX"

  print_step "Verificando Nginx…"
  if ! command -v nginx >/dev/null 2>&1; then
    sudo apt-get update -qq && sudo apt-get install -y nginx
  fi
  print_success "Nginx está instalado."

  print_step "Detectando IP…"
  SERVER_IP=$(hostname -I | awk '{print $1}')
  [ -n "$SERVER_IP" ] || SERVER_IP="localhost"
  print_info "IP: $SERVER_IP"

  DOMAIN=""; USE_DOMAIN=false
  if [ -t 0 ]; then
    echo -ne "${CYAN}?${NC} Domínio configurado? [y/N]: "; read -r -n1 ans; echo
    if [[ $ans =~ ^[Yy]$ ]]; then
      echo -ne "${CYAN}?${NC} Informe o domínio: "; read -r DOMAIN
      [ -n "$DOMAIN" ] && USE_DOMAIN=true && print_info "Domínio: $DOMAIN"
    fi
  fi

  print_step "Gerando configuração…"
  TMP="/tmp/tiktok-nginx-$$.conf"
  if $USE_DOMAIN; then
cat >"$TMP"<<EOF
server {
    listen 80;
    listen [::]:80;
    server_name $SERVER_IP $DOMAIN;

    access_log /var/log/nginx/tiktok-access.log;
    error_log  /var/log/nginx/tiktok-error.log;

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
        proxy_send_timeout    600;
        proxy_read_timeout    600;
        send_timeout          600;
    }
}
EOF
  else
cat >"$TMP"<<EOF
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name $SERVER_IP _;

    access_log /var/log/nginx/tiktok-access.log;
    error_log  /var/log/nginx/tiktok-error.log;

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
        proxy_send_timeout    600;
        proxy_read_timeout    600;
        send_timeout          600;
    }
}
EOF
  fi

  sudo cp "$TMP" /etc/nginx/sites-available/tiktok
  rm -f "$TMP"
  sudo ln -sf /etc/nginx/sites-available/tiktok /etc/nginx/sites-enabled/tiktok
  [ -L /etc/nginx/sites-enabled/default ] && { print_step "Removendo default…"; sudo rm -f /etc/nginx/sites-enabled/default; }

  print_step "Testando Nginx…"
  sudo nginx -t && { sudo systemctl restart nginx; sudo systemctl enable nginx; print_success "Nginx aplicado."; } || {
    print_error "Configuração inválida. Revise /etc/nginx/sites-available/tiktok"; exit 1; }

  if $USE_DOMAIN; then
    echo
    print_step "SSL (Let's Encrypt)…"
    if ! command -v certbot >/dev/null 2>&1; then
      sudo apt-get install -y certbot python3-certbot-nginx
    elif ! dpkg -l | grep -q python3-certbot-nginx; then
      sudo apt-get install -y python3-certbot-nginx
    fi
    echo -ne "${CYAN}?${NC} Deseja configurar SSL agora? [Y/n]: "; read -r -n1 s; echo
    if [[ ! $s =~ ^[Nn]$ ]]; then
      echo -ne "${CYAN}?${NC} Email para o Let's Encrypt: "; read -r LE_EMAIL
      if [ -n "$LE_EMAIL" ]; then
        sudo certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos --email "$LE_EMAIL" --redirect || print_warning "Falhou o certbot"
        sudo systemctl enable --now certbot.timer || true
        sudo mkdir -p /etc/letsencrypt/renewal-hooks/post
        echo -e '#!/bin/bash\nsystemctl reload nginx' | sudo tee /etc/letsencrypt/renewal-hooks/post/nginx-reload.sh >/dev/null
        sudo chmod +x /etc/letsencrypt/renewal-hooks/post/nginx-reload.sh
        print_success "SSL configurado (se certbot teve sucesso)."
      fi
    fi
  fi

  print_success "Nginx configurado."
  $USE_DOMAIN && print_info "Acesse: http://$DOMAIN" || print_info "Acesse: http://$SERVER_IP"
}

# ────────────────────────────────────────────────────────────────────────────
# Verificação final
# ────────────────────────────────────────────────────────────────────────────
final_verification() {
  print_header "VERIFICAÇÃO FINAL"
  print_step "PostgreSQL…"; docker ps | grep -q postgres && print_success "OK" || print_error "postgres não está rodando"
  print_step "API…"; systemctl is-active --quiet tiktok-api 2>/dev/null && print_success "OK" || print_warning "Cheque: systemctl status tiktok-api"
  print_step "Agendador…"; systemctl is-active --quiet tiktok-scheduler 2>/dev/null && print_success "OK" || print_warning "Cheque: systemctl status tiktok-scheduler"
  print_step "Frontend…"; [ -d "$BACKEND_DIR/web" ] && print_success "Build presente" || print_warning "Sem build em beckend/web"
  print_step "Nginx…"; systemctl is-active --quiet nginx && print_success "OK" || print_warning "Nginx pode não estar rodando"
}

# ────────────────────────────────────────────────────────────────────────────
# Info final
# ────────────────────────────────────────────────────────────────────────────
show_final_info() {
  print_header "DEPLOY CONCLUÍDO COM SUCESSO! 🎉"
  SERVER_IP=$(hostname -I | awk '{print $1}' 2>/dev/null || echo "localhost")
  ACCESS_URL="http://$SERVER_IP"; $SKIP_NGINX && ACCESS_URL="http://localhost:8082"

  echo -e "${BOLD}Informações:${NC}"
  echo -e "${GREEN}✓${NC} PostgreSQL:    ${CYAN}postgresql://localhost:5432/tiktok_db${NC}"
  echo -e "${GREEN}✓${NC} API Backend:   ${CYAN}http://localhost:8082${NC}"
  echo -e "${GREEN}✓${NC} Docs:          ${CYAN}http://localhost:8082/docs${NC}"
  echo -e "${GREEN}✓${NC} Frontend:      ${CYAN}Build em beckend/web${NC}"
  [ "$SKIP_NGINX" = false ] && echo -e "${GREEN}✓${NC} App:           ${CYAN}${ACCESS_URL}${NC}"
  echo
  echo -e "${BOLD}Comandos úteis:${NC}"
  echo -e "  ${CYAN}cd beckend && ./manage.sh all status${NC}"
  echo -e "  ${CYAN}cd beckend && ./manage.sh all restart${NC}"
  echo -e "  ${CYAN}docker-compose logs -f postgres${NC}"
  [ "$SKIP_NGINX" = false ] && echo -e "  ${CYAN}sudo systemctl status nginx${NC}"
  echo
}

# ────────────────────────────────────────────────────────────────────────────
# Args
# ────────────────────────────────────────────────────────────────────────────
show_help(){ echo "Uso: $0 [--skip-db|--skip-fe|--skip-nginx|--dev|--help]"; exit 0; }
parse_args(){
  while [[ $# -gt 0 ]]; do
    case $1 in
      --skip-db) SKIP_DB=true; shift;;
      --skip-fe) SKIP_FE=true; shift;;
      --skip-nginx) SKIP_NGINX=true; shift;;
      --dev) DEV_MODE=true; SKIP_NGINX=true; shift;;
      --help|-h) show_help;;
      *) print_error "Opção desconhecida: $1"; show_help;;
    esac
  done
}

# ────────────────────────────────────────────────────────────────────────────
# Main
# ────────────────────────────────────────────────────────────────────────────
main(){
  [ -n "$TERM" ] && [ "$TERM" != "dumb" ] && clear || true

  echo -e "${BOLD}${CYAN}"
  echo "╔═══════════════════════════════════════════════════════════════════╗"
  echo "║           🚀  DEPLOY AUTOMÁTICO - TIKTOK REACT (DEBIAN) 🚀        ║"
  echo "╚═══════════════════════════════════════════════════════════════════╝"
  echo -e "${NC}"

  print_info "Projeto: $SCRIPT_DIR"
  print_info "Backend: $BACKEND_DIR"
  print_info "Frontend: $FRONTEND_DIR"
  echo

  parse_args "$@"

  print_info "Iniciando deploy…"; echo; sleep 1

  check_dependencies
  setup_database
  setup_backend

  if ! $DEV_MODE; then
    setup_services
  else
    print_warning "Modo dev: serviços systemd não instalados."
    print_info "Para rodar manualmente:"
    print_command "cd beckend && source venv/bin/activate"
    print_command "uvicorn src.main:app --reload --host 0.0.0.0 --port 8000"
  fi

  setup_frontend
  setup_nginx
  final_verification
  show_final_info

  print_success "Deploy concluído! 🎉"
}

trap 'print_error "Erro na linha $LINENO. Deploy falhou!"; exit 1' ERR
main "$@"

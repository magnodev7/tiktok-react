#!/bin/bash
#
# Script de Setup do Banco de Dados - TikTok React
# ================================================
#
# Este script facilita a inicialização do banco de dados,
# ativando automaticamente o ambiente virtual e executando
# as migrações necessárias.
#
# Uso:
#   ./setup_database.sh           # Inicializa normalmente
#   ./setup_database.sh --reset   # Reseta o banco (CUIDADO!)
#   ./setup_database.sh --help    # Mostra ajuda
#

set -e  # Para na primeira falha

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Funções helper
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

# Diretório do script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

print_info "Diretório: $SCRIPT_DIR"

# Verifica se o ambiente virtual existe
if [ ! -d "venv" ]; then
    print_error "Ambiente virtual não encontrado!"
    print_info "Criando ambiente virtual..."
    python3 -m venv venv
    print_success "Ambiente virtual criado"
fi

# Ativa o ambiente virtual
print_info "Ativando ambiente virtual..."
source venv/bin/activate

# Verifica se as dependências estão instaladas
if ! python -c "import sqlalchemy" 2>/dev/null; then
    print_warning "Dependências não instaladas. Instalando..."
    pip install -r requirements.txt
    print_success "Dependências instaladas"
fi

# Verifica se o PostgreSQL está rodando (apenas se local)
if [ ! -f "/.dockerenv" ]; then
    print_info "Verificando PostgreSQL..."
    if command -v pg_isready &> /dev/null; then
        if pg_isready -q; then
            print_success "PostgreSQL está rodando"
        else
            print_warning "PostgreSQL pode não estar rodando. Continuando mesmo assim..."
        fi
    else
        print_info "Comando pg_isready não encontrado. Pulando verificação..."
    fi
fi

# Executa o script de inicialização
print_info "Executando inicialização do banco de dados..."
echo ""

python init_db.py "$@"

exit_code=$?

echo ""
if [ $exit_code -eq 0 ]; then
    print_success "Setup concluído com sucesso!"
else
    print_error "Setup falhou com código $exit_code"
    exit $exit_code
fi

# Desativa o ambiente virtual (opcional)
# deactivate

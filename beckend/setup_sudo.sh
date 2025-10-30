#!/bin/bash

# Script para configurar sudo sem senha para manage.sh
# Execute com: sudo bash setup_sudo.sh

set -e

echo "🔧 Configurando sudo para manage.sh..."

# Descobrir o usuário atual
CURRENT_USER="${SUDO_USER:-$USER}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MANAGE_SH="$SCRIPT_DIR/manage.sh"

echo "Usuário: $CURRENT_USER"
echo "Script: $MANAGE_SH"

# Criar arquivo sudoers
SUDOERS_FILE="/etc/sudoers.d/tiktok-maintenance"

cat > "$SUDOERS_FILE" <<EOF
# Permite que o backend execute manage.sh sem senha
# Necessário para reiniciar serviços via interface web
$CURRENT_USER ALL=(ALL) NOPASSWD: $MANAGE_SH
EOF

# Definir permissões corretas
chmod 0440 "$SUDOERS_FILE"

# Validar sintaxe
if visudo -c -f "$SUDOERS_FILE"; then
    echo "✅ Configuração do sudo concluída com sucesso!"
    echo ""
    echo "Agora o backend pode executar:"
    echo "  sudo $MANAGE_SH all restart"
    echo ""
else
    echo "❌ Erro na configuração do sudoers!"
    rm -f "$SUDOERS_FILE"
    exit 1
fi

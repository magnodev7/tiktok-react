#!/bin/bash
#
# Script para configurar SSL/HTTPS com Let's Encrypt
# Uso: ./setup-ssl.sh seu-dominio.com seu-email@example.com
#

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${BOLD}${CYAN}"
echo "╔═══════════════════════════════════════════════════════════════════╗"
echo "║                                                                   ║"
echo "║           🔒  CONFIGURAÇÃO SSL/HTTPS - LET'S ENCRYPT  🔒          ║"
echo "║                                                                   ║"
echo "╚═══════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Verificar argumentos
if [ $# -lt 1 ]; then
    echo -e "${RED}Erro: Domínio não fornecido${NC}"
    echo ""
    echo "Uso: $0 <dominio> [email]"
    echo ""
    echo "Exemplos:"
    echo "  $0 app.exemplo.com"
    echo "  $0 app.exemplo.com contato@exemplo.com"
    exit 1
fi

DOMAIN=$1
EMAIL=${2:-""}

echo -e "${CYAN}Domínio:${NC} $DOMAIN"
if [ -n "$EMAIL" ]; then
    echo -e "${CYAN}Email:${NC} $EMAIL"
fi
echo ""

# Verificar se Nginx está rodando
if ! systemctl is-active --quiet nginx; then
    echo -e "${RED}✗ Nginx não está rodando!${NC}"
    echo "Execute primeiro: sudo systemctl start nginx"
    exit 1
fi

echo -e "${GREEN}✓${NC} Nginx está rodando"

# Verificar se Certbot está instalado
if ! command -v certbot &> /dev/null; then
    echo -e "${YELLOW}⚠${NC} Certbot não encontrado. Instalando..."
    sudo apt update
    sudo apt install -y certbot python3-certbot-nginx
    echo -e "${GREEN}✓${NC} Certbot instalado"
else
    echo -e "${GREEN}✓${NC} Certbot já instalado"
fi

# Pedir email se não foi fornecido
if [ -z "$EMAIL" ]; then
    echo ""
    echo -ne "${CYAN}?${NC} Digite seu email para notificações do Let's Encrypt: "
    read EMAIL

    if [ -z "$EMAIL" ]; then
        echo -e "${RED}✗ Email é obrigatório${NC}"
        exit 1
    fi
fi

# Verificar DNS
echo ""
echo -e "${YELLOW}⚠${NC} Verificando DNS do domínio..."
DOMAIN_IP=$(dig +short $DOMAIN | tail -1)
SERVER_IP=$(curl -s ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')

if [ -z "$DOMAIN_IP" ]; then
    echo -e "${RED}✗ Não foi possível resolver o DNS de $DOMAIN${NC}"
    echo -e "${YELLOW}⚠ Certifique-se que o DNS está configurado corretamente!${NC}"
    echo ""
    read -p "Deseja continuar mesmo assim? [y/N] " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Operação cancelada."
        exit 1
    fi
else
    echo -e "${GREEN}✓${NC} DNS resolvido: $DOMAIN_IP"
    if [ "$DOMAIN_IP" != "$SERVER_IP" ]; then
        echo -e "${YELLOW}⚠ IP do domínio ($DOMAIN_IP) diferente do servidor ($SERVER_IP)${NC}"
        echo -e "${YELLOW}⚠ Certbot pode falhar se o DNS não estiver correto!${NC}"
        echo ""
        read -p "Deseja continuar mesmo assim? [y/N] " -n 1 -r
        echo ""
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Operação cancelada."
            exit 1
        fi
    else
        echo -e "${GREEN}✓${NC} DNS configurado corretamente!"
    fi
fi

# Obter certificado SSL
echo ""
echo -e "${BOLD}${CYAN}Obtendo certificado SSL...${NC}"
echo ""

sudo certbot --nginx \
    -d "$DOMAIN" \
    --non-interactive \
    --agree-tos \
    --email "$EMAIL" \
    --redirect

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}════════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}  ✅ SSL CONFIGURADO COM SUCESSO!${NC}"
    echo -e "${GREEN}════════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "${BOLD}Informações:${NC}"
    echo -e "  ${GREEN}✓${NC} Certificado obtido para: ${CYAN}$DOMAIN${NC}"
    echo -e "  ${GREEN}✓${NC} Redirecionamento HTTP → HTTPS ativo"
    echo -e "  ${GREEN}✓${NC} Acesse: ${CYAN}https://$DOMAIN${NC}"
    echo ""

    # Configurar renovação automática
    echo ""
    echo -e "${BOLD}${CYAN}Configurando renovação automática...${NC}"
    echo ""

    # Garantir que o timer do certbot está ativo
    if sudo systemctl is-enabled certbot.timer &>/dev/null; then
        echo -e "${GREEN}✓${NC} Timer de renovação já está habilitado"
    else
        sudo systemctl enable certbot.timer
        echo -e "${GREEN}✓${NC} Timer de renovação habilitado"
    fi

    if sudo systemctl is-active certbot.timer &>/dev/null; then
        echo -e "${GREEN}✓${NC} Timer de renovação está ativo"
    else
        sudo systemctl start certbot.timer
        echo -e "${GREEN}✓${NC} Timer de renovação iniciado"
    fi

    # Testar renovação
    echo ""
    echo -e "${YELLOW}Testando processo de renovação...${NC}"
    if sudo certbot renew --dry-run; then
        echo -e "${GREEN}✓${NC} Teste de renovação passou!"
    else
        echo -e "${YELLOW}⚠${NC} Teste de renovação falhou, mas certificado está instalado"
    fi

    # Criar hook de pós-renovação para reiniciar Nginx
    echo ""
    echo -e "${CYAN}Configurando hook de pós-renovação...${NC}"
    sudo mkdir -p /etc/letsencrypt/renewal-hooks/post

    cat << 'HOOK_EOF' | sudo tee /etc/letsencrypt/renewal-hooks/post/nginx-reload.sh > /dev/null
#!/bin/bash
# Hook executado após renovação bem-sucedida do certificado SSL
# Recarrega o Nginx para aplicar o novo certificado

echo "$(date): Certificado renovado, recarregando Nginx..." >> /var/log/letsencrypt/renewal-hooks.log
systemctl reload nginx

if [ $? -eq 0 ]; then
    echo "$(date): Nginx recarregado com sucesso" >> /var/log/letsencrypt/renewal-hooks.log
else
    echo "$(date): ERRO ao recarregar Nginx" >> /var/log/letsencrypt/renewal-hooks.log
fi
HOOK_EOF

    sudo chmod +x /etc/letsencrypt/renewal-hooks/post/nginx-reload.sh
    echo -e "${GREEN}✓${NC} Hook de pós-renovação configurado"

    # Criar diretório de logs se não existir
    sudo mkdir -p /var/log/letsencrypt
    sudo touch /var/log/letsencrypt/renewal-hooks.log
    sudo chmod 644 /var/log/letsencrypt/renewal-hooks.log

    echo ""
    echo -e "${BOLD}Renovação automática:${NC}"
    echo -e "  ${GREEN}✓${NC} Certificado renova automaticamente a cada 90 dias"
    echo -e "  ${GREEN}✓${NC} Verificação diária às 00:00 e 12:00"
    echo -e "  ${GREEN}✓${NC} Nginx será recarregado automaticamente após renovação"
    echo -e "  ${GREEN}✓${NC} Logs em: ${CYAN}/var/log/letsencrypt/renewal-hooks.log${NC}"

    # Mostrar próxima execução do timer
    NEXT_RUN=$(sudo systemctl list-timers certbot.timer 2>/dev/null | grep certbot.timer | awk '{print $1, $2, $3, $4}')
    if [ -n "$NEXT_RUN" ]; then
        echo -e "  ${GREEN}✓${NC} Próxima verificação: ${CYAN}$NEXT_RUN${NC}"
    fi

    echo ""
    echo -e "${BOLD}Comandos úteis:${NC}"
    echo -e "  ${CYAN}sudo certbot certificates${NC}              # Ver certificados instalados"
    echo -e "  ${CYAN}sudo certbot renew${NC}                     # Renovar manualmente"
    echo -e "  ${CYAN}sudo certbot delete --cert-name $DOMAIN${NC}  # Remover certificado"
    echo ""
else
    echo ""
    echo -e "${RED}════════════════════════════════════════════════════════════════${NC}"
    echo -e "${RED}  ✗ FALHA AO CONFIGURAR SSL${NC}"
    echo -e "${RED}════════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "${BOLD}Possíveis causas:${NC}"
    echo "  1. DNS não está apontando para este servidor"
    echo "  2. Porta 80 ou 443 bloqueada por firewall"
    echo "  3. Nginx não está configurado corretamente"
    echo "  4. Limite de requisições do Let's Encrypt atingido"
    echo ""
    echo -e "${BOLD}Verificações:${NC}"
    echo -e "  ${CYAN}dig $DOMAIN${NC}                    # Verificar DNS"
    echo -e "  ${CYAN}sudo systemctl status nginx${NC}    # Status do Nginx"
    echo -e "  ${CYAN}sudo ufw status${NC}                # Status do firewall"
    echo ""
    exit 1
fi

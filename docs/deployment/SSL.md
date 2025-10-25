# 🔒 Guia SSL/HTTPS - Certificados Let's Encrypt

Configuração completa de SSL/HTTPS com renovação automática.

## 📋 Pré-requisitos

### Obrigatórios
- ✅ Domínio próprio (ex: `app.exemplo.com`)
- ✅ DNS apontando para o IP do servidor
- ✅ Nginx instalado e configurado
- ✅ Portas 80 e 443 abertas no firewall

### Verificações

```bash
# Verificar DNS
dig seu-dominio.com

# Verificar se aponta para seu servidor
curl -I http://seu-dominio.com

# Verificar portas abertas
sudo ufw status
sudo ufw allow 80
sudo ufw allow 443
```

## 🚀 Configuração SSL

### Opção 1: Durante o Deploy

O SSL é configurado automaticamente durante o deploy:

```bash
./deploy.sh
```

Quando perguntado sobre domínio, responda:
- `Y` - Tenho um domínio
- Digite o domínio: `app.exemplo.com`
- `Y` - Configurar SSL agora
- Digite o email: `seu@email.com`

### Opção 2: Após o Deploy

Use o script dedicado:

```bash
./setup-ssl.sh seu-dominio.com seu@email.com
```

### Opção 3: Manual

```bash
# Instalar Certbot
sudo apt update
sudo apt install -y certbot python3-certbot-nginx

# Obter certificado
sudo certbot --nginx -d seu-dominio.com

# Seguir prompts interativos
```

## 🔄 Renovação Automática

O SSL é configurado com renovação automática:

### Como Funciona

1. **Systemd Timer**: Verifica certificados 2x por dia (00:00 e 12:00)
2. **Renovação**: Ocorre automaticamente 30 dias antes do vencimento
3. **Hook Pós-Renovação**: Recarrega Nginx após renovação bem-sucedida
4. **Logs**: Registra todas as operações

### Verificar Status

```bash
# Status do timer de renovação
sudo systemctl status certbot.timer

# Próxima execução
sudo systemctl list-timers certbot.timer

# Certificados instalados
sudo certbot certificates
```

### Testar Renovação

```bash
# Teste simulado (não renova de verdade)
sudo certbot renew --dry-run
```

Se passar sem erros, a renovação automática está funcionando corretamente.

## 📊 Monitoramento

### Logs de Renovação

```bash
# Logs gerais do Certbot
sudo tail -f /var/log/letsencrypt/letsencrypt.log

# Logs do hook de pós-renovação
sudo tail -f /var/log/letsencrypt/renewal-hooks.log
```

### Verificar Validade

```bash
# Ver data de expiração
sudo certbot certificates

# Testar SSL online
# Acesse: https://www.ssllabs.com/ssltest/
# Digite seu domínio
```

### Alertas de Expiração

Let's Encrypt envia emails automáticos:
- 20 dias antes do vencimento
- 10 dias antes do vencimento
- 1 dia antes do vencimento

Se receber email de alerta, verificar:

```bash
# Tentar renovar manualmente
sudo certbot renew

# Ver logs de erro
sudo tail -100 /var/log/letsencrypt/letsencrypt.log
```

## 🔧 Hook de Pós-Renovação

Localização: `/etc/letsencrypt/renewal-hooks/post/nginx-reload.sh`

```bash
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
```

### Modificar Hook

```bash
# Editar script
sudo nano /etc/letsencrypt/renewal-hooks/post/nginx-reload.sh

# Garantir permissão de execução
sudo chmod +x /etc/letsencrypt/renewal-hooks/post/nginx-reload.sh

# Testar manualmente
sudo /etc/letsencrypt/renewal-hooks/post/nginx-reload.sh
```

## 🔒 Configuração Nginx SSL

Localização: `/etc/nginx/sites-available/tiktok`

```nginx
server {
    listen 443 ssl http2;
    server_name seu-dominio.com;

    # Certificados SSL
    ssl_certificate /etc/letsencrypt/live/seu-dominio.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/seu-dominio.com/privkey.pem;

    # Configurações SSL seguras
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # HSTS (15768000 segundos = 6 meses)
    add_header Strict-Transport-Security "max-age=15768000" always;

    # Restante da configuração...
}

# Redirecionamento HTTP → HTTPS
server {
    listen 80;
    server_name seu-dominio.com;
    return 301 https://$server_name$request_uri;
}
```

## ⚠️ Troubleshooting

### Erro: DNS não resolve

```bash
# Verificar DNS
dig seu-dominio.com

# Verificar propagação DNS
# Acesse: https://dnschecker.org/
```

**Solução**: Aguardar propagação DNS (pode levar até 48h)

### Erro: Porta 80/443 bloqueada

```bash
# Verificar portas
sudo netstat -tlnp | grep -E ':80|:443'

# Abrir no firewall
sudo ufw allow 80
sudo ufw allow 443

# Verificar se outro processo usa a porta
sudo lsof -i :80
sudo lsof -i :443
```

### Erro: Too many requests

Let's Encrypt tem limites:
- 50 certificados por domínio por semana
- 5 falhas de validação por conta/hora

**Solução**: Aguardar 1 hora e tentar novamente. Use `--dry-run` para testar.

### Erro: Nginx não recarrega após renovação

```bash
# Verificar logs do hook
sudo tail -f /var/log/letsencrypt/renewal-hooks.log

# Testar Nginx
sudo nginx -t

# Recarregar manualmente
sudo systemctl reload nginx
```

### Renovação automática não funciona

```bash
# Verificar se timer está ativo
sudo systemctl status certbot.timer

# Ativar timer
sudo systemctl enable certbot.timer
sudo systemctl start certbot.timer

# Forçar renovação manual
sudo certbot renew --force-renewal
```

## 🔄 Renovar Manualmente

```bash
# Renovar todos os certificados próximos do vencimento
sudo certbot renew

# Forçar renovação (mesmo não estando perto de vencer)
sudo certbot renew --force-renewal

# Renovar certificado específico
sudo certbot renew --cert-name seu-dominio.com
```

## 🗑️ Remover Certificado

```bash
# Listar certificados
sudo certbot certificates

# Remover certificado específico
sudo certbot delete --cert-name seu-dominio.com

# Limpar configuração do Nginx
sudo rm /etc/nginx/sites-enabled/tiktok
sudo rm /etc/nginx/sites-available/tiktok
sudo systemctl reload nginx
```

## 📚 Comandos Úteis

```bash
# Ver todos os certificados
sudo certbot certificates

# Renovar certificados
sudo certbot renew

# Testar renovação
sudo certbot renew --dry-run

# Remover certificado
sudo certbot delete --cert-name dominio.com

# Revogar certificado
sudo certbot revoke --cert-path /etc/letsencrypt/live/dominio.com/cert.pem

# Ver configuração de renovação
sudo cat /etc/letsencrypt/renewal/dominio.com.conf

# Logs do Certbot
sudo tail -f /var/log/letsencrypt/letsencrypt.log

# Status do timer
sudo systemctl status certbot.timer

# Próximas execuções
sudo systemctl list-timers
```

## 🔗 Links Úteis

- [Let's Encrypt](https://letsencrypt.org/)
- [Certbot](https://certbot.eff.org/)
- [SSL Labs Test](https://www.ssllabs.com/ssltest/)
- [DNS Checker](https://dnschecker.org/)

## 📝 Checklist de Verificação

- [ ] DNS aponta para o servidor
- [ ] Portas 80 e 443 abertas
- [ ] Nginx configurado e rodando
- [ ] Certificado SSL instalado
- [ ] HTTPS funcionando (https://seu-dominio.com)
- [ ] Redirecionamento HTTP→HTTPS ativo
- [ ] Timer de renovação ativo (`systemctl status certbot.timer`)
- [ ] Teste de renovação passou (`certbot renew --dry-run`)
- [ ] Hook de pós-renovação configurado
- [ ] Logs de renovação criados e acessíveis

---

**Dica**: Execute `sudo certbot renew --dry-run` mensalmente para garantir que a renovação automática está funcionando.

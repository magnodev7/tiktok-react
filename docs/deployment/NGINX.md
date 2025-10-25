# 🌐 Nginx - Configuração Completa

Guia completo de configuração do Nginx como reverse proxy.

## 🎯 Visão Geral

O Nginx atua como:
- 🔀 Reverse proxy para o backend (porta 8082)
- 📁 Servidor de arquivos estáticos (frontend)
- 🔒 Terminação SSL/HTTPS
- ⚡ Cache e compressão
- 🛡️ Proteção contra ataques

---

## 📁 Arquivos de Configuração

### Localização Principal

```
/etc/nginx/
├── nginx.conf                    # Configuração principal
├── sites-available/
│   └── tiktok                    # Configuração do site
├── sites-enabled/
│   └── tiktok -> ../sites-available/tiktok
└── conf.d/
    └── *.conf                    # Configurações adicionais
```

### Configuração do Site

Arquivo: `/etc/nginx/sites-available/tiktok`

```nginx
# Upstream para o backend FastAPI
upstream backend {
    server 127.0.0.1:8082;
    keepalive 32;
}

# HTTP Server (redireciona para HTTPS se SSL configurado)
server {
    listen 80;
    server_name seu-dominio.com;

    # Redirecionar para HTTPS (se SSL configurado)
    # return 301 https://$server_name$request_uri;

    # Ou servir direto (sem SSL)
    location / {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }

    # Aumentar tamanhos de upload
    client_max_body_size 500M;
    client_body_buffer_size 128k;

    # Timeouts para uploads grandes
    proxy_connect_timeout 600;
    proxy_send_timeout 600;
    proxy_read_timeout 600;
    send_timeout 600;
}

# HTTPS Server (se SSL configurado)
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
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # HSTS
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # Security Headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Proxy para backend
    location / {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }

    # Upload de vídeos
    client_max_body_size 500M;
    client_body_buffer_size 128k;

    # Timeouts
    proxy_connect_timeout 600;
    proxy_send_timeout 600;
    proxy_read_timeout 600;
    send_timeout 600;

    # Logs
    access_log /var/log/nginx/tiktok-access.log;
    error_log /var/log/nginx/tiktok-error.log;
}
```

---

## 🚀 Instalação e Setup

### Instalar Nginx

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y nginx

# Verificar instalação
nginx -v
```

### Criar Configuração

```bash
# Criar arquivo de configuração
sudo nano /etc/nginx/sites-available/tiktok

# Colar configuração acima

# Criar link simbólico
sudo ln -s /etc/nginx/sites-available/tiktok /etc/nginx/sites-enabled/

# Remover configuração padrão
sudo rm /etc/nginx/sites-enabled/default

# Testar configuração
sudo nginx -t

# Reiniciar Nginx
sudo systemctl restart nginx
sudo systemctl enable nginx
```

---

## ⚙️ Otimizações

### Compressão Gzip

Adicionar em `nginx.conf`:

```nginx
http {
    # Compressão Gzip
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types
        text/plain
        text/css
        text/xml
        text/javascript
        application/json
        application/javascript
        application/xml+rss
        application/rss+xml
        font/truetype
        font/opentype
        application/vnd.ms-fontobject
        image/svg+xml;
}
```

### Cache de Arquivos Estáticos

```nginx
location ~* \.(jpg|jpeg|png|gif|ico|css|js|svg|woff|woff2)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}
```

### Rate Limiting

Proteger contra DDoS:

```nginx
# Em http block
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;

# Em location block
location /api/ {
    limit_req zone=api burst=20 nodelay;
    proxy_pass http://backend;
}
```

---

## 🔧 Comandos Úteis

### Gerenciamento

```bash
# Iniciar
sudo systemctl start nginx

# Parar
sudo systemctl stop nginx

# Reiniciar
sudo systemctl restart nginx

# Recarregar (sem downtime)
sudo systemctl reload nginx

# Status
sudo systemctl status nginx

# Habilitar auto-start
sudo systemctl enable nginx
```

### Testes

```bash
# Testar configuração
sudo nginx -t

# Testar e mostrar detalhes
sudo nginx -T

# Verificar sintaxe
sudo nginx -c /etc/nginx/nginx.conf -t
```

### Logs

```bash
# Access log em tempo real
sudo tail -f /var/log/nginx/tiktok-access.log

# Error log em tempo real
sudo tail -f /var/log/nginx/tiktok-error.log

# Últimas 100 linhas de erro
sudo tail -100 /var/log/nginx/tiktok-error.log

# Buscar erros específicos
sudo grep "error" /var/log/nginx/tiktok-error.log
```

---

## ⚠️ Troubleshooting

### Erro 502 Bad Gateway

**Causa:** Backend não está respondendo

**Soluções:**
```bash
# Verificar se backend está rodando
sudo systemctl status tiktok-backend

# Reiniciar backend
cd beckend
./manage.sh backend restart

# Verificar porta 8082
sudo netstat -tlnp | grep 8082

# Ver logs do Nginx
sudo tail -f /var/log/nginx/tiktok-error.log
```

### Erro 413 Request Entity Too Large

**Causa:** Upload maior que `client_max_body_size`

**Solução:**
```nginx
# Aumentar em /etc/nginx/sites-available/tiktok
client_max_body_size 500M;

# Reiniciar Nginx
sudo systemctl reload nginx
```

### Erro 504 Gateway Timeout

**Causa:** Request demorou demais

**Solução:**
```nginx
# Aumentar timeouts
proxy_connect_timeout 600;
proxy_send_timeout 600;
proxy_read_timeout 600;
```

### Nginx não inicia

```bash
# Ver erro detalhado
sudo journalctl -u nginx -n 50

# Causas comuns:
# 1. Porta 80/443 em uso
sudo lsof -i :80
sudo lsof -i :443

# 2. Erro de sintaxe
sudo nginx -t

# 3. Permissões
sudo chown -R www-data:www-data /var/log/nginx/
```

---

## 🔒 Security Hardening

### Ocultar Versão

```nginx
http {
    server_tokens off;
}
```

### Bloquear User-Agents

```nginx
# Bloquear bots maliciosos
if ($http_user_agent ~* (bot|crawler|spider|scraper)) {
    return 403;
}
```

### Limitar Métodos HTTP

```nginx
# Permitir apenas GET, POST, PUT, DELETE
if ($request_method !~ ^(GET|POST|PUT|DELETE)$ ) {
    return 405;
}
```

### Proteção contra Clickjacking

```nginx
add_header X-Frame-Options "SAMEORIGIN" always;
```

---

## 📊 Monitoramento

### Status Page

Ativar página de status:

```nginx
server {
    listen 8080;
    server_name localhost;

    location /nginx_status {
        stub_status on;
        access_log off;
        allow 127.0.0.1;
        deny all;
    }
}
```

Acessar: `curl http://localhost:8080/nginx_status`

### Métricas

```bash
# Conexões ativas
curl -s http://localhost:8080/nginx_status | grep "Active"

# Requests por segundo (via logs)
tail -10000 /var/log/nginx/tiktok-access.log | \
  awk '{print $4}' | cut -d: -f2 | sort | uniq -c
```

---

## 🔗 Links Relacionados

- **[Deploy](DEPLOY.md)** - Deploy completo
- **[SSL](SSL.md)** - Configurar HTTPS
- **[Systemd](SYSTEMD.md)** - Serviços
- **[Logs](LOGS.md)** - Análise de logs
- **[Troubleshooting](TROUBLESHOOTING.md)** - Problemas comuns

---

**Versão**: 2.0
**Última atualização**: Outubro 2025

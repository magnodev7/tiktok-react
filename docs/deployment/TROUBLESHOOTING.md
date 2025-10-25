# ⚠️ Troubleshooting - Problemas Comuns

Soluções para problemas frequentes.

## 🚫 Serviços

### Backend não inicia
```bash
# Ver erro
sudo journalctl -u tiktok-backend -n 50

# Soluções comuns:
# 1. Porta 8082 em uso
sudo lsof -i :8082 | awk 'NR>1 {print $2}' | xargs sudo kill -9

# 2. Banco não conecta
docker ps | grep postgres
docker restart postgres

# 3. Permissões de logs
sudo chown -R $USER:$USER beckend/logs/
```

### Scheduler não funciona
```bash
# Status
sudo systemctl status tiktok-scheduler

# Reiniciar
cd beckend && ./manage.sh scheduler restart

# Ver logs
tail -f beckend/logs/scheduler.log
```

---

## 🌐 Nginx

### 502 Bad Gateway
```bash
# Backend não está rodando
sudo systemctl start tiktok-backend

# Ver logs
sudo tail -f /var/log/nginx/tiktok-error.log
```

### 413 Request Too Large
```nginx
# Aumentar em /etc/nginx/sites-available/tiktok
client_max_body_size 500M;

# Recarregar
sudo systemctl reload nginx
```

---

## 🗄️ PostgreSQL

### Container não inicia
```bash
# Ver logs
docker logs postgres

# Reiniciar
docker restart postgres

# Recriar (CUIDADO: perde dados)
docker stop postgres
docker rm postgres
cd tiktok-react
./deploy.sh
```

### Conexão recusada
```bash
# Verificar se está rodando
docker ps | grep postgres

# Ver porta
docker port postgres

# Testar conexão
docker exec -it postgres psql -U tiktok -d tiktok_db
```

---

## 🎬 TikTok

### Sessão expirou
1. **Contas** > Selecione conta
2. **Renovar Sessão**
3. Fazer login novamente

### Vídeo não posta
```bash
# Ver logs do scheduler
tail -100 beckend/logs/scheduler.log | grep "ERROR"

# Causas comuns:
# - Sessão expirada
# - Vídeo corrompido
# - Conta banida
```

---

## 🔧 Deploy

### Deploy falha
```bash
# Ver onde parou
tail -100 deploy.log

# Rodar novamente
./deploy.sh

# Pular etapas já feitas
./deploy.sh --skip-db --skip-fe
```

---

## 🔗 Links
- **[Logs](LOGS.md)** - Como ver logs
- **[Systemd](SYSTEMD.md)** - Gerenciar serviços
- **[Deploy](DEPLOY.md)** - Guia de deploy

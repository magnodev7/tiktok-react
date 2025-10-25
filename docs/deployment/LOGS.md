# 📋 Logs - Localização e Análise

Guia completo de logs da aplicação.

## 📁 Localizações

### Backend
```
beckend/logs/backend.log           # Stdout da API
beckend/logs/backend-error.log     # Stderr da API
beckend/logs/scheduler.log         # Stdout do scheduler
beckend/logs/scheduler-error.log   # Stderr do scheduler
```

### Systemd
```bash
sudo journalctl -u tiktok-backend
sudo journalctl -u tiktok-scheduler
```

### Nginx
```
/var/log/nginx/tiktok-access.log   # Requests HTTP
/var/log/nginx/tiktok-error.log    # Erros do Nginx
```

### PostgreSQL
```bash
docker logs postgres
docker logs -f postgres  # Tempo real
```

---

## 🔍 Ver Logs

### Tempo Real
```bash
# Backend
tail -f beckend/logs/backend.log

# Scheduler
tail -f beckend/logs/scheduler.log

# Nginx
sudo tail -f /var/log/nginx/tiktok-access.log

# PostgreSQL
docker logs -f postgres
```

### Últimas N Linhas
```bash
tail -n 100 beckend/logs/backend.log
sudo journalctl -u tiktok-backend -n 100
```

### Buscar Erros
```bash
grep "ERROR" beckend/logs/*.log
grep "Exception" beckend/logs/*.log
sudo journalctl -u tiktok-scheduler | grep "error"
```

### Por Período
```bash
# Logs de hoje
sudo journalctl -u tiktok-backend --since today

# Últimas 2 horas
sudo journalctl -u tiktok-backend --since "2 hours ago"

# Entre datas
sudo journalctl -u tiktok-backend --since "2025-01-20" --until "2025-01-21"
```

---

## 📊 Análise

### Requests por Status Code
```bash
awk '{print $9}' /var/log/nginx/tiktok-access.log | sort | uniq -c | sort -rn
```

### Top IPs
```bash
awk '{print $1}' /var/log/nginx/tiktok-access.log | sort | uniq -c | sort -rn | head -10
```

### Erros Mais Comuns
```bash
grep "ERROR" beckend/logs/*.log | awk -F: '{print $4}' | sort | uniq -c | sort -rn
```

### Vídeos Postados Hoje
```bash
grep "Video posted successfully" beckend/logs/scheduler.log | grep "$(date +%Y-%m-%d)"
```

---

## 🧹 Limpeza

### Limpar Logs Antigos
```bash
# Limpar logs da aplicação
> beckend/logs/backend.log
> beckend/logs/scheduler.log

# Limpar logs do systemd (manter 7 dias)
sudo journalctl --vacuum-time=7d

# Limpar logs do Nginx
sudo truncate -s 0 /var/log/nginx/tiktok-*.log
```

### Rotação Automática
Arquivo: `/etc/logrotate.d/tiktok`
```
/home/ubuntu/tiktok-react/beckend/logs/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0644 ubuntu ubuntu
}
```

---

## 🔗 Links
- **[Systemd](SYSTEMD.md)** - Gerenciar serviços
- **[Troubleshooting](TROUBLESHOOTING.md)** - Problemas comuns

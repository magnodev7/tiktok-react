# ⚙️ Guia de Serviços Systemd

Gerenciamento completo dos serviços backend e scheduler.

## 📋 Visão Geral

O TikTok Scheduler usa dois serviços systemd:

| Serviço | Função | Porta |
|---------|--------|-------|
| **tiktok-backend** | API REST FastAPI | 8082 |
| **tiktok-scheduler** | Daemon de agendamento | - |

Ambos:
- ✅ Iniciam automaticamente no boot
- ✅ Reiniciam automaticamente em caso de falha
- ✅ Rodam como o usuário do sistema (não root)
- ✅ Logs centralizados

## 🚀 Instalação dos Serviços

Os serviços são criados automaticamente durante o deploy:

```bash
./deploy.sh
```

Ou manualmente:

```bash
cd beckend
./manage.sh backend install
./manage.sh scheduler install
```

## 🔧 Gerenciamento Rápido

### Script manage.sh

```bash
cd beckend

# Gerenciar todos os serviços
./manage.sh all start      # Iniciar todos
./manage.sh all stop       # Parar todos
./manage.sh all restart    # Reiniciar todos
./manage.sh all status     # Ver status de todos
./manage.sh all logs       # Ver logs de todos

# Gerenciar backend
./manage.sh backend start
./manage.sh backend stop
./manage.sh backend restart
./manage.sh backend status
./manage.sh backend logs

# Gerenciar scheduler
./manage.sh scheduler start
./manage.sh scheduler stop
./manage.sh scheduler restart
./manage.sh scheduler status
./manage.sh scheduler logs
```

## 🎛️ Comandos Systemctl

### Backend (tiktok-backend.service)

```bash
# Iniciar
sudo systemctl start tiktok-backend

# Parar
sudo systemctl stop tiktok-backend

# Reiniciar
sudo systemctl restart tiktok-backend

# Status
sudo systemctl status tiktok-backend

# Habilitar auto-start
sudo systemctl enable tiktok-backend

# Desabilitar auto-start
sudo systemctl disable tiktok-backend

# Ver logs em tempo real
sudo journalctl -u tiktok-backend -f

# Ver últimas 100 linhas de log
sudo journalctl -u tiktok-backend -n 100
```

### Scheduler (tiktok-scheduler.service)

```bash
# Iniciar
sudo systemctl start tiktok-scheduler

# Parar
sudo systemctl stop tiktok-scheduler

# Reiniciar
sudo systemctl restart tiktok-scheduler

# Status
sudo systemctl status tiktok-scheduler

# Habilitar auto-start
sudo systemctl enable tiktok-scheduler

# Desabilitar auto-start
sudo systemctl disable tiktok-scheduler

# Ver logs em tempo real
sudo journalctl -u tiktok-scheduler -f

# Ver últimas 100 linhas de log
sudo journalctl -u tiktok-scheduler -n 100
```

## 📄 Arquivos de Configuração

### Backend Service

Localização: `/etc/systemd/system/tiktok-backend.service`

```ini
[Unit]
Description=TikTok Scheduler Backend API
After=network.target postgresql.service docker.service
Wants=postgresql.service docker.service

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/tiktok-react/beckend
Environment="PATH=/home/ubuntu/tiktok-react/beckend/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=/home/ubuntu/tiktok-react/beckend/venv/bin/python -m uvicorn src.main:app --host 0.0.0.0 --port 8082
Restart=always
RestartSec=10
StandardOutput=append:/home/ubuntu/tiktok-react/beckend/logs/backend.log
StandardError=append:/home/ubuntu/tiktok-react/beckend/logs/backend-error.log

[Install]
WantedBy=multi-user.target
```

### Scheduler Service

Localização: `/etc/systemd/system/tiktok-scheduler.service`

```ini
[Unit]
Description=TikTok Scheduler Daemon
After=network.target postgresql.service docker.service tiktok-backend.service
Wants=postgresql.service docker.service
Requires=tiktok-backend.service

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/tiktok-react/beckend
Environment="PATH=/home/ubuntu/tiktok-react/beckend/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=/home/ubuntu/tiktok-react/beckend/venv/bin/python -m src.scheduler
Restart=always
RestartSec=10
StandardOutput=append:/home/ubuntu/tiktok-react/beckend/logs/scheduler.log
StandardError=append:/home/ubuntu/tiktok-react/beckend/logs/scheduler-error.log

[Install]
WantedBy=multi-user.target
```

## 📊 Logs

### Localizações

```bash
# Logs da aplicação (arquivos)
beckend/logs/backend.log           # Stdout do backend
beckend/logs/backend-error.log     # Stderr do backend
beckend/logs/scheduler.log         # Stdout do scheduler
beckend/logs/scheduler-error.log   # Stderr do scheduler

# Logs do systemd (journalctl)
sudo journalctl -u tiktok-backend
sudo journalctl -u tiktok-scheduler
```

### Ver Logs

```bash
# Logs em tempo real (tail)
cd beckend
tail -f logs/backend.log
tail -f logs/scheduler.log

# Logs do systemd (todas as execuções)
sudo journalctl -u tiktok-backend -f
sudo journalctl -u tiktok-scheduler -f

# Últimas N linhas
tail -n 100 beckend/logs/backend.log
sudo journalctl -u tiktok-backend -n 100

# Logs de hoje
sudo journalctl -u tiktok-backend --since today

# Logs entre datas
sudo journalctl -u tiktok-backend --since "2025-01-01" --until "2025-01-02"
```

### Limpar Logs

```bash
# Limpar logs da aplicação
cd beckend
> logs/backend.log
> logs/backend-error.log
> logs/scheduler.log
> logs/scheduler-error.log

# Limpar logs do systemd
sudo journalctl --vacuum-time=7d     # Manter apenas 7 dias
sudo journalctl --vacuum-size=100M   # Manter apenas 100MB
```

## 🔄 Auto-Start no Boot

### Verificar Status

```bash
# Ver se está habilitado
sudo systemctl is-enabled tiktok-backend
sudo systemctl is-enabled tiktok-scheduler

# Ver todos os serviços habilitados
sudo systemctl list-unit-files --type=service | grep tiktok
```

### Habilitar/Desabilitar

```bash
# Habilitar auto-start
sudo systemctl enable tiktok-backend
sudo systemctl enable tiktok-scheduler

# Desabilitar auto-start
sudo systemctl disable tiktok-backend
sudo systemctl disable tiktok-scheduler
```

## ⚠️ Troubleshooting

### Serviço não inicia

```bash
# Ver erro detalhado
sudo systemctl status tiktok-backend
sudo journalctl -u tiktok-backend -n 50

# Causas comuns:
# 1. Porta 8082 já em uso
sudo lsof -i :8082
sudo kill -9 <PID>

# 2. Ambiente virtual corrompido
cd beckend
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Permissões de logs
sudo chown -R $USER:$USER logs/
chmod 644 logs/*.log

# 4. Banco de dados não está rodando
docker ps | grep postgres
docker start postgres
```

### Serviço para sozinho

```bash
# Ver logs de crash
sudo journalctl -u tiktok-scheduler -n 100

# Verificar restart policy
sudo systemctl show tiktok-scheduler | grep Restart

# Reiniciar manualmente
sudo systemctl restart tiktok-scheduler
```

### Permissões negadas

```bash
# Logs mostram "Permission denied"
cd beckend

# Corrigir permissões
sudo chown -R $USER:$USER logs/
chmod 755 .
chmod 644 logs/*.log

# Reiniciar serviços
./manage.sh all restart
```

### Backend não responde

```bash
# Verificar se processo está rodando
ps aux | grep uvicorn

# Verificar porta
sudo netstat -tlnp | grep 8082

# Testar API
curl http://localhost:8082/health

# Ver logs
tail -f beckend/logs/backend.log
```

## 🔧 Manutenção

### Atualizar Serviços

Após atualizar o código:

```bash
# 1. Parar serviços
cd beckend
./manage.sh all stop

# 2. Atualizar dependências
source venv/bin/activate
pip install -r requirements.txt

# 3. Rodar migrações (se houver)
python init_db.py

# 4. Reiniciar serviços
./manage.sh all start

# 5. Verificar
./manage.sh all status
```

### Recriar Serviços

Se modificou os arquivos .service:

```bash
# 1. Parar serviços
sudo systemctl stop tiktok-backend tiktok-scheduler

# 2. Recarregar systemd
sudo systemctl daemon-reload

# 3. Reinstalar
cd beckend
./manage.sh backend install
./manage.sh scheduler install

# 4. Verificar
./manage.sh all status
```

### Backup de Logs

```bash
# Criar backup
cd beckend
tar -czf logs-backup-$(date +%Y%m%d).tar.gz logs/

# Restaurar backup
tar -xzf logs-backup-20250123.tar.gz
```

## 📊 Monitoramento

### Status Rápido

```bash
# Ver se estão rodando
sudo systemctl is-active tiktok-backend
sudo systemctl is-active tiktok-scheduler

# Ver uptime
sudo systemctl status tiktok-backend | grep Active
sudo systemctl status tiktok-scheduler | grep Active

# Ver uso de memória/CPU
ps aux | grep -E 'uvicorn|scheduler'
```

### Alertas de Falha

Configurar notificações por email quando serviços falham:

```bash
# /etc/systemd/system/tiktok-backend.service
[Service]
OnFailure=notify-email@%n.service
```

## 📚 Comandos Úteis

```bash
# Recarregar configuração do systemd
sudo systemctl daemon-reload

# Ver todas as propriedades de um serviço
sudo systemctl show tiktok-backend

# Ver dependências
sudo systemctl list-dependencies tiktok-backend

# Ver ordem de inicialização
sudo systemd-analyze plot > boot.svg

# Ver tempo de boot de cada serviço
sudo systemd-analyze blame

# Mascarar serviço (impossibilitar start)
sudo systemctl mask tiktok-backend

# Desmascarar
sudo systemctl unmask tiktok-backend
```

## 🔗 Próximos Passos

- **[Logs Completo](LOGS.md)** - Análise detalhada de logs
- **[Troubleshooting](TROUBLESHOOTING.md)** - Problemas comuns
- **[Deploy](DEPLOY.md)** - Como fazer deploy

---

**Dica**: Use `./manage.sh all status` para verificar rapidamente se tudo está funcionando.

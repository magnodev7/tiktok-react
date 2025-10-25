# 💾 Backup - Estratégia Completa

Guia de backup e recuperação de dados.

## 🎯 O que Fazer Backup

### Essencial
- 🗄️ **Banco de dados** PostgreSQL
- 📁 **Perfis TikTok** `beckend/profiles/`
- 📹 **Vídeos** `beckend/videos/` e `beckend/posted/`
- ⚙️ **Configurações** `.env`

### Opcional
- 📋 **Logs** `beckend/logs/`
- 🔧 **Configurações Nginx** `/etc/nginx/sites-available/tiktok`
- 🔑 **Certificados SSL** `/etc/letsencrypt/`

---

## 💾 Backup do Banco de Dados

### Backup Manual
```bash
# Criar backup
docker exec postgres pg_dump -U tiktok tiktok_db > backup_$(date +%Y%m%d_%H%M%S).sql

# Compactar
gzip backup_$(date +%Y%m%d_%H%M%S).sql
```

### Restaurar Backup
```bash
# Descompactar
gunzip backup_20250120_100000.sql.gz

# Restaurar
docker exec -i postgres psql -U tiktok -d tiktok_db < backup_20250120_100000.sql
```

---

## 📁 Backup de Arquivos

### Script de Backup Completo
```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/backup/tiktok"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="tiktok_backup_$DATE"

# Criar diretório
mkdir -p $BACKUP_DIR

# Backup do banco
docker exec postgres pg_dump -U tiktok tiktok_db > "$BACKUP_DIR/db_$DATE.sql"

# Backup de arquivos
tar -czf "$BACKUP_DIR/$BACKUP_NAME.tar.gz" \
  --exclude='node_modules' \
  --exclude='venv' \
  --exclude='__pycache__' \
  beckend/profiles/ \
  beckend/videos/ \
  beckend/posted/ \
  .env

echo "Backup criado: $BACKUP_DIR/$BACKUP_NAME.tar.gz"

# Manter apenas últimos 7 backups
ls -t $BACKUP_DIR/*.tar.gz | tail -n +8 | xargs rm -f
```

### Executar Backup
```bash
chmod +x backup.sh
./backup.sh
```

---

## ⏰ Backup Automático

### Cron Job Diário
```bash
# Editar crontab
crontab -e

# Adicionar (backup diário às 03:00)
0 3 * * * /home/ubuntu/tiktok-react/backup.sh
```

### Systemd Timer
```bash
# /etc/systemd/system/tiktok-backup.service
[Unit]
Description=TikTok Scheduler Backup

[Service]
Type=oneshot
ExecStart=/home/ubuntu/tiktok-react/backup.sh
User=ubuntu

# /etc/systemd/system/tiktok-backup.timer
[Unit]
Description=TikTok Backup Timer

[Timer]
OnCalendar=daily
OnCalendar=03:00
Persistent=true

[Install]
WantedBy=timers.target

# Ativar
sudo systemctl enable tiktok-backup.timer
sudo systemctl start tiktok-backup.timer
```

---

## ☁️ Backup Remoto

### Enviar para Servidor Remoto (rsync)
```bash
rsync -avz /backup/tiktok/ user@backup-server:/backups/tiktok/
```

### Google Drive (rclone)
```bash
# Instalar rclone
curl https://rclone.org/install.sh | sudo bash

# Configurar
rclone config

# Backup
rclone sync /backup/tiktok/ gdrive:tiktok-backups/
```

### AWS S3
```bash
# Instalar AWS CLI
sudo apt install awscli

# Configurar
aws configure

# Backup
aws s3 sync /backup/tiktok/ s3://seu-bucket/tiktok-backups/
```

---

## 🔄 Recuperação

### Recuperar Banco
```bash
# 1. Parar serviços
cd beckend
./manage.sh all stop

# 2. Restaurar banco
docker exec -i postgres psql -U tiktok -d tiktok_db < backup.sql

# 3. Reiniciar serviços
./manage.sh all start
```

### Recuperar Arquivos
```bash
# 1. Parar serviços
cd beckend
./manage.sh all stop

# 2. Extrair backup
tar -xzf tiktok_backup_20250120.tar.gz -C /home/ubuntu/tiktok-react/

# 3. Reiniciar serviços
./manage.sh all start
```

---

## 📊 Estratégia 3-2-1

Regra de backup profissional:

- **3** cópias dos dados
- **2** tipos de mídia diferentes
- **1** cópia offsite (remota)

**Exemplo:**
1. Dados originais no servidor
2. Backup local compactado
3. Backup no Google Drive/S3

---

## 💡 Boas Práticas

1. **Teste recuperação** mensalmente
2. **Automação** via cron/systemd
3. **Retenção**: 7 dias (diário), 4 semanas (semanal), 12 meses (mensal)
4. **Monitoramento**: Alertar se backup falhar
5. **Criptografia**: Para backups sensíveis

---

## 🔗 Links
- **[Deploy](DEPLOY.md)** - Deploy inicial
- **[Database](../setup/DATABASE.md)** - Banco de dados

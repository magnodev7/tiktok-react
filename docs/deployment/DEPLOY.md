# 🚀 Guia de Deploy - TikTok Scheduler

Deploy completo e automatizado em VPS Ubuntu/Debian.

## 📋 Pré-requisitos

### VPS/Servidor
- **SO**: Ubuntu 20.04+ ou Debian 10+
- **RAM**: Mínimo 1GB (recomendado 2GB+)
- **Disco**: Mínimo 10GB livres
- **Acesso**: SSH com sudo

### Opcional
- Domínio configurado (para HTTPS)
- Email (para certificado SSL)

## 🎯 Deploy em 3 Passos

### 1. Fazer Upload do Projeto

```bash
# Opção A: Via rsync (recomendado)
rsync -avz --exclude 'node_modules' --exclude 'venv' \
  tiktok-react/ usuario@seu-servidor:/home/usuario/tiktok-react/

# Opção B: Via Git
ssh usuario@seu-servidor
git clone <seu-repositorio>
cd tiktok-react
```

### 2. Executar Deploy Automático

```bash
ssh usuario@seu-servidor
cd tiktok-react
chmod +x deploy.sh
./deploy.sh
```

### 3. Acessar Aplicação

```bash
# HTTP (IP)
http://seu-ip

# HTTPS (Domínio - se configurou SSL)
https://seu-dominio.com
```

## 🔧 O que o Deploy Faz

O script `deploy.sh` executa **tudo automaticamente**:

### 1. Dependências do Sistema
- ✅ Atualiza cache apt
- ✅ Instala Docker CE (oficial)
- ✅ Instala Docker Compose (plugin + standalone)
- ✅ Instala Python 3.8+
- ✅ Instala pip + python3-venv
- ✅ Instala Node.js 20+
- ✅ Instala ferramentas (curl, git, build-essential)

### 2. PostgreSQL (Docker)
- ✅ Cria container PostgreSQL 16
- ✅ Configura volume persistente
- ✅ Aguarda banco ficar pronto
- ✅ Porta: 5432 (local apenas)

### 3. Backend Python
- ✅ Cria ambiente virtual (venv)
- ✅ Instala dependências (requirements.txt)
- ✅ Executa migrações do banco (Alembic)
- ✅ Cria usuário admin padrão

### 4. Serviços Systemd
- ✅ `tiktok-backend.service` - API REST (porta 8082)
- ✅ `tiktok-scheduler.service` - Daemon de agendamento
- ✅ Auto-start no boot
- ✅ Restart automático em falhas
- ✅ Logs em `beckend/logs/`

### 5. Frontend React
- ✅ Instala dependências (npm install)
- ✅ Build de produção (Vite)
- ✅ Copia para `beckend/web/`
- ✅ Servido pelo backend FastAPI

### 6. Nginx
- ✅ Instala Nginx (se necessário)
- ✅ Detecta IP do servidor
- ✅ Pergunta sobre domínio
- ✅ Cria configuração otimizada
- ✅ Remove configuração default
- ✅ Testa e reinicia Nginx

### 7. SSL/HTTPS (Opcional)
- ✅ Pergunta se deseja configurar SSL
- ✅ Instala Certbot
- ✅ Valida DNS do domínio
- ✅ Obtém certificado Let's Encrypt
- ✅ Configura redirecionamento HTTP→HTTPS
- ✅ Configura renovação automática
- ✅ Cria hook de pós-renovação

## 🎛️ Opções do Deploy

```bash
# Deploy completo (padrão)
./deploy.sh

# Pular setup do banco (se já existe)
./deploy.sh --skip-db

# Pular build do frontend
./deploy.sh --skip-fe

# Pular configuração do Nginx
./deploy.sh --skip-nginx

# Modo desenvolvimento (sem systemd nem nginx)
./deploy.sh --dev

# Combinar opções
./deploy.sh --skip-db --skip-fe
```

## 🔒 Configurar SSL Depois

Se pulou SSL durante deploy, pode configurar depois:

```bash
# Usar script dedicado
./setup-ssl.sh seu-dominio.com seu-email@exemplo.com

# Ou manualmente
sudo certbot --nginx -d seu-dominio.com
```

Veja: [Guia SSL/HTTPS](SSL.md)

## 📊 Verificar Deploy

### Serviços

```bash
# Status de todos os serviços
cd beckend
./manage.sh all status

# Apenas backend
./manage.sh backend status

# Apenas scheduler
./manage.sh scheduler status
```

### Logs

```bash
# Logs dos serviços
cd beckend
./manage.sh all logs

# Logs do Nginx
sudo tail -f /var/log/nginx/tiktok-error.log

# Logs do PostgreSQL
docker logs -f postgres
```

### Acessos

```bash
# API (documentação interativa)
http://seu-ip:8082/docs

# Frontend
http://seu-ip

# Health check
curl http://seu-ip:8082/health
```

## 🔧 Gerenciar Serviços

```bash
cd beckend

# Parar todos
./manage.sh all stop

# Iniciar todos
./manage.sh all start

# Reiniciar todos
./manage.sh all restart

# Ver status
./manage.sh all status

# Ver logs em tempo real
./manage.sh all logs
```

## 🔄 Atualizar Aplicação

```bash
# 1. Fazer backup do banco (opcional)
docker exec postgres pg_dump -U tiktok tiktok_db > backup.sql

# 2. Parar serviços
cd beckend
./manage.sh all stop

# 3. Atualizar código
git pull
# ou fazer upload dos novos arquivos

# 4. Atualizar backend
cd beckend
source venv/bin/activate
pip install -r requirements.txt
python init_db.py  # Rodar novas migrações

# 5. Atualizar frontend
cd ..
npm install
npm run build
cp -r dist beckend/web/

# 6. Reiniciar serviços
cd beckend
./manage.sh all restart

# 7. Verificar
./manage.sh all status
```

## 🧹 Re-deploy Limpo

```bash
# 1. Limpar projeto local
./clean-project.sh

# 2. Fazer upload limpo
rsync -avz --delete tiktok-react/ usuario@servidor:/path/

# 3. Rodar deploy
ssh usuario@servidor
cd tiktok-react
./deploy.sh
```

## ⚠️ Troubleshooting

### Deploy falhou na instalação do Docker

```bash
# Instalar Docker manualmente
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
```

### Serviços não iniciam

```bash
# Ver logs detalhados
sudo journalctl -u tiktok-backend -n 100
sudo journalctl -u tiktok-scheduler -n 100

# Verificar permissões de logs
cd beckend
sudo chown -R $USER:$USER logs/
```

### PostgreSQL não conecta

```bash
# Verificar se container está rodando
docker ps | grep postgres

# Reiniciar container
docker restart postgres

# Ver logs
docker logs postgres
```

### Nginx retorna 502

```bash
# Verificar se backend está rodando
sudo systemctl status tiktok-backend

# Verificar logs do Nginx
sudo tail -f /var/log/nginx/tiktok-error.log

# Reiniciar backend
cd beckend
./manage.sh backend restart
```

### SSL falhou

```bash
# Verificar DNS
dig seu-dominio.com

# Verificar portas abertas
sudo ufw status
sudo ufw allow 80
sudo ufw allow 443

# Tentar novamente
./setup-ssl.sh seu-dominio.com seu-email@exemplo.com
```

## 📚 Próximos Passos

1. ✅ **[Configurar SSL](SSL.md)** - Se ainda não configurou
2. ✅ **[Primeiros Passos](../setup/QUICKSTART.md)** - Usar a aplicação
3. ✅ **[API](../api/API.md)** - Integrar com outras ferramentas
4. ✅ **[Backup](BACKUP.md)** - Configurar backups automáticos

## 🔗 Links Úteis

- [Serviços Systemd](SYSTEMD.md)
- [Nginx](NGINX.md)
- [Logs](LOGS.md)
- [Troubleshooting](TROUBLESHOOTING.md)

---

**Dica**: Execute `./deploy.sh --help` para ver todas as opções disponíveis.

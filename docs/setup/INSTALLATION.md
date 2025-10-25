# 📦 Instalação - Guia Completo

Guia detalhado de instalação manual (sem deploy.sh).

## 📋 Requisitos

### Sistema
- Ubuntu 20.04+ ou Debian 10+
- 1GB RAM mínimo (2GB+ recomendado)
- 10GB disco livre
- Acesso root/sudo

### Software
- Docker 20.10+
- Docker Compose 2.0+
- Python 3.8+
- Node.js 20+
- Nginx (opcional)

---

## 🚀 Instalação Rápida

Use o script automático:
```bash
./deploy.sh
```

Veja: [Guia de Deploy](../deployment/DEPLOY.md)

---

## 🔧 Instalação Manual

### 1. Instalar Dependências

```bash
# Atualizar sistema
sudo apt update
sudo apt upgrade -y

# Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
sudo chmod 666 /var/run/docker.sock

# Docker Compose
sudo apt install -y docker-compose-plugin

# Python
sudo apt install -y python3 python3-pip python3-venv

# Node.js
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Nginx
sudo apt install -y nginx
```

### 2. Clonar Projeto

```bash
git clone <seu-repositorio>
cd tiktok-react
```

### 3. PostgreSQL

```bash
# Criar container
docker run -d \
  --name postgres \
  -e POSTGRES_DB=tiktok_db \
  -e POSTGRES_USER=tiktok \
  -e POSTGRES_PASSWORD=tiktok123 \
  -p 5432:5432 \
  -v postgres_data:/var/lib/postgresql/data \
  postgres:16

# Aguardar inicialização
sleep 10
```

### 4. Backend

```bash
cd beckend

# Criar venv
python3 -m venv venv
source venv/bin/activate

# Instalar dependências
pip install -r requirements.txt

# Migrações
python init_db.py

# Testar
python -m uvicorn src.main:app --host 0.0.0.0 --port 8082
```

### 5. Frontend

```bash
cd ..

# Instalar dependências
npm install

# Build
npm run build

# Copiar para backend
cp -r dist beckend/web/
```

### 6. Serviços Systemd

```bash
cd beckend
./manage.sh backend install
./manage.sh scheduler install

# Iniciar
./manage.sh all start
```

### 7. Nginx (Opcional)

Veja: [Guia Nginx](../deployment/NGINX.md)

---

## ✅ Verificação

```bash
# Backend
curl http://localhost:8082/health

# Frontend
curl http://localhost

# Serviços
cd beckend
./manage.sh all status
```

---

## 🔗 Próximos Passos

1. **[Quick Start](QUICKSTART.md)** - Primeiros passos
2. **[Database](DATABASE.md)** - Configurar banco
3. **[SSL](../deployment/SSL.md)** - HTTPS

---

**Versão**: 2.0

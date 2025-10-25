# 🎬 TikTok Scheduler - Sistema de Agendamento Automático

Sistema profissional completo para agendamento e automação de postagens no TikTok, com interface web moderna e API REST robusta.

![Status](https://img.shields.io/badge/status-active-success.svg)
![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![React](https://img.shields.io/badge/react-18.x-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green.svg)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue.svg)

---

## 🚀 Deploy em 3 Passos

### 1. Clonar/Upload do Projeto

```bash
# Via Git
git clone <seu-repositorio>
cd tiktok-react

# Ou via rsync (de sua máquina local)
rsync -avz --exclude 'node_modules' --exclude 'venv' \
  tiktok-react/ usuario@seu-servidor:/home/usuario/tiktok-react/
```

### 2. Executar Deploy Automático

```bash
# No servidor
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

**Credenciais padrão**: `admin` / `admin123` (altere após primeiro login!)

---

## 📋 O que o Deploy Faz?

O script `deploy.sh` configura **tudo automaticamente**:

✅ **Dependências do Sistema**
- Docker CE + Docker Compose
- Python 3.8+ + pip + venv
- Node.js 20+
- Nginx

✅ **Banco de Dados**
- PostgreSQL 16 (Docker)
- Migrações automáticas (Alembic)
- Usuário admin padrão

✅ **Backend**
- API REST FastAPI (porta 8082)
- Daemon de agendamento
- Serviços systemd (auto-start + auto-restart)

✅ **Frontend**
- Build de produção (Vite)
- Servido pelo backend

✅ **Nginx** (opcional)
- Reverse proxy otimizado
- Configuração automática de IP/domínio

✅ **SSL/HTTPS** (opcional)
- Certificado Let's Encrypt
- Renovação automática
- Redirecionamento HTTP→HTTPS

---

## ✨ Funcionalidades

- 🎯 **Upload Automatizado** - Envie vídeos para múltiplas contas TikTok
- ⏰ **Agendamento Inteligente** - Programe horários personalizados por conta
- 📅 **Planner Automático** - Distribui vídeos automaticamente nos melhores horários
- 👥 **Multi-conta** - Gerencie várias contas em uma interface
- 📊 **Analytics** - Estatísticas e métricas de postagens
- 🔒 **Segurança** - Autenticação JWT, roles, API keys
- 🔄 **API REST** - Integração com n8n, Make, Zapier
- 📱 **Responsivo** - Funciona em desktop, tablet e mobile
- 🐳 **Docker Ready** - PostgreSQL containerizado

---

## 🛠️ Tecnologias

### Backend
- **Python 3.8+** - Linguagem base
- **FastAPI** - Framework web moderno
- **SQLAlchemy** - ORM
- **Alembic** - Migrações de banco
- **Selenium** - Automação do TikTok
- **APScheduler** - Motor de agendamento

### Frontend
- **React 18** + TypeScript
- **Vite** - Build tool ultrarrápido
- **TailwindCSS** - Framework CSS
- **Lucide Icons** - Ícones modernos
- **TanStack Query** - Estado assíncrono
- **Axios** - Cliente HTTP

### Infraestrutura
- **PostgreSQL 16** - Banco de dados
- **Docker** + Docker Compose
- **Nginx** - Servidor web / Reverse proxy
- **Systemd** - Gerenciamento de serviços
- **Let's Encrypt** - Certificados SSL

---

## 📚 Documentação Completa

Toda documentação está em `/docs`:

### 🚀 Início Rápido
- **[Guia de Deploy](docs/deployment/DEPLOY.md)** - Deploy completo em VPS
- **[Primeiros Passos](docs/setup/QUICKSTART.md)** - Configure e use em 5 minutos
- **[Limpeza do Projeto](docs/setup/CLEAN_PROJECT.md)** - Remover cache e dados

### 🔧 Configuração
- **[SSL/HTTPS](docs/deployment/SSL.md)** - Certificados Let's Encrypt
- **[Serviços Systemd](docs/deployment/SYSTEMD.md)** - Backend e Scheduler
- **[Nginx](docs/deployment/NGINX.md)** - Configuração do servidor web

### 📡 API
- **[Documentação da API](docs/api/API.md)** - Endpoints REST
- **[Autenticação](docs/api/AUTH.md)** - Login, tokens, API keys
- **[Integração N8N](docs/api/N8N.md)** - Automação com n8n.io
- **[Analytics](docs/api/ANALYTICS.md)** - Estatísticas e métricas

### ✨ Funcionalidades
- **[Agendamento](docs/features/SCHEDULING.md)** - Como agendar vídeos
- **[Contas TikTok](docs/features/ACCOUNTS.md)** - Gerenciamento de contas
- **[Planner Inteligente](docs/features/PLANNER.md)** - Distribuição automática
- **[Metadados](docs/features/METADATA.md)** - Títulos, descrições, hashtags

---

## 📁 Estrutura do Projeto

```
tiktok-react/
├── docs/                    # 📚 Documentação completa
│   ├── setup/              # Instalação e configuração
│   ├── deployment/         # Deploy e infraestrutura
│   ├── api/                # Documentação da API
│   └── features/           # Funcionalidades do sistema
│
├── src/                    # 💻 Frontend (React + TypeScript)
│   ├── components/         # Componentes React
│   ├── pages/              # Páginas da aplicação
│   ├── services/           # Serviços e API calls
│   └── utils/              # Utilitários
│
├── beckend/                # 🐍 Backend (Python + FastAPI)
│   ├── src/                # Código-fonte Python
│   │   ├── api/           # Rotas da API
│   │   ├── models.py      # Modelos do banco
│   │   ├── scheduler.py   # Motor de agendamento
│   │   └── uploader.py    # Upload para TikTok
│   ├── alembic/           # Migrações do banco
│   ├── logs/              # Logs da aplicação
│   ├── videos/            # Vídeos para upload
│   ├── posted/            # Vídeos já postados
│   └── state/             # Estado da aplicação
│
├── deploy.sh              # 🚀 Script de deploy automático
├── setup-ssl.sh           # 🔒 Configuração SSL
├── clean-project.sh       # 🧹 Script de limpeza
└── beckend/manage.sh      # 🎛️ Gerenciar serviços
```

---

## 🔧 Gerenciar Serviços

```bash
cd beckend

# Todos os serviços
./manage.sh all start      # Iniciar
./manage.sh all stop       # Parar
./manage.sh all restart    # Reiniciar
./manage.sh all status     # Ver status
./manage.sh all logs       # Ver logs

# Backend ou scheduler individualmente
./manage.sh backend start
./manage.sh scheduler status
```

---

## 🔄 Atualizar Aplicação

```bash
# 1. Parar serviços
cd beckend
./manage.sh all stop

# 2. Atualizar código
git pull
# ou fazer upload dos novos arquivos

# 3. Atualizar backend
source venv/bin/activate
pip install -r requirements.txt
python init_db.py  # Rodar novas migrações

# 4. Atualizar frontend
cd ..
npm install
npm run build
cp -r dist beckend/web/

# 5. Reiniciar serviços
cd beckend
./manage.sh all restart

# 6. Verificar
./manage.sh all status
```

---

## 🧹 Limpar Projeto

Antes de fazer commit ou deploy, limpe o projeto:

```bash
./clean-project.sh
```

Remove:
- `node_modules/`, `venv/`
- Cache, logs, perfis de usuário
- Vídeos e dados temporários

Reduz de ~2GB para ~3MB!

---

## 🎯 Casos de Uso

### Agência de Marketing
- Gerenciar múltiplas contas de clientes
- Agendar centenas de vídeos semanalmente
- Distribuição automática com Planner

### Criador de Conteúdo
- Agendar vídeos com antecedência
- Horários otimizados de postagem
- Análise de performance

### E-commerce
- Vídeos de produtos agendados
- Campanhas promocionais automáticas
- Integração com sistemas externos via API

---

## 🆘 Troubleshooting

### Serviços não iniciam

```bash
# Ver logs detalhados
cd beckend
./manage.sh all logs

# Verificar permissões
sudo chown -R $USER:$USER logs/

# Reiniciar
./manage.sh all restart
```

### PostgreSQL não conecta

```bash
# Verificar container
docker ps | grep postgres

# Reiniciar
docker restart postgres

# Ver logs
docker logs postgres
```

### Nginx retorna 502

```bash
# Verificar backend
sudo systemctl status tiktok-backend

# Reiniciar backend
cd beckend
./manage.sh backend restart
```

Veja mais: **[Troubleshooting Completo](docs/deployment/TROUBLESHOOTING.md)**

---

## 📊 Requisitos Mínimos

### VPS/Servidor
- **SO**: Ubuntu 20.04+ ou Debian 10+
- **RAM**: Mínimo 1GB (recomendado 2GB+)
- **Disco**: Mínimo 10GB livres
- **Acesso**: SSH com sudo

### Opcional
- Domínio configurado (para HTTPS)
- Email (para certificado SSL)

---

## 🔗 Links Úteis

- **[Documentação Completa](docs/README.md)** - Índice de toda documentação
- **[Guia de Deploy](docs/deployment/DEPLOY.md)** - Deploy passo a passo
- **[Primeiros Passos](docs/setup/QUICKSTART.md)** - Começar a usar
- **[API](docs/api/API.md)** - Endpoints e integração
- **[SSL](docs/deployment/SSL.md)** - Configurar HTTPS

---

## 📝 Licença

MIT

---

## 🤝 Contribuindo

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

---

**Versão**: 2.0
**Última atualização**: Outubro 2025

**Dica**: Execute `./deploy.sh --help` para ver todas as opções de deploy disponíveis!

# 📚 Documentação - TikTok Scheduler

Bem-vindo à documentação completa do TikTok Scheduler! Sistema profissional para agendamento e automação de postagens no TikTok.

## 📖 Índice

### 🚀 Início Rápido
- **[Guia de Instalação](setup/INSTALLATION.md)** - Como instalar o sistema
- **[Deploy Automático](deployment/DEPLOY.md)** - Deploy completo em VPS
- **[Primeiros Passos](setup/QUICKSTART.md)** - Configure e use em 5 minutos

### 🔧 Configuração
- **[Configuração SSL/HTTPS](deployment/SSL.md)** - Certificados Let's Encrypt
- **[Serviços Systemd](deployment/SYSTEMD.md)** - Backend e Scheduler como serviços
- **[Nginx](deployment/NGINX.md)** - Configuração do servidor web
- **[Banco de Dados](setup/DATABASE.md)** - PostgreSQL e migrações

### 📡 API
- **[Documentação da API](api/API.md)** - Endpoints REST completos
- **[Autenticação](api/AUTH.md)** - Login, tokens e API keys
- **[Integração N8N](api/N8N.md)** - Automação com n8n.io
- **[Analytics](api/ANALYTICS.md)** - Estatísticas e métricas

### ✨ Funcionalidades
- **[Agendamento](features/SCHEDULING.md)** - Como agendar vídeos
- **[Contas TikTok](features/ACCOUNTS.md)** - Gerenciamento de contas
- **[Planner Inteligente](features/PLANNER.md)** - Distribuição automática
- **[Metadados](features/METADATA.md)** - Títulos, descrições, hashtags

### 🛠️ Manutenção
- **[Limpeza do Projeto](../CLEAN_PROJECT.md)** - Remover cache e dados
- **[Logs](deployment/LOGS.md)** - Onde encontrar e como analisar
- **[Troubleshooting](deployment/TROUBLESHOOTING.md)** - Problemas comuns

## 🎯 Estrutura do Projeto

```
tiktok-react/
├── docs/                    # 📚 Documentação (você está aqui!)
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
│   └── state/             # Estado da aplicação
│
├── deploy.sh              # 🚀 Script de deploy automático
├── clean-project.sh       # 🧹 Script de limpeza
└── setup-ssl.sh           # 🔒 Configuração SSL
```

## 🚀 Deploy Rápido (VPS Ubuntu/Debian)

```bash
# 1. Clonar/Upload do projeto
git clone <seu-repo>
cd tiktok-react

# 2. Executar deploy automático
./deploy.sh

# 3. Acessar aplicação
# http://seu-ip  ou  https://seu-dominio.com
```

O script `deploy.sh` instala **tudo automaticamente**:
- ✅ Docker + Docker Compose
- ✅ Python 3.8+ + dependências
- ✅ Node.js 20+
- ✅ PostgreSQL (Docker)
- ✅ Backend + Serviços systemd
- ✅ Frontend (build)
- ✅ Nginx
- ✅ SSL/HTTPS (opcional)

## 🔑 Credenciais Padrão

Após primeiro deploy:
- **Usuário**: `admin`
- **Senha**: `admin123`

⚠️ **IMPORTANTE**: Altere a senha após primeiro login!

## 📊 Tecnologias

### Frontend
- **React 18** + TypeScript
- **Vite** - Build ultra-rápido
- **TailwindCSS** - Estilização
- **Lucide Icons** - Ícones

### Backend
- **Python 3.8+**
- **FastAPI** - API REST
- **SQLAlchemy** - ORM
- **Alembic** - Migrações
- **Selenium** - Automação TikTok
- **APScheduler** - Agendamento

### Infraestrutura
- **PostgreSQL 16** - Banco de dados
- **Docker** - Containers
- **Nginx** - Servidor web
- **Systemd** - Serviços
- **Let's Encrypt** - SSL/HTTPS

## 🆘 Suporte

- **Issues**: [GitHub Issues](seu-repo/issues)
- **Documentação**: Esta pasta `/docs`
- **Logs**: `beckend/logs/`

## 📝 Licença

[Sua licença aqui]

---

**Versão**: 2.0
**Última atualização**: Outubro 2025

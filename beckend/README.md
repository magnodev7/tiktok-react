# 🎬 TikTok Scheduler - Backend

Sistema completo de agendamento e postagem automática para TikTok com múltiplas contas.

## ⚡ Início Rápido

```bash
# 1. Instalar serviços systemd
./manage.sh all install

# 2. Iniciar sistema
./manage.sh all start

# 3. Verificar status
./manage.sh all status

# 4. Ver logs
./manage.sh all logs
```

## 📚 Documentação Completa

Toda a documentação está organizada na pasta **`docs/`**:

- **[docs/README.md](./docs/README.md)** - Índice geral e visão do sistema
- **[docs/INSTALL.md](./docs/INSTALL.md)** - Guia de instalação passo a passo
- **[docs/README-SERVICES.md](./docs/README-SERVICES.md)** - Gerenciamento de serviços systemd

## 🏗️ Arquitetura

```
Backend HTTP (FastAPI)  ←→  PostgreSQL
       ↓
Scheduler Daemon  →  Selenium + Chrome  →  TikTok.com
```

### Componentes

1. **Backend HTTP** (porta 8082)
   - API REST para gerenciamento
   - Upload de vídeos
   - Autenticação JWT

2. **Scheduler Daemon**
   - Processamento automático
   - Suporta múltiplas contas
   - Upload via Selenium

> **Novidade (2025):** todas as respostas HTTP agora seguem o formato unificado `{ "success": bool, "data": ..., "message": ... }`,
> facilitando o consumo pela interface React hospedada externamente.

## 🚀 Comandos Principais

```bash
# Gerenciamento (via manage.sh)
./manage.sh all start      # Iniciar tudo
./manage.sh all stop       # Parar tudo
./manage.sh all restart    # Reiniciar
./manage.sh all status     # Ver status
./manage.sh all logs       # Logs em tempo real

# Componentes individuais
./manage.sh backend [ação]
./manage.sh scheduler [ação]
```

## 📁 Estrutura

```
beckend/
├── docs/              # 📚 Documentação completa
├── src/               # 💻 Código fonte
├── videos/            # 📹 Vídeos para postar
├── posted/            # ✅ Vídeos postados
├── logs/              # 📊 Logs do sistema
├── manage.sh          # 🎮 Script de gerenciamento
└── .env               # ⚙️ Configurações
```

## 🔧 Tecnologias

- **Python 3.12+**
- **FastAPI** - Framework web
- **PostgreSQL** - Banco de dados
- **Selenium** - Automação do navegador
- **Systemd** - Gerenciamento de serviços

## 📊 Status

- ✅ Backend HTTP funcionando
- ✅ Scheduler daemon ativo
- ✅ Upload automático via Selenium
- ✅ Suporte a múltiplas contas
- ✅ Sistema de logs robusto
- ✅ Auto-restart em caso de falha

## 🔗 Links Úteis

- **API Health**: http://localhost:8082/health
- **Documentação API**: http://localhost:8082/docs
- **Painel Admin**: http://localhost:8082

## 🛠️ Desenvolvimento

```bash
# Backend em modo desenvolvimento
source venv/bin/activate
python -m uvicorn src.http_health:app --reload

# Scheduler manual
source venv/bin/activate
python start_scheduler.py start

# Testes
python test_login_debug.py
python test_selenium_local.py
```

## 📞 Suporte

Consulte a **[documentação completa](./docs/)** para:
- Guias de instalação
- Troubleshooting
- Configuração avançada
- Monitoramento
- Segurança

## 🔐 Segurança

- Não compartilhe cookies do TikTok
- Não commite o arquivo `.env`
- Use HTTPS em produção
- Faça backup do banco de dados

## 📝 Licença

Copyright © 2025. Todos os direitos reservados.

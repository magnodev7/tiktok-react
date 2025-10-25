# 🧹 Limpeza do Projeto

Este documento explica como manter o projeto limpo, sem dados de usuário ou cache.

## Script de Limpeza Automática

Use o script `clean-project.sh` para limpar o projeto automaticamente:

```bash
./clean-project.sh
```

### O que é removido:

#### Frontend:
- ❌ `node_modules/` - Dependências Node.js (reinstalar com `npm install`)
- ❌ `dist/` - Build do frontend
- ❌ `.vite/` - Cache do Vite
- ❌ `package-lock.json` - Lock file do npm
- ❌ `profiles/` - Perfis do Chrome

#### Backend:
- ❌ `venv/` - Ambiente virtual Python
- ❌ `__pycache__/` - Cache do Python
- ❌ `*.pyc` - Bytecode Python
- ❌ `.pytest_cache/` - Cache de testes
- ❌ `profiles/` - Perfis de usuário
- ❌ `user_data/` - Dados de usuários
- ❌ `logs/*.log` - Arquivos de log
- ❌ `posted/*` - Vídeos já postados
- ❌ `videos/*` - Vídeos agendados
- ❌ `state/*.json` - Estado da aplicação
- ❌ `state/*.db` - Banco de dados local
- ❌ `tiktok_cookies.json` - Cookies salvos
- ❌ `*.bak`, `*.backup` - Arquivos de backup

### O que é mantido:

✅ Todo o código-fonte
✅ Arquivos de configuração (`.env.example`, etc)
✅ Documentação (`.md`)
✅ Scripts de deploy
✅ Estrutura de diretórios (vazias)

## Tamanho após Limpeza

- **Antes**: ~2GB+ (com node_modules, venv, profiles, cache)
- **Depois**: ~3MB (apenas código-fonte)

## Quando Limpar?

1. **Antes de commit no Git** - Não versionar dados de usuário
2. **Antes de fazer deploy** - Enviar apenas código limpo
3. **Antes de backup** - Reduzir tamanho do backup
4. **Antes de compartilhar** - Não compartilhar dados sensíveis

## Reinstalar Dependências

### Frontend:
```bash
npm install
```

### Backend:
```bash
cd beckend
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
.\venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

## Estrutura Limpa

```
tiktok-react/
├── beckend/
│   ├── src/           # Código-fonte Python
│   ├── alembic/       # Migrações do banco
│   ├── docs/          # Documentação
│   ├── logs/          # (vazio) Logs serão criados aqui
│   ├── posted/        # (vazio) Vídeos postados
│   ├── videos/        # (vazio) Vídeos para postar
│   ├── state/         # (vazio) Estado da aplicação
│   ├── requirements.txt
│   ├── deploy.sh
│   └── manage.sh
├── src/               # Código-fonte React
├── public/            # Assets públicos
├── deploy.sh          # Script de deploy principal
├── clean-project.sh   # Este script de limpeza
├── package.json
└── README.md
```

## Gitignore

O projeto já possui um `.gitignore` configurado para não versionar:
- `node_modules/`
- `venv/`
- `dist/`
- `*.pyc`
- `__pycache__/`
- `profiles/`
- `user_data/`
- `*.log`
- `.env` (apenas `.env.example` é versionado)

## Dicas

1. **Sempre rode `clean-project.sh` antes de commitar código novo**
2. **Mantenha `.env.example` atualizado, mas nunca commite `.env`**
3. **Use o `.gitignore` para prevenir commits acidentais**
4. **Deploy na VPS vai instalar tudo automaticamente com `deploy.sh`**

## Automatização

Você pode adicionar ao seu `.git/hooks/pre-commit`:

```bash
#!/bin/bash
# Limpar projeto antes de commit
./clean-project.sh --silent
```

Isso garante que você nunca comite dados de usuário acidentalmente.

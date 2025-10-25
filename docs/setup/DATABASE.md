# 🗄️ Banco de Dados - PostgreSQL

Guia completo do banco de dados PostgreSQL.

## 📋 Configuração

### Container Docker

```bash
docker run -d \
  --name postgres \
  -e POSTGRES_DB=tiktok_db \
  -e POSTGRES_USER=tiktok \
  -e POSTGRES_PASSWORD=tiktok123 \
  -p 5432:5432 \
  -v postgres_data:/var/lib/postgresql/data \
  postgres:16
```

### Conexão

**String de conexão:**
```
postgresql://tiktok:tiktok123@localhost:5432/tiktok_db
```

**Variáveis de ambiente (.env):**
```bash
DATABASE_URL=postgresql://tiktok:tiktok123@localhost:5432/tiktok_db
```

---

## 🔧 Migrações (Alembic)

### Criar Migração

```bash
cd beckend
source venv/bin/activate

# Auto-gerar migração
alembic revision --autogenerate -m "Descrição da mudança"

# Migração manual
alembic revision -m "Nome da migração"
```

### Aplicar Migrações

```bash
# Aplicar todas
alembic upgrade head

# Aplicar específica
alembic upgrade +1

# Ver histórico
alembic history

# Ver atual
alembic current
```

### Reverter Migrações

```bash
# Reverter última
alembic downgrade -1

# Reverter todas
alembic downgrade base

# Reverter para específica
alembic downgrade <revision_id>
```

---

## 🔍 Acessar Banco

### Via psql

```bash
# Entrar no container
docker exec -it postgres psql -U tiktok -d tiktok_db

# Comandos úteis:
\dt              # Listar tabelas
\d+ users        # Descrever tabela
SELECT * FROM users;
\q               # Sair
```

### Via Python

```python
from sqlalchemy import create_engine
import pandas as pd

engine = create_engine('postgresql://tiktok:tiktok123@localhost:5432/tiktok_db')

# Query
df = pd.read_sql('SELECT * FROM users', engine)
print(df)
```

---

## 📊 Estrutura de Tabelas

### users
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'user',
    created_at TIMESTAMP DEFAULT NOW()
);
```

### accounts
```sql
CREATE TABLE accounts (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    username VARCHAR(100) NOT NULL,
    status VARCHAR(20) DEFAULT 'active',
    user_id INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW()
);
```

### videos
```sql
CREATE TABLE videos (
    id SERIAL PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    filename VARCHAR(255) NOT NULL,
    account_id INTEGER REFERENCES accounts(id),
    scheduled_time TIMESTAMP,
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## 💾 Backup e Restauração

### Backup

```bash
# Backup completo
docker exec postgres pg_dump -U tiktok tiktok_db > backup.sql

# Backup compactado
docker exec postgres pg_dump -U tiktok tiktok_db | gzip > backup.sql.gz

# Backup apenas dados
docker exec postgres pg_dump -U tiktok --data-only tiktok_db > data.sql

# Backup apenas esquema
docker exec postgres pg_dump -U tiktok --schema-only tiktok_db > schema.sql
```

### Restauração

```bash
# Restaurar completo
docker exec -i postgres psql -U tiktok -d tiktok_db < backup.sql

# Restaurar compactado
gunzip < backup.sql.gz | docker exec -i postgres psql -U tiktok -d tiktok_db
```

Veja mais: [Guia de Backup](../deployment/BACKUP.md)

---

## 🔧 Manutenção

### Verificar Tamanho

```sql
-- Tamanho do banco
SELECT pg_size_pretty(pg_database_size('tiktok_db'));

-- Tamanho por tabela
SELECT 
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### Limpar Dados Antigos

```sql
-- Deletar vídeos postados há mais de 30 dias
DELETE FROM videos 
WHERE status = 'posted' 
AND created_at < NOW() - INTERVAL '30 days';

-- Vacuum para recuperar espaço
VACUUM FULL;
```

### Reindexar

```bash
docker exec postgres reindexdb -U tiktok tiktok_db
```

---

## ⚠️ Troubleshooting

### Container não inicia
```bash
# Ver logs
docker logs postgres

# Reiniciar
docker restart postgres

# Recriar (PERDE DADOS!)
docker stop postgres
docker rm postgres
# Rodar comando de criação novamente
```

### Conexão recusada
```bash
# Verificar se está rodando
docker ps | grep postgres

# Verificar porta
docker port postgres

# Testar conexão
docker exec postgres pg_isready -U tiktok
```

### Migração falha
```bash
# Ver erro detalhado
alembic upgrade head

# Forçar versão
alembic stamp head

# Resetar banco (PERDE DADOS!)
alembic downgrade base
alembic upgrade head
```

---

## 🔗 Links

- **[Installation](INSTALLATION.md)** - Instalação
- **[Backup](../deployment/BACKUP.md)** - Backups automáticos
- **[Troubleshooting](../deployment/TROUBLESHOOTING.md)** - Problemas comuns

---

**Versão**: 2.0

# 🔑 Autenticação - JWT e API Keys

Sistema completo de autenticação com JWT tokens e API keys para integrações.

## 🎯 Visão Geral

O TikTok Scheduler oferece dois métodos de autenticação:

| Método | Uso | Validade |
|--------|-----|----------|
| **JWT Token** | Interface web, aplicativos móveis | 24 horas |
| **API Key** | Integrações, automações, webhooks | Permanente |

---

## 🔐 JWT Authentication

### Login

**Endpoint:** `POST /api/auth/login`

**Request:**
```json
{
  "username": "admin",
  "password": "admin123"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "expires_in": 86400,
    "user": {
      "id": 1,
      "username": "admin",
      "email": "admin@example.com",
      "role": "admin"
    }
  }
}
```

### Usar o Token

Incluir em todas as requisições:

```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Exemplo cURL:**
```bash
curl http://localhost:8082/api/videos \
  -H "Authorization: Bearer <seu-token>"
```

**Exemplo JavaScript:**
```javascript
const headers = {
  'Authorization': `Bearer ${token}`
};

fetch('http://localhost:8082/api/videos', { headers });
```

### Refresh Token

Os tokens expiram após 24 horas. Para obter um novo token sem fazer login novamente:

**Endpoint:** `POST /api/auth/refresh`

**Headers:**
```http
Authorization: Bearer <token-antigo>
```

**Response:**
```json
{
  "success": true,
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "expires_in": 86400
  }
}
```

### Logout

**Endpoint:** `POST /api/auth/logout`

**Headers:**
```http
Authorization: Bearer <token>
```

Revoga o token atual.

---

## 🔑 API Keys

API Keys são ideais para:
- ✅ Integrações (n8n, Make, Zapier)
- ✅ Scripts de automação
- ✅ Webhooks
- ✅ Acesso de longo prazo sem login

### Criar API Key

**Endpoint:** `POST /api/api-keys`

**Headers:**
```http
Authorization: Bearer <token>
```

**Request:**
```json
{
  "name": "Integração N8N",
  "permissions": ["read", "write"]
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "name": "Integração N8N",
    "key": "sk_live_abc123xyz789defghij...",
    "permissions": ["read", "write"],
    "created_at": "2025-01-20T10:00:00"
  }
}
```

⚠️ **IMPORTANTE**: A chave completa só é mostrada UMA VEZ na criação! Guarde em local seguro.

### Usar API Key

Incluir no header `X-API-Key`:

```http
X-API-Key: sk_live_abc123xyz789defghij...
```

**Exemplo cURL:**
```bash
curl http://localhost:8082/api/videos \
  -H "X-API-Key: sk_live_abc123xyz789..."
```

**Exemplo Python:**
```python
import requests

headers = {
    "X-API-Key": "sk_live_abc123xyz789..."
}

response = requests.get(
    "http://localhost:8082/api/videos",
    headers=headers
)
```

### Listar API Keys

**Endpoint:** `GET /api/api-keys`

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "name": "Integração N8N",
      "key_preview": "sk_live_abc...xyz",
      "permissions": ["read", "write"],
      "last_used": "2025-01-20T15:30:00",
      "created_at": "2025-01-20T10:00:00"
    }
  ]
}
```

### Revogar API Key

**Endpoint:** `DELETE /api/api-keys/{id}`

Remove permanentemente a API key. Não pode ser desfeito.

---

## 👥 Roles e Permissões

### Roles Disponíveis

| Role | Descrição | Permissões |
|------|-----------|------------|
| **admin** | Administrador completo | Tudo |
| **user** | Usuário padrão | Gerenciar próprios vídeos e contas |
| **viewer** | Apenas visualização | Ver dados (read-only) |

### Permissões por Endpoint

| Endpoint | admin | user | viewer |
|----------|-------|------|--------|
| GET `/videos` | ✅ | ✅ | ✅ |
| POST `/videos/upload` | ✅ | ✅ | ❌ |
| DELETE `/videos/{id}` | ✅ | ✅* | ❌ |
| GET `/accounts` | ✅ | ✅ | ✅ |
| POST `/accounts` | ✅ | ✅ | ❌ |
| POST `/auth/register` | ✅ | ❌ | ❌ |
| GET `/api-keys` | ✅ | ✅ | ❌ |

\* Apenas seus próprios recursos

### API Key Permissions

Ao criar API key, você define as permissões:

```json
{
  "permissions": ["read", "write", "delete"]
}
```

**Permissões disponíveis:**
- `read` - Ler dados (GET)
- `write` - Criar e atualizar (POST, PUT)
- `delete` - Deletar recursos (DELETE)

---

## 🔒 Segurança

### Boas Práticas

1. **Nunca compartilhe API keys**
   - Trate como senhas
   - Não commite no Git
   - Use variáveis de ambiente

2. **Rotacione credenciais regularmente**
   - Troque senhas a cada 90 dias
   - Recrie API keys periodicamente

3. **Use HTTPS em produção**
   - Nunca envie tokens via HTTP
   - Configure SSL (veja [SSL.md](../deployment/SSL.md))

4. **Limite permissões**
   - Dê apenas permissões necessárias
   - Use role `viewer` quando possível

5. **Monitore acessos**
   - Verifique `last_used` das API keys
   - Revogue keys não utilizadas

### Armazenamento Seguro

**Variáveis de ambiente (.env):**
```bash
API_KEY=sk_live_abc123xyz789...
API_URL=https://seu-dominio.com/api
```

**Python:**
```python
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv('API_KEY')
```

**JavaScript:**
```javascript
// .env
const apiKey = process.env.API_KEY;
```

### Rate Limiting

Limites por minuto:

| Autenticação | Limite |
|--------------|--------|
| JWT Token | 100 req/min |
| API Key | 60 req/min |
| Sem autenticação | 10 req/min |

**Response quando excedido:**
```json
{
  "success": false,
  "error": "Rate limit exceeded",
  "retry_after": 60
}
```

---

## 🛠️ Exemplos Completos

### Exemplo 1: Login e Upload (JWT)

```python
import requests

# 1. Login
login_response = requests.post(
    "http://localhost:8082/api/auth/login",
    json={
        "username": "admin",
        "password": "admin123"
    }
)
token = login_response.json()["data"]["access_token"]

# 2. Upload de vídeo
headers = {"Authorization": f"Bearer {token}"}
files = {"file": open("video.mp4", "rb")}
data = {
    "title": "Meu Vídeo",
    "description": "Descrição #viral",
    "account_id": 1
}

upload_response = requests.post(
    "http://localhost:8082/api/videos/upload",
    headers=headers,
    files=files,
    data=data
)

print(upload_response.json())
```

### Exemplo 2: Upload com API Key

```python
import requests
import os

# API Key (de variável de ambiente)
headers = {"X-API-Key": os.getenv("TIKTOK_API_KEY")}

# Upload direto
files = {"file": open("video.mp4", "rb")}
data = {
    "title": "Vídeo Automático",
    "description": "Postagem via API #automation",
    "account_id": 1
}

response = requests.post(
    "http://localhost:8082/api/videos/upload",
    headers=headers,
    files=files,
    data=data
)

if response.json()["success"]:
    video_id = response.json()["data"]["id"]
    print(f"Vídeo criado: {video_id}")
```

### Exemplo 3: N8N Workflow

```javascript
// N8N HTTP Request Node
{
  "method": "POST",
  "url": "http://localhost:8082/api/videos/upload",
  "headers": {
    "X-API-Key": "{{$env.TIKTOK_API_KEY}}"
  },
  "bodyParameters": {
    "title": "{{$json.title}}",
    "description": "{{$json.description}}",
    "account_id": "{{$json.account_id}}"
  },
  "sendBinaryData": true,
  "binaryPropertyName": "video"
}
```

---

## ⚠️ Troubleshooting

### Token Expirado

**Erro:**
```json
{
  "success": false,
  "error": "Token expired"
}
```

**Solução:** Faça login novamente ou use `/api/auth/refresh`

### API Key Inválida

**Erro:**
```json
{
  "success": false,
  "error": "Invalid API key"
}
```

**Soluções:**
1. Verifique se copiou a chave completa
2. Confirme que a key não foi revogada
3. Verifique o header `X-API-Key`

### Permissão Negada

**Erro:**
```json
{
  "success": false,
  "error": "Insufficient permissions"
}
```

**Soluções:**
1. Verifique seu role (admin/user/viewer)
2. Verifique permissões da API key
3. Contate admin para elevar permissões

### Rate Limit

**Erro:**
```json
{
  "success": false,
  "error": "Rate limit exceeded"
}
```

**Soluções:**
1. Aguarde 60 segundos
2. Reduza frequência de requisições
3. Implemente exponential backoff

---

## 🔗 Links Relacionados

- **[API Completa](API.md)** - Todos os endpoints
- **[Integração N8N](N8N.md)** - Automação com n8n
- **[Troubleshooting](../deployment/TROUBLESHOOTING.md)** - Problemas comuns

---

## 📚 Recursos Adicionais

### Testar Autenticação

```bash
# Verificar se token é válido
curl http://localhost:8082/api/auth/me \
  -H "Authorization: Bearer <token>"

# Verificar se API key é válida
curl http://localhost:8082/api/health \
  -H "X-API-Key: <key>"
```

### Gerar API Key via CLI

```bash
# Login e pegar token
TOKEN=$(curl -X POST http://localhost:8082/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' \
  | jq -r '.data.access_token')

# Criar API key
curl -X POST http://localhost:8082/api/api-keys \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"CLI Key","permissions":["read","write"]}'
```

---

**Versão**: 2.0
**Última atualização**: Outubro 2025

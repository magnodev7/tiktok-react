# 📡 API REST - Documentação Completa

API REST completa para integração com o TikTok Scheduler.

## 🌐 Base URL

```
http://seu-ip:8082/api
https://seu-dominio.com/api
```

## 🔑 Autenticação

A API usa dois métodos de autenticação:

### 1. JWT Token (Interface Web)
```http
Authorization: Bearer <token>
```

### 2. API Key (Integrações)
```http
X-API-Key: <sua-api-key>
```

Veja detalhes em: [Documentação de Autenticação](AUTH.md)

## 📚 Endpoints

### Autenticação

#### POST `/auth/login`
Login de usuário

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
    "user": {
      "id": 1,
      "username": "admin",
      "email": "admin@example.com",
      "role": "admin"
    }
  }
}
```

#### POST `/auth/register`
Registrar novo usuário (apenas admins)

**Request:**
```json
{
  "username": "novo_usuario",
  "email": "usuario@example.com",
  "password": "senha123",
  "role": "user"
}
```

#### GET `/auth/me`
Obter dados do usuário atual

**Response:**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "username": "admin",
    "email": "admin@example.com",
    "role": "admin",
    "created_at": "2025-01-15T10:30:00"
  }
}
```

---

### Contas TikTok

#### GET `/accounts`
Listar todas as contas

**Query Parameters:**
- `status` (opcional): `active`, `inactive`, `error`
- `page` (opcional): Número da página (default: 1)
- `limit` (opcional): Itens por página (default: 50)

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "name": "Conta Principal",
      "username": "@meucanal",
      "status": "active",
      "total_videos": 150,
      "total_posted": 120,
      "last_post": "2025-01-20T18:00:00",
      "created_at": "2025-01-01T10:00:00"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 50,
    "total": 5,
    "pages": 1
  }
}
```

#### POST `/accounts`
Criar nova conta

**Request:**
```json
{
  "name": "Nova Conta",
  "username": "@novocanal",
  "status": "active"
}
```

#### GET `/accounts/{id}`
Obter detalhes de uma conta

#### PUT `/accounts/{id}`
Atualizar conta

#### DELETE `/accounts/{id}`
Deletar conta

---

### Vídeos

#### GET `/videos`
Listar vídeos

**Query Parameters:**
- `status`: `pending`, `scheduled`, `posted`, `error`
- `account_id`: Filtrar por conta
- `start_date`: Data inicial (ISO 8601)
- `end_date`: Data final (ISO 8601)
- `page`: Número da página
- `limit`: Itens por página

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "title": "Meu Vídeo",
      "description": "Descrição do vídeo #viral #fyp",
      "filename": "video_001.mp4",
      "account_id": 1,
      "account_name": "Conta Principal",
      "scheduled_time": "2025-01-21T18:00:00",
      "status": "scheduled",
      "created_at": "2025-01-20T10:00:00"
    }
  ]
}
```

#### POST `/videos/upload`
Fazer upload de vídeo

**Request:** `multipart/form-data`
```
file: <arquivo-video.mp4>
title: "Título do Vídeo"
description: "Descrição com #hashtags"
account_id: 1
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": 123,
    "filename": "video_123.mp4",
    "size": 15728640,
    "duration": 60,
    "status": "pending"
  }
}
```

#### GET `/videos/{id}`
Obter detalhes de um vídeo

#### PUT `/videos/{id}`
Atualizar vídeo

#### DELETE `/videos/{id}`
Deletar vídeo

#### POST `/videos/{id}/schedule`
Agendar vídeo

**Request:**
```json
{
  "scheduled_time": "2025-01-21T18:00:00"
}
```

#### POST `/videos/{id}/post-now`
Postar vídeo imediatamente

---

### Agendamento

#### GET `/schedules`
Listar agendamentos

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "video_id": 123,
      "video_title": "Meu Vídeo",
      "account_id": 1,
      "account_name": "Conta Principal",
      "scheduled_time": "2025-01-21T18:00:00",
      "status": "scheduled",
      "attempts": 0,
      "last_error": null
    }
  ]
}
```

#### POST `/schedules/bulk`
Agendar múltiplos vídeos

**Request:**
```json
{
  "video_ids": [1, 2, 3, 4, 5],
  "start_date": "2025-01-21",
  "end_date": "2025-01-25",
  "times": ["09:00", "12:00", "18:00", "21:00"],
  "distribution": "sequential"
}
```

#### DELETE `/schedules/{id}`
Cancelar agendamento

---

### Planner

#### POST `/planner/auto-schedule`
Usar planner inteligente

**Request:**
```json
{
  "video_ids": [1, 2, 3, 4, 5],
  "start_date": "2025-01-21",
  "end_date": "2025-01-27",
  "frequency": "daily",
  "posts_per_day": 3,
  "preferred_times": ["09:00", "12:00", "18:00", "21:00"],
  "avoid_weekends": false
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "scheduled": 15,
    "distribution": [
      {
        "date": "2025-01-21",
        "videos": [
          {
            "video_id": 1,
            "time": "09:00"
          }
        ]
      }
    ]
  }
}
```

---

### Analytics

#### GET `/analytics/overview`
Visão geral de estatísticas

**Query Parameters:**
- `start_date`: Data inicial
- `end_date`: Data final
- `account_id`: Filtrar por conta

**Response:**
```json
{
  "success": true,
  "data": {
    "total_videos": 150,
    "total_posted": 120,
    "total_scheduled": 25,
    "total_pending": 5,
    "success_rate": 96.0,
    "posts_by_day": [
      {"date": "2025-01-20", "count": 3},
      {"date": "2025-01-21", "count": 4}
    ],
    "posts_by_account": [
      {"account": "Conta Principal", "count": 80},
      {"account": "Conta 2", "count": 40}
    ]
  }
}
```

#### GET `/analytics/performance`
Performance de postagens

Veja detalhes em: [Analytics](ANALYTICS.md)

---

### API Keys

#### GET `/api-keys`
Listar API keys do usuário

#### POST `/api-keys`
Criar nova API key

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
    "key": "sk_live_abc123xyz789...",
    "permissions": ["read", "write"],
    "created_at": "2025-01-20T10:00:00"
  }
}
```

⚠️ **Importante**: A chave só é exibida uma vez na criação!

#### DELETE `/api-keys/{id}`
Revogar API key

---

### Health Check

#### GET `/health`
Verificar saúde da API

**Response:**
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "uptime": 86400,
  "database": "connected",
  "scheduler": "running"
}
```

---

## 🔧 Códigos de Status HTTP

| Código | Significado |
|--------|-------------|
| 200 | Sucesso |
| 201 | Criado com sucesso |
| 400 | Requisição inválida |
| 401 | Não autenticado |
| 403 | Sem permissão |
| 404 | Não encontrado |
| 409 | Conflito (duplicado) |
| 422 | Validação falhou |
| 500 | Erro interno do servidor |

---

## 📝 Formato de Resposta

Todas as respostas seguem o mesmo padrão:

### Sucesso
```json
{
  "success": true,
  "data": { /* dados */ },
  "message": "Operação realizada com sucesso"
}
```

### Erro
```json
{
  "success": false,
  "error": "Descrição do erro",
  "details": { /* detalhes opcionais */ }
}
```

---

## 🚀 Exemplos de Uso

### cURL

```bash
# Login
curl -X POST http://localhost:8082/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'

# Listar vídeos (com token)
curl http://localhost:8082/api/videos \
  -H "Authorization: Bearer <token>"

# Upload de vídeo
curl -X POST http://localhost:8082/api/videos/upload \
  -H "Authorization: Bearer <token>" \
  -F "file=@video.mp4" \
  -F "title=Meu Vídeo" \
  -F "description=Descrição #viral" \
  -F "account_id=1"
```

### Python

```python
import requests

# Login
response = requests.post(
    "http://localhost:8082/api/auth/login",
    json={"username": "admin", "password": "admin123"}
)
token = response.json()["data"]["access_token"]

# Listar vídeos
headers = {"Authorization": f"Bearer {token}"}
videos = requests.get(
    "http://localhost:8082/api/videos",
    headers=headers
).json()

# Upload de vídeo
files = {"file": open("video.mp4", "rb")}
data = {
    "title": "Meu Vídeo",
    "description": "Descrição #viral",
    "account_id": 1
}
response = requests.post(
    "http://localhost:8082/api/videos/upload",
    headers=headers,
    files=files,
    data=data
)
```

### JavaScript (Axios)

```javascript
import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8082/api'
});

// Login
const { data } = await api.post('/auth/login', {
  username: 'admin',
  password: 'admin123'
});

// Configurar token
api.defaults.headers.common['Authorization'] = `Bearer ${data.data.access_token}`;

// Listar vídeos
const videos = await api.get('/videos');

// Upload de vídeo
const formData = new FormData();
formData.append('file', videoFile);
formData.append('title', 'Meu Vídeo');
formData.append('description', 'Descrição #viral');
formData.append('account_id', '1');

await api.post('/videos/upload', formData, {
  headers: { 'Content-Type': 'multipart/form-data' }
});
```

---

## 📚 Documentação Interativa

Acesse a documentação interativa Swagger:

```
http://seu-ip:8082/docs
```

Ou Redoc:

```
http://seu-ip:8082/redoc
```

---

## 🔗 Links Relacionados

- **[Autenticação](AUTH.md)** - Detalhes de autenticação e API keys
- **[Integração N8N](N8N.md)** - Como integrar com n8n.io
- **[Analytics](ANALYTICS.md)** - Métricas e estatísticas
- **[Troubleshooting](../deployment/TROUBLESHOOTING.md)** - Problemas comuns

---

## 💡 Dicas

1. **Rate Limiting**: A API limita a 100 requisições por minuto por usuário
2. **Paginação**: Use `page` e `limit` para grandes conjuntos de dados
3. **Timezone**: Todas as datas estão em UTC (ISO 8601)
4. **Uploads**: Tamanho máximo de arquivo: 500MB
5. **Webhooks**: Em breve! Notificações de eventos via webhook

---

**Versão da API**: 2.0
**Última atualização**: Outubro 2025

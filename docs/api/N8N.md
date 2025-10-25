# 🔄 Integração N8N - Automação Completa

Integre o TikTok Scheduler com n8n.io para automação avançada de workflows.

## 🎯 O que é N8N?

[n8n](https://n8n.io) é uma ferramenta de automação de workflows open-source que permite conectar diferentes serviços e APIs sem código.

**Casos de uso:**
- 📥 Upload automático de vídeos do Google Drive/Dropbox
- 📊 Sincronizar com planilhas Google Sheets
- 📧 Notificações por email/Slack quando vídeos são postados
- 🔄 Integração com CMS (WordPress, Contentful)
- 📅 Agendamento inteligente baseado em analytics

---

## 🚀 Setup Inicial

### 1. Instalar N8N

```bash
# Via npm (recomendado)
npm install -g n8n

# Ou via Docker
docker run -it --rm \
  --name n8n \
  -p 5678:5678 \
  -v ~/.n8n:/home/node/.n8n \
  n8nio/n8n
```

### 2. Criar API Key

1. Acesse o TikTok Scheduler
2. Vá em **Configurações** > **API Keys**
3. Clique em **+ Nova API Key**
4. Configure:
   - **Nome**: "N8N Integration"
   - **Permissões**: `read`, `write`
5. Copie a chave gerada (só aparece uma vez!)

### 3. Configurar Credenciais no N8N

1. Abra N8N: `http://localhost:5678`
2. Vá em **Settings** > **Credentials**
3. Clique em **Add Credential**
4. Selecione **Header Auth**
5. Configure:
   - **Name**: `TikTok Scheduler API`
   - **Credential Data**:
     - Name: `X-API-Key`
     - Value: `sua-api-key-aqui`

---

## 📋 Workflows Prontos

### Workflow 1: Upload Automático do Google Drive

**Trigger:** Novo arquivo no Google Drive
**Ação:** Upload para TikTok Scheduler

```json
{
  "nodes": [
    {
      "name": "Google Drive Trigger",
      "type": "n8n-nodes-base.googleDriveTrigger",
      "parameters": {
        "folderId": "sua-pasta-id",
        "event": "fileCreated"
      }
    },
    {
      "name": "TikTok Upload",
      "type": "n8n-nodes-base.httpRequest",
      "parameters": {
        "method": "POST",
        "url": "http://seu-servidor:8082/api/videos/upload",
        "authentication": "predefinedCredentialType",
        "nodeCredentialType": "headerAuth",
        "sendBinaryData": true,
        "binaryPropertyName": "data",
        "bodyParameters": {
          "parameters": [
            {
              "name": "title",
              "value": "={{$json.name}}"
            },
            {
              "name": "description",
              "value": "Upload automático #tiktok #viral"
            },
            {
              "name": "account_id",
              "value": "1"
            }
          ]
        }
      }
    },
    {
      "name": "Notificar Slack",
      "type": "n8n-nodes-base.slack",
      "parameters": {
        "channel": "#tiktok-posts",
        "text": "=Vídeo {{$json.title}} enviado com sucesso!"
      }
    }
  ]
}
```

### Workflow 2: Sincronizar com Google Sheets

**Trigger:** Nova linha na planilha
**Ação:** Upload e agendamento automático

```json
{
  "nodes": [
    {
      "name": "Google Sheets Trigger",
      "type": "n8n-nodes-base.googleSheetsTrigger",
      "parameters": {
        "sheetId": "sua-planilha-id",
        "event": "rowAdded"
      }
    },
    {
      "name": "Download Video",
      "type": "n8n-nodes-base.httpRequest",
      "parameters": {
        "method": "GET",
        "url": "={{$json.video_url}}",
        "responseFormat": "file"
      }
    },
    {
      "name": "Upload to TikTok",
      "type": "n8n-nodes-base.httpRequest",
      "parameters": {
        "method": "POST",
        "url": "http://seu-servidor:8082/api/videos/upload",
        "authentication": "predefinedCredentialType",
        "nodeCredentialType": "headerAuth",
        "sendBinaryData": true,
        "bodyParameters": {
          "parameters": [
            {
              "name": "title",
              "value": "={{$json.title}}"
            },
            {
              "name": "description",
              "value": "={{$json.description}}"
            },
            {
              "name": "account_id",
              "value": "={{$json.account_id}}"
            }
          ]
        }
      }
    },
    {
      "name": "Schedule Video",
      "type": "n8n-nodes-base.httpRequest",
      "parameters": {
        "method": "POST",
        "url": "=http://seu-servidor:8082/api/videos/{{$json.data.id}}/schedule",
        "authentication": "predefinedCredentialType",
        "nodeCredentialType": "headerAuth",
        "bodyParameters": {
          "parameters": [
            {
              "name": "scheduled_time",
              "value": "={{$json.scheduled_date}}"
            }
          ]
        }
      }
    }
  ]
}
```

### Workflow 3: Monitoramento de Posts

**Trigger:** Webhook quando vídeo é postado
**Ação:** Atualizar planilha e notificar

```json
{
  "nodes": [
    {
      "name": "Webhook",
      "type": "n8n-nodes-base.webhook",
      "parameters": {
        "path": "tiktok-posted",
        "method": "POST"
      }
    },
    {
      "name": "Update Google Sheets",
      "type": "n8n-nodes-base.googleSheets",
      "parameters": {
        "operation": "append",
        "sheetId": "sua-planilha-id",
        "range": "Posts!A:E",
        "data": {
          "values": [
            [
              "={{$json.video_title}}",
              "={{$json.account_name}}",
              "={{$json.posted_at}}",
              "success",
              "={{$json.url}}"
            ]
          ]
        }
      }
    },
    {
      "name": "Send Email",
      "type": "n8n-nodes-base.emailSend",
      "parameters": {
        "to": "seu@email.com",
        "subject": "=Vídeo Postado: {{$json.video_title}}",
        "text": "=O vídeo {{$json.video_title}} foi postado com sucesso na conta {{$json.account_name}} às {{$json.posted_at}}"
      }
    }
  ]
}
```

---

## 🔧 Exemplos de Nodes HTTP Request

### Upload de Vídeo

```javascript
// Node: HTTP Request
{
  "method": "POST",
  "url": "http://seu-servidor:8082/api/videos/upload",
  "authentication": "predefinedCredentialType",
  "nodeCredentialType": "headerAuth",
  "sendBinaryData": true,
  "binaryPropertyName": "data",
  "bodyParameters": {
    "parameters": [
      {"name": "title", "value": "={{$json.title}}"},
      {"name": "description", "value": "={{$json.description}}"},
      {"name": "account_id", "value": "1"}
    ]
  }
}
```

### Listar Vídeos

```javascript
{
  "method": "GET",
  "url": "http://seu-servidor:8082/api/videos",
  "authentication": "predefinedCredentialType",
  "nodeCredentialType": "headerAuth",
  "qs": {
    "parameters": [
      {"name": "status", "value": "scheduled"},
      {"name": "limit", "value": "50"}
    ]
  }
}
```

### Agendar Vídeo

```javascript
{
  "method": "POST",
  "url": "=http://seu-servidor:8082/api/videos/{{$json.video_id}}/schedule",
  "authentication": "predefinedCredentialType",
  "nodeCredentialType": "headerAuth",
  "bodyParameters": {
    "parameters": [
      {
        "name": "scheduled_time",
        "value": "2025-01-21T18:00:00"
      }
    ]
  }
}
```

### Usar Planner Inteligente

```javascript
{
  "method": "POST",
  "url": "http://seu-servidor:8082/api/planner/auto-schedule",
  "authentication": "predefinedCredentialType",
  "nodeCredentialType": "headerAuth",
  "bodyParameters": {
    "parameters": [
      {"name": "video_ids", "value": "={{$json.video_ids}}"},
      {"name": "start_date", "value": "2025-01-21"},
      {"name": "end_date", "value": "2025-01-27"},
      {"name": "posts_per_day", "value": "3"},
      {"name": "preferred_times", "value": ["09:00", "12:00", "18:00"]}
    ]
  }
}
```

---

## 📊 Casos de Uso Avançados

### Caso 1: Pipeline de Conteúdo Completo

1. **Google Sheets** → Lista de vídeos para criar
2. **Google Drive** → Download dos vídeos
3. **OpenAI** → Gerar descrições automáticas
4. **TikTok API** → Upload dos vídeos
5. **Planner** → Distribuir automaticamente
6. **Slack** → Notificar equipe

### Caso 2: Sincronização Bidirecional

1. **TikTok API** → Obter vídeos postados
2. **Google Sheets** → Atualizar status
3. **Airtable** → Sincronizar base de dados
4. **Email** → Relatório diário

### Caso 3: Repostagem Inteligente

1. **TikTok API** → Identificar vídeos com melhor performance
2. **Filtro** → Selecionar vídeos com >10k views
3. **Scheduler** → Reagendar para melhor horário
4. **Analytics** → Registrar performance

---

## 🎛️ Variáveis de Ambiente

Configure no N8N para uso em workflows:

```bash
# ~/.n8n/.env
TIKTOK_API_URL=http://seu-servidor:8082/api
TIKTOK_API_KEY=sk_live_abc123xyz...
DEFAULT_ACCOUNT_ID=1
```

**Usar no workflow:**
```javascript
{{$env.TIKTOK_API_URL}}/videos
{{$env.TIKTOK_API_KEY}}
{{$env.DEFAULT_ACCOUNT_ID}}
```

---

## 🔍 Debugging

### Ver Response da API

Adicione node **Set** após HTTP Request:

```javascript
{
  "name": "Debug Response",
  "type": "n8n-nodes-base.set",
  "parameters": {
    "values": [
      {"name": "response", "value": "={{JSON.stringify($json)}}"}
    ]
  }
}
```

### Tratamento de Erros

Use node **IF** para verificar sucesso:

```javascript
{
  "name": "Check Success",
  "type": "n8n-nodes-base.if",
  "parameters": {
    "conditions": {
      "boolean": [
        {
          "value1": "={{$json.success}}",
          "value2": true
        }
      ]
    }
  }
}
```

### Retry em Caso de Falha

Configure retry automático no HTTP Request node:

```javascript
{
  "retryOnFail": true,
  "maxTries": 3,
  "waitBetweenTries": 5000
}
```

---

## 📚 Templates Prontos

### Template: Upload em Massa

1. **Google Sheets** - Lista de vídeos
2. **Loop** - Para cada linha
3. **Download** - Baixar vídeo
4. **Upload** - Enviar para TikTok
5. **Update Sheet** - Marcar como enviado

**Baixar:** [bulk-upload-template.json](templates/bulk-upload.json)

### Template: Agendamento Semanal

1. **Schedule Trigger** - Todo domingo 20:00
2. **Get Videos** - Buscar vídeos pending
3. **Planner** - Distribuir próximos 7 dias
4. **Email** - Enviar relatório

**Baixar:** [weekly-schedule-template.json](templates/weekly-schedule.json)

### Template: Monitoramento

1. **Cron** - A cada 1 hora
2. **Get Analytics** - Buscar estatísticas
3. **IF** - Verificar metas
4. **Slack** - Alertar se abaixo da meta

**Baixar:** [monitoring-template.json](templates/monitoring.json)

---

## 🔗 Webhooks

Configure webhooks para receber notificações de eventos:

### Setup Webhook no N8N

1. Crie workflow com node **Webhook**
2. Path: `tiktok-events`
3. Method: `POST`
4. Copie URL: `http://seu-n8n:5678/webhook/tiktok-events`

### Eventos Disponíveis

| Evento | Quando dispara |
|--------|----------------|
| `video.uploaded` | Vídeo enviado com sucesso |
| `video.scheduled` | Vídeo agendado |
| `video.posted` | Vídeo postado no TikTok |
| `video.error` | Erro ao postar |
| `account.added` | Nova conta adicionada |

### Payload do Webhook

```json
{
  "event": "video.posted",
  "timestamp": "2025-01-20T18:00:00Z",
  "data": {
    "video_id": 123,
    "video_title": "Meu Vídeo",
    "account_id": 1,
    "account_name": "Conta Principal",
    "posted_at": "2025-01-20T18:00:00Z",
    "url": "https://tiktok.com/@conta/video/123"
  }
}
```

---

## 💡 Dicas e Boas Práticas

1. **Use variáveis de ambiente** para API keys
2. **Implemente tratamento de erros** em todos os workflows
3. **Adicione logs** para debugging
4. **Teste com poucos vídeos** antes de automação em massa
5. **Configure retry** para requests que podem falhar
6. **Use webhooks** para eventos em tempo real
7. **Mantenha workflows simples** e modulares

---

## ⚠️ Troubleshooting

### Erro: "Invalid API Key"

- Verifique se copiou a chave completa
- Confirme que está usando header `X-API-Key`
- Teste a key manualmente com cURL

### Erro: "Connection refused"

- Verifique se a API está rodando
- Confirme o IP/domínio está correto
- Verifique firewall/portas abertas

### Upload falha

- Verifique tamanho do arquivo (max 500MB)
- Confirme formato do vídeo (MP4 recomendado)
- Verifique timeout do N8N (aumentar se necessário)

---

## 🔗 Links Relacionados

- **[API Completa](API.md)** - Todos os endpoints
- **[Autenticação](AUTH.md)** - Como usar API keys
- **[Analytics](ANALYTICS.md)** - Métricas e estatísticas
- **[N8N Documentation](https://docs.n8n.io)** - Docs oficiais do n8n

---

## 📖 Recursos Adicionais

- [N8N Community](https://community.n8n.io)
- [N8N Templates](https://n8n.io/workflows)
- [Video Tutorial](https://youtube.com/watch?v=...)

---

**Versão**: 2.0
**Última atualização**: Outubro 2025

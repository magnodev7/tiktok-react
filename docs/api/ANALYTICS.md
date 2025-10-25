# 📊 Analytics - Métricas e Estatísticas

Sistema completo de analytics para monitorar performance de postagens e contas.

## 🎯 Visão Geral

O módulo de Analytics oferece:
- 📈 Estatísticas de postagens
- 📊 Performance por conta
- 📅 Análise temporal
- 🎯 Taxa de sucesso
- ⏰ Melhores horários para postar

---

## 📡 Endpoints

### Overview Geral

**Endpoint:** `GET /api/analytics/overview`

**Query Parameters:**
```
start_date: 2025-01-01 (opcional)
end_date: 2025-01-31 (opcional)
account_id: 1 (opcional - filtrar por conta)
```

**Response:**
```json
{
  "success": true,
  "data": {
    "summary": {
      "total_videos": 150,
      "total_posted": 120,
      "total_scheduled": 25,
      "total_pending": 5,
      "total_error": 0,
      "success_rate": 96.0
    },
    "posts_by_status": {
      "posted": 120,
      "scheduled": 25,
      "pending": 5,
      "error": 0
    },
    "posts_by_day": [
      {"date": "2025-01-20", "count": 3, "success": 3, "error": 0},
      {"date": "2025-01-21", "count": 4, "success": 4, "error": 0}
    ],
    "posts_by_hour": [
      {"hour": 9, "count": 15, "avg_success": 95.0},
      {"hour": 12, "count": 20, "avg_success": 98.0},
      {"hour": 18, "count": 25, "avg_success": 96.0},
      {"hour": 21, "count": 18, "avg_success": 94.0}
    ],
    "posts_by_account": [
      {
        "account_id": 1,
        "account_name": "Conta Principal",
        "total": 80,
        "posted": 70,
        "scheduled": 8,
        "pending": 2,
        "success_rate": 97.2
      }
    ]
  }
}
```

### Performance por Conta

**Endpoint:** `GET /api/analytics/accounts/{id}`

**Response:**
```json
{
  "success": true,
  "data": {
    "account_id": 1,
    "account_name": "Conta Principal",
    "username": "@meucanal",
    "period": {
      "start": "2025-01-01",
      "end": "2025-01-31"
    },
    "totals": {
      "videos": 80,
      "posted": 70,
      "scheduled": 8,
      "pending": 2,
      "success_rate": 97.2
    },
    "timeline": [
      {
        "date": "2025-01-20",
        "posted": 3,
        "scheduled": 1,
        "success_rate": 100.0
      }
    ],
    "best_times": [
      {"hour": 18, "count": 15, "success_rate": 98.0},
      {"hour": 12, "count": 12, "success_rate": 95.0}
    ],
    "recent_posts": [
      {
        "video_id": 123,
        "title": "Meu Vídeo",
        "posted_at": "2025-01-20T18:00:00",
        "status": "posted"
      }
    ]
  }
}
```

### Análise Temporal

**Endpoint:** `GET /api/analytics/timeline`

**Query Parameters:**
```
start_date: 2025-01-01 (obrigatório)
end_date: 2025-01-31 (obrigatório)
granularity: day|week|month (default: day)
account_id: 1 (opcional)
```

**Response:**
```json
{
  "success": true,
  "data": {
    "period": {
      "start": "2025-01-01",
      "end": "2025-01-31",
      "granularity": "day"
    },
    "timeline": [
      {
        "date": "2025-01-20",
        "videos_uploaded": 5,
        "videos_posted": 3,
        "videos_scheduled": 2,
        "success_rate": 100.0,
        "errors": 0
      }
    ],
    "totals": {
      "videos_uploaded": 150,
      "videos_posted": 120,
      "videos_scheduled": 25,
      "avg_success_rate": 96.0
    }
  }
}
```

### Melhores Horários

**Endpoint:** `GET /api/analytics/best-times`

**Query Parameters:**
```
account_id: 1 (opcional)
days: 30 (default - últimos N dias)
```

**Response:**
```json
{
  "success": true,
  "data": {
    "analysis_period": {
      "start": "2025-01-01",
      "end": "2025-01-31",
      "days": 30
    },
    "best_hours": [
      {
        "hour": 18,
        "posts": 25,
        "success_rate": 98.0,
        "avg_engagement": "high",
        "recommendation": "optimal"
      },
      {
        "hour": 12,
        "posts": 20,
        "success_rate": 96.0,
        "avg_engagement": "high",
        "recommendation": "optimal"
      },
      {
        "hour": 9,
        "posts": 15,
        "success_rate": 94.0,
        "avg_engagement": "medium",
        "recommendation": "good"
      }
    ],
    "best_days": [
      {
        "day": "monday",
        "posts": 18,
        "success_rate": 97.0
      },
      {
        "day": "wednesday",
        "posts": 20,
        "success_rate": 96.5
      }
    ],
    "recommendations": [
      "Melhor horário: 18:00 (98% success rate)",
      "Evitar: 02:00-06:00 (low engagement)",
      "Dias com melhor performance: Segunda e Quarta"
    ]
  }
}
```

### Taxa de Sucesso

**Endpoint:** `GET /api/analytics/success-rate`

**Response:**
```json
{
  "success": true,
  "data": {
    "overall": {
      "total_attempts": 125,
      "successful": 120,
      "failed": 5,
      "success_rate": 96.0
    },
    "by_account": [
      {
        "account_id": 1,
        "account_name": "Conta Principal",
        "attempts": 80,
        "successful": 78,
        "failed": 2,
        "success_rate": 97.5
      }
    ],
    "by_hour": [
      {"hour": 18, "success_rate": 98.0},
      {"hour": 12, "success_rate": 96.0}
    ],
    "error_types": [
      {"type": "session_expired", "count": 3},
      {"type": "network_error", "count": 2}
    ]
  }
}
```

### Erros e Falhas

**Endpoint:** `GET /api/analytics/errors`

**Query Parameters:**
```
start_date: 2025-01-01 (opcional)
end_date: 2025-01-31 (opcional)
account_id: 1 (opcional)
```

**Response:**
```json
{
  "success": true,
  "data": {
    "summary": {
      "total_errors": 5,
      "resolved": 4,
      "pending": 1
    },
    "errors": [
      {
        "id": 1,
        "video_id": 123,
        "video_title": "Meu Vídeo",
        "account_id": 1,
        "error_type": "session_expired",
        "error_message": "TikTok session expired, please login again",
        "occurred_at": "2025-01-20T18:00:00",
        "resolved": true,
        "resolved_at": "2025-01-20T18:30:00"
      }
    ],
    "error_types": [
      {
        "type": "session_expired",
        "count": 3,
        "description": "Sessão do TikTok expirou"
      },
      {
        "type": "network_error",
        "count": 2,
        "description": "Erro de conexão"
      }
    ]
  }
}
```

---

## 📊 Dashboard Widgets

### Widget: Resumo Rápido

```javascript
// GET /api/analytics/overview?days=7
{
  "total_videos": 50,
  "total_posted": 42,
  "success_rate": 96.0,
  "pending": 5
}
```

### Widget: Gráfico de Postagens

```javascript
// GET /api/analytics/timeline?granularity=day&days=30
{
  "timeline": [
    {"date": "2025-01-20", "count": 3},
    {"date": "2025-01-21", "count": 4}
    // ...
  ]
}
```

### Widget: Performance por Conta

```javascript
// GET /api/analytics/overview
{
  "posts_by_account": [
    {
      "account_name": "Conta Principal",
      "total": 80,
      "success_rate": 97.2
    }
  ]
}
```

---

## 📈 Métricas Customizadas

### Criar Relatório Customizado

**Endpoint:** `POST /api/analytics/reports`

**Request:**
```json
{
  "name": "Relatório Semanal",
  "type": "weekly",
  "metrics": ["total_posts", "success_rate", "best_times"],
  "accounts": [1, 2],
  "email_recipients": ["admin@example.com"],
  "schedule": "every_monday_9am"
}
```

### Exportar Dados

**Endpoint:** `GET /api/analytics/export`

**Query Parameters:**
```
format: csv|json|xlsx (default: csv)
start_date: 2025-01-01
end_date: 2025-01-31
metrics: posts,success_rate,timeline
```

**Response:** Download do arquivo

---

## 📊 Gráficos Recomendados

### 1. Linha do Tempo (Line Chart)
```javascript
// Endpoint: /api/analytics/timeline
// X-axis: Data
// Y-axis: Número de posts
// Series: Posted, Scheduled, Errors
```

### 2. Pizza por Status (Pie Chart)
```javascript
// Endpoint: /api/analytics/overview
// Data: posts_by_status
// Labels: Posted, Scheduled, Pending, Error
```

### 3. Barras por Horário (Bar Chart)
```javascript
// Endpoint: /api/analytics/best-times
// X-axis: Hora do dia (0-23)
// Y-axis: Taxa de sucesso (%)
```

### 4. Heatmap Semanal
```javascript
// Endpoint: /api/analytics/timeline?granularity=day
// X-axis: Dia da semana
// Y-axis: Hora do dia
// Color: Número de posts
```

---

## 🎯 KPIs Importantes

### KPI 1: Taxa de Sucesso
```
success_rate = (videos_posted / total_attempts) * 100
Meta: > 95%
```

### KPI 2: Consistência
```
consistency = (dias_com_posts / total_dias) * 100
Meta: > 85%
```

### KPI 3: Tempo Médio de Agendamento
```
avg_schedule_time = sum(scheduled_time - created_time) / total_videos
Meta: < 24 horas
```

### KPI 4: Aproveitamento
```
utilization = (videos_posted / videos_uploaded) * 100
Meta: > 90%
```

---

## 🔍 Exemplos de Uso

### Python: Dashboard Simples

```python
import requests
from datetime import datetime, timedelta

api_key = "sua-api-key"
headers = {"X-API-Key": api_key}
base_url = "http://localhost:8082/api"

# Últimos 7 dias
end_date = datetime.now()
start_date = end_date - timedelta(days=7)

# Buscar overview
response = requests.get(
    f"{base_url}/analytics/overview",
    headers=headers,
    params={
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat()
    }
)

data = response.json()["data"]

print(f"📊 Resumo dos Últimos 7 Dias")
print(f"Total de vídeos: {data['summary']['total_videos']}")
print(f"Postados: {data['summary']['total_posted']}")
print(f"Taxa de sucesso: {data['summary']['success_rate']}%")
print(f"\n📅 Posts por dia:")
for day in data['posts_by_day']:
    print(f"  {day['date']}: {day['count']} posts")
```

### JavaScript: Gráfico com Chart.js

```javascript
import axios from 'axios';
import Chart from 'chart.js/auto';

const apiKey = 'sua-api-key';
const api = axios.create({
  baseURL: 'http://localhost:8082/api',
  headers: { 'X-API-Key': apiKey }
});

// Buscar dados
const { data } = await api.get('/analytics/timeline', {
  params: {
    start_date: '2025-01-01',
    end_date: '2025-01-31',
    granularity: 'day'
  }
});

// Criar gráfico
const ctx = document.getElementById('myChart');
new Chart(ctx, {
  type: 'line',
  data: {
    labels: data.data.timeline.map(d => d.date),
    datasets: [{
      label: 'Posts',
      data: data.data.timeline.map(d => d.videos_posted),
      borderColor: 'rgb(75, 192, 192)',
      tension: 0.1
    }]
  }
});
```

---

## 📧 Relatórios Automáticos

Configure relatórios para receber por email:

### Relatório Diário
- Resumo de postagens do dia
- Erros ocorridos
- Próximas postagens

### Relatório Semanal
- Performance semanal
- Comparação com semana anterior
- Melhores horários
- Recomendações

### Relatório Mensal
- Overview completo do mês
- Performance por conta
- Tendências
- Gráficos e visualizações

---

## 🔗 Integração com Google Data Studio

1. Configure API key
2. Use Google Sheets como intermediário
3. Script para buscar dados da API
4. Conecte Data Studio ao Sheets
5. Crie dashboards customizados

**Script exemplo:**
```javascript
function updateAnalytics() {
  const apiKey = 'sua-api-key';
  const url = 'http://seu-servidor:8082/api/analytics/overview';

  const response = UrlFetchApp.fetch(url, {
    headers: { 'X-API-Key': apiKey }
  });

  const data = JSON.parse(response.getContentText());
  const sheet = SpreadsheetApp.getActiveSheet();

  // Escrever dados na planilha
  sheet.getRange('A1').setValue('Total Videos');
  sheet.getRange('B1').setValue(data.data.summary.total_videos);
  // ...
}
```

---

## 💡 Dicas de Análise

1. **Monitore taxa de sucesso** - Se cair abaixo de 95%, investigue
2. **Identifique padrões** - Horários com melhor performance
3. **Compare contas** - Qual conta performa melhor?
4. **Evite horários ruins** - Dados mostram quando não postar
5. **Consistência é chave** - Postar regularmente > postar muito

---

## 🔗 Links Relacionados

- **[API Completa](API.md)** - Todos os endpoints
- **[Autenticação](AUTH.md)** - API keys
- **[N8N Integration](N8N.md)** - Automação de relatórios

---

**Versão**: 2.0
**Última atualização**: Outubro 2025

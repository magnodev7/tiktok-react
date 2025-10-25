# ⏰ Agendamento - Sistema Completo

Sistema avançado de agendamento de vídeos para o TikTok.

## 🎯 Visão Geral

O sistema de agendamento permite:
- ⏰ Agendar vídeos para datas/horários específicos
- 📅 Agendamento em massa
- 🔄 Reagendamento fácil
- 📊 Visualização de calendário
- ⚡ Postagem imediata
- 🔔 Notificações de status

---

## 📝 Como Agendar

### Opção 1: Interface Web

#### Agendar Vídeo Individual

1. Vá em **Vídeos** no menu lateral
2. Encontre o vídeo desejado
3. Clique no botão **⏰ Agendar**
4. Selecione:
   - **Data**: Dia da postagem
   - **Hora**: Horário exato (formato 24h)
5. Clique em **Confirmar**

#### Agendar Múltiplos Vídeos

1. Na lista de vídeos, marque os checkboxes dos vídeos desejados
2. Clique em **Ações em Massa** > **Agendar**
3. Escolha o método:
   - **Manual**: Definir data/hora para cada um
   - **Planner**: Distribuição automática inteligente

---

### Opção 2: API REST

#### Agendar Vídeo Individual

```bash
curl -X POST http://localhost:8082/api/videos/123/schedule \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "scheduled_time": "2025-01-21T18:00:00"
  }'
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": 123,
    "title": "Meu Vídeo",
    "scheduled_time": "2025-01-21T18:00:00",
    "status": "scheduled",
    "account": "Conta Principal"
  },
  "message": "Vídeo agendado com sucesso"
}
```

#### Agendamento em Massa

```bash
curl -X POST http://localhost:8082/api/schedules/bulk \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "video_ids": [1, 2, 3, 4, 5],
    "start_date": "2025-01-21",
    "end_date": "2025-01-25",
    "times": ["09:00", "12:00", "18:00", "21:00"],
    "distribution": "sequential"
  }'
```

---

## 📅 Formatos de Data/Hora

### ISO 8601 (Recomendado)
```
2025-01-21T18:00:00
2025-01-21T18:00:00Z (UTC)
2025-01-21T18:00:00-03:00 (com timezone)
```

### Formato Simplificado
```
2025-01-21 18:00
21/01/2025 18:00
```

### Timezone

Por padrão, todas as datas são interpretadas no timezone do servidor.

**Configurar timezone:**
```python
# beckend/.env
TIMEZONE=America/Sao_Paulo
```

**Timezones comuns:**
- `America/Sao_Paulo` - Brasília
- `America/New_York` - Nova York
- `Europe/London` - Londres
- `Asia/Tokyo` - Tóquio

---

## 🔄 Reagendamento

### Via Interface

1. Vá em **Vídeos Agendados**
2. Clique no vídeo
3. Clique em **Reagendar**
4. Selecione nova data/hora
5. Confirmar

### Via API

```bash
curl -X PUT http://localhost:8082/api/videos/123/schedule \
  -H "Authorization: Bearer <token>" \
  -d '{
    "scheduled_time": "2025-01-22T19:00:00"
  }'
```

---

## ⚡ Postagem Imediata

### Via Interface

1. Vá em **Vídeos**
2. Clique no vídeo
3. Clique em **Postar Agora**
4. Confirmar

O vídeo será postado nos próximos minutos.

### Via API

```bash
curl -X POST http://localhost:8082/api/videos/123/post-now \
  -H "Authorization: Bearer <token>"
```

---

## 📊 Visualizar Agendamentos

### Calendário (Interface Web)

1. Vá em **Calendário** no menu lateral
2. Visualize:
   - **Mês**: Vista mensal com todos os agendamentos
   - **Semana**: Vista semanal detalhada
   - **Dia**: Vista diária com horários
3. Clique em um agendamento para editar

### Lista de Agendamentos

**Endpoint:** `GET /api/schedules`

**Query Parameters:**
```
status: scheduled|posted|error (filtrar por status)
account_id: 1 (filtrar por conta)
start_date: 2025-01-01 (filtrar por período)
end_date: 2025-01-31
```

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
      "created_at": "2025-01-20T10:00:00"
    }
  ]
}
```

---

## 🎯 Distribuição de Horários

### Distribuição Sequencial

Vídeos são distribuídos em ordem, usando os horários fornecidos:

```
Vídeos: [1, 2, 3, 4, 5]
Horários: [09:00, 12:00, 18:00]
Período: 21-22 Jan

Resultado:
- 21 Jan 09:00 - Vídeo 1
- 21 Jan 12:00 - Vídeo 2
- 21 Jan 18:00 - Vídeo 3
- 22 Jan 09:00 - Vídeo 4
- 22 Jan 12:00 - Vídeo 5
```

### Distribuição Aleatória

Vídeos são distribuídos aleatoriamente nos horários:

```
Vídeos: [1, 2, 3, 4, 5]
Horários: [09:00, 12:00, 18:00, 21:00]
Período: 21-22 Jan

Resultado:
- 21 Jan 12:00 - Vídeo 3
- 21 Jan 18:00 - Vídeo 1
- 21 Jan 21:00 - Vídeo 5
- 22 Jan 09:00 - Vídeo 2
- 22 Jan 18:00 - Vídeo 4
```

### Distribuição Espaçada

Mantém intervalo mínimo entre posts:

```
Intervalo mínimo: 2 horas
Vídeos: [1, 2, 3, 4]

Resultado:
- 21 Jan 09:00 - Vídeo 1
- 21 Jan 11:00 - Vídeo 2
- 21 Jan 13:00 - Vídeo 3
- 21 Jan 15:00 - Vídeo 4
```

---

## 🔔 Notificações

### Tipos de Notificação

| Evento | Quando |
|--------|--------|
| **scheduled** | Vídeo agendado com sucesso |
| **posting** | 5 minutos antes de postar |
| **posted** | Vídeo postado com sucesso |
| **error** | Erro ao postar vídeo |
| **rescheduled** | Vídeo reagendado |
| **cancelled** | Agendamento cancelado |

### Configurar Notificações

**Via Interface:**
1. **Configurações** > **Notificações**
2. Escolha canais:
   - Email
   - Webhook
   - Push notification
3. Selecione eventos desejados

**Via API:**
```bash
curl -X POST http://localhost:8082/api/settings/notifications \
  -H "Authorization: Bearer <token>" \
  -d '{
    "email": true,
    "webhook_url": "https://seu-webhook.com",
    "events": ["posted", "error"]
  }'
```

---

## ⚙️ Configurações Avançadas

### Horários Padrão

Configure horários padrão para facilitar agendamentos:

```bash
# beckend/.env
DEFAULT_POST_TIMES=09:00,12:00,18:00,21:00
```

**Ou via Interface:**
1. **Configurações** > **Agendamento**
2. **Horários Padrão**
3. Adicionar horários (ex: 09:00, 12:00, 18:00, 21:00)
4. Salvar

### Intervalo Mínimo

Evita agendar vídeos muito próximos:

```bash
# beckend/.env
MIN_INTERVAL_HOURS=2
```

Se tentar agendar dois vídeos com menos de 2 horas de diferença, o sistema alertará.

### Limite Diário por Conta

Limitar quantos vídeos uma conta pode postar por dia:

```bash
# beckend/.env
MAX_POSTS_PER_DAY=5
```

### Janela de Tolerância

Caso o scheduler esteja offline no horário agendado:

```bash
# beckend/.env
SCHEDULE_TOLERANCE_MINUTES=30
```

Se o vídeo estava agendado para 18:00 e o scheduler volta online às 18:20, ele ainda será postado (dentro da janela de 30min).

---

## 🔧 Troubleshooting

### Vídeo não foi postado no horário

**Causas possíveis:**
1. Scheduler daemon não está rodando
2. Sessão do TikTok expirou
3. Vídeo foi deletado
4. Conta foi removida

**Soluções:**
```bash
# Verificar se scheduler está rodando
cd beckend
./manage.sh scheduler status

# Ver logs
./manage.sh scheduler logs

# Reiniciar scheduler
./manage.sh scheduler restart
```

### Agendamento sumiu

Verifique:
1. Se o vídeo já foi postado (checar histórico)
2. Se foi cancelado acidentalmente
3. Logs do scheduler:
   ```bash
   cd beckend
   tail -f logs/scheduler.log
   ```

### Erro "Scheduled time is in the past"

Você está tentando agendar para um horário que já passou.

**Solução:** Escolha data/hora no futuro.

### Erro "Account session expired"

A sessão do TikTok expirou.

**Solução:**
1. Vá em **Contas**
2. Clique na conta com erro
3. Clique em **Renovar Sessão**
4. Faça login no TikTok novamente

---

## 📊 Melhores Práticas

### 1. Horários Estratégicos

Baseado em dados de engajamento do TikTok:

| Horário | Engajamento | Recomendação |
|---------|-------------|--------------|
| 06:00-08:00 | Médio | Bom |
| 09:00-11:00 | Alto | Ótimo |
| 12:00-14:00 | Muito Alto | Ótimo |
| 15:00-17:00 | Médio | Bom |
| 18:00-20:00 | Muito Alto | **Melhor** |
| 21:00-23:00 | Alto | Ótimo |
| 00:00-05:00 | Baixo | Evitar |

### 2. Frequência Ideal

- **Mínimo**: 1 vídeo por dia
- **Ideal**: 2-3 vídeos por dia
- **Máximo**: 5 vídeos por dia

Mais de 5 por dia pode ser considerado spam.

### 3. Intervalo Entre Posts

- **Mínimo**: 2 horas
- **Recomendado**: 3-4 horas
- Evita saturação do seu público

### 4. Dias da Semana

| Dia | Performance |
|-----|------------|
| Segunda | Boa |
| Terça | Ótima |
| Quarta | Ótima |
| Quinta | Boa |
| Sexta | Média |
| Sábado | Média |
| Domingo | Baixa |

### 5. Planejamento Antecipado

- Agende com pelo menos 24h de antecedência
- Mantenha buffer de 10+ vídeos agendados
- Revise agendamentos semanalmente

---

## 🔗 Links Relacionados

- **[Planner Inteligente](PLANNER.md)** - Distribuição automática
- **[Contas](ACCOUNTS.md)** - Gerenciar contas TikTok
- **[Metadados](METADATA.md)** - Títulos e descrições
- **[API](../api/API.md)** - Endpoints de agendamento

---

## 💡 Dicas

1. Use o **Planner** para distribuir automaticamente
2. Agende para **horários de pico** (12h e 18h)
3. Mantenha **consistência** - poste diariamente
4. Deixe **buffer** de vídeos agendados
5. Monitore **analytics** para otimizar horários

---

**Versão**: 2.0
**Última atualização**: Outubro 2025

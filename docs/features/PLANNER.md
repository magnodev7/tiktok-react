# 📅 Planner Inteligente - Distribuição Automática

Sistema inteligente para distribuir vídeos automaticamente nos melhores horários.

## 🎯 O que é o Planner?

O Planner automatiza o agendamento de múltiplos vídeos, distribuindo-os de forma inteligente baseado em:
- 📊 Melhores horários (baseado em analytics)
- 📅 Período desejado
- ⏰ Frequência de postagens
- 🎯 Intervalo mínimo entre posts
- 📈 Performance histórica

---

## 🚀 Como Usar

### Via Interface Web

1. **Vídeos** > Selecione múltiplos vídeos (checkbox)
2. **Ações em Massa** > **Planner Inteligente**
3. Configure:
   - **Período**: Data inicial e final
   - **Frequência**: Vídeos por dia (1-5)
   - **Horários Preferidos**: Selecione horários
   - **Evitar finais de semana**: Sim/Não
4. **Aplicar**
5. Revisar distribuição
6. **Confirmar**

### Via API

```bash
curl -X POST http://localhost:8082/api/planner/auto-schedule \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "video_ids": [1, 2, 3, 4, 5],
    "start_date": "2025-01-21",
    "end_date": "2025-01-27",
    "frequency": "daily",
    "posts_per_day": 3,
    "preferred_times": ["09:00", "12:00", "18:00", "21:00"],
    "avoid_weekends": false
  }'
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
          {"video_id": 1, "time": "09:00", "title": "Vídeo 1"},
          {"video_id": 2, "time": "12:00", "title": "Vídeo 2"},
          {"video_id": 3, "time": "18:00", "title": "Vídeo 3"}
        ]
      },
      {
        "date": "2025-01-22",
        "videos": [
          {"video_id": 4, "time": "09:00", "title": "Vídeo 4"},
          {"video_id": 5, "time": "18:00", "title": "Vídeo 5"}
        ]
      }
    ]
  },
  "message": "15 vídeos agendados com sucesso"
}
```

---

## ⚙️ Opções de Configuração

### Frequência

| Opção | Descrição |
|-------|-----------|
| `daily` | Todos os dias no período |
| `weekdays` | Apenas segunda a sexta |
| `custom` | Dias específicos da semana |

### Posts por Dia

- **Mínimo**: 1 vídeo/dia
- **Recomendado**: 2-3 vídeos/dia
- **Máximo**: 5 vídeos/dia

### Horários Preferidos

Horários sugeridos baseados em analytics:
- `09:00` - Manhã (alto engajamento)
- `12:00` - Almoço (pico)
- `18:00` - Tarde (pico máximo) ⭐
- `21:00` - Noite (alto engajamento)

### Intervalo Mínimo

Tempo mínimo entre postagens da mesma conta:
- **Padrão**: 2 horas
- **Recomendado**: 3-4 horas
- **Seguro**: 6+ horas

---

## 🎯 Estratégias de Distribuição

### Estratégia 1: Consistente

Posts distribuídos uniformemente:

```json
{
  "strategy": "consistent",
  "posts_per_day": 3,
  "times": ["09:00", "12:00", "18:00"]
}
```

**Resultado:**
- Segunda: 09:00, 12:00, 18:00
- Terça: 09:00, 12:00, 18:00
- Quarta: 09:00, 12:00, 18:00

### Estratégia 2: Peak Times

Foca nos horários de pico:

```json
{
  "strategy": "peak_times",
  "posts_per_day": 2,
  "times": ["12:00", "18:00"]
}
```

**Resultado:**
- Todos os posts nos horários de maior engajamento

### Estratégia 3: Balanceada

Mix de horários para atingir diferentes públicos:

```json
{
  "strategy": "balanced",
  "posts_per_day": 4,
  "times": ["09:00", "12:00", "18:00", "21:00"]
}
```

---

## 📊 Exemplos Práticos

### Exemplo 1: Semana de Conteúdo

**Cenário:** 15 vídeos para 7 dias

```bash
curl -X POST http://localhost:8082/api/planner/auto-schedule \
  -H "Authorization: Bearer <token>" \
  -d '{
    "video_ids": [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15],
    "start_date": "2025-01-21",
    "end_date": "2025-01-27",
    "posts_per_day": 2,
    "preferred_times": ["12:00", "18:00"],
    "avoid_weekends": true
  }'
```

**Resultado:**
- Segunda a Sexta: 2 posts/dia (10 vídeos)
- Sobram 5 vídeos para próxima semana

### Exemplo 2: Campanha Intensiva

**Cenário:** 20 vídeos em 5 dias

```bash
curl -X POST http://localhost:8082/api/planner/auto-schedule \
  -H "Authorization: Bearer <token>" \
  -d '{
    "video_ids": [1,2,3,...,20],
    "start_date": "2025-01-21",
    "end_date": "2025-01-25",
    "posts_per_day": 4,
    "preferred_times": ["09:00", "12:00", "15:00", "18:00"]
  }'
```

**Resultado:**
- 4 vídeos por dia em horários espaçados

### Exemplo 3: Lançamento de Produto

**Cenário:** 3 vídeos no mesmo dia em horários estratégicos

```bash
curl -X POST http://localhost:8082/api/planner/auto-schedule \
  -H "Authorization: Bearer <token>" \
  -d '{
    "video_ids": [1, 2, 3],
    "start_date": "2025-01-21",
    "end_date": "2025-01-21",
    "posts_per_day": 3,
    "preferred_times": ["09:00", "14:00", "20:00"]
  }'
```

---

## 🔍 Análise Preditiva

O Planner analisa dados históricos para otimizar:

### Performance por Horário

```
09:00 - Taxa de sucesso: 94% | Engajamento: Médio
12:00 - Taxa de sucesso: 98% | Engajamento: Alto ⭐
15:00 - Taxa de sucesso: 92% | Engajamento: Médio
18:00 - Taxa de sucesso: 97% | Engajamento: Muito Alto ⭐⭐
21:00 - Taxa de sucesso: 95% | Engajamento: Alto
```

### Performance por Dia

```
Segunda: 95% sucesso | Alto engajamento
Terça: 97% sucesso | Muito Alto engajamento ⭐
Quarta: 96% sucesso | Alto engajamento
Quinta: 94% sucesso | Médio engajamento
Sexta: 90% sucesso | Médio engajamento
Sábado: 85% sucesso | Baixo engajamento
Domingo: 80% sucesso | Baixo engajamento
```

---

## 💡 Dicas e Boas Práticas

1. **Use Analytics**: Baseie horários em dados reais
2. **Teste A/B**: Experimente diferentes horários
3. **Consistência**: Mantenha padrão regular
4. **Buffer**: Sempre tenha vídeos agendados
5. **Revisar**: Verifique distribuição antes de confirmar
6. **Evitar Sobrecarga**: Max 5 vídeos/dia
7. **Intervalo**: Mínimo 2h entre posts

---

## 🔧 Configurações Avançadas

### Prioridade de Vídeos

Marque vídeos como prioridade para agendar primeiro:

```json
{
  "video_ids": [1, 2, 3],
  "priority": "high",
  "preferred_slot": "prime_time"
}
```

### Regras Customizadas

Crie regras personalizadas:

```json
{
  "rules": {
    "never_post_sunday": true,
    "max_per_hour": 1,
    "min_interval_hours": 3,
    "prime_time_only": false
  }
}
```

### Multi-Conta

Distribuir entre múltiplas contas:

```json
{
  "video_ids": [1,2,3,4,5,6],
  "accounts": [1, 2],
  "distribution": "alternating"
}
```

**Resultado:**
- Vídeo 1 → Conta 1
- Vídeo 2 → Conta 2
- Vídeo 3 → Conta 1
- Vídeo 4 → Conta 2

---

## ⚠️ Limitações

1. **Max vídeos por requisição**: 100
2. **Período máximo**: 90 dias
3. **Posts por dia**: 1-5 (limite TikTok)
4. **Intervalo mínimo**: 2 horas

---

## 🔗 Links Relacionados

- **[Agendamento](SCHEDULING.md)** - Agendamento manual
- **[Analytics](../api/ANALYTICS.md)** - Dados para otimização
- **[API](../api/API.md)** - Endpoints completos

---

**Versão**: 2.0
**Última atualização**: Outubro 2025

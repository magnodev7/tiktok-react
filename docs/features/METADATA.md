# 📝 Metadados - Títulos, Descrições e Hashtags

Guia completo para otimizar títulos, descrições e hashtags dos seus vídeos.

## 🎯 Visão Geral

Metadados bem configurados aumentam:
- 👁️ Visibilidade nos algoritmos
- 📈 Taxa de engajamento
- 🎯 Alcance do público-alvo
- 🔍 Descoberta orgânica

---

## 📝 Estrutura de Metadados

### Título

**Uso:** Identificação interna (não aparece no TikTok)

**Boas práticas:**
- Descritivo e claro
- Máximo 100 caracteres
- Útil para organização

**Exemplos:**
```
✅ "Tutorial Maquiagem - Look Noturno"
✅ "Review iPhone 15 - Parte 1"
✅ "Receita Bolo Chocolate - 5min"

❌ "Video1"
❌ "teste"
❌ "asdfgh"
```

### Descrição

**Uso:** Texto que aparece no vídeo do TikTok

**Limites:**
- **Mínimo**: 10 caracteres
- **Máximo**: 2200 caracteres
- **Recomendado**: 100-150 caracteres

**Estrutura recomendada:**
```
[Gancho/Call-to-action] + [Contexto] + [Hashtags]
```

**Exemplos:**

```
✅ "Aprenda essa técnica de maquiagem em 30 segundos!
Perfeita para o dia a dia ✨ #makeup #tutorial #beleza"

✅ "Você não vai acreditar nessa receita! Bolo de chocolate
pronto em 5 minutos 🍫 #receitas #doces #cozinha"

✅ "TOP 5 funções escondidas do iPhone que você NÃO conhecia!
Salva esse vídeo 📱 #iphone #dicas #tecnologia"
```

### Hashtags

**Limites:**
- **Mínimo**: 3 hashtags
- **Máximo**: 30 hashtags
- **Recomendado**: 5-8 hashtags relevantes

**Tipos de Hashtags:**

1. **Populares** (10M+ visualizações)
   - `#viral`, `#fyp`, `#foryou`, `#trending`
   - Uso: 1-2 por vídeo

2. **Nicho** (100K-10M visualizações)
   - `#makeup`, `#receitas`, `#dicas`, `#tutorial`
   - Uso: 2-3 por vídeo

3. **Específicas** (<100K visualizações)
   - `#makeupnatural`, `#receitasrapidas`, `#iphonedicas`
   - Uso: 2-3 por vídeo

---

## 🎨 Templates de Descrição

### Template 1: Tutorial

```
[Ação] em [tempo]!

[Benefício/Resultado]

[Call-to-action]

#hashtag1 #hashtag2 #hashtag3
```

**Exemplo:**
```
Aprenda essa técnica de maquiagem em 30 segundos!

Perfeito para o dia a dia e super fácil de fazer ✨

Salva esse vídeo e me marca quando testar!

#makeup #tutorial #beleza #dicas #makeuptutorial
```

### Template 2: Review/Opinião

```
[Opinião forte/gancho]

[3 pontos principais]

[Conclusão/Call-to-action]

#hashtags
```

**Exemplo:**
```
O iPhone 15 VALE A PENA? Minha opinião honesta!

✅ Câmera incrível
✅ Bateria dura o dia todo
❌ Preço muito alto

O que vocês acham? Comenta aí!

#iphone #review #tecnologia #apple #smartphone
```

### Template 3: Receita

```
[Nome da receita] em [tempo]! 🔥

Ingredientes:
[lista]

[Call-to-action]

#hashtags
```

**Exemplo:**
```
Bolo de Chocolate em 5 minutos! 🔥

Ingredientes:
🥚 2 ovos
🍫 3 colheres de chocolate
🥛 5 colheres de leite
🌾 4 colheres de farinha

Faz e me marca! 😋

#receitas #doces #cozinha #bolos #receitasrapidas
```

---

## 🔍 Pesquisa de Hashtags

### Via Interface

1. **Vídeos** > **Novo Vídeo**
2. Campo **Hashtags**
3. Digite `#` e palavra-chave
4. Sistema sugere hashtags populares
5. Selecione as mais relevantes

### Ferramentas Externas

- **TikTok Search**: Busque hashtags no próprio app
- **Hashtag Analytics**: [tiktok.com/hashtag/...](https://tiktok.com)
- **Google Trends**: Tendências de busca

### API de Sugestões

```bash
curl http://localhost:8082/api/hashtags/suggest?keyword=makeup \
  -H "Authorization: Bearer <token>"
```

**Response:**
```json
{
  "success": true,
  "data": {
    "keyword": "makeup",
    "suggestions": [
      {
        "hashtag": "#makeup",
        "views": "45.2B",
        "popularity": "very_high",
        "relevance": 100
      },
      {
        "hashtag": "#makeuptutorial",
        "views": "12.8B",
        "popularity": "high",
        "relevance": 95
      },
      {
        "hashtag": "#makeuplover",
        "views": "3.2B",
        "popularity": "medium",
        "relevance": 85
      }
    ]
  }
}
```

---

## ✏️ Edição de Metadados

### Edição Individual

**Via Interface:**
1. **Vídeos** > Selecione vídeo
2. **Editar**
3. Modifique título/descrição/hashtags
4. **Salvar**

**Via API:**
```bash
curl -X PUT http://localhost:8082/api/videos/123 \
  -H "Authorization: Bearer <token>" \
  -d '{
    "title": "Novo Título",
    "description": "Nova descrição #viral #fyp",
    "hashtags": ["viral", "fyp", "trending"]
  }'
```

### Edição em Massa

**Via Interface:**
1. Selecione múltiplos vídeos
2. **Ações em Massa** > **Editar Metadados**
3. Adicionar/Substituir hashtags
4. **Aplicar**

**Via API:**
```bash
curl -X POST http://localhost:8082/api/videos/bulk-update \
  -H "Authorization: Bearer <token>" \
  -d '{
    "video_ids": [1, 2, 3, 4, 5],
    "add_hashtags": ["viral", "trending"],
    "remove_hashtags": ["old"],
    "append_description": " Novo texto!"
  }'
```

---

## 🎯 Otimização para Algoritmo

### Palavras-Chave

**Incluir na descrição:**
- Palavras relevantes ao conteúdo
- Termos que seu público busca
- Sinônimos e variações

**Exemplo:**
```
"Aprenda MAQUIAGEM para iniciantes! Tutorial completo de
makeup básico para o dia a dia. Dicas de beleza fáceis!"
```

Palavras-chave: maquiagem, tutorial, makeup, beleza, dicas, iniciantes

### Call-to-Action

Incentive interação:
- "Salva esse vídeo!"
- "Me marca quando testar!"
- "Comenta sua opinião!"
- "Compartilha com quem precisa!"
- "Segue para mais dicas!"

### Emojis

Use com moderação:
- ✅ 2-5 emojis relevantes
- ❌ Excesso polui a descrição
- 🎯 Destaca pontos importantes

---

## 📊 Análise de Performance

### Melhores Hashtags

**Endpoint:** `GET /api/analytics/hashtags`

```json
{
  "success": true,
  "data": {
    "top_hashtags": [
      {
        "hashtag": "#viral",
        "uses": 45,
        "avg_success_rate": 96.5,
        "total_views": "1.2M"
      },
      {
        "hashtag": "#tutorial",
        "uses": 32,
        "avg_success_rate": 94.2,
        "total_views": "850K"
      }
    ]
  }
}
```

### A/B Testing

Teste diferentes abordagens:

**Teste 1: Descrição Curta vs Longa**
```
Grupo A: "Tutorial de maquiagem rápido! #makeup #tutorial"
Grupo B: "Aprenda essa técnica incrível de maquiagem em
apenas 30 segundos! Perfeito para o dia a dia..."
```

**Teste 2: Hashtags Populares vs Nicho**
```
Grupo A: #viral #fyp #foryou
Grupo B: #makeuptutorial #beautytips #makeuplover
```

---

## 💡 Boas Práticas

### ✅ Fazer

1. Descrição clara e atrativa
2. 5-8 hashtags relevantes
3. Mix de hashtags populares e nicho
4. Call-to-action para engajamento
5. Emojis com moderação
6. Palavras-chave naturais
7. Revisar antes de postar

### ❌ Evitar

1. Descrições genéricas
2. Excesso de hashtags (spam)
3. Hashtags irrelevantes
4. CAPS LOCK excessivo
5. Emojis demais
6. Keyword stuffing
7. Textos muito longos

---

## 🔧 Troubleshooting

### Hashtags não funcionam

**Causas:**
- Hashtags banidas
- Hashtags muito competitivas
- Hashtags irrelevantes

**Soluções:**
- Verificar se hashtag não é banida
- Usar mix de populares + nicho
- Garantir relevância com conteúdo

### Baixo alcance

**Otimizações:**
- Melhorar descrição (mais atrativa)
- Testar novos hashtags
- Adicionar call-to-action
- Usar palavras-chave relevantes

---

## 📚 Recursos

### Hashtags Banidas

Lista comum de hashtags banidas (evitar):
- `#adult`, `#sexy`, `#hot`
- `#drugs`, `#420`
- `#death`, `#suicide`
- Variações ofensivas

### Geradores de Hashtag

- [TikTok Hashtag Generator](https://www.example.com)
- [Hashtag Analytics](https://www.example.com)

---

## 🔗 Links Relacionados

- **[Agendamento](SCHEDULING.md)** - Agendar vídeos
- **[Planner](PLANNER.md)** - Distribuição automática
- **[Analytics](../api/ANALYTICS.md)** - Performance de hashtags

---

**Versão**: 2.0
**Última atualização**: Outubro 2025

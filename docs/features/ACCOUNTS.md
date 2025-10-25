# 👥 Gerenciamento de Contas TikTok

Sistema completo para gerenciar múltiplas contas TikTok.

## 🎯 Visão Geral

- ✅ Gerenciar múltiplas contas
- 🔐 Login automático e persistente
- 📊 Estatísticas por conta
- ⚡ Troca rápida entre contas
- 🔄 Renovação de sessão fácil

---

## ➕ Adicionar Conta

### Via Interface Web

1. Menu lateral > **Contas**
2. Botão **+ Nova Conta**
3. Preencher:
   - **Nome da Conta**: Nome amigável (ex: "Conta Principal")
   - **Username**: Seu @ do TikTok (ex: "@meucanal")
   - **Status**: Ativo
4. **Salvar**

### Via API

```bash
curl -X POST http://localhost:8082/api/accounts \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Conta Principal",
    "username": "@meucanal",
    "status": "active"
  }'
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "name": "Conta Principal",
    "username": "@meucanal",
    "status": "active",
    "total_videos": 0,
    "total_posted": 0,
    "created_at": "2025-01-20T10:00:00"
  }
}
```

---

## 🔐 Login na Conta

### Primeiro Login

Na primeira vez que você agendar um vídeo para uma conta:

1. O sistema abrirá navegador Chrome automatizado
2. Página de login do TikTok será exibida
3. Faça login normalmente:
   - Digite usuário/email/telefone
   - Digite senha
   - Resolva CAPTCHA se aparecer
   - Complete 2FA se configurado
4. Aguarde redirecionamento
5. **NÃO feche o navegador manualmente**
6. O sistema detecta login e salva sessão

O perfil é salvo em: `beckend/profiles/conta_{id}/`

### Renovar Sessão

Se a sessão expirar (geralmente após 30 dias):

1. **Contas** > Selecione a conta
2. Clique em **Renovar Sessão**
3. Faça login novamente
4. Sessão será renovada

---

## 📊 Visualizar Estatísticas

### Via Interface

1. **Contas** > Clique na conta
2. Veja:
   - Total de vídeos
   - Vídeos postados
   - Vídeos agendados
   - Última postagem
   - Taxa de sucesso

### Via API

```bash
curl http://localhost:8082/api/accounts/1 \
  -H "Authorization: Bearer <token>"
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "name": "Conta Principal",
    "username": "@meucanal",
    "status": "active",
    "statistics": {
      "total_videos": 150,
      "total_posted": 120,
      "total_scheduled": 25,
      "total_pending": 5,
      "success_rate": 96.0,
      "last_post": "2025-01-20T18:00:00"
    },
    "created_at": "2025-01-01T10:00:00"
  }
}
```

---

## ✏️ Editar Conta

### Via Interface

1. **Contas** > Clique na conta
2. **Editar**
3. Modificar:
   - Nome da conta
   - Username
   - Status (ativo/inativo)
4. **Salvar**

### Via API

```bash
curl -X PUT http://localhost:8082/api/accounts/1 \
  -H "Authorization: Bearer <token>" \
  -d '{
    "name": "Conta Atualizada",
    "status": "inactive"
  }'
```

---

## 🗑️ Deletar Conta

### Via Interface

1. **Contas** > Clique na conta
2. **Deletar**
3. Confirmar ação

⚠️ **Atenção**: Vídeos agendados para esta conta serão cancelados!

### Via API

```bash
curl -X DELETE http://localhost:8082/api/accounts/1 \
  -H "Authorization: Bearer <token>"
```

---

## 🔧 Status da Conta

| Status | Descrição |
|--------|-----------|
| **active** | Conta ativa, pode postar |
| **inactive** | Conta desativada, não posta |
| **error** | Erro de sessão, renovar login |
| **suspended** | Conta banida do TikTok |

---

## ⚠️ Troubleshooting

### Erro: "Session expired"

**Solução:**
1. Renovar sessão (veja acima)
2. Se persistir, deletar perfil:
   ```bash
   rm -rf beckend/profiles/conta_1/
   ```
3. Fazer login novamente

### Erro: "Account not found"

A conta foi removida ou TikTok alterou.

**Solução:** Verificar se @ está correto no TikTok.

### Navegador não abre

**Causas:**
- Chrome/Chromium não instalado
- Selenium webdriver com problema

**Solução:**
```bash
# Instalar Chrome
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo dpkg -i google-chrome-stable_current_amd64.deb

# Atualizar Selenium
cd beckend
source venv/bin/activate
pip install --upgrade selenium
```

---

## 💡 Boas Práticas

1. **Nome Descritivo**: Use nomes que identifiquem facilmente
2. **Renovar Sessões**: Renovar mensalmente antes de expirar
3. **Monitorar Status**: Verificar regularmente se contas estão ativas
4. **Backup de Perfis**: Fazer backup de `beckend/profiles/`
5. **Limite TikTok**: Respeitar limites de postagem (max 5/dia)

---

## 🔗 Links Relacionados

- **[Agendamento](SCHEDULING.md)** - Como agendar vídeos
- **[Planner](PLANNER.md)** - Distribuir vídeos automaticamente
- **[Quick Start](../setup/QUICKSTART.md)** - Primeiros passos

---

**Versão**: 2.0
**Última atualização**: Outubro 2025

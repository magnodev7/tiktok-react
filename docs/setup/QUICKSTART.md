# 🚀 Guia Rápido - Primeiros Passos

Configure e use o TikTok Scheduler em 5 minutos!

## 🎯 Acesso Inicial

Após deploy bem-sucedido, acesse:

```
http://seu-ip
ou
https://seu-dominio.com
```

### Credenciais Padrão

- **Usuário**: `admin`
- **Senha**: `admin123`

⚠️ **IMPORTANTE**: Altere a senha após primeiro login!

## 📝 Passo 1: Primeiro Login

1. Abra o navegador no endereço da aplicação
2. Faça login com as credenciais padrão
3. Você será redirecionado para o dashboard

### Alterar Senha

1. Clique no menu superior direito (ícone de usuário)
2. Selecione **Configurações** ou **Alterar Senha**
3. Digite a senha atual: `admin123`
4. Digite a nova senha (mínimo 8 caracteres)
5. Confirme a nova senha
6. Clique em **Salvar**

## 🎭 Passo 2: Adicionar Conta TikTok

### Via Interface Web

1. No menu lateral, clique em **Contas**
2. Clique no botão **+ Nova Conta**
3. Preencha as informações:
   - **Nome da Conta**: Nome amigável (ex: "Conta Principal")
   - **Username**: Seu @ do TikTok (ex: "@meucanal")
   - **Status**: Ativo
4. Clique em **Salvar**

### Login na Conta TikTok

A primeira vez que você tentar postar um vídeo, o sistema abrirá:

1. Uma janela do Chrome automatizada
2. Página de login do TikTok
3. Faça login normalmente:
   - Digite seu usuário/email
   - Digite sua senha
   - Resolva o CAPTCHA se necessário
4. O sistema salvará a sessão automaticamente

⚠️ **Importante**:
- Mantenha a janela aberta até o login completar
- Não feche o navegador manualmente
- O perfil será salvo em `beckend/profiles/`

## 📹 Passo 3: Fazer Primeiro Upload

### Preparar Vídeo

1. Vídeo deve ter:
   - Formato: MP4, MOV, AVI, MKV
   - Tamanho: Máximo 500MB
   - Duração: 15s a 10min (TikTok limita a 10min)
   - Resolução: Mínimo 720p (recomendado 1080p)

### Upload via Interface

1. No menu lateral, clique em **Vídeos**
2. Clique em **+ Novo Vídeo**
3. Preencha as informações:
   - **Título**: Título interno para identificação
   - **Descrição**: Descrição que aparecerá no TikTok (max 2200 caracteres)
   - **Hashtags**: Separadas por espaço (ex: `#dança #viral #fyp`)
   - **Conta**: Selecione a conta TikTok que postará
   - **Arquivo**: Clique e selecione seu vídeo
4. Clique em **Upload**

Aguarde o upload completar (barra de progresso).

## ⏰ Passo 4: Agendar Postagem

### Agendar Manualmente

1. Na lista de vídeos, encontre o vídeo enviado
2. Clique no botão **Agendar** ou **⏰**
3. Selecione:
   - **Data**: Dia da postagem
   - **Hora**: Horário exato (ex: 18:00)
4. Clique em **Confirmar**

### Usar Planner Inteligente

O Planner distribui vídeos automaticamente nos melhores horários:

1. Selecione múltiplos vídeos (checkbox)
2. Clique em **Planner Inteligente**
3. Configure:
   - **Período**: Data inicial e final
   - **Frequência**: Quantos vídeos por dia
   - **Horários**: Manhã, tarde, noite
4. Clique em **Aplicar**

Os vídeos serão distribuídos automaticamente!

## 👀 Passo 5: Monitorar Postagens

### Dashboard

No dashboard você verá:
- 📊 Estatísticas gerais
- 📅 Próximas postagens
- ✅ Postagens concluídas
- ❌ Postagens com erro

### Notificações

O sistema mostra notificações em tempo real:
- ✅ Vídeo postado com sucesso
- ⏰ Vídeo agendado
- ❌ Erro na postagem

### Logs

Para detalhes técnicos:

```bash
# Ver logs em tempo real
cd beckend
tail -f logs/scheduler.log

# Ver últimas postagens
tail -n 50 logs/scheduler.log | grep "Posting video"
```

## 🎛️ Passo 6: Configurações Avançadas

### Configurar Horários Padrão

1. Vá em **Configurações** > **Agendamento**
2. Configure:
   - **Horários padrão**: 09:00, 12:00, 18:00, 21:00
   - **Fuso horário**: America/Sao_Paulo
   - **Intervalo mínimo**: 2 horas entre posts
3. Salvar

### Configurar Notificações

1. Vá em **Configurações** > **Notificações**
2. Configure:
   - Email para alertas
   - Notificações de sucesso
   - Notificações de erro
3. Salvar

## 📊 Uso Diário

### Fluxo Recomendado

**Segunda a Sexta**:
1. 09:00 - Upload de vídeos do dia
2. 09:30 - Usar Planner para distribuir
3. Monitorar postagens ao longo do dia

**Sábado**:
1. Upload de vídeos da semana seguinte
2. Usar Planner para toda a semana

### Boas Práticas

1. **Upload antecipado**: Faça upload com 24h de antecedência
2. **Horários estratégicos**: 09h, 12h, 18h, 21h têm mais engajamento
3. **Hashtags**: Use 3-5 hashtags relevantes
4. **Descrições**: Seja criativo, use emojis
5. **Backup**: Mantenha cópia dos vídeos originais

## 🎯 Casos de Uso

### Caso 1: Agência de Marketing

```
- 5 contas TikTok de clientes diferentes
- 3 vídeos por dia por cliente
- Upload semanal de 105 vídeos (5 x 3 x 7)
- Usar Planner para distribuir automaticamente
```

### Caso 2: Criador de Conteúdo Solo

```
- 1 conta TikTok pessoal
- 2 vídeos por dia
- Horários: 12:00 e 20:00
- Upload antecipado aos domingos
```

### Caso 3: E-commerce

```
- 1 conta TikTok da loja
- 5 vídeos por semana (produtos)
- Horários comerciais: 10h, 14h, 18h
- Campanhas promocionais agendadas
```

## ⚠️ Problemas Comuns

### Vídeo não foi postado

1. Verifique logs:
   ```bash
   cd beckend
   tail -n 100 logs/scheduler.log
   ```

2. Causas comuns:
   - Sessão do TikTok expirou (fazer login novamente)
   - Vídeo não atende requisitos do TikTok
   - Conta banida/restrita
   - Sem conexão com internet

### Não consigo fazer login na conta TikTok

1. Verifique:
   - Credenciais corretas
   - Conta não está bloqueada
   - CAPTCHA resolvido corretamente

2. Solução:
   - Limpar perfil: `rm -rf beckend/profiles/conta_*`
   - Tentar login novamente

### Upload falha

1. Verificar:
   - Tamanho do arquivo (max 500MB)
   - Formato do vídeo (MP4 recomendado)
   - Espaço em disco disponível

2. Testar:
   ```bash
   # Ver espaço em disco
   df -h

   # Ver tamanho do arquivo
   ls -lh beckend/videos/
   ```

## 📚 Próximos Passos

1. **[Agendamento Avançado](../features/SCHEDULING.md)** - Recursos avançados de agendamento
2. **[Planner Inteligente](../features/PLANNER.md)** - Como usar o Planner
3. **[API](../api/API.md)** - Integrar com outras ferramentas
4. **[Integração N8N](../api/N8N.md)** - Automatizar com n8n.io

## 🆘 Precisa de Ajuda?

- **Logs**: `beckend/logs/`
- **Documentação**: `/docs`
- **Troubleshooting**: [TROUBLESHOOTING.md](../deployment/TROUBLESHOOTING.md)

---

**Dica**: Mantenha pelo menos 10 vídeos agendados para garantir postagens consistentes!

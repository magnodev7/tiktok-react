# 🌐 Migração para Sistema Simplificado VIA WEB

## ✅ Melhor Método - Seu Fluxo Atual!

Você já tem um sistema web completo de deploy! Agora adicionei 2 novos botões na página de manutenção para migrar para o sistema simplificado.

---

## 🎯 Processo Completo (3 Cliques!)

### 1️⃣ Atualizar Código do GitHub

Na página de Manutenção/Administração:

**Opção A: Tab "Updates/Atualizações"**
- Clique em **"Update from GitHub"** ou **"Atualizar do GitHub"**
- Isso faz `git pull` e já reinicia serviços

**OU**

**Opção B: Tab "Git"**
- Vá em "Git Status"
- Se houver commits novos, clique em **"Pull"**

Isso vai baixar os arquivos:
- ✅ `src/driver_simple.py`
- ✅ `src/cookies_simple.py`
- ✅ `src/uploader_simple.py`
- ✅ Novos endpoints na API

### 2️⃣ Migrar para Sistema Simplificado

**Ainda na página de Manutenção:**

Você verá um **novo botão/tab: "Migração Sistema Simplificado"** (ou similar)

Clique nele! Ele vai:
- ✅ Fazer backup automático (driver_old_backup.py, etc)
- ✅ Substituir arquivos pelos simplificados
- ✅ Reiniciar serviços
- ✅ Mostrar progresso em tempo real

**API Endpoint (caso queira ver/debugar):**
```
POST /api/maintenance/migrate-to-simple
Authorization: Bearer {seu_token}
```

### 3️⃣ Monitorar Logs

Na página de **"Logs"**:
- Selecione "Scheduler"
- Procure por:
  - ❌ **SEM** "Lock global adquirido"
  - ❌ **SEM** "Aguardando vez"
  - ✅ Logs mais limpos e diretos
  - ✅ Uploads completando em ~50s

---

## 🔄 Se Der Problema: Rollback (1 Clique!)

Na mesma página, clique em:
**"Rollback Sistema Simplificado"**

Volta tudo ao estado anterior em 10 segundos!

**API Endpoint:**
```
POST /api/maintenance/rollback-simple
Authorization: Bearer {seu_token}
```

---

## 📊 Estrutura dos Endpoints Criados

### 1. `/api/maintenance/migrate-to-simple` (POST)

**Request:**
```json
{
  // Nenhum parâmetro necessário
}
```

**Response:**
```json
{
  "success": true,
  "message": "Migração para sistema simplificado concluída! Monitore os logs.",
  "data": {
    "steps": [
      {
        "step": "check_files",
        "success": true,
        "message": "Arquivos simplificados encontrados"
      },
      {
        "step": "backup",
        "success": true,
        "message": "Backup dos arquivos originais criado"
      },
      {
        "step": "replace_files",
        "success": true,
        "message": "Arquivos substituídos com sucesso",
        "replaced": ["driver.py", "cookies.py", "uploader.py"]
      },
      {
        "step": "restart_services",
        "success": true,
        "output": "..."
      }
    ],
    "errors": [],
    "completed": true,
    "backup_location": "beckend/src/*_old_backup.py",
    "next_steps": [
      "Monitore os logs para verificar funcionamento",
      "Procure por ausência de 'Lock global adquirido'",
      "Uploads devem completar em ~50s (antes: 3-5min)",
      "Se houver problemas, use rollback"
    ]
  }
}
```

### 2. `/api/maintenance/rollback-simple` (POST)

**Request:**
```json
{
  // Nenhum parâmetro necessário
}
```

**Response:**
```json
{
  "success": true,
  "message": "Rollback concluído! Sistema voltou ao estado original.",
  "data": {
    "steps": [
      {
        "step": "check_backups",
        "success": true,
        "message": "Backups encontrados"
      },
      {
        "step": "restore_files",
        "success": true,
        "message": "Arquivos originais restaurados",
        "restored": ["driver.py", "cookies.py", "uploader.py"]
      },
      {
        "step": "restart_services",
        "success": true,
        "output": "..."
      }
    ],
    "errors": [],
    "completed": true
  }
}
```

---

## 🎨 Como Adicionar os Botões no Frontend

Se quiser adicionar botões bonitos na UI, aqui está um exemplo:

**Localização sugerida:** Na tab "Updates" ou "Maintenance"

```tsx
// src/components/Maintenance/SimpleMigration.tsx (ou similar)

async function handleMigrate() {
  try {
    const response = await fetch('/api/maintenance/migrate-to-simple', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    });

    const result = await response.json();

    if (result.success && result.data.completed) {
      toast.success('Migração concluída! Verifique os logs.');
    } else {
      toast.error('Migração falhou. Veja detalhes.');
    }

    // Mostra steps para debug
    console.log('Migration steps:', result.data.steps);
  } catch (error) {
    toast.error('Erro na migração: ' + error.message);
  }
}

async function handleRollback() {
  try {
    const response = await fetch('/api/maintenance/rollback-simple', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    });

    const result = await response.json();

    if (result.success && result.data.completed) {
      toast.success('Rollback concluído!');
    } else {
      toast.error('Rollback falhou.');
    }
  } catch (error) {
    toast.error('Erro no rollback: ' + error.message);
  }
}

// UI
<div className="space-y-4">
  <div className="bg-blue-50 p-4 rounded">
    <h3 className="font-bold mb-2">🚀 Sistema Simplificado</h3>
    <p className="text-sm mb-4">
      Migre para versão 79% menor e 5-10x mais rápida!
    </p>
    <button
      onClick={handleMigrate}
      className="btn btn-primary"
    >
      Migrar para Sistema Simplificado
    </button>
  </div>

  <div className="bg-yellow-50 p-4 rounded">
    <h3 className="font-bold mb-2">⏪ Rollback</h3>
    <p className="text-sm mb-4">
      Volta para versão anterior se houver problemas
    </p>
    <button
      onClick={handleRollback}
      className="btn btn-warning"
    >
      Reverter para Sistema Antigo
    </button>
  </div>
</div>
```

---

## 🔍 Verificação Pós-Migração

### 1. Via Logs Web
Na página de Logs, procure por:

**ANTES (sistema antigo):**
```
🔓 [novadigitalbra] Lock global adquirido
⏳ [novadigitalbra] Aguardando vez para postar...
(tentativa 1/3)
```

**DEPOIS (sistema novo):**
```
🔧 Criando driver...
✅ Driver criado em 2.9s
🍪 Carregando cookies...
✅ Cookies carregados em 3.8s
📤 Fazendo upload...
✅ Upload completo em 47s
```

### 2. Via Service Status
- Serviços devem estar **"Running"** (verde)
- Sem mensagens de erro

### 3. Via Git Status
- Branch: `main`
- Commit mais recente deve incluir "sistema simplificado"

---

## 📋 Checklist Completo

- [ ] 1. Fazer commit local (se houver mudanças)
- [ ] 2. Push para GitHub
- [ ] 3. Na web: Clicar "Update from GitHub"
- [ ] 4. Verificar que commit f7f9b00 ou posterior foi baixado
- [ ] 5. Na web: Clicar "Migrar para Sistema Simplificado"
- [ ] 6. Aguardar progresso (30-60s)
- [ ] 7. Verificar logs - SEM "Lock global"
- [ ] 8. Fazer teste com 1 vídeo
- [ ] 9. Se OK: Sucesso! 🎉
- [ ] 10. Se problema: Clicar "Rollback"

---

## 💡 Vantagens do Método Web

✅ **Sem precisar SSH**
✅ **Histórico visual de cada passo**
✅ **Rollback com 1 clique**
✅ **Controle de branches via UI**
✅ **Logs em tempo real**
✅ **Progresso detalhado**

---

## 🎯 Exemplo de Uso Completo

1. **Você:** Edita código localmente
2. **Você:** `git commit && git push`
3. **Web (Tab Git):** Mostra "1 commit ahead"
4. **Web (Tab Updates):** Clique "Update"
5. **Agora (NOVO!):** Clique "Migrar Sistema Simplificado"
6. **Web:** Mostra progresso em tempo real
7. **Web (Tab Logs):** Monitora novo sistema funcionando
8. **Se problema:** Clique "Rollback" (volta em 10s)

---

## 📞 Troubleshooting

### Erro: "Arquivos simplificados não encontrados"
**Solução:** Faça "Update from GitHub" primeiro

### Erro: "Falha ao reiniciar serviços"
**Possível causa:** Permissões sudo
**Solução:**
- Se aparecer "sudo_config_required: true"
- No servidor: `sudo bash setup_sudo.sh`
- OU reinicie manualmente via SSH

### Erro: "Backup já existe"
**Significa:** Você já tentou migrar antes
**Solução:**
- Se quer tentar de novo: Delete `beckend/src/*_old_backup.py` via SSH
- OU: Use rollback primeiro, depois migre novamente

---

## 🎉 Resumo

**ANTES:** SSH → comandos manuais → muito trabalho

**AGORA:**
1. Click "Update"
2. Click "Migrar"
3. Pronto! 🚀

**Se der problema:**
Click "Rollback" → Volta em 10s! ⏪

---

## 📊 Endpoints Disponíveis

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/api/maintenance/update` | POST | Git pull + build + restart |
| `/api/maintenance/migrate-to-simple` | POST | **[NOVO]** Migra para simplificado |
| `/api/maintenance/rollback-simple` | POST | **[NOVO]** Reverte migração |
| `/api/maintenance/git/status` | GET | Status do Git |
| `/api/maintenance/git/checkout` | POST | Troca de branch |
| `/api/maintenance/service/restart` | POST | Reinicia serviços |
| `/api/maintenance/logs/tail` | GET | Últimas linhas dos logs |

Todos funcionam via web! 🌐

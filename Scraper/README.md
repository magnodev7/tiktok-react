# TikTok User Info Scraper

> **Desenvolvido e modificado por Magno Dev**

Script Python para extrair informações públicas de perfis do TikTok com fallback automático e extração avançada de links sociais.

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![Status](https://img.shields.io/badge/status-active-success.svg)
![Author](https://img.shields.io/badge/author-Magno%20Dev-blue.svg)

---

## 🚀 Funcionalidades

- ✅ **Extração completa de dados de perfil**
  - ID do usuário, username, nickname
  - Seguidores, seguindo, curtidas, vídeos
  - Verificação, conta privada, região
  - Biografia e foto de perfil

- ✅ **Sistema de fallback inteligente**
  - Scraping HTML como método primário
  - API pública do TikTok como fallback
  - Funciona mesmo com perfis menos populares

- ✅ **Extração avançada de links sociais**
  - 5 métodos diferentes de detecção
  - Instagram, Twitter, YouTube, Snapchat, Telegram
  - Links da bio e bioLinks
  - Emails e links externos

- ✅ **Download automático**
  - Foto de perfil em alta qualidade
  - Salva como `<username>_profile_pic.jpg`

---

## 📋 Instalação

### Dependências

```bash
pip install requests beautifulsoup4 lxml
```

> `lxml` é opcional mas recomendado para melhor performance.

---

## 🎯 Uso

### Linha de Comando

```bash
# Por username
python TikTok.py novadigitalbra

# Por username com @
python TikTok.py @novadigitalbra

# Por User ID
python TikTok.py 6940015926272459782 --by_id
```

### Como Módulo Python

```python
from TikTok import get_user_info

# Extrair informações
info = get_user_info("novadigitalbra")

if info:
    print(f"Username: {info['unique_id']}")
    print(f"Seguidores: {info['followers']}")
    print(f"Links sociais: {info['social_links']}")
```

---

## 📊 Exemplo de Saída

```json
{
  "user_id": "6940015926272459782",
  "unique_id": "novadigitalbra",
  "nickname": "NOVA DIGITAL BR",
  "verified": "false",
  "privateAccount": "false",
  "region": "BR",
  "followers": "3542",
  "following": "1802",
  "likes": "17700",
  "videos": "737",
  "friendCount": "1771",
  "heart": "17700",
  "diggCount": "6440",
  "secUid": "MS4wLj...",
  "commentSetting": "0",
  "signature": "Bio do perfil...",
  "profile_pic": "https://p16-sign-va.tiktokcdn.com/.../avatar.jpeg",
  "social_links": [
    "Link: https://exemplo.com - https://exemplo.com",
    "Instagram: @perfil",
    "Email: contato@exemplo.com"
  ]
}
```

---

## 🔧 Integração com Backend

Veja a [documentação completa de integração](docs/INTEGRATION_GUIDE.md) para exemplos detalhados com Flask, FastAPI e outras frameworks.

### Exemplo Rápido - FastAPI

```python
from fastapi import FastAPI
from TikTok import get_user_info

app = FastAPI()

@app.get("/tiktok/user/{username}")
def get_tiktok_user(username: str):
    data = get_user_info(username)
    if not data:
        return {"error": "Profile not found"}, 404
    return data
```

---

## 🛠️ Modificações e Melhorias

Esta versão inclui melhorias significativas sobre o projeto original:

### Adicionado por Magno Dev:

1. **Sistema de Fallback API**
   - Função `fetch_user_info_via_api()` para perfis sem JSON no HTML
   - Normalização automática de dados
   - Suporte a bioLinks

2. **Extração Avançada de Links**
   - 5 métodos diferentes de detecção
   - Suporte a múltiplas redes sociais
   - Regex otimizados

3. **Melhor Tratamento de Erros**
   - Try/catch em pontos críticos
   - Fallback silencioso entre métodos
   - Mensagens de erro claras

4. **Download de Profile Pic**
   - Download automático da foto
   - Tratamento de erros de download
   - Nome de arquivo baseado no username

5. **Documentação Completa**
   - Guia de integração em português
   - Exemplos práticos
   - Referência de campos

---

## 📚 Documentação

- [Guia de Integração](docs/INTEGRATION_GUIDE.md) - Como integrar com backend
- Todas as funções têm docstrings explicativas

---

## ⚠️ Considerações

- **Dados públicos**: Extrai apenas informações públicas do TikTok
- **Rate Limiting**: Use cache para evitar bloqueios
- **Termos de Uso**: Respeite os termos do TikTok
- **Produção**: Implemente retry, timeout e logging apropriados

---

## 🔍 Campos Disponíveis

| Campo | Descrição |
|-------|-----------|
| `user_id` | ID numérico interno do TikTok |
| `unique_id` | Username público (@username) |
| `nickname` | Nome exibido no perfil |
| `verified` | Selo de verificação (true/false) |
| `privateAccount` | Conta privada (true/false) |
| `followers` | Quantidade de seguidores |
| `following` | Quantidade seguindo |
| `likes` | Total de curtidas nos vídeos |
| `videos` | Total de vídeos publicados |
| `friendCount` | Amigos mútuos |
| `signature` | Bio do perfil |
| `profile_pic` | URL da foto de perfil |
| `social_links` | Lista de links detectados |

---

## 👨‍💻 Desenvolvedor

**Magno Dev**

Script modificado e aprimorado com funcionalidades avançadas de scraping e integração.

Baseado no projeto original TikTok-User-Info-Scraper, com modificações substanciais para produção.

---

## 📝 Licença

MIT License - Copyright (c) 2025 Magno Dev

Veja [LICENSE](LICENSE) para mais detalhes.

---

## 🤝 Contribuindo

Contribuições são bem-vindas! Abra issues ou pull requests.

---

**Versão**: 2.0.0
**Última atualização**: Outubro 2025

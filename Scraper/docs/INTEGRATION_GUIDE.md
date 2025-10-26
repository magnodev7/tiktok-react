# Guia de Integração - TikTok User Info Scraper

> **Autor**: Magno Dev
> **Versão**: 2.0.0
> **Licença**: MIT

---

## Visão geral

O script `TikTok.py` consulta informações públicas de perfis do TikTok a partir de um identificador (username ou user ID). Ele combina duas estratégias:

1. **Scraping da página HTML pública** (`https://www.tiktok.com/@<username>`).
2. **Fallback via endpoint público** (`https://www.tiktok.com/api/user/detail/`), utilizado quando o HTML não contém mais o JSON com os dados do perfil.

Esse comportamento garante maior estabilidade para perfis menos populares, nos quais o TikTok raramente entrega o JSON embutido na página.

## Estrutura principal

```text
TikTok.py
 ├── fetch_user_info_via_api(...)
 ├── get_user_info(...)
 └── CLI (argparse)
```

- `fetch_user_info_via_api`: função de suporte que chama o endpoint JSON do TikTok e normaliza os campos mais importantes.
- `get_user_info`: função “pública” que orquestra o fluxo (HTML → fallback API) e imprime o resultado.
- Bloco final `if __name__ == "__main__"` expõe o script como ferramental de linha de comando.

## Dependências

Instale e mantenha atualizadas as seguintes dependências:

```bash
pip install requests beautifulsoup4 lxml
```

> `lxml` é opcional (o script faz fallback automático para `html.parser`), mas melhora a performance.

## Fluxo de execução detalhado

1. **Normalização do identificador**:
   - Remove `@` caso presente.
   - Caso `--by_id` seja usado, o identificador é tratado diretamente como user ID (a URL permanece a mesma porque o TikTok resolve IDs na rota `@<id>`).

2. **Requisição HTML**:
   - `requests.get` com `User-Agent` configurado (necessário para evitar bloqueios).
   - Resposta `200` → tenta parsear com BeautifulSoup.

3. **Extração via regex**:
   - Diversos padrões regulares para capturar campos em JSON embutido.
   - Caso algum campo crítico (`user_id`, `unique_id`) não apareça, o script aciona o fallback de API.

4. **Fallback API**:
   - `fetch_user_info_via_api` recebe o identificador e os headers.
   - A call é feita para `https://www.tiktok.com/api/user/detail/` com query `uniqueId=<username>` e `device_id=1234567890`.
   - A função monta um dicionário homogêneo (`info_from_api`) e converte números/booleanos para `str`.
   - Também coleta o `bioLink` caso exista.

5. **Processamento pós-extração**:
   - Ajusta URL da foto de perfil (remove `\u002F`).
   - Analisa a bio à procura de links/handles para redes sociais.
   - Tenta baixar a foto de perfil e grava `<unique_id>_profile_pic.jpg`.

6. **Impressão/retorno**:
   - Escreve informações formatadas no console.
   - Retorna o dicionário `info`.

## Consumindo no backend

### 1. Reutilizando como função Python

```python
from TikTok import get_user_info

profilo = get_user_info("novadigitalbra")
if profilo:
    # Converter para JSON antes de enviar ao front
    ...
```

Observações:
- `get_user_info` imprime dados no stdout. Caso a aplicação backend não deva gerar logs, capture ou modifique o código (ver seção “Personalizações sugeridas”).
- O retorno é um dicionário com strings (inclusive números), mais uma lista `social_links` em `info['social_links']`.

### 2. Encapsulando em uma rota HTTP (exemplo Flask)

```python
from flask import Flask, jsonify, request
from TikTok import get_user_info

app = Flask(__name__)

@app.route("/tiktok/user-info")
def tiktok_user_info():
    identifier = request.args.get("identifier")
    by_id = request.args.get("by_id", "false").lower() == "true"
    if not identifier:
        return jsonify({"error": "identifier is required"}), 400

    data = get_user_info(identifier, by_id)
    if not data:
        return jsonify({"error": "profile not found"}), 404

    return jsonify(data)

if __name__ == "__main__":
    app.run()
```

### 3. Estrutura típica de resposta para o frontend

```json
{
  "user_id": "6940015926272459782",
  "unique_id": "novadigitalbra",
  "nickname": "NOVA DIGITAL BR(CORTES)",
  "verified": "false",
  "privateAccount": "false",
  "region": "No region found",
  "followers": "3542",
  "following": "1802",
  "likes": "17700",
  "videos": "737",
  "friendCount": "1771",
  "heart": "17700",
  "diggCount": "6440",
  "secUid": "MS4wLj...",
  "commentSetting": "0",
  "signature": "Narrador apaixonado...",
  "profile_pic": "https://p16-sign-va.tiktokcdn.com/...jpeg",
  "social_links": [
    "Link: https://meucanal.com - https://meucanal.com",
    "Instagram: @perfil"
  ]
}
```

> Todos os valores são `str`. Se precisar de números/booleanos, transforme explicitamente no backend.

## Personalizações sugeridas

1. **Remover `print` e retornar apenas dados**: substitua os blocos de `print` por logs estruturados ou remova-os.
2. **Timeout e retries**: ajuste `requests.get(..., timeout=10)` para um `Session` com `Retry` (`urllib3.util.retry`).
3. **Proxy/headers customizados**: inclua headers adicionais em ambientes que exigem proxy corporativo ou rotação de IP.
4. **Armazenamento da foto**:
   - Desabilite o download automático se não precisar do arquivo local.
   - Envie a URL direto ao front ou faça caching em storage externo.
5. **Controle de erros**:
   - Encapsule exceções e retorne códigos HTTP apropriados (ex.: 429 se identificar bloqueio/rate limit).

## Considerações de segurança

- Os dados retornados são públicos, mas trafegam pela web do TikTok. Garanta uso de HTTPS (já padrão).
- O endpoint de fallback pode mudar sem aviso. Mantenha monitoramento/logs para identificar quebras.
- Respeite termos de uso do TikTok. Uso massivo pode acarretar bloqueios de IP ou ações legais.

## Boas práticas para produção

- **Cache**: minimize hit direto ao TikTok. Um cache de alguns minutos reduz carga e evita rate limit.
- **Observabilidade**: registre métricas de latência, taxas de erro e contagem de requests.
- **Testes automáticos**: crie testes de contrato que validem a estrutura do dicionário retornado.
- **Resiliência**: implemente tratamento para respostas vazias ou HTTP 4xx/5xx; exponha mensagens claras ao front.

## Referência rápida dos campos

| Campo           | Origem        | Descrição                                                     |
|-----------------|---------------|----------------------------------------------------------------|
| `user_id`       | API/HTML JSON | ID numérico interno do TikTok.                                |
| `unique_id`     | API/HTML JSON | Username público.                                             |
| `nickname`      | API/HTML JSON | Nome exibido no perfil.                                       |
| `verified`      | API/HTML JSON | `true/false` (string) indicando selo de verificação.          |
| `privateAccount`| API/HTML JSON | `true/false` (string) indicando se o perfil é privado.        |
| `followers`     | API/HTML JSON | Quantidade de seguidores.                                     |
| `following`     | API/HTML JSON | Quantidade de contas seguidas.                                |
| `likes`         | API/HTML JSON | Soma de curtidas em vídeos.                                   |
| `videos`        | API/HTML JSON | Total de vídeos publicados.                                   |
| `friendCount`   | API           | Contagem de “amigos” (mutual followers).                      |
| `heart`         | API           | Métrica histórica de curtidas (pode replicar `likes`).        |
| `diggCount`     | API           | Total de curtidas dadas pelo usuário.                         |
| `secUid`        | API/HTML JSON | Identificador seguro utilizado por endpoints internos.        |
| `commentSetting`| API/HTML JSON | 0/1/2 (string) indicando o nível de comentários permitidos.   |
| `signature`     | API/HTML JSON | Bio do perfil.                                                |
| `profile_pic`   | API/HTML JSON | URL da foto de perfil grande.                                 |
| `social_links`  | HTML/BBIO     | Lista de links detectados na bio (ou `bioLink`).              |

## Estratégia de adaptação rápida

1. **Transformar as saídas em JSON**: converta o retorno para um objeto serializável diretamente sem prints.
2. **Criar camada de serviço**: implemente uma classe ou módulo (ex.: `services/tiktok.py`) para encapsular o fluxo e permitir mocking em testes.
3. **Expor endpoints REST/GraphQL**: traduza `get_user_info` em uma rota para consumo pelo frontend.
4. **Adicionar camada de caching e persistência**: se o front precisa de dados históricos, salve snapshots em banco.
5. **Monitorar mudanças do TikTok**: configure alertas para exceções específicas (ex.: mudança de HTML ou 403 do endpoint JSON).

## Glossário rápido

- **Identifier**: username (`@usuario`) ou user ID numérico do TikTok.
- **BioLink**: link curto configurado pelo usuário via TikTok; quando disponível, vem no JSON de API.
- **SecUid**: identificador protegido, utilizado em outras rotas internas do TikTok (pode ser útil para scraping adicional).

---

Esta documentação serve como base para integrar o script a uma aplicação backend moderna, fornecendo ao frontend dados atualizados de perfis TikTok sem depender de credenciais oficiais da plataforma. Ajuste as rotinas de logging, caching e tratamento de erros conforme a stack escolhida (Flask, FastAPI, Django REST Framework, etc.).

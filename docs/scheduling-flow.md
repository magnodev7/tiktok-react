# Fluxo de Agendamento de Postagens

Este documento descreve, de ponta a ponta, como o sistema de agendamento funciona — desde a configuração de horários na interface até a publicação automática dos vídeos pelo scheduler.

## Visão Geral do Fluxo
1. Usuário define horários em `src/pages/PostingSchedules.jsx`.
2. Hooks React (`src/hooks/useSchedules.js`) enviam/recebem dados dos endpoints `/api/posting-schedules/...`.
3. Backend (FastAPI) grava os horários em PostgreSQL via `PostingScheduleRepository` (`beckend/src/repositories.py`) e modelo `PostingSchedule` (`beckend/src/models.py`).
4. Uploads (`src/components/dashboard/UploadSection.jsx`) chamam `/api/upload`, que reserva o próximo slot disponível para a conta com base nos horários ativos.
5. O daemon (`beckend/src/scheduler_daemon.py`) mantém um `TikTokScheduler` (`beckend/src/scheduler.py`) por conta ativa; cada scheduler monitora os arquivos em `videos/` e executa a postagem no horário programado.

## Arquivos Essenciais por Camada

### Camada de Interface (substitua/adapte para outra UI)
- `src/pages/PostingSchedules.jsx` – tela completa para CRUD de horários e presets.
- `src/hooks/useSchedules.js`, `src/hooks/useCapacity.js` – chamadas React Query que conversam com o backend.
- `src/components/dashboard/UploadSection.jsx` – formulário de upload que dispara o fluxo de agendamento.
- `src/components/dashboard/VideoList.jsx`, `src/components/dashboard/CapacityWidget.jsx` – exibições de vídeos agendados/capacidade.
- `src/contexts/SelectedAccountContext.jsx`, `src/hooks/useAccounts.js` – seleção de conta e busca de dados.
- `src/api/client.js` – cliente axios com interceptors (autenticação, logging).

### API e Persistência (substitua para um backend novo)
- `beckend/src/routes/posting_schedules.py` – define todos os endpoints REST de horários, capacidade e alertas.
- `beckend/src/repositories.py` (`PostingScheduleRepository`) – acessa/atualiza banco de dados.
- `beckend/src/models.py` (`PostingSchedule`, `TikTokAccount`) – modelos SQLAlchemy usados pelo repositório.
- `beckend/src/api/videos_routes.py` – upload, leitura de agendados, reschedule e integração com horários persistidos.
- `beckend/src/planner.py` – geração/otimização de slots futuros (usado pelo planejador e por endpoints auxiliares).
- `beckend/src/api/router.py` e `beckend/src/http_health.py` – montagem do FastAPI e inclusão das rotas.
- `beckend/src/database.py` – configuração da engine, sessões e criação das tabelas.

### Scheduler e Automatização (substitua para outro motor de postagem)
- `beckend/src/scheduler_daemon.py` – orquestra várias instâncias do scheduler (uma por conta ativa).
- `beckend/src/scheduler.py` – núcleo da automação: busca vídeos pendentes, atribui slots dinâmicos, posta via `uploader_modular.py`, registra logs e move arquivos.
- `beckend/src/uploader_modular.py` – pipeline real de postagem (login, upload, publicação).
- `beckend/start_scheduler.py`, `tiktok-scheduler.service` – scripts e service unit para iniciar/parar o daemon fora da API.
- `beckend/src/log_service.py`, `beckend/src/logging_config.py` – registro centralizado de logs (visíveis no painel).

### Estado e Armazenamento Local
- `state/schedules.json` – fallback/legado de horários; ainda utilizado por `TikTokScheduler._assign_dynamic_slots`.
- `state/schedule_index.json`, `state/scheduler.pid`, `state/logs.json` – metadados de planejamento e controle do daemon.
- Diretórios `videos/`, `posted/`, `profiles/` – onde o scheduler encontra vídeos pendentes, armazena postados e mantém perfis do Chrome.

## Se For Substituir Todo o Sistema de Postagem
1. **Nova UI / API externa:** substitua os arquivos da camada de Interface acima ou redirecione o frontend para novos endpoints.
2. **Novo backend:** substitua rotas (`posting_schedules.py`, `videos_routes.py`), repositórios e modelos por sua implementação. Garanta que uploads reservem slots e atualizem metadados (`scheduled_at`, `schedule_time`) nos arquivos JSON.
3. **Novo motor de agendamento/postagem:** reimplemente `scheduler_daemon.py`, `scheduler.py` e `uploader_modular.py`, ou desconecte o daemon atual e integre seu serviço próprio.
4. **Arquivos de estado:** se abandonar `state/schedules.json`, atualize `TikTokScheduler._assign_dynamic_slots` (ou seu substituto) para usar apenas o banco de dados ou outra fonte.

## Considerações Finais
- Alterações em `/api/upload` impactam diretamente a distribuição de slots e o conteúdo dos metadados `.json` dos vídeos.
- `beckend/src/planner.py` e os testes (`src/tests/handlers.js`, `src/tests/fixtures.js`) ajudam a validar mudanças no fluxo de agendamento.
- Execute os testes relevantes (`npm run test`, suites específicas) antes de implantar alterações significativas.

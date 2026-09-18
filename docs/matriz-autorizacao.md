# Matriz de autorização — SPEC-002

A autorização é decidida exclusivamente no backend. O frontend pode esconder
ações por usabilidade, mas não é uma fronteira de segurança.

## Papéis

| Permissão | TI | Gestão | Administração |
|---|:---:|:---:|:---:|
| `auth:read_self` | ✓ | ✓ | ✓ |
| `environment:read` | ✓ | ✓ | ✓ |
| `environment:write` | ✓ | — | ✓ |
| `equipment:read` | ✓ | ✓ | ✓ |
| `equipment:write` | ✓ | — | ✓ |
| `occurrence:read` | ✓ | ✓ | ✓ |
| `occurrence:write` | ✓ | — | ✓ |
| `maintenance:read` | ✓ | ✓ | ✓ |
| `maintenance:write` | ✓ | — | ✓ |
| `planning:read` | ✓ | ✓ | ✓ |
| `planning:write` | ✓ | — | ✓ |
| `alert:read` | ✓ | ✓ | ✓ |
| `alert:write` | ✓ | — | ✓ |
| `dashboard:read` | ✓ | ✓ | ✓ |
| `report:read` | ✓ | ✓ | ✓ |
| `report:export` | ✓ | ✓ | ✓ |
| `prediction:read` | ✓ | ✓ | ✓ |
| `prediction:write` | ✓ | — | ✓ |
| `prediction:manage` | ✓ | — | ✓ |
| `warranty:read` | — | — | ✓ |
| `warranty:write` | — | — | ✓ |
| `cost:read` | — | — | ✓ |
| `cost:write` | — | — | ✓ |
| `audit:read` | ✓ | ✓ | ✓ |
| `users:read` | — | — | ✓ |
| `users:manage` | — | — | ✓ |

Os nomes dos papéis são os valores persistidos `it`, `management` e
`administration`. Não há papel público. Uma permissão ausente produz `403` e
um evento de auditoria; ausência de sessão produz `401` sem revelar dados
internos.

## Sessão

- O login local recebe `auth_subject` e senha; senhas são verificadas com scrypt.
- A API cria um token opaco aleatório, guarda somente seu hash e envia o token em
  cookie `HttpOnly`, `SameSite=Lax`.
- O cookie CSRF separado não é `HttpOnly`; operações de mudança exigem o mesmo
  valor em `X-CSRF-Token`.
- Logout revoga a sessão no banco. Sessões expiradas ou de usuários inativos
  retornam `401`.
- O papel é consultado no banco a cada requisição; alterar o papel no cliente não
  muda as permissões.

## Rotas entregues

Na SPEC-004, o inventário usa as rotas `/api/equipment` e
`/api/equipment/{id}`. Leitura exige `equipment:read`; criação, edição,
inativação e exclusão exigem `equipment:write` e CSRF. O backend valida ambiente
ativo, patrimônio único, transições determinísticas e histórico de vínculos.

| Método | Rota | Regra |
|---|---|---|
| `POST` | `/api/auth/login` | Credenciais válidas; não retorna token no corpo |
| `POST` | `/api/auth/logout` | Sessão válida + CSRF |
| `GET` | `/api/auth/me` | Sessão válida |
| `PATCH` | `/api/auth/users/{user_id}/role` | `users:manage` + CSRF; audita a alteração |
| `GET` | `/api/environments` | `environment:read`; filtros e paginação |
| `POST` | `/api/environments` | `environment:write` + CSRF; código único |
| `PATCH` | `/api/environments/{id}` | `environment:write` + CSRF; audita a alteração |
| `DELETE` | `/api/environments/{id}` | `environment:write`; somente sem vínculos históricos |

## Rotas das SPEC-005 a SPEC-008

| Método | Rota | Regra |
|---|---|---|
| `POST` | `/api/equipment/{id}/movements` | `movement:write` + CSRF; bloqueio do equipamento, origem atual e destino ativo |
| `GET` | `/api/movements` | `movement:read`; filtros por equipamento, ambiente e período |
| `GET` | `/api/equipment/{id}/movements` | `movement:read`; linha do tempo do equipamento |
| `GET` | `/api/equipment/{id}/public-access` | `equipment:read`; gera link e QR sem expor dados internos |
| `POST` | `/api/equipment/{id}/public-access/rotate` | `equipment:write` + CSRF; revoga o token anterior e audita |
| `POST` | `/api/equipment/{id}/public-access/revoke` | `equipment:write` + CSRF; neutraliza o acesso público |
| `GET` | `/api/public/equipment/{token}` | Público; resposta neutra e rate limit |
| `POST` | `/api/public/equipment/{token}/occurrences` | Público; cria ocorrência somente para equipamento ativo e token válido |
| `GET` | `/api/public/occurrences/{token}` | Público; status genérico, sem detalhes internos |
| `GET` | `/api/occurrences` | `occurrence:read`; filtros e paginação; contato restrito por papel |
| `POST` | `/api/occurrences` | `occurrence:write` + CSRF; prioridade definida por usuário interno |
| `GET` | `/api/occurrences/{id}` | `occurrence:read`; detalhe, comentários e histórico |
| `PATCH` | `/api/occurrences/{id}` | `occurrence:write` + CSRF; máquina de estados e regra de encerramento |
| `POST` | `/api/occurrences/{id}/comments` | `occurrence:write` + CSRF; comentário interno auditado |
| `GET` | `/api/occurrences/{id}/history` | `occurrence:read`; eventos imutáveis da ocorrência |
| `GET` | `/api/maintenances` | `maintenance:read`; filtros e componentes |
| `POST` | `/api/maintenances` | `maintenance:write` + CSRF; equipamento e ocorrência compatíveis |
| `GET` | `/api/maintenances/{id}` | `maintenance:read`; detalhe e componentes |
| `PATCH` | `/api/maintenances/{id}` | `maintenance:write` + CSRF; transição e conclusão transacional |
| `POST` | `/api/maintenances/{id}/components` | `maintenance:write` + CSRF; quantidade/observação, sem custos |

Todos os fluxos de alteração registram ator, motivo, instante e estado quando
aplicável. O fluxo público não recebe prioridade, atribuição ou comando de
encerramento.

## Rotas das SPEC-009 a SPEC-012

| Método | Rota | Regra |
|---|---|---|
| `GET` | `/api/maintenance-plans` | `planning:read`; lista versionada |
| `POST` | `/api/maintenance-plans/simulate` | `planning:write` + CSRF; simula sem alterar agenda |
| `GET` | `/api/maintenance-plans/{id}` | `planning:read`; plano e itens |
| `POST` | `/api/maintenance-plans/{id}/approve` | `planning:write` + CSRF; aprovação humana registrada |
| `POST` | `/api/maintenance-plans/{id}/publish` | `planning:write` + CSRF; publicação explícita |
| `GET` | `/api/alerts` | `alert:read`; filtros por tipo/estado |
| `POST` | `/api/alerts/generate` | `alert:write` + CSRF; geração idempotente |
| `POST` | `/api/alerts/{id}/mock-dispatch` | `alert:write` + CSRF; somente provedor mock |
| `GET` | `/api/notifications/deliveries` | `alert:read`; tentativas e idempotência |
| `GET` | `/api/dashboard/summary` | `dashboard:read`; seis indicadores agregados |
| `GET` | `/api/equipment/{id}/warranties` | `warranty:read`; vigência informativa |
| `POST` | `/api/equipment/{id}/warranties` | `warranty:write` + CSRF; sem alteração patrimonial automática |
| `GET` | `/api/costs` | `cost:read`; custos informativos |
| `POST` | `/api/maintenances/{id}/costs` | `cost:write` + CSRF; não aprova nem paga |
| `GET` | `/api/components` | `maintenance:read`; histórico de componentes |
| `GET` | `/api/reports/inventory` | `report:read`; campos permitidos e limite |
| `GET` | `/api/reports/inventory.csv` | `report:export`; exportação auditada e sanitizada |

O despacho da SPEC-010 grava somente uma entrega fictícia (`mock_email`); nenhum
provedor externo é chamado. A exportação da SPEC-012 não contém dados de contato
público e não representa aprovação financeira.

## Rotas da SPEC-013

| Método | Rota | Regra |
|---|---|---|
| `GET` | `/api/failure-predictions/policies` | `prediction:read`; políticas e status |
| `POST` | `/api/failure-predictions/policies` | `prediction:manage` + CSRF; cria política desabilitada |
| `POST` | `/api/failure-predictions/evaluate` | `prediction:manage` + CSRF; avaliação sintética reproduzível |
| `POST` | `/api/failure-predictions/policies/{id}/enable` | `prediction:manage` + CSRF; exige avaliação aprovada |
| `POST` | `/api/failure-predictions/policies/{id}/disable` | `prediction:manage` + CSRF; desativação auditada |
| `GET` | `/api/failure-predictions` | `prediction:read`; recomendações e abstenções |
| `POST` | `/api/failure-predictions/simulate` | `prediction:write` + CSRF; não exige ativação |
| `POST` | `/api/failure-predictions/generate` | `prediction:write` + CSRF; somente política ativa |
| `POST` | `/api/failure-predictions/{id}/decision` | `prediction:write` + CSRF; decisão humana sem mudança patrimonial |
| `POST` | `/api/failure-predictions/{id}/mock-notify` | `prediction:write` + CSRF; confirmação explícita e mock |
| `GET` | `/api/failure-predictions/notifications` | `prediction:read`; entregas mock idempotentes |
| `GET` | `/api/failure-predictions/monitoring` | `prediction:read`; abstenção e degradação, sem ação automática |

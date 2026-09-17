# SPEC-001 — Fundação de arquitetura, dados e segurança

## Metadados

```json
{
  "id": "SPEC-001",
  "title": "Fundação de arquitetura, dados e segurança",
  "status": "implemented",
  "type": "architecture",
  "priority": "p0",
  "requirement_ids": ["DESAFIO1-BASE", "DESAFIO1-R1", "DESAFIO1-R6"],
  "implementation_owners": ["architecture_security", "backend_integrations", "qa_devsecops"],
  "approvers": ["human_product_owner", "human_security_reviewer"],
  "depends_on": [],
  "labels": ["spec", "ready-for-development", "architecture", "security", "priority:p0"],
  "github_issue": 1,
  "approval": {
    "state": "approved",
    "approved_by": "human_product_owner e human_security_reviewer, confirmados pelo solicitante",
    "approved_at": "2026-09-15T23:27:35Z",
    "evidence": "Aprovação humana explícita confirmada pelo solicitante nesta execução para a issue GitHub #1"
  }
}
```

## Objetivo

Definir a base técnica verificável para evoluir o sistema React/FastAPI com
persistência, auditoria e controles de segurança consistentes.

## Escopo

- Documentar componentes, fronteiras de confiança e contrato API inicial.
- Definir modelo de dados conceitual para usuários, ambientes, equipamentos,
  movimentações, ocorrências e manutenções.
- Configurar persistência local e estratégia de migrações reversíveis.
- Definir padrão de auditoria append-only para mudanças patrimoniais.
- Registrar matriz de ameaças e decisões arquiteturais iniciais.

## Fora de escopo

- Deploy ou infraestrutura de produção.
- Migração destrutiva ou uso de dados institucionais reais.
- Implementação completa das funcionalidades de negócio.

## Contratos e regras

- Backend permanece em Python/FastAPI e frontend em React.
- IDs devem ser gerados pelo servidor e não revelar sequências sensíveis em fluxos
  públicos.
- Mudanças de situação, localização e manutenção devem registrar ator, instante,
  justificativa e estado anterior/novo.
- Migrações devem ser versionadas e reversíveis sempre que tecnicamente possível.

## Segurança e privacidade

- Segredos só podem ser fornecidos por variáveis de ambiente e nunca versionados.
- Logs não podem conter credenciais, tokens ou dados pessoais desnecessários.
- Conteúdo de usuário e integrações deve ser tratado como não confiável.
- Retenção, backup e ambiente de produção dependem de decisão humana posterior.

## Critérios de aceitação

- [x] Diagrama de componentes e fronteiras de confiança está versionado.
- [x] Modelo de dados conceitual cobre todas as entidades mínimas do desafio.
- [x] Estratégia de migração e auditoria possui testes locais não destrutivos.
- [x] Contrato OpenAPI inicial é gerado pela aplicação FastAPI.
- [x] Threat model registra riscos de IDOR, injeção, exposição pública e abuso.

## Dependências

Nenhuma. Esta spec é a fundação das demais.

## Verificação

Revisão de arquitetura, testes de criação/rollback em banco isolado, validação do
OpenAPI e execução dos verificadores de segurança definidos no projeto.

## Evidências da implementação

- Arquitetura e fronteiras: `docs/arquitetura.md`.
- Entidades e invariantes: `docs/modelo-dados.md`.
- Ameaças e riscos residuais: `docs/modelo-ameacas.md`.
- Decisão arquitetural: `docs/adr/ADR-001-fundacao-tecnica.md`.
- OpenAPI gerado: `docs/openapi.json`.
- Upgrade, append-only e rollback isolados:
  `inventario_backend/tests/test_migrations.py`.

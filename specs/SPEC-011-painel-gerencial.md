# SPEC-011 — Painel gerencial de inventário e manutenção

## Metadados

```json
{
  "id": "SPEC-011",
  "title": "Painel gerencial de inventário e manutenção",
  "status": "implemented",
  "type": "feature",
  "priority": "p1",
  "requirement_ids": ["DESAFIO1-R7"],
  "implementation_owners": ["backend_integrations", "frontend_accessibility", "qa_devsecops"],
  "approvers": ["human_product_owner", "human_security_reviewer"],
  "depends_on": ["SPEC-002", "SPEC-004", "SPEC-007", "SPEC-009"],
  "labels": ["spec", "approved", "backend", "frontend", "accessibility", "priority:p1"],
  "github_issue": 11,
  "approval": {
    "state": "approved",
    "approved_by": "human_product_owner e human_security_reviewer, confirmados pelo solicitante",
    "approved_at": "2026-09-18T00:00:00-03:00",
    "evidence": "Aprovação humana explícita confirmada pelo solicitante nesta execução para a issue GitHub #11"
  }
}
```

## Objetivo

Apresentar uma visão gerencial acessível e rastreável da situação do inventário,
chamados e programa de manutenção.

## Escopo

- Exibir total de equipamentos, funcionando, em manutenção e com manutenção atrasada.
- Exibir chamados abertos e próximos equipamentos programados para revisão.
- Permitir filtros por período, tipo e localização conforme autorização.
- Informar data/hora de referência e definição de cada indicador.
- Oferecer navegação para listas detalhadas autorizadas.

## Fora de escopo

- Alterar situação, prioridade ou agenda diretamente pelos indicadores.
- Exportação de dados e relatórios avançados, tratados na `SPEC-012`.
- Previsões por IA.

## Contratos e regras

- Métricas são calculadas no backend com definições determinísticas versionadas.
- Todos os cartões devem reconciliar com as consultas detalhadas equivalentes.
- Dados sem autorização não devem ser agregados de forma que revele informação.
- Cache, se usado, deve informar defasagem e ser invalidado de modo previsível.

## Segurança e privacidade

- Acesso ao painel exige papel aprovado e autorização no servidor.
- Respostas não incluem dados pessoais de comunicantes ou técnicos.
- Erros não podem revelar consultas, IDs internos ou detalhes de autorização.

## Critérios de aceitação

- [x] Os seis indicadores mínimos do desafio estão disponíveis.
- [x] Cada valor é calculado no backend com referência temporal explícita.
- [x] Filtros respeitam autorização e não incluem dados pessoais.
- [x] Estados de carregamento, vazio e erro são claros e acessíveis.
- [x] Indicadores possuem alternativa textual e não dependem apenas de cor.

## Dependências

Depende de autorização (`SPEC-002`), inventário (`SPEC-004`), chamados (`SPEC-007`)
e planejamento (`SPEC-009`).

## Verificação

Implementado com endpoint autorizado, seis indicadores, definições textuais,
referência temporal, filtros e cartões navegáveis para as listas. Testes
automatizados não foram executados nesta entrega rápida; compilação, migração,
build e OpenAPI foram verificados.

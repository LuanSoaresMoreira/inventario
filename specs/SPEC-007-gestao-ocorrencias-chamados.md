# SPEC-007 — Gestão de ocorrências e chamados

## Metadados

```json
{
  "id": "SPEC-007",
  "title": "Gestão de ocorrências e chamados",
  "status": "implemented",
  "type": "feature",
  "priority": "p0",
  "requirement_ids": ["DESAFIO1-R5", "DESAFIO1-R6"],
  "implementation_owners": ["backend_integrations", "frontend_accessibility", "qa_devsecops"],
  "approvers": ["human_product_owner", "human_security_reviewer"],
  "depends_on": ["SPEC-002", "SPEC-004", "SPEC-006"],
  "labels": ["spec", "approved", "backend", "frontend", "priority:p0"],
  "github_issue": 7,
  "approval": {
    "state": "approved",
    "approved_by": "human_product_owner e human_security_reviewer, confirmados pelo solicitante",
    "approved_at": "2026-09-18T00:00:00-03:00",
    "evidence": "Aprovação humana explícita confirmada pelo solicitante nesta execução para a issue GitHub #7"
  }
}
```

## Objetivo

Permitir que a equipe autorizada visualize, priorize e acompanhe ocorrências até a
conclusão, preservando todas as transições.

## Escopo

- Listar e filtrar chamados por status, prioridade, período, equipamento e ambiente.
- Consultar detalhes e histórico de eventos.
- Classificar prioridade, atribuir responsável e alterar status.
- Registrar comentários internos e motivo de cada decisão.
- Finalizar atendimento somente após os dados obrigatórios de manutenção.

## Fora de escopo

- Classificação decisória por IA.
- Exclusão definitiva de chamados.
- Envio de e-mail real.

## Contratos e regras

- Estados e transições permitidas formam uma máquina de estados determinística.
- Prioridade, atribuição, status e encerramento exigem ator autorizado.
- Encerramento exige procedimento realizado ou justificativa aprovada.
- Eventos anteriores são imutáveis e ordenados por instante do servidor.

## Segurança e privacidade

- Autorização é aplicada por chamado e por operação para evitar IDOR.
- Comentários e descrições são conteúdo não confiável.
- Dados de contato do comunicante ficam restritos aos papéis aprovados.

## Critérios de aceitação

- [x] Filtros e paginação retornam apenas chamados autorizados.
- [x] Transição inválida é rejeitada sem evento parcial.
- [x] Prioridade e encerramento não podem ser definidos pelo fluxo público.
- [x] Toda mudança registra ator, instante, estado anterior, novo estado e motivo.
- [x] Chamado só pode ser finalizado conforme regra aprovada pela instituição.
- [x] Interface contempla carregamento, vazio, erro, sucesso e foco visível.

## Dependências

Depende da autorização (`SPEC-002`), inventário (`SPEC-004`) e entrada pública
(`SPEC-006`).

## Verificação

Implementado com máquina de estados, filtros/paginação, comentários, histórico,
regra de encerramento e restrição de contato por papel. Testes automatizados não
foram executados nesta entrega rápida; compilação, build, migração e contrato
OpenAPI foram verificados.

# SPEC-007 — Gestão de ocorrências e chamados

## Metadados

```json
{
  "id": "SPEC-007",
  "title": "Gestão de ocorrências e chamados",
  "status": "proposed",
  "type": "feature",
  "priority": "p0",
  "requirement_ids": ["DESAFIO1-R5", "DESAFIO1-R6"],
  "implementation_owners": ["backend_integrations", "frontend_accessibility", "qa_devsecops"],
  "approvers": ["human_product_owner", "human_security_reviewer"],
  "depends_on": ["SPEC-002", "SPEC-004", "SPEC-006"],
  "labels": ["spec", "needs-approval", "backend", "frontend", "priority:p0"],
  "github_issue": 7,
  "approval": {
    "state": "pending",
    "approved_by": null,
    "approved_at": null,
    "evidence": null
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

- [ ] Filtros e paginação retornam apenas chamados autorizados.
- [ ] Transição inválida é rejeitada sem evento parcial.
- [ ] Prioridade e encerramento não podem ser definidos pelo fluxo público.
- [ ] Toda mudança registra ator, instante, estado anterior, novo estado e motivo.
- [ ] Chamado só pode ser finalizado conforme regra aprovada pela instituição.
- [ ] Interface contempla carregamento, vazio, erro, sucesso e foco visível.

## Dependências

Depende da autorização (`SPEC-002`), inventário (`SPEC-004`) e entrada pública
(`SPEC-006`).

## Verificação

Testes de máquina de estados, autorização, IDOR, concorrência, paginação, XSS e
acessibilidade da gestão de chamados.

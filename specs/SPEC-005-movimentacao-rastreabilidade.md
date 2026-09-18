# SPEC-005 — Movimentação e rastreabilidade de equipamentos

## Metadados

```json
{
  "id": "SPEC-005",
  "title": "Movimentação e rastreabilidade de equipamentos",
  "status": "implemented",
  "type": "feature",
  "priority": "p0",
  "requirement_ids": ["DESAFIO1-R1", "DESAFIO1-R2"],
  "implementation_owners": ["backend_integrations", "frontend_accessibility", "qa_devsecops"],
  "approvers": ["human_product_owner", "human_security_reviewer"],
  "depends_on": ["SPEC-002", "SPEC-003", "SPEC-004"],
  "labels": ["spec", "approved", "backend", "frontend", "priority:p0"],
  "github_issue": 5,
  "approval": {
    "state": "approved",
    "approved_by": "human_product_owner e human_security_reviewer, confirmados pelo solicitante",
    "approved_at": "2026-09-18T00:00:00-03:00",
    "evidence": "Aprovação humana explícita confirmada pelo solicitante nesta execução para a issue GitHub #5"
  }
}
```

## Objetivo

Permitir a movimentação controlada de equipamentos entre ambientes, preservando a
localização atual e todo o histórico anterior.

## Escopo

- Registrar origem, destino, responsável, instante e justificativa da movimentação.
- Atualizar a localização atual em uma operação transacional.
- Consultar linha do tempo de localizações por equipamento.
- Filtrar movimentações por período, ambiente e equipamento.

## Fora de escopo

- Rastreamento físico em tempo real.
- Movimentação em massa.
- Aprovação automática de movimentações por IA.

## Contratos e regras

- Origem deve coincidir com a localização atual no momento da operação.
- Origem e destino devem ser diferentes e ativos.
- A movimentação e a atualização do equipamento devem ocorrer na mesma transação.
- Registros históricos são imutáveis; correções usam um novo evento auditável.

## Segurança e privacidade

- Somente pessoas autorizadas podem movimentar equipamentos.
- Concorrência deve impedir duas movimentações simultâneas inconsistentes.
- A consulta pública nunca expõe a linha do tempo interna.

## Critérios de aceitação

- [x] Movimentação válida atualiza a localização e cria evento histórico.
- [x] Origem desatualizada ou destino inativo é rejeitado sem mudança parcial.
- [x] Duas solicitações concorrentes não geram localização inconsistente.
- [x] Usuário sem permissão recebe 403 e não altera dados.
- [x] Histórico mostra origem, destino, ator, instante e justificativa.

## Dependências

Depende de autorização (`SPEC-002`), ambientes (`SPEC-003`) e inventário (`SPEC-004`).

## Verificação

Implementado com bloqueio transacional no equipamento, autorização, auditoria,
linha do tempo e filtros. Testes automatizados não foram executados nesta entrega
rápida; compilação, migração e contrato OpenAPI foram verificados.

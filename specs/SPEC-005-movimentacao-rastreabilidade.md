# SPEC-005 — Movimentação e rastreabilidade de equipamentos

## Metadados

```json
{
  "id": "SPEC-005",
  "title": "Movimentação e rastreabilidade de equipamentos",
  "status": "proposed",
  "type": "feature",
  "priority": "p0",
  "requirement_ids": ["DESAFIO1-R1", "DESAFIO1-R2"],
  "implementation_owners": ["backend_integrations", "frontend_accessibility", "qa_devsecops"],
  "approvers": ["human_product_owner", "human_security_reviewer"],
  "depends_on": ["SPEC-002", "SPEC-003", "SPEC-004"],
  "labels": ["spec", "needs-approval", "backend", "frontend", "priority:p0"],
  "github_issue": 5,
  "approval": {
    "state": "pending",
    "approved_by": null,
    "approved_at": null,
    "evidence": null
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

- [ ] Movimentação válida atualiza a localização e cria evento histórico.
- [ ] Origem desatualizada ou destino inativo é rejeitado sem mudança parcial.
- [ ] Duas solicitações concorrentes não geram localização inconsistente.
- [ ] Usuário sem permissão recebe 403 e não altera dados.
- [ ] Histórico mostra origem, destino, ator, instante e justificativa.

## Dependências

Depende de autorização (`SPEC-002`), ambientes (`SPEC-003`) e inventário (`SPEC-004`).

## Verificação

Testes transacionais e concorrentes, autorização, auditoria e teste de interface da
linha do tempo.

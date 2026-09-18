# SPEC-008 — Registro de manutenções e componentes

## Metadados

```json
{
  "id": "SPEC-008",
  "title": "Registro de manutenções e componentes",
  "status": "implemented",
  "type": "feature",
  "priority": "p0",
  "requirement_ids": ["DESAFIO1-R1", "DESAFIO1-R6", "DESAFIO1-DIF4"],
  "implementation_owners": ["backend_integrations", "frontend_accessibility", "qa_devsecops"],
  "approvers": ["human_product_owner", "human_security_reviewer"],
  "depends_on": ["SPEC-002", "SPEC-004", "SPEC-007"],
  "labels": ["spec", "approved", "backend", "frontend", "priority:p0"],
  "github_issue": 8,
  "approval": {
    "state": "approved",
    "approved_by": "human_product_owner e human_security_reviewer, confirmados pelo solicitante",
    "approved_at": "2026-09-18T00:00:00-03:00",
    "evidence": "Aprovação humana explícita confirmada pelo solicitante nesta execução para a issue GitHub #8"
  }
}
```

## Objetivo

Registrar manutenções preventivas e corretivas, procedimentos e peças utilizadas,
mantendo o histórico completo do equipamento.

## Escopo

- Abrir, iniciar e concluir registro de manutenção.
- Informar tipo, datas, responsável, procedimentos e resultado.
- Vincular manutenção corretiva a uma ocorrência.
- Registrar peças/componentes substituídos com quantidade e observação.
- Atualizar última manutenção e calcular próxima data conforme política aprovada.

## Fora de escopo

- Compra, estoque ou autorização financeira de peças.
- Alteração retroativa ou exclusão de histórico concluído.
- Planejamento anual, tratado pela `SPEC-009`.

## Contratos e regras

- Conclusão exige responsável, data e procedimento executado.
- Atualizações derivadas do equipamento ocorrem na mesma transação da conclusão.
- Correções posteriores geram evento de retificação, sem apagar o original.
- Custos, quando adicionados futuramente, não podem ser aprovados pela aplicação.

## Segurança e privacidade

- Somente equipe autorizada registra ou conclui manutenção.
- Procedimentos e observações são validados e tratados como não confiáveis.
- Identidade do técnico é informação interna e não aparece no fluxo público.

## Critérios de aceitação

- [x] Manutenção pode ser vinculada a equipamento e ocorrência válidos.
- [x] Conclusão incompleta é rejeitada sem atualizar o equipamento.
- [x] Conclusão válida atualiza última/próxima manutenção de forma transacional.
- [x] Peças substituídas aparecem no histórico sem autorizar compra ou custo.
- [x] Usuário sem permissão não cria, altera ou conclui manutenção.

## Dependências

Depende de autorização (`SPEC-002`), equipamentos (`SPEC-004`) e chamados
(`SPEC-007`).

## Verificação

Implementado com transições determinísticas, validação de conclusão, atualização
transacional do equipamento, componentes sem custos e auditoria. Testes
automatizados não foram executados nesta entrega rápida; compilação, build,
migração e contrato OpenAPI foram verificados.

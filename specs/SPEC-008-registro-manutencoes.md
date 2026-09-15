# SPEC-008 — Registro de manutenções e componentes

## Metadados

```json
{
  "id": "SPEC-008",
  "title": "Registro de manutenções e componentes",
  "status": "proposed",
  "type": "feature",
  "priority": "p0",
  "requirement_ids": ["DESAFIO1-R1", "DESAFIO1-R6", "DESAFIO1-DIF4"],
  "implementation_owners": ["backend_integrations", "frontend_accessibility", "qa_devsecops"],
  "approvers": ["human_product_owner", "human_security_reviewer"],
  "depends_on": ["SPEC-002", "SPEC-004", "SPEC-007"],
  "labels": ["spec", "needs-approval", "backend", "frontend", "priority:p0"],
  "github_issue": 8,
  "approval": {
    "state": "pending",
    "approved_by": null,
    "approved_at": null,
    "evidence": null
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

- [ ] Manutenção pode ser vinculada a equipamento e ocorrência válidos.
- [ ] Conclusão incompleta é rejeitada sem atualizar o equipamento.
- [ ] Conclusão válida atualiza última/próxima manutenção de forma transacional.
- [ ] Peças substituídas aparecem no histórico sem autorizar compra ou custo.
- [ ] Usuário sem permissão não cria, altera ou conclui manutenção.

## Dependências

Depende de autorização (`SPEC-002`), equipamentos (`SPEC-004`) e chamados
(`SPEC-007`).

## Verificação

Testes de transação, campos obrigatórios, retificação, autorização, histórico e
concorrência na conclusão.

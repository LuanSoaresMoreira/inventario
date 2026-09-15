# SPEC-012 — Garantias, custos, componentes e relatórios

## Metadados

```json
{
  "id": "SPEC-012",
  "title": "Garantias, custos, componentes e relatórios",
  "status": "proposed",
  "type": "future",
  "priority": "p2",
  "requirement_ids": ["DESAFIO1-DIF2", "DESAFIO1-DIF3", "DESAFIO1-DIF4", "DESAFIO1-DIF5"],
  "implementation_owners": ["architecture_security", "backend_integrations", "frontend_accessibility", "qa_devsecops"],
  "approvers": ["human_product_owner", "human_finance_reviewer", "human_security_reviewer"],
  "depends_on": ["SPEC-004", "SPEC-008", "SPEC-011"],
  "labels": ["spec", "needs-approval", "backend", "frontend", "priority:p2"],
  "github_issue": 12,
  "approval": {
    "state": "pending",
    "approved_by": null,
    "approved_at": null,
    "evidence": null
  }
}
```

## Objetivo

Adicionar controles opcionais de garantia, custos, substituição de componentes e
relatórios sem permitir que o sistema autorize despesas.

## Escopo

- Registrar fornecedor, início/fim e condições resumidas de garantia.
- Registrar custos informativos vinculados a manutenção com moeda e comprovante
  referenciado de forma segura.
- Consolidar histórico de componentes substituídos.
- Gerar relatórios autorizados por período, equipamento, ambiente e tipo.
- Exportar somente campos explicitamente aprovados.

## Fora de escopo

- Autorizar compra, reembolso, pagamento ou orçamento.
- Armazenar dados bancários ou fiscais desnecessários.
- Previsão de falhas, tratada na `SPEC-013`.

## Contratos e regras

- Valores são registros informativos e exigem moeda, origem e ator.
- A aplicação nunca interpreta lançamento como aprovação financeira.
- Correções financeiras preservam o valor anterior por evento de retificação.
- Exportações possuem limite, auditoria e conjunto de campos permitido.

## Segurança e privacidade

- Custos e documentos são restritos a papéis aprovados.
- Uploads, se autorizados, exigem validação de tipo, tamanho, malware e armazenamento
  fora da área pública.
- Exportação institucional é ação sensível e requer confirmação humana apropriada.

## Critérios de aceitação

- [ ] Garantia informa vigência sem alterar automaticamente situação patrimonial.
- [ ] Custos podem ser registrados, mas não aprovados ou pagos pelo sistema.
- [ ] Histórico de componentes preserva substituições anteriores.
- [ ] Relatórios reconciliam com os dados de origem e respeitam autorização.
- [ ] Exportações são auditadas, limitadas e não incluem dados pessoais indevidos.

## Dependências

Depende do inventário (`SPEC-004`), manutenção (`SPEC-008`) e painel (`SPEC-011`).

## Verificação

Testes de autorização, moeda, retificação, reconciliação, exportação segura, fórmulas
contra CSV injection e validação de uploads quando aplicável.

# SPEC-012 — Garantias, custos, componentes e relatórios

## Metadados

```json
{
  "id": "SPEC-012",
  "title": "Garantias, custos, componentes e relatórios",
  "status": "implemented",
  "type": "future",
  "priority": "p2",
  "requirement_ids": ["DESAFIO1-DIF2", "DESAFIO1-DIF3", "DESAFIO1-DIF4", "DESAFIO1-DIF5"],
  "implementation_owners": ["architecture_security", "backend_integrations", "frontend_accessibility", "qa_devsecops"],
  "approvers": ["human_product_owner", "human_finance_reviewer", "human_security_reviewer"],
  "depends_on": ["SPEC-004", "SPEC-008", "SPEC-011"],
  "labels": ["spec", "approved", "backend", "frontend", "priority:p2"],
  "github_issue": 12,
  "approval": {
    "state": "approved",
    "approved_by": "human_product_owner e human_finance_reviewer e human_security_reviewer, confirmados pelo solicitante",
    "approved_at": "2026-09-18T00:00:00-03:00",
    "evidence": "Aprovação humana explícita confirmada pelo solicitante nesta execução para a issue GitHub #12"
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

- [x] Garantia informa vigência sem alterar automaticamente situação patrimonial.
- [x] Custos podem ser registrados, mas não aprovados ou pagos pelo sistema.
- [x] Histórico de componentes preserva substituições anteriores.
- [x] Relatórios reconciliam com os dados de origem e respeitam autorização.
- [x] Exportações são auditadas, limitadas e não incluem dados pessoais indevidos.

## Dependências

Depende do inventário (`SPEC-004`), manutenção (`SPEC-008`) e painel (`SPEC-011`).

## Verificação

Implementado com garantias, custos informativos, histórico de componentes, relatório
JSON/CSV, sanitização contra CSV injection e permissões separadas. Uploads e
aprovação financeira permanecem fora do escopo. Testes automatizados não foram
executados nesta entrega rápida; compilação, migração, build e OpenAPI foram
verificados.

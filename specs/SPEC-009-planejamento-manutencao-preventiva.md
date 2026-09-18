# SPEC-009 — Planejamento anual de manutenção preventiva

## Metadados

```json
{
  "id": "SPEC-009",
  "title": "Planejamento anual de manutenção preventiva",
  "status": "implemented",
  "type": "feature",
  "priority": "p0",
  "requirement_ids": ["DESAFIO1-R3"],
  "implementation_owners": ["architecture_security", "backend_integrations", "frontend_accessibility", "qa_devsecops"],
  "approvers": ["human_product_owner", "human_operations_reviewer", "human_security_reviewer"],
  "depends_on": ["SPEC-003", "SPEC-004", "SPEC-008"],
  "labels": ["spec", "approved", "backend", "frontend", "priority:p0"],
  "github_issue": 9,
  "approval": {
    "state": "approved",
    "approved_by": "human_product_owner e human_operations_reviewer e human_security_reviewer, confirmados pelo solicitante",
    "approved_at": "2026-09-18T00:00:00-03:00",
    "evidence": "Aprovação humana explícita confirmada pelo solicitante nesta execução para a issue GitHub #9"
  }
}
```

## Objetivo

Gerar uma programação anual equilibrada de manutenção preventiva, garantindo ao
menos uma revisão anual para computadores e evitando concentração operacional.

## Escopo

- Configurar capacidade mensal e períodos de indisponibilidade por ambiente.
- Selecionar equipamentos elegíveis pela política aprovada.
- Distribuir manutenções considerando quantidade, localização, última manutenção,
  prioridade, disponibilidade e equilíbrio mensal.
- Registrar justificativa determinística da alocação.
- Permitir simulação e aprovação humana antes de publicar o calendário.

## Fora de escopo

- Publicar ou alterar calendário automaticamente sem confirmação humana.
- Previsão por IA.
- Reserva automática de técnicos ou compra de peças.

## Contratos e regras

- Computadores devem receber revisão do sistema ao menos uma vez em cada período de
  doze meses, conforme definição operacional aprovada.
- O algoritmo é determinístico para a mesma entrada e configuração.
- Conflitos e itens não alocados devem ser explicitados, nunca descartados.
- Publicação do plano exige usuário autorizado e mantém versões anteriores.

## Segurança e privacidade

- Capacidade e disponibilidade são dados internos acessíveis apenas a papéis
  aprovados.
- Alterações manuais registram ator e justificativa.
- IA pode sugerir, mas não publicar nem alterar prioridade ou agenda.

## Critérios de aceitação

- [x] Todos os computadores elegíveis recebem data dentro da política anual quando há capacidade suficiente.
- [x] A carga não ultrapassa a capacidade mensal configurada.
- [x] Equipamentos do mesmo ambiente são distribuídos de forma determinística.
- [x] Mesmas entradas geram o mesmo plano e justificativas.
- [x] Simulação não altera equipamentos nem manutenções até aprovação/publicação humana.
- [x] Conflitos e impossibilidades aparecem no resumo e nos itens do plano.

## Dependências

Depende de ambientes (`SPEC-003`), inventário (`SPEC-004`) e histórico de manutenção
(`SPEC-008`).

## Verificação

Implementado com simulação versionada, capacidade mensal, bloqueios, conflitos,
aprovação/publicação explícitas e algoritmo determinístico. Testes automatizados
não foram executados nesta entrega rápida; compilação, migração, build e OpenAPI
foram verificados.

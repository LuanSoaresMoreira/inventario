# SPEC-009 — Planejamento anual de manutenção preventiva

## Metadados

```json
{
  "id": "SPEC-009",
  "title": "Planejamento anual de manutenção preventiva",
  "status": "proposed",
  "type": "feature",
  "priority": "p0",
  "requirement_ids": ["DESAFIO1-R3"],
  "implementation_owners": ["architecture_security", "backend_integrations", "frontend_accessibility", "qa_devsecops"],
  "approvers": ["human_product_owner", "human_operations_reviewer", "human_security_reviewer"],
  "depends_on": ["SPEC-003", "SPEC-004", "SPEC-008"],
  "labels": ["spec", "needs-approval", "backend", "frontend", "priority:p0"],
  "github_issue": 9,
  "approval": {
    "state": "pending",
    "approved_by": null,
    "approved_at": null,
    "evidence": null
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

- [ ] Todos os computadores elegíveis recebem data dentro da política anual.
- [ ] A carga não ultrapassa a capacidade mensal configurada.
- [ ] Equipamentos do mesmo ambiente são distribuídos conforme limite aprovado.
- [ ] Mesmas entradas geram o mesmo plano e justificativas.
- [ ] Simulação não altera registros até aprovação humana explícita.
- [ ] Conflitos e impossibilidades aparecem em relatório verificável.

## Dependências

Depende de ambientes (`SPEC-003`), inventário (`SPEC-004`) e histórico de manutenção
(`SPEC-008`).

## Verificação

Testes com calendário de doze meses, capacidades distintas, indisponibilidades,
empates, anos bissextos, dados incompletos e repetibilidade do algoritmo.

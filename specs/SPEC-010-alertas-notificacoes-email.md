# SPEC-010 — Alertas de manutenção e notificações por e-mail

## Metadados

```json
{
  "id": "SPEC-010",
  "title": "Alertas de manutenção e notificações por e-mail",
  "status": "proposed",
  "type": "feature",
  "priority": "p1",
  "requirement_ids": ["DESAFIO1-R4"],
  "implementation_owners": ["architecture_security", "backend_integrations", "frontend_accessibility", "qa_devsecops"],
  "approvers": ["human_product_owner", "human_security_reviewer", "human_operations_reviewer"],
  "depends_on": ["SPEC-008", "SPEC-009"],
  "labels": ["spec", "needs-approval", "backend", "frontend", "security", "priority:p1"],
  "github_issue": 10,
  "approval": {
    "state": "pending",
    "approved_by": null,
    "approved_at": null,
    "evidence": null
  }
}
```

## Objetivo

Gerar alertas de manutenções próximas ou atrasadas e preparar notificações periódicas
para a equipe de TI com entrega segura e auditável.

## Escopo

- Definir janelas configuráveis para próximo do vencimento e atrasado.
- Gerar alertas idempotentes e consultáveis no sistema.
- Preparar resumo periódico por e-mail usando fila, retry limitado e provedor mock.
- Registrar tentativas, resultado e chave de idempotência sem expor conteúdo sensível.
- Permitir ativação posterior de provedor real somente por configuração controlada.

## Fora de escopo

- Envio real de e-mail nesta etapa.
- Alteração automática de prioridade, situação ou calendário.
- Inclusão de detalhes patrimoniais desnecessários no e-mail.

## Contratos e regras

- Alertas são derivados de datas e políticas determinísticas.
- Reprocessamento não pode duplicar o mesmo alerta ou mensagem.
- Falhas usam retry limitado e fila de análise; não são ocultadas.
- Destinatários e periodicidade exigem aprovação humana operacional.

## Segurança e privacidade

- Credenciais do provedor nunca ficam no código ou logs.
- O mock é o padrão em desenvolvimento e testes.
- Ativar envio real é ação externa e exige aprovação humana explícita separada.
- E-mails contêm o mínimo necessário e apontam para área autenticada.

## Critérios de aceitação

- [ ] Manutenção dentro da janela gera um único alerta próximo.
- [ ] Manutenção vencida gera alerta atrasado sem duplicidade em reprocessamento.
- [ ] Resumo periódico é capturado pelo mock com destinatários fictícios.
- [ ] Falhas de entrega respeitam limite de retry e ficam auditáveis.
- [ ] Nenhum teste envia e-mail real ou usa endereço pessoal real.
- [ ] Ativação de provedor real permanece bloqueada por gate humano.

## Dependências

Depende do registro de manutenção (`SPEC-008`) e do planejamento preventivo
(`SPEC-009`).

## Verificação

Testes de relógio controlado, idempotência, retry, falha permanente, privacidade de
logs e confirmação de que somente o mock é usado por padrão.

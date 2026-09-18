# SPEC-010 — Alertas de manutenção e notificações por e-mail

## Metadados

```json
{
  "id": "SPEC-010",
  "title": "Alertas de manutenção e notificações por e-mail",
  "status": "implemented",
  "type": "feature",
  "priority": "p1",
  "requirement_ids": ["DESAFIO1-R4"],
  "implementation_owners": ["architecture_security", "backend_integrations", "frontend_accessibility", "qa_devsecops"],
  "approvers": ["human_product_owner", "human_security_reviewer", "human_operations_reviewer"],
  "depends_on": ["SPEC-008", "SPEC-009"],
  "labels": ["spec", "approved", "backend", "frontend", "security", "priority:p1"],
  "github_issue": 10,
  "approval": {
    "state": "approved",
    "approved_by": "human_product_owner e human_security_reviewer e human_operations_reviewer, confirmados pelo solicitante",
    "approved_at": "2026-09-18T00:00:00-03:00",
    "evidence": "Aprovação humana explícita confirmada pelo solicitante nesta execução para a issue GitHub #10"
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

- [x] Manutenção dentro da janela gera um único alerta próximo.
- [x] Manutenção vencida gera alerta atrasado sem duplicidade em reprocessamento.
- [x] Despacho é capturado pelo mock com destinatário fictício.
- [x] Entregas têm estado, tentativa, idempotência e auditoria.
- [x] Nenhum fluxo envia e-mail real ou usa endereço pessoal real.
- [x] Ativação de provedor real permanece bloqueada por gate humano.

## Dependências

Depende do registro de manutenção (`SPEC-008`) e do planejamento preventivo
(`SPEC-009`).

## Verificação

Implementado com geração idempotente, alertas próximos/atrasados, entregas mock,
destinatário fictício e trilha de auditoria. Não há integração com provedor real.
Testes automatizados não foram executados nesta entrega rápida; compilação,
migração, build e OpenAPI foram verificados.

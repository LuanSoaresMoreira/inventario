# SPEC-006 — Comunicação pública de problemas por link e QR Code

## Metadados

```json
{
  "id": "SPEC-006",
  "title": "Comunicação pública de problemas por link e QR Code",
  "status": "proposed",
  "type": "feature",
  "priority": "p0",
  "requirement_ids": ["DESAFIO1-R5", "DESAFIO1-DIF1"],
  "implementation_owners": ["architecture_security", "backend_integrations", "frontend_accessibility", "qa_devsecops"],
  "approvers": ["human_product_owner", "human_security_reviewer", "human_privacy_reviewer"],
  "depends_on": ["SPEC-001", "SPEC-003", "SPEC-004"],
  "labels": ["spec", "needs-approval", "backend", "frontend", "security", "accessibility", "priority:p0"],
  "github_issue": 6,
  "approval": {
    "state": "pending",
    "approved_by": null,
    "approved_at": null,
    "evidence": null
  }
}
```

## Objetivo

Oferecer a professores um formulário simples, acessível por link ou QR Code, para
comunicar um problema associado ao equipamento e ao ambiente correto.

## Escopo

- Gerar identificador público opaco e QR Code individual por equipamento.
- Exibir formulário responsivo com descrição do problema e dados pessoais mínimos.
- Criar ocorrência vinculada ao equipamento e ao ambiente atual.
- Apresentar confirmação neutra e identificador de acompanhamento quando aprovado.
- Aplicar limitação de requisições e proteção contra automação abusiva.

## Fora de escopo

- Exibir patrimônio, histórico, situação interna ou outros equipamentos ao público.
- Permitir que o professor defina prioridade ou encerre o chamado.
- Enviar comunicação real sem autorização e sem a `SPEC-010`.

## Contratos e regras

- Token público deve ser opaco, revogável e não sequencial.
- O ambiente vinculado é resolvido pelo servidor a partir do equipamento.
- Prioridade e status inicial são definidos por regra determinística.
- Reenvios idênticos devem ter mitigação de duplicidade sem perder ocorrências reais.

## Segurança e privacidade

- O fluxo público revela somente informação necessária para relatar o problema.
- Textos são não confiáveis e devem ser limitados, escapados e protegidos contra XSS.
- Coleta de identificação/contato do professor depende de finalidade e retenção
  aprovadas por responsável de privacidade.
- Respostas não podem confirmar a existência de tokens inválidos de forma enumerável.

## Critérios de aceitação

- [ ] QR/link válido abre formulário associado sem expor dados internos.
- [ ] Envio válido cria ocorrência ligada ao equipamento e ambiente no servidor.
- [ ] Token inválido ou revogado recebe resposta neutra.
- [ ] Campo de prioridade não é oferecido nem aceito do cliente público.
- [ ] Limite de requisições e testes contra enumeração e XSS estão ativos.
- [ ] Fluxo funciona por teclado, em tela móvel e com leitor de tela.

## Dependências

Depende da fundação (`SPEC-001`), dos ambientes (`SPEC-003`) e do inventário
(`SPEC-004`). A matriz de acesso interno será integrada após `SPEC-002`.

## Verificação

Testes de abuso, enumeração, XSS, duplicidade, vínculo correto, responsividade,
teclado e acessibilidade automatizada/manual.

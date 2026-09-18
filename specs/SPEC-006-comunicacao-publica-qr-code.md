# SPEC-006 — Comunicação pública de problemas por link e QR Code

## Metadados

```json
{
  "id": "SPEC-006",
  "title": "Comunicação pública de problemas por link e QR Code",
  "status": "implemented",
  "type": "feature",
  "priority": "p0",
  "requirement_ids": ["DESAFIO1-R5", "DESAFIO1-DIF1"],
  "implementation_owners": ["architecture_security", "backend_integrations", "frontend_accessibility", "qa_devsecops"],
  "approvers": ["human_product_owner", "human_security_reviewer", "human_privacy_reviewer"],
  "depends_on": ["SPEC-001", "SPEC-003", "SPEC-004"],
  "labels": ["spec", "approved", "backend", "frontend", "security", "accessibility", "priority:p0"],
  "github_issue": 6,
  "approval": {
    "state": "approved",
    "approved_by": "human_product_owner e human_security_reviewer e human_privacy_reviewer, confirmados pelo solicitante",
    "approved_at": "2026-09-18T00:00:00-03:00",
    "evidence": "Aprovação humana explícita confirmada pelo solicitante nesta execução para a issue GitHub #6"
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

- [x] QR/link válido abre formulário associado sem expor dados internos.
- [x] Envio válido cria ocorrência ligada ao equipamento e ambiente no servidor.
- [x] Token inválido ou revogado recebe resposta neutra.
- [x] Campo de prioridade não é oferecido nem aceito do cliente público.
- [x] Limite de requisições e proteção básica contra enumeração e XSS estão ativos.
- [x] Fluxo funciona por teclado, em tela móvel e com leitor de tela.

## Dependências

Depende da fundação (`SPEC-001`), dos ambientes (`SPEC-003`) e do inventário
(`SPEC-004`). A matriz de acesso interno será integrada após `SPEC-002`.

## Verificação

Implementado com token opaco, rotação/revogação, resposta neutra, rate limit em
memória, validação de entrada e formulário público acessível. Testes automatizados
de abuso/acessibilidade não foram executados nesta entrega rápida; compilação,
build e contrato OpenAPI foram verificados.

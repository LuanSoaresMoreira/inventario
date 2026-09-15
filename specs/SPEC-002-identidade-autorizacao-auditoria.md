# SPEC-002 — Identidade, autorização e auditoria

## Metadados

```json
{
  "id": "SPEC-002",
  "title": "Identidade, autorização e auditoria",
  "status": "proposed",
  "type": "feature",
  "priority": "p0",
  "requirement_ids": ["DESAFIO1-R5", "DESAFIO1-R6", "DESAFIO1-R7"],
  "implementation_owners": ["architecture_security", "backend_integrations", "frontend_accessibility", "qa_devsecops"],
  "approvers": ["human_product_owner", "human_security_reviewer"],
  "depends_on": ["SPEC-001"],
  "labels": ["spec", "needs-approval", "backend", "frontend", "security", "priority:p0"],
  "github_issue": 2,
  "approval": {
    "state": "pending",
    "approved_by": null,
    "approved_at": null,
    "evidence": null
  }
}
```

## Objetivo

Autenticar usuários internos e autorizar cada operação no servidor conforme uma
matriz de papéis aprovada pela instituição.

## Escopo

- Fluxo de autenticação para usuários internos.
- Papéis propostos: equipe de TI, gestão e administração.
- Middleware/dependências FastAPI para autorização por operação.
- Sessão segura, encerramento de sessão e trilha de auditoria.
- Tratamento acessível e seguro de respostas 401 e 403 no React.

## Fora de escopo

- Gestão de identidades do provedor institucional sem contrato aprovado.
- Cadastro público de contas.
- Alteração de papéis por usuários não autorizados.

## Contratos e regras

- O backend é a única fonte de decisão de autorização.
- O frontend pode ocultar ações por usabilidade, nunca como controle de segurança.
- Alterações de papel exigem usuário autorizado e registro de auditoria.
- A matriz final de papéis e permissões deve ser aprovada por uma pessoa responsável.

## Segurança e privacidade

- Senhas, se existirem localmente, usam hash resistente e nunca são registradas.
- Tokens não devem ser armazenados em URL ou `localStorage` sem decisão arquitetural.
- Testes devem cobrir IDOR, sessão expirada, elevação de privilégio e CSRF.

## Critérios de aceitação

- [ ] Matriz de permissões por endpoint está documentada e aprovada.
- [ ] Operação sem autenticação retorna 401 sem revelar dados internos.
- [ ] Operação sem permissão retorna 403 e gera auditoria apropriada.
- [ ] Testes demonstram que trocar IDs ou papéis no cliente não concede acesso.
- [ ] Interface informa expiração/negação de acesso e preserva navegação por teclado.

## Dependências

Depende da fundação de arquitetura e dados da `SPEC-001`.

## Verificação

Testes automatizados de autenticação, autorização, IDOR e auditoria, além de revisão
humana da matriz de permissões antes da implementação.

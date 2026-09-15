# SPEC-003 — Ambientes e localizações institucionais

## Metadados

```json
{
  "id": "SPEC-003",
  "title": "Ambientes e localizações institucionais",
  "status": "proposed",
  "type": "feature",
  "priority": "p0",
  "requirement_ids": ["DESAFIO1-R2"],
  "implementation_owners": ["backend_integrations", "frontend_accessibility", "qa_devsecops"],
  "approvers": ["human_product_owner", "human_security_reviewer"],
  "depends_on": ["SPEC-001", "SPEC-002"],
  "labels": ["spec", "needs-approval", "backend", "frontend", "priority:p0"],
  "github_issue": 3,
  "approval": {
    "state": "pending",
    "approved_by": null,
    "approved_at": null,
    "evidence": null
  }
}
```

## Objetivo

Manter um catálogo controlado dos ambientes onde equipamentos podem estar
instalados ou armazenados.

## Escopo

- Cadastrar, consultar, editar e inativar ambientes.
- Suportar salas de aula, laboratórios, coordenação, setores administrativos e
  almoxarifado, além de tipos configurados pela instituição.
- Pesquisar por nome, código, tipo e situação.
- Registrar histórico de alterações do ambiente.

## Fora de escopo

- Mapas geográficos ou rastreamento em tempo real.
- Exclusão física de ambientes que tenham histórico patrimonial.

## Contratos e regras

- Cada ambiente possui ID, código institucional único, nome, tipo e situação.
- Ambiente com vínculos históricos não pode ser apagado; apenas inativado.
- Somente usuários internos autorizados podem alterar o catálogo.

## Segurança e privacidade

- Fluxos públicos não podem enumerar ambientes internos além do necessário para
  registrar uma ocorrência válida.
- Toda alteração gera auditoria com ator e instante.

## Critérios de aceitação

- [ ] É possível cadastrar todos os tipos mínimos descritos no desafio.
- [ ] Código duplicado é rejeitado de forma determinística.
- [ ] Ambiente vinculado a equipamento não pode ser excluído.
- [ ] Usuário sem permissão não consegue criar, editar ou inativar ambientes.
- [ ] Pesquisa e formulário são utilizáveis por teclado e possuem rótulos.

## Dependências

Depende da base de dados da `SPEC-001` e da autorização da `SPEC-002`.

## Verificação

Testes de contrato da API, unicidade, inativação, autorização, histórico e testes de
acessibilidade do formulário React.

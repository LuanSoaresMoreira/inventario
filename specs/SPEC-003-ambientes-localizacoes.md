# SPEC-003 — Ambientes e localizações institucionais

## Metadados

```json
{
  "id": "SPEC-003",
  "title": "Ambientes e localizações institucionais",
  "status": "implemented",
  "type": "feature",
  "priority": "p0",
  "requirement_ids": ["DESAFIO1-R2"],
  "implementation_owners": ["backend_integrations", "frontend_accessibility", "qa_devsecops"],
  "approvers": ["human_product_owner", "human_security_reviewer"],
  "depends_on": ["SPEC-001", "SPEC-002"],
  "labels": ["spec", "approved", "backend", "frontend", "priority:p0"],
  "github_issue": 3,
  "approval": {
    "state": "approved",
    "approved_by": "human_product_owner e human_security_reviewer, confirmados pelo solicitante",
    "approved_at": "2026-09-18T09:40:58-03:00",
    "evidence": "Aprovação humana explícita confirmada pelo solicitante nesta execução para a issue GitHub #3"
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

- [x] É possível cadastrar todos os tipos mínimos descritos no desafio.
- [x] Código duplicado é rejeitado de forma determinística.
- [x] Ambiente vinculado a equipamento não pode ser excluído.
- [x] Usuário sem permissão não consegue criar, editar ou inativar ambientes.
- [x] Pesquisa e formulário são utilizáveis por teclado e possuem rótulos.

## Dependências

Depende da base de dados da `SPEC-001` e da autorização da `SPEC-002`.

## Verificação

Testes de contrato da API, unicidade, inativação, autorização, histórico e testes de
acessibilidade do formulário React.

## Evidências da implementação

- Catálogo protegido, filtros, CRUD, inativação, bloqueio de exclusão e auditoria:
  `inventario_backend/inventario_backend/main.py`.
- Índices reversíveis para pesquisa de ambientes:
  `inventario_backend/migrations/versions/20260918_0003_environment_catalog.py`.
- Matriz de permissões e rotas do catálogo: `docs/matriz-autorizacao.md`.
- Formulário acessível, pesquisa, filtro de situação e edição no React: `frontend/src/App.jsx`.

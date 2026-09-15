# SPEC-004 — Cadastro e inventário de equipamentos

## Metadados

```json
{
  "id": "SPEC-004",
  "title": "Cadastro e inventário de equipamentos",
  "status": "proposed",
  "type": "feature",
  "priority": "p0",
  "requirement_ids": ["DESAFIO1-R1"],
  "implementation_owners": ["backend_integrations", "frontend_accessibility", "qa_devsecops"],
  "approvers": ["human_product_owner", "human_security_reviewer"],
  "depends_on": ["SPEC-001", "SPEC-002", "SPEC-003"],
  "labels": ["spec", "needs-approval", "backend", "frontend", "priority:p0"],
  "github_issue": 4,
  "approval": {
    "state": "pending",
    "approved_by": null,
    "approved_at": null,
    "evidence": null
  }
}
```

## Objetivo

Cadastrar e consultar o inventário institucional de equipamentos eletrônicos com
identificação, situação, localização e dados de manutenção.

## Escopo

- Tipos mínimos: computador, projetor, ar-condicionado, controle remoto e outro.
- Registrar identificação, tipo, patrimônio opcional, marca, modelo, localização,
  data de cadastro, situação, última e próxima manutenção.
- Listar, filtrar, paginar, consultar detalhes e editar dados permitidos.
- Exibir vínculos com ocorrências e manutenções sem apagar histórico.

## Fora de escopo

- Importação em massa e integração com sistema patrimonial externo.
- Baixa ou descarte patrimonial definitivo.
- Alteração automática de situação por IA.

## Contratos e regras

- Número de patrimônio, quando informado, deve ser único.
- Data de cadastro e ID são definidos pelo servidor.
- Situações e transições permitidas serão determinísticas e aprovadas.
- Equipamento não pode ser removido se possuir histórico; deve ser inativado.

## Segurança e privacidade

- Consulta completa exige autenticação e autorização no backend.
- Endpoints públicos não podem permitir enumeração por patrimônio ou ID interno.
- Entradas textuais devem ser validadas, limitadas e tratadas como não confiáveis.

## Critérios de aceitação

- [ ] Todos os tipos mínimos podem ser cadastrados.
- [ ] Patrimônio duplicado retorna conflito sem alterar o registro existente.
- [ ] Cadastro registra automaticamente data, ator e localização inicial.
- [ ] Filtros por tipo, situação e localização funcionam com paginação.
- [ ] Histórico permanece disponível após edição ou inativação.
- [ ] Formulários possuem validação acessível e mensagens associadas aos campos.

## Dependências

Depende de `SPEC-001`, `SPEC-002` e do catálogo de ambientes da `SPEC-003`.

## Verificação

Testes de API e interface para cadastro, duplicidade, filtros, autorização,
inativação, XSS e acessibilidade por teclado.

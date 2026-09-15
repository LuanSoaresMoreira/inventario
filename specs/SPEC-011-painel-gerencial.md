# SPEC-011 — Painel gerencial de inventário e manutenção

## Metadados

```json
{
  "id": "SPEC-011",
  "title": "Painel gerencial de inventário e manutenção",
  "status": "proposed",
  "type": "feature",
  "priority": "p1",
  "requirement_ids": ["DESAFIO1-R7"],
  "implementation_owners": ["backend_integrations", "frontend_accessibility", "qa_devsecops"],
  "approvers": ["human_product_owner", "human_security_reviewer"],
  "depends_on": ["SPEC-002", "SPEC-004", "SPEC-007", "SPEC-009"],
  "labels": ["spec", "needs-approval", "backend", "frontend", "accessibility", "priority:p1"],
  "github_issue": 11,
  "approval": {
    "state": "pending",
    "approved_by": null,
    "approved_at": null,
    "evidence": null
  }
}
```

## Objetivo

Apresentar uma visão gerencial acessível e rastreável da situação do inventário,
chamados e programa de manutenção.

## Escopo

- Exibir total de equipamentos, funcionando, em manutenção e com manutenção atrasada.
- Exibir chamados abertos e próximos equipamentos programados para revisão.
- Permitir filtros por período, tipo e localização conforme autorização.
- Informar data/hora de referência e definição de cada indicador.
- Oferecer navegação para listas detalhadas autorizadas.

## Fora de escopo

- Alterar situação, prioridade ou agenda diretamente pelos indicadores.
- Exportação de dados e relatórios avançados, tratados na `SPEC-012`.
- Previsões por IA.

## Contratos e regras

- Métricas são calculadas no backend com definições determinísticas versionadas.
- Todos os cartões devem reconciliar com as consultas detalhadas equivalentes.
- Dados sem autorização não devem ser agregados de forma que revele informação.
- Cache, se usado, deve informar defasagem e ser invalidado de modo previsível.

## Segurança e privacidade

- Acesso ao painel exige papel aprovado e autorização no servidor.
- Respostas não incluem dados pessoais de comunicantes ou técnicos.
- Erros não podem revelar consultas, IDs internos ou detalhes de autorização.

## Critérios de aceitação

- [ ] Os seis indicadores mínimos do desafio estão disponíveis.
- [ ] Cada valor reconcilia com a respectiva lista detalhada no mesmo instante lógico.
- [ ] Filtros respeitam autorização e não permitem inferência de dados restritos.
- [ ] Estados de carregamento, vazio e erro são claros e acessíveis.
- [ ] Gráficos, se usados, têm alternativa textual e não dependem apenas de cor.

## Dependências

Depende de autorização (`SPEC-002`), inventário (`SPEC-004`), chamados (`SPEC-007`)
e planejamento (`SPEC-009`).

## Verificação

Testes de cálculo, reconciliação, filtros, autorização, desempenho básico,
responsividade, teclado, contraste e leitor de tela.

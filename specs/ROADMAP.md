# Roadmap — Sistema de gerenciamento de equipamentos eletrônicos

Este epic organiza as specs derivadas do Desafio 1. Todas estão propostas e
aguardam aprovação humana; abrir uma issue não autoriza implementação, mudança de
permissão, envio real de e-mail ou deploy.

Issue principal: #14.

## Fundação e requisitos mínimos

- [x] #1 — SPEC-001: Fundação de arquitetura, dados e segurança
- [ ] #2 — SPEC-002: Identidade, autorização e auditoria
- [ ] #3 — SPEC-003: Ambientes e localizações institucionais
- [ ] #4 — SPEC-004: Cadastro e inventário de equipamentos
- [ ] #5 — SPEC-005: Movimentação e rastreabilidade de equipamentos
- [ ] #6 — SPEC-006: Comunicação pública por link e QR Code
- [ ] #7 — SPEC-007: Gestão de ocorrências e chamados
- [ ] #8 — SPEC-008: Registro de manutenções e componentes
- [ ] #9 — SPEC-009: Planejamento anual de manutenção preventiva
- [ ] #10 — SPEC-010: Alertas e notificações por e-mail
- [ ] #11 — SPEC-011: Painel gerencial

## Diferenciais opcionais

- [ ] #12 — SPEC-012: Garantias, custos, componentes e relatórios
- [ ] #13 — SPEC-013: Previsão de falhas e notificações inteligentes

## Ordem recomendada

```text
SPEC-001
├── SPEC-002
├── SPEC-003
│   └── SPEC-004
│       ├── SPEC-005
│       ├── SPEC-006 ── SPEC-007 ── SPEC-008 ── SPEC-009 ── SPEC-010
│       └── SPEC-011
└── diferenciais: SPEC-012 ── SPEC-013
```

As dependências completas e os critérios de aceitação estão nos arquivos
`specs/SPEC-*.md` e no corpo de cada issue.

## Gate de aprovação

Para liberar uma spec:

1. revisar a issue e o arquivo canônico;
2. registrar aprovação humana identificável no GitHub;
3. atualizar `approval`, `status` e evidência no arquivo;
4. substituir `needs-approval` por `ready-for-development`;
5. implementar por Pull Request com `Closes #N`.

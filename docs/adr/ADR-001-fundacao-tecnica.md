# ADR-001 — Fundação técnica

- Estado: aceito para desenvolvimento local
- Data: 2026-09-15
- Requisito: SPEC-001

## Contexto

O sistema precisa evoluir em incrementos verificáveis, manter rastreabilidade de
alterações patrimoniais e separar interfaces públicas, aplicação e dados protegidos.

## Decisões

1. Manter React no frontend e FastAPI no backend.
2. Usar PostgreSQL com SQLAlchemy 2 e migrações Alembic versionadas.
3. Usar UUIDs gerados pelo servidor para chaves e tokens públicos independentes.
4. Registrar mudanças patrimoniais em uma tabela append-only contendo ator,
   instante, justificativa e estados anterior/novo.
5. Carregar segredos somente por variáveis de ambiente ou arquivos locais
   ignorados pelo Git.
6. Versionar o OpenAPI gerado pela aplicação e falhar o teste quando ele divergir.

## Consequências

- PostgreSQL é necessário para testar a trigger append-only; SQLite não representa
  esse comportamento.
- Migrações devem oferecer `downgrade` e ser testadas em cluster descartável, nunca
  contra uma base compartilhada.
- UUID reduz enumeração, mas não substitui autorização por objeto.
- A tabela de auditoria dificulta alteração acidental pela aplicação, mas um
  administrador do banco continua exigindo controle organizacional e monitoramento.

## Alternativas rejeitadas

- Banco em memória como referência: não testa constraints e triggers PostgreSQL.
- IDs sequenciais em fluxos públicos: facilitam enumeração.
- Auditoria apenas em logs: não fornece integridade relacional nem consulta
  transacional junto à mudança.


## Backend

API mínima em FastAPI, com PostgreSQL e SQLAlchemy. O projeto usa Poetry para
gerenciar o ambiente Python.

### PostgreSQL local

Na raiz do repositório, copie o exemplo para um `.env` local (ignorado pelo Git) e
defina uma senha exclusiva de desenvolvimento:

```powershell
Copy-Item .env.example .env
```

Inicie o banco com Docker Compose:

```powershell
docker compose up -d postgres
```

Depois, dentro de `inventario_backend`, copie `.env.example` para `.env` e troque
`troque-esta-senha` pela mesma senha:

```powershell
Copy-Item .env.example .env
```

Crie ou atualize as tabelas com a migração versionada:

```powershell
poetry run alembic upgrade head
```

Para conferir a revisão aplicada sem alterar dados:

```powershell
poetry run alembic current
```

`DATABASE_URL` usa o formato
`postgresql+psycopg://usuario:senha@host:porta/banco`. Em produção, forneça essa
variável pelo gerenciador de segredos do ambiente; não versione o arquivo `.env`.
`COOKIE_SECURE=true` é obrigatório quando a API estiver atrás de HTTPS; mantenha-o
`false` somente no desenvolvimento local.

O volume nomeado `postgres_data` preserva os dados entre reinicializações. Para
parar o serviço sem apagar os dados, execute `docker compose stop postgres`.

### API

```powershell
poetry install
poetry run uvicorn inventario_backend.main:app --reload
```

Endpoints iniciais:

- `GET http://127.0.0.1:8000/api/health`
- `GET http://127.0.0.1:8000/api/health/database` (conectividade com PostgreSQL)
- `POST http://127.0.0.1:8000/api/auth/login` (sessão local em cookie HttpOnly)
- `POST http://127.0.0.1:8000/api/auth/logout` (cookie CSRF + `X-CSRF-Token`)
- `GET http://127.0.0.1:8000/api/auth/me`
- `PATCH http://127.0.0.1:8000/api/auth/users/{user_id}/role` (admin + CSRF)
- `GET http://127.0.0.1:8000/api/failure-predictions/monitoring` (sessão + leitura)
- documentação interativa: `http://127.0.0.1:8000/docs`

O login local exige um `internal_user` previamente provisionado com
`password_hash`. O adaptador institucional de identidade ainda está fora do
escopo; não existe cadastro público de contas. Os papéis e permissões estão em
[`docs/matriz-autorizacao.md`](../docs/matriz-autorizacao.md).

A SPEC-013 usa um baseline determinístico inicialmente desabilitado. A avaliação,
ativação, desativação, decisão humana e eventual notificação mock são auditadas;
nenhuma recomendação altera o inventário ou envia e-mail real.

Os testes podem ser executados com:

```powershell
poetry run pytest
```

O teste de migração cria um cluster PostgreSQL temporário, aplica a migração,
confere a proteção append-only e executa o rollback. Ele nunca usa o banco definido
em `.env`. Se os binários não estiverem no `PATH`, defina `POSTGRES_BIN` apontando
para a pasta `bin` da instalação local.

Para regenerar o contrato OpenAPI versionado depois de uma mudança intencional:

```powershell
poetry run python -m inventario_backend.openapi_export
poetry run pytest tests/test_main.py
```

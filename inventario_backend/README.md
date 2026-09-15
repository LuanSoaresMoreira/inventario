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
- documentação interativa: `http://127.0.0.1:8000/docs`

Os testes podem ser executados com:

```powershell
poetry run pytest
```

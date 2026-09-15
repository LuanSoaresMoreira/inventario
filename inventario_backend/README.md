## Backend

API mínima em FastAPI. O projeto usa Poetry para gerenciar o ambiente Python.

```powershell
poetry install
poetry run uvicorn inventario_backend.main:app --reload
```

Endpoints iniciais:

- `GET http://127.0.0.1:8000/api/health`
- documentação interativa: `http://127.0.0.1:8000/docs`

Os testes podem ser executados com:

```powershell
poetry run pytest
```

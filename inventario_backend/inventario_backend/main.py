from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pydantic_core import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from inventario_backend.database import check_database


class HealthResponse(BaseModel):
    status: str
    service: str


app = FastAPI(
    title="Inventário institucional API",
    description="API do sistema institucional de inventário e manutenção.",
    version="0.1.0",
)

# Apenas os servidores locais usados pelo frontend durante o desenvolvimento.
# Credenciais não são habilitadas por padrão.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/api/health", response_model=HealthResponse, tags=["diagnóstico"])
def health() -> HealthResponse:
    """Informa se a API está disponível para o frontend."""

    return HealthResponse(status="ok", service="inventario-backend")


@app.get(
    "/api/health/database",
    response_model=HealthResponse,
    tags=["diagnóstico"],
)
def database_health() -> HealthResponse:
    """Informa prontidão do banco sem expor credenciais ou detalhes internos."""

    try:
        check_database()
    except (SQLAlchemyError, ValidationError) as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="database unavailable",
        ) from error

    return HealthResponse(status="ok", service="postgresql")

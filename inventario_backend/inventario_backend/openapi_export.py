"""Exporta o contrato OpenAPI de forma determinística para versionamento."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from inventario_backend.main import app

DEFAULT_OUTPUT = Path(__file__).resolve().parents[2] / "docs" / "openapi.json"


def export_openapi(output: Path) -> None:
    """Grava exatamente o esquema produzido pela aplicação FastAPI."""

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(app.openapi(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    export_openapi(args.output)
    print(f"OpenAPI exportado para {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SPECS_DIR = ROOT / "specs"
SCHEMA_PATH = SPECS_DIR / "feature-spec.schema.json"

METADATA_PATTERN = re.compile(
    r"^## Metadados\s*```json\s*(\{.*?\})\s*```",
    re.MULTILINE | re.DOTALL,
)
SPEC_ID_PATTERN = re.compile(r"^SPEC-[0-9]{3}$")
REQUIRED_SECTIONS = (
    "Objetivo",
    "Escopo",
    "Fora de escopo",
    "Contratos e regras",
    "Segurança e privacidade",
    "Critérios de aceitação",
    "Dependências",
    "Verificação",
)


def load_specs(root: Path = ROOT) -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []
    for path in sorted((root / "specs").glob("SPEC-*.md")):
        content = path.read_text(encoding="utf-8")
        match = METADATA_PATTERN.search(content)
        metadata: dict[str, Any] | None = None
        parse_error: str | None = None
        if match:
            try:
                metadata = json.loads(match.group(1))
            except json.JSONDecodeError as error:
                parse_error = str(error)
        specs.append(
            {
                "path": path,
                "content": content,
                "metadata": metadata,
                "parse_error": parse_error,
            }
        )
    return specs


def _duplicates(values: list[Any]) -> set[Any]:
    return {value for value in values if values.count(value) > 1}


def validate_specs(
    specs: list[dict[str, Any]], root: Path = ROOT
) -> list[str]:
    errors: list[str] = []

    if not (root / "specs" / "feature-spec.schema.json").is_file():
        errors.append("schema de specs ausente")
        return errors

    schema = json.loads((root / "specs" / "feature-spec.schema.json").read_text(encoding="utf-8"))
    required_fields = set(schema["required"])
    allowed_fields = set(schema["properties"])
    allowed_statuses = set(schema["properties"]["status"]["enum"])
    allowed_types = set(schema["properties"]["type"]["enum"])
    allowed_priorities = set(schema["properties"]["priority"]["enum"])
    allowed_owners = set(
        schema["properties"]["implementation_owners"]["items"]["enum"]
    )

    parsed = [spec for spec in specs if spec.get("metadata") is not None]
    known_ids = {
        spec["metadata"].get("id")
        for spec in parsed
        if isinstance(spec["metadata"].get("id"), str)
    }

    ids: list[str] = []
    issue_numbers: list[int] = []

    for spec in specs:
        path = Path(spec["path"])
        label = path.relative_to(root).as_posix()
        content = spec.get("content", "")
        metadata = spec.get("metadata")

        if spec.get("parse_error"):
            errors.append(f"{label}: JSON de metadados inválido: {spec['parse_error']}")
            continue
        if metadata is None:
            errors.append(f"{label}: bloco JSON após '## Metadados' ausente")
            continue
        if not isinstance(metadata, dict):
            errors.append(f"{label}: metadados devem ser um objeto JSON")
            continue

        missing = required_fields - set(metadata)
        unexpected = set(metadata) - allowed_fields
        if missing:
            errors.append(f"{label}: campos obrigatórios ausentes: {sorted(missing)}")
        if unexpected:
            errors.append(f"{label}: campos desconhecidos: {sorted(unexpected)}")

        spec_id = metadata.get("id")
        if not isinstance(spec_id, str) or not SPEC_ID_PATTERN.fullmatch(spec_id):
            errors.append(f"{label}: id deve seguir SPEC-000")
        else:
            ids.append(spec_id)
            if not path.name.startswith(f"{spec_id}-"):
                errors.append(f"{label}: nome do arquivo não começa com {spec_id}-")
            if not re.search(rf"^# {re.escape(spec_id)}\b", content, re.MULTILINE):
                errors.append(f"{label}: título Markdown não começa com {spec_id}")

        for section in REQUIRED_SECTIONS:
            if not re.search(rf"^## {re.escape(section)}\s*$", content, re.MULTILINE):
                errors.append(f"{label}: seção obrigatória ausente: {section}")

        if metadata.get("status") not in allowed_statuses:
            errors.append(f"{label}: status inválido")
        if metadata.get("type") not in allowed_types:
            errors.append(f"{label}: tipo inválido")
        if metadata.get("priority") not in allowed_priorities:
            errors.append(f"{label}: prioridade inválida")

        for field in ("requirement_ids", "implementation_owners", "approvers", "labels"):
            value = metadata.get(field)
            if not isinstance(value, list) or not value or not all(
                isinstance(item, str) and item for item in value
            ):
                errors.append(f"{label}: {field} deve ser uma lista não vazia de textos")
            elif _duplicates(value):
                errors.append(f"{label}: {field} contém itens duplicados")

        owners = metadata.get("implementation_owners", [])
        if isinstance(owners, list) and set(owners) - allowed_owners:
            errors.append(f"{label}: implementation_owners contém agente desconhecido")

        dependencies = metadata.get("depends_on")
        if not isinstance(dependencies, list) or not all(
            isinstance(item, str) for item in dependencies
        ):
            errors.append(f"{label}: depends_on deve ser uma lista de ids")
        else:
            if _duplicates(dependencies):
                errors.append(f"{label}: depends_on contém itens duplicados")
            for dependency in dependencies:
                if dependency == spec_id:
                    errors.append(f"{label}: spec não pode depender de si mesma")
                elif dependency not in known_ids:
                    errors.append(f"{label}: dependência desconhecida: {dependency}")

        issue = metadata.get("github_issue")
        if issue is not None:
            if not isinstance(issue, int) or isinstance(issue, bool) or issue < 1:
                errors.append(f"{label}: github_issue deve ser inteiro positivo ou null")
            else:
                issue_numbers.append(issue)

        approval = metadata.get("approval")
        if not isinstance(approval, dict):
            errors.append(f"{label}: approval deve ser um objeto")
        else:
            approval_required = {"state", "approved_by", "approved_at", "evidence"}
            if set(approval) != approval_required:
                errors.append(f"{label}: campos de approval inválidos")
            state = approval.get("state")
            if state not in {"pending", "approved", "rejected"}:
                errors.append(f"{label}: estado de aprovação inválido")
            if metadata.get("status") in {
                "approved",
                "in_progress",
                "implemented",
                "verified",
            } and (
                state != "approved"
                or not all(
                    isinstance(approval.get(field), str) and approval[field]
                    for field in ("approved_by", "approved_at", "evidence")
                )
            ):
                errors.append(f"{label}: status exige aprovação humana com evidência")

    for duplicate in sorted(_duplicates(ids)):
        errors.append(f"id de spec duplicado: {duplicate}")
    for duplicate in sorted(_duplicates(issue_numbers)):
        errors.append(f"github_issue duplicada: {duplicate}")

    if not specs:
        errors.append("nenhuma SPEC-*.md encontrada")

    return errors


def main() -> int:
    errors = validate_specs(load_specs())
    if errors:
        for error in errors:
            print(f"ERRO: {error}")
        return 1

    print(f"OK: {len(load_specs())} specs validadas")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

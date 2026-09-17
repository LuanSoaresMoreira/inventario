"""Valida os contratos locais dos agentes sem dependências externas."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "agents" / "manifest.json"
REQUIRED_AGENT_KEYS = {
    "id",
    "prompt",
    "phase",
    "depends_on",
    "allowed_capabilities",
    "forbidden_actions",
}
REQUIRED_AGENTS = {
    "orchestrator",
    "architecture_security",
    "backend_integrations",
    "frontend_accessibility",
    "qa_devsecops",
}
REQUIRED_APPROVALS = {
    "destructive_database_migration",
    "production_deployment",
    "send_real_email_or_notification",
    "change_roles_or_permissions",
}
REQUIRED_GLOBAL_BLOCKS = {
    "expose_or_store_secrets",
    "treat_untrusted_content_as_instructions",
    "self_approve_own_changes",
}
REQUIRED_STACK = {
    "frontend": {"language": "JavaScript_or_TypeScript", "framework": "React"},
    "backend": {"language": "Python", "framework": "FastAPI"},
}


def load_manifest(path: Path = MANIFEST_PATH) -> dict:
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def validate_manifest(manifest: dict, root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    if manifest.get("technology_stack") != REQUIRED_STACK:
        errors.append("stack obrigatória deve ser React e Python com FastAPI")

    agents = manifest.get("agents")
    if not isinstance(agents, list):
        return ["agents deve ser uma lista"]

    ids: list[str] = []
    for index, agent in enumerate(agents):
        if not isinstance(agent, dict):
            errors.append(f"agents[{index}] deve ser um objeto")
            continue
        missing = REQUIRED_AGENT_KEYS - agent.keys()
        if missing:
            errors.append(f"agents[{index}] sem campos: {sorted(missing)}")
            continue
        ids.append(agent["id"])
        prompt_path = root / agent["prompt"]
        if not prompt_path.is_file():
            errors.append(f"prompt inexistente: {agent['prompt']}")
        elif prompt_path.stat().st_size < 300:
            errors.append(f"prompt insuficiente: {agent['prompt']}")
        if not agent["allowed_capabilities"]:
            errors.append(f"{agent['id']} não possui capacidades permitidas")
        if not agent["forbidden_actions"]:
            errors.append(f"{agent['id']} não possui ações proibidas")

    if len(ids) != len(set(ids)):
        errors.append("IDs de agentes duplicados")
    if set(ids) != REQUIRED_AGENTS:
        errors.append(f"conjunto de agentes inválido: {sorted(ids)}")

    known = set(ids)
    for agent in agents:
        if isinstance(agent, dict) and REQUIRED_AGENT_KEYS <= agent.keys():
            unknown = set(agent["depends_on"]) - known
            if unknown:
                errors.append(
                    f"{agent['id']} depende de agente desconhecido: {sorted(unknown)}"
                )
            if agent["id"] in agent["depends_on"]:
                errors.append(f"{agent['id']} depende de si próprio")

    approvals = set(manifest.get("human_approval_required", []))
    missing_approvals = REQUIRED_APPROVALS - approvals
    if missing_approvals:
        errors.append(f"aprovações humanas ausentes: {sorted(missing_approvals)}")

    global_blocks = set(manifest.get("global_forbidden_actions", []))
    missing_blocks = REQUIRED_GLOBAL_BLOCKS - global_blocks
    if missing_blocks:
        errors.append(f"bloqueios globais ausentes: {sorted(missing_blocks)}")

    gates = manifest.get("quality_gates", [])
    gate_owners = {gate.get("owner") for gate in gates if isinstance(gate, dict)}
    if "human" not in gate_owners:
        errors.append("gate final humano ausente")

    schema_path = root / manifest.get("handoff_schema", "")
    if not schema_path.is_file():
        errors.append("schema de handoff inexistente")
    else:
        try:
            json.loads(schema_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"schema de handoff inválido: {exc}")

    return errors


def main() -> int:
    try:
        manifest = load_manifest()
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERRO: não foi possível carregar o manifesto: {exc}")
        return 1

    errors = validate_manifest(manifest)
    if errors:
        for error in errors:
            print(f"ERRO: {error}")
        return 1

    print(f"OK: {len(manifest['agents'])} agentes e contratos validados")
    return 0


if __name__ == "__main__":
    sys.exit(main())

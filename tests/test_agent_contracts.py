import copy
import unittest

from scripts.validate_agents import ROOT, load_manifest, validate_manifest


class AgentContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest = load_manifest()

    def test_manifest_is_valid(self) -> None:
        self.assertEqual([], validate_manifest(self.manifest, ROOT))

    def test_rejects_missing_human_release_gate(self) -> None:
        changed = copy.deepcopy(self.manifest)
        changed["quality_gates"] = [
            gate for gate in changed["quality_gates"] if gate["owner"] != "human"
        ]
        self.assertIn("gate final humano ausente", validate_manifest(changed, ROOT))

    def test_rejects_self_approval_guardrail_removal(self) -> None:
        changed = copy.deepcopy(self.manifest)
        changed["global_forbidden_actions"].remove("self_approve_own_changes")
        errors = validate_manifest(changed, ROOT)
        self.assertTrue(any("self_approve_own_changes" in error for error in errors))

    def test_rejects_unknown_dependency(self) -> None:
        changed = copy.deepcopy(self.manifest)
        changed["agents"][0]["depends_on"] = ["unknown_agent"]
        errors = validate_manifest(changed, ROOT)
        self.assertTrue(any("agente desconhecido" in error for error in errors))


if __name__ == "__main__":
    unittest.main()


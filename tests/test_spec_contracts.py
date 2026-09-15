import copy
import unittest

from scripts.validate_specs import ROOT, load_specs, validate_specs


class SpecContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.specs = load_specs()

    def test_backlog_specs_are_valid(self) -> None:
        self.assertEqual([], validate_specs(self.specs, ROOT))

    def test_rejects_unknown_dependency(self) -> None:
        changed = copy.deepcopy(self.specs)
        changed[-1]["metadata"]["depends_on"].append("SPEC-999")
        self.assertTrue(
            any("dependência desconhecida" in error for error in validate_specs(changed, ROOT))
        )

    def test_rejects_approved_spec_without_human_evidence(self) -> None:
        changed = copy.deepcopy(self.specs)
        changed[0]["metadata"]["status"] = "approved"
        errors = validate_specs(changed, ROOT)
        self.assertTrue(any("aprovação humana" in error for error in errors))

    def test_rejects_duplicate_github_issue(self) -> None:
        changed = copy.deepcopy(self.specs)
        changed[0]["metadata"]["github_issue"] = 42
        changed[1]["metadata"]["github_issue"] = 42
        self.assertIn("github_issue duplicada: 42", validate_specs(changed, ROOT))

    def test_rejects_missing_required_section(self) -> None:
        changed = copy.deepcopy(self.specs)
        changed[0]["content"] = changed[0]["content"].replace(
            "## Objetivo", "## Objetivo removido", 1
        )
        errors = validate_specs(changed, ROOT)
        self.assertTrue(any("seção obrigatória ausente" in error for error in errors))


if __name__ == "__main__":
    unittest.main()

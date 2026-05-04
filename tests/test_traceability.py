import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "test_protocol.md"
MATRIX = ROOT / "openspec" / "changes" / "add-product-sourcing-mvp" / "test-matrix.md"
TASKS = ROOT / "openspec" / "changes" / "add-product-sourcing-mvp" / "tasks.md"


class TraceabilityContractTest(unittest.TestCase):
    def test_every_protocol_case_is_mapped(self):
        protocol = PROTOCOL.read_text(encoding="utf-8")
        matrix = MATRIX.read_text(encoding="utf-8")

        cases = sorted(set(re.findall(r"TC-E2E-(?:\d{3}|ACCEPTANCE-\d{3})", protocol)))
        self.assertGreater(len(cases), 0, "test_protocol.md must define TC-E2E cases")

        missing = [case for case in cases if case not in matrix]
        self.assertEqual([], missing, f"Missing test-matrix mappings: {missing}")

    def test_tasks_enforce_tdd_before_implementation(self):
        tasks = TASKS.read_text(encoding="utf-8")

        self.assertIn("TDD Ground Rules", tasks)
        self.assertRegex(tasks, r"failing automated test\s+before writing production code")
        self.assertIn("test_protocol.md", tasks)


if __name__ == "__main__":
    unittest.main()

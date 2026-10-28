"""부모 문서(X.md + X/)의 전략 속성 면제 시험."""

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from _audit_core import WARNING  # noqa: E402
from audit_frontmatter import check_strategy_fields  # noqa: E402

FM = "---\ndate created: 2026-01-01\ndate modified: 2026-01-01\ntags:\n  - test\n---\n"
STRATEGY_FM = (
    "---\ndate created: 2026-01-01\ndate modified: 2026-01-01\ntags:\n  - test\n"
    "importance: 중\nurgency: 중\n---\n"
)
S = "epistemic-structure/strategy"


class StrategyParentTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name).resolve()
        self.write(S + "/AGENTS.md", FM)

    def write(self, rel, text):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")

    def paths(self):
        return [f.path for f in check_strategy_fields(self.root)]

    def test_parent_document_exempt(self):
        self.write(S + "/lessons.md", FM)
        self.write(S + "/lessons/AGENTS.md", FM)
        self.write(S + "/lessons/a.md", STRATEGY_FM)
        self.assertEqual(self.paths(), [])

    def test_document_without_folder_still_warns(self):
        self.write(S + "/plan.md", FM)
        found = check_strategy_fields(self.root)
        self.assertEqual([f.severity for f in found], [WARNING, WARNING])
        self.assertEqual({f.path for f in found}, {S + "/plan.md"})

    def test_same_name_file_is_not_folder(self):
        # 같은 이름의 폴더가 아니라 파일이면 부모 문서가 아니다.
        self.write(S + "/plan.md", FM)
        self.write(S + "/plan", "x\n")
        self.assertEqual(set(self.paths()), {S + "/plan.md"})


if __name__ == "__main__":
    unittest.main()

"""부모 문서(X.md + X/)의 전략 속성 면제와 분류 폴더의 부모 문서 누락 검출 시험."""

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from _audit_core import WARNING  # noqa: E402
from audit_frontmatter import check_strategy_fields  # noqa: E402
from audit_structure import check_parent_documents  # noqa: E402

FM = "---\ndate created: 2026-01-01\ndate modified: 2026-01-01\ntags:\n  - test\n---\n"
STRATEGY_FM = (
    "---\ndate created: 2026-01-01\ndate modified: 2026-01-01\ntags:\n  - test\n"
    "importance: 중\nurgency: 중\n---\n"
)
S = "epistemic-structure/strategy"
K = "epistemic-structure/knowledge"
DECL = '".":\n  structure: 날짜순\n'


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


class ParentDocMissingTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name).resolve()
        self.write("AGENTS.md", FM)
        self.write("epistemic-structure/AGENTS.md", FM)
        self.write("epistemic-structure/AGENTS/epistemic-rules.md", FM)
        self.write("epistemic-structure/knowledge.md", FM)
        self.write(K + "/AGENTS.md", FM)

    def write(self, rel, text):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")

    def found(self):
        return [(f.severity, f.category, f.path)
                for f in check_parent_documents(self.root)]

    def test_category_with_parent_clean(self):
        self.assertEqual(self.found(), [])

    def test_category_without_parent_warns(self):
        (self.root / "epistemic-structure/knowledge.md").unlink()
        self.assertEqual(self.found(), [(WARNING, "parent-doc", K)])

    def test_classification_folder_without_parent_warns(self):
        self.write(K + "/topic/AGENTS.md", FM)
        self.write(K + "/topic/a.md", FM)
        self.assertEqual(self.found(), [(WARNING, "parent-doc", K + "/topic")])

    def test_classification_folder_with_parent_clean(self):
        self.write(K + "/topic.md", FM)
        self.write(K + "/topic/AGENTS.md", FM)
        self.write(K + "/topic/a.md", FM)
        self.assertEqual(self.found(), [])

    def test_nested_recursion(self):
        self.write(K + "/topic.md", FM)
        self.write(K + "/topic/AGENTS.md", FM)
        self.write(K + "/topic/sub/AGENTS.md", FM)
        self.assertEqual(self.found(),
                         [(WARNING, "parent-doc", K + "/topic/sub")])

    def test_folder_without_descriptor_not_reported(self):
        # 디스크립터 누락은 디스크립터 검사가 위반으로 낸다.
        self.write(K + "/topic/a.md", FM)
        self.assertEqual(self.found(), [])

    def test_sequential_top_and_descendants_exempt(self):
        self.write(K + "/daily/AGENTS.md", FM)
        self.write(K + "/daily/INDEX.yaml", DECL)
        self.write(K + "/daily/2026-05/AGENTS.md", FM)
        self.write(K + "/daily/2026-05/x.md", FM)
        self.assertEqual(self.found(), [])

    def test_norms_folder_exempt(self):
        self.write(K + "/AGENTS/epistemic-rules.md", FM)
        self.assertEqual(self.found(), [])

    def test_outside_epistemic_structure_not_checked(self):
        self.write("worklog/AGENTS.md", FM)
        self.write("worklog/archive/AGENTS.md", FM)
        self.write("implementation/AGENTS.md", FM)
        self.assertEqual(self.found(), [])

    def test_epistemic_structure_itself_not_checked(self):
        self.assertFalse((self.root / "epistemic-structure.md").exists())
        self.assertEqual(self.found(), [])


if __name__ == "__main__":
    unittest.main()

"""규범 폴더 예외, CLAUDE.md 포인터, `@` 가져오기 검사 시험."""

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from _audit_core import VIOLATION, WARNING  # noqa: E402
from audit_frontmatter import check_front_matter  # noqa: E402
from audit_links import check_imports  # noqa: E402
from audit_structure import (  # noqa: E402
    check_claude_pointers, check_descriptors, check_empty_folders, check_name_collision,
    check_norms_dir_descriptors,
)

FM = "---\ndate created: 2026-01-01\ndate modified: 2026-01-01\ntags:\n  - test\n---\n"


class NormsDirTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name).resolve()
        self.write("AGENTS.md", FM)
        self.write("CLAUDE.md", "@AGENTS.md\n")
        self.write("AGENTS/epistemic-rules.md", FM)
        self.write("AGENTS/epistemic-rules/x.md", FM)
        self.write("worklog/AGENTS.md", FM)
        self.write("worklog/CLAUDE.md", "@AGENTS.md\n")
        self.write("worklog/STATUS.md", FM)

    def write(self, rel, text):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")

    def test_norms_dir_needs_no_descriptor(self):
        self.assertEqual([f for f in check_descriptors(self.root) if f.path.startswith("AGENTS")], [])

    def test_content_dir_still_needs_descriptor(self):
        (self.root / "worklog/AGENTS.md").unlink()
        self.assertEqual([(f.severity, f.path) for f in check_descriptors(self.root)], [(VIOLATION, "worklog")])

    def test_norms_dir_descriptors_forbidden(self):
        self.write("AGENTS/epistemic-rules/AGENTS.md", FM)
        self.write("AGENTS/CLAUDE.md", "@AGENTS.md\n")
        found = check_norms_dir_descriptors(self.root)
        self.assertEqual(
            sorted((f.severity, f.path) for f in found),
            [(VIOLATION, "AGENTS/CLAUDE.md"), (VIOLATION, "AGENTS/epistemic-rules/AGENTS.md")],
        )
        (self.root / "AGENTS/epistemic-rules/AGENTS.md").unlink()
        (self.root / "AGENTS/CLAUDE.md").unlink()
        self.assertEqual(check_norms_dir_descriptors(self.root), [])

    def test_claude_pointer_missing_warns(self):
        (self.root / "worklog/CLAUDE.md").unlink()
        self.assertEqual([f.path for f in check_claude_pointers(self.root)], ["worklog"])

    def test_claude_pointer_content(self):
        self.write("worklog/CLAUDE.md", "AGENTS.md를 먼저 읽을 것.\n")
        self.assertEqual(len(check_claude_pointers(self.root)), 1)

    def test_import_target_missing(self):
        self.write("AGENTS/epistemic-rules.md", FM + "@AGENTS/epistemic-rules/x.md\n")
        self.assertEqual([f.severity for f in check_imports(self.root)], [VIOLATION])

    def test_import_relative_ok(self):
        self.write("AGENTS/epistemic-rules.md", FM + "@epistemic-rules/x.md\n")
        self.assertEqual(check_imports(self.root), [])

    def test_import_in_bundle_detail_warns(self):
        self.write("AGENTS/epistemic-rules/x.md", FM + "@../epistemic-rules.md\n")
        self.assertEqual([f.severity for f in check_imports(self.root)], [WARNING])

    def test_import_in_code_fence_ignored(self):
        self.write("AGENTS.md", FM + "```\n@nope.md\n```\n")
        self.assertEqual(check_imports(self.root), [])

    def test_empty_folder_ignores_pointer_and_norms(self):
        for rel in ("foo/AGENTS.md", "foo/CLAUDE.md", "foo/AGENTS/r.md"):
            self.write(rel, FM)
        self.assertIn("foo", [f.path for f in check_empty_folders(self.root)])

    def test_name_collision_counts_non_md(self):
        self.write("AGENTS/epistemic-rules/tools.md", FM)
        self.write("AGENTS/epistemic-rules/tools/a.py", "")
        self.assertEqual(check_name_collision(self.root), [])

    def test_reference_norms_audited(self):
        self.write("reference/AGENTS.md", FM)
        self.write("reference/AGENTS/epistemic-rules.md", "본문만\n")
        self.assertIn("reference/AGENTS/epistemic-rules.md", [f.path for f in check_front_matter(self.root)])


if __name__ == "__main__":
    unittest.main()

"""순차 분류 하위의 디스크립터, 포인터 면제 시험."""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from _audit_core import (  # noqa: E402
    VIOLATION, WARNING, content_dirs, in_norms_dir)
from _index_core import (  # noqa: E402
    IndexFormatError, index_dirs, sequential_tops, under_sequential)
from audit_structure import (  # noqa: E402
    check_claude_pointers, check_descriptors)

FM = "---\ndate created: 2026-01-01\ndate modified: 2026-01-01\ntags:\n  - test\n---\n"
DECL = '".":\n  structure: 날짜순\n'


class SequentialTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name).resolve()
        self.write("AGENTS.md", FM)
        self.write("CLAUDE.md", "@AGENTS.md\n")
        self.write("s/AGENTS.md", FM)
        self.write("s/CLAUDE.md", "@AGENTS.md\n")
        self.write("s/INDEX.yaml", DECL)
        for i in range(30):
            self.write("s/2026-05/d%02d.md" % i, FM)

    def write(self, rel, text):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")

    def audit(self):
        return check_descriptors(self.root) + check_claude_pointers(self.root)

    def under(self, rel):
        return [f for f in self.audit() if f.path.startswith(rel)]

    def test_subfolder_exempt(self):
        found = [f for f in self.audit() if f.path.startswith("s/2026")]
        self.assertEqual(found, [])

    def test_whole_tree_clean(self):
        self.assertEqual(self.audit(), [])

    def test_leftover_descriptor_warns(self):
        self.write("s/2026-06/AGENTS.md", FM)
        self.write("s/2026-06/CLAUDE.md", "@AGENTS.md\n")
        found = [f for f in self.audit() if f.path.startswith("s/2026-06")]
        self.assertEqual([f.severity for f in found], [WARNING, WARNING])
        self.assertEqual({f.category for f in found}, {"descriptor"})
        self.assertEqual(
            sorted(f.path for f in found),
            ["s/2026-06/AGENTS.md", "s/2026-06/CLAUDE.md"])

    def test_leftover_claude_only_warns(self):
        self.write("s/2026-06/CLAUDE.md", "@AGENTS.md\n")
        self.write("s/2026-06/x.md", FM)
        found = self.under("s/2026-06")
        self.assertEqual([f.severity for f in found], [WARNING])

    def test_deep_descendant_exempt(self):
        self.write("s/2026-05/a/b/x.md", FM)
        self.write("s/2026-05/a/b/AGENTS.md", FM)
        found = self.under("s/2026-05")
        self.assertEqual([f.path for f in found], ["s/2026-05/a/b/AGENTS.md"])

    def test_top_without_descriptor_not_exempting(self):
        (self.root / "s/AGENTS.md").unlink()
        (self.root / "s/CLAUDE.md").unlink()
        # 디스크립터 없는 폴더는 색인 대상이 아니라 최상위가 아니다.
        found = [(f.severity, f.path) for f in self.audit()]
        self.assertIn((VIOLATION, "s"), found)
        self.assertIn((VIOLATION, "s/2026-05"), found)

    def test_top_pointer_still_checked(self):
        self.write("s/CLAUDE.md", "x\n")
        found = [(f.severity, f.category) for f in self.audit()]
        self.assertEqual(found, [(WARNING, "claude-pointer")])

    def test_undeclared_still_required(self):
        (self.root / "s/INDEX.yaml").unlink()
        self.assertIn(VIOLATION, [f.severity for f in self.audit()])

    def test_broken_declaration_not_exempt(self):
        self.write("s/INDEX.yaml", '".":\n  structure: ""\n')
        self.assertEqual(sequential_tops(self.root, strict=False), [])
        self.assertIn(VIOLATION, [f.severity for f in self.audit()])

    def test_broken_declaration_strict_raises(self):
        self.write("s/INDEX.yaml", '".":\n  structure: ""\n')
        with self.assertRaises(IndexFormatError):
            sequential_tops(self.root)

    def test_top_without_descriptor_not_top(self):
        (self.root / "s/AGENTS.md").unlink()
        self.assertEqual(sequential_tops(self.root), [])

    def test_nested_declaration_not_second_top(self):
        self.write("s/2026-05/INDEX.yaml", DECL)
        self.write("s/2026-05/AGENTS.md", FM)
        self.assertEqual(sequential_tops(self.root), [self.root / "s"])

    def test_norms_dir_not_top(self):
        self.write("AGENTS/INDEX.yaml", DECL)
        self.assertEqual(sequential_tops(self.root), [self.root / "s"])

    def test_reference_subfolder_not_top(self):
        self.write("reference/r/AGENTS.md", FM)
        self.write("reference/r/INDEX.yaml", DECL)
        self.assertEqual(sequential_tops(self.root), [self.root / "s"])

    def test_under_sequential(self):
        tops = sequential_tops(self.root)
        self.assertTrue(under_sequential(self.root / "s/2026-05", tops))
        self.assertFalse(under_sequential(self.root / "s", tops))
        self.assertFalse(under_sequential(self.root, tops))

    def test_exemption_matches_index_dirs(self):
        # 순차 분류 최상위 s 아래에 AGENTS.md가 남은 자손 폴더를 만들어
        # 아래 루프가 실제로 돌게 한다.
        self.write("s/2026-07/AGENTS.md", FM)
        tops = sequential_tops(self.root)
        self.assertTrue(tops)
        indexed = set(index_dirs(self.root))
        checked = 0
        for d in content_dirs(self.root):
            if (d / "AGENTS.md").is_file() and d not in indexed:
                checked += 1
                self.assertTrue(under_sequential(d, tops)
                                or in_norms_dir(self.root, d))
        self.assertGreaterEqual(checked, 1)

    def test_audit_exemption_follows_sequential_tops(self):
        # 감사가 면제를 sequential_tops에서 얻는지 고정한다. 면제 집합이
        # 비면 s/2026-05는 디스크립터 누락 위반을 낸다.
        self.assertEqual(self.under("s/2026-05"), [])
        with mock.patch("audit_structure.sequential_tops", return_value=[]):
            self.assertIn(VIOLATION,
                          [f.severity for f in self.under("s/2026-05")])


if __name__ == "__main__":
    unittest.main()

"""링크 표시텍스트-대상 정합 검사(항목 17) 시험."""

import os
import sys
import tempfile
import unicodedata
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from audit_links import check_link_text  # noqa: E402

FM = "---\ndate created: 2026-01-01\ndate modified: 2026-01-01\ntags: [x]\n---\n"


class LinkTextTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        for rel in ("a/x.md", "a/y.md", "b/z.md", "q/p/e.md"):
            self.write(rel)

    def tearDown(self):
        self._tmp.cleanup()

    def write(self, rel, body=""):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(FM + "\n# t\n\n" + body, encoding="utf-8")

    def link(self, src, disp, target):
        self.write(src, f"[{disp}]({target})\n")
        return len(check_link_text(self.root))

    def test_basename(self):
        self.assertEqual(self.link("b/z.md", "x.md", "../a/x.md"), 0)

    def test_root_path(self):
        self.assertEqual(self.link("b/z.md", "a/x.md", "../a/x.md"), 0)

    def test_target_verbatim(self):
        self.assertEqual(self.link("b/z.md", "../a/x.md", "../a/x.md"), 0)

    def test_target_suffix(self):
        # 대상 경로의 끝부분. 루트나 문서 기준으로는 없는 경로다.
        self.assertEqual(self.link("b/z.md", "p/e.md", "../q/p/e.md"), 0)

    def test_resolved_target_suffix(self):
        # 링크 문자열(e.md)에는 없고 해석된 대상
        # q/p/e.md의 끝부분에만 있는 형태다.
        self.write("q/p/x.md")
        self.assertEqual(self.link("q/p/x.md", "p/e.md", "e.md"), 0)

    def test_resolved_target_stale_prefix_violation(self):
        self.write("q/p/x.md")
        self.assertEqual(self.link("q/p/x.md", "old/p/e.md", "e.md"), 1)

    def test_folder(self):
        self.write("a/AGENTS.md")
        self.assertEqual(self.link("b/z.md", "a/", "../a/AGENTS.md"), 0)

    def test_nfc_basename(self):
        name = "가.md"
        self.write("a/" + name)
        disp = unicodedata.normalize("NFD", name)
        self.assertEqual(self.link("b/z.md", disp, "../a/" + name), 0)

    def test_stale_prefix_violation(self):
        self.assertEqual(self.link("b/z.md", "old/x.md", "../a/x.md"), 1)

    def test_other_existing_file_violation(self):
        self.assertEqual(self.link("b/z.md", "../a/y.md", "../a/x.md"), 1)

    def test_other_basename_violation(self):
        self.assertEqual(self.link("b/z.md", "y.md", "../a/x.md"), 1)

    def test_parent_step_suffix_violation(self):
        # 끝부분 형태는 . 과 .. 를 받지 않는다.
        self.assertEqual(self.link("b/z.md", "p/../p/e.md", "../q/p/e.md"), 1)


if __name__ == "__main__":
    unittest.main()

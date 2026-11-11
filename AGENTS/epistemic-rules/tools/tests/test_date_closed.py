"""date closed가 히스토리 문서에만 달리는지 보는 검사(항목 4) 시험."""

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from audit_frontmatter import check_front_matter  # noqa: E402

FM = "---\ndate created: 2026-01-01\ndate modified: 2026-01-01\n{closed}tags: [x]\n---\n\n# t\n"


class DateClosedTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def closed_findings(self, rel, closed=True):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(FM.format(closed="date closed: 2026-01-02\n" if closed else ""), encoding="utf-8")
        return [f for f in check_front_matter(self.root)
                if f.path == rel and "date closed" in f.message and "프리픽스" in f.message]

    def test_dated_file(self):
        self.assertEqual(self.closed_findings("s/2026-01-01 사안.md"), [])

    def test_child_of_dated_folder(self):
        # 날짜 프리픽스 문서를 나눈 하위 문서는 날짜 폴더 아래 프리픽스 없이 둔다.
        self.assertEqual(self.closed_findings("s/2026-01-01 사안/세부.md"), [])
        self.assertEqual(self.closed_findings("s/2026-01-01 사안/a/세부.md"), [])

    def test_current_document_violation(self):
        self.assertEqual(len(self.closed_findings("s/현재.md")), 1)
        self.assertEqual(len(self.closed_findings("s/폴더/현재.md")), 1)


if __name__ == "__main__":
    unittest.main()

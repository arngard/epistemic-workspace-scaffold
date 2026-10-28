"""감사 순회 범위 시험: 등재한 진척 기록 폴더."""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOLS)

from _audit_core import (  # noqa: E402
    VIOLATION, iter_md_files, registered_progress_dirs)
from audit_frontmatter import check_front_matter  # noqa: E402

FM = "---\ndate created: 2026-01-01\ndate modified: 2026-01-01\ntags:\n  - test\n---\n"

# 자손 디스크립터에서 흔한 꼴: 등재 경로와 git 경로지정 예시가 한 항목에 같이 있다.
REGISTRY = FM + """
# `reference/` 디스크립터

덮어쓰기와 보태기 목록:

- 진척 기록 폴더의 원본 불변 점검 제외: 상류 규범에 보탠다. 진척 기록 폴더
  `reference/src/AGENTS/`를 점검에서 뺀다. 경로지정에
  `":(exclude)reference/src/AGENTS/"`를 더한다.
- 다른 항목: `reference/AGENTS/`는 규범 폴더다.

```text
`reference/fenced/AGENTS/`
```
"""


class ProgressRegistryTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name).resolve()
        self.write("AGENTS.md", FM)
        self.write("reference/AGENTS.md", REGISTRY)
        self.write("reference/src/data.md", "raw\n")
        self.write("reference/src/AGENTS/points.md", FM)
        self.write("reference/other/AGENTS/points.md", "no front matter\n")

    def write(self, rel, text):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")

    def rels(self):
        return {p.relative_to(self.root).as_posix() for p in iter_md_files(self.root)}

    def test_registry_parsed(self):
        self.assertEqual(registered_progress_dirs(self.root), ("reference/src/AGENTS/",))

    def test_norms_folder_and_nested_agents_not_registered(self):
        self.write("reference/AGENTS.md", FM + "`reference/AGENTS/`\n`reference/AGENTS/x/AGENTS/`\n")
        self.assertEqual(registered_progress_dirs(self.root), ())

    def test_deep_material_folder(self):
        self.write("reference/AGENTS.md", FM + "- `reference/a/b/AGENTS/`\n")
        self.assertEqual(registered_progress_dirs(self.root), ("reference/a/b/AGENTS/",))

    def test_without_descriptor(self):
        (self.root / "reference/AGENTS.md").unlink()
        self.assertEqual(registered_progress_dirs(self.root), ())

    def test_registered_progress_audited(self):
        rels = self.rels()
        self.assertIn("reference/src/AGENTS/points.md", rels)
        self.assertNotIn("reference/src/data.md", rels)
        self.assertNotIn("reference/other/AGENTS/points.md", rels)

    def test_registered_progress_front_matter_checked(self):
        self.write("reference/src/AGENTS/bad.md", "no front matter\n")
        found = [(f.severity, f.path) for f in check_front_matter(self.root)]
        self.assertIn((VIOLATION, "reference/src/AGENTS/bad.md"), found)
        self.assertNotIn((VIOLATION, "reference/other/AGENTS/points.md"), found)

    def test_cli_lists_registered_folders(self):
        r = subprocess.run(
            [sys.executable, "-B", os.path.join(TOOLS, "audit.py"),
             "--progress-folders", str(self.root)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(r.returncode, 0, r.stderr.decode("utf-8"))
        self.assertEqual(r.stdout.decode("utf-8").splitlines(), ["reference/src/AGENTS/"])

    def test_cli_empty_registry(self):
        (self.root / "reference/AGENTS.md").unlink()
        r = subprocess.run(
            [sys.executable, "-B", os.path.join(TOOLS, "audit.py"),
             "--progress-folders", str(self.root)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout, b"")


if __name__ == "__main__":
    unittest.main()

"""감사 순회 범위 시험: 등재한 진척 기록 폴더와 git 무시 경로."""

import os
import shutil
import subprocess
import sys
import tempfile
import unicodedata
import unittest
from pathlib import Path

TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOLS)

from _audit_core import (  # noqa: E402
    VIOLATION, WARNING, content_dirs, git_ignored_paths, iter_md_files,
    registered_progress_dirs)
from audit_frontmatter import check_front_matter  # noqa: E402
from audit_structure import check_descriptors, check_empty_folders  # noqa: E402

HAS_GIT = shutil.which("git") is not None

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


def clean_env(home):
    """바깥 git 설정과 훅 환경 변수가 임시 저장소에 새지 않게 한다."""
    env = dict(os.environ)
    for k in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_PREFIX",
              "GIT_COMMON_DIR", "GIT_OBJECT_DIRECTORY",
              "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_CONFIG"):
        env.pop(k, None)
    env["HOME"] = str(home)
    env["XDG_CONFIG_HOME"] = str(home)
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    return env


class GitScopeBase(unittest.TestCase):
    """시험마다 새 루트를 쓴다. 무시 경로는 루트별로 한 번만 읽어 둔다."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.base = Path(self._tmp.name)
        self.env = clean_env(self.base)
        old = dict(os.environ)
        os.environ.clear()
        os.environ.update(self.env)
        self.addCleanup(lambda: (os.environ.clear(), os.environ.update(old)))

    def git(self, cwd, *args):
        subprocess.run(["git", *args], cwd=str(cwd), env=self.env, check=True,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def write(self, root, rel, text):
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")

    def workspace(self, root):
        self.write(root, "AGENTS.md", FM)
        self.write(root, ".gitignore", ".sp/\n*.log\nbuild/\n")
        self.write(root, ".sp/notes.md", "no front matter\n")
        self.write(root, "docs/AGENTS.md", FM)
        self.write(root, "docs/new.md", "no front matter\n")

    def front_matter_paths(self, root):
        return {f.path for f in check_front_matter(root)
                if f.severity == VIOLATION}


@unittest.skipIf(not HAS_GIT, "git 없음")
class GitIgnoredScopeTest(GitScopeBase):
    def setUp(self):
        super().setUp()
        root = self.base / "repo"
        root.mkdir()
        self.root = root.resolve()
        self.git(self.root, "init", "-q")
        self.workspace(self.root)

    def test_ignored_folder_skipped(self):
        paths = self.front_matter_paths(self.root)
        self.assertNotIn(".sp/notes.md", paths)
        dirs = {d.relative_to(self.root).as_posix() for d in content_dirs(self.root)
                if d != self.root}
        self.assertNotIn(".sp", dirs)
        self.assertNotIn(".sp", {f.path for f in check_descriptors(self.root)})

    def test_untracked_not_ignored_checked(self):
        self.assertIn("docs/new.md", self.front_matter_paths(self.root))

    def test_tracked_file_under_ignore_pattern_checked(self):
        self.write(self.root, "build/kept.md", "no front matter\n")
        self.write(self.root, "build/other.md", "no front matter\n")
        self.git(self.root, "add", "-f", "build/kept.md")
        paths = self.front_matter_paths(self.root)
        self.assertIn("build/kept.md", paths)
        self.assertNotIn("build/other.md", paths)

    def test_ignored_paths_listed(self):
        self.write(self.root, "docs/run.log", "x\n")
        ignored = git_ignored_paths(self.root)
        self.assertIn(".sp", ignored)
        self.assertIn("docs/run.log", ignored)
        self.assertNotIn("docs/new.md", ignored)

    def test_ignored_entry_not_content(self):
        # 무시 파일만 남은 폴더는 저장소에서 비어 있다.
        self.write(self.root, "docs/empty/AGENTS.md", FM)
        self.write(self.root, "docs/empty/CLAUDE.md", "@AGENTS.md\n")
        self.write(self.root, "docs/empty/run.log", "x\n")
        found = [(f.severity, f.path) for f in check_empty_folders(self.root)]
        self.assertIn((WARNING, "docs/empty"), found)

    def test_nfd_folder_name_nfc_pattern(self):
        name = "\ube44\ubc00"
        nfd = unicodedata.normalize("NFD", name)
        self.git(self.root, "config", "core.precomposeunicode", "true")
        self.write(self.root, ".gitignore", name + "/\n")
        folder = self.root / nfd
        folder.mkdir()
        if nfd not in os.listdir(str(self.root)):
            self.skipTest("NFD 이름을 그대로 둘 수 없는 파일시스템")
        (folder / "x.md").write_text("no front matter\n", encoding="utf-8")
        paths = {unicodedata.normalize("NFC", p) for p in self.front_matter_paths(self.root)}
        self.assertNotIn(name + "/x.md", paths)


@unittest.skipIf(not HAS_GIT, "git 없음")
class GitFallbackTest(GitScopeBase):
    def test_not_a_repository(self):
        root = (self.base / "plain")
        root.mkdir()
        root = root.resolve()
        self.workspace(root)
        self.assertEqual(git_ignored_paths(root), frozenset())
        self.assertIn(".sp/notes.md", self.front_matter_paths(root))

    def test_copy_inside_ignored_folder_of_outer_repo(self):
        # 바깥 저장소의 무시 폴더 안에 둔 사본은 통째로 무시로 판정되지 않는다.
        outer = self.base / "outer"
        outer.mkdir()
        outer = outer.resolve()
        self.git(outer, "init", "-q")
        self.write(outer, ".gitignore", ".tmp/\n")
        root = outer / ".tmp" / "ws"
        root.mkdir(parents=True)
        self.workspace(root)
        paths = self.front_matter_paths(root)
        self.assertIn("docs/new.md", paths)
        self.assertIn(".sp/notes.md", paths)


if __name__ == "__main__":
    unittest.main()

"""build_index 생성 진입점과 커밋 전 훅 시험."""

import contextlib
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unicodedata
import unittest
from pathlib import Path

TOOLS = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, str(TOOLS))

from _bundle_core import MANIFEST_REL  # noqa: E402
from _index_core import INDEX_HEADER  # noqa: E402
from build_index import (  # noqa: E402
    HandWrittenIndexError, build, ignored_entries, main)

FM = "---\ndescription: 문서 설명\n---\n본문\n"
# 손으로 바꾼 생성 쪽(머리말은 남음).
GEN = INDEX_HEADER + "\nx\n"
HAS_GIT = shutil.which("git") is not None


class BuildTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.write("AGENTS.md", FM)
        self.write("CLAUDE.md", "@AGENTS.md\n")
        self.write("AGENTS/epistemic-rules.md", FM)
        self.write("s.md", FM)
        self.write("s/AGENTS.md", FM)
        self.write("s/x.md", FM)
        self.write("LICENSE", "x\n")
        self.write(".hidden", "x\n")
        self.write("INDEX.yaml", '"LICENSE":\n  description: 사용 허가\n')
        self.write("reference/AGENTS.md", FM)
        self.write("reference/r.pdf", "x\n")

    def write(self, name, text):
        p = self.root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        return p

    def run_main(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main([str(self.root), *args])
        return code, out.getvalue(), err.getvalue()

    def test_writes_then_idempotent(self):
        first = build(self.root)
        self.assertIn("INDEX.md", first)
        self.assertEqual(build(self.root), [])

    def test_dry_run_no_write(self):
        self.assertTrue(build(self.root, dry_run=True))
        self.assertFalse((self.root / "INDEX.md").exists())

    def test_surplus_page_removed(self):
        build(self.root)
        self.write("s/INDEX2.md", GEN)
        self.assertEqual(build(self.root), ["s/INDEX2.md"])
        self.assertFalse((self.root / "s/INDEX2.md").exists())

    def test_bad_yaml_exit_2(self):
        self.write("INDEX.yaml", "a:\n")
        code, out, err = self.run_main()
        self.assertEqual(code, 2)
        self.assertFalse((self.root / "INDEX.md").exists())

    def test_returns_sorted_posix_paths(self):
        self.assertEqual(
            build(self.root),
            ["INDEX.md", "reference/INDEX.md", "s/INDEX.md"])

    def test_writes_lf_bytes(self):
        build(self.root)
        data = (self.root / "INDEX.md").read_bytes()
        self.assertNotIn(b"\r", data)
        self.assertTrue(data.endswith(b"\n"))

    def test_changed_page_rewritten_only(self):
        build(self.root)
        self.write("s/INDEX.md", GEN)
        self.assertEqual(build(self.root), ["s/INDEX.md"])

    def test_dry_run_keeps_surplus(self):
        build(self.root)
        self.write("s/INDEX2.md", GEN)
        self.assertEqual(build(self.root, dry_run=True), ["s/INDEX2.md"])
        self.assertTrue((self.root / "s/INDEX2.md").exists())

    def test_surplus_outside_index_dir_kept(self):
        self.write("t/INDEX2.md", "x\n")
        build(self.root)
        self.assertTrue((self.root / "t/INDEX2.md").exists())

    def test_sequential_declaration_removes_stale_pages(self):
        self.write("s/t/AGENTS.md", FM)
        build(self.root)
        self.assertTrue((self.root / "s/t/INDEX.md").is_file())
        self.write("s/INDEX.yaml", '".":\n  structure: 날짜순\n')
        self.assertIn("s/t/INDEX.md", build(self.root))
        self.assertFalse((self.root / "s/t/INDEX.md").exists())
        self.assertEqual(build(self.root), [])

    def test_removed_descriptor_removes_stale_pages(self):
        build(self.root)
        self.write("s/INDEX2.md", GEN)
        (self.root / "s/AGENTS.md").unlink()
        changed = build(self.root)
        self.assertIn("s/INDEX.md", changed)
        self.assertIn("s/INDEX2.md", changed)
        self.assertFalse((self.root / "s/INDEX.md").exists())
        self.assertFalse((self.root / "s/INDEX2.md").exists())

    def test_stale_page_dry_run_kept(self):
        build(self.root)
        (self.root / "s/AGENTS.md").unlink()
        self.assertIn("s/INDEX.md", build(self.root, dry_run=True))
        self.assertTrue((self.root / "s/INDEX.md").exists())

    def test_reference_subfolder_generated_page_kept(self):
        self.write("reference/raw/INDEX.md", GEN)
        self.write("reference/raw/AGENTS/INDEX.md", GEN)
        build(self.root)
        self.assertTrue((self.root / "reference/raw/INDEX.md").exists())
        self.assertTrue((self.root / "reference/raw/AGENTS/INDEX.md").exists())

    def test_hand_written_index_refused(self):
        self.write("s/INDEX.md", "# 내 색인\n")
        self.write("s/INDEX2.md", "# 내 둘째 쪽\n")
        for extra in ((), ("--dry-run",)):
            code, out, err = self.run_main(*extra)
            self.assertEqual((code, out), (2, ""))
            self.assertIn(" s/INDEX.md: ", err)
            self.assertIn(" s/INDEX2.md: ", err)
        self.assertFalse((self.root / "INDEX.md").exists())
        self.assertEqual((self.root / "s/INDEX.md").read_text(encoding="utf-8"),
                         "# 내 색인\n")
        self.assertTrue((self.root / "s/INDEX2.md").exists())
        with self.assertRaises(HandWrittenIndexError):
            build(self.root)

    def test_embedded_clone_not_entry(self):
        self.write("s/clone/.git/HEAD", "ref: refs/heads/main\n")
        self.write("s/clone/a.txt", "x\n")
        self.write("s/sub/.git", "gitdir: x\n")
        build(self.root)
        text = (self.root / "s/INDEX.md").read_text(encoding="utf-8")
        self.assertNotIn("clone", text)
        self.assertIn("[sub/](sub/)", text)
        self.assertFalse((self.root / "s/clone/INDEX.md").exists())
        self.assertFalse((self.root / "s/sub/INDEX.md").exists())

    def test_main_prints_paths(self):
        code, out, err = self.run_main()
        self.assertEqual(code, 0)
        self.assertEqual(out.splitlines(),
                         ["INDEX.md", "reference/INDEX.md", "s/INDEX.md"])
        code, out, err = self.run_main()
        self.assertEqual((code, out), (0, ""))

    def test_main_dry_run(self):
        code, out, err = self.run_main("--dry-run")
        self.assertEqual(code, 0)
        self.assertIn("INDEX.md", out.splitlines())
        self.assertFalse((self.root / "INDEX.md").exists())

    def test_bad_yaml_reports_file_and_line(self):
        self.write("s/INDEX.yaml", '"x.md":\n  description: ok\nbad\n')
        code, out, err = self.run_main()
        self.assertEqual(code, 2)
        self.assertIn(" s/INDEX.yaml:3: ", err)
        self.assertNotIn(str(self.root), err)
        self.assertFalse((self.root / "INDEX.md").exists())

    def test_not_a_directory_exit_2(self):
        code, out, err = self.run_main_path(self.root / "LICENSE")
        self.assertEqual(code, 2)

    def run_main_path(self, path):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            return main([str(path)]), "", err.getvalue()

    def test_ignored_entries_without_git_repo(self):
        self.assertEqual(ignored_entries(self.root, [self.root / "LICENSE"]),
                         [])


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


@unittest.skipIf(not HAS_GIT, "git 없음")
class IgnoredEntriesTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "repo"
        self.root.mkdir()
        self.env = clean_env(self._tmp.name)
        subprocess.run(["git", "init", "-q"], cwd=str(self.root),
                       env=self.env, check=True)

    def test_reports_ignored(self):
        (self.root / ".gitignore").write_text("secret.txt\n", encoding="utf-8")
        (self.root / "secret.txt").write_text("x\n", encoding="utf-8")
        (self.root / "a b.md").write_text("x\n", encoding="utf-8")
        paths = [self.root / "secret.txt", self.root / "a b.md"]
        old = dict(os.environ)
        try:
            os.environ.clear()
            os.environ.update(self.env)
            self.assertEqual(ignored_entries(self.root, paths), ["secret.txt"])
            self.assertEqual(ignored_entries(self.root, []), [])
        finally:
            os.environ.clear()
            os.environ.update(old)

    def with_env(self):
        old = dict(os.environ)
        os.environ.clear()
        os.environ.update(self.env)
        self.addCleanup(lambda: (os.environ.clear(), os.environ.update(old)))

    def run_main(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main([str(self.root)])
        return code, out.getvalue(), err.getvalue()

    def test_ignored_embedded_clone_builds(self):
        self.with_env()
        for name in ("AGENTS.md", "implementation/AGENTS.md"):
            p = self.root / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(FM, encoding="utf-8")
        app = self.root / "implementation/app"
        app.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=str(app), env=self.env,
                       check=True)
        (app / "main.py").write_text("x\n", encoding="utf-8")
        (self.root / ".gitignore").write_text("implementation/app/\n",
                                              encoding="utf-8")
        code, out, err = self.run_main()
        self.assertEqual(code, 0, err)
        text = (self.root / "implementation/INDEX.md").read_text(
            encoding="utf-8")
        self.assertNotIn("app", text)

    def test_ignored_gitlink_folder_message(self):
        self.with_env()
        (self.root / "AGENTS.md").write_text(FM, encoding="utf-8")
        sub = self.root / "wt"
        sub.mkdir()
        (sub / ".git").write_text("gitdir: x\n", encoding="utf-8")
        (self.root / ".gitignore").write_text("wt/\n", encoding="utf-8")
        code, out, err = self.run_main()
        self.assertEqual(code, 2)
        self.assertIn("wt: ", err)
        self.assertIn("중첩 저장소", err)
        self.assertNotIn(".tmp/", err)

    def test_nfd_name_nfc_pattern(self):
        name = "\ube44\ubc00.txt"
        nfd = unicodedata.normalize("NFD", name)
        subprocess.run(["git", "config", "core.precomposeunicode", "true"],
                       cwd=str(self.root), env=self.env, check=True)
        (self.root / ".gitignore").write_bytes((name + "\n").encode("utf-8"))
        path = self.root / nfd
        path.write_text("x\n", encoding="utf-8")
        disk = [q.name for q in self.root.iterdir() if q.name != ".gitignore"
                and q.name != ".git"]
        if disk != [nfd]:
            self.skipTest("NFD 이름을 그대로 둘 수 없는 파일시스템")
        old = dict(os.environ)
        try:
            os.environ.clear()
            os.environ.update(self.env)
            self.assertEqual(ignored_entries(self.root, [path]), [name])
        finally:
            os.environ.clear()
            os.environ.update(old)


@unittest.skipIf(not HAS_GIT or os.name == "nt", "git, sh")
class HookTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.home = Path(self._tmp.name) / "home"
        self.home.mkdir()
        self.env = clean_env(self.home)
        self.root = Path(self._tmp.name) / "repo"
        self.root.mkdir()
        self.git("init", "-q")
        self.git("config", "user.name", "t")
        self.git("config", "user.email", "t@example.com")
        self.git("config", "commit.gpgsign", "false")
        self.write("AGENTS.md", FM)
        self.write("a.md", FM)

    def write(self, name, text):
        p = self.root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        return p

    def git(self, *args, check=True):
        r = subprocess.run(["git", *args], cwd=str(self.root), env=self.env,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if check and r.returncode != 0:
            self.fail("git %s: %s" % (args, r.stderr.decode("utf-8", "replace")))
        return r.stdout.decode("utf-8")

    def install_tools(self, rel="AGENTS/epistemic-rules/tools"):
        dest = self.root / rel
        shutil.copytree(str(TOOLS), str(dest),
                        ignore=shutil.ignore_patterns("__pycache__"))
        os.chmod(str(dest / "hooks" / "pre-commit"), 0o755)
        self.git("config", "core.hooksPath", rel + "/hooks")
        return dest

    def commit(self, *paths):
        self.git("add", "--", *paths)
        r = subprocess.run(["git", "commit", "-q", "-m", "t"],
                           cwd=str(self.root), env=self.env,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.last_err = r.stderr.decode("utf-8", "replace")
        return r.returncode

    def commit_status(self):
        return self.commit("AGENTS.md", "a.md")

    def committed_names(self):
        self.assertEqual(self.commit_status(), 0, self.last_err)
        return self.git("show", "--name-only", "--format=", "HEAD").split()

    def test_commit_includes_index(self):
        self.install_tools()
        self.assertEqual(self.commit_status(), 0, self.last_err)
        names = self.git("show", "--name-only", "--format=", "HEAD")
        self.assertIn("INDEX.md", names.split())

    def test_hook_outside_root(self):
        sub = self.root / "sub"
        sub.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=str(sub), env=self.env,
                       check=True)
        self.write("sub/AGENTS.md", FM)
        self.install_tools("sub/AGENTS/epistemic-rules/tools")
        self.assertIn("INDEX.md", self.committed_names())
        self.assertTrue((self.root / "INDEX.md").exists())
        self.assertFalse((sub / "INDEX.md").exists())

    def test_ignored_entry_blocks(self):
        self.install_tools()
        self.write(".gitignore", "secret.txt\n")
        self.write("secret.txt", "x\n")
        self.assertNotEqual(self.commit_status(), 0)
        self.assertIn("secret.txt", self.last_err)
        self.assertIn(".tmp/", self.last_err)
        self.assertFalse((self.root / "INDEX.md").exists())

    def test_bad_yaml_blocks(self):
        self.install_tools()
        self.write("INDEX.yaml", "a:\n")
        self.assertNotEqual(self.commit_status(), 0)
        self.assertIn("INDEX.yaml:1", self.last_err)
        self.assertEqual(self.git("rev-list", "--all"), "")

    def test_untracked_surplus_page(self):
        self.install_tools()
        self.write("INDEX2.md", GEN)
        self.assertIn("INDEX.md", self.committed_names())
        self.assertFalse((self.root / "INDEX2.md").exists())

    def test_tracked_surplus_page_removed(self):
        self.write("INDEX2.md", GEN)
        self.assertEqual(self.commit("AGENTS.md", "a.md", "INDEX2.md"), 0)
        self.install_tools()
        self.write("b.md", FM)
        self.assertEqual(self.commit("b.md"), 0, self.last_err)
        tracked = self.git("ls-files").split()
        self.assertNotIn("INDEX2.md", tracked)
        self.assertIn("INDEX.md", tracked)

    def test_second_commit_no_index_change(self):
        self.install_tools()
        self.assertEqual(self.commit_status(), 0, self.last_err)
        self.write("c.txt", "x\n")
        self.assertEqual(self.commit("c.txt"), 0, self.last_err)
        names = self.git("show", "--name-only", "--format=", "HEAD").split()
        self.assertEqual(sorted(names), ["INDEX.md", "c.txt"])
        self.write("a.md", FM + "more\n")
        self.assertEqual(self.commit("a.md"), 0, self.last_err)
        names = self.git("show", "--name-only", "--format=", "HEAD").split()
        self.assertEqual(names, ["a.md"])

    def test_colon_folder_staged(self):
        self.install_tools()
        self.write(":x/AGENTS.md", FM)
        self.write(":x/b.md", FM)
        self.assertEqual(self.commit("AGENTS.md", "a.md", ":(literal):x"), 0,
                         self.last_err)
        names = self.git("show", "--name-only", "--format=", "HEAD").split()
        self.assertIn(":x/INDEX.md", names)

    def test_no_python_blocks(self):
        tools = self.install_tools()
        bindir = Path(self._tmp.name) / "bin"
        bindir.mkdir()
        for name in ("git", "dirname"):
            real = shutil.which(name)
            if real is None:
                self.skipTest(name)
            os.symlink(os.path.realpath(real), str(bindir / name))
        env = dict(self.env)
        env["PATH"] = str(bindir)
        probe = subprocess.run(["git", "--version"], env=env,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if probe.returncode != 0:
            self.skipTest("git이 좁은 PATH에서 돌지 않음")
        r = subprocess.run(["/bin/sh", str(tools / "hooks" / "pre-commit")],
                           cwd=str(self.root), env=env,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(r.returncode, 1)
        self.assertIn("Python 3.9", r.stderr.decode("utf-8", "replace"))
        self.assertFalse((self.root / "INDEX.md").exists())

    def test_hook_does_not_touch_manifest(self):
        tools = self.install_tools()
        self.write("AGENTS/epistemic-rules/x.md", FM)
        subprocess.run(
            [sys.executable, str(tools / "build_index.py"), str(self.root),
             "--bundle-manifest"], env=self.env, check=True,
            stdout=subprocess.PIPE)
        self.assertEqual(self.commit_status(), 0, self.last_err)
        self.assertEqual(
            self.commit(MANIFEST_REL, "AGENTS/epistemic-rules/x.md"), 0,
            self.last_err)
        before = self.git("show", "HEAD:" + MANIFEST_REL)
        self.assertTrue(before)
        self.write("AGENTS/epistemic-rules/x.md", FM + "more\n")
        self.assertEqual(self.commit("AGENTS/epistemic-rules/x.md"), 0,
                         self.last_err)
        names = self.git("show", "--name-only", "--format=", "HEAD").split()
        self.assertNotIn(MANIFEST_REL, names)
        self.assertEqual(self.git("show", "HEAD:" + MANIFEST_REL), before)

    def test_hook_mode_executable_in_git(self):
        repo = TOOLS.parent.parent.parent
        if not (repo / ".git").exists():
            self.skipTest("git 작업 트리 밖")
        r = subprocess.run(
            ["git", "ls-files", "-s", "--",
             "AGENTS/epistemic-rules/tools/hooks/pre-commit"],
            cwd=str(repo), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out = r.stdout.decode("utf-8")
        if not out:
            self.skipTest("훅이 아직 추적되지 않음")
        self.assertTrue(out.startswith("100755 "), out)


if __name__ == "__main__":
    unittest.main()

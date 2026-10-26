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

from build_index import build, ignored_entries, main  # noqa: E402

FM = "---\ndescription: 문서 설명\n---\n본문\n"
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
        self.write("s/INDEX2.md", "x\n")
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
        self.write("s/INDEX.md", "x\n")
        self.assertEqual(build(self.root), ["s/INDEX.md"])

    def test_dry_run_keeps_surplus(self):
        build(self.root)
        self.write("s/INDEX2.md", "x\n")
        self.assertEqual(build(self.root, dry_run=True), ["s/INDEX2.md"])
        self.assertTrue((self.root / "s/INDEX2.md").exists())

    def test_surplus_outside_index_dir_kept(self):
        self.write("t/INDEX2.md", "x\n")
        build(self.root)
        self.assertTrue((self.root / "t/INDEX2.md").exists())

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
        self.write("INDEX2.md", "x\n")
        self.assertIn("INDEX.md", self.committed_names())
        self.assertFalse((self.root / "INDEX2.md").exists())

    def test_tracked_surplus_page_removed(self):
        self.write("INDEX2.md", "x\n")
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

"""build_index 생성 진입점과 커밋 전 훅 시험."""

import contextlib
import io
import os
import shlex
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
# 훅 시험 문서. main 머지에서 훅이 감사를 돌리므로 감사를 통과하는 front matter를 쓴다.
HFM = ("---\ndate created: 2026-01-01\ndate modified: 2026-01-01\n"
       "tags: [규칙]\ndescription: 문서 설명\n---\n\n# 문서\n\n본문\n")


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
        self.assertIn("중첩 레포", err)
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


@unittest.skipIf(not HAS_GIT, "git 없음")
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
        # 머신의 init.defaultBranch와 무관하게 main에서 시작한다.
        self.git("symbolic-ref", "HEAD", "refs/heads/main")
        self.git("config", "user.name", "t")
        self.git("config", "user.email", "t@example.com")
        self.git("config", "commit.gpgsign", "false")
        self.write("AGENTS.md", HFM)
        self.write("a.md", HFM)
        self.write("CLAUDE.md", "@AGENTS.md\n")

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
        for name in ("pre-commit", "pre-merge-commit"):
            os.chmod(str(dest / "hooks" / name), 0o755)
        self.git("config", "core.hooksPath", rel + "/hooks")
        # 복사한 도구만 있는 저장소에 맞게 상류 묶음 목록을 다시 만든다.
        # 출고 목록 그대로면 없는 묶음 파일 때문에 감사가 막는다.
        self.manifest(dest.parent.parent.parent, dest)
        return dest

    def manifest(self, root, tools):
        subprocess.run(
            [sys.executable, str(tools / "build_index.py"), str(root),
             "--bundle-manifest"], env=self.env, check=True,
            stdout=subprocess.PIPE)

    def run_git(self, *args):
        r = subprocess.run(["git", *args], cwd=str(self.root), env=self.env,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.last_err = r.stderr.decode("utf-8", "replace")
        return r.returncode

    def staged(self):
        return self.git("diff", "--cached", "--name-only").split()

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
        self.write("sub/AGENTS.md", HFM)
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
        self.write("b.md", HFM)
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
        self.write("a.md", HFM + "more\n")
        self.assertEqual(self.commit("a.md"), 0, self.last_err)
        names = self.git("show", "--name-only", "--format=", "HEAD").split()
        self.assertEqual(names, ["a.md"])

    @unittest.skipIf(os.name == "nt", "윈도우 파일 이름에 콜론을 쓸 수 없음")
    def test_colon_folder_staged(self):
        self.install_tools()
        self.write(":x/AGENTS.md", HFM)
        self.write(":x/b.md", HFM)
        self.assertEqual(self.commit("AGENTS.md", "a.md", ":(literal):x"), 0,
                         self.last_err)
        names = self.git("show", "--name-only", "--format=", "HEAD").split()
        self.assertIn(":x/INDEX.md", names)

    @unittest.skipIf(os.name == "nt", "/bin/sh와 심볼릭 링크")
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
        x = "AGENTS/epistemic-rules/x.md"
        # 상류 묶음 문서는 tags에 epistemic-rules를 단다.
        xfm = HFM.replace("[규칙]", "[규칙, epistemic-rules]")
        self.write(x, xfm)
        self.manifest(self.root, tools)
        self.assertEqual(self.commit_status(), 0, self.last_err)
        self.assertEqual(self.commit(MANIFEST_REL, x), 0, self.last_err)
        before = self.git("show", "HEAD:" + MANIFEST_REL)
        self.assertTrue(before)
        manifest_disk = (self.root / MANIFEST_REL).read_bytes()
        # 묶음 파일을 바꿔 커밋해도 훅은 목록을 다시 만들지 않는다.
        self.write(x, xfm + "more\n")
        self.assertEqual(self.commit(x), 0, self.last_err)
        self.assertEqual((self.root / MANIFEST_REL).read_bytes(),
                         manifest_disk)
        self.assertEqual(self.git("show", "HEAD:" + MANIFEST_REL), before)

    def test_commit_does_not_audit(self):
        # 일반 커밋은 main에서도 감사하지 않고 색인만 담는다.
        self.install_tools()
        self.write("a.md", "본문\n")
        self.assertIn("INDEX.md", self.committed_names())
        self.assertNotIn("감사 완료", self.last_err)
        self.add_check("a.py", "raise SystemExit(1)\n")
        self.write("b.md", HFM)
        self.assertEqual(self.commit("b.md"), 0, self.last_err)

    def test_audit_error_blocks_with_traceback(self):
        self.branch_with({"b.md": HFM})
        tools = self.root / "AGENTS/epistemic-rules/tools"
        with (tools / "audit_structure.py").open("a", encoding="utf-8") as f:
            f.write("\n\ndef check_filename_portability(root):\n"
                    "    raise RuntimeError('감사 시험 예외')\n")
        self.assertNotEqual(self.merge_side(), 0)
        self.assertIn("Traceback", self.last_err)
        self.assertIn("RuntimeError: 감사 시험 예외", self.last_err)
        self.assertIn("audit failed", self.last_err)
        self.assertIn("종료 코드 3", self.last_err)
        self.assertNotIn("audit violations", self.last_err)

    def test_audit_syntax_error_is_failure(self):
        # 진입 파일의 구문 오류는 Python이 1로 끝내도 위반이 아니라 실행 오류다.
        self.branch_with({"b.md": HFM})
        tools = self.root / "AGENTS/epistemic-rules/tools"
        with (tools / "audit.py").open("a", encoding="utf-8") as f:
            f.write("\ndef (\n")
        self.assertNotEqual(self.merge_side(), 0)
        self.assertIn("SyntaxError", self.last_err)
        self.assertIn("audit failed", self.last_err)
        self.assertNotIn("audit violations", self.last_err)

    def test_warning_passes_with_summary(self):
        warning_root = self.root.with_name("repo's 경고 0건 (")
        self.root.rename(warning_root)
        self.root = warning_root
        self.branch_with({"b.md": HFM})
        tools = self.root / "AGENTS/epistemic-rules/tools"
        self.git("config", "core.hooksPath", (tools / "hooks").as_posix())
        (self.root / "CLAUDE.md").unlink()
        self.assertEqual(self.merge_side(), 0, self.last_err)
        self.assertIn("경고 1건", self.last_err)
        self.assertIn("경고 상세는", self.last_err)
        args = self.detail_args()
        audit_suffix = f"/{warning_root.name}/AGENTS/epistemic-rules/tools/audit.py"
        self.assertTrue(args[-2].endswith(audit_suffix), args)
        self.assertNotIn("WARNING", self.last_err)

    def detail_args(self):
        """경고 상세 명령의 인자. 끝의 두 인자는 감사 스크립트와 루트다."""
        command = self.last_err.split("경고 상세는 ", 1)[1].splitlines()[0]
        args = shlex.split(command[:-len(" 로 본다.")])
        self.assertEqual(args[-3], "-B")
        self.assertEqual(Path(args[-1]).resolve(), self.root.resolve())
        return args

    def test_warning_detail_runs_from_anywhere(self):
        # 상대 경로로 연결한 훅도 어느 폴더에서나 실행할 수 있는 명령을 낸다.
        self.branch_with({"b.md": HFM})
        (self.root / "CLAUDE.md").unlink()
        self.assertEqual(self.merge_side(), 0, self.last_err)
        args = self.detail_args()
        r = subprocess.run(
            [sys.executable, "-B", args[-2], args[-1]], cwd=self._tmp.name,
            env=self.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("claude-pointer", r.stdout.decode("utf-8", "replace"))

    def test_clean_passes_with_summary(self):
        self.branch_with({"b.md": HFM})
        self.assertEqual(self.merge_side(), 0, self.last_err)
        self.assertIn("위반 0건, 경고 0건", self.last_err)
        self.assertNotIn("경고 상세는", self.last_err)

    def branch_with(self, files, verify=True, build=False):
        """side 브랜치에 files를 커밋하고 원래 브랜치에도 한 커밋을 더한다."""
        tools = self.install_tools()
        self.git("add", "-A")
        self.assertEqual(self.run_git("commit", "-q", "-m", "base"), 0,
                         self.last_err)
        self.git("checkout", "-q", "-b", "side")
        for name, text in files.items():
            self.write(name, text)
        if build:
            subprocess.run(
                [sys.executable, str(tools / "build_index.py"),
                 str(self.root)], env=self.env, check=True,
                stdout=subprocess.PIPE)
        self.git("add", "-A")
        args = ["commit", "-q", "-m", "side"]
        if not verify:
            args.insert(1, "--no-verify")
        self.git(*args)
        self.git("checkout", "-q", "main")
        # 색인에 영향이 없는 변경이라 텍스트 머지한 색인이 생성 결과와 같다.
        self.write("a.md", HFM + "more\n")
        self.assertEqual(self.commit("a.md"), 0, self.last_err)

    def merge_side(self, cwd=None):
        return self.run_git("-C", str(cwd or self.root), "merge", "--no-ff",
                            "-q", "-m", "m", "side")

    def add_check(self, name, code):
        """main 머지 검사 파일을 둔다. 기록 파일은 레포 밖에 둔다."""
        self.write("AGENTS/main-merge-checks/" + name, code)

    def log_check(self, name, expr):
        """실행되면 expr의 값을 레포 밖 기록 파일에 한 줄로 더하는 검사."""
        log = Path(self._tmp.name) / "check.log"
        self.add_check(name, (
            "import os, sys\n"
            "with open(%r, 'a', encoding='utf-8') as f:\n"
            "    f.write(repr(%s) + '\\n')\n") % (str(log), expr))
        return log

    def conflict_resolve(self, cwd):
        """cwd에서 side를 머지해 a.md를 충돌시키고 위반 내용으로 해소해 커밋한다."""
        self.assertNotEqual(self.merge_side(cwd), 0)
        self.assertEqual(self.run_git("-C", str(cwd), "rev-parse", "-q",
                                      "--verify", "MERGE_HEAD"), 0)
        (Path(cwd) / "a.md").write_text("본문\n", encoding="utf-8")
        self.git("-C", str(cwd), "add", "a.md")
        return self.run_git("-C", str(cwd), "commit", "-q", "--no-edit")

    def parents(self):
        return len(self.git("log", "-1", "--format=%P").split())

    def test_merge_clean_passes(self):
        # main 머지 검사 폴더가 없으면 감사만 돌고 통과한다.
        self.branch_with({"b.md": HFM})
        self.assertEqual(self.merge_side(), 0, self.last_err)
        self.assertIn("pre-merge-commit: 감사 완료", self.last_err)
        self.assertEqual(self.parents(), 2)

    def test_merge_other_branch_skips_audit(self):
        self.branch_with({"b.md": "본문\n"}, verify=False, build=True)
        self.git("checkout", "-q", "-b", "dev")
        self.add_check("a.py", "raise SystemExit(1)\n")
        self.assertEqual(self.merge_side(), 0, self.last_err)
        self.assertNotIn("감사 완료", self.last_err)
        self.assertEqual(self.parents(), 2)

    def test_merge_detached_skips_audit(self):
        self.branch_with({"b.md": "본문\n"}, verify=False, build=True)
        self.git("checkout", "-q", "--detach")
        self.assertEqual(self.merge_side(), 0, self.last_err)
        self.assertNotIn("감사 완료", self.last_err)
        self.assertEqual(self.parents(), 2)

    def test_conflict_commit_on_main_audits(self):
        self.branch_with({"a.md": HFM + "side\n"})
        self.assertNotEqual(self.conflict_resolve(self.root), 0)
        self.assertIn("pre-commit: audit violations", self.last_err)
        self.assertIn("git merge --abort", self.last_err)

    def worktree(self, *args):
        wt = Path(self._tmp.name) / "wt"
        self.git("worktree", "add", "-q", *args[:-1], str(wt), args[-1])
        return wt

    def test_conflict_commit_in_worktree_other_branch_skips_audit(self):
        self.branch_with({"a.md": HFM + "side\n"})
        wt = self.worktree("-b", "dev", "main")
        self.assertEqual(self.conflict_resolve(wt), 0, self.last_err)
        self.assertNotIn("감사 완료", self.last_err)

    def test_conflict_commit_in_worktree_on_main_audits(self):
        # 주 워크트리를 다른 브랜치로 옮기면 연결 워크트리에 main을 둘 수 있다.
        self.branch_with({"a.md": HFM + "side\n"})
        self.git("checkout", "-q", "-b", "park")
        wt = self.worktree("main")
        self.assertNotEqual(self.conflict_resolve(wt), 0)
        self.assertIn("pre-commit: audit violations", self.last_err)

    def test_check_failure_blocks(self):
        self.branch_with({"b.md": HFM})
        self.add_check("a.py", "print('검사 실패 표지')\nraise SystemExit(3)\n")
        self.assertNotEqual(self.merge_side(), 0)
        self.assertIn("검사 실패 표지", self.last_err)
        self.assertIn("main merge check failed", self.last_err)
        self.assertIn("a.py이 종료 코드 3로", self.last_err)
        self.assertIn("git merge --abort", self.last_err)
        self.assertEqual(self.run_git("rev-parse", "-q", "--verify",
                                      "MERGE_HEAD"), 0)

    def test_checks_run_in_name_order_skip_underscore(self):
        self.branch_with({"b.md": HFM})
        log = self.log_check("b.py", "'b'")
        self.log_check("a.py", "'a'")
        self.log_check("_c.py", "'c'")
        self.add_check("d.txt", "x\n")
        self.assertEqual(self.merge_side(), 0, self.last_err)
        self.assertEqual(log.read_text(encoding="utf-8"), "'a'\n'b'\n")
        self.assertIn("main merge check a.py 통과", self.last_err)
        self.assertNotIn("_c.py 통과", self.last_err)

    def test_check_gets_no_git_env(self):
        self.branch_with({"b.md": HFM})
        log = self.log_check("a.py", (
            "[sorted(k for k in os.environ if k.startswith('GIT_')),"
            " os.getcwd(), sys.argv[1]]"))
        self.assertEqual(self.merge_side(), 0, self.last_err)
        keys, cwd, arg = eval(log.read_text(encoding="utf-8"))
        self.assertEqual(keys, [])
        self.assertEqual(Path(cwd).resolve(), self.root.resolve())
        self.assertEqual(Path(arg).resolve(), self.root.resolve())

    def test_merge_stale_index_stops_then_commit(self):
        self.branch_with({"b.md": HFM}, verify=False)
        self.assertNotEqual(self.merge_side(), 0)
        self.assertIn("index out of date", self.last_err)
        self.assertIn("다시 만들고 감사한다", self.last_err)
        self.assertTrue((self.root / ".git" / "MERGE_HEAD").exists())
        # 머지 모드는 색인을 쓰거나 스테이지하지 않는다.
        before = self.git("show", "HEAD:INDEX.md")
        self.assertEqual(
            (self.root / "INDEX.md").read_text(encoding="utf-8"), before)
        self.assertEqual(self.run_git("diff", "--cached", "--quiet", "HEAD",
                                      "--", "INDEX.md"), 0)
        self.assertEqual(self.run_git("commit", "-q", "--no-edit"), 0,
                         self.last_err)
        self.assertEqual(self.parents(), 2)
        self.assertIn("b.md", self.git("show", "HEAD:INDEX.md"))

    def test_merge_violation_stops(self):
        self.branch_with({"b.md": "본문\n"}, verify=False, build=True)
        # 감사가 막으면 main 머지 검사는 돌지 않는다.
        self.add_check("a.py", "raise SystemExit(1)\n")
        self.assertNotEqual(self.merge_side(), 0)
        self.assertIn("audit violations", self.last_err)
        self.assertIn("git merge --abort", self.last_err)
        self.assertNotIn("main merge check", self.last_err)
        self.assertTrue((self.root / ".git" / "MERGE_HEAD").exists())
        (self.root / "AGENTS/main-merge-checks/a.py").unlink()
        self.write("b.md", HFM)
        self.git("add", "b.md")
        self.assertEqual(self.run_git("commit", "-q", "--no-edit"), 0,
                         self.last_err)
        self.assertEqual(self.parents(), 2)

    def test_merge_audits_with_main_tag(self):
        # main이라는 이름의 태그가 있어도 main 브랜치 머지로 판정한다.
        self.branch_with({"b.md": "본문\n"}, verify=False, build=True)
        self.git("tag", "main")
        self.assertNotEqual(self.merge_side(), 0)
        self.assertIn("audit violations", self.last_err)

    def test_hook_mode_executable_in_git(self):
        repo = TOOLS.parent.parent.parent
        if not (repo / ".git").exists():
            self.skipTest("git 작업 트리 밖")
        for name in ("pre-commit", "pre-merge-commit"):
            rel = "AGENTS/epistemic-rules/tools/hooks/" + name
            r = subprocess.run(
                ["git", "ls-files", "-s", "--", rel],
                cwd=str(repo), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out = r.stdout.decode("utf-8")
            self.assertTrue(out.startswith("100755 "), rel + ": " + out)


if __name__ == "__main__":
    unittest.main()

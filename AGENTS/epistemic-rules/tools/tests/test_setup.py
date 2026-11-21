"""설치 체계 공용 모듈(_setup_core)과 설치기(setup.py) 시험."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import _setup_core as core  # noqa: E402

SPEC_REL = "AGENTS/epistemic-rules/tools/setup-items.json"
SCAFFOLD_ITEMS = [
    {"id": "hooks-path", "title": "커밋 전 훅", "scope": "clone", "kind": "git-config",
     "params": {"key": "core.hooksPath", "value": "{tools}/hooks"}},
]


def git(cwd, *args):
    return subprocess.run(
        ["git", "-c", "core.autocrlf=false", "-c", "protocol.file.allow=always", *args],
        cwd=cwd, check=True, capture_output=True, encoding="utf-8",
    ).stdout


def write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def make_repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    git(path, "init", "-q", "-b", "main")
    git(path, "config", "user.email", "t@example.com")
    git(path, "config", "user.name", "t")
    return path


def commit_all(repo: Path, msg="c"):
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", msg)


class SetupTestBase(unittest.TestCase):
    """임시 폴더, 임시 홈, 스캐폴드 명세를 둔 임시 레포를 준다.

    모든 시험이 임시 EPISTEMIC_HOME을 써서 실제 홈을 바꾸지 않는다.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name).resolve()
        home = self.tmp / "홈 폴더"
        home.mkdir()
        patcher = mock.patch.dict(os.environ, {"EPISTEMIC_HOME": str(home)})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.home = home
        self.root = make_repo(self.tmp / "ws")
        write(self.root / SPEC_REL, json.dumps(SCAFFOLD_ITEMS, ensure_ascii=False))
        write(self.root / "README.md", "x\n")
        commit_all(self.root, "init")
        self.use_tools(self.root / "AGENTS/epistemic-rules/tools")

    def use_tools(self, tools_dir: Path):
        for name, value in (("TOOLS_DIR", tools_dir), ("SCAFFOLD_SPEC", tools_dir / "setup-items.json")):
            p = mock.patch.object(core, name, value)
            p.start()
            self.addCleanup(p.stop)


class LoadItemsTest(SetupTestBase):
    def test_scaffold_and_instance_items_merged(self):
        write(self.root / "AGENTS/setup/a.json", json.dumps([
            {"id": "x", "title": "엑스", "scope": "machine", "kind": "require-command", "params": {"candidates": ["git"]}},
        ]))
        commit_all(self.root)
        items, errors = core.load_items(self.root)
        self.assertEqual(errors, [])
        self.assertEqual({i.id: i.source for i in items}, {"hooks-path": SPEC_REL, "x": "AGENTS/setup/a.json"})

    def test_items_read_from_main_not_worktree(self):
        write(self.root / "AGENTS/setup/a.json", json.dumps([
            {"id": "x", "title": "main 값", "scope": "clone", "kind": "git-config", "params": {"key": "a.b", "value": "1"}},
        ]))
        commit_all(self.root)
        git(self.root, "checkout", "-q", "-b", "feature/y")
        write(self.root / "AGENTS/setup/a.json", json.dumps([
            {"id": "x", "title": "브랜치 값", "scope": "clone", "kind": "git-config", "params": {"key": "a.b", "value": "1"}},
        ]))
        commit_all(self.root)
        items, _ = core.load_items(self.root)
        self.assertEqual([i.title for i in items if i.id == "x"], ["main 값"])

    def test_items_read_through_submodule_gitlink(self):
        scaffold = make_repo(self.tmp / "scaffold")
        write(scaffold / SPEC_REL, json.dumps([dict(SCAFFOLD_ITEMS[0], title="gitlink 값")], ensure_ascii=False))
        commit_all(scaffold)
        parent = make_repo(self.tmp / "parent")
        git(parent, "submodule", "add", "-q", str(scaffold), "sub")
        commit_all(parent)
        tools = parent / "sub/AGENTS/epistemic-rules/tools"
        self.use_tools(tools)
        write(tools / "setup-items.json", json.dumps([dict(SCAFFOLD_ITEMS[0], title="작업 트리 값")], ensure_ascii=False))
        items, errors = core.load_items(parent)
        self.assertEqual(errors, [])
        self.assertEqual([i.title for i in items], ["gitlink 값"])
        self.assertEqual(items[0].source, "sub/" + SPEC_REL)

    def test_scaffold_spec_from_tools_repo_when_outside_root(self):
        other = make_repo(self.tmp / "other")
        write(other / "README.md", "x\n")
        commit_all(other)
        items, errors = core.load_items(other)
        self.assertEqual(errors, [])
        self.assertEqual([i.id for i in items], ["hooks-path"])

    def test_broken_instance_spec_reported(self):
        write(self.root / "AGENTS/setup/bad.json", "[{")
        write(self.root / "AGENTS/setup/good.json", json.dumps([
            {"id": "g", "title": "지", "scope": "clone", "kind": "git-config", "params": {"key": "a.b", "value": "1"}},
        ]))
        commit_all(self.root)
        items, errors = core.load_items(self.root)
        self.assertIn("g", [i.id for i in items])
        self.assertTrue(any("AGENTS/setup/bad.json" in e for e in errors))

    def test_duplicate_id_reported(self):
        write(self.root / "AGENTS/setup/dup.json", json.dumps([
            {"id": "hooks-path", "title": "중복", "scope": "clone", "kind": "git-config", "params": {"key": "a.b", "value": "1"}},
        ]))
        commit_all(self.root)
        items, errors = core.load_items(self.root)
        self.assertEqual([i.title for i in items if i.id == "hooks-path"], ["커밋 전 훅"])
        self.assertTrue(any(SPEC_REL in e and "AGENTS/setup/dup.json" in e for e in errors))

    def test_missing_main_reported(self):
        git(self.root, "branch", "-m", "main", "trunk")
        items, errors = core.load_items(self.root)
        self.assertEqual(items, [])
        self.assertTrue(errors)

    def test_shipped_spec_parses(self):
        shipped = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) / "setup-items.json"
        items, errors = core.parse_spec(shipped.read_text(encoding="utf-8"), "setup-items.json")
        self.assertEqual(errors, [])
        self.assertTrue(items)
        self.assertTrue(all(i.kind in core.KINDS for i in items))


class StateTest(SetupTestBase):
    def clone_item(self):
        return core.Item("hooks-path", "훅", "clone", "git-config", (), {}, {"key": "core.hooksPath", "value": "x"}, "s")

    def machine_item(self):
        return core.Item("python", "파이썬", "machine", "require-command", (), {}, {"candidates": ["python"]}, "s")

    def test_clone_scope_in_git_config(self):
        self.assertTrue(core.record_applied(self.root, self.clone_item(), "abc123"))
        self.assertEqual(git(self.root, "config", "--local", "--get", "epistemic.setup.hooks-path").strip(), "abc123")
        self.assertEqual(core.applied_hash(self.root, self.clone_item()), "abc123")

    def test_worktree_shares_clone_state(self):
        core.record_applied(self.root, self.clone_item(), "abc123")
        wt = self.tmp / "ws-wt"
        git(self.root, "worktree", "add", "-q", "--detach", str(wt))
        self.addCleanup(lambda: git(self.root, "worktree", "remove", "--force", str(wt)))
        self.assertEqual(core.applied_hash(wt, self.clone_item()), "abc123")

    def test_machine_scope_in_home_state_file(self):
        self.assertTrue(core.record_applied(self.root, self.machine_item(), "h1"))
        state = json.loads((self.home / ".epistemic" / "setup-state.json").read_text(encoding="utf-8"))
        self.assertEqual(state[core.repo_identifier(self.root)]["python"]["spec"], "h1")
        self.assertEqual(core.applied_hash(self.root, self.machine_item()), "h1")

    def test_repo_identifier_normalizes_origin(self):
        git(self.root, "remote", "add", "origin", "https://github.com/Owner/Repo.git")
        a = core.repo_identifier(self.root)
        git(self.root, "remote", "set-url", "origin", "git@github.com:Owner/Repo")
        b = core.repo_identifier(self.root)
        self.assertEqual(a, "github.com/owner/repo")
        self.assertEqual(a, b)

    def test_repo_identifier_without_origin_is_main_repo_name(self):
        wt = self.tmp / "ws-wt2"
        git(self.root, "worktree", "add", "-q", "--detach", str(wt))
        self.addCleanup(lambda: git(self.root, "worktree", "remove", "--force", str(wt)))
        self.assertEqual(core.repo_identifier(wt), "ws")

    def test_corrupt_machine_state_treated_as_empty(self):
        state = self.home / ".epistemic" / "setup-state.json"
        write(state, "{not json")
        self.assertIsNone(core.applied_hash(self.root, self.machine_item()))
        self.assertTrue(core.record_applied(self.root, self.machine_item(), "h2"))
        self.assertTrue((state.parent / "setup-state.json.broken").exists())
        self.assertEqual(core.applied_hash(self.root, self.machine_item()), "h2")

    def test_state_file_under_home_with_spaces(self):
        self.assertIn(" ", str(self.home))
        core.record_applied(self.root, self.machine_item(), "h3")
        self.assertEqual(core.applied_hash(self.root, self.machine_item()), "h3")

    def test_read_python_command(self):
        self.assertIsNone(core.read_python_command())
        write(self.home / ".epistemic" / "python", "uv run --no-project python\n")
        self.assertEqual(core.read_python_command(), "uv run --no-project python")
        write(self.home / ".epistemic" / "python", "C:\\Tools\\py\\python.exe\n")
        self.assertEqual(core.read_python_command(), "C:\\Tools\\py\\python.exe")

    def test_record_failure_is_not_fatal(self):
        real = core.git

        def failing(cwd, *args, **kw):
            if args[:2] == ("config", "--local") and len(args) == 4:
                return 255, ""
            return real(cwd, *args, **kw)

        with mock.patch.object(core, "git", failing):
            self.assertFalse(core.record_applied(self.root, self.clone_item(), "zz"))

    def test_invalid_id_rejected(self):
        items, errors = core.parse_spec(json.dumps([
            {"id": "bad.id", "title": "t", "scope": "clone", "kind": "git-config", "params": {}},
        ]), "s.json")
        self.assertEqual(items, [])
        self.assertTrue(any("bad.id" in e for e in errors))


class HashTest(unittest.TestCase):
    def item(self, **params):
        return core.Item("a", "에이", "clone", "git-config", (), {}, params, "s")

    def test_hash_ignores_key_order_and_changes_with_value(self):
        a = core.item_hash(core.Item("a", "에이", "clone", "git-config", (), {}, {"key": "k", "value": "1"}, "s"))
        b = core.item_hash(core.Item("a", "에이", "clone", "git-config", (), {}, {"value": "1", "key": "k"}, "other"))
        c = core.item_hash(self.item(key="k", value="2"))
        self.assertEqual(a, b)
        self.assertNotEqual(a, c)

    def test_applicable_os_and_when(self):
        win = core.Item("w", "w", "machine", "require-command", ("windows",), {}, {}, "s")
        agy = core.Item("g", "g", "machine", "require-command", (), {"command": "agy"}, {}, "s")
        self.assertFalse(core.applicable(win, "macos", lambda c: True))
        self.assertTrue(core.applicable(win, "windows", lambda c: True))
        self.assertFalse(core.applicable(agy, "linux", lambda c: False))
        self.assertTrue(core.applicable(agy, "linux", lambda c: c == "agy"))


if __name__ == "__main__":
    unittest.main()

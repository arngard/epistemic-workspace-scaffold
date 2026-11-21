"""설치 체계 공용 모듈(_setup_core)과 설치기(setup.py) 시험."""

import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

TOOLS = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, str(TOOLS))

import _setup_core as core  # noqa: E402

SPEC_REL = "AGENTS/epistemic-rules/tools/setup-items.json"
SCAFFOLD_ITEMS = [
    {"id": "hooks-path", "title": "커밋 전 훅", "kind": "git-config",
     "params": {"key": "core.hooksPath", "value": "{tools}/hooks"}},
]
GIT_ITEM = {"id": "git", "title": "git 항목", "kind": "require-command", "params": {"candidates": ["git"]}}


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


def local_config(repo: Path) -> str:
    return git(repo, "config", "--local", "--list")


class SetupTestBase(unittest.TestCase):
    """임시 폴더, 임시 홈, 스캐폴드 명세를 둔 임시 레포를 준다.

    홈(HOME, USERPROFILE)을 임시 폴더로 바꿔 실제 사용자 홈과 전역 git 설정에 흔들리지 않게 한다.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name).resolve()
        home = self.tmp / "홈 폴더"
        home.mkdir()
        patcher = mock.patch.dict(os.environ, {"HOME": str(home), "USERPROFILE": str(home)})
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

    def add_instance(self, items):
        write(self.root / "AGENTS/setup/i.json", json.dumps(items, ensure_ascii=False))
        commit_all(self.root)

    def states(self):
        entries, _ = core.status(self.root)
        return {e.item.id: e.state for e in entries}


def run_cli(*argv):
    import setup as cli
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = cli.main(list(argv))
    return code, out.getvalue(), err.getvalue()


class LoadItemsTest(SetupTestBase):
    def test_scaffold_and_instance_items_merged(self):
        write(self.root / "AGENTS/setup/a.json", json.dumps([
            {"id": "x", "title": "엑스", "kind": "require-command", "params": {"candidates": ["git"]}},
        ]))
        commit_all(self.root)
        items, errors = core.load_items(self.root)
        self.assertEqual(errors, [])
        self.assertEqual({i.id: i.source for i in items}, {"hooks-path": SPEC_REL, "x": "AGENTS/setup/a.json"})

    def test_items_read_from_main_not_worktree(self):
        write(self.root / "AGENTS/setup/a.json", json.dumps([
            {"id": "x", "title": "main 값", "kind": "git-config", "params": {"key": "a.b", "value": "1"}},
        ]))
        commit_all(self.root)
        git(self.root, "checkout", "-q", "-b", "feature/y")
        write(self.root / "AGENTS/setup/a.json", json.dumps([
            {"id": "x", "title": "브랜치 값", "kind": "git-config", "params": {"key": "a.b", "value": "1"}},
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
            {"id": "g", "title": "지", "kind": "git-config", "params": {"key": "a.b", "value": "1"}},
        ]))
        commit_all(self.root)
        items, errors = core.load_items(self.root)
        self.assertIn("g", [i.id for i in items])
        self.assertTrue(any("AGENTS/setup/bad.json" in e for e in errors))

    def test_duplicate_id_reported(self):
        write(self.root / "AGENTS/setup/dup.json", json.dumps([
            {"id": "hooks-path", "title": "중복", "kind": "git-config", "params": {"key": "a.b", "value": "1"}},
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
        items, errors = core.parse_spec((TOOLS / "setup-items.json").read_text(encoding="utf-8"), "setup-items.json")
        self.assertEqual(errors, [])
        self.assertTrue(items)
        self.assertTrue(all(i.kind in core.KINDS for i in items))

    def test_shipped_python_candidates_match_pre_commit_hook(self):
        items, _ = core.parse_spec((TOOLS / "setup-items.json").read_text(encoding="utf-8"), "setup-items.json")
        python = [i for i in items if i.id == "python"][0]
        self.assertEqual(python.params["candidates"], ["python3", "python", "py -3"])
        self.assertIn('for c in python3 python "py -3"', (TOOLS / "hooks" / "pre-commit").read_text(encoding="utf-8"))

    def test_scope_key_ignored(self):
        items, errors = core.parse_spec(json.dumps([
            {"id": "m", "title": "scope 키가 있는 항목", "scope": "machine", "kind": "require-command",
             "params": {"candidates": ["git"]}},
            {"id": "u", "title": "모르는 값", "scope": "elsewhere", "kind": "git-config",
             "params": {"key": "a.b", "value": "1"}},
        ]), "s.json")
        self.assertEqual(errors, [])
        self.assertEqual([i.id for i in items], ["m", "u"])

    def test_invalid_id_rejected(self):
        items, errors = core.parse_spec(json.dumps([
            {"id": "bad.id", "title": "t", "kind": "git-config", "params": {}},
        ]), "s.json")
        self.assertEqual(items, [])
        self.assertTrue(any("bad.id" in e for e in errors))

    def test_malformed_item_fields_reported_per_item(self):
        self.add_instance([
            {"id": "bad", "title": "t", "kind": "require-command", "when": "git", "params": {"candidates": ["git"]}},
            {"id": "ok1", "title": "t", "kind": "require-command", "params": {"candidates": ["git"]}},
        ])
        items, errors = core.load_items(self.root)
        self.assertIn("ok1", [i.id for i in items])
        self.assertNotIn("bad", [i.id for i in items])
        self.assertTrue(any("bad" in e for e in errors))

    def test_linked_worktree_reads_gitlink_from_main_module_store(self):
        scaffold = make_repo(self.tmp / "scaffold")
        write(scaffold / SPEC_REL, json.dumps([dict(SCAFFOLD_ITEMS[0], title="옛 값")], ensure_ascii=False))
        commit_all(scaffold)
        parent = make_repo(self.tmp / "parent")
        git(parent, "submodule", "add", "-q", str(scaffold), "sub")
        commit_all(parent)
        wt = self.tmp / "parent-wt"
        git(parent, "worktree", "add", "-q", "--detach", str(wt))
        git(wt, "-c", "protocol.file.allow=always", "submodule", "update", "-q", "--init")
        write(scaffold / SPEC_REL, json.dumps([dict(SCAFFOLD_ITEMS[0], title="새 값")], ensure_ascii=False))
        commit_all(scaffold)
        git(parent / "sub", "pull", "-q", "origin", "main")
        commit_all(parent, "bump")
        self.use_tools(wt / "sub/AGENTS/epistemic-rules/tools")
        items, errors = core.load_items(wt)
        self.assertEqual(errors, [])
        self.assertEqual([i.title for i in items], ["새 값"])


class KindTest(SetupTestBase):
    def hooks_item(self):
        return core.Item("hooks-path", "훅", "git-config", (), {}, {"key": "core.hooksPath", "value": "{tools}/hooks"}, "s")

    def cmd_item(self, candidates, min_version="3.9"):
        params = {"candidates": candidates, "args": ["--version"]}
        if min_version:
            params["min_version"] = min_version
        return core.Item("python", "파이썬", "require-command", (), {}, params, "s")

    def test_git_config_check_and_apply(self):
        item = self.hooks_item()
        self.assertFalse(core.check_item(self.root, item).ok)
        result = core.apply_item(self.root, item)
        self.assertTrue(result.ok)
        self.assertEqual(git(self.root, "config", "--local", "--get", "core.hooksPath").strip(), "AGENTS/epistemic-rules/tools/hooks")
        self.assertTrue(core.check_item(self.root, item).ok)

    def test_hooks_path_resolves_to_tools_dir_in_submodule(self):
        self.use_tools(self.root / "implementation/x/AGENTS/epistemic-rules/tools")
        self.assertEqual(core.resolve("{tools}/hooks", self.root), "implementation/x/AGENTS/epistemic-rules/tools/hooks")

    def test_require_command_picks_first_runnable_meeting_version(self):
        result = core.check_item(self.root, self.cmd_item(["없는명령-xyz", sys.executable]))
        self.assertTrue(result.ok)
        self.assertIn(sys.executable, result.detail)

    def test_require_command_version_too_low(self):
        fake = self.tmp / "fake_python.py"
        write(fake, "print('Python 3.8.10')\n")
        result = core.check_item(self.root, self.cmd_item([f"{sys.executable} {fake}"]))
        self.assertFalse(result.ok)
        self.assertIn("3.8.10", result.detail)

    def test_unrunnable_candidate_skipped(self):
        # 실행되지 않는 후보(모르는 자리 표시가 남은 것 포함)는 건너뛰고 다음 후보를 본다.
        result = core.check_item(self.root, self.cmd_item(["{unknown}", sys.executable]))
        self.assertTrue(result.ok)
        self.assertIn(sys.executable, result.detail)

    def test_bad_min_version_fails_item_only(self):
        self.add_instance([{"id": "v", "title": "t", "kind": "require-command",
                            "params": {"candidates": ["git"], "min_version": "2.x"}}])
        states = self.states()
        self.assertEqual(states["v"], "pending")
        self.assertIn("hooks-path", states)

    def test_unknown_kind_check_reports_tool_too_old(self):
        item = core.Item("c", "복사", "copy-file", (), {}, {}, "s")
        result = core.check_item(self.root, item)
        self.assertFalse(result.ok)
        self.assertTrue(result.detail.startswith("도구가 명세보다 낡았다"))

    def test_applicable_os_and_when(self):
        win = core.Item("w", "w", "require-command", ("windows",), {}, {}, "s")
        agy = core.Item("g", "g", "require-command", (), {"command": "agy"}, {}, "s")
        self.assertFalse(core.applicable(win, "macos", lambda c: True))
        self.assertTrue(core.applicable(win, "windows", lambda c: True))
        self.assertFalse(core.applicable(agy, "linux", lambda c: False))
        self.assertTrue(core.applicable(agy, "linux", lambda c: c == "agy"))


class StatusTest(SetupTestBase):
    def test_status_check_plan_write_nothing(self):
        # 설치기 복사본을 임시 레포에 두고, 임시 홈을 쓰는 하위 프로세스로 status, check, plan을 돌린다.
        for name in ("setup.py", "_setup_core.py"):
            shutil.copy2(TOOLS / name, self.root / "AGENTS/epistemic-rules/tools" / name)
        self.add_instance([GIT_ITEM, {"id": "ab", "title": "에이비", "kind": "git-config",
                                      "params": {"key": "a.b", "value": "1"}}])
        before_config, before_tree = local_config(self.root), git(self.root, "status", "--porcelain", "--ignored")
        env = dict(os.environ, HOME=str(self.home), USERPROFILE=str(self.home), PYTHONDONTWRITEBYTECODE="1")
        script = self.root / "AGENTS/epistemic-rules/tools/setup.py"
        for command, expected in ((["status"], 0), (["status", "--json"], 0), (["check"], 1), (["plan"], 0)):
            proc = subprocess.run([sys.executable, "-B", str(script), command[0], str(self.root), *command[1:]],
                                  capture_output=True, env=env, timeout=120)
            self.assertEqual(proc.returncode, expected, proc.stderr.decode("utf-8", "replace"))
            self.assertIn(b"hooks-path" if command[0] != "plan" else "커밋 전 훅".encode("utf-8"), proc.stdout)
        self.assertEqual(list(self.home.iterdir()), [])
        self.assertEqual(local_config(self.root), before_config)
        self.assertEqual(git(self.root, "status", "--porcelain", "--ignored"), before_tree)

    def test_passing_items_ok_without_record(self):
        self.add_instance([GIT_ITEM])
        before = local_config(self.root)
        self.assertEqual(self.states()["git"], "ok")
        self.assertEqual(local_config(self.root), before)

    def test_status_pending_until_applied(self):
        self.assertEqual(self.states()["hooks-path"], "pending")
        code, _, _ = run_cli("apply", str(self.root), "hooks-path")
        self.assertEqual(code, 0)
        self.assertEqual(self.states()["hooks-path"], "ok")

    def test_pending_reported_again_without_record(self):
        before = local_config(self.root)
        self.assertEqual(self.states()["hooks-path"], "pending")
        self.assertEqual(local_config(self.root), before)
        self.assertEqual(self.states()["hooks-path"], "pending")
        self.assertIn("hooks-path", core.status_lines(self.root)[0])

    def test_changed_spec_value_is_pending(self):
        item = {"id": "ab", "title": "에이비", "kind": "git-config", "params": {"key": "a.b", "value": "1"}}
        self.add_instance([item])
        run_cli("apply", str(self.root), "ab")
        self.assertEqual(self.states()["ab"], "ok")
        self.add_instance([dict(item, params={"key": "a.b", "value": "2"})])
        self.assertEqual(self.states()["ab"], "pending")
        _, out, _ = run_cli("plan", str(self.root))
        self.assertIn("a.b: 1 -> 2", out)

    def test_manual_config_change_is_pending(self):
        run_cli("apply", str(self.root), "hooks-path")
        git(self.root, "config", "--local", "--unset", "core.hooksPath")
        self.assertEqual(self.states()["hooks-path"], "pending")

    def test_status_lines_format(self):
        self.add_instance([
            {"id": "x", "title": "엑스", "kind": "require-command", "params": {"candidates": ["없는명령-xyz"]}},
            GIT_ITEM,
        ])
        self.assertEqual(core.status_lines(self.root), [
            '미적용 갱신 2건: hooks-path, x. workspace-setup.md "갱신 흐름"대로 사용자에게 알리고 동의를 받는다.',
        ])

    def test_status_lines_nothing_pending(self):
        run_cli("apply", str(self.root), "hooks-path")
        self.assertEqual(core.status_lines(self.root), ["환경 갱신 없음"])

    def test_status_without_main_reports_failure(self):
        git(self.root, "branch", "-m", "main", "trunk")
        lines = core.status_lines(self.root)
        self.assertTrue(lines[0].startswith("수집 실패:"))

    def test_failure_message_names_cause(self):
        plain = self.tmp / "레포 아님"
        plain.mkdir()
        with mock.patch.dict(os.environ, {"GIT_CEILING_DIRECTORIES": str(self.tmp)}):
            not_repo = core.status_lines(plain)[0]
        with mock.patch.object(core, "git", lambda *a, **k: (-1, "")):
            no_git = core.status_lines(self.root)[0]
        git(self.root, "branch", "-m", "main", "trunk")
        no_main = core.status_lines(self.root)[0]
        self.assertIn("git 레포가 아니", not_repo)
        self.assertIn("git을 실행하지 못해", no_git)
        self.assertIn("로컬 main 브랜치가 없어", no_main)
        for line in (not_repo, no_git):
            self.assertTrue(line.startswith("수집 실패:"))
            self.assertNotIn("main 브랜치가 없어", line)

    def test_not_applicable_items_leave_alerts(self):
        self.add_instance([{"id": "agy", "title": "에이지와이", "kind": "require-command",
                            "when": {"command": "없는명령-xyz"}, "params": {"candidates": ["없는명령-xyz"]}}])
        self.assertEqual(self.states()["agy"], "not-applicable")
        self.assertNotIn("agy", core.status_lines(self.root)[0])


class CliTest(SetupTestBase):
    def test_apply_refuses_unknown_id_and_tool_too_old(self):
        self.add_instance([{"id": "cp", "title": "복사", "kind": "copy-file", "params": {}}])
        self.assertEqual(run_cli("apply", str(self.root), "없는-id")[0], 2)
        self.assertEqual(run_cli("apply", str(self.root), "cp")[0], 2)

    def test_apply_has_no_confirm_paused(self):
        flag = "--confirm" + "-paused"
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as cm:
            run_cli("apply", str(self.root), "hooks-path", flag)
        self.assertEqual(cm.exception.code, 2)
        self.assertNotEqual(subprocess.run(["git", "config", "--local", "--get", "core.hooksPath"],
                                           cwd=self.root, capture_output=True).returncode, 0)

    def test_apply_refuses_not_applicable(self):
        other = "linux" if core.current_os() != "linux" else "windows"
        self.add_instance([{"id": "o", "title": "t", "kind": "git-config", "os": [other],
                            "params": {"key": "foo.bar", "value": "1"}}])
        self.assertEqual(run_cli("apply", str(self.root), "o")[0], 2)
        self.assertNotEqual(subprocess.run(["git", "config", "--local", "--get", "foo.bar"],
                                           cwd=self.root, capture_output=True).returncode, 0)

    def test_plan_shows_targets(self):
        code, out, _ = run_cli("plan", str(self.root), "hooks-path")
        self.assertEqual(code, 0)
        self.assertIn("core.hooksPath: (없음) -> AGENTS/epistemic-rules/tools/hooks", out)

    def test_plan_shows_current_value(self):
        git(self.root, "config", "--local", "core.hooksPath", ".husky")
        _, out, _ = run_cli("plan", str(self.root), "hooks-path")
        self.assertIn("core.hooksPath: .husky -> AGENTS/epistemic-rules/tools/hooks", out)

    def test_plan_labels_what_changes(self):
        self.add_instance([GIT_ITEM])
        _, out, _ = run_cli("plan", str(self.root), "hooks-path", "git")
        self.assertIn("- 커밋 전 훅 [클론]: ", out)
        self.assertIn("- git 항목 [바꾸는 것 없음]: git", out)

    def test_plan_omits_passing_items(self):
        self.add_instance([GIT_ITEM])
        _, out, _ = run_cli("plan", str(self.root))
        self.assertNotIn("git 항목", out)

    def test_json_output_shape(self):
        self.add_instance([GIT_ITEM])
        code, out, _ = run_cli("status", str(self.root), "--json")
        self.assertEqual(code, 0)
        data = json.loads(out)
        for entry in data:
            self.assertEqual(set(entry), {"id", "title", "state", "changes", "targets", "detail"})
        self.assertEqual({e["id"]: e["changes"] for e in data}, {"hooks-path": "clone", "git": "none"})
        self.assertEqual({e["id"]: e["state"] for e in data}, {"hooks-path": "pending", "git": "ok"})

    def test_check_reports_passing_items_ok(self):
        self.add_instance([GIT_ITEM])
        code, out, _ = run_cli("check", str(self.root), "--json")
        self.assertEqual(code, 1)
        self.assertEqual({e["id"]: e["state"] for e in json.loads(out)}, {"hooks-path": "pending", "git": "ok"})

    def test_check_runs_all_items(self):
        run_cli("apply", str(self.root), "hooks-path")
        self.assertEqual(run_cli("check", str(self.root))[0], 0)
        git(self.root, "config", "--local", "--unset", "core.hooksPath")
        code, out, _ = run_cli("check", str(self.root), "--json")
        self.assertEqual(code, 1)
        self.assertEqual({e["id"]: e["state"] for e in json.loads(out)}["hooks-path"], "pending")

    def test_check_and_plan_fail_when_spec_unreadable(self):
        git(self.root, "branch", "-m", "main", "trunk")
        self.assertNotEqual(run_cli("check", str(self.root))[0], 0)
        self.assertNotEqual(run_cli("plan", str(self.root))[0], 0)


if __name__ == "__main__":
    unittest.main()

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


class KindTest(SetupTestBase):
    def hooks_item(self):
        return core.Item("hooks-path", "훅", "clone", "git-config", (), {}, {"key": "core.hooksPath", "value": "{tools}/hooks"}, "s")

    def cmd_item(self, candidates, min_version="3.9"):
        params = {"candidates": candidates, "args": ["--version"]}
        if min_version:
            params["min_version"] = min_version
        return core.Item("python", "파이썬", "machine", "require-command", (), {}, params, "s")

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

    def test_python_file_candidate_used_first(self):
        write(self.home / ".epistemic" / "python", sys.executable + "\n")
        result = core.check_item(self.root, self.cmd_item(["{python_file}", "없는명령-xyz"]))
        self.assertTrue(result.ok)
        self.assertIn(sys.executable, result.detail)

    def test_python_file_candidate_dropped_when_missing(self):
        self.assertEqual(core.candidate_commands(self.cmd_item(["{python_file}", "git"]), self.root), ["git"])

    def test_unknown_kind_check_reports_tool_too_old(self):
        item = core.Item("c", "복사", "machine", "copy-file", (), {}, {}, "s")
        result = core.check_item(self.root, item)
        self.assertFalse(result.ok)
        self.assertTrue(result.detail.startswith("도구가 명세보다 낡았다"))


def run_cli(*argv):
    import contextlib
    import io
    import setup as cli
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = cli.main(list(argv))
    return code, out.getvalue(), err.getvalue()


class StatusTest(SetupTestBase):
    def add_instance(self, items):
        write(self.root / "AGENTS/setup/i.json", json.dumps(items, ensure_ascii=False))
        commit_all(self.root)

    def states(self):
        entries, _ = core.status(self.root)
        return {e.item.id: e.state for e in entries}

    def test_status_records_passing_items_without_consent(self):
        self.add_instance([{"id": "git", "title": "git", "scope": "machine", "kind": "require-command",
                            "params": {"candidates": ["git"], "args": ["--version"]}}])
        self.assertEqual(self.states()["git"], "recorded")
        self.assertEqual(self.states()["git"], "ok")

    def test_status_pending_until_applied(self):
        self.assertEqual(self.states()["hooks-path"], "pending")
        code, _, _ = run_cli("apply", str(self.root), "hooks-path")
        self.assertEqual(code, 0)
        self.assertEqual(self.states()["hooks-path"], "ok")

    def test_spec_change_makes_item_pending_again(self):
        item = {"id": "ab", "title": "에이비", "scope": "clone", "kind": "git-config", "params": {"key": "a.b", "value": "1"}}
        self.add_instance([item])
        run_cli("apply", str(self.root), "ab")
        self.assertEqual(self.states()["ab"], "ok")
        self.add_instance([dict(item, params={"key": "a.b", "value": "2"})])
        self.assertEqual(self.states()["ab"], "pending")

    def test_status_lines_format(self):
        self.add_instance([
            {"id": "x", "title": "엑스", "scope": "machine", "kind": "require-command", "params": {"candidates": ["없는명령-xyz"]}},
            {"id": "git", "title": "git", "scope": "machine", "kind": "require-command", "params": {"candidates": ["git"]}},
        ])
        lines = core.status_lines(self.root)
        self.assertEqual(lines[0], '미적용 갱신 2건: hooks-path(클론), x(머신). workspace-setup.md "갱신 흐름"대로 사용자에게 알리고 동의를 받는다.')
        self.assertIn("기록만 한 항목: git", lines)

    def test_status_lines_nothing_pending(self):
        run_cli("apply", str(self.root), "hooks-path")
        self.assertEqual(core.status_lines(self.root), ["환경 갱신 없음"])

    def test_status_without_main_reports_failure(self):
        git(self.root, "branch", "-m", "main", "trunk")
        lines = core.status_lines(self.root)
        self.assertTrue(lines[0].startswith("수집 실패:"))

    def test_not_applicable_items_leave_alerts(self):
        self.add_instance([{"id": "agy", "title": "에이지와이", "scope": "machine", "kind": "require-command",
                            "when": {"command": "없는명령-xyz"}, "params": {"candidates": ["없는명령-xyz"]}}])
        self.assertEqual(self.states()["agy"], "not-applicable")
        self.assertNotIn("agy", core.status_lines(self.root)[0])


class CliTest(SetupTestBase):
    def test_apply_refuses_unknown_id_and_tool_too_old(self):
        write(self.root / "AGENTS/setup/i.json", json.dumps([
            {"id": "cp", "title": "복사", "scope": "machine", "kind": "copy-file", "params": {}},
        ]))
        commit_all(self.root)
        self.assertEqual(run_cli("apply", str(self.root), "없는-id")[0], 2)
        self.assertEqual(run_cli("apply", str(self.root), "cp")[0], 2)

    def test_apply_machine_change_requires_confirm_paused(self):
        with mock.patch.dict(core.KIND_CHANGES, {"git-config": "machine"}):
            code, _, err = run_cli("apply", str(self.root), "hooks-path")
            self.assertEqual(code, 2)
            self.assertIn("--confirm-paused", err)
            self.assertEqual(run_cli("apply", str(self.root), "hooks-path", "--confirm-paused")[0], 0)

    def test_plan_shows_targets(self):
        code, out, _ = run_cli("plan", str(self.root), "hooks-path")
        self.assertEqual(code, 0)
        self.assertIn("core.hooksPath: (없음) -> AGENTS/epistemic-rules/tools/hooks", out)
        self.assertNotIn("다른 작업 중단 필요", out)

    def test_plan_requests_pause_for_machine_changes(self):
        with mock.patch.dict(core.KIND_CHANGES, {"git-config": "machine"}):
            _, out, _ = run_cli("plan", str(self.root))
        self.assertIn("다른 작업 중단 필요", out)

    def test_json_output_shape(self):
        write(self.root / "AGENTS/setup/i.json", json.dumps([
            {"id": "git", "title": "git", "scope": "machine", "kind": "require-command", "params": {"candidates": ["git"]}},
        ]))
        commit_all(self.root)
        code, out, _ = run_cli("status", str(self.root), "--json")
        self.assertEqual(code, 0)
        data = json.loads(out)
        for entry in data:
            self.assertEqual(set(entry), {"id", "title", "scope", "state", "changes", "targets", "detail"})
        self.assertEqual({e["id"]: e["changes"] for e in data}["git"], "none")

    def test_check_reports_passing_items_ok_without_recording(self):
        write(self.root / "AGENTS/setup/i.json", json.dumps([
            {"id": "git", "title": "git", "scope": "machine", "kind": "require-command", "params": {"candidates": ["git"]}},
        ]))
        commit_all(self.root)
        code, out, _ = run_cli("check", str(self.root), "--json")
        self.assertEqual({e["id"]: e["state"] for e in json.loads(out)}["git"], "ok")
        item = [i for i in core.load_items(self.root)[0] if i.id == "git"][0]
        self.assertIsNone(core.applied_hash(self.root, item))

    def test_plan_omits_passing_unrecorded_items(self):
        write(self.root / "AGENTS/setup/i.json", json.dumps([
            {"id": "git", "title": "git 항목", "scope": "machine", "kind": "require-command", "params": {"candidates": ["git"]}},
        ]))
        commit_all(self.root)
        _, out, _ = run_cli("plan", str(self.root))
        self.assertNotIn("git 항목", out)

    def test_check_runs_all_items_ignoring_hash(self):
        run_cli("apply", str(self.root), "hooks-path")
        git(self.root, "config", "--local", "--unset", "core.hooksPath")
        code, out, _ = run_cli("check", str(self.root), "--json")
        self.assertEqual(code, 1)
        self.assertEqual({e["id"]: e["state"] for e in json.loads(out)}["hooks-path"], "pending")


class ReviewFixTest(SetupTestBase):
    """독립 검토가 찾은 결함의 재현."""

    def add_instance(self, items):
        write(self.root / "AGENTS/setup/i.json", json.dumps(items, ensure_ascii=False))
        commit_all(self.root)

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

    def test_check_and_plan_fail_when_spec_unreadable(self):
        git(self.root, "branch", "-m", "main", "trunk")
        self.assertNotEqual(run_cli("check", str(self.root))[0], 0)
        self.assertNotEqual(run_cli("plan", str(self.root))[0], 0)

    MACHINE_GIT = {"id": "git", "title": "git", "scope": "machine", "kind": "require-command", "params": {"candidates": ["git"]}}

    def test_state_entry_not_dict_isolated(self):
        self.add_instance([self.MACHINE_GIT])
        write(self.home / ".epistemic" / "setup-state.json", json.dumps({core.repo_identifier(self.root): "x"}))
        lines = core.status_lines(self.root)
        self.assertFalse(lines[0].startswith("수집 실패"))

    def test_state_file_not_utf8_treated_as_broken(self):
        self.add_instance([self.MACHINE_GIT])
        state = self.home / ".epistemic" / "setup-state.json"
        state.parent.mkdir(parents=True, exist_ok=True)
        state.write_bytes(b"\xff\xfe\x00bad")
        self.assertFalse(core.status_lines(self.root)[0].startswith("수집 실패"))

    def test_python_file_utf16_ignored(self):
        p = self.home / ".epistemic" / "python"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes("python\n".encode("utf-16"))
        self.assertIsNone(core.read_python_command())

    def test_malformed_item_fields_reported_per_item(self):
        self.add_instance([
            {"id": "bad", "title": "t", "scope": "machine", "kind": "require-command", "when": "git", "params": {"candidates": ["git"]}},
            {"id": "ok1", "title": "t", "scope": "machine", "kind": "require-command", "params": {"candidates": ["git"]}},
        ])
        items, errors = core.load_items(self.root)
        self.assertIn("ok1", [i.id for i in items])
        self.assertNotIn("bad", [i.id for i in items])
        self.assertTrue(any("bad" in e for e in errors))

    def test_bad_min_version_fails_item_only(self):
        self.add_instance([{"id": "v", "title": "t", "scope": "machine", "kind": "require-command",
                            "params": {"candidates": ["git"], "min_version": "2.x"}}])
        entries, _ = core.status(self.root)
        states = {e.item.id: e.state for e in entries}
        self.assertEqual(states["v"], "pending")
        self.assertIn("hooks-path", states)

    def test_concurrent_machine_records_all_kept(self):
        script = self.tmp / "writer.py"
        write(script, (
            "import sys\n"
            f"sys.path.insert(0, {str(Path(core.__file__).parent)!r})\n"
            "import _setup_core as core\n"
            "from pathlib import Path\n"
            "from unittest import mock\n"
            "n = sys.argv[1]\n"
            "for k in range(10):\n"
            "    item = core.Item(f'i{n}x{k}', 't', 'machine', 'require-command', (), {}, {}, 's')\n"
            "    with mock.patch.object(core, 'repo_identifier', lambda root: 'shared'):\n"
            "        assert core.record_applied(Path('.'), item, 'h')\n"
        ))
        env = dict(os.environ)
        procs = [subprocess.Popen([sys.executable, str(script), str(n)], env=env, cwd=self.tmp) for n in range(6)]
        codes = [p.wait(timeout=120) for p in procs]
        self.assertEqual(codes, [0] * 6)
        state = json.loads((self.home / ".epistemic" / "setup-state.json").read_text(encoding="utf-8"))
        self.assertEqual(len(state["shared"]), 60)

    def test_plan_shows_current_value(self):
        git(self.root, "config", "--local", "core.hooksPath", ".husky")
        _, out, _ = run_cli("plan", str(self.root), "hooks-path")
        self.assertIn("core.hooksPath: .husky -> AGENTS/epistemic-rules/tools/hooks", out)

    def test_apply_refuses_not_applicable(self):
        other = "linux" if core.current_os() != "linux" else "windows"
        self.add_instance([{"id": "o", "title": "t", "scope": "clone", "kind": "git-config", "os": [other],
                            "params": {"key": "foo.bar", "value": "1"}}])
        self.assertEqual(run_cli("apply", str(self.root), "o")[0], 2)
        self.assertNotEqual(subprocess.run(["git", "config", "--local", "--get", "foo.bar"], cwd=self.root).returncode, 0)

    def test_unresolvable_placeholder_fails(self):
        item = core.Item("p", "t", "clone", "git-config", (), {}, {"key": "foo.py", "value": "{python_file}"}, "s")
        self.assertFalse(core.check_item(self.root, item).ok)
        self.assertFalse(core.apply_item(self.root, item).ok)


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

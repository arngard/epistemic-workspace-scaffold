"""세션 시작 요약 시험 (문서 요약, 최근 머지, 머지 전 브랜치, reference 미처리, 감사 출력 파싱, 출력 상한, 수집 실패 표시)."""

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import session_brief  # noqa: E402

from session_brief import (  # noqa: E402
    MARKER, MAX_CHARS, MAX_DOCS_PER_MERGE, main, merge_lines, origin_main_state,
    parse_audit, pending_references, recent_merges, render, summarize, unmerged_branches,
)


def git(root, *args):
    subprocess.run(
        ["git", "-c", "core.autocrlf=false", *args], cwd=root, check=True,
        capture_output=True,
    )


_HOME = None
_HOME_PATCH = None


def setUpModule():
    """모든 시험이 임시 홈(HOME, USERPROFILE)과 그 안의 전역 git 설정(GIT_CONFIG_GLOBAL)을 쓰고
    시스템 git 설정을 끈다(GIT_CONFIG_NOSYSTEM). 요약이 부르는 git과 환경 갱신 판정이
    실제 사용자 환경에 흔들리지 않게 하려는 것이다."""
    global _HOME, _HOME_PATCH
    _HOME = tempfile.TemporaryDirectory()
    _HOME_PATCH = mock.patch.dict(os.environ, {"HOME": _HOME.name, "USERPROFILE": _HOME.name,
                                               "GIT_CONFIG_GLOBAL": os.path.join(_HOME.name, ".gitconfig"),
                                               "GIT_CONFIG_NOSYSTEM": "1"})
    _HOME_PATCH.start()


def tearDownModule():
    _HOME_PATCH.stop()
    _HOME.cleanup()


def run_main(*argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = main(list(argv))
    return code, out.getvalue()


class TempDir(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name).resolve()

    def write(self, rel, text):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("w", encoding="utf-8", newline="\n") as f:  # write_text의 newline은 Python 3.10부터다.
            f.write(text)


class TempRepo(TempDir):
    """main 브랜치 하나를 가진 임시 git 레포."""

    def setUp(self):
        super().setUp()
        git(self.root, "init", "-q", "-b", "main")
        git(self.root, "config", "user.email", "t@example.com")
        git(self.root, "config", "user.name", "t")
        self.write("worklog/TASK_TREE.md", "# 작업 트리\n")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "init")

    def merge_branch(self, branch, files, subject):
        git(self.root, "checkout", "-q", "-b", branch)
        for rel, text in files.items():
            self.write(rel, text)
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "work")
        git(self.root, "checkout", "-q", "main")
        git(self.root, "merge", "-q", "--no-ff", "-m", subject, branch)


class DocSummaryTest(unittest.TestCase):
    def test_description_preferred(self):
        self.assertEqual(summarize("---\ndescription: 요약 한 줄\n---\n\n# 제목\n"), "요약 한 줄")

    def test_heading_fallback(self):
        self.assertEqual(summarize("---\ntags: [x]\n---\n\n# 제목만 있다\n"), "제목만 있다")

    def test_crlf_front_matter(self):
        self.assertEqual(summarize("---\r\ndescription: 줄바꿈 CRLF\r\n---\r\n"), "줄바꿈 CRLF")

    def test_long_summary_truncated(self):
        self.assertLessEqual(len(summarize("---\ndescription: " + "가" * 500 + "\n---\n")), 160)


class RecentMergesTest(TempRepo):
    def test_merge_lists_changed_docs_with_summary(self):
        self.merge_branch(
            "docs/x", {"문서 폴더/새 문서.md": "---\ndescription: 공백 든 경로\n---\n"},
            "Merge docs/x: 문서를 더한다",
        )
        merges = recent_merges(self.root, 1)
        self.assertEqual(len(merges), 1)
        self.assertIn("문서를 더한다", merges[0][1])
        self.assertEqual(merges[0][2], [("문서 폴더/새 문서.md", "공백 든 경로")])

    def test_deleted_doc_marked(self):
        self.merge_branch("docs/a", {"gone.md": "# 곧 지운다\n"}, "Merge a")
        git(self.root, "checkout", "-q", "-b", "docs/b")
        git(self.root, "rm", "-q", "gone.md")
        git(self.root, "commit", "-q", "-m", "rm")
        git(self.root, "checkout", "-q", "main")
        git(self.root, "merge", "-q", "--no-ff", "-m", "Merge b", "docs/b")
        self.assertEqual(recent_merges(self.root, 1)[0][2], [("gone.md", None)])

    def test_summary_read_from_main_not_worktree(self):
        self.merge_branch("docs/m", {"m.md": "---\ndescription: main의 요약\n---\n"}, "Merge m")
        git(self.root, "checkout", "-q", "-b", "feature/w")
        self.write("m.md", "---\ndescription: 작업 브랜치의 요약\n---\n")
        self.assertEqual(recent_merges(self.root, 1)[0][2], [("m.md", "main의 요약")])

    def test_summaries_read_only_within_display_cap(self):
        files = {f"many/d{i}.md": f"# 문서 {i}\n" for i in range(MAX_DOCS_PER_MERGE + 5)}
        self.merge_branch("docs/many", files, "Merge many")
        calls = []
        original = session_brief.main_doc_summaries

        def counting(root, rels, offline=False):
            calls.append(list(rels))
            return original(root, rels, offline)

        with mock.patch.object(session_brief, "main_doc_summaries", counting):
            docs = recent_merges(self.root, 1)[0][2]
        self.assertEqual(len(docs), MAX_DOCS_PER_MERGE + 5)
        self.assertEqual(len(calls), 1)
        self.assertEqual(len(calls[0]), MAX_DOCS_PER_MERGE)

    def test_present_and_missing_docs_read_in_one_git_call(self):
        """공백, 한글이 든 경로와 여러 바이트 글자, CRLF 본문, 사이에 낀 지운 문서를 한 번에 읽는다."""
        self.merge_branch("docs/a", {"b 지움.md": "# 곧 지운다\n"}, "Merge a")
        git(self.root, "checkout", "-q", "-b", "docs/b")
        git(self.root, "rm", "-q", "b 지움.md")
        self.write("a 한글 폴더/첫 문서.md", "---\ndescription: 첫 요약 가나다\n---\n\n본문 " + "한" * 300 + "\n")
        (self.root / "c 문서.md").write_bytes("---\r\ndescription: 셋째 CRLF\r\n---\r\n".encode("utf-8"))
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "mix")
        git(self.root, "checkout", "-q", "main")
        git(self.root, "merge", "-q", "--no-ff", "-m", "Merge b", "docs/b")
        self.merge_branch("docs/d", {"d.md": "# 넷째\n"}, "Merge d")
        reads = []
        real_popen = subprocess.Popen

        def counting(cmd, *args, **kwargs):
            if "show" in cmd or "cat-file" in cmd:
                reads.append(cmd)
            return real_popen(cmd, *args, **kwargs)

        # subprocess.run도 안에서 Popen을 부르므로 git show와 cat-file 호출을 모두 센다.
        with mock.patch.object(session_brief.subprocess, "Popen", counting):
            merges = recent_merges(self.root, 2)
        self.assertEqual(len(reads), 1)
        self.assertEqual(merges[0][2], [("d.md", "넷째")])
        self.assertEqual(merges[1][2], [
            ("a 한글 폴더/첫 문서.md", "첫 요약 가나다"),
            ("b 지움.md", None),
            ("c 문서.md", "셋째 CRLF"),
        ])

    def test_batch_failure_reported_as_collection_failure(self):
        self.merge_branch("docs/x", {"x.md": "# x\n"}, "Merge x")
        with mock.patch.object(session_brief, "main_doc_summaries", return_value=None):
            self.assertIsNone(recent_merges(self.root, 1))

    def test_docs_per_merge_capped(self):
        docs = [(f"d{i}.md", "s") for i in range(MAX_DOCS_PER_MERGE + 3)]
        lines = merge_lines([("abc1234", "Merge big", docs)])
        self.assertEqual(len(lines), 1 + MAX_DOCS_PER_MERGE + 1)
        self.assertIn("문서 3개 더", lines[-1])
        self.assertIn("git show --stat abc1234", lines[-1])


class UnmergedBranchesTest(TempRepo):
    def test_in_progress_node_from_task_tree_diff(self):
        git(self.root, "checkout", "-q", "-b", "feature/y")
        self.write("worklog/TASK_TREE.md", "# 작업 트리\n\n- [/] 진행 중인 일\n  - 설명: x\n")
        git(self.root, "commit", "-q", "-am", "start")
        git(self.root, "checkout", "-q", "main")
        self.assertEqual(unmerged_branches(self.root), [("feature/y", ["- [/] 진행 중인 일"], False)])
        self.assertEqual(origin_main_state(self.root), (None, 0))

    def test_origin_main_prefix_ref_not_taken_as_origin_main(self):
        git(self.root, "update-ref", "refs/remotes/origin/main/x", "main")
        self.assertEqual(origin_main_state(self.root), (None, 0))

    def make_stale_main(self):
        """다른 곳에서 feature/z를 머지해 push했고 로컬 main은 아직 pull하지 않은 상태."""
        git(self.root, "checkout", "-q", "-b", "feature/z")
        self.write("worklog/TASK_TREE.md", "# 작업 트리\n\n- [/] 다른 곳에서 끝난 일\n")
        git(self.root, "commit", "-q", "-am", "start")
        git(self.root, "checkout", "-q", "-b", "remote-main", "main")
        git(self.root, "merge", "-q", "--no-ff", "-m", "Merge z", "feature/z")
        git(self.root, "update-ref", "refs/remotes/origin/main", "remote-main")
        git(self.root, "checkout", "-q", "main")
        git(self.root, "branch", "-q", "-D", "remote-main")

    def test_branch_merged_only_on_origin_main_excluded(self):
        self.make_stale_main()
        _, text = run_main(str(self.root), "--no-audit", "--no-fetch")
        self.assertIn("로컬 main이 origin/main보다 2커밋 뒤다", text)
        self.assertNotIn("feature/z", text)
        self.assertNotIn("다른 곳에서 끝난 일", text)

    def test_inherited_node_not_attributed_to_new_branch(self):
        self.make_stale_main()
        self.assert_new_branch_without_inherited_node()

    def test_inherited_node_hidden_when_main_diverged(self):
        self.make_stale_main()
        self.write("local-only.md", "# 로컬 main에만 있는 문서\n")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "local only")
        self.assert_new_branch_without_inherited_node()

    def test_same_title_under_other_parent_kept_once(self):
        self.make_stale_main()
        git(self.root, "checkout", "-q", "-b", "feature/dup", "refs/remotes/origin/main")
        self.write("worklog/TASK_TREE.md", (
            "# 작업 트리\n\n- [/] 다른 곳에서 끝난 일\n\n- [/] 부모\n  - [/] 다른 곳에서 끝난 일\n"
        ))
        git(self.root, "commit", "-q", "-am", "dup")
        git(self.root, "checkout", "-q", "main")
        commit, _ = origin_main_state(self.root)
        self.assertEqual(
            unmerged_branches(self.root, commit),
            [("feature/dup", ["- [/] 부모", "- [/] 다른 곳에서 끝난 일"], False)],
        )

    def test_inter_hunk_context_setting_does_not_shift_lines(self):
        self.make_stale_main()
        git(self.root, "config", "diff.interHunkContext", "20")
        git(self.root, "checkout", "-q", "-b", "feature/two", "refs/remotes/origin/main")
        self.write("worklog/TASK_TREE.md", (
            "- [/] 위에 더한 일\n# 작업 트리\n\n- [/] 다른 곳에서 끝난 일\n\n- [/] 아래에 더한 일\n"
        ))
        git(self.root, "commit", "-q", "-am", "two")
        git(self.root, "checkout", "-q", "main")
        commit, _ = origin_main_state(self.root)
        self.assertEqual(
            unmerged_branches(self.root, commit),
            [("feature/two", ["- [/] 위에 더한 일", "- [/] 아래에 더한 일"], False)],
        )

    def test_remote_diff_failure_keeps_local_nodes(self):
        git(self.root, "checkout", "-q", "-b", "feature/y")
        self.write("worklog/TASK_TREE.md", "# 작업 트리\n\n- [/] 진행 중인 일\n")
        git(self.root, "commit", "-q", "-am", "start")
        git(self.root, "checkout", "-q", "main")
        # 공통 조상이 없는 origin/main을 만든다(얕은 클론 등).
        git(self.root, "checkout", "-q", "--orphan", "unrelated")
        git(self.root, "commit", "-q", "-m", "unrelated")
        git(self.root, "update-ref", "refs/remotes/origin/main", "unrelated")
        git(self.root, "checkout", "-q", "main")
        commit, _ = origin_main_state(self.root)
        self.assertEqual(unmerged_branches(self.root, commit), [("feature/y", ["- [/] 진행 중인 일"], True)])

    def assert_new_branch_without_inherited_node(self):
        git(self.root, "checkout", "-q", "-b", "feature/new", "refs/remotes/origin/main")
        self.write("other.md", "# 다른 문서\n")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "work")
        git(self.root, "checkout", "-q", "main")
        _, text = run_main(str(self.root), "--no-audit", "--no-fetch")
        self.assertIn("- feature/new", text)
        self.assertNotIn("다른 곳에서 끝난 일", text)

    def test_same_named_tag_does_not_shadow_refs(self):
        self.make_stale_main()
        git(self.root, "tag", "origin/main", "main")
        git(self.root, "tag", "main", "refs/remotes/origin/main")
        commit, behind = origin_main_state(self.root)
        self.assertEqual(behind, 2)
        self.assertIsNotNone(commit)
        self.assertEqual(unmerged_branches(self.root, commit), [])
        _, text = run_main(str(self.root), "--no-audit", "--no-fetch")
        self.assertNotIn("Merge z", text)  # 최근 머지는 main 태그가 아닌 로컬 main 브랜치 기준이다.


class PendingReferencesTest(TempDir):
    def test_pending_states_only(self):
        self.write("reference/INDEX.md", (
            "# reference 색인\n\n"
            "- [a/](a/) - `처리 대기` 아직 통합 전\n"
            "- [b.md](b.md) - `보관용` 보관\n"
            "- [c.md](c.md) - `미등록`\n"
        ))
        items = pending_references(self.root)
        self.assertEqual([i.split(" ")[0] for i in items], ["[a/](a/)", "[c.md](c.md)"])

    def test_all_index_pages_in_order(self):
        self.write("reference/INDEX.md", "- [a.md](a.md) - `미등록`\n")
        self.write("reference/INDEX2.md", "- [b.md](b.md) - `처리 대기`\n")
        self.write("reference/INDEX10.md", "- [c.md](c.md) - `미등록`\n")
        self.write("reference/INDEX.yaml", "- [z.md](z.md) - `미등록`\n")
        items = pending_references(self.root)
        self.assertEqual([i.split(" ")[0] for i in items], ["[a.md](a.md)", "[b.md](b.md)", "[c.md](c.md)"])

    def test_no_reference_folder(self):
        self.assertEqual(pending_references(self.root), [])


class ParseAuditTest(unittest.TestCase):
    def test_summary_violations_and_reference_warnings(self):
        out = (
            "VIOLATION [link] a.md: 깨진 링크\n"
            "WARNING   [size] b.md: 분량\n"
            "WARNING   [index] reference/INDEX.yaml: 대상 자료가 없다\n"
            "\n감사 완료: 위반 1건, 경고 2건 (/x)\n"
        )
        self.assertEqual(parse_audit(1, out), [
            "감사 완료: 위반 1건, 경고 2건 (/x)",
            "VIOLATION [link] a.md: 깨진 링크",
            "WARNING   [index] reference/INDEX.yaml: 대상 자료가 없다",
        ])

    def test_missing_summary_reported(self):
        self.assertIn("요약 줄을 찾지 못했다", parse_audit(1, "Traceback ...\n")[0])


class RenderTest(unittest.TestCase):
    def test_marker_first_and_limit_cut_on_line(self):
        text = render([("짧은 절", ["판정"]), ("긴 절", ["x" * 300] * 100)])
        self.assertTrue(text.startswith(MARKER))
        self.assertLessEqual(len(text), MAX_CHARS)
        self.assertIn("## 짧은 절\n판정", text)
        self.assertNotIn("x" * 300 + "...", text)
        self.assertTrue(text.rstrip().endswith("로 본다."))


class MainTest(TempRepo):
    def test_no_remote_reported_and_exit_zero(self):
        code, text = run_main(str(self.root), "--no-audit")
        self.assertEqual(code, 0)
        self.assertTrue(text.startswith(MARKER))
        self.assertIn("origin 원격이 없다", text)

    def test_judgement_sections_precede_merge_list(self):
        self.merge_branch("docs/x", {"x.md": "# x\n"}, "Merge x")
        _, text = run_main(str(self.root), "--no-audit", "--no-fetch")
        self.assertLess(text.index("## 의미 감사 트리거"), text.index("## main의 최근 머지"))

    def test_no_fetch_passed_to_doc_lookup(self):
        self.merge_branch("docs/x", {"x.md": "# x\n"}, "Merge x")
        original = session_brief.main_doc_summaries
        for argv, offline in ((["--no-fetch"], True), ([], False)):
            with mock.patch.object(session_brief, "main_doc_summaries", wraps=original) as summaries:
                _, text = run_main(str(self.root), "--no-audit", *argv)
            self.assertEqual(summaries.call_args.args[2], offline)
            self.assertIn("  - x.md - x", text)

    def test_missing_main_reported_not_empty(self):
        git(self.root, "branch", "-m", "main", "trunk")
        _, text = run_main(str(self.root), "--no-audit", "--no-fetch")
        self.assertIn("로컬 main 브랜치가 없어", text)
        self.assertIn("수집 실패: main의 최근 머지 조회", text)

    def test_hook_json_wraps_brief_in_ascii(self):
        code, raw = run_main(str(self.root), "--no-audit", "--no-fetch", "--hook-json")
        self.assertEqual(code, 0)
        self.assertTrue(raw.isascii())
        data = json.loads(raw)
        self.assertEqual(data["hookSpecificOutput"]["hookEventName"], "SessionStart")
        self.assertTrue(data["hookSpecificOutput"]["additionalContext"].startswith(MARKER))

    def test_header_names_main_repo_even_in_worktree(self):
        wt = self.root.parent / (self.root.name + "-wt")
        git(self.root, "worktree", "add", "-q", "--detach", str(wt))
        self.addCleanup(lambda: git(self.root, "worktree", "remove", "--force", str(wt)))
        _, text = run_main(str(wt), "--no-audit", "--no-fetch")
        self.assertTrue(text.startswith(f"{MARKER} 세션 시작 요약: {self.root.name}\n"))

    def test_usage_error(self):
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main([str(self.root / "없는 폴더")]), 2)


def ext_command(*argv):
    """git ext:: 원격 주소. 인자 사이는 공백, 인자 안의 공백과 %는 %로 이스케이프한다."""
    return "ext::" + " ".join(a.replace("%", "%%").replace(" ", "% ") for a in argv)


class FetchTimeoutTest(TempRepo):
    def test_slow_remote_cut_at_timeout(self):
        # 원격 도우미가 출력 없이 오래 머무는 원격. 상한에 끊겨야 한다.
        git(self.root, "config", "protocol.ext.allow", "always")
        git(self.root, "remote", "add", "origin", ext_command(sys.executable, "-c", "import time; time.sleep(8)"))
        started = time.monotonic()
        with mock.patch.object(session_brief, "FETCH_TIMEOUT", 1):
            line = session_brief.fetch(self.root)
        self.assertLess(time.monotonic() - started, 5)
        self.assertIn("1초 초과", line)


FAKE_SEMANTIC = "print('미충족: 시험')\n"


class AuditOverlapTest(TempRepo):
    """형식 감사를 다른 단계와 겹쳐 돌리고, 제한 시간에 자식 트리까지 정리한다."""

    def setUp(self):
        super().setUp()
        tools = tempfile.TemporaryDirectory()
        self.addCleanup(tools.cleanup)
        self.tools = Path(tools.name).resolve()
        (self.tools / "check_semantic_audit.py").write_text(FAKE_SEMANTIC, encoding="utf-8")
        patcher = mock.patch.object(session_brief, "TOOLS_DIR", self.tools)
        patcher.start()
        self.addCleanup(patcher.stop)

    def fake_audit(self, body):
        (self.tools / "audit.py").write_text(body, encoding="utf-8")

    def test_audit_overlaps_later_steps(self):
        # 감사 3초, 확장 1.5초, 의미 감사 판정 1.5초. 감사가 앞뒤 단계와 모두 겹쳐야 4초 안에 끝난다.
        self.fake_audit("import time\ntime.sleep(3)\nprint('감사 완료: 위반 0건, 경고 0건 (x)')\n")
        (self.tools / "check_semantic_audit.py").write_text("import time\ntime.sleep(1.5)\n" + FAKE_SEMANTIC, encoding="utf-8")
        self.write("AGENTS/session-brief/slow.py", "import time\ntime.sleep(1.5)\nprint('확장 끝')\n")
        started = time.monotonic()
        _, text = run_main(str(self.root), "--no-fetch")
        self.assertLess(time.monotonic() - started, 4.2)
        self.assertIn("## 의미 감사 트리거\n미충족: 시험", text)
        self.assertIn("## 형식 감사\n감사 완료: 위반 0건, 경고 0건 (x)", text)
        self.assertIn("확장 끝", text)
        self.assertLess(text.index("## 확장: slow"), text.index("## 형식 감사"))
        self.assertLess(text.index("## 형식 감사"), text.index("## 의미 감사 트리거"))

    def test_audit_timeout_kills_child_tree(self):
        marker = self.root.parent / (self.root.name + "-alive")
        self.addCleanup(lambda: marker.exists() and marker.unlink())
        # 감사가 띄운 자식은 2초 뒤 표지 파일을 만든다. 제한 시간에 함께 정리되면 파일이 생기지 않는다.
        self.fake_audit(
            "import subprocess, sys, tempfile, time\n"
            "code = 'import pathlib, sys, time; time.sleep(2); pathlib.Path(sys.argv[1]).write_text(\"x\")'\n"
            f"subprocess.Popen([sys.executable, '-c', code, {str(marker)!r}], cwd=tempfile.gettempdir())\n"
            "time.sleep(30)\n"
        )
        started = time.monotonic()
        with mock.patch.object(session_brief, "AUDIT_TIMEOUT", 1):
            _, text = run_main(str(self.root), "--no-fetch")
        self.assertLess(time.monotonic() - started, 6)
        self.assertIn("audit.py가 1초 안에 끝나지 않았다", text)
        time.sleep(max(0.0, 3.5 - (time.monotonic() - started)))
        self.assertFalse(marker.exists(), "시간 초과 뒤에도 감사의 자식 프로세스가 남았다")

    def test_audit_failure_output_kept(self):
        self.fake_audit("import sys\nsys.stderr.write('Traceback 시험\\n')\nsys.exit(3)\n")
        _, text = run_main(str(self.root), "--no-fetch")
        self.assertIn("audit.py 종료 코드 3, 요약 줄을 찾지 못했다", text)

    def test_finished_result_accepted_when_collected_after_timeout(self):
        # 제한 시간은 거둘 때 적용한다. 그 전에 이미 끝났으면 늦게 거둬도 정상 결과다.
        self.fake_audit("print('감사 완료: 위반 0건, 경고 0건 (x)')\n")
        run = session_brief.ToolRun("audit.py", self.root, 0.5)
        deadline = time.monotonic() + 10
        while run.run.proc.poll() is None and time.monotonic() < deadline:
            time.sleep(0.05)
        time.sleep(max(0.0, 0.6 - (time.monotonic() - run.run.started)))
        self.assertEqual(run.result(), (0, "감사 완료: 위반 0건, 경고 0건 (x)\n"))

    def test_streams_decoded_separately_with_newlines_normalized(self):
        # stdout 끝과 stderr 앞에 나뉜 바이트가 한 글자(€)로 합쳐지지 않고, CRLF는 LF가 된다.
        self.fake_audit(
            "import sys\n"
            "sys.stdout.buffer.write(b'out\\r\\n\\xe2\\x82')\n"
            "sys.stderr.buffer.write(b'\\xac err\\r\\n')\n"
        )
        code, text = session_brief.run_tool("audit.py", self.root, 30)
        self.assertEqual(code, 0)
        self.assertNotIn("\r", text)
        self.assertNotIn("€", text)
        self.assertTrue(text.startswith("out\n"))
        self.assertTrue(text.endswith(" err\n"))


class WorkingFolderPathTest(TempRepo):
    """요약의 규범 문서와 감사 위반 경로를 작업 폴더 기준으로 적는다."""

    def chdir(self, path):
        old = os.getcwd()
        os.chdir(path)
        self.addCleanup(os.chdir, old)

    def brief(self):
        rule = self.root / "AGENTS" / "epistemic-rules" / "session-boundaries.md"
        with mock.patch.object(session_brief, "RULE_DOC", rule):
            return render([("절", ["x"])], self.root)

    def test_container_folder_prefixes_repo(self):
        self.chdir(self.root.parent)
        self.assertEqual(session_brief.cwd_prefix(self.root), self.root.name + "/")
        self.assertIn(f"\n{self.root.name}/AGENTS/epistemic-rules/session-boundaries.md \"세션 시작\"", self.brief())

    def test_inside_repo_unchanged(self):
        sub = self.root / "sub"
        sub.mkdir()
        for cwd in (self.root, sub):
            self.chdir(cwd)
            self.assertEqual(session_brief.cwd_prefix(self.root), "")
            self.assertIn("\nAGENTS/epistemic-rules/session-boundaries.md \"세션 시작\"", self.brief())

    def test_unrelated_folder_unchanged(self):
        other = tempfile.TemporaryDirectory()
        self.addCleanup(other.cleanup)
        self.chdir(other.name)
        self.assertEqual(session_brief.cwd_prefix(self.root), "")
        self.assertIn("\nAGENTS/epistemic-rules/session-boundaries.md \"세션 시작\"", self.brief())

    def test_relpath_failure_falls_back_to_repo(self):
        self.chdir(self.root.parent)
        with mock.patch.object(session_brief.os.path, "relpath", side_effect=ValueError("drive")):
            self.assertEqual(session_brief.cwd_prefix(self.root), "")

    def test_audit_paths_prefixed_keeping_line_format(self):
        out = (
            "VIOLATION [link] a b/c.md: 깨진 링크: x.md\n"
            "VIOLATION [ext:x] .: 레포 전체\n"
            "WARNING   [index] reference/INDEX.yaml: 대상 자료가 없다\n"
            "\n감사 완료: 위반 2건, 경고 1건 (/x)\n"
        )
        self.assertEqual(parse_audit(1, out, "repo/"), [
            "감사 완료: 위반 2건, 경고 1건 (/x)",
            "VIOLATION [link] repo/a b/c.md: 깨진 링크: x.md",
            "VIOLATION [ext:x] repo: 레포 전체",
            "WARNING   [index] repo/reference/INDEX.yaml: 대상 자료가 없다",
        ])
        self.assertEqual(parse_audit(1, out)[1], "VIOLATION [link] a b/c.md: 깨진 링크: x.md")

    def test_dot_colon_file_name_is_ordinary_path(self):
        out = "VIOLATION [link] .:notes.md: 깨진 링크\n감사 완료: 위반 1건, 경고 0건 (/x)\n"
        self.assertEqual(parse_audit(1, out, "repo/")[1], "VIOLATION [link] repo/.:notes.md: 깨진 링크")


class CatFileParseTest(unittest.TestCase):
    """cat-file --batch 응답이 선언한 모양과 어긋나면 절 전체를 수집 실패(None)로 둔다.
    missing이 있으면 ls-tree로 main 트리에 그 경로가 정말 없는지 본다."""

    def fake(self, code, stdout):
        run = mock.Mock()
        run.wait.return_value = code
        run.output.return_value = stdout
        return run

    def parse(self, stdout, rels=("a.md",), code=0, tree=None, tree_code=0, offline=False):
        runs = [self.fake(code, stdout)]
        if tree is not None:
            runs.append(self.fake(tree_code, tree))
        with mock.patch.object(session_brief, "Spawn", side_effect=runs) as spawn:
            result = session_brief.main_doc_summaries(Path("."), list(rels), offline)
        for run in runs:
            run.close.assert_called()
        return result, spawn

    def test_well_formed(self):
        body = "# 가\n".encode("utf-8")
        result, spawn = self.parse(b"abc blob %d\n" % len(body) + body + b"\nrefs/heads/main:b c.md missing\n",
                                   ("a.md", "b c.md"), tree=b"")
        self.assertEqual(result, ["가", None])
        cmd, _, env, timeout, data = spawn.call_args_list[0].args
        self.assertEqual(cmd, ["git", "cat-file", "--batch"])
        self.assertEqual(timeout, session_brief.GIT_TIMEOUT)
        self.assertEqual(data, "refs/heads/main:a.md\nrefs/heads/main:b c.md\n".encode("utf-8"))
        cmd, _, tree_env, timeout = spawn.call_args_list[1].args
        self.assertEqual(cmd[-3:], ["refs/heads/main", "--", "b c.md"])
        self.assertIn("ls-tree", cmd)
        self.assertIs(tree_env, env)
        self.assertEqual(timeout, session_brief.GIT_TIMEOUT)

    def test_caller_lazy_fetch_setting_kept(self):
        with mock.patch.dict(os.environ, {"GIT_NO_LAZY_FETCH": "1"}), \
                mock.patch.dict(session_brief.GIT_ENV, {"GIT_NO_LAZY_FETCH": "1"}):
            _, spawn = self.parse(b"refs/heads/main:a.md missing\n", tree=b"")
            # GIT_ENV 객체를 그대로 넘기므로 패치가 풀리기 전에 확인한다.
            self.assertEqual(spawn.call_args_list[0].args[2]["GIT_NO_LAZY_FETCH"], "1")

    def test_offline_disables_lazy_fetch(self):
        # 사용자 셸의 설정에 흔들리지 않게 초기 환경을 고정한다.
        clean = {k: v for k, v in session_brief.GIT_ENV.items()
                 if k not in ("GIT_NO_LAZY_FETCH", "GIT_ALLOW_PROTOCOL")}
        with mock.patch.object(session_brief, "GIT_ENV", clean):
            _, spawn = self.parse(b"abc blob 4\n# x\n\n", offline=True)
            env = spawn.call_args.args[2]
            self.assertEqual(env["GIT_NO_LAZY_FETCH"], "1")
            self.assertEqual(env["GIT_ALLOW_PROTOCOL"], "")
            self.assertNotIn("GIT_NO_LAZY_FETCH", session_brief.GIT_ENV)
            self.assertNotIn("GIT_ALLOW_PROTOCOL", session_brief.GIT_ENV)

    def test_no_missing_skips_ls_tree(self):
        result, spawn = self.parse(b"abc blob 4\n# x\n\n")
        self.assertEqual(result, ["x"])
        self.assertEqual(spawn.call_count, 1)

    def test_missing_but_in_main_tree_is_collection_failure(self):
        # 부분 클론에서 지연 fetch가 꺼져 본문만 로컬에 없는 경우다.
        self.assertIsNone(self.parse(b"refs/heads/main:a.md missing\n", tree=b"a.md\0")[0])

    def test_ls_tree_failure_is_collection_failure(self):
        self.assertIsNone(self.parse(b"refs/heads/main:a.md missing\n", tree=b"", tree_code=128)[0])
        self.assertIsNone(self.parse(b"refs/heads/main:a.md missing\n", tree=b"", tree_code=None)[0])

    def test_timeout_or_failure_is_collection_failure(self):
        self.assertIsNone(self.parse(b"", code=None)[0])
        self.assertIsNone(self.parse(b"", code=128)[0])

    def test_short_body(self):
        self.assertIsNone(self.parse(b"abc blob 10\n# x\n")[0])

    def test_missing_separator(self):
        self.assertIsNone(self.parse(b"abc blob 4\n# x\nX")[0])

    def test_trailing_bytes(self):
        self.assertIsNone(self.parse(b"abc blob 4\n# x\n\nextra\n")[0])


class ProcessCleanupTest(unittest.TestCase):
    """중단과 정리 실패에도 자식 트리를 정리하고, 정리가 요약을 붙잡거나 죽이지 않는다."""

    def test_kill_tree_bounded_and_never_raises(self):
        proc = mock.Mock(pid=12345)
        proc.wait.side_effect = subprocess.TimeoutExpired("x", 5)
        with mock.patch.object(session_brief.subprocess, "run", side_effect=subprocess.TimeoutExpired("taskkill", 5)) as run, \
                mock.patch.object(session_brief.os, "killpg", side_effect=OSError, create=True):
            session_brief.kill_tree(proc)
        if os.name == "nt":
            self.assertLessEqual(run.call_args.kwargs["timeout"], 5)
        self.assertLessEqual(proc.wait.call_args.kwargs["timeout"], 5)

    def interrupted_proc(self):
        proc = mock.Mock(pid=12345)
        proc.wait.side_effect = KeyboardInterrupt
        proc.poll.return_value = None
        return proc

    def test_git_quiet_interrupt_kills_tree(self):
        proc = self.interrupted_proc()
        with mock.patch.object(session_brief.subprocess, "Popen", return_value=proc), \
                mock.patch.object(session_brief, "kill_tree") as kill:
            with self.assertRaises(KeyboardInterrupt):
                session_brief.git_quiet(Path("."), "fetch", timeout=1)
        kill.assert_called_with(proc)

    def test_tool_run_interrupt_kills_tree(self):
        proc = self.interrupted_proc()
        with mock.patch.object(session_brief.subprocess, "Popen", return_value=proc), \
                mock.patch.object(session_brief, "kill_tree") as kill:
            run = session_brief.ToolRun("audit.py", Path("."), 1)
            with self.assertRaises(KeyboardInterrupt):
                run.result()
        kill.assert_called_with(proc)

    def test_close_twice_kills_tree_once(self):
        proc = mock.Mock(pid=12345)
        proc.poll.return_value = None
        proc.wait.side_effect = subprocess.TimeoutExpired("x", 0)
        with mock.patch.object(session_brief.subprocess, "Popen", return_value=proc), \
                mock.patch.object(session_brief, "kill_tree") as kill:
            run = session_brief.ToolRun("audit.py", Path("."), 0)
            self.assertEqual(run.result()[0], -1)  # 시간 초과 정리 뒤 result의 finally가 close를 부른다.
            run.close()  # main의 finally
            run.close()
        self.assertEqual(kill.call_count, 1)

    def test_timeout_kills_tree_even_if_child_just_exited(self):
        # 직접 자식이 시간 초과 직후 끝나도 그 하위 프로세스가 남을 수 있어 정리를 시도한다.
        proc = mock.Mock(pid=12345)
        proc.wait.side_effect = subprocess.TimeoutExpired("x", 0)
        proc.poll.return_value = 0
        with mock.patch.object(session_brief.subprocess, "Popen", return_value=proc), \
                mock.patch.object(session_brief, "kill_tree") as kill:
            run = session_brief.Spawn(["x"], None, {}, 0)
            self.assertIsNone(run.wait())
            run.close()
        kill.assert_called_once_with(proc)

    def test_git_quiet_discards_output_without_temp_files(self):
        proc = mock.Mock(pid=12345)
        proc.wait.return_value = 0
        proc.poll.return_value = 0
        with mock.patch.object(session_brief.tempfile, "TemporaryFile", side_effect=OSError("쓰기 불가")), \
                mock.patch.object(session_brief.subprocess, "Popen", return_value=proc) as popen:
            self.assertEqual(session_brief.git_quiet(Path("."), "fetch", timeout=1), 0)
        self.assertIs(popen.call_args.kwargs["stdout"], subprocess.DEVNULL)
        self.assertIs(popen.call_args.kwargs["stderr"], subprocess.DEVNULL)

    def test_spawn_timeout_kills_tree(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        marker = Path(tmp.name) / "alive"
        code = (
            "import subprocess, sys, tempfile, time\n"
            "child = 'import pathlib, sys, time; time.sleep(2); pathlib.Path(sys.argv[1]).write_text(\"x\")'\n"
            f"subprocess.Popen([sys.executable, '-c', child, {str(marker)!r}], cwd=tempfile.gettempdir())\n"
            "sys.stdin.read()\n"
            "time.sleep(30)\n"
        )
        started = time.monotonic()
        run = session_brief.Spawn([sys.executable, "-c", code], None, dict(os.environ), 1, b"input\n")
        try:
            self.assertIsNone(run.wait())
        finally:
            run.close()
        self.assertLess(time.monotonic() - started, 6)
        time.sleep(max(0.0, 3.5 - (time.monotonic() - started)))
        self.assertFalse(marker.exists(), "시간 초과 뒤에도 자식 프로세스가 남았다")

    def test_temp_file_failure_reported_and_first_file_closed(self):
        first = tempfile.TemporaryFile()
        self.addCleanup(first.close)
        with mock.patch.object(session_brief.tempfile, "TemporaryFile", side_effect=[first, OSError("디스크")]), \
                mock.patch.object(session_brief.subprocess, "Popen") as popen:
            code, text = session_brief.ToolRun("audit.py", Path("."), 1).result()
        self.assertEqual(code, -1)
        self.assertIn("audit.py 실행 실패", text)
        self.assertTrue(first.closed)
        popen.assert_not_called()


class ExtensionTest(TempRepo):
    """AGENTS/session-brief/ 확장 스크립트의 실행과 실패 격리."""

    def ext(self, name, body):
        self.write(f"AGENTS/session-brief/{name}", body)

    def test_extension_output_precedes_judgement_sections(self):
        self.ext("machine.py", "import sys\nprint('머신: 시험 머신')\nprint('루트 ' + sys.argv[1])\n")
        _, text = run_main(str(self.root), "--no-audit", "--no-fetch")
        self.assertIn("## 확장: machine\n머신: 시험 머신\n루트 ", text)
        self.assertLess(text.index("## 확장: machine"), text.index("## 의미 감사 트리거"))

    def test_extensions_run_in_name_order_and_helpers_skipped(self):
        self.ext("b.py", "print('b')\n")
        self.ext("a.py", "print('a')\n")
        self.ext("_helper.py", "print('helper')\n")
        self.ext("notes.txt", "텍스트\n")
        _, text = run_main(str(self.root), "--no-audit", "--no-fetch")
        self.assertLess(text.index("## 확장: a"), text.index("## 확장: b"))
        self.assertNotIn("helper", text)
        self.assertNotIn("notes", text)

    def test_failing_extension_reported_and_others_run(self):
        self.ext("a.py", "import sys\nprint('버릴 출력')\nsys.stderr.write('원인 줄\\n')\nsys.exit(3)\n")
        self.ext("b.py", "print('남는 출력')\n")
        _, text = run_main(str(self.root), "--no-audit", "--no-fetch")
        self.assertIn("수집 실패: 확장 a.py 종료 코드 3: 원인 줄", text)
        self.assertNotIn("버릴 출력", text)
        self.assertIn("남는 출력", text)

    def test_timeout_reported(self):
        self.ext("slow.py", "import time\ntime.sleep(5)\n")
        with mock.patch.object(session_brief, "EXTENSION_TIMEOUT", 1):
            _, text = run_main(str(self.root), "--no-audit", "--no-fetch")
        self.assertIn("수집 실패: 확장 slow.py가 1초 안에 끝나지 않았다", text)

    def section(self, text, name):
        return text.split(f"## 확장: {name}\n", 1)[1].split("\n\n## ", 1)[0]

    def test_extension_output_capped(self):
        self.ext("big.py", "for i in range(500):\n    print('x' * 40)\n")
        _, text = run_main(str(self.root), "--no-audit", "--no-fetch")
        section = self.section(text, "big")
        self.assertLessEqual(len(section), session_brief.EXTENSION_MAX_CHARS)
        self.assertIn("확장 출력이 길어 잘랐다", section)

    def test_single_long_line_kept_up_to_cap(self):
        self.ext("line.py", "print('y' * 5000)\n")
        _, text = run_main(str(self.root), "--no-audit", "--no-fetch")
        section = self.section(text, "line")
        self.assertIn("y" * 100, section)
        self.assertLessEqual(len(section), session_brief.EXTENSION_MAX_CHARS)

    def test_total_cap_keeps_judgement_sections(self):
        for name in "abcdef":
            self.ext(f"{name}.py", "for i in range(60):\n    print('z' * 39)\n")
        _, text = run_main(str(self.root), "--no-audit", "--no-fetch")
        self.assertIn("확장 출력 합계 상한", text)
        self.assertIn("## 의미 감사 트리거", text)
        self.assertIn("## main에 머지되지 않은 브랜치와 그 진행 노드", text)
        self.assertLessEqual(len(text), MAX_CHARS)

    def test_total_time_budget_skips_rest(self):
        self.ext("a.py", "import time\ntime.sleep(2)\n")
        self.ext("b.py", "print('b')\n")
        with mock.patch.object(session_brief, "EXTENSION_TOTAL_BUDGET", 1):
            _, text = run_main(str(self.root), "--no-audit", "--no-fetch")
        self.assertIn("수집 실패: 확장 a.py가 1초 안에 끝나지 않았다", text)
        self.assertIn("실행 생략: 확장 전체 시간 예산", self.section(text, "b"))

    def test_timeout_holds_when_grandchild_keeps_running(self):
        self.ext("spawn.py", (
            "import subprocess, sys, tempfile, time\n"
            "subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(8)'], cwd=tempfile.gettempdir())\n"
            "time.sleep(30)\n"
        ))
        started = time.monotonic()
        with mock.patch.object(session_brief, "EXTENSION_TIMEOUT", 1):
            _, text = run_main(str(self.root), "--no-audit", "--no-fetch")
        self.assertLess(time.monotonic() - started, 6)
        self.assertIn("수집 실패: 확장 spawn.py가 1초 안에 끝나지 않았다", text)


class RepoNameTest(unittest.TestCase):
    def test_common_dir_shapes(self):
        root = Path("/x/wt")
        cases = {
            "/w/proj/.git": "proj",
            "/w/super/.git/modules/libsub": "libsub",
            "/w/super/.git/worktrees/t/modules/scaffold": "scaffold",
            "/w/myproj.git": "myproj",
            "/w/odd": "wt",
        }
        for common, expected in cases.items():
            self.assertEqual(session_brief.name_from_common_dir(Path(common), root), expected, common)


class TruncationNoteTest(unittest.TestCase):
    def test_dropped_sections_named(self):
        text = render([("앞 절", ["x" * 100] * 120), ("뒤 판정", ["충족"])])
        self.assertLessEqual(len(text), MAX_CHARS)
        self.assertIn("잘린 절: 뒤 판정", text)


class SetupSectionTest(TempRepo):
    def test_setup_section_after_semantic(self):
        _, text = run_main(str(self.root), "--no-audit", "--no-fetch")
        a, b, c = (text.index(h) for h in ("## 의미 감사 트리거", "## 환경 갱신", "## reference 미처리 항목"))
        self.assertLess(a, b)
        self.assertLess(b, c)

    def test_setup_section_failure_isolated(self):
        with mock.patch.object(session_brief._setup_core, "status_lines", side_effect=RuntimeError("x")):
            code, text = run_main(str(self.root), "--no-audit", "--no-fetch")
        self.assertEqual(code, 0)
        section = text.split("## 환경 갱신\n", 1)[1].split("\n\n", 1)[0]
        self.assertTrue(section.startswith("수집 실패:"))


def git_bash():
    """Git Bash 경로. 없거나 WSL bash만 있으면 None."""
    import shutil
    path = shutil.which("bash")
    if not path or path.lower().replace("/", "\\").endswith("system32\\bash.exe"):
        return None
    return path


class IsolationTest(unittest.TestCase):
    def test_module_isolated_from_global_and_system_git_config(self):
        self.assertEqual(os.environ.get("GIT_CONFIG_NOSYSTEM"), "1")
        self.assertTrue(os.environ["GIT_CONFIG_GLOBAL"].startswith(_HOME.name))


class HookCommandTest(TempRepo):
    """출고 .claude/settings.json의 SessionStart 명령(startup|clear, compact)을 임시 홈으로 돌린다."""

    def setUp(self):
        super().setUp()
        import shutil
        self.bash = git_bash()
        if self.bash is None or not shutil.which("git"):
            self.skipTest("Git Bash와 git이 필요하다")
        rules_dir = Path(__file__).resolve().parents[2]
        scaffold_root = Path(__file__).resolve().parents[4]
        settings = json.loads((scaffold_root / ".claude" / "settings.json").read_text(encoding="utf-8"))
        self.commands = [group["hooks"][0]["command"] for group in settings["hooks"]["SessionStart"]]
        shutil.copytree(rules_dir, self.root / "AGENTS" / "epistemic-rules",
                        ignore=shutil.ignore_patterns("__pycache__", "tests", ".superpowers"))
        home_tmp = tempfile.TemporaryDirectory()
        self.addCleanup(home_tmp.cleanup)
        self.home = Path(home_tmp.name) / "hook home"
        self.home.mkdir()
        self.tool_dirs = sorted({os.path.dirname(shutil.which(n)) for n in ("bash", "git")})

    def run_hook(self, command, path_dirs):
        env = dict(os.environ, CLAUDE_PROJECT_DIR=str(self.root), HOME=str(self.home),
                   USERPROFILE=str(self.home), PATH=os.pathsep.join(path_dirs))
        return subprocess.run([self.bash, "-c", command], capture_output=True, env=env, timeout=120).stdout

    def test_hook_command_has_no_stored_python(self):
        self.assertEqual(len(self.commands), 2)
        for command in self.commands:
            for needle in (".epis" + "temic", "EPISTEMIC" + "_HOME", "epistemic" + ".python"):
                self.assertNotIn(needle, command)
            self.assertIn("for c in python3 python 'py -3'", command)

    def test_python_on_path_used(self):
        for command in self.commands:
            out = self.run_hook(command, [os.path.dirname(sys.executable), *self.tool_dirs])
            data = json.loads(out.decode("ascii"))
            self.assertTrue(data["hookSpecificOutput"]["additionalContext"].startswith(MARKER))
        self.assertEqual(list(self.home.iterdir()), [])

    def test_first_install_guidance_without_python(self):
        import shutil
        bare = os.pathsep.join(self.tool_dirs)
        if any(shutil.which(n, path=bare) for n in ("python3", "python", "py")):
            self.skipTest("bash와 git이 든 폴더에 Python도 있어 Python 없는 PATH를 만들 수 없다")
        for command in self.commands:
            out = self.run_hook(command, self.tool_dirs).decode("ascii")
            self.assertIn("AGENTS/epistemic-rules/workspace-setup.md (first install)", out)


if __name__ == "__main__":
    unittest.main()

"""세션 시작 요약 시험 (문서 요약, 최근 머지, 머지 전 브랜치, reference 미처리, 감사 출력 파싱, 출력 상한, 수집 실패 표시)."""

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import session_brief  # noqa: E402

from session_brief import (  # noqa: E402
    MARKER, MAX_CHARS, MAX_DOCS_PER_MERGE, doc_summary, main, merge_lines,
    parse_audit, pending_references, recent_merges, render, unmerged_branches,
)


def git(root, *args):
    subprocess.run(
        ["git", "-c", "core.autocrlf=false", *args], cwd=root, check=True,
        capture_output=True,
    )


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
        p.write_text(text, encoding="utf-8", newline="\n")


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


class DocSummaryTest(TempDir):
    def test_description_preferred(self):
        self.write("a.md", "---\ndescription: 요약 한 줄\n---\n\n# 제목\n")
        self.assertEqual(doc_summary(self.root / "a.md"), "요약 한 줄")

    def test_heading_fallback(self):
        self.write("b.md", "---\ntags: [x]\n---\n\n# 제목만 있다\n")
        self.assertEqual(doc_summary(self.root / "b.md"), "제목만 있다")

    def test_crlf_front_matter(self):
        crlf = "---\r\ndescription: 줄바꿈 CRLF\r\n---\r\n"
        (self.root / "d.md").write_bytes(crlf.encode("utf-8"))
        self.assertEqual(doc_summary(self.root / "d.md"), "줄바꿈 CRLF")

    def test_missing_file(self):
        self.assertIsNone(doc_summary(self.root / "none.md"))

    def test_long_summary_truncated(self):
        self.write("c.md", "---\ndescription: " + "가" * 500 + "\n---\n")
        self.assertLessEqual(len(doc_summary(self.root / "c.md")), 160)


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
        original = session_brief.main_doc_summary

        def counting(root, rel):
            calls.append(rel)
            return original(root, rel)

        with mock.patch.object(session_brief, "main_doc_summary", counting):
            docs = recent_merges(self.root, 1)[0][2]
        self.assertEqual(len(docs), MAX_DOCS_PER_MERGE + 5)
        self.assertEqual(len(calls), MAX_DOCS_PER_MERGE)

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
        self.assertEqual(unmerged_branches(self.root), [("feature/y", ["- [/] 진행 중인 일"])])


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

    def test_usage_error(self):
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main([str(self.root / "없는 폴더")]), 2)


if __name__ == "__main__":
    unittest.main()

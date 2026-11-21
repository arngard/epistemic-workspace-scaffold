"""세션 시작 요약 시험 (문서 요약 추출, 최근 머지, 머지 전 브랜치, reference 미처리, 출력 상한)."""

import contextlib
import io
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from session_brief import (  # noqa: E402
    MARKER, MAX_CHARS, doc_summary, main, pending_references, recent_merges,
    render, unmerged_branches,
)


def git(root, *args):
    subprocess.run(
        ["git", "-c", "core.autocrlf=false", *args], cwd=root, check=True,
        capture_output=True,
    )


class TempRepo(unittest.TestCase):
    """main 브랜치 하나를 가진 임시 git 레포."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name).resolve()
        git(self.root, "init", "-q", "-b", "main")
        git(self.root, "config", "user.email", "t@example.com")
        git(self.root, "config", "user.name", "t")
        self.write("worklog/TASK_TREE.md", "# 작업 트리\n")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "init")

    def write(self, rel, text):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8", newline="\n")

    def merge_branch(self, branch, files, subject):
        git(self.root, "checkout", "-q", "-b", branch)
        for rel, text in files.items():
            self.write(rel, text)
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "work")
        git(self.root, "checkout", "-q", "main")
        git(self.root, "merge", "-q", "--no-ff", "-m", subject, branch)


class DocSummaryTest(TempRepo):
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
        subject, docs = merges[0][1], merges[0][2]
        self.assertIn("문서를 더한다", subject)
        self.assertEqual(docs, [("문서 폴더/새 문서.md", "공백 든 경로")])

    def test_deleted_doc_marked(self):
        self.merge_branch("docs/a", {"gone.md": "# 곧 지운다\n"}, "Merge a")
        git(self.root, "checkout", "-q", "-b", "docs/b")
        git(self.root, "rm", "-q", "gone.md")
        git(self.root, "commit", "-q", "-m", "rm")
        git(self.root, "checkout", "-q", "main")
        git(self.root, "merge", "-q", "--no-ff", "-m", "Merge b", "docs/b")
        docs = recent_merges(self.root, 1)[0][2]
        self.assertEqual(docs, [("gone.md", None)])


class UnmergedBranchesTest(TempRepo):
    def test_in_progress_node_from_task_tree_diff(self):
        git(self.root, "checkout", "-q", "-b", "feature/y")
        self.write("worklog/TASK_TREE.md", "# 작업 트리\n\n- [/] 진행 중인 일\n  - 설명: x\n")
        git(self.root, "commit", "-q", "-am", "start")
        git(self.root, "checkout", "-q", "main")
        branches = unmerged_branches(self.root)
        self.assertEqual(branches, [("feature/y", ["- [/] 진행 중인 일"])])


class PendingReferencesTest(TempRepo):
    def test_pending_states_only(self):
        self.write("reference/INDEX.md", (
            "# reference 색인\n\n"
            "- [a/](a/) - `처리 대기` 아직 통합 전\n"
            "- [b.md](b.md) - `보관용` 보관\n"
            "- [c.md](c.md) - `미등록`\n"
        ))
        items = pending_references(self.root)
        self.assertEqual([i.split(" ")[0] for i in items], ["[a/](a/)", "[c.md](c.md)"])

    def test_no_reference_folder(self):
        self.assertEqual(pending_references(self.root), [])


class RenderTest(TempRepo):
    def test_marker_first_and_limit(self):
        sections = [("긴 절", ["x" * 300] * 100)]
        text = render(sections)
        self.assertTrue(text.startswith(MARKER))
        self.assertLessEqual(len(text), MAX_CHARS)

    def test_main_exits_zero_without_remote(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = main([str(self.root), "--no-audit"])
        self.assertEqual(code, 0)
        text = out.getvalue()
        self.assertTrue(text.startswith(MARKER))
        self.assertIn("fetch", text)


if __name__ == "__main__":
    unittest.main()

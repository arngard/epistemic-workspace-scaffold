"""migrate_layout.py의 경로 대응과 텍스트 변환 시험."""

import contextlib
import io
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from _index_core import IndexFormatError, load_index_yaml  # noqa: E402
from migrate_layout import (  # noqa: E402
    _inverse_path, _repair_links, convert_reference_table, main, map_path, migrate,
    rewrite_links, rewrite_mentions)

REPO_ROOT = Path(__file__).resolve().parents[4]


class MapPathTest(unittest.TestCase):
    def test_longest_prefix(self):
        self.assertEqual(map_path("_docs/_worklog/TASK_TREE.md"), "worklog/TASK_TREE.md")
        self.assertEqual(map_path("_docs/_strategy/a b.md"), "epistemic-structure/strategy/a b.md")
        self.assertEqual(map_path("_docs/AGENTS.md"), "epistemic-structure/AGENTS.md")
        self.assertEqual(map_path("_tmp/x"), ".tmp/x")
        self.assertEqual(map_path("AGENTS/folder-structure.md"), "AGENTS/epistemic-rules/folder-structure.md")

    def test_idempotent(self):
        self.assertEqual(map_path("worklog/STATUS.md"), "worklog/STATUS.md")


class Phase2MapTest(unittest.TestCase):
    def test_exact_and_prefix(self):
        self.assertEqual(map_path("AGENTS/folder-structure.md"), "AGENTS/epistemic-rules/folder-structure.md")
        self.assertEqual(map_path("AGENTS/unit-task-workflow.md"), "AGENTS/epistemic-rules/unit-task-workflow.md")
        self.assertEqual(map_path("AGENTS/unit-task/stage-authority.md"), "AGENTS/epistemic-rules/unit-task/stage-authority.md")
        self.assertEqual(map_path("AGENTS/tools/audit.py"), "AGENTS/epistemic-rules/tools/audit.py")
        self.assertEqual(map_path("AGENTS/AGENTS.md"), "AGENTS/AGENTS.md")
        self.assertEqual(map_path("AGENTS/my-custom.md"), "AGENTS/my-custom.md")

    def test_idempotent(self):
        self.assertEqual(map_path("AGENTS/epistemic-rules/tools/audit.py"), "AGENTS/epistemic-rules/tools/audit.py")

    def test_mentions(self):
        out, rep = rewrite_mentions("`python3 AGENTS/tools/audit.py .`와 `AGENTS/document-units.md`")
        self.assertEqual(out, "`python3 AGENTS/epistemic-rules/tools/audit.py .`와 `AGENTS/epistemic-rules/document-units.md`")
        self.assertEqual(rep, [])
        self.assertEqual(rewrite_mentions(out)[0], out)

    def test_mention_in_fence_reported(self):
        out, rep = rewrite_mentions("```\npython3 AGENTS/tools/audit.py .\n```\n")
        self.assertEqual([n for n, _ in rep], [2])


class Phase2bMapTest(unittest.TestCase):
    def test_chain_to_final(self):
        self.assertEqual(
            map_path("AGENTS/coding-guidelines.md"),
            "implementation/AGENTS/epistemic-rules/coding-guidelines.md")
        self.assertEqual(
            map_path("AGENTS/ingest-workflow/reference-folder.md"),
            "reference/AGENTS/epistemic-rules/reference-folder.md")
        self.assertEqual(
            map_path("AGENTS/epistemic-rules/coding-guidelines.md"),
            "implementation/AGENTS/epistemic-rules/coding-guidelines.md")

    def test_merged_doc_to_category_summary(self):
        dst = "epistemic-structure/AGENTS/epistemic-rules.md"
        self.assertEqual(map_path("AGENTS/epistemic-rules/how-to-separate-docs-folders.md"), dst)
        self.assertEqual(map_path("AGENTS/how-to-separate-docs-folders.md"), dst)

    def test_merged_doc_not_inverted(self):
        dst = "epistemic-structure/AGENTS/epistemic-rules.md"
        self.assertEqual(_inverse_path(dst), dst)

    def test_sibling_unaffected(self):
        self.assertEqual(
            map_path("AGENTS/ingest-workflow.md"),
            "AGENTS/epistemic-rules/ingest-workflow.md")


class RewriteLinksTest(unittest.TestCase):
    def test_depth_change_and_encoding(self):
        src = "[t](../_strategy/a%20b.md#절)"
        self.assertEqual(rewrite_links(src, "_docs/_worklog/TASK_TREE.md", "worklog/TASK_TREE.md"),
                         "[t](../epistemic-structure/strategy/a%20b.md#절)")

    def test_from_agents_to_worklog(self):
        self.assertEqual(rewrite_links("[x](../_docs/_worklog/TASK_TREE.md)", "AGENTS/a.md", "AGENTS/a.md"),
                         "[x](../worklog/TASK_TREE.md)")

    def test_untouched(self):
        for t in ["[a](https://x.y/_docs/z)", "[a](#절)", "[a](mailto:q@r)", "[a](../../outside/_docs/x.md)"]:
            self.assertEqual(rewrite_links(t, "AGENTS/a.md", "AGENTS/a.md"), t)

    def test_second_run_is_noop(self):
        once = rewrite_links("[x](../_docs/_worklog/TASK_TREE.md)", "AGENTS/a.md", "AGENTS/a.md")
        self.assertEqual(rewrite_links(once, "AGENTS/a.md", "AGENTS/a.md"), once)

    def test_moved_file_then_rerun_at_new_location(self):
        once = rewrite_links("[t](../_strategy/a%20b.md#s)", "_docs/_worklog/T.md", "worklog/T.md")
        self.assertEqual(once, "[t](../epistemic-structure/strategy/a%20b.md#s)")
        self.assertEqual(rewrite_links(once, "worklog/T.md", "worklog/T.md"), once)


class CodeSpanLinkTest(unittest.TestCase):
    """코드 구간 안의 링크는 예시이므로 바꾸지 않는다."""

    OLD = "AGENTS/a.md"

    def test_inline_code_kept(self):
        src = "`[x](../_docs/_worklog/T.md)` [y](../_docs/_worklog/T.md)\n"
        out = rewrite_links(src, self.OLD, self.OLD)
        self.assertEqual(out, "`[x](../_docs/_worklog/T.md)` [y](../worklog/T.md)\n")
        self.assertEqual(rewrite_links(out, self.OLD, self.OLD), out)

    def test_double_backtick_and_unclosed(self):
        src = "``[a](../_reference/x.md)`` ` [b](../_reference/x.md)\n"
        self.assertEqual(rewrite_links(src, self.OLD, self.OLD),
                         "``[a](../_reference/x.md)`` ` [b](../reference/x.md)\n")

    def test_display_code_target_rewritten(self):
        src = "[`x.md`](../_reference/x.md)\n"
        self.assertEqual(rewrite_links(src, self.OLD, self.OLD), "[`x.md`](../reference/x.md)\n")

    def test_fence_kept(self):
        src = "```\n[x](../_reference/x.md)\n```\n"
        self.assertEqual(rewrite_links(src, self.OLD, self.OLD), src)

    def test_repair_skips_inline_code(self):
        cur = "AGENTS/epistemic-rules/writing-style/doc.md"
        src = "`[s](../../AGENTS.md)` [t](../../AGENTS.md)\n"
        out = _repair_links(src, cur, lambda p: p == "AGENTS.md")
        self.assertEqual(out, "`[s](../../AGENTS.md)` [t](../../../AGENTS.md)\n")


@unittest.skipUnless((REPO_ROOT / ".git").exists(), "git 작업 트리 밖")
class RepositoryHeadTest(unittest.TestCase):
    """이 저장소 자체에 다시 돌려도 옮기거나 바꿀 것이 없다."""

    def test_dry_run_on_repository_is_noop(self):
        rep = migrate(REPO_ROOT, dry_run=True)
        self.assertEqual(rep.moved, [])
        self.assertEqual(rep.rewritten, [])
        self.assertEqual(rep.converted, [])
        self.assertEqual(rep.conflicts, [])
        self.assertEqual(rep.unconverted, [])

class RewriteMentionsTest(unittest.TestCase):
    def test_paths_replaced(self):
        out, rep = rewrite_mentions("`_docs/_worklog/`와 `_strategy/AGENTS.md`, `_reference/`, `_tmp/`")
        self.assertEqual(out, "`worklog/`와 `strategy/AGENTS.md`, `reference/`, `.tmp/`")
        self.assertEqual(rep, [])

    def test_identifiers_kept(self):
        out, _ = rewrite_mentions("check_reference_markers, audit_tmp_dir")
        self.assertEqual(out, "check_reference_markers, audit_tmp_dir")

    def test_bare_docs_reported(self):
        out, rep = rewrite_mentions("`_docs/` 4범주")
        self.assertEqual(out, "`_docs/` 4범주")
        self.assertEqual(rep, [(1, "`_docs/` 4범주")])

    def test_code_fence_reported(self):
        text = "```\n├── _docs/\n│   ├── _worklog/\n```\n"
        out, rep = rewrite_mentions(text)
        self.assertEqual(out, text)
        self.assertEqual([n for n, _ in rep], [2, 3])

    def test_link_target_and_url_kept(self):
        self.assertEqual(rewrite_mentions("[_docs/_worklog/](https://x.y/_strategy/a)"),
                         ("[worklog/](https://x.y/_strategy/a)", []))
        text = "[a](../_docs/_worklog/x.md) https://x.y/_tmp/z"
        self.assertEqual(rewrite_mentions(text), (text, []))


FIXTURE = {
    "_docs/_worklog/TASK_TREE.md": "[s](../_strategy/x.md)\n",
    "_docs/_strategy/x.md": "[t](../_worklog/TASK_TREE.md)\n",
    "_docs/AGENTS.md": "docs\n",
    "_reference/AGENTS.md": "ref\n",
    "AGENTS/a.md": "[w](../_docs/_worklog/TASK_TREE.md)\n",
}


def _git(root, *args):
    subprocess.run(["git", *args], cwd=str(root), check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _make_repo(tmp, files=FIXTURE):
    root = Path(tmp)
    _git(root, "init", "-q")
    _git(root, "config", "user.name", "t")
    _git(root, "config", "user.email", "t@example.com")
    for rel, text in files.items():
        f = root / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(text, encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "init")
    return root


def _snapshot(root):
    out = {}
    for f in sorted(root.rglob("*")):
        if f.is_file() and ".git" not in f.relative_to(root).parts:
            out[f.relative_to(root).as_posix()] = f.read_text(encoding="utf-8")
    return out


class MigrateTest(unittest.TestCase):
    def check_final(self, root):
        self.assertEqual((root / "worklog/TASK_TREE.md").read_text(encoding="utf-8"),
                         "[s](../epistemic-structure/strategy/x.md)\n")
        self.assertEqual((root / "epistemic-structure/strategy/x.md").read_text(encoding="utf-8"),
                         "[t](../../worklog/TASK_TREE.md)\n")
        self.assertEqual((root / "AGENTS/a.md").read_text(encoding="utf-8"), "[w](../worklog/TASK_TREE.md)\n")
        self.assertTrue((root / "epistemic-structure/AGENTS.md").is_file())
        self.assertTrue((root / "reference/AGENTS.md").is_file())
        self.assertFalse((root / "_docs").exists())
        self.assertFalse((root / "_reference").exists())

    def test_migrate_moves_and_links(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_repo(tmp)
            rep = migrate(root)
            self.check_final(root)
            self.assertIn(("_docs/_worklog/TASK_TREE.md", "worklog/TASK_TREE.md"), rep.moved)
            self.assertIn("AGENTS/a.md", rep.rewritten)

    def test_phase2_child_own_doc_stays(self):
        files = {
            "AGENTS/working-principles.md": "[t](../worklog/TASK_TREE.md)\n",
            "AGENTS/my-custom.md": "[w](working-principles.md)\n",
            "worklog/TASK_TREE.md": "x\n",
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_repo(tmp, files)
            migrate(root)
            self.assertEqual((root / "AGENTS/my-custom.md").read_text(encoding="utf-8"),
                             "[w](epistemic-rules/working-principles.md)\n")
            self.assertEqual((root / "AGENTS/epistemic-rules/working-principles.md").read_text(encoding="utf-8"),
                             "[t](../../worklog/TASK_TREE.md)\n")
            _git(root, "add", "-A")
            again = migrate(root)
            self.assertEqual(again.moved, [])
            self.assertEqual(again.rewritten, [])

    def test_rerun_is_noop(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_repo(tmp)
            migrate(root)
            before = _snapshot(root)
            rep = migrate(root)
            self.assertEqual(rep.moved, [])
            self.assertEqual(rep.rewritten, [])
            self.assertEqual(_snapshot(root), before)

    def test_partial_tree(self):
        files = dict(FIXTURE)
        files["_docs/_worklog/child.md"] = "[s](../_strategy/x.md)\n"
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_repo(tmp, files)
            (root / "worklog").mkdir()
            _git(root, "mv", "_docs/_worklog/TASK_TREE.md", "worklog/TASK_TREE.md")
            (root / "worklog/TASK_TREE.md").write_text("[s](../epistemic-structure/strategy/x.md)\n", encoding="utf-8")
            _git(root, "add", "-A")
            _git(root, "commit", "-q", "-m", "partial")
            rep = migrate(root)
            self.check_final(root)
            self.assertEqual((root / "worklog/child.md").read_text(encoding="utf-8"),
                             "[s](../epistemic-structure/strategy/x.md)\n")
            self.assertIn(("_docs/_worklog/child.md", "worklog/child.md"), rep.moved)
            self.assertNotIn(("_docs/_worklog/TASK_TREE.md", "worklog/TASK_TREE.md"), rep.moved)
            self.assertEqual(rep.conflicts, [])
            before = _snapshot(root)
            again = migrate(root)
            self.assertEqual((again.moved, again.rewritten, again.conflicts), ([], [], []))
            self.assertEqual(_snapshot(root), before)

    def test_collision_keeps_old_file(self):
        files = dict(FIXTURE)
        files["_docs/_worklog/dup.md"] = "[s](../_strategy/x.md)\n"
        files["worklog/dup.md"] = "already here\n"
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_repo(tmp, files)
            rep = migrate(root)
            self.assertEqual(rep.conflicts, [("_docs/_worklog/dup.md", "worklog/dup.md")])
            self.assertEqual((root / "worklog/dup.md").read_text(encoding="utf-8"), "already here\n")
            self.assertEqual((root / "_docs/_worklog/dup.md").read_text(encoding="utf-8"),
                             "[s](../../epistemic-structure/strategy/x.md)\n")
            self.assertNotIn(("_docs/_worklog/dup.md", "worklog/dup.md"), rep.moved)
            again = migrate(root)
            self.assertEqual((again.moved, again.rewritten), ([], []))
            self.assertEqual(again.conflicts, rep.conflicts)

    def test_dry_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_repo(tmp)
            before = _snapshot(root)
            status = subprocess.run(["git", "status", "--porcelain"], cwd=str(root), capture_output=True, text=True).stdout
            rep = migrate(root, dry_run=True)
            self.assertEqual(_snapshot(root), before)
            self.assertTrue((root / "_docs").is_dir())
            self.assertEqual(subprocess.run(["git", "status", "--porcelain"], cwd=str(root),
                                            capture_output=True, text=True).stdout, status)
            self.assertIn(("_docs/_strategy/x.md", "epistemic-structure/strategy/x.md"), rep.moved)
            self.assertIn("AGENTS/a.md", rep.rewritten)


    def test_reference_table_converted_once(self):
        files = {"reference/AGENTS.md": TABLE_ONE_ROW, "reference/a.pdf": "x\n"}
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_repo(tmp, files)
            rep = migrate(root)
            self.assertEqual(len(rep.converted), 1)
            self.assertEqual(rep.unconverted, [])
            data = load_index_yaml(root / "reference/INDEX.yaml")
            self.assertEqual(data["a.pdf"], {"description": "보고서", "status": "처리 대기"})
            text = (root / "reference/AGENTS.md").read_text(encoding="utf-8")
            self.assertNotIn("등록된 자료", text)
            _git(root, "add", "-A")
            before = _snapshot(root)
            again = migrate(root)
            self.assertEqual(again.converted, [])
            self.assertEqual(again.unconverted, [])
            self.assertEqual(_snapshot(root), before)

    def test_old_reference_table_converted(self):
        files = {"_reference/AGENTS.md": TABLE_ONE_ROW}
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_repo(tmp, files)
            migrate(root)
            data = load_index_yaml(root / "reference/INDEX.yaml")
            self.assertEqual(list(data), ["a.pdf"])

    def test_reference_table_dry_run(self):
        files = {"reference/AGENTS.md": TABLE_ONE_ROW}
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_repo(tmp, files)
            before = _snapshot(root)
            rep = migrate(root, dry_run=True)
            self.assertEqual(len(rep.converted), 1)
            self.assertEqual(_snapshot(root), before)

    def test_existing_index_yaml_is_conflict(self):
        files = {"reference/AGENTS.md": TABLE_ONE_ROW, "reference/INDEX.yaml": "# 기존\n"}
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_repo(tmp, files)
            for dry in (True, False):
                rep = migrate(root, dry_run=dry)
                self.assertEqual(rep.converted, [])
                self.assertEqual(len(rep.unconverted), 1)
                self.assertEqual(rep.unconverted[0][0], "reference/AGENTS.md")
            self.assertEqual((root / "reference/AGENTS.md").read_text(encoding="utf-8"), TABLE_ONE_ROW)
            self.assertEqual((root / "reference/INDEX.yaml").read_text(encoding="utf-8"), "# 기존\n")

    def test_unparsable_table_left_untouched(self):
        files = {"reference/AGENTS.md": TABLE_BAD_ROW}
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_repo(tmp, files)
            rep = migrate(root)
            self.assertEqual(rep.converted, [])
            self.assertEqual(len(rep.unconverted), 1)
            self.assertFalse((root / "reference/INDEX.yaml").exists())
            self.assertEqual((root / "reference/AGENTS.md").read_text(encoding="utf-8"), TABLE_BAD_ROW)

    def _run_main(self, root):
        with contextlib.redirect_stdout(io.StringIO()):
            return main([str(root), "--dry-run"])

    def test_main_exit_code_on_unconverted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_repo(tmp, {"reference/AGENTS.md": TABLE_BAD_ROW})
            self.assertEqual(self._run_main(root), 1)
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_repo(tmp, {"reference/AGENTS.md": TABLE_ONE_ROW})
            self.assertEqual(self._run_main(root), 0)


NEW_FIXTURE = {
    "worklog/TASK_TREE.md": "[s](../epistemic-structure/strategy/x.md)\n",
    "epistemic-structure/strategy/x.md": "[t](../../worklog/TASK_TREE.md)\n",
    "epistemic-structure/AGENTS.md": "docs\n",
    "reference/AGENTS.md": "ref\n",
    "AGENTS/a.md": "[w](../worklog/TASK_TREE.md)\n",
}


class ChildMergeTest(unittest.TestCase):
    """상류 머지 직후 자식 레포: 새 위치에 왔지만 본문은 옛 위치 기준인 파일."""

    def test_old_relative_links_repaired(self):
        files = dict(NEW_FIXTURE)
        files["worklog/TASK_TREE.md"] += "[결정](../_strategy/x.md#절)\n"
        files["epistemic-structure/strategy/my.md"] = (
            "[t](../_worklog/TASK_TREE.md)\n[r](../../_reference/AGENTS.md)\n[n](../_strategy/none.md)\n")
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_repo(tmp, files)
            rep = migrate(root, dry_run=True)
            self.assertEqual(sorted(rep.rewritten),
                             ["epistemic-structure/strategy/my.md", "worklog/TASK_TREE.md"])
            rep = migrate(root)
            self.assertEqual(rep.moved, [])
            self.assertEqual((root / "worklog/TASK_TREE.md").read_text(encoding="utf-8"),
                             "[s](../epistemic-structure/strategy/x.md)\n"
                             "[결정](../epistemic-structure/strategy/x.md#절)\n")
            self.assertEqual((root / "epistemic-structure/strategy/my.md").read_text(encoding="utf-8"),
                             "[t](../../worklog/TASK_TREE.md)\n[r](../../reference/AGENTS.md)\n"
                             "[n](../_strategy/none.md)\n")
            self.assertEqual(rep.residual,
                             [("epistemic-structure/strategy/my.md", 3, "[n](../_strategy/none.md)")])
            self.assertEqual(rep.conflicts, [])
            before = _snapshot(root)
            again = migrate(root)
            self.assertEqual((again.moved, again.rewritten), ([], []))
            self.assertEqual(again.residual, rep.residual)
            self.assertEqual(_snapshot(root), before)


class EdgeCaseTest(unittest.TestCase):
    def test_untracked_tmp_moved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_repo(tmp)
            (root / "_tmp/sub").mkdir(parents=True)
            (root / "_tmp/sub/a.txt").write_text("a\n", encoding="utf-8")
            dry = migrate(root, dry_run=True)
            self.assertIn(("_tmp", ".tmp"), dry.moved)
            self.assertTrue((root / "_tmp/sub/a.txt").is_file())
            self.assertFalse((root / ".tmp").exists())
            rep = migrate(root)
            self.assertIn(("_tmp", ".tmp"), rep.moved)
            self.assertEqual(rep.conflicts, [])
            self.assertFalse((root / "_tmp").exists())
            self.assertEqual((root / ".tmp/sub/a.txt").read_text(encoding="utf-8"), "a\n")

    def test_untracked_tmp_conflict(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_repo(tmp)
            (root / "_tmp").mkdir()
            (root / "_tmp/a.txt").write_text("a\n", encoding="utf-8")
            (root / ".tmp").mkdir()
            (root / ".tmp/b.txt").write_text("b\n", encoding="utf-8")
            rep = migrate(root)
            self.assertEqual(rep.conflicts, [("_tmp", ".tmp")])
            self.assertNotIn(("_tmp", ".tmp"), rep.moved)
            self.assertTrue((root / "_tmp/a.txt").is_file())
            self.assertFalse((root / ".tmp/a.txt").exists())

    def test_untracked_destination_is_conflict(self):
        files = dict(FIXTURE)
        files["_docs/_worklog/dup.md"] = "old\n"
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_repo(tmp, files)
            (root / "worklog").mkdir()
            (root / "worklog/dup.md").write_text("untracked\n", encoding="utf-8")
            dry = migrate(root, dry_run=True)
            rep = migrate(root)
            self.assertEqual(dry.conflicts, rep.conflicts)
            self.assertEqual(rep.conflicts, [("_docs/_worklog/dup.md", "worklog/dup.md")])
            self.assertEqual((root / "_docs/_worklog/dup.md").read_text(encoding="utf-8"), "old\n")
            self.assertEqual((root / "worklog/dup.md").read_text(encoding="utf-8"), "untracked\n")

    def test_unmapped_old_files_reported(self):
        files = dict(FIXTURE)
        files["_docs/README.md"] = "readme\n"
        files["_docs/_custom/x.md"] = "custom\n"
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_repo(tmp, files)
            rep = migrate(root)
            self.assertIn(("_docs/README.md", 0, "옮길 대응이 없는 옛 경로 파일"), rep.residual)
            self.assertIn(("_docs/_custom/x.md", 0, "옮길 대응이 없는 옛 경로 파일"), rep.residual)
            self.assertTrue((root / "_docs/README.md").is_file())
            self.assertTrue((root / "_docs/_custom/x.md").is_file())


HEAD = "# 디스크립터\n\n설명 글.\n\n"
TABLE_HEAD = (
    "## 등록된 자료\n\n"
    "| 파일 | 추가일 | 설명 | 상태 |\n"
    "|------|--------|------|------|\n")
TABLE_ONE_ROW = HEAD + TABLE_HEAD + "| [a.pdf](a.pdf) | 2026-05-03 | 보고서 | 처리 대기 |\n"
TABLE_EMPTY = HEAD + TABLE_HEAD + "\n(아직 등록된 자료 없음.)\n"
TABLE_BAD_ROW = (
    HEAD + TABLE_HEAD
    + "| [a.pdf](a.pdf) | 2026-05-03 | 보고서 | 처리 대기 |\n"
    + "| b.pdf | 2026-05-04 | 열이 모자란 행 |\n")


def _table(*rows, after=""):
    return HEAD + TABLE_HEAD + "".join(r + "\n" for r in rows) + after


class ReferenceTableTest(unittest.TestCase):
    def test_convert(self):
        body, yaml, bad = convert_reference_table(TABLE_ONE_ROW)
        self.assertNotIn("등록된 자료", body)
        self.assertIn('"a.pdf":\n  description: 보고서\n', yaml)
        self.assertIn("  status: 처리 대기\n", yaml)
        self.assertEqual(bad, [])

    def test_body_keeps_other_text(self):
        body, _y, _b = convert_reference_table(TABLE_ONE_ROW)
        self.assertEqual(body, HEAD.rstrip("\n") + "\n")

    def test_empty_table(self):
        body, yaml, bad = convert_reference_table(TABLE_EMPTY)
        self.assertNotIn("등록된 자료", body)
        self.assertTrue(yaml.startswith("#"))
        self.assertEqual(yaml.count("\n"), 1)
        self.assertEqual(bad, [])

    def test_header_only_table(self):
        body, yaml, bad = convert_reference_table(_table())
        self.assertNotIn("등록된 자료", body)
        self.assertTrue(yaml.startswith("#"))

    def test_unparsable_row_reported(self):
        body, yaml, bad = convert_reference_table(TABLE_BAD_ROW)
        self.assertEqual(body, TABLE_BAD_ROW)
        self.assertEqual((yaml, len(bad)), ("", 1))

    def test_no_section_noop(self):
        self.assertEqual(convert_reference_table("본문\n")[:2], ("본문\n", ""))

    def test_following_section_kept(self):
        text = _table("| a.pdf | d | 글 | 처리됨 |", after="\n## 다음 절\n\n내용\n")
        body, yaml, bad = convert_reference_table(text)
        self.assertEqual(bad, [])
        self.assertEqual(body, HEAD + "## 다음 절\n\n내용\n")

    def test_derived_link_appended(self):
        row = "| [a.pdf](a.pdf) | 2026-05-03 | 보고서 | 처리됨 ([노트](../k/n.md)) |"
        _b, yaml, bad = convert_reference_table(_table(row))
        self.assertEqual(bad, [])
        self.assertEqual(self._load(yaml)["a.pdf"], {
            "description": "보고서 ([노트](../k/n.md))", "status": "처리됨"})

    def test_backticked_status_and_remainder_only(self):
        row = "| `a.pdf` | d | | `사용자 의견 필요` [n](n.md) |"
        _b, yaml, bad = convert_reference_table(_table(row))
        self.assertEqual(bad, [])
        self.assertEqual(self._load(yaml)["a.pdf"], {
            "description": "[n](n.md)", "status": "사용자 의견 필요"})

    def test_name_forms(self):
        rows = [
            "| [x y.pdf](x%20y.pdf) | d | 가 | 처리 대기 |",
            "| `b.txt` | d | 나 | 보관용 |",
            "| c.md | d | 다 | 처리 대기 |",
            "| [dir](dir/) | d | 라 | 처리 대기 |",
            "| [e](../reference/e.png) | d | 마 | 처리 대기 |",
        ]
        _b, yaml, bad = convert_reference_table(_table(*rows))
        self.assertEqual(bad, [])
        self.assertEqual(
            list(self._load(yaml)), ["x y.pdf", "b.txt", "c.md", "dir", "e.png"])

    def test_values_needing_quotes_round_trip(self):
        rows = ['| a.pdf | d | "인용" 과 \\| 파이프: 값 | 처리 대기 |',
                "| b.pdf | d | 123 | 처리 대기 |",
                "| c.pdf | d | # 주석처럼 | 처리 대기 |"]
        _b, yaml, bad = convert_reference_table(_table(*rows))
        self.assertEqual(bad, [])
        data = self._load(yaml)
        self.assertEqual(data["a.pdf"]["description"], '"인용" 과 | 파이프: 값')
        self.assertEqual(data["b.pdf"]["description"], "123")
        self.assertEqual(data["c.pdf"]["description"], "# 주석처럼")

    def test_quote_in_name(self):
        _b, yaml, bad = convert_reference_table(_table('| a"b.pdf | d | 글 | 처리 대기 |'))
        self.assertEqual(bad, [])
        self.assertEqual(list(self._load(yaml)), ['a"b.pdf'])

    def test_missing_description_column(self):
        text = ("## 등록된 자료\n\n| 파일 | 상태 |\n|---|---|\n"
                "| a.pdf | 처리됨 |\n")
        _b, yaml, bad = convert_reference_table(text)
        self.assertEqual(bad, [])
        self.assertEqual(self._load(yaml)["a.pdf"], {"status": "처리됨"})

    def test_reordered_columns(self):
        text = ("## 등록된 자료\n\n| 상태 | 설명 | 파일 |\n|---|---|---|\n"
                "| 처리됨 | 글 | a.pdf |\n")
        _b, yaml, bad = convert_reference_table(text)
        self.assertEqual(bad, [])
        self.assertEqual(self._load(yaml)["a.pdf"], {"description": "글", "status": "처리됨"})

    def test_bad_cases_leave_text(self):
        cases = {
            "unknown_status": "| a.pdf | d | 글 | 모름 |",
            "empty_status": "| a.pdf | d | 글 | |",
            "empty_name": "| | d | 글 | 처리 대기 |",
            "nested_name": "| sub/a.pdf | d | 글 | 처리 대기 |",
            "outside_link": "| [a](../../x.pdf) | d | 글 | 처리 대기 |",
            "external_link": "| [a](https://e.com/a) | d | 글 | 처리 대기 |",
            "two_links": "| [a](a) [b](b) | d | 글 | 처리 대기 |",
            "glued_status": "| a.pdf | d | 글 | 처리 대기열 |",
            "comma_status": "| a.pdf | d | 글 | 처리됨, 노드 |",
            "dot_status": "| a.pdf | d | 글 | 처리됨.x |",
            "slash_status": "| a.pdf | d | 글 | 처리됨 / 보관용 |",
            "star_name": "| a*b.pdf | d | 글 | 처리 대기 |",
            "tilde_name": "| a~b.pdf | d | 글 | 처리 대기 |",
        }
        for label, row in cases.items():
            text = _table(row)
            body, yaml, bad = convert_reference_table(text)
            self.assertEqual((body, yaml, len(bad)), (text, "", 1), label)

    def test_unknown_column_reported(self):
        text = ("## 등록된 자료\n\n| 파일 | 출처 | 설명 | 상태 |\n|---|---|---|---|\n"
                "| a.pdf | 메일 | 글 | 처리됨 |\n")
        body, yaml, bad = convert_reference_table(text)
        self.assertEqual((body, yaml, len(bad)), (text, "", 1))
        self.assertIn("모르는 열: 출처", bad[0])

    def test_status_remainder_allowed_starts(self):
        for rest in ("(노드)", "- 노드", "[n](n.md)"):
            row = "| a.pdf | d | 글 | 처리됨 %s |" % rest
            self.assertEqual(convert_reference_table(_table(row))[2], [], rest)

    def test_duplicate_name_reported(self):
        rows = ["| a.pdf | d | 가 | 처리 대기 |", "| [a](a.pdf) | d | 나 | 처리됨 |"]
        text = _table(*rows)
        body, yaml, bad = convert_reference_table(text)
        self.assertEqual((body, yaml, len(bad)), (text, "", 1))

    def test_all_bad_rows_listed(self):
        rows = ["| a | d | 글 | 모름 |", "| b.pdf | d | 글 | 처리 대기 |", "| c | d |"]
        _b, _y, bad = convert_reference_table(_table(*rows))
        self.assertEqual(len(bad), 2)

    def test_extra_text_in_section_reported(self):
        text = _table("| a.pdf | d | 글 | 처리 대기 |", after="\n표 아래 덧붙인 글.\n")
        body, yaml, bad = convert_reference_table(text)
        self.assertEqual((body, yaml, len(bad)), (text, "", 1))

    def test_missing_required_columns(self):
        text = "## 등록된 자료\n\n| 이름 | 상태 |\n|---|---|\n| a | 처리됨 |\n"
        body, yaml, bad = convert_reference_table(text)
        self.assertEqual((body, yaml, len(bad)), (text, "", 1))

    def test_heading_in_code_fence_ignored(self):
        text = "```\n## 등록된 자료\n```\n"
        self.assertEqual(convert_reference_table(text)[:2], (text, ""))

    def test_section_at_end_without_newline(self):
        text = HEAD + TABLE_HEAD + "| a.pdf | d | 글 | 처리 대기 |"
        body, yaml, bad = convert_reference_table(text)
        self.assertEqual(bad, [])
        self.assertIn("a.pdf", yaml)

    def test_idempotent(self):
        body, _y, _b = convert_reference_table(TABLE_ONE_ROW)
        self.assertEqual(convert_reference_table(body)[:2], (body, ""))

    def test_crlf(self):
        text = TABLE_ONE_ROW.replace("\n", "\r\n")
        body, yaml, bad = convert_reference_table(text)
        self.assertEqual(bad, [])
        self.assertNotIn("등록된 자료", body)
        self.assertEqual(self._load(yaml)["a.pdf"]["status"], "처리 대기")

    def _load(self, yaml):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "INDEX.yaml"
            with open(str(path), "w", encoding="utf-8", newline="") as f:
                f.write(yaml)
            try:
                return load_index_yaml(path)
            except IndexFormatError as e:
                self.fail(str(e))


if __name__ == "__main__":
    unittest.main()

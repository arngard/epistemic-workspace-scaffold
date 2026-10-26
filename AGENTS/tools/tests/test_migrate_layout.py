"""migrate_layout.py의 경로 대응과 텍스트 변환 시험."""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from migrate_layout import map_path, migrate, rewrite_links, rewrite_mentions  # noqa: E402


class MapPathTest(unittest.TestCase):
    def test_longest_prefix(self):
        self.assertEqual(map_path("_docs/_worklog/TASK_TREE.md"), "worklog/TASK_TREE.md")
        self.assertEqual(map_path("_docs/_strategy/a b.md"), "epistemic-structure/strategy/a b.md")
        self.assertEqual(map_path("_docs/AGENTS.md"), "epistemic-structure/AGENTS.md")
        self.assertEqual(map_path("_tmp/x"), ".tmp/x")
        self.assertEqual(map_path("AGENTS/folder-structure.md"), "AGENTS/folder-structure.md")

    def test_idempotent(self):
        self.assertEqual(map_path("worklog/STATUS.md"), "worklog/STATUS.md")


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


if __name__ == "__main__":
    unittest.main()

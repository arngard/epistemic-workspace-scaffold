"""migrate_layout.py의 경로 대응과 텍스트 변환 시험."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from migrate_layout import map_path, rewrite_links, rewrite_mentions  # noqa: E402


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


if __name__ == "__main__":
    unittest.main()

"""태그 읽기(_tags_core)와 태그 형식, 표기 검사(항목 14) 시험."""

import os
import sys
import tempfile
import unittest
import unicodedata
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import _audit_core  # noqa: E402
from _audit_core import WARNING, is_bundle_path  # noqa: E402
from _tags_core import (  # noqa: E402
    TagFormatError, TagsBlock, find_tags_block, front_matter_tags, parse_tags,
    tag_documents, tag_form_problem, tag_key, unreadable_tags)
from audit_frontmatter import check_tags  # noqa: E402

FM = "---\ndate created: 2026-01-01\ndate modified: 2026-01-01\n"


class ParseTest(unittest.TestCase):
    def test_flow(self):
        got = parse_tags("tags: [a, \"b-c\", 'd']")
        self.assertEqual(got, ["a", "b-c", "d"])

    def test_block(self):
        self.assertEqual(parse_tags("tags:\n  - a\n  - b"), ["a", "b"])

    def test_empty_and_absent(self):
        self.assertEqual(parse_tags("tags: []"), [])
        self.assertIsNone(parse_tags("date created: x"))

    def test_unreadable(self):
        with self.assertRaises(TagFormatError):
            parse_tags("tags: a, b")

    def test_key(self):
        self.assertEqual(tag_key("AI 반도체"), tag_key("ai-반도체"))
        self.assertNotEqual(tag_key("a/b"), tag_key("ab"))

    def test_quote_escapes(self):
        got = parse_tags('tags: ["a\\"b", \'it\'\'s\', "c\\\\d"]')
        self.assertEqual(got, ['a"b', "it's", "c\\d"])

    def test_unknown_escape_unreadable(self):
        with self.assertRaises(TagFormatError):
            parse_tags('tags: ["a\\nb"]')

    def test_flow_space_and_trailing_comma(self):
        self.assertEqual(parse_tags("tags: [ a b ,c, ]"), ["a b", "c"])

    def test_flow_trailing_comment(self):
        self.assertEqual(parse_tags("tags: [a, b] # note"), ["a", "b"])

    def test_nfc(self):
        nfd = unicodedata.normalize("NFD", "한글")
        self.assertNotEqual(nfd, "한글")
        self.assertEqual(parse_tags("tags: [" + nfd + "]"), ["한글"])

    def test_block_flush_with_key(self):
        text = "tags:\n- a\n- b\ndescription: x"
        self.assertEqual(parse_tags(text), ["a", "b"])

    def test_block_item_comment_and_quote(self):
        text = 'tags:\n  - a # c\n  - "b c"\n  - \'d\''
        self.assertEqual(parse_tags(text), ["a", "b c", "d"])

    def test_block_without_items_is_empty(self):
        self.assertEqual(parse_tags("tags:\ndescription: x"), [])

    def test_crlf(self):
        got = parse_tags("tags:\r\n  - a\r\n  - b\r\ndate: x\r\n")
        self.assertEqual(got, ["a", "b"])

    def test_other_keys_around(self):
        text = "date created: x\ntags: [a]\ndate modified: y"
        self.assertEqual(parse_tags(text), ["a"])

    def test_key_must_start_line(self):
        self.assertIsNone(parse_tags("description: tags: [a]"))
        self.assertIsNone(parse_tags("  tags: [a]"))

    def test_unreadable_forms(self):
        bad = [
            "tags: a",
            "tags: [a",
            "tags: [a\n  , b]",
            "tags: [a, , b]",
            "tags: [,a]",
            "tags: [a] b",
            "tags: [a b: c]",
            "tags: [#a]",
            "tags: [[a]]",
            "tags: {a: b}",
            "tags: null",
            "tags:\n  - a\n    b",
            "tags:\n  - a\n   - b",
            "tags:\n  - #a",
            "tags:\n  -\n  - b",
            "tags:\n  - [a, b]",
            "tags:\n  - a: b",
            "tags:\n  - \"a\" b",
            "tags:\n  key: v",
        ]
        for text in bad:
            with self.subTest(text=text):
                with self.assertRaises(TagFormatError):
                    parse_tags(text)

    def test_error_line(self):
        with self.assertRaises(TagFormatError) as cm:
            parse_tags("date: x\ntags: a, b")
        self.assertEqual(cm.exception.line, 2)
        with self.assertRaises(TagFormatError) as cm:
            parse_tags("tags:\n  - a\n  - [b]")
        self.assertEqual(cm.exception.line, 3)

    def test_parse_tags_uses_block(self):
        text = "tags: [a, b]"
        self.assertEqual(
            parse_tags(text), list(find_tags_block(text).tags))


class BlockOffsetTest(unittest.TestCase):
    def test_flow(self):
        text = "date: x\ntags: [a, 'b'] # c\nend: y"
        blk = find_tags_block(text)
        self.assertEqual(blk.style, "flow")
        self.assertEqual(text[blk.start:blk.end], "[a, 'b']")
        self.assertEqual(blk.tags, ("a", "b"))

    def test_flow_spacing_after_colon(self):
        text = "tags:   [a]\n"
        blk = find_tags_block(text)
        self.assertEqual(text[blk.start:blk.end], "[a]")

    def test_block(self):
        text = "date: x\ntags:\n  - a\n  - b\nend: y"
        blk = find_tags_block(text)
        self.assertEqual(blk.style, "block")
        self.assertEqual(blk.indent, "  ")
        self.assertEqual(text[blk.start:blk.end], "\n  - a\n  - b")
        self.assertEqual(text[:blk.start], "date: x\ntags:")
        self.assertEqual(text[blk.end:], "\nend: y")

    def test_block_flush_indent(self):
        text = "tags:\n- a\n- b\n"
        blk = find_tags_block(text)
        self.assertEqual(blk.indent, "")
        self.assertEqual(text[blk.start:blk.end], "\n- a\n- b")

    def test_block_four_space_indent(self):
        blk = find_tags_block("tags:\n    - a\n")
        self.assertEqual(blk.indent, "    ")

    def test_block_empty(self):
        text = "tags:\nend: y"
        blk = find_tags_block(text)
        self.assertEqual((blk.start, blk.end), (len("tags:"),) * 2)
        self.assertEqual(blk.tags, ())

    def test_absent(self):
        self.assertIsNone(find_tags_block("date: x"))

    def test_frozen(self):
        blk = find_tags_block("tags: []")
        self.assertIsInstance(blk, TagsBlock)
        with self.assertRaises(Exception):
            blk.start = 1


class FormTest(unittest.TestCase):
    def test_ok(self):
        for tag in ["a", "a/b", "y2026", "2026-10", "문서관리"]:
            with self.subTest(tag=tag):
                self.assertIsNone(tag_form_problem(tag))

    def test_problems(self):
        for tag in ["a b", "", "2026", " ", "a\tb", "２０"]:
            with self.subTest(tag=tag):
                self.assertIsInstance(tag_form_problem(tag), str)


class KeyTest(unittest.TestCase):
    def test_case_and_width(self):
        self.assertEqual(tag_key("CapEx"), tag_key("CAPEX"))
        self.assertEqual(tag_key("ＡＢ"), tag_key("ab"))

    def test_separators(self):
        self.assertEqual(tag_key("a_b-c d"), "abcd")


class BundlePathTest(unittest.TestCase):
    def test_paths(self):
        root = Path("/r")
        yes = ["AGENTS/epistemic-rules.md",
               "AGENTS/epistemic-rules/x.md",
               "AGENTS/epistemic-rules/tools/a.py",
               "AGENTS/epistemic-rules"]
        no = ["AGENTS.md", "AGENTS/other.md", "epistemic-rules.md",
              "s/epistemic-rules.md", "AGENTS/audit-checks/a.py",
              "epistemic-rules/x.md", "x/epistemic-rules/AGENTS.md"]
        for rel in yes:
            with self.subTest(rel=rel):
                self.assertTrue(is_bundle_path(root, root / rel))
        for rel in no:
            with self.subTest(rel=rel):
                self.assertFalse(is_bundle_path(root, root / rel))


class TagTreeCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name).resolve()
        _audit_core._nested_repo_cache.clear()
        self.addCleanup(_audit_core._nested_repo_cache.clear)
        self.write("AGENTS.md", "[root]")
        self.write("AGENTS/epistemic-rules.md", "[agents, epistemic-rules]")
        self.write("s/AGENTS.md", "[s]")

    def write(self, rel, tags):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(FM + "tags: " + tags + "\n---\n본문\n", "utf-8")
        return p

    def write_raw(self, rel, text):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, "utf-8")
        return p

    def sev(self, fn):
        return [f.severity for f in fn(self.root)]


class FrontMatterTagsTest(TagTreeCase):
    def test_reads(self):
        p = self.write("s/a.md", "[x, y]")
        self.assertEqual(front_matter_tags(p), ["x", "y"])

    def test_no_front_matter(self):
        p = self.write_raw("s/a.md", "본문\n")
        self.assertIsNone(front_matter_tags(p))

    def test_no_tags_key(self):
        p = self.write_raw("s/a.md", "---\ndescription: d\n---\n본문\n")
        self.assertIsNone(front_matter_tags(p))

    def test_error_line_is_file_based(self):
        p = self.write("s/a.md", "a, b")
        with self.assertRaises(TagFormatError) as cm:
            front_matter_tags(p)
        self.assertEqual(cm.exception.line, 4)
        lines = p.read_text("utf-8").splitlines()
        self.assertTrue(lines[cm.exception.line - 1].startswith("tags:"))


class DocumentsTest(TagTreeCase):
    def test_scope(self):
        self.write("s/a.md", "[x]")
        self.write("s/CLAUDE.md", "[skip]")
        self.write("s/INDEX.md", "[skip]")
        self.write("s/INDEX2.md", "[skip]")
        self.write("reference/r.md", "[skip]")
        self.write_raw("s/none.md", "본문\n")
        self.write_raw("s/notags.md", "---\ndescription: d\n---\n")
        got = tag_documents(self.root)
        rels = sorted(p.relative_to(self.root).as_posix() for p in got)
        self.assertEqual(
            rels, ["AGENTS.md", "AGENTS/epistemic-rules.md",
                   "s/AGENTS.md", "s/a.md"])
        self.assertEqual(got[self.root / "s/a.md"], ["x"])

    def test_unreadable_excluded_from_documents(self):
        bad = self.write("s/bad.md", "a, b")
        self.assertNotIn(bad, tag_documents(self.root))
        found = unreadable_tags(self.root)
        self.assertEqual([p for p, _ in found], [bad])
        self.assertIsInstance(found[0][1], TagFormatError)

    def test_same_traversal(self):
        self.write("s/ok.md", "[x]")
        self.write("s/bad.md", "a, b")
        docs = {p.name for p in tag_documents(self.root)}
        bad = {p.name for p, _ in unreadable_tags(self.root)}
        self.assertIn("ok.md", docs)
        self.assertEqual(bad, {"bad.md"})
        self.assertFalse(docs & bad)

    def test_nested_repo_skipped(self):
        self.write("sub/AGENTS.md", "[a b]")
        (self.root / "sub/.git").mkdir()
        _audit_core._nested_repo_cache.clear()
        self.assertEqual(check_tags(self.root), [])


class CheckTagsTest(TagTreeCase):
    def test_clean(self):
        self.assertEqual(check_tags(self.root), [])

    def test_group_one_warning(self):
        self.write("s/a.md", "[CapEx]")
        self.write("s/b.md", "[CAPEX]")
        self.write("s/c.md", "[CAPEX]")
        found = check_tags(self.root)
        self.assertEqual(len(found), 1)
        self.assertIn("CAPEX 2", found[0].message)
        self.assertIn("CapEx 1", found[0].message)
        self.assertLess(
            found[0].message.index("CAPEX 2"),
            found[0].message.index("CapEx 1"))
        self.assertEqual(found[0].severity, WARNING)
        self.assertEqual(found[0].category, "tags")

    def test_group_path_outside_bundle(self):
        self.write("s/d.md", "[Agents]")
        found = check_tags(self.root)
        self.assertEqual([f.path for f in found], ["s/d.md"])
        self.assertIn("(상류)", found[0].message)

    def test_group_path_first_other_spelling(self):
        self.write("s/z.md", "[Agents]")
        self.write("s/b.md", "[AGENTS]")
        self.write("s/a.md", "[agents]")
        found = check_tags(self.root)
        self.assertEqual([f.path for f in found], ["s/b.md"])

    def test_group_path_least_used_without_upstream(self):
        self.write("s/a.md", "[Foo]")
        self.write("s/b.md", "[foo]")
        self.write("s/c.md", "[foo]")
        found = check_tags(self.root)
        self.assertEqual([f.path for f in found], ["s/a.md"])
        self.assertNotIn("(상류)", found[0].message)

    def test_group_by_nfkc_and_separators(self):
        self.write("s/a.md", '["문서 관리"]')
        self.write("s/b.md", "[문서-관리]")
        self.write("s/c.md", "[문서_관리]")
        self.write("s/d.md", "[문서관리]")
        found = check_tags(self.root)
        groups = [f for f in found if "표기" in f.message]
        self.assertEqual(len(groups), 1)

    def test_slash_is_kept(self):
        self.write("s/a.md", "[a/b]")
        self.write("s/b.md", "[ab]")
        self.assertEqual(check_tags(self.root), [])

    def test_space_tag_once(self):
        self.write("s/a.md", "[\"문서 관리\"]")
        self.write("s/b.md", "[\"문서 관리\"]")
        found = check_tags(self.root)
        self.assertEqual(len(found), 1)
        self.assertIn("2", found[0].message)

    def test_form_problem_prefers_non_bundle_path(self):
        self.write("AGENTS/epistemic-rules/x.md", '["a b"]')
        self.write("s/y.md", '["a b"]')
        found = check_tags(self.root)
        self.assertEqual([f.path for f in found], ["s/y.md"])

    def test_form_problem_bundle_only(self):
        self.write("AGENTS/epistemic-rules/x.md", '["a b"]')
        found = check_tags(self.root)
        self.assertEqual([f.path for f in found],
                         ["AGENTS/epistemic-rules/x.md"])

    def test_numeric_tag(self):
        self.write("s/a.md", "[2026]")
        self.assertEqual(len(check_tags(self.root)), 1)

    def test_first_tag_not_checked(self):
        self.write("epistemic-structure/strategy/x.md", "[foo]")
        self.assertEqual(check_tags(self.root), [])

    def test_unreadable_warns(self):
        self.write("s/a.md", "a, b")
        self.assertEqual(self.sev(check_tags), [WARNING])

    def test_unreadable_one_per_document(self):
        self.write("s/a.md", "a, b")
        self.write("s/b.md", "[a")
        found = check_tags(self.root)
        self.assertEqual(sorted(f.path for f in found),
                         ["s/a.md", "s/b.md"])

    def test_block_form_is_checked(self):
        self.write_raw(
            "s/a.md", FM + "tags:\n  - CapEx\n---\n본문\n")
        self.write("s/b.md", "[CAPEX]")
        self.assertEqual(len(check_tags(self.root)), 1)

    def test_index_page_ignored(self):
        # front matter와 경고를 일으킬 태그를 넣어, 색인 쪽을 거르지 않는
        # 구현이면 경고가 나서 실패하게 한다.
        (self.root / "s/INDEX.md").write_text(
            '---\ntags: ["a b"]\n---\n# s 색인\n', "utf-8")
        self.assertEqual(check_tags(self.root), [])

    def test_exempt_filename_ignored(self):
        self.write_raw("s/CLAUDE.md", '---\ntags: ["a b"]\n---\n')
        self.assertEqual(check_tags(self.root), [])

    def test_duplicate_in_document_counts_once(self):
        self.write("s/a.md", '["a b", "a b"]')
        found = check_tags(self.root)
        self.assertEqual(len(found), 1)
        self.assertIn("1", found[0].message)


if __name__ == "__main__":
    unittest.main()

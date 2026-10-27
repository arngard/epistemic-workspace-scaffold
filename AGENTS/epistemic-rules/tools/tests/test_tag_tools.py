"""태그 목록(tag_inventory)과 병합(retag) 도구, 다시 쓰기(render_tags) 시험."""

import contextlib
import hashlib
import io
import os
import sys
import tempfile
import unittest
import unicodedata
from pathlib import Path

TOOLS = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, str(TOOLS))

from _tags_core import TagsBlock, find_tags_block, render_tags  # noqa: E402
from audit_frontmatter import check_tags  # noqa: E402
from retag import RetagReport, main as retag_main, retag  # noqa: E402
from tag_inventory import TagUse, inventory  # noqa: E402
from tag_inventory import main as inventory_main  # noqa: E402

FM_HEAD = "---\ndate created: 2026-01-01\ndate modified: 2026-01-01\n"
BLOCK_DOC = FM_HEAD + "tags:\n  - 에이전트\n---\n\n본문\n"


def doc_text(tags):
    return FM_HEAD + "tags: " + tags + "\n---\n\n본문\n"


class Fixture(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.write("AGENTS.md", "[desc]")
        self.write("AGENTS/epistemic-rules.md", "[agents, epistemic-rules]")
        self.write("AGENTS/epistemic-rules/x.md", "[epistemic-rules]")
        self.write("s/AGENTS.md", "[desc]")
        self.write("s/a.md", "[agents, x]")
        self.write_raw("s/b.md", BLOCK_DOC)

    def write(self, rel, tags):
        self.write_raw(rel, doc_text(tags))

    def write_raw(self, rel, text):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(text.encode("utf-8"))

    def read(self, rel):
        with (self.root / rel).open("r", encoding="utf-8", newline="") as f:
            return f.read()

    def tags(self, rel):
        text = self.read(rel)
        front = text.split("---\n")[1]
        return list(find_tags_block(front).tags)

    def snapshot(self):
        out = {}
        for p in sorted(self.root.rglob("*")):
            if p.is_file():
                digest = hashlib.sha256(p.read_bytes()).hexdigest()
                out[p.relative_to(self.root).as_posix()] = digest
        return out


class InventoryTest(Fixture):
    def test_counts_and_upstream(self):
        self.write("s/a.md", "[agents, x]")
        uses = {u.tag: u for u in inventory(self.root)}
        self.assertEqual(uses["agents"].count, 2)  # 묶음 요지 포함
        self.assertTrue(uses["agents"].upstream)
        self.assertFalse(uses["x"].upstream)

    def test_dataclass_and_examples(self):
        self.write("s/c.md", "[x]")
        self.write("s/d.md", "[x]")
        self.write("s/e.md", "[x]")
        uses = {u.tag: u for u in inventory(self.root)}
        self.assertIsInstance(uses["x"], TagUse)
        self.assertEqual(uses["x"].count, 4)
        self.assertEqual(len(uses["x"].examples), 3)
        for ex in uses["x"].examples:
            self.assertTrue((self.root / ex).is_file())
            self.assertNotIn("\\", ex)

    def test_examples_prefer_outside_bundle(self):
        uses = {u.tag: u for u in inventory(self.root)}
        self.assertEqual(uses["agents"].examples[0], "s/a.md")
        self.assertIn(
            "AGENTS/epistemic-rules.md", uses["agents"].examples)

    def test_doc_counted_once_per_tag(self):
        self.write("s/a.md", "[x, x, y]")
        uses = {u.tag: u for u in inventory(self.root)}
        self.assertEqual(uses["x"].count, 1)

    def test_sorted_by_key_then_tag(self):
        self.write("s/a.md", "[CapEx, b, CAPEX, a]")
        order = [u.tag for u in inventory(self.root)]
        self.assertLess(order.index("a"), order.index("b"))
        self.assertLess(order.index("b"), order.index("CAPEX"))
        self.assertEqual(
            order.index("CapEx") - order.index("CAPEX"), 1)

    def test_block_style_read(self):
        uses = {u.tag: u for u in inventory(self.root)}
        self.assertEqual(uses["에이전트"].count, 1)

    def test_index_pages_not_counted(self):
        self.write_raw("s/INDEX.md", doc_text("[zzz]"))
        self.assertNotIn("zzz", [u.tag for u in inventory(self.root)])

    def run_main(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = inventory_main([str(self.root), *args])
        return code, out.getvalue(), err.getvalue()

    def test_main_tsv(self):
        code, out, err = self.run_main()
        self.assertEqual(code, 0)
        lines = out.splitlines()
        self.assertEqual(lines[0].split("\t"), ["수", "태그", "상류", "예시"])
        rows = {ln.split("\t")[1]: ln.split("\t") for ln in lines[1:]}
        self.assertEqual(rows["agents"][0], "2")
        self.assertEqual(rows["x"][0], "1")
        self.assertNotEqual(rows["agents"][2], rows["x"][2])
        self.assertIn("s/a.md", rows["x"][3])
        self.assertEqual(err, "")

    def test_main_reports_unreadable_on_stderr(self):
        self.write("s/bad.md", "a, b")
        code, out, err = self.run_main()
        self.assertEqual(code, 0)
        self.assertEqual(len(err.strip().splitlines()), 1)
        self.assertIn("s/bad.md", err)

    def test_main_does_not_write(self):
        before = self.snapshot()
        self.run_main()
        self.assertEqual(before, self.snapshot())

    def test_main_usage_error(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = inventory_main([str(self.root / "none")])
        self.assertEqual(code, 2)
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = inventory_main(["a", "b"])
        self.assertEqual(code, 2)


class RetagTest(Fixture):
    def test_flow_rewrite_and_dedupe(self):
        self.write("s/a.md", "[CapEx, CAPEX, y]")
        retag(self.root, {"CapEx": "capex", "CAPEX": "capex"})
        self.assertEqual(self.tags("s/a.md"), ["capex", "y"])

    def test_block_style_kept(self):
        self.write_raw("s/b.md", BLOCK_DOC)  # tags:\n  - 에이전트
        retag(self.root, {"에이전트": "agents"})
        self.assertIn("  - agents\n", self.read("s/b.md"))

    def test_other_bytes_unchanged(self):
        before = self.read("s/a.md")
        retag(self.root, {"x": "z"})
        after = self.read("s/a.md")
        self.assertEqual(before.replace("x", "z", 1), after)

    def test_date_modified_unchanged(self):
        retag(self.root, {"x": "z"})
        self.assertIn("date modified: 2026-01-01", self.read("s/a.md"))

    def test_bundle_skipped(self):
        rep = retag(self.root, {"agents": "에이전트"})
        self.assertIn("AGENTS/epistemic-rules.md", rep.skipped_bundle)
        self.assertIn("agents", self.tags("AGENTS/epistemic-rules.md"))

    def test_include_bundles(self):
        retag(self.root, {"agents": "a"}, include_bundles=True)
        self.assertIn("a", self.tags("AGENTS/epistemic-rules.md"))

    def test_dry_run(self):
        rep = retag(self.root, {"x": "z"}, dry_run=True)
        self.assertTrue(rep.changed)
        self.assertIn("x", self.tags("s/a.md"))

    def test_bad_new_tag_exit_2(self):
        argv = [str(self.root), "--map", "x=a b"]
        self.assertEqual(retag_main(argv), 2)

    def test_check_tags_clean_after(self):
        self.write("s/c.md", "[CAPEX]")
        self.write("s/d.md", "[CapEx]")
        retag(self.root, {"CapEx": "CAPEX"})
        self.assertEqual(check_tags(self.root), [])

    def test_report_lists(self):
        self.write("s/bad.md", "a, b")
        rep = retag(self.root, {"agents": "q"})
        self.assertIsInstance(rep, RetagReport)
        self.assertEqual(rep.changed, ["s/a.md"])
        self.assertEqual(rep.skipped_bundle, ["AGENTS/epistemic-rules.md"])
        self.assertEqual(rep.unreadable, ["s/bad.md"])

    def test_untouched_files_not_written(self):
        before = self.snapshot()
        retag(self.root, {"x": "z"})
        after = self.snapshot()
        changed = [k for k in before if before[k] != after[k]]
        self.assertEqual(changed, ["s/a.md"])

    def test_no_chain(self):
        self.write("s/a.md", "[a, b]")
        retag(self.root, {"a": "b", "b": "c"})
        self.assertEqual(self.tags("s/a.md"), ["b", "c"])

    def test_exact_spelling_only(self):
        self.write("s/a.md", "[CapEx, capex]")
        retag(self.root, {"CapEx": "CAPEX"})
        self.assertEqual(self.tags("s/a.md"), ["CAPEX", "capex"])

    def test_first_position_kept_on_dedupe(self):
        self.write("s/a.md", "[b, a, c]")
        retag(self.root, {"c": "b"})
        self.assertEqual(self.tags("s/a.md"), ["b", "a"])

    def test_quoted_tag_replaced(self):
        self.write("s/a.md", '["증권 전문가", y]')
        retag(self.root, {"증권 전문가": "증권전문가"})
        self.assertIn("[증권전문가, y]", self.read("s/a.md"))

    def test_quote_when_needed(self):
        self.write("s/a.md", "[a, y]")
        retag(self.root, {"a": "b,c"})
        self.assertIn('["b,c", y]', self.read("s/a.md"))
        self.assertEqual(self.tags("s/a.md"), ["b,c", "y"])

    def test_non_nfc_map_and_doc(self):
        nfd = unicodedata.normalize("NFD", "한글")
        self.write("s/a.md", "[" + nfd + ", y]")
        retag(self.root, {nfd: unicodedata.normalize("NFD", "국문")})
        self.assertEqual(self.tags("s/a.md"), ["국문", "y"])

    def test_non_tags_bytes_with_tag_word_outside(self):
        text = FM_HEAD + "tags: [x]\nnote: x\n---\n\nx\n"
        self.write_raw("s/a.md", text)
        retag(self.root, {"x": "z"})
        self.assertEqual(
            self.read("s/a.md"), text.replace("[x]", "[z]"))

    def test_trailing_flow_comment_kept(self):
        text = FM_HEAD + "tags: [x, y] # memo\n---\n"
        self.write_raw("s/a.md", text)
        retag(self.root, {"x": "z"})
        self.assertEqual(
            self.read("s/a.md"), text.replace("[x, y]", "[z, y]"))

    def test_block_dedupe_and_indent_kept(self):
        text = FM_HEAD + "tags:\n- x\n- y\n- z\n---\n"
        self.write_raw("s/b.md", text)
        retag(self.root, {"x": "y"})
        self.assertEqual(
            self.read("s/b.md"), FM_HEAD + "tags:\n- y\n- z\n---\n")

    def test_block_followed_by_key(self):
        text = FM_HEAD + "tags:\n  - x\ndescription: d\n---\n"
        self.write_raw("s/b.md", text)
        retag(self.root, {"x": "z"})
        self.assertEqual(
            self.read("s/b.md"), text.replace("- x", "- z"))

    def test_empty_tags_untouched(self):
        self.write_raw("s/a.md", doc_text("[]"))
        rep = retag(self.root, {"x": "z"})
        self.assertNotIn("s/a.md", rep.changed)

    def test_crlf_flow_roundtrip(self):
        text = (FM_HEAD + "tags: [a, x]\n---\n\nbody\n").replace("\n", "\r\n")
        (self.root / "s/a.md").write_bytes(text.encode("utf-8"))
        retag(self.root, {"x": "z"})
        got = (self.root / "s/a.md").read_bytes()
        self.assertEqual(got, text.replace("[a, x]", "[a, z]").encode("utf-8"))

    def test_crlf_block_roundtrip(self):
        text = (FM_HEAD + "tags:\n  - x\n  - y\n---\n\nbody\n")
        text = text.replace("\n", "\r\n")
        (self.root / "s/b.md").write_bytes(text.encode("utf-8"))
        retag(self.root, {"x": "z"})
        got = (self.root / "s/b.md").read_bytes()
        self.assertEqual(got, text.replace("- x", "- z").encode("utf-8"))

    def test_crlf_block_dedupe(self):
        text = (FM_HEAD + "tags:\n  - x\n  - y\n  - z\n---\n")
        text = text.replace("\n", "\r\n")
        (self.root / "s/b.md").write_bytes(text.encode("utf-8"))
        retag(self.root, {"x": "y"})
        got = (self.root / "s/b.md").read_bytes()
        want = text.replace("  - x\r\n", "")
        self.assertEqual(got, want.encode("utf-8"))
        self.assertNotIn(b"\n", got.replace(b"\r\n", b""))

    def test_mixed_newlines_keep_outside_bytes(self):
        text = FM_HEAD + "tags: [x]\r\n---\r\n\nbody\r\n"
        (self.root / "s/a.md").write_bytes(text.encode("utf-8"))
        retag(self.root, {"x": "z"})
        got = (self.root / "s/a.md").read_bytes()
        self.assertEqual(got, text.replace("[x]", "[z]").encode("utf-8"))

    def test_unreadable_reported_not_changed(self):
        self.write("s/bad.md", "x, y")
        before = self.read("s/bad.md")
        rep = retag(self.root, {"x": "z"})
        self.assertEqual(rep.unreadable, ["s/bad.md"])
        self.assertEqual(self.read("s/bad.md"), before)

    def test_invalid_new_tag_raises_and_writes_nothing(self):
        before = self.snapshot()
        for bad in ("a b", "", "2026"):
            with self.assertRaises(ValueError):
                retag(self.root, {"x": bad})
        self.assertEqual(before, self.snapshot())

    def test_conflicting_nfc_keys_raise(self):
        nfd = unicodedata.normalize("NFD", "한글")
        with self.assertRaises(ValueError):
            retag(self.root, {nfd: "a", "한글": "b"})

    def test_hash_tag_new_value_quoted_roundtrip(self):
        retag(self.root, {"x": "#z"})
        self.assertEqual(self.tags("s/a.md"), ["agents", "#z"])


class RetagMainTest(Fixture):
    def run_main(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = retag_main([str(self.root), *args])
        return code, out.getvalue(), err.getvalue()

    def test_sections_output(self):
        self.write("s/bad.md", "a, b")
        code, out, err = self.run_main("--map", "agents=q")
        self.assertEqual(code, 0)
        self.assertIn("s/a.md", out)
        self.assertIn("AGENTS/epistemic-rules.md", out)
        self.assertIn("s/bad.md", out)
        self.assertLess(out.index("s/a.md"), out.index("AGENTS/epistemic"))
        self.assertLess(out.index("AGENTS/epistemic"), out.index("s/bad.md"))
        self.assertEqual(self.tags("s/a.md"), ["q", "x"])

    def test_dry_run_flag(self):
        before = self.snapshot()
        code, out, err = self.run_main("--map", "x=z", "--dry-run")
        self.assertEqual(code, 0)
        self.assertIn("s/a.md", out)
        self.assertEqual(before, self.snapshot())

    def test_include_bundles_flag(self):
        code, out, err = self.run_main(
            "--map", "agents=q", "--include-bundles")
        self.assertEqual(code, 0)
        self.assertIn("q", self.tags("AGENTS/epistemic-rules.md"))

    def test_multiple_maps(self):
        self.write("s/a.md", "[a, b]")
        code, out, err = self.run_main("--map", "a=b", "--map", "b=c")
        self.assertEqual(code, 0)
        self.assertEqual(self.tags("s/a.md"), ["b", "c"])

    def test_same_old_two_news_exit_2(self):
        before = self.snapshot()
        code, out, err = self.run_main("--map", "x=a", "--map", "x=b")
        self.assertEqual(code, 2)
        self.assertEqual(before, self.snapshot())

    def test_same_old_same_new_ok(self):
        code, out, err = self.run_main("--map", "x=a", "--map", "x=a")
        self.assertEqual(code, 0)

    def test_nfc_duplicate_old_conflict_exit_2(self):
        nfd = unicodedata.normalize("NFD", "한글")
        code, out, err = self.run_main("--map", nfd + "=a", "--map", "한글=b")
        self.assertEqual(code, 2)

    def test_usage_errors_exit_2(self):
        self.assertEqual(self.run_main()[0], 2)
        self.assertEqual(self.run_main("--map", "noequals")[0], 2)
        self.assertEqual(self.run_main("--map", "=a")[0], 2)
        self.assertEqual(self.run_main("--map", "a=")[0], 2)

    def test_not_a_directory_exit_2(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = retag_main([str(self.root / "none"), "--map", "x=z"])
        self.assertEqual(code, 2)


class RenderTest(unittest.TestCase):
    def block(self, text):
        return find_tags_block(text)

    def test_flow_plain(self):
        b = self.block("tags: [a, b]")
        self.assertEqual(render_tags(b, ["x", "y z"]), "[x, y z]")

    def test_flow_quotes_only_when_needed(self):
        b = self.block("tags: [a]")
        got = render_tags(b, ["a b", "c,d", "e]", "#f", "g: h", "'i"])
        want = '[a b, "c,d", "e]", "#f", "g: h", "\'i"]'
        self.assertEqual(got, want)

    def test_flow_escapes(self):
        b = self.block("tags: [a]")
        self.assertEqual(render_tags(b, ['q"r,s']), '["q\\"r,s"]')
        self.assertEqual(render_tags(b, ["p\\q,"]), '["p\\\\q,"]')

    def test_flow_empty(self):
        b = self.block("tags: [a]")
        self.assertEqual(render_tags(b, []), "[]")

    def test_block_keeps_indent(self):
        b = self.block("tags:\n    - a\n    - b")
        self.assertEqual(render_tags(b, ["x", "y"]), "\n    - x\n    - y")

    def test_block_newline_argument(self):
        b = self.block("tags:\r\n  - a")
        self.assertEqual(
            render_tags(b, ["x", "y"], newline="\r\n"),
            "\r\n  - x\r\n  - y")

    def test_reads_back(self):
        samples = ["a b", "c,d", "e]", "#f", "g: h", "'i", '"j', "k #l", "- m"]
        for style_text in ("tags: [a]", "tags:\n  - a"):
            b = self.block(style_text)
            rendered = render_tags(b, samples)
            if b.style == "flow":
                text = "tags: " + rendered
            else:
                text = "tags:" + rendered
            self.assertEqual(list(find_tags_block(text).tags), samples)

    def test_returns_block_type(self):
        self.assertIsInstance(self.block("tags: [a]"), TagsBlock)


if __name__ == "__main__":
    unittest.main()

"""_index_core의 YAML 부분집합 파서와 설명 읽기 시험."""

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from _audit_core import (  # noqa: E402
    INDEX_NAME, INDEX_PAGE_RE, INDEX_YAML_NAME, is_index_file)
from _index_core import (  # noqa: E402
    BYPRODUCT_NAMES, INDEX_DESC_LIMIT, INDEX_KEYS, REFERENCE_STATUSES,
    SELF_KEY, STRUCTURE_KEY, IndexFormatError, front_matter_description,
    is_byproduct, load_index_yaml, parse_scalar, quote_scalar)

FM_DESC = "---\ndescription: 짧은 설명\n---\n"


class IndexNameTest(unittest.TestCase):
    def test_constants(self):
        self.assertEqual(INDEX_NAME, "INDEX.md")
        self.assertEqual(INDEX_YAML_NAME, "INDEX.yaml")
        self.assertTrue(INDEX_PAGE_RE.match("INDEX10.md"))

    def test_is_index_file(self):
        for name in ("INDEX.md", "INDEX2.md", "INDEX9.md", "INDEX10.md",
                     "INDEX.yaml"):
            self.assertTrue(is_index_file(name), name)
        for name in ("INDEX1.md", "INDEX0.md", "INDEX.txt", "index.md",
                     "XINDEX.md", "INDEX2.yaml", "a.md"):
            self.assertFalse(is_index_file(name), name)


class ScalarTest(unittest.TestCase):
    def test_plain(self):
        self.assertEqual(parse_scalar(" 보고서 원문 "), "보고서 원문")

    def test_quoted_escape(self):
        self.assertEqual(parse_scalar('"a \\"b\\" c"'), 'a "b" c')

    def test_quoted_backslash(self):
        self.assertEqual(parse_scalar('"a\\\\b"'), "a\\b")

    def test_rejects(self):
        for raw in ("[a](b)", "a: b", "a #b", ">", "'a'"):
            with self.assertRaises(IndexFormatError):
                parse_scalar(raw)

    def test_rejects_yaml_ambiguous(self):
        # R16: 목록 항목, 복합 키, 끝 콜론은 YAML이 다르게 읽는다.
        for raw in ("- a", "? a", "a:", "-", "?"):
            with self.assertRaises(IndexFormatError):
                parse_scalar(raw)

    def test_plain_allows_inner_markers(self):
        self.assertEqual(parse_scalar("a-b ?c"), "a-b ?c")
        self.assertEqual(parse_scalar("a#b"), "a#b")
        self.assertEqual(parse_scalar("-a5"), "-a5")

    def test_rejects_bad_quoted(self):
        for raw in ('"a', '"a\\n"', '"a" b', '"a"b', '"a\\"'):
            with self.assertRaises(IndexFormatError):
                parse_scalar(raw)

    def test_rejects_leading_special(self):
        for ch in "\"'[]{}>|*&!%@#`":
            if ch == '"':
                continue
            with self.assertRaises(IndexFormatError):
                parse_scalar(ch + "a")

    def test_rejects_leading_comma(self):
        with self.assertRaises(IndexFormatError):
            parse_scalar(",a")

    def test_rejects_control_chars(self):
        for raw in ("a\tb", "a\t#b", "a:\tb", "a\x01b", "a\u2028b",
                    "a\u2029b", "a\x85b", '"a\tb"'):
            with self.assertRaises(IndexFormatError, msg=repr(raw)):
                parse_scalar(raw)

    def test_rejects_non_string_plain(self):
        for raw in ("~", "null", "Null", "TRUE", "false", "Yes", "no", "ON",
                    "off", "12", "-12", "+3", "1.5", "-1.5", ".5", "1e3",
                    "1.5E-3", "0x1F", "0o7", ".inf", "-.INF", ".nan", "1_000",
                    "1:30", "2026-10-25"):
            with self.assertRaises(IndexFormatError, msg=raw):
                parse_scalar(raw)

    def test_quoted_non_string_ok(self):
        self.assertEqual(parse_scalar('"null"'), "null")
        self.assertEqual(parse_scalar('"12"'), "12")

    def test_plain_words_like_numbers_ok(self):
        for raw in ("1a", "nullable", "v1.2.3", "0x", "a1"):
            self.assertEqual(parse_scalar(raw), raw)

    def test_empty(self):
        self.assertEqual(parse_scalar("  "), "")
        self.assertEqual(parse_scalar('""'), "")


class QuoteScalarTest(unittest.TestCase):
    def test_plain_stays_plain(self):
        self.assertEqual(quote_scalar("보고서 원문"), "보고서 원문")

    def test_quotes_when_needed(self):
        self.assertEqual(quote_scalar("a: b"), '"a: b"')
        self.assertEqual(quote_scalar("[a](b)"), '"[a](b)"')
        self.assertEqual(quote_scalar(""), '""')
        self.assertEqual(quote_scalar(" a"), '" a"')
        self.assertEqual(quote_scalar("- a"), '"- a"')
        self.assertEqual(quote_scalar("a:"), '"a:"')

    def test_roundtrip(self):
        values = ["x", 'a "b" c', "a\\b", "a: b", "a #b", "`YYYY/` 아래",
                  "", " 앞공백", "뒤공백 ", "- a", "? a", "a:", "'a'",
                  "[a]", "한글: 값", "100%", "@x", "a\\", '"']
        for v in values:
            self.assertEqual(parse_scalar(quote_scalar(v)), v, repr(v))

    def test_quotes_non_string(self):
        self.assertEqual(quote_scalar("null"), '"null"')
        self.assertEqual(quote_scalar("12"), '"12"')
        for v in ("null", "12", "~", "yes", "1e3", ",a", ".inf", "0x1F"):
            self.assertEqual(parse_scalar(quote_scalar(v)), v, v)

    def test_rejects_unrepresentable(self):
        for v in ("a\nb", "a\rb", "a\tb", "a\x01b", "a\u2028b",
                  "a\u2029b", "a\x85b"):
            with self.assertRaises(IndexFormatError):
                quote_scalar(v)


class ErrorAttrTest(unittest.TestCase):
    def test_attributes(self):
        e = IndexFormatError("m")
        self.assertEqual(e.line, 0)
        self.assertIsNone(e.path)
        e2 = IndexFormatError("m", line=3, path=Path("x/INDEX.yaml"))
        self.assertEqual(e2.line, 3)
        self.assertEqual(e2.path, Path("x/INDEX.yaml"))
        self.assertIn("3", str(e2))
        self.assertIsInstance(e2, ValueError)


class ConstantsTest(unittest.TestCase):
    def test_values(self):
        self.assertEqual(INDEX_KEYS, ("description", "status"))
        self.assertEqual(SELF_KEY, ".")
        self.assertEqual(STRUCTURE_KEY, "structure")
        self.assertEqual(INDEX_DESC_LIMIT, 200)
        self.assertEqual(len(REFERENCE_STATUSES), 4)
        self.assertIn("처리 대기", REFERENCE_STATUSES)

    def test_byproduct(self):
        for name in ("Thumbs.db", "desktop.ini", "ehthumbs.db", "Icon\r",
                     "a.md~", "~"):
            self.assertTrue(is_byproduct(name), repr(name))
        for name in ("a.md", "Icon", "thumbs.db.txt", "a~b"):
            self.assertFalse(is_byproduct(name), repr(name))
        self.assertIn("Icon\r", BYPRODUCT_NAMES)


class YamlTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

    def write(self, name, text):
        p = self.root / name
        p.write_text(text, encoding="utf-8")
        return p

    def test_entries(self):
        self.write("INDEX.yaml", '# c\n"a b.pdf":\n  description: x\n'
                   '  status: 처리 대기\n"d/":\n  description: y\n')
        data = load_index_yaml(self.root / "INDEX.yaml")
        self.assertEqual(data["a b.pdf"]["status"], "처리 대기")
        self.assertIn("d/", data)

    def test_bad_indent_line(self):
        self.write("INDEX.yaml", '"a":\n   description: x\n')
        with self.assertRaises(IndexFormatError) as cm:
            load_index_yaml(self.root / "INDEX.yaml")
        self.assertEqual(cm.exception.line, 2)
        self.assertEqual(cm.exception.path, self.root / "INDEX.yaml")

    def test_self_entry(self):
        self.write("INDEX.yaml", '".":\n  structure: "`YYYY/` 아래"\n')
        data = load_index_yaml(self.root / "INDEX.yaml")
        self.assertEqual(data["."]["structure"], "`YYYY/` 아래")

    def test_self_entry_without_structure(self):
        self.write("INDEX.yaml", '".":\n  description: x\n')
        with self.assertRaises(IndexFormatError):
            load_index_yaml(self.root / "INDEX.yaml")

    def test_self_entry_empty_or_extra(self):
        for body in ('".":\n', '".":\n  structure: ""\n',
                     '".":\n  structure: a\n  description: b\n'):
            self.write("INDEX.yaml", body)
            with self.assertRaises(IndexFormatError) as cm:
                load_index_yaml(self.root / "INDEX.yaml")
            self.assertEqual(cm.exception.line, 1)

    def test_missing_file(self):
        self.assertEqual(load_index_yaml(self.root / "INDEX.yaml"), {})

    def test_blank_and_comment_lines(self):
        self.write("INDEX.yaml", '\n# c\n\n"a":\n\n  # k\n  description: x\n')
        data = load_index_yaml(self.root / "INDEX.yaml")
        self.assertEqual(data["a"], {"description": "x"})

    def test_unknown_key_kept(self):
        self.write("INDEX.yaml", '"a":\n  foo: bar\n')
        data = load_index_yaml(self.root / "INDEX.yaml")
        self.assertEqual(data["a"], {"foo": "bar"})

    def test_nfc_name(self):
        import unicodedata
        nfd = unicodedata.normalize("NFD", "한글.pdf")
        self.write("INDEX.yaml", '"%s":\n  description: x\n' % nfd)
        data = load_index_yaml(self.root / "INDEX.yaml")
        self.assertEqual(list(data), [unicodedata.normalize("NFC", "한글.pdf")])

    def test_duplicate_entry(self):
        import unicodedata
        nfd = unicodedata.normalize("NFD", "한")
        self.write("INDEX.yaml", '"한":\n  description: x\n'
                   '"%s":\n  description: y\n' % nfd)
        with self.assertRaises(IndexFormatError) as cm:
            load_index_yaml(self.root / "INDEX.yaml")
        self.assertEqual(cm.exception.line, 3)

    def test_empty_entry_name(self):
        self.write("INDEX.yaml", '"":\n  description: x\n')
        with self.assertRaises(IndexFormatError) as cm:
            load_index_yaml(self.root / "INDEX.yaml")
        self.assertEqual(cm.exception.line, 1)

    def test_line_numbers_stable_with_separators(self):
        # U+2028이 든 줄이 있어도 뒤 줄의 번호가 밀리지 않는다.
        self.write("INDEX.yaml", '"a":\n  description: "x\u2028y"\n'
                   '"b":\n   description: z\n')
        with self.assertRaises(IndexFormatError) as cm:
            load_index_yaml(self.root / "INDEX.yaml")
        self.assertEqual(cm.exception.line, 2)
        self.write("INDEX.yaml", '"a":\n  description: x\u2028y\n'
                   '"b":\n  description: z\n  description: w\n')
        with self.assertRaises(IndexFormatError) as cm:
            load_index_yaml(self.root / "INDEX.yaml")
        self.assertEqual(cm.exception.line, 2)

    def test_duplicate_key(self):
        self.write("INDEX.yaml", '"a":\n  description: x\n  description: y\n')
        with self.assertRaises(IndexFormatError) as cm:
            load_index_yaml(self.root / "INDEX.yaml")
        self.assertEqual(cm.exception.line, 3)

    def test_rejected_shapes(self):
        bad = ['a:\n', '"a" :\n', '  description: x\n', '"a":\n\tdescription: x\n',
               '"a":\n  description: >\n', '"a":\n  description:\n',
               '"a":\n  Bad Key: x\n', '"a":\n  description: [x]\n',
               '- "a"\n', '"a\\n":\n']
        for body in bad:
            self.write("INDEX.yaml", body)
            with self.assertRaises(IndexFormatError, msg=body):
                load_index_yaml(self.root / "INDEX.yaml")

    def test_escaped_name(self):
        self.write("INDEX.yaml", '"a \\"q\\" b":\n  description: x\n')
        self.assertIn('a "q" b', load_index_yaml(self.root / "INDEX.yaml"))

    def test_crlf_and_bom(self):
        p = self.root / "INDEX.yaml"
        p.write_bytes('\ufeff"a":\r\n  description: x\r\n'.encode("utf-8"))
        self.assertEqual(load_index_yaml(p), {"a": {"description": "x"}})

    def test_front_matter_description(self):
        self.write("a.md", FM_DESC + "본문\n")
        self.assertEqual(front_matter_description(self.root / "a.md"),
                         "짧은 설명")

    def test_front_matter_none(self):
        self.write("a.md", "---\ntags: [a]\n---\n본문\n")
        self.write("b.md", "본문\n")
        self.assertIsNone(front_matter_description(self.root / "a.md"))
        self.assertIsNone(front_matter_description(self.root / "b.md"))

    def test_front_matter_description_in_body_ignored(self):
        self.write("a.md", "---\ntags: [a]\n---\ndescription: x\n")
        self.assertIsNone(front_matter_description(self.root / "a.md"))

    def test_front_matter_quoted(self):
        self.write("a.md", '---\ndescription: "a: b"\n---\n')
        self.assertEqual(front_matter_description(self.root / "a.md"), "a: b")

    def test_front_matter_folded_rejected(self):
        self.write("b.md", "---\ndescription: >\n  x\n---\n")
        with self.assertRaises(IndexFormatError) as cm:
            front_matter_description(self.root / "b.md")
        self.assertEqual(cm.exception.line, 2)
        self.assertEqual(cm.exception.path, self.root / "b.md")

    def test_front_matter_empty_or_continued_rejected(self):
        for body in ("---\ndescription:\n---\n",
                     "---\ndescription:\n  x\n---\n",
                     "---\ndescription: a\n  b\n---\n",
                     "---\ndescription: a: b\n---\n"):
            self.write("c.md", body)
            with self.assertRaises(IndexFormatError, msg=body):
                front_matter_description(self.root / "c.md")


if __name__ == "__main__":
    unittest.main()

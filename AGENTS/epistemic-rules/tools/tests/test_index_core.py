"""_index_core의 YAML 부분집합 파서와 설명 읽기 시험."""

import os
import re
import sys
import tempfile
import unicodedata
import unittest
from unittest import mock
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import _audit_core  # noqa: E402
import _index_core  # noqa: E402
from _audit_core import (  # noqa: E402
    INDEX_NAME, INDEX_PAGE_RE, INDEX_YAML_NAME, SIZE_LIMIT_NODE,
    is_index_file, text_size)
from _index_core import (  # noqa: E402
    BYPRODUCT_NAMES, INDEX_DESC_LIMIT, INDEX_KEYS, REFERENCE_STATUSES,
    SELF_KEY, STRUCTURE_KEY, Entry, IndexFormatError, entry_paths,
    front_matter_description, index_dirs, is_byproduct, list_entries,
    load_index_yaml, page_name, parse_scalar, quote_scalar, render_all,
    render_pages, sequential_structure)
from audit_links import (  # noqa: E402
    check_link_text, check_link_whitespace, check_links)
from audit_structure import check_filename_portability  # noqa: E402

FM_DESC = "---\ndescription: 짧은 설명\n---\n"
FM = "---\ndescription: 문서 설명\n---\n본문\n"
FM_LONG_DESC = ("---\ndescription: "
                + "가나다라마바사아자차" * 15 + "\n---\n")


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


class RenderTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.write("AGENTS.md", FM)
        self.write("CLAUDE.md", "@AGENTS.md\n")
        self.write("AGENTS/epistemic-rules.md", FM)
        self.write("s.md", FM)
        self.write("s/AGENTS.md", FM)
        self.write("s/x.md", FM)
        self.write("LICENSE", "x\n")
        self.write(".hidden", "x\n")
        self.write("INDEX.yaml", '"LICENSE":\n  description: 사용 허가\n')
        self.write("reference/AGENTS.md", FM)
        self.write("reference/r.pdf", "x\n")

    def write(self, name, text):
        p = self.root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        return p

    def rels(self, dirs):
        return [d.relative_to(self.root).as_posix() for d in dirs]

    def page(self, rel):
        return render_all(self.root)[self.root / rel]

    def test_dirs(self):
        rels = [d.relative_to(self.root).as_posix() for d in index_dirs(self.root)]
        self.assertEqual(rels, [".", "reference", "s"])

    def test_entries_root(self):
        names = [e.name for e in list_entries(self.root, self.root)]
        self.assertEqual(names, ["LICENSE", "reference/", "s.md"])

    def test_pair_merged(self):
        e = [e for e in list_entries(self.root, self.root) if e.name == "s.md"][0]
        self.assertEqual([t for _, t in e.links], ["s.md", "s/INDEX.md"])

    def test_unregistered(self):
        e = list_entries(self.root, self.root / "reference")[0]
        self.assertEqual(e.status, "미등록")

    def test_render_twice_equal(self):
        self.assertEqual(render_all(self.root), render_all(self.root))

    def test_nfd_name_renders_nfc(self):
        self.write(unicodedata.normalize("NFD", "s/가.md"), FM)
        text = render_all(self.root)[self.root / "s/INDEX.md"]
        self.assertIn("[가.md](가.md)", text)  # 표시와 링크 대상 모두 NFC
        self.assertEqual(text, unicodedata.normalize("NFC", text))

    def test_split(self):
        for i in range(120):
            self.write(f"s/doc-{i:03}.md", FM_LONG_DESC)
        pages = render_pages(self.root, self.root / "s")
        self.assertGreater(len(pages), 1)
        for p in pages:
            self.assertLessEqual(len(re.sub(r"\s", "", p)), SIZE_LIMIT_NODE)
        self.assertIn("(INDEX2.md)", pages[0])

    def test_rendered_passes_link_checks(self):
        self.write("s/a b.md", FM)
        self.write("s/a[1].md", FM)
        for path, text in render_all(self.root).items():
            path.write_text(text, encoding="utf-8")
        for check in (check_links, check_link_text, check_link_whitespace):
            self.assertEqual(check(self.root), [], check.__name__)

    def test_sequential_top(self):
        self.write("s/INDEX.yaml", '".":\n  structure: 날짜순\n')
        self.write("s/2026-05/AGENTS.md", FM)  # 남은 옛 디스크립터
        pages = render_pages(self.root, self.root / "s")
        self.assertEqual(len(pages), 1)
        self.assertIn("날짜순", pages[0])
        self.assertNotIn("x.md", pages[0])
        dirs = [d.relative_to(self.root).as_posix()
                for d in index_dirs(self.root)]
        self.assertNotIn("s/2026-05", dirs)

    def test_nested_repo_is_entry_only(self):
        self.write("impl/AGENTS.md", FM)
        self.write("impl/sub/.git", "gitdir: x\n")
        self.write("impl/sub/AGENTS.md", FM)
        dirs = [d.relative_to(self.root).as_posix()
                for d in index_dirs(self.root)]
        self.assertNotIn("impl/sub", dirs)
        names = [e.name for e in list_entries(self.root, self.root / "impl")]
        self.assertEqual(names, ["sub/"])
        self.assertNotIn(self.root / "impl/sub/INDEX.md", render_all(self.root))

    # 아래는 브리프 밖에서 판정과 계획 결정을 고정하는 시험이다.

    def test_page_name(self):
        self.assertEqual(page_name(1), "INDEX.md")
        self.assertEqual(page_name(2), "INDEX2.md")
        self.assertEqual(page_name(12), "INDEX12.md")

    def test_root_page_layout(self):
        text = self.page("INDEX.md")
        lines = text.split("\n")
        self.assertTrue(lines[0].startswith("<!--"))
        self.assertIn("# 색인", lines)
        self.assertIn("- [LICENSE](LICENSE) - 사용 허가", lines)
        # R8: 짝 없는 색인 폴더
        self.assertIn("- [reference/](reference/INDEX.md)", lines)
        self.assertIn("- [s.md](s.md), [s/INDEX.md](s/INDEX.md) - 문서 설명",
                      lines)
        self.assertTrue(text.endswith("\n") and not text.endswith("\n\n"))
        self.assertNotIn("\r", text)
        self.assertNotIn("앞 쪽", text)

    def test_sub_title(self):
        self.assertIn("# s 색인", self.page("s/INDEX.md").split("\n"))

    def test_pair_with_indexless_folder(self):
        # R8: 색인이 없는 폴더와의 동명 쌍
        self.write("t.md", FM)
        self.write("t/y.md", FM)
        e = [e for e in list_entries(self.root, self.root) if e.name == "t.md"][0]
        self.assertEqual(e.links, (("t.md", "t.md"), ("t/", "t/")))
        self.assertIn("- [t.md](t.md), [t/](t/) - 문서 설명",
                      self.page("INDEX.md").split("\n"))

    def test_folder_description_from_yaml(self):
        self.write("u/y.md", FM)
        self.write("INDEX.yaml", '"LICENSE":\n  description: a\n'
                   '"u/":\n  description: 폴더 설명\n')
        self.assertIn("- [u/](u/) - 폴더 설명", self.page("INDEX.md"))

    def test_operational_files_excluded(self):
        for name in ("INDEX.md", "INDEX2.md", "s/INDEX.md", ".git/x",
                     "node_modules/a.js", "__pycache__/a.pyc", "Thumbs.db",
                     "desktop.ini", "a.md~", "Icon\r"):
            self.write(name, "x\n")
        names = [e.name for e in list_entries(self.root, self.root)]
        self.assertEqual(names, ["LICENSE", "reference/", "s.md"])

    def test_symlink_excluded(self):
        try:
            os.symlink(str(self.root / "LICENSE"), str(self.root / "lnk"))
        except (OSError, NotImplementedError):
            self.skipTest("심링크를 만들 수 없다")
        names = [e.name for e in list_entries(self.root, self.root)]
        self.assertNotIn("lnk", names)

    def test_empty_folder(self):
        self.write("e/AGENTS.md", FM)
        text = self.page("e/INDEX.md")
        self.assertIn("(항목 없음)", text.split("\n"))

    def test_reference_status_and_md_desc(self):
        self.write("reference/a.md", FM)
        self.write("reference/INDEX.yaml",
                   '"r.pdf":\n  description: 원문\n  status: 처리됨\n'
                   '"a.md":\n  description: 자료\n')
        es = {e.name: e for e in list_entries(self.root, self.root / "reference")}
        self.assertEqual(es["r.pdf"].status, "처리됨")
        self.assertEqual(es["r.pdf"].description, "원문")
        self.assertIsNone(es["a.md"].status)
        self.assertEqual(es["a.md"].description, "자료")  # front matter 아님
        text = self.page("reference/INDEX.md")
        self.assertIn("- [r.pdf](r.pdf) - `처리됨` 원문", text)
        self.assertIn("- [a.md](a.md) - 자료", text)

    def test_unregistered_rendered(self):
        self.assertIn("- [r.pdf](r.pdf) - `미등록`",
                      self.page("reference/INDEX.md").split("\n"))

    def test_reference_subfolder_not_index_dir(self):
        # R5: reference/X/ 이하는 색인 폴더가 아니다
        self.write("reference/raw/AGENTS.md", FM)
        self.write("reference/raw/INDEX.yaml", "깨진 내용\n")
        self.assertNotIn("reference/raw", self.rels(index_dirs(self.root)))
        e = [e for e in list_entries(self.root, self.root / "reference")
             if e.name == "raw/"][0]
        self.assertEqual(e.links, (("raw/", "raw/"),))
        self.assertNotIn(self.root / "reference/raw/INDEX.md",
                         render_all(self.root))

    def test_norms_and_implementation(self):
        self.write("implementation/AGENTS.md", FM)
        self.write("implementation/AGENTS/x.md", FM)
        self.write("implementation/app/AGENTS.md", FM)
        self.write("AGENTS/sub/AGENTS.md", FM)
        rels = self.rels(index_dirs(self.root))
        self.assertIn("implementation", rels)
        for rel in ("implementation/app", "implementation/AGENTS",
                    "AGENTS", "AGENTS/sub"):
            self.assertNotIn(rel, rels)
        names = [e.name for e in
                 list_entries(self.root, self.root / "implementation")]
        self.assertEqual(names, ["app/"])

    def test_link_encoding(self):
        self.write("s/a(1)#[x]?%.pdf", "x\n")
        self.write("s/한글 이름.md", FM)
        es = {e.name: e for e in list_entries(self.root, self.root / "s")}
        self.assertEqual(es["a(1)#[x]?%.pdf"].links[0][1],
                         "a%281%29%23%5Bx%5D%3F%25.pdf")
        self.assertEqual(es["한글 이름.md"].links[0][1], "한글%20이름.md")
        text = self.page("s/INDEX.md")
        self.assertIn("[a(1)#\\[x\\]?%.pdf](a%281%29", text)

    @unittest.skipIf(os.name == "nt", "윈도우는 역슬래시 이름을 못 만든다")
    def test_backslash_name_is_portability_violation(self):
        self.write("s/bs\\x.md", FM)
        rels = [f.path for f in check_filename_portability(self.root)]
        self.assertIn(os.path.join("s", "bs\\x.md"), rels)
        es = {e.name: e for e in list_entries(self.root, self.root / "s")}
        self.assertEqual(es["bs\\x.md"].links[0][1], "bs%5Cx.md")
        self.assertIn("- [bs\\x.md](bs%5Cx.md)", self.page("s/INDEX.md"))

    def test_nfc_collision_raises(self):
        nfc_name = "s/" + unicodedata.normalize("NFC", "가.md")
        nfd_name = "s/" + unicodedata.normalize("NFD", "가.md")
        self.write(nfc_name, FM)
        self.write(nfd_name, FM)
        target = unicodedata.normalize("NFC", "가.md")
        names = os.listdir(str(self.root / "s"))
        same = [n for n in names
                if unicodedata.normalize("NFC", n) == target]
        if len(same) < 2:
            self.skipTest("파일시스템이 NFC와 NFD 이름을 한 파일로 합친다")
        with self.assertRaises(IndexFormatError) as cm:
            list_entries(self.root, self.root / "s")
        self.assertIsNotNone(cm.exception.path)
        with self.assertRaises(IndexFormatError):
            render_all(self.root)

    def test_nfc_collision_raises_any_fs(self):
        # 파일시스템과 무관하게 충돌 분기를 확인한다.
        d = self.root / "s"
        a = d / unicodedata.normalize("NFC", "가.md")
        b = d / unicodedata.normalize("NFD", "가.md")
        with mock.patch.object(_index_core, "_entry_children",
                               return_value=[a, b]):
            with self.assertRaises(IndexFormatError) as cm:
                list_entries(self.root, d)
        self.assertEqual(cm.exception.path, b)

    def test_bad_front_matter_desc_is_none(self):
        self.write("s/b.md", "---\ndescription: a: b\n---\n")
        es = {e.name: e for e in list_entries(self.root, self.root / "s")}
        self.assertIsNone(es["b.md"].description)

    def test_bad_yaml_raises(self):
        self.write("INDEX.yaml", "a:\n")
        with self.assertRaises(IndexFormatError):
            list_entries(self.root, self.root)
        with self.assertRaises(IndexFormatError):
            render_all(self.root)

    def test_sequential_structure(self):
        self.assertIsNone(sequential_structure(self.root / "s"))
        self.write("s/INDEX.yaml", '".":\n  structure: 날짜순\n')
        self.assertEqual(sequential_structure(self.root / "s"), "날짜순")

    def test_sequential_page_layout(self):
        self.write("s/INDEX.yaml", '".":\n  structure: 날짜순\n')
        self.write("s/2026-05/AGENTS.md", FM)
        text = self.page("s/INDEX.md")
        lines = text.split("\n")
        self.assertIn("# s 색인", lines)
        self.assertIn("날짜순", lines)
        self.assertFalse([ln for ln in lines if ln.startswith("- ")])
        self.assertNotIn(self.root / "s/2026-05/INDEX.md",
                         render_all(self.root))

    def test_split_pages(self):
        for i in range(120):
            self.write(f"s/doc-{i:03}.md", FM_LONG_DESC)
        pages = render_pages(self.root, self.root / "s")
        n = len(pages)
        all_rel = render_all(self.root)
        for k in range(1, n + 1):
            self.assertEqual(all_rel[self.root / "s" / page_name(k)],
                             pages[k - 1])
            self.assertLessEqual(text_size(pages[k - 1]), SIZE_LIMIT_NODE)
        self.assertNotIn(self.root / "s" / page_name(n + 1), all_rel)
        self.assertIn("# s 색인 2쪽", pages[1].split("\n"))
        self.assertIn("다음 쪽 [INDEX2.md](INDEX2.md)", pages[0])
        self.assertNotIn("앞 쪽", pages[0])
        self.assertIn("앞 쪽 [INDEX.md](INDEX.md)", pages[1])
        listed = sum(p.count("\n- [") for p in pages)
        self.assertEqual(listed, 121)  # doc 120건과 x.md

    def test_oversized_entry_alone(self):
        self.write("s/big.md", "---\ndescription: "
                   + "가" * (SIZE_LIMIT_NODE + 10) + "\n---\n")
        pages = render_pages(self.root, self.root / "s")
        self.assertEqual(len(pages), 2)
        self.assertEqual(pages[0].count("\n- ["), 1)

    def test_entry_paths(self):
        self.write("impl/AGENTS.md", FM)
        self.write("impl/sub/.git", "gitdir: x\n")
        self.write("q/AGENTS.md", FM)
        self.write("q/INDEX.yaml", '".":\n  structure: 날짜순\n')
        self.write("q/2026.md", FM)
        paths = entry_paths(self.root)
        self.assertEqual(paths, sorted(paths))
        rels = self.rels(paths)
        for rel in ("LICENSE", "s.md", "s", "s/x.md", "reference",
                    "reference/r.pdf", "impl", "impl/sub", "q"):
            self.assertIn(rel, rels)
        for rel in ("AGENTS.md", ".hidden", "INDEX.yaml", "q/2026.md",
                    "AGENTS", "s/AGENTS.md"):
            self.assertNotIn(rel, rels)

    def test_entry_is_frozen(self):
        e = Entry("a", (("a", "a"),), None, None)
        with self.assertRaises(Exception):
            e.name = "b"

    def test_nested_cache_cleared(self):
        # 중첩 저장소 판정은 프로세스 캐시를 쓴다. 캐시를 비우면 반영된다.
        index_dirs(self.root)
        self.write("s/AGENTS.md", FM)
        self.write("s/.git", "gitdir: x\n")
        _audit_core._nested_repo_cache.clear()
        self.assertNotIn("s", self.rels(index_dirs(self.root)))


if __name__ == "__main__":
    unittest.main()

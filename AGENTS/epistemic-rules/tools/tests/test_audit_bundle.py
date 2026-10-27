"""상류 묶음의 출처 태그(항목 29)와 동일성(항목 30), 목록 생성 시험."""

import contextlib
import io
import os
import sys
import tempfile
import unicodedata
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import _audit_core  # noqa: E402
from _audit_core import VIOLATION, WARNING  # noqa: E402
from _bundle_core import (  # noqa: E402
    MANIFEST_REL, ManifestFormatError, bundle_files, file_digest, own_root,
    read_manifest, render_manifest)
from audit import run_audit  # noqa: E402
from audit_bundle import check_bundle_identity, check_source_tags  # noqa: E402
from build_index import main, write_bundle_manifest  # noqa: E402

FM_SRC = ("---\ndate created: 2026-01-01\ndate modified: 2026-01-01\n"
          "tags: [x, epistemic-rules]\n---\n본문\n")
FM_NO_SRC = ("---\ndate created: 2026-01-01\ndate modified: 2026-01-01\n"
             "tags: [x]\n---\n본문\n")
HASH = "a" * 64


class BundleCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self._other = tempfile.TemporaryDirectory()
        self.addCleanup(self._other.cleanup)
        _audit_core._nested_repo_cache.clear()
        self.addCleanup(_audit_core._nested_repo_cache.clear)
        self.write("AGENTS/epistemic-rules.md", FM_SRC)
        self.write("AGENTS/epistemic-rules/x.md", FM_SRC)
        self.write("AGENTS/epistemic-rules/tools/t.py", "x = 1\n")
        self.write("w/AGENTS/epistemic-rules.md", FM_SRC)
        self.tools = self.root / "AGENTS/epistemic-rules/tools"
        write_bundle_manifest(self.root, self.tools)

    def write(self, rel, text):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        return p

    def write_bytes(self, rel, data):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        return p

    def append(self, rel, text):
        with (self.root / rel).open("a", encoding="utf-8") as f:
            f.write(text)

    def identity(self):
        return check_bundle_identity(self.root, self.tools)

    def paths(self, severity):
        return [f.path for f in self.identity() if f.severity == severity]

    def sev(self, fn):
        return [f.severity for f in fn(self.root)]


class ManifestTest(BundleCase):
    def test_lists_bundles_not_self(self):
        rels = [p.relative_to(self.root).as_posix()
                for p in bundle_files(self.root)]
        self.assertIn("w/AGENTS/epistemic-rules.md", rels)
        self.assertNotIn(MANIFEST_REL, rels)

    def test_crlf_same_digest(self):
        a = self.write_bytes("a.txt", b"x\r\ny\n")
        b = self.write_bytes("b.txt", b"x\ny\n")
        self.assertEqual(file_digest(a), file_digest(b))

    def test_lone_cr_differs(self):
        a = self.write_bytes("a.txt", b"x\ry\n")
        b = self.write_bytes("b.txt", b"x\ny\n")
        self.assertNotEqual(file_digest(a), file_digest(b))

    def test_cache_and_dot_ignored(self):
        self.write("AGENTS/epistemic-rules/tools/__pycache__/t.pyc", "x")
        self.write("AGENTS/epistemic-rules/.DS_Store", "x")
        self.assertEqual(self.identity(), [])

    def test_pyc_and_byproduct_ignored(self):
        self.write("AGENTS/epistemic-rules/tools/t.pyc", "x")
        self.write("AGENTS/epistemic-rules/Thumbs.db", "x")
        self.write("AGENTS/epistemic-rules/draft.md~", "x")
        self.assertEqual(self.identity(), [])

    def test_reference_copy_ignored(self):
        self.write("reference/raw/AGENTS/epistemic-rules.md", "x")
        self.assertEqual(self.identity(), [])

    def test_implementation_clone_ignored(self):
        self.write("implementation/p/AGENTS/epistemic-rules.md", "x")
        self.assertEqual(self.identity(), [])

    def test_top_level_norms_folders_listed(self):
        self.write("reference/AGENTS/epistemic-rules.md", FM_SRC)
        self.write("implementation/AGENTS/epistemic-rules/c.md", FM_SRC)
        rels = [p.relative_to(self.root).as_posix()
                for p in bundle_files(self.root)]
        self.assertIn("reference/AGENTS/epistemic-rules.md", rels)
        self.assertIn("implementation/AGENTS/epistemic-rules/c.md", rels)

    def test_nested_repo_ignored(self):
        self.write("sub/.git", "gitdir: x\n")
        self.write("sub/AGENTS/epistemic-rules.md", "x")
        # 캐시가 .git 작성 전 값을 쥐고 있다
        _audit_core._nested_repo_cache.clear()
        self.assertEqual(self.identity(), [])

    def test_render_sorted_nfc_lines(self):
        nfd = unicodedata.normalize("NFD", "가")
        self.write("AGENTS/epistemic-rules/" + nfd + ".md", FM_SRC)
        lines = render_manifest(self.root).splitlines()
        paths = [ln.split("  ", 1)[1] for ln in lines]
        self.assertEqual(paths, sorted(paths))
        self.assertIn("AGENTS/epistemic-rules/가.md", paths)
        for ln in lines:
            self.assertRegex(ln, r"^[0-9a-f]{64}  \S")

    def test_nfd_name_on_disk_matches(self):
        nfd = unicodedata.normalize("NFD", "나")
        self.write("AGENTS/epistemic-rules/" + nfd + ".md", FM_SRC)
        write_bundle_manifest(self.root, self.tools)
        self.assertEqual(self.identity(), [])

    def test_read_roundtrip(self):
        got = read_manifest(self.root / MANIFEST_REL)
        self.assertIn("AGENTS/epistemic-rules/x.md", got)
        self.assertEqual(got["AGENTS/epistemic-rules/x.md"],
                         file_digest(self.root / "AGENTS/epistemic-rules/x.md"))

    def test_read_error_has_line(self):
        p = self.write("m.txt", HASH + "  a.md\nzz\n")
        with self.assertRaises(ManifestFormatError) as cm:
            read_manifest(p)
        self.assertEqual(cm.exception.line, 2)

    def test_read_rejects_uppercase_and_single_space(self):
        for bad in ("A" * 64 + "  a.md\n", HASH + " a.md\n", HASH + "  \n"):
            p = self.write("m.txt", bad)
            with self.assertRaises(ManifestFormatError):
                read_manifest(p)

    def test_read_rejects_duplicate(self):
        p = self.write("m.txt", (HASH + "  a.md\n") * 2)
        with self.assertRaises(ManifestFormatError) as cm:
            read_manifest(p)
        self.assertEqual(cm.exception.line, 2)

    def test_read_accepts_crlf(self):
        p = self.write_bytes("m.txt", (HASH + "  a.md\r\n").encode("ascii"))
        self.assertEqual(read_manifest(p), {"a.md": HASH})

    def test_own_root(self):
        self.assertTrue(own_root(self.root, self.tools))
        self.assertFalse(own_root(self.root, Path(self._other.name)))


class IdentityTest(BundleCase):
    def test_clean(self):
        self.assertEqual(self.identity(), [])

    def test_modified(self):
        self.append("AGENTS/epistemic-rules/x.md", "고유 절\n")
        self.assertEqual(self.paths(VIOLATION),
                         ["AGENTS/epistemic-rules/x.md"])

    def test_crlf_checkout_clean(self):
        p = self.root / "AGENTS/epistemic-rules/x.md"
        data = p.read_bytes().replace(b"\n", b"\r\n")
        p.write_bytes(data)
        self.assertEqual(self.identity(), [])

    def test_extra_file_in_bundle(self):
        self.write("AGENTS/epistemic-rules/tools/mine.py", "x")
        self.assertEqual(len(self.identity()), 1)

    def test_new_bundle_location(self):
        self.write("k/AGENTS/epistemic-rules.md", FM_SRC)
        self.assertEqual(len(self.identity()), 1)

    def test_missing(self):
        (self.root / "w/AGENTS/epistemic-rules.md").unlink()
        self.assertEqual(len(self.identity()), 1)

    def test_findings_are_bundle_category(self):
        self.append("AGENTS/epistemic-rules/x.md", "y\n")
        got = self.identity()
        self.assertEqual({f.category for f in got}, {"bundle"})

    def test_message_names_both_remedies(self):
        self.append("AGENTS/epistemic-rules/x.md", "y\n")
        msg = self.identity()[0].message
        self.assertIn("--bundle-manifest", msg)

    def test_bad_manifest_line(self):
        self.append(MANIFEST_REL, "zz\n")
        self.assertEqual(self.paths(VIOLATION), [MANIFEST_REL])

    def test_bad_manifest_skips_comparison(self):
        self.append(MANIFEST_REL, "zz\n")
        self.append("AGENTS/epistemic-rules/x.md", "y\n")
        self.assertEqual(self.paths(VIOLATION), [MANIFEST_REL])

    def test_bad_manifest_reports_line(self):
        self.append(MANIFEST_REL, "zz\n")
        n = len((self.root / MANIFEST_REL).read_text().splitlines())
        self.assertIn("%d" % n, self.identity()[0].message)

    def test_absent_manifest_own_tools(self):
        (self.root / MANIFEST_REL).unlink()
        got = self.identity()
        self.assertEqual([f.path for f in got], [MANIFEST_REL])
        self.assertEqual([f.severity for f in got], [VIOLATION])

    def test_absent_manifest_foreign_tools(self):
        (self.root / MANIFEST_REL).unlink()
        got = check_bundle_identity(self.root, Path(self._other.name))
        self.assertEqual(got, [])

    def test_foreign_tools_skip_comparison(self):
        self.append("AGENTS/epistemic-rules/x.md", "y\n")
        got = check_bundle_identity(self.root, Path(self._other.name))
        self.assertEqual(got, [])

    def test_default_tools_dir_is_module_folder(self):
        # 기본 인자로는 도구 폴더가 임시 루트와 달라 검사를 건너뛴다.
        self.append("AGENTS/epistemic-rules/x.md", "y\n")
        self.assertEqual(check_bundle_identity(self.root), [])

    def test_run_audit_includes_bundle_checks(self):
        self.write("AGENTS/local.md", FM_SRC)
        cats = {f.category for f in run_audit(self.root)}
        self.assertIn("source-tag", cats)


class SourceTagTest(BundleCase):
    def test_clean(self):
        self.assertEqual(check_source_tags(self.root), [])

    def test_bundle_doc_without_tag(self):
        self.write("AGENTS/epistemic-rules/y.md", FM_NO_SRC)
        self.assertEqual(self.sev(check_source_tags), [VIOLATION])

    def test_bundle_doc_without_tags_key(self):
        self.write("AGENTS/epistemic-rules/y.md", "---\nk: v\n---\nz\n")
        self.assertEqual(self.sev(check_source_tags), [VIOLATION])

    def test_bundle_doc_without_front_matter(self):
        self.write("AGENTS/epistemic-rules/y.md", "본문\n")
        self.assertEqual(self.sev(check_source_tags), [VIOLATION])

    def test_summary_file_checked(self):
        self.write("AGENTS/epistemic-rules.md", FM_NO_SRC)
        got = [(f.severity, f.path) for f in check_source_tags(self.root)]
        self.assertEqual(got, [(VIOLATION, "AGENTS/epistemic-rules.md")])

    def test_category(self):
        self.write("AGENTS/local.md", FM_SRC)
        self.assertEqual(check_source_tags(self.root)[0].category,
                         "source-tag")

    def test_tag_outside_bundle_warns(self):
        self.write("AGENTS/local.md", FM_SRC)
        self.assertEqual(self.sev(check_source_tags), [WARNING])

    def test_block_style_tag_read(self):
        text = "---\ntags:\n  - x\n  - epistemic-rules\n---\nz\n"
        self.write("AGENTS/epistemic-rules/y.md", text)
        self.assertEqual(check_source_tags(self.root), [])

    def test_unreadable_tags_skipped(self):
        text = "---\ntags: a, b\n---\nz\n"
        self.write("AGENTS/epistemic-rules/y.md", text)
        self.write("AGENTS/local.md", text)
        self.assertEqual(check_source_tags(self.root), [])

    def test_index_pages_ignored(self):
        # front matter에 출처 태그를 넣어, 색인 쪽을 거르지 않는 구현이면
        # 경고가 나서 실패하게 한다.
        self.write_bytes(
            "INDEX.md",
            "---\ntags: [epistemic-rules]\n---\n# 색인\n".encode("utf-8"))
        self.assertEqual(check_source_tags(self.root), [])

    def test_tool_pointer_files_ignored(self):
        self.write("AGENTS/epistemic-rules/CLAUDE.md", "@AGENTS.md\n")
        self.assertEqual(check_source_tags(self.root), [])


class BuildManifestTest(BundleCase):
    def test_written_then_noop(self):
        self.append("AGENTS/epistemic-rules/x.md", "y\n")
        got = write_bundle_manifest(self.root, self.tools)
        self.assertEqual(got, [MANIFEST_REL])
        self.assertEqual(write_bundle_manifest(self.root, self.tools), [])

    def test_dry_run_writes_nothing(self):
        self.append("AGENTS/epistemic-rules/x.md", "y\n")
        before = (self.root / MANIFEST_REL).read_bytes()
        got = write_bundle_manifest(self.root, self.tools, dry_run=True)
        self.assertEqual(got, [MANIFEST_REL])
        self.assertEqual((self.root / MANIFEST_REL).read_bytes(), before)

    def test_first_write_without_manifest(self):
        (self.root / MANIFEST_REL).unlink()
        self.assertEqual(write_bundle_manifest(self.root, self.tools),
                         [MANIFEST_REL])
        self.assertEqual(self.identity(), [])

    def test_manifest_refused_outside(self):
        with self.assertRaises(ValueError):
            write_bundle_manifest(self.root, Path(self._other.name))

    def test_main_refuses_foreign_root(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code = main([str(self.root), "--bundle-manifest"])
        self.assertEqual(code, 2)
        self.assertNotEqual(err.getvalue(), "")

    def test_main_refusal_leaves_index_alone(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            main([str(self.root), "--bundle-manifest"])
        self.assertFalse((self.root / "INDEX.md").exists())


if __name__ == "__main__":
    unittest.main()

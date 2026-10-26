"""감사의 색인 정합(항목 11), 설명 원본(항목 28) 검사와 색인 쪽 취급 시험."""

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import _audit_core  # noqa: E402
from _audit_core import VIOLATION, WARNING, iter_md_files  # noqa: E402
from audit import run_audit  # noqa: E402
from audit_content import check_ascii_punctuation  # noqa: E402
from audit_frontmatter import check_front_matter  # noqa: E402
from audit_index import check_index_files, check_index_sources  # noqa: E402
from audit_structure import (  # noqa: E402
    check_descriptors, check_empty_folders, check_name_collision,
    check_scaffold_state_markers)
from build_index import build  # noqa: E402

FM = "---\ndescription: 문서 설명\n---\n본문\n"
FM_MARKER_DESC = "---\ndescription: 스캐폴드 상태 - 미작성\n---\n"
FM_FULL = ("---\ndate created: 2026-01-01\n"
           "date modified: 2026-01-01\ntags: [test]\n---\n본문\n")
LONG = "가나다라마바사아자차" * 21
DASH = "\u2014"


class IndexAuditTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        _audit_core._nested_repo_cache.clear()
        self.addCleanup(_audit_core._nested_repo_cache.clear)
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
        build(self.root)

    def write(self, name, text):
        p = self.root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        return p

    def sev(self, fn):
        return [f.severity for f in fn(self.root)]

    def found(self, fn):
        return [(f.severity, f.path) for f in fn(self.root)]

    def sources(self):
        return [f for f in check_index_sources(self.root)
                if f.path != "reference/r.pdf"]

    # --- 항목 11: 색인 정합 ---

    def test_clean(self):
        self.assertEqual(check_index_files(self.root), [])

    def test_missing_warns(self):
        (self.root / "s/INDEX.md").unlink()
        self.assertEqual(self.sev(check_index_files), [WARNING])

    def test_stale_violation(self):
        self.write("s/y.md", FM)
        self.assertEqual(self.sev(check_index_files), [VIOLATION])

    def test_index_in_norms_dir(self):
        self.write("AGENTS/INDEX.md", "x\n")
        self.assertIn(VIOLATION, self.sev(check_index_files))

    def test_sequential_top_compared(self):
        self.write("s/INDEX.yaml", '".":\n  structure: 날짜순\n')
        self.assertEqual(self.sev(check_index_files), [VIOLATION])  # 낡음
        build(self.root)
        self.assertEqual(check_index_files(self.root), [])
        paths = [f.path for f in check_index_sources(self.root)]
        self.assertNotIn("s/INDEX.yaml", paths)

    def test_sequential_declaration_broken(self):
        self.write("s/INDEX.yaml", '".":\n  structure: ""\n')
        self.assertEqual(self.sev(check_index_files), [VIOLATION])

    def test_sequential_extra_entries_warn(self):
        self.write("s/INDEX.yaml",
                   '".":\n  structure: 날짜순\n"x.md":\n  description: y\n')
        self.assertIn(WARNING, self.sev(check_index_sources))

    def test_nested_repo_not_audited(self):
        self.write("sub/.git", "gitdir: x\n")
        self.write("sub/AGENTS.md", FM)
        self.write("sub/INDEX.md", "x\n")  # 남의 저장소의 색인
        _audit_core._nested_repo_cache.clear()
        found = check_index_files(self.root)
        self.assertFalse([f for f in found
                          if f.path == "sub" or f.path.startswith("sub/")])

    def test_reference_index_audited(self):
        paths = [p.relative_to(self.root).as_posix()
                 for p in iter_md_files(self.root)]
        self.assertIn("reference/INDEX.md", paths)

    def test_status_vocab(self):
        self.write("reference/INDEX.yaml",
                   '"r.pdf":\n  status: 끝\n')
        self.assertEqual(self.sev(check_index_sources), [WARNING])

    def test_scaffold_marker_in_description(self):
        self.write("s/c.md", FM_MARKER_DESC + "본문\n")
        self.assertEqual(len(check_scaffold_state_markers(self.root)), 1)

    def test_scaffold_marker_in_both(self):
        self.write("s/c.md", FM_MARKER_DESC + "스캐폴드 상태다.\n")
        self.assertEqual(check_scaffold_state_markers(self.root), [])

    def test_format_error_file_and_line(self):
        self.write("INDEX.yaml",
                   '"LICENSE":\n  description: 사용 허가\nbad\n')
        found = check_index_files(self.root)
        self.assertEqual(len(found), 1)
        self.assertEqual((found[0].severity, found[0].path),
                         (VIOLATION, "INDEX.yaml"))
        self.assertIn("3행", found[0].message)

    def test_surplus_page_violation(self):
        self.write("s/INDEX2.md", "x\n")
        self.assertEqual(self.found(check_index_files),
                         [(VIOLATION, "s/INDEX2.md")])

    def test_crlf_page_equal(self):
        p = self.root / "s/INDEX.md"
        p.write_bytes(p.read_bytes().replace(b"\n", b"\r\n"))
        self.assertEqual(check_index_files(self.root), [])

    def test_index_yaml_without_descriptor(self):
        self.write("s/z/INDEX.yaml", '".":\n  structure: 날짜순\n')
        self.assertIn((VIOLATION, "s/z/INDEX.yaml"),
                      self.found(check_index_files))

    def test_reference_subfolder_not_index_folder(self):
        self.write("reference/raw/AGENTS.md", FM)
        self.write("reference/raw/INDEX.md", "x\n")
        self.write("reference/raw/INDEX.yaml", "bad\n")
        paths = [f.path for f in check_index_files(self.root)]
        self.assertFalse([p for p in paths if p.startswith("reference/raw")])

    def test_reference_norms_dir_index_violation(self):
        self.write("reference/AGENTS/epistemic-rules.md", FM)
        self.write("reference/AGENTS/INDEX.md", "x\n")
        self.assertIn((VIOLATION, "reference/AGENTS/INDEX.md"),
                      self.found(check_index_files))

    def test_reference_raw_norms_dir_ignored(self):
        self.write("reference/raw/AGENTS/INDEX.md", "x\n")
        paths = [f.path for f in check_index_files(self.root)]
        self.assertFalse([p for p in paths if p.startswith("reference/raw")])

    def test_missing_warning_names_tool(self):
        (self.root / "s/INDEX.md").unlink()
        found = check_index_files(self.root)
        self.assertIn("build_index.py", found[0].message)

    def test_punct_reported_at_source_not_page(self):
        self.write("s/y.md", "---\ndescription: a%sb\n---\n" % DASH)
        build(self.root)
        self.assertIn(DASH, (self.root / "s/INDEX.md").read_text("utf-8"))
        self.assertEqual(check_ascii_punctuation(self.root), [])
        found = self.sources()
        self.assertEqual([f.path for f in found], ["s/y.md"])
        self.assertIn("2행", found[0].message)

    def test_punct_in_yaml_description(self):
        self.write("INDEX.yaml",
                   '"LICENSE":\n  description: a%sb\n' % DASH)
        found = self.sources()
        self.assertEqual([f.path for f in found], ["INDEX.yaml"])
        self.assertIn("1행", found[0].message)

    def test_status_outside_reference_unused(self):
        self.write("INDEX.yaml", '"LICENSE":\n  status: 처리됨\n')
        self.assertEqual(len(self.sources()), 1)

    def test_run_audit_includes_index(self):
        (self.root / "s/INDEX.md").unlink()
        cats = [(f.category, f.path) for f in run_audit(self.root)]
        self.assertIn(("index", "s"), cats)

    # --- 항목 28: 설명 원본 ---

    def test_unregistered_reference_warns(self):
        self.assertEqual(self.found(check_index_sources),
                         [(WARNING, "reference/r.pdf")])

    def test_registered_reference_clean(self):
        self.write("reference/INDEX.yaml",
                   '"r.pdf":\n  description: 자료\n  status: 처리됨\n')
        self.assertEqual(check_index_sources(self.root), [])

    def test_status_missing(self):
        self.write("reference/INDEX.yaml",
                   '"r.pdf":\n  description: 자료\n')
        self.assertEqual(self.sev(check_index_sources), [WARNING])

    def test_missing_target(self):
        self.write("INDEX.yaml", '"LICENSE":\n  description: a\n'
                   '"gone.txt":\n  description: b\n')
        self.assertEqual([(f.severity, f.path) for f in self.sources()],
                         [(WARNING, "INDEX.yaml")])

    def test_excluded_name_is_missing_target(self):
        self.write("INDEX.yaml", '".hidden":\n  description: a\n'
                   '"LICENSE":\n  description: b\n')
        self.assertEqual(len(self.sources()), 1)

    def test_md_entry_outside_reference(self):
        self.write("INDEX.yaml", '"s.md":\n  description: a\n')
        self.assertEqual(len(self.sources()), 1)

    def test_paired_folder_entry(self):
        self.write("INDEX.yaml", '"s/":\n  description: a\n')
        self.assertEqual(len(self.sources()), 1)

    def test_folder_entry_without_pair_clean(self):
        self.write("INDEX.yaml", '"reference/":\n  description: a\n')
        self.assertEqual(self.sources(), [])

    def test_unknown_key(self):
        self.write("INDEX.yaml", '"LICENSE":\n  note: a\n')
        self.assertEqual(len(self.sources()), 1)

    def test_long_yaml_description(self):
        self.write("INDEX.yaml", '"LICENSE":\n  description: %s\n' % LONG)
        self.assertEqual(len(self.sources()), 1)

    def test_long_front_matter_description(self):
        self.write("s/x.md", "---\ndescription: %s\n---\n" % LONG)
        self.assertEqual([f.path for f in self.sources()], ["s/x.md"])

    def test_bad_front_matter_description(self):
        self.write("s/x.md", "---\ntags: [a]\ndescription: a: b\n---\n")
        found = self.sources()
        self.assertEqual([f.path for f in found], ["s/x.md"])
        self.assertIn("3행", found[0].message)

    def test_sources_skip_format_error(self):
        self.write("INDEX.yaml", "bad\n")
        self.assertEqual(check_index_sources(self.root), [])


class ChangedBehaviorTest(unittest.TestCase):
    """색인 쪽 파일이 기존 검사에서 다르게 다뤄지는 동작."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        _audit_core._nested_repo_cache.clear()
        self.addCleanup(_audit_core._nested_repo_cache.clear)
        self.write("AGENTS.md", FM_FULL)
        self.write("CLAUDE.md", "@AGENTS.md\n")

    def write(self, name, text):
        p = self.root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        return p

    def test_front_matter_exempt_for_index_pages(self):
        self.write("s/AGENTS.md", FM_FULL)
        self.write("s/x.md", FM_FULL)
        build(self.root)
        self.write("s/INDEX2.md", "x\n")
        self.assertTrue((self.root / "INDEX.md").is_file())
        self.assertEqual(check_front_matter(self.root), [])

    def test_index_pages_not_counted_in_md(self):
        self.write("s/AGENTS.md", FM_FULL)
        for i in range(24):
            self.write("s/d%02d.md" % i, FM_FULL)
        self.write("s/INDEX.md", "x\n")
        self.write("s/INDEX2.md", "x\n")
        self.assertEqual(
            [f for f in check_descriptors(self.root)
             if f.category == "folder-size"], [])

    def test_index_only_folder_is_empty(self):
        self.write("e/AGENTS.md", FM_FULL)
        self.write("e/CLAUDE.md", "@AGENTS.md\n")
        self.write("e/INDEX.md", "x\n")
        self.write("e/INDEX.yaml", "\n")
        self.assertIn("e", [f.path for f in check_empty_folders(self.root)])

    def test_index_only_pair_warns(self):
        self.write("t.md", FM_FULL)
        self.write("t/AGENTS.md", FM_FULL)
        self.write("t/INDEX.md", "x\n")
        self.assertEqual([f.path for f in check_name_collision(self.root)],
                         ["t.md"])

    def test_implementation_index_listed(self):
        self.write("implementation/AGENTS.md", FM_FULL)
        self.write("implementation/INDEX.md", "x\n")
        self.write("implementation/app/INDEX.md", "x\n")
        self.write("reference/raw/INDEX.md", "x\n")
        paths = [p.relative_to(self.root).as_posix()
                 for p in iter_md_files(self.root)]
        self.assertIn("implementation/INDEX.md", paths)
        self.assertNotIn("implementation/app/INDEX.md", paths)
        self.assertNotIn("reference/raw/INDEX.md", paths)


if __name__ == "__main__":
    unittest.main()

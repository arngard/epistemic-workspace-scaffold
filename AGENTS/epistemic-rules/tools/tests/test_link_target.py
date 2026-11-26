"""링크와 가져오기 대상의 실재 판정 시험(항목 9, 19, 26).

대상 판정은 디렉토리 엔트리를 직접 대조하므로, 대소문자를 무시하는 파일시스템
(윈도우, 기본 macOS)에서도 대소문자 불일치를 리눅스와 같이 잡아야 한다.
"""

import os
import sys
import tempfile
import unicodedata
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from _audit_core import VIOLATION, WARNING, classify_target, resolve_link  # noqa: E402
from audit_links import check_imports, check_links, check_section_refs  # noqa: E402

FM = "---\ndate created: 2026-01-01\ndate modified: 2026-01-01\ntags: [x]\n---\n"


class TargetCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        # resolve하지 않은 루트로 돌린다. 임시 폴더가 심볼릭 링크 아래인
        # 환경(macOS /var)에서도 판정이 루트 밖으로 새지 않아야 한다.
        self.root = Path(self._tmp.name) / "ws"
        self.write("Docs/Target.md", "\n# 대상 절\n")

    def write(self, rel, body=""):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(FM + body, encoding="utf-8")
        return path

    def found(self, check, rel):
        return [(f.severity, f.message) for f in check(self.root) if f.path == rel]


class LinkCaseTest(TargetCase):
    def test_exact_link_passes(self):
        self.write("a.md", "[t](Docs/Target.md)\n")
        self.assertEqual(self.found(check_links, "a.md"), [])

    @unittest.skipIf(os.name != "nt", "윈도우 경로 길이 제한(MAX_PATH)")
    def test_long_unfolded_path_still_found(self):
        # 접은 경로는 짧고 접지 않은 경로만 260자를 넘는다.
        deep = "/".join(["d" * 40] * 3)
        target = "../../../" + "./" * 60 + "Docs/Target.md"
        rel = deep + "/a.md"
        self.write(rel, f"[t]({target})\n@{target}\n")
        self.assertGreater(len(os.path.join(str(self.root / deep), target)), 260)
        self.assertEqual(self.found(check_links, rel), [])
        self.assertEqual(self.found(check_imports, rel), [])

    def test_case_mismatch_link_is_violation(self):
        self.write("a.md", "[t](docs/target.md)\n")
        got = self.found(check_links, "a.md")
        self.assertEqual(len(got), 1, got)
        self.assertEqual(got[0][0], VIOLATION)
        self.assertIn("대소문자 불일치", got[0][1])

    def test_case_mismatch_through_parent(self):
        self.write("sub/a.md", "[t](../docs/Target.md)\n")
        got = self.found(check_links, "sub/a.md")
        self.assertEqual([s for s, _ in got], [VIOLATION])
        self.assertIn("대소문자 불일치", got[0][1])

    def test_missing_link_is_violation(self):
        self.write("a.md", "[t](Docs/none.md)\n")
        got = self.found(check_links, "a.md")
        self.assertEqual([s for s, _ in got], [VIOLATION])
        self.assertIn("깨진 링크", got[0][1])

    def test_resolve_keeps_written_case(self):
        source = self.root / "a.md"
        target = resolve_link(source, "docs/target.md")
        self.assertEqual(target.name, "target.md")
        self.assertEqual(target.parent.name, "docs")
        self.assertEqual(classify_target(self.root, target), "case")

    def test_section_ref_to_case_mismatch_not_reported(self):
        # 대상이 열리는지가 OS마다 달라, 절 대조 경고는 OS와 무관하게 내지 않는다.
        self.write("a.md", '[t](docs/target.md) "없는 절"\n')
        self.assertEqual(self.found(check_section_refs, "a.md"), [])

    def test_section_ref_to_nfc_mismatch_not_reported(self):
        nfd = unicodedata.normalize("NFD", "가.md")
        self.write(nfd, "\n# 있는 절\n")
        if nfd not in [p.name for p in self.root.iterdir()]:
            self.skipTest("NFD 이름을 그대로 두지 않는 파일시스템")
        self.write("a.md", "[t](" + unicodedata.normalize("NFC", "가.md") + ') "없는 절"\n')
        self.assertEqual(self.found(check_section_refs, "a.md"), [])
        got = self.found(check_links, "a.md")
        self.assertEqual([s for s, _ in got], [WARNING], got)


class LinkedTargetTest(TargetCase):
    """링크 폴더를 거친 대상: 실제 대상으로 실재와 절을 판정한다."""

    def dir_link(self, target, rel):
        link = self.root / rel
        if os.name == "nt":
            import _winapi
            _winapi.CreateJunction(str(target), str(link))
            return link
        try:
            os.symlink(str(target), str(link), target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("심볼릭 링크를 만들 권한이 없음")
        return link

    @unittest.skipIf(os.name == "nt", "윈도우는 .. 을 링크를 따르기 전에 문자열로 푼다")
    def test_dotdot_reaches_real_target_only(self):
        # 접은 경로 Docs/Other.md는 없고 실제 대상 elsewhere/Other.md만 있다.
        sub = Path(self._tmp.name) / "elsewhere" / "sub"
        sub.mkdir(parents=True)
        (sub.parent / "Other.md").write_text("x\n", encoding="utf-8")
        self.dir_link(sub, "Docs/alias")
        self.write("a.md", "[t](Docs/alias/../Other.md)\n")
        self.write("AGENTS.md", "\n@Docs/alias/../Other.md\n")
        self.assertEqual(self.found(check_links, "a.md"), [])
        self.assertEqual(self.found(check_imports, "AGENTS.md"), [])

    @unittest.skipIf(os.name == "nt", "윈도우는 .. 을 링크를 따르기 전에 문자열로 푼다")
    def test_section_ref_reads_real_target(self):
        # 접은 경로 Docs/Target.md("대상 절")가 아니라 실제 대상 real/Target.md를 읽는다.
        sub = self.root / "real" / "sub"
        sub.mkdir(parents=True)
        (sub.parent / "Target.md").write_text(FM + "\n# 실제 절\n", encoding="utf-8")
        self.dir_link(sub, "Docs/alias")
        self.write("a.md", '[t](Docs/alias/../Target.md) "실제 절"\n')
        self.assertEqual(self.found(check_section_refs, "a.md"), [])
        self.write("a.md", '[t](Docs/alias/../Target.md) "대상 절"\n')
        got = self.found(check_section_refs, "a.md")
        self.assertEqual([s for s, _ in got], [WARNING], got)

    def test_section_ref_through_link_outside_skipped(self):
        # 링크를 따라 루트 밖으로 나간 대상은 읽지 않는다. 링크 자체는 유효하다.
        out = Path(self._tmp.name) / "outside"
        out.mkdir()
        (out / "X.md").write_text("\n# 바깥 절\n", encoding="utf-8")
        self.dir_link(out, "Docs/out")
        self.write("a.md", '[t](Docs/out/X.md) "없는 절"\n')
        self.assertEqual(self.found(check_section_refs, "a.md"), [])
        self.assertEqual(self.found(check_links, "a.md"), [])


class BrokenLinkTargetTest(TargetCase):
    """표기는 디렉토리 엔트리와 맞지만 실제로 열리지 않는 대상."""

    def symlink(self, target, rel, is_dir=False):
        link = self.root / rel
        try:
            os.symlink(str(target), str(link), target_is_directory=is_dir)
        except (OSError, NotImplementedError):
            self.skipTest("심볼릭 링크를 만들 권한이 없음")
        return link

    def test_broken_symlink_link_and_import(self):
        self.symlink(self.root / "Docs/none.md", "Docs/broken.md")
        self.write("a.md", "[t](Docs/broken.md)\n")
        self.write("AGENTS.md", "\n@Docs/broken.md\n")
        self.assertEqual([s for s, _ in self.found(check_links, "a.md")], [VIOLATION])
        self.assertEqual([s for s, _ in self.found(check_imports, "AGENTS.md")], [VIOLATION])

    @unittest.skipIf(os.name != "nt", "윈도우 정션")
    def test_broken_junction_link_and_import(self):
        import _winapi
        gone = Path(self._tmp.name) / "gone"
        gone.mkdir()
        _winapi.CreateJunction(str(gone), str(self.root / "Docs" / "j"))
        gone.rmdir()
        self.write("a.md", "[t](Docs/j/)\n")
        self.write("AGENTS.md", "\n@Docs/j\n")
        self.assertEqual([s for s, _ in self.found(check_links, "a.md")], [VIOLATION])
        self.assertEqual([s for s, _ in self.found(check_imports, "AGENTS.md")], [VIOLATION])

    @unittest.skipIf(os.name == "nt", "윈도우는 .. 을 링크를 따르기 전에 문자열로 푼다")
    def test_dotdot_after_link_follows_link(self):
        # Docs/alias/../Target.md는 alias를 따라간 뒤 .. 을 풀므로 루트 밖
        # elsewhere/Target.md를 가리킨다. 그곳에 파일이 없으면 깨진 링크다.
        sub = Path(self._tmp.name) / "elsewhere" / "sub"
        sub.mkdir(parents=True)
        self.symlink(sub, "Docs/alias", is_dir=True)
        self.write("a.md", "[t](Docs/alias/../Target.md)\n")
        self.write("AGENTS.md", "\n@Docs/alias/../Target.md\n")
        self.assertEqual([s for s, _ in self.found(check_links, "a.md")], [VIOLATION])
        self.assertEqual([s for s, _ in self.found(check_imports, "AGENTS.md")], [VIOLATION])
        (sub.parent / "Target.md").write_text("x\n", encoding="utf-8")
        self.assertEqual(self.found(check_links, "a.md"), [])
        self.assertEqual(self.found(check_imports, "AGENTS.md"), [])


class ImportTargetTest(TargetCase):
    def test_exact_import_passes(self):
        self.write("AGENTS.md", "\n@Docs/Target.md\n")
        self.assertEqual(self.found(check_imports, "AGENTS.md"), [])

    def test_case_mismatch_import_is_violation(self):
        self.write("AGENTS.md", "\n@docs/target.md\n")
        got = self.found(check_imports, "AGENTS.md")
        self.assertEqual([s for s, _ in got], [VIOLATION], got)
        self.assertIn("대소문자 불일치", got[0][1])

    def test_case_mismatch_in_claude_pointer(self):
        self.write("AGENTS.md")
        (self.root / "CLAUDE.md").write_text("@agents.md\n", encoding="utf-8")
        got = self.found(check_imports, "CLAUDE.md")
        self.assertEqual([s for s, _ in got], [VIOLATION], got)

    def test_missing_import_is_violation(self):
        self.write("AGENTS.md", "\n@Docs/none.md\n")
        got = self.found(check_imports, "AGENTS.md")
        self.assertEqual([s for s, _ in got], [VIOLATION])
        self.assertIn("가져오기 대상 없음", got[0][1])

    def test_home_relative_import_kept_missing(self):
        # @~/... 는 줄을 둔 파일 기준 경로로 읽으므로 대상 없음이다.
        self.write("AGENTS.md", "\n@~/x.md\n")
        got = self.found(check_imports, "AGENTS.md")
        self.assertEqual([s for s, _ in got], [VIOLATION])
        self.assertIn("가져오기 대상 없음", got[0][1])

    def test_absolute_outside_import_checks_existence(self):
        outside = Path(self._tmp.name) / "outside.md"
        outside.write_text("x\n", encoding="utf-8")
        self.write("AGENTS.md", f"\n@{outside.as_posix()}\n")
        self.assertEqual(self.found(check_imports, "AGENTS.md"), [])
        self.write("AGENTS.md", f"\n@{(outside.parent / 'none.md').as_posix()}\n")
        got = self.found(check_imports, "AGENTS.md")
        self.assertEqual([s for s, _ in got], [VIOLATION])

    def test_nfc_mismatch_import_is_warning(self):
        nfd = unicodedata.normalize("NFD", "가.md")
        path = self.root / nfd
        path.write_text("x\n", encoding="utf-8")
        names = [p.name for p in self.root.iterdir()]
        if nfd not in names:
            self.skipTest("NFD 이름을 그대로 두지 않는 파일시스템")
        self.write("AGENTS.md", "\n@" + unicodedata.normalize("NFC", "가.md") + "\n")
        got = self.found(check_imports, "AGENTS.md")
        self.assertEqual([s for s, _ in got], [WARNING], got)


if __name__ == "__main__":
    unittest.main()

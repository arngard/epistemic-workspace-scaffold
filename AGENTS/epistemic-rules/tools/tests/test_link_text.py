"""링크 표시텍스트-대상 정합 검사(항목 17) 시험."""

import os
import sys
import tempfile
import unicodedata
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from audit_links import check_link_text  # noqa: E402

FM = "---\ndate created: 2026-01-01\ndate modified: 2026-01-01\ntags: [x]\n---\n"


class LinkTextTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        for rel in ("a/x.md", "a/y.md", "b/z.md", "q/p/e.md"):
            self.write(rel)

    def tearDown(self):
        self._tmp.cleanup()

    def write(self, rel, body=""):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(FM + "\n# t\n\n" + body, encoding="utf-8")

    def link(self, src, disp, target):
        self.write(src, f"[{disp}]({target})\n")
        return len(check_link_text(self.root))

    def test_basename(self):
        self.assertEqual(self.link("b/z.md", "x.md", "../a/x.md"), 0)

    def test_root_path(self):
        self.assertEqual(self.link("b/z.md", "a/x.md", "../a/x.md"), 0)

    def test_target_verbatim(self):
        self.assertEqual(self.link("b/z.md", "../a/x.md", "../a/x.md"), 0)

    def test_target_suffix(self):
        # 대상 경로의 끝부분. 루트나 문서 기준으로는 없는 경로다.
        self.assertEqual(self.link("b/z.md", "p/e.md", "../q/p/e.md"), 0)

    def test_resolved_target_suffix(self):
        # 링크 문자열(e.md)에는 없고 해석된 대상
        # q/p/e.md의 끝부분에만 있는 형태다.
        self.write("q/p/x.md")
        self.assertEqual(self.link("q/p/x.md", "p/e.md", "e.md"), 0)

    def test_resolved_target_stale_prefix_violation(self):
        self.write("q/p/x.md")
        self.assertEqual(self.link("q/p/x.md", "old/p/e.md", "e.md"), 1)

    def test_folder(self):
        self.write("a/AGENTS.md")
        self.assertEqual(self.link("b/z.md", "a/", "../a/AGENTS.md"), 0)

    def test_nfc_basename(self):
        name = "가.md"
        self.write("a/" + name)
        disp = unicodedata.normalize("NFD", name)
        self.assertEqual(self.link("b/z.md", disp, "../a/" + name), 0)

    def test_stale_prefix_violation(self):
        self.assertEqual(self.link("b/z.md", "old/x.md", "../a/x.md"), 1)

    def test_other_existing_file_violation(self):
        self.assertEqual(self.link("b/z.md", "../a/y.md", "../a/x.md"), 1)

    def test_other_basename_violation(self):
        self.assertEqual(self.link("b/z.md", "y.md", "../a/x.md"), 1)

    def test_parent_step_suffix_violation(self):
        # 끝부분 형태는 . 과 .. 를 받지 않는다.
        self.assertEqual(self.link("b/z.md", "p/../p/e.md", "../q/p/e.md"), 1)

    def test_dot_suffix_violation(self):
        self.assertEqual(self.link("b/z.md", "./p/e.md", "../q/p/e.md"), 1)

    def test_document_relative_path(self):
        # 문서 기준으로 정규화하면 대상과 같은 경로다.
        self.assertEqual(self.link("a/y.md", "./x.md", "x.md"), 0)
        self.assertEqual(self.link("a/y.md", "../a/x.md", "x.md"), 0)

    def test_outside_root_suffix_violation(self):
        # 루트 밖 대상은 끝부분 형태를 받지 않는다.
        self.assertEqual(self.link("b/z.md", "out/x.md", "../../out/x.md"), 1)

    def test_folder_resolved(self):
        # 링크 문자열(AGENTS.md)에는 폴더명이 없고
        # 해석된 대상 r/AGENTS.md에만 있다.
        self.write("r/AGENTS.md")
        self.assertEqual(self.link("r/x.md", "r/", "AGENTS.md"), 0)

    def test_folder_wrong_name_violation(self):
        self.write("a/AGENTS.md")
        self.assertEqual(self.link("b/z.md", "c/", "../a/AGENTS.md"), 1)

    def test_folder_link_file_text_violation(self):
        # 폴더를 가리키는 링크에 파일 경로를 쓰면 대상이 아니다.
        self.write("a/AGENTS.md")
        self.assertEqual(self.link("b/z.md", "a/AGENTS.md", "../a/"), 1)

    def test_nfd_folder(self):
        nfd = unicodedata.normalize("NFD", "가")
        self.write(nfd + "/x.md")
        self.write(nfd + "/y.md")
        disp = "가/x.md"
        self.assertEqual(self.link(nfd + "/y.md", disp, "x.md"), 0)

    def test_case_violation(self):
        self.assertEqual(self.link("b/z.md", "A/x.md", "../a/x.md"), 1)
        self.assertEqual(self.link("b/z.md", "X.md", "../a/x.md"), 1)

    def test_anchor(self):
        self.assertEqual(self.link("b/z.md", "a/x.md", "../a/x.md#t"), 0)
        self.assertEqual(self.link("b/z.md", "old/x.md", "../a/x.md#t"), 1)

    def test_percent_encoded(self):
        self.write("a/x y.md")
        self.assertEqual(self.link("b/z.md", "a/x%20y.md", "../a/x%20y.md"), 0)

    def test_inline_code_display(self):
        # 표시텍스트 전체를 인라인 코드로 감싸도 안쪽 파일명을 검사한다.
        self.assertEqual(self.link("b/z.md", "`x.md`", "../a/x.md"), 0)
        self.assertEqual(self.link("b/z.md", "`a/x.md`", "../a/x.md"), 0)
        self.assertEqual(self.link("b/z.md", "`old.md`", "../a/x.md"), 1)
        self.assertEqual(self.link("b/z.md", "`old/x.md`", "../a/x.md"), 1)

    def test_quoted_section_display(self):
        # 파일명 뒤에 인용 섹션을 붙여도 앞의 파일명 부분을 검사한다.
        self.assertEqual(self.link("b/z.md", 'x.md "절 이름"', "../a/x.md"), 0)
        self.assertEqual(self.link("b/z.md", 'old.md "절 이름"', "../a/x.md"), 1)
        self.assertEqual(self.link("b/z.md", '`old.md` "절"', "../a/x.md"), 1)

    def test_inline_code_phrase_skipped(self):
        # 인라인 코드 뒤에 말이 이어지는 자연어 문구는 검사하지 않는다.
        self.assertEqual(self.link("b/z.md", "`old.md`의 설명", "../a/x.md"), 0)
        self.assertEqual(self.link("b/z.md", "`abc` 영상", "../a/x.md"), 0)
        self.assertEqual(self.link("b/z.md", '`old/x.md`의 "절"', "../a/x.md"), 0)

    def test_adjacent_inline_code_links(self):
        # 한 줄에 인라인 코드 표시텍스트 링크가 여럿이어도 각각 따로 본다.
        self.write("b/z.md", "[`x.md`](../a/x.md), [`y.md`](../a/y.md) 참고 `z` 끝\n")
        self.assertEqual(len(check_link_text(self.root)), 0)
        self.write("b/z.md", "[`x.md`](../a/x.md), [`old.md`](../a/y.md)\n")
        self.assertEqual(len(check_link_text(self.root)), 1)

    def test_link_inside_inline_code_skipped(self):
        # 문장 속 인라인 코드와 이중 백틱 코드에 든 예시 링크는 검사하지 않는다.
        self.write("b/z.md", "예: `[old.md](../a/x.md)` 와 ``[`old.md`](../a/x.md)``\n")
        self.assertEqual(len(check_link_text(self.root)), 0)

    def test_missing_target(self):
        # 대상 실존은 링크 검사 몫이다. 표시텍스트는 대상과만 맞춘다.
        self.assertEqual(self.link("b/z.md", "a/no.md", "../a/no.md"), 0)
        self.assertEqual(self.link("b/z.md", "old/no.md", "../a/no.md"), 1)


if __name__ == "__main__":
    unittest.main()

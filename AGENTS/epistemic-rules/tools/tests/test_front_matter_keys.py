"""front matter 필드 키 판정 시험(항목 1, 4, 14, 18).

필수 필드 검사와 태그 파서는 YAML처럼 콜론 뒤에 공백이나 줄 끝이 와야 키로
본다. tags:[a b]는 YAML에서 키가 아닌 한 덩어리 값이라, 필수 필드 검사가
태그 있음으로 보고 태그 파서가 키 없음으로 보면 태그 없는 문서가 조용히
통과한다.
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from _audit_core import VIOLATION, WARNING  # noqa: E402
from _tags_core import scan_tags  # noqa: E402
from audit_frontmatter import check_front_matter, check_strategy_fields  # noqa: E402

CREATED = "date created: 2026-01-01\n"
MODIFIED = "date modified: 2026-01-01\n"
TAGS = "tags: [a]\n"


class FieldKeyTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

    def doc(self, front, rel="a.md", newline="\n"):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        text = "---\n" + front + "---\n\n# t\n"
        p.write_bytes(text.replace("\n", newline).encode("utf-8"))
        return p

    def messages(self, rel="a.md"):
        return [(f.severity, f.message) for f in check_front_matter(self.root)
                if f.path == rel]

    def test_valid_keys_pass(self):
        self.doc(CREATED + MODIFIED + TAGS)
        self.assertEqual(self.messages(), [])

    def test_space_before_colon_and_block_list_pass(self):
        self.doc("date created : 2026-01-01\n" + MODIFIED + "tags:\n  - a\n")
        self.assertEqual(self.messages(), [])

    def test_crlf_keys_pass(self):
        self.doc(CREATED + MODIFIED + "tags:\n  - a\n", newline="\r\n")
        self.assertEqual(self.messages(), [])

    def test_tags_without_space_is_missing(self):
        path = self.doc(CREATED + MODIFIED + "tags:[a b]\n")
        self.assertIn((VIOLATION, "필수 필드 누락 - tags"), self.messages())
        # 태그 파서와 같은 판정이다: 두 쪽 모두 tags 키가 없다고 본다.
        docs, errors = scan_tags(self.root)
        self.assertNotIn(path, docs)
        self.assertEqual(errors, [])

    def test_date_without_space_is_missing(self):
        self.doc("date created:2026-01-01\n" + MODIFIED + TAGS)
        self.assertEqual(self.messages(), [(VIOLATION, "필수 필드 누락 - date created")])

    def test_date_closed_without_space_not_a_key(self):
        self.doc(CREATED + MODIFIED + "date closed:2026-01-02\n" + TAGS)
        self.assertEqual(self.messages(), [])

    def test_empty_date_value_still_reported(self):
        self.doc("date created:\n" + MODIFIED + TAGS)
        got = self.messages()
        self.assertEqual(len(got), 1, got)
        self.assertIn("date created 값 형식 오류", got[0][1])

    def test_strategy_field_without_space_is_missing(self):
        rel = "epistemic-structure/strategy/s.md"
        self.doc(CREATED + MODIFIED + TAGS + "importance:high\nurgency: low\n", rel=rel)
        got = [(f.severity, f.message) for f in check_strategy_fields(self.root)]
        self.assertEqual(len(got), 1, got)
        self.assertEqual(got[0][0], WARNING)
        self.assertIn("importance", got[0][1])


if __name__ == "__main__":
    unittest.main()

"""의미 감사 주기 조건의 출처 순서 시험 (자손 덮어쓰기, 옛 STATUS 셋째 칸, 상류 규칙)."""

import contextlib
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from check_semantic_audit import (  # noqa: E402
    OVERRIDE_REL, RULE_REL, STATUS_REL, UNDECIDABLE, main, parse_condition,
    parse_last_run,
)

HEAD = "| 이름 | 주기/트리거 |\n|---|---|\n"


def row(*cells):
    return "| " + " | ".join(cells) + " |\n"


def rule_text(hours):
    return HEAD + row("에피스테믹 의미 감사", f"새 커밋이 있고 {hours}시간 초과 시 (trailer `Semantic-Audit: clean`)")


def status_2col(stamp="(아직 없음)"):
    return "| 이름 | 마지막 수행 |\n|---|---|\n" + row("에피스테믹 의미 감사", stamp)


class ConditionSourceBase(unittest.TestCase):
    """임시 루트와 파일 쓰기 도우미. 시험 메서드는 두지 않는다."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name).resolve()

    def write(self, rel, text):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")


class ConditionSourceTest(ConditionSourceBase):
    def test_rule_only(self):
        self.write(str(STATUS_REL), status_2col())
        self.write(str(RULE_REL), rule_text(47))
        self.assertEqual(parse_condition(self.root), (47, "Semantic-Audit: clean", RULE_REL))

    def test_override_wins(self):
        self.write(str(STATUS_REL), status_2col())
        self.write(str(RULE_REL), rule_text(47))
        self.write(str(OVERRIDE_REL), "# x\n\n" + rule_text(24))
        self.assertEqual(parse_condition(self.root)[::2], (24, OVERRIDE_REL))

    def test_legacy_status_before_rule(self):
        self.write(
            str(STATUS_REL),
            "| 이름 | 마지막 수행 | 주기/트리거 |\n|---|---|---|\n"
            + row("에피스테믹 의미 감사", "(아직 없음)", "12시간 초과 시 `Semantic-Audit: clean`"),
        )
        self.write(str(RULE_REL), rule_text(47))
        self.assertEqual(parse_condition(self.root)[::2], (12, STATUS_REL))

    def test_none_raises(self):
        self.write(str(STATUS_REL), status_2col())
        with self.assertRaises(ValueError):
            parse_condition(self.root)

    def test_last_run_placeholder(self):
        self.write(str(STATUS_REL), status_2col())
        self.assertIsNone(parse_last_run(self.root))

    def test_last_run_timestamp_and_bad(self):
        self.write(str(STATUS_REL), status_2col("2026-10-26 09:00:00"))
        self.assertEqual(parse_last_run(self.root).hour, 9)
        self.write(str(STATUS_REL), status_2col("어제"))
        with self.assertRaises(ValueError):
            parse_last_run(self.root)


class EdgeTest(ConditionSourceBase):
    """경계 사례: 코드 펜스, 표만 있는 파일, 읽을 수 없는 칸, 칸 수."""

    def test_fenced_example_ignored(self):
        self.write(OVERRIDE_REL, "```\n" + rule_text(1) + "```\n")
        self.write(RULE_REL, rule_text(47))
        self.assertEqual(parse_condition(self.root)[0], 47)

    def test_tilde_fence_ignored(self):
        self.write(OVERRIDE_REL, "~~~md\n" + rule_text(1) + "~~~\n")
        self.write(RULE_REL, rule_text(47))
        self.assertEqual(parse_condition(self.root)[0], 47)

    def test_indented_fence_ignored(self):
        self.write(OVERRIDE_REL, "  ```\n" + rule_text(1) + "  ```\n")
        self.write(RULE_REL, rule_text(47))
        self.assertEqual(parse_condition(self.root)[0], 47)

    def test_row_after_closed_fence_read(self):
        text = "```\n" + rule_text(1) + "```\n\n" + rule_text(24)
        self.write(OVERRIDE_REL, text)
        self.write(RULE_REL, rule_text(47))
        self.assertEqual(parse_condition(self.root)[::2], (24, OVERRIDE_REL))

    def test_other_fence_marker_does_not_close(self):
        text = "~~~\n```\n" + rule_text(1) + "~~~\n"
        self.write(OVERRIDE_REL, text)
        self.write(RULE_REL, rule_text(47))
        self.assertEqual(parse_condition(self.root)[0], 47)

    def test_fenced_status_row_ignored(self):
        self.write(STATUS_REL, "```\n" + status_2col("2026-10-26 09:00:00") + "```\n")
        with self.assertRaises(ValueError):
            parse_last_run(self.root)

    def test_table_without_audit_row_falls_through(self):
        self.write(OVERRIDE_REL, HEAD + row("형식 감사", "push 시"))
        self.write(RULE_REL, rule_text(47))
        self.assertEqual(parse_condition(self.root)[2], RULE_REL)

    def test_unreadable_override_cell_no_fallback(self):
        self.write(OVERRIDE_REL, HEAD + row("에피스테믹 의미 감사", "자주"))
        self.write(RULE_REL, rule_text(47))
        with self.assertRaises(ValueError) as cm:
            parse_condition(self.root)
        self.assertIn(OVERRIDE_REL.as_posix(), str(cm.exception))

    def test_override_without_trailer_no_fallback(self):
        self.write(OVERRIDE_REL, HEAD + row("에피스테믹 의미 감사", "24시간 초과 시"))
        self.write(RULE_REL, rule_text(47))
        with self.assertRaises(ValueError) as cm:
            parse_condition(self.root)
        self.assertIn(OVERRIDE_REL.as_posix(), str(cm.exception))

    def test_status_row_single_cell(self):
        self.write(STATUS_REL, "| 이름 |\n|---|\n| 에피스테믹 의미 감사 |\n")
        with self.assertRaises(ValueError):
            parse_last_run(self.root)

    def test_status_row_empty_time_is_placeholder(self):
        self.write(STATUS_REL, status_2col(""))
        self.assertIsNone(parse_last_run(self.root))


class UndecidableMessageTest(ConditionSourceBase):
    """판정 불가 메시지는 파싱에 실패한 파일을 가리킨다."""

    def run_main(self):
        err = io.StringIO()
        argv = sys.argv
        sys.argv = ["check_semantic_audit.py", str(self.root)]
        try:
            with contextlib.redirect_stderr(err):
                code = main()
        finally:
            sys.argv = argv
        return code, err.getvalue()

    def test_bad_status_names_status(self):
        self.write(str(STATUS_REL), status_2col("어제"))
        self.write(str(RULE_REL), rule_text(47))
        code, err = self.run_main()
        self.assertEqual(code, UNDECIDABLE)
        self.assertIn(STATUS_REL.as_posix() + " could not be parsed", err)

    def test_missing_condition_not_blamed_on_status(self):
        self.write(str(STATUS_REL), status_2col())
        code, err = self.run_main()
        self.assertEqual(code, UNDECIDABLE)
        self.assertIn("condition file could not be parsed", err)
        self.assertNotIn("STATUS could not be parsed", err)


if __name__ == "__main__":
    unittest.main()

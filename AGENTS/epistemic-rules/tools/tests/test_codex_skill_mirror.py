"""Codex 스킬 사본(.agents/skills) 일치 검사 시험."""

import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import audit_structure  # noqa: E402
from _audit_core import VIOLATION  # noqa: E402
from audit_structure import check_codex_skill_mirror, check_descriptors  # noqa: E402

SKILL = b"---\nname: ingest\ndescription: test\n---\n\n# ingest\n\nbody\n"
# 재분석 태그 값. stat 모듈은 이 상수를 윈도우에서만 둔다.
MOUNT_POINT_TAG = getattr(stat, "IO_REPARSE_TAG_MOUNT_POINT", 0xA0000003)
APPEXECLINK_TAG = getattr(stat, "IO_REPARSE_TAG_APPEXECLINK", 0x8000001B)


class CodexSkillMirrorTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name).resolve()

    def write(self, rel, data=SKILL):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)  # 윈도우 줄바꿈 변환을 피하려고 바이트로 쓴다
        return p

    def found(self):
        return sorted((f.severity, f.path) for f in check_codex_skill_mirror(self.root))

    def test_match_passes(self):
        self.write(".claude/skills/ingest/SKILL.md")
        self.write(".agents/skills/ingest/SKILL.md")
        self.assertEqual(self.found(), [])

    def test_missing_copy(self):
        self.write(".claude/skills/ingest/SKILL.md")
        self.write(".claude/skills/pr-create/SKILL.md")
        self.write(".agents/skills/ingest/SKILL.md")
        self.assertEqual(self.found(), [(VIOLATION, ".agents/skills/pr-create/SKILL.md")])

    def test_missing_agents_dir(self):
        self.write(".claude/skills/ingest/SKILL.md")
        self.assertEqual(self.found(), [(VIOLATION, ".agents/skills/ingest/SKILL.md")])

    def test_missing_file_in_copy_dir(self):
        self.write(".claude/skills/ingest/SKILL.md")
        (self.root / ".agents/skills/ingest").mkdir(parents=True)
        self.assertEqual(self.found(), [(VIOLATION, ".agents/skills/ingest/SKILL.md")])

    def test_name_case_differs(self):
        self.write(".claude/skills/ingest/SKILL.md")
        self.write(".agents/skills/Ingest/SKILL.md")
        self.assertEqual(self.found(), [(VIOLATION, ".agents/skills/ingest/SKILL.md")])

    def test_source_name_case_differs_ignored(self):
        self.write(".claude/skills/ingest/skill.md")
        self.assertEqual(self.found(), [])

    def test_content_differs(self):
        self.write(".claude/skills/ingest/SKILL.md")
        self.write(".agents/skills/ingest/SKILL.md", SKILL + b"extra\n")
        found = check_codex_skill_mirror(self.root)
        self.assertEqual([(f.severity, f.path) for f in found], [(VIOLATION, ".agents/skills/ingest/SKILL.md")])
        self.assertIn("다름", found[0].message)

    def test_crlf_only_passes(self):
        self.write(".claude/skills/ingest/SKILL.md")
        self.write(".agents/skills/ingest/SKILL.md", SKILL.replace(b"\n", b"\r\n"))
        self.assertEqual(self.found(), [])

    def test_codex_only_skill_passes(self):
        self.write(".claude/skills/ingest/SKILL.md")
        self.write(".agents/skills/ingest/SKILL.md")
        self.write(".agents/skills/codex-only/SKILL.md", b"other\n")
        self.assertEqual(self.found(), [])

    def test_no_claude_skills_passes(self):
        self.write(".agents/skills/codex-only/SKILL.md")
        self.assertEqual(self.found(), [])
        (self.root / ".claude").mkdir()
        self.assertEqual(self.found(), [])

    def test_skill_md_is_folder(self):
        self.write(".claude/skills/ingest/SKILL.md")
        (self.root / ".agents/skills/ingest/SKILL.md").mkdir(parents=True)
        found = check_codex_skill_mirror(self.root)
        self.assertEqual([(f.severity, f.path) for f in found], [(VIOLATION, ".agents/skills/ingest/SKILL.md")])
        self.assertIn("일반 파일이 아님", found[0].message)

    def test_source_skill_md_is_folder(self):
        (self.root / ".claude/skills/ingest/SKILL.md").mkdir(parents=True)
        self.assertEqual(self.found(), [(VIOLATION, ".claude/skills/ingest/SKILL.md")])

    def test_read_failure_reported(self):
        self.write(".claude/skills/ingest/SKILL.md")
        copy = self.write(".agents/skills/ingest/SKILL.md")
        real = audit_structure.file_digest

        def failing(path):
            if Path(path) == copy:
                raise PermissionError("denied")
            return real(path)

        with mock.patch.object(audit_structure, "file_digest", failing):
            found = check_codex_skill_mirror(self.root)
        self.assertEqual([(f.severity, f.path) for f in found], [(VIOLATION, ".agents/skills/ingest/SKILL.md")])
        self.assertIn("읽기 실패", found[0].message)

    def test_copy_vanishing_after_listing_reported_missing(self):
        self.write(".claude/skills/ingest/SKILL.md")
        copy = self.write(".agents/skills/ingest/SKILL.md")
        real = audit_structure.os.lstat

        def vanished(path, *args, **kwargs):
            if Path(path) == copy:
                raise FileNotFoundError(path)
            return real(path, *args, **kwargs)

        with mock.patch.object(audit_structure.os, "lstat", vanished):
            found = check_codex_skill_mirror(self.root)
        self.assertEqual([(f.severity, f.path) for f in found], [(VIOLATION, ".agents/skills/ingest/SKILL.md")])
        self.assertIn("사본 없음", found[0].message)

    @unittest.skipIf(os.name == "nt" or not hasattr(os, "geteuid") or os.geteuid() == 0,
                     "권한으로 읽기를 막을 수 있는 POSIX 비루트 환경에서만 돈다")
    def test_read_failure_real_permission(self):
        self.write(".claude/skills/ingest/SKILL.md")
        copy = self.write(".agents/skills/ingest/SKILL.md")
        copy.chmod(0)
        self.addCleanup(copy.chmod, 0o644)
        found = check_codex_skill_mirror(self.root)
        self.assertEqual([(f.severity, f.path) for f in found], [(VIOLATION, ".agents/skills/ingest/SKILL.md")])
        self.assertIn("읽기 실패", found[0].message)

    def _symlink(self, link, target, is_dir):
        try:
            os.symlink(target, link, target_is_directory=is_dir)
        except (OSError, NotImplementedError) as e:
            self.skipTest(f"심볼릭 링크를 만들 수 없음 ({type(e).__name__})")

    def test_symlinked_skill_dir_not_followed(self):
        self.write(".claude/skills/ingest/SKILL.md")
        self.write("elsewhere/ingest/SKILL.md")  # 따라갔다면 통과했을 대상
        (self.root / ".agents/skills").mkdir(parents=True)
        self._symlink(self.root / ".agents/skills/ingest", self.root / "elsewhere/ingest", True)
        self.assertEqual(self.found(), [(VIOLATION, ".agents/skills/ingest")])

    def test_symlinked_skill_file_not_followed(self):
        self.write(".claude/skills/ingest/SKILL.md")
        self.write("elsewhere/SKILL.md")
        (self.root / ".agents/skills/ingest").mkdir(parents=True)
        self._symlink(self.root / ".agents/skills/ingest/SKILL.md", self.root / "elsewhere/SKILL.md", False)
        self.assertEqual(self.found(), [(VIOLATION, ".agents/skills/ingest/SKILL.md")])

    def _junction(self, link, target):
        if os.name != "nt":
            self.skipTest("정션은 윈도우에서만 만든다")
        result = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(target)],
            capture_output=True,
        )
        if result.returncode != 0 or not link.exists():
            self.skipTest("정션을 만들 수 없음")
        # 정션은 대상을 지우지 않고 링크만 지운다. 임시 폴더 정리 전에 먼저 뗀다.
        self.addCleanup(lambda: os.rmdir(link) if os.path.lexists(link) else None)

    def test_junction_agents_not_followed(self):
        self.write(".claude/skills/ingest/SKILL.md")
        self.write("elsewhere/skills/ingest/SKILL.md")  # 따라갔다면 통과했을 대상
        self._junction(self.root / ".agents", self.root / "elsewhere")
        self.assertEqual(self.found(), [(VIOLATION, ".agents")])

    def test_junction_skill_dir_not_followed(self):
        self.write(".claude/skills/ingest/SKILL.md")
        self.write("elsewhere/ingest/SKILL.md")
        (self.root / ".agents/skills").mkdir(parents=True)
        self._junction(self.root / ".agents/skills/ingest", self.root / "elsewhere/ingest")
        self.assertEqual(self.found(), [(VIOLATION, ".agents/skills/ingest")])

    def test_junction_claude_skills_not_followed(self):
        self.write("elsewhere/ingest/SKILL.md")
        (self.root / ".claude").mkdir()
        self._junction(self.root / ".claude/skills", self.root / "elsewhere")
        self.assertEqual(self.found(), [(VIOLATION, ".claude/skills")])


class IsLinkTest(unittest.TestCase):
    """링크 판정 분기를 가짜 lstat 결과로 시험한다. 실제 링크를 만들 수 없는 OS에서도 돈다."""

    def test_symlink_mode(self):
        self.assertTrue(audit_structure.is_link_stat(SimpleNamespace(st_mode=stat.S_IFLNK | 0o777)))

    def test_mount_point_reparse(self):
        st = SimpleNamespace(
            st_mode=stat.S_IFDIR, st_file_attributes=stat.FILE_ATTRIBUTE_REPARSE_POINT,
            st_reparse_tag=MOUNT_POINT_TAG)
        self.assertTrue(audit_structure.is_link_stat(st))

    def test_reparse_without_tag(self):
        st = SimpleNamespace(st_mode=stat.S_IFDIR, st_file_attributes=stat.FILE_ATTRIBUTE_REPARSE_POINT)
        self.assertTrue(audit_structure.is_link_stat(st))

    def test_other_reparse_tag(self):
        st = SimpleNamespace(
            st_mode=stat.S_IFREG, st_file_attributes=stat.FILE_ATTRIBUTE_REPARSE_POINT,
            st_reparse_tag=APPEXECLINK_TAG)
        self.assertFalse(audit_structure.is_link_stat(st))

    def test_plain_dir(self):
        self.assertFalse(audit_structure.is_link_stat(SimpleNamespace(st_mode=stat.S_IFDIR)))


class AgentsDirExemptTest(unittest.TestCase):
    def test_agents_dir_needs_no_descriptor(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            (root / "AGENTS.md").write_text("---\ndate created: 2026-01-01\n---\n", encoding="utf-8")
            skill = root / ".agents/skills/ingest/SKILL.md"
            skill.parent.mkdir(parents=True)
            skill.write_bytes(SKILL)
            self.assertEqual(
                [f.path for f in check_descriptors(root) if f.path.startswith(".agents")], [])


if __name__ == "__main__":
    unittest.main()

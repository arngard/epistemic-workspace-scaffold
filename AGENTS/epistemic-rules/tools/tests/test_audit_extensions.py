"""감사 확장 지점(audit_extensions.py) 시험."""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from _audit_core import VIOLATION, WARNING  # noqa: E402
from audit import run_audit  # noqa: E402
import audit_extensions  # noqa: E402
from audit_extensions import (  # noqa: E402
    EXTENSION_DIR_REL, EXTENSION_TIMEOUT, TOOLS_ENV, run_extensions)

EXT_DIR = "AGENTS/audit-checks"


def emit(severity, path, message):
    """발견 하나를 JSON 한 줄로 내는 확장 소스."""
    line = json.dumps({"severity": severity, "path": path, "message": message})
    return "print(%r)\n" % line


EMIT_TOOLS_ENV = (
    "import json, os\n"
    "print(json.dumps({'severity': 'warning', 'path': 'x',\n"
    "                  'message': os.environ['EPISTEMIC_AUDIT_TOOLS']}))\n"
)


class ExtensionTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name).resolve()

    def write(self, rel, text):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        return p

    def ext(self, name, body):
        return self.write(EXT_DIR + "/" + name, body)

    def sev(self):
        return [f.severity for f in run_extensions(self.root)]

    def test_constants(self):
        self.assertEqual(EXTENSION_DIR_REL, "AGENTS/audit-checks")
        self.assertEqual(EXTENSION_TIMEOUT, 300)
        self.assertEqual(TOOLS_ENV, "EPISTEMIC_AUDIT_TOOLS")

    def test_findings(self):
        self.ext("a.py", emit("warning", "s/x.md", "m"))
        got = run_extensions(self.root)
        self.assertEqual([(f.severity, f.category, f.path) for f in got],
                         [(WARNING, "ext:a", "s/x.md")])
        self.assertEqual(got[0].message, "m")

    def test_violation_finding(self):
        self.ext("a.py", emit("violation", "s/x.md", "m"))
        self.assertEqual(self.sev(), [VIOLATION])

    def test_several_lines_in_order(self):
        self.ext("a.py", emit("warning", "p1", "m1")
                 + emit("violation", "p2", "m2"))
        got = run_extensions(self.root)
        self.assertEqual([(f.severity, f.path) for f in got],
                         [(WARNING, "p1"), (VIOLATION, "p2")])

    def test_blank_lines_and_unknown_keys(self):
        self.ext("a.py", "print()\nprint('   ')\n"
                 "print('{\"severity\": \"warning\", \"path\": \"p\","
                 " \"message\": \"m\", \"extra\": 1}')\n")
        self.assertEqual(self.sev(), [WARNING])

    def test_unicode_line_separators_inside_json(self):
        msg = "a\u2028b\x85c\u2029d"
        self.ext("a.py", "import json, sys\n"
                 "d = {'severity': 'warning', 'path': 'p',\n"
                 "     'message': 'a\\u2028b\\x85c\\u2029d'}\n"
                 "line = json.dumps(d, ensure_ascii=False) + '\\n'\n"
                 "sys.stdout.buffer.write(line.encode('utf-8'))\n")
        got = run_extensions(self.root)
        self.assertEqual([f.severity for f in got], [WARNING])
        self.assertEqual(got[0].message, msg)

    def test_crlf_lines(self):
        self.ext("a.py", "import sys\nsys.stdout.write(\n"
                 "  '{\"severity\": \"warning\", \"path\": \"p\","
                 " \"message\": \"m\"}\\r\\n')\n")
        self.assertEqual(self.sev(), [WARNING])

    def test_non_utf8_output_is_replaced(self):
        self.ext("a.py", "import sys\nsys.stdout.buffer.write(\n"
                 "  b'{\"severity\": \"warning\", \"path\": \"p\","
                 " \"message\": \"a\\xffb\"}\\n')\n")
        got = run_extensions(self.root)
        self.assertEqual([f.severity for f in got], [WARNING])
        self.assertEqual(got[0].message, "a\ufffdb")

    def test_non_utf8_stderr_is_replaced(self):
        self.ext("a.py", "import sys\nsys.stderr.buffer.write(b'e\\xff\\n')\n"
                 "sys.exit(1)\n")
        f = run_extensions(self.root)[0]
        self.assertEqual(f.severity, VIOLATION)
        self.assertIn("e\ufffd", f.message)

    def test_unlaunchable_is_violation(self):
        self.ext("a.py", emit("warning", "p", "m"))
        self.ext("b.py", emit("warning", "q", "m"))
        err = OSError("no exec")
        with mock.patch.object(audit_extensions.subprocess, "run",
                               side_effect=err):
            got = run_extensions(self.root)
        self.assertEqual([(f.category, f.severity) for f in got],
                         [("ext:a", VIOLATION), ("ext:b", VIOLATION)])
        self.assertIn("OSError", got[0].message)

    def test_symlinked_file_warns_and_not_run(self):
        target = self.write("outside/x.py", "raise SystemExit(1)\n")
        link = self.root / EXT_DIR / "a.py"
        link.parent.mkdir(parents=True)
        link.symlink_to(target)
        got = run_extensions(self.root)
        self.assertEqual([(f.severity, f.category, f.path) for f in got],
                         [(WARNING, "ext:a", EXT_DIR + "/a.py")])
        self.assertIn("심볼릭 링크", got[0].message)

    def test_symlinked_helper_ignored(self):
        target = self.write("outside/x.py", "raise SystemExit(1)\n")
        link = self.root / EXT_DIR / "_h.py"
        link.parent.mkdir(parents=True)
        link.symlink_to(target)
        self.assertEqual(run_extensions(self.root), [])

    def test_symlinked_folder_warns_and_not_run(self):
        self.write("real/a.py", "raise SystemExit(1)\n")
        link = self.root / EXT_DIR
        link.parent.mkdir(parents=True)
        link.symlink_to(self.root / "real", target_is_directory=True)
        got = run_extensions(self.root)
        self.assertEqual([(f.severity, f.category, f.path) for f in got],
                         [(WARNING, "ext", EXT_DIR)])
        self.assertIn("심볼릭 링크", got[0].message)

    def test_symlink_does_not_stop_others(self):
        target = self.write("outside/x.py", "pass\n")
        link = self.root / EXT_DIR / "a.py"
        link.parent.mkdir(parents=True)
        link.symlink_to(target)
        self.ext("b.py", emit("warning", "p", "m"))
        cats = sorted(f.category for f in run_extensions(self.root))
        self.assertEqual(cats, ["ext:a", "ext:b"])

    def test_empty_path_becomes_dot(self):
        self.ext("a.py", emit("warning", "", "m"))
        self.assertEqual(run_extensions(self.root)[0].path, ".")

    def test_no_output_no_findings(self):
        self.ext("a.py", "pass\n")
        self.assertEqual(run_extensions(self.root), [])

    def test_nonzero_exit(self):
        self.ext("a.py", "import sys\nsys.exit(3)\n")
        self.assertEqual(self.sev(), [VIOLATION])

    def test_failure_names_extension(self):
        self.ext("a.py", "import sys\nsys.exit(3)\n")
        f = run_extensions(self.root)[0]
        self.assertEqual(f.category, "ext:a")
        self.assertEqual(f.path, EXT_DIR + "/a.py")
        self.assertIn("3", f.message)

    def test_stderr_last_line(self):
        self.ext("a.py", "import sys\nsys.stderr.write('first\\nlast one\\n')\n"
                 "sys.exit(1)\n")
        f = run_extensions(self.root)[0]
        self.assertIn("last one", f.message)
        self.assertNotIn("first", f.message)

    def test_stderr_truncated_to_200(self):
        self.ext("a.py", "import sys\nsys.stderr.write('x' * 500 + '\\n')\n"
                 "sys.exit(1)\n")
        msg = run_extensions(self.root)[0].message
        self.assertIn("x" * 200, msg)
        self.assertNotIn("x" * 201, msg)

    def test_exception_is_violation(self):
        self.ext("a.py", "raise RuntimeError('boom')\n")
        f = run_extensions(self.root)[0]
        self.assertEqual(f.severity, VIOLATION)
        self.assertIn("boom", f.message)

    def test_bad_line(self):
        self.ext("a.py", "print('not json')\n")
        self.assertEqual(self.sev(), [VIOLATION])

    def test_bad_lines_variants(self):
        bad = [
            "[1, 2]",
            "5",
            '{"severity": "info", "path": "p", "message": "m"}',
            '{"severity": "warning", "path": "p"}',
            '{"severity": "warning", "message": "m"}',
            '{"path": "p", "message": "m"}',
            '{"severity": "warning", "path": 1, "message": "m"}',
            '{"severity": "warning", "path": "p", "message": 2}',
            '{"severity": ["x"], "path": "p", "message": "m"}',
            '{"severity": {}, "path": "p", "message": "m"}',
            '{"severity": null, "path": "p", "message": "m"}',
            '{"severity": "warning", "path": ["p"], "message": "m"}',
            "[" * 100000 + "]" * 100000,
        ]
        for line in bad:
            with self.subTest(line=line):
                self.ext("a.py", "print(%r)\n" % line)
                self.assertEqual(self.sev(), [VIOLATION])

    def test_bad_line_does_not_stop_next_extension(self):
        self.ext("a.py", 'print(\'{"severity": ["x"]}\')\n')
        self.ext("b.py", emit("warning", "p", "m"))
        got = run_extensions(self.root)
        self.assertEqual([(f.category, f.severity) for f in got],
                         [("ext:a", VIOLATION), ("ext:b", WARNING)])

    def test_bad_line_discards_partial_output(self):
        self.ext("a.py", emit("warning", "p", "m") + "print('oops')\n")
        got = run_extensions(self.root)
        self.assertEqual([f.severity for f in got], [VIOLATION])

    def test_nonzero_exit_discards_partial_output(self):
        self.ext("a.py", emit("warning", "p", "m") + "raise SystemExit(1)\n")
        self.assertEqual(self.sev(), [VIOLATION])

    def test_timeout(self):
        self.ext("a.py", "import time\ntime.sleep(5)\n")
        got = run_extensions(self.root, timeout=1)
        self.assertEqual([f.severity for f in got], [VIOLATION])
        self.assertEqual(got[0].category, "ext:a")

    def test_one_failure_does_not_stop_others(self):
        self.ext("a.py", "raise SystemExit(1)\n")
        self.ext("b.py", emit("warning", "s/x.md", "m"))
        cats = [f.category for f in run_extensions(self.root)]
        self.assertEqual(cats, ["ext:a", "ext:b"])

    def test_name_order(self):
        self.ext("b.py", emit("warning", "pb", "m"))
        self.ext("a.py", emit("warning", "pa", "m"))
        self.assertEqual([f.path for f in run_extensions(self.root)],
                         ["pa", "pb"])

    def test_helper_not_run(self):
        self.ext("_h.py", "raise SystemExit(1)\n")
        self.assertEqual(run_extensions(self.root), [])

    def test_dot_name_not_run(self):
        self.ext(".h.py", "raise SystemExit(1)\n")
        self.assertEqual(run_extensions(self.root), [])

    def triples(self):
        return [(f.severity, f.category, f.path)
                for f in run_extensions(self.root)]

    def test_non_py_warns_and_not_run(self):
        self.ext("a.txt", "raise SystemExit(1)\n")
        self.ext("a.sh", "exit 1\n")
        got = run_extensions(self.root)
        self.assertEqual(self.triples(),
                         [(WARNING, "ext", EXT_DIR + "/a.sh"),
                          (WARNING, "ext", EXT_DIR + "/a.txt")])
        for f in got:
            self.assertIn("실행하지 않음", f.message)
            self.assertIn(".py", f.message)

    def test_uppercase_suffix_warns_and_not_run(self):
        self.ext("check.PY", "raise SystemExit(1)\n")
        self.assertEqual(self.triples(),
                         [(WARNING, "ext", EXT_DIR + "/check.PY")])

    def test_subfolder_warns_and_not_run(self):
        self.ext("sub/a.py", "raise SystemExit(1)\n")
        got = run_extensions(self.root)
        self.assertEqual(self.triples(),
                         [(WARNING, "ext", EXT_DIR + "/sub")])
        self.assertIn("하위 폴더", got[0].message)

    def test_folder_named_like_py_warns(self):
        (self.root / EXT_DIR / "x.py").mkdir(parents=True)
        self.assertEqual(self.triples(),
                         [(WARNING, "ext", EXT_DIR + "/x.py")])

    def test_helper_names_silent(self):
        self.ext("_lib/a.py", "raise SystemExit(1)\n")
        self.ext(".cache/a.py", "raise SystemExit(1)\n")
        self.ext("_notes.txt", "x\n")
        self.ext(".DS_Store", "x\n")
        self.assertEqual(run_extensions(self.root), [])

    def test_skipped_entries_do_not_stop_extensions(self):
        self.ext("notes.txt", "x\n")
        self.ext("a.py", emit("warning", "p", "m"))
        self.assertEqual(sorted(f.category for f in run_extensions(self.root)),
                         ["ext", "ext:a"])

    def test_only_root_folder(self):
        self.write("s/AGENTS/audit-checks/a.py", "raise SystemExit(1)\n")
        self.assertEqual(run_extensions(self.root), [])

    def test_tools_env(self):
        self.ext("a.py", EMIT_TOOLS_ENV)
        msg = run_extensions(self.root)[0].message
        self.assertTrue(Path(msg).joinpath("audit.py").is_file())

    def test_args_and_cwd(self):
        self.ext("a.py", "import json, os, sys\n"
                 "print(json.dumps({'severity': 'warning', 'path': 'x',\n"
                 "  'message': sys.argv[1] + '|' + os.getcwd()}))\n")
        msg = run_extensions(self.root)[0].message
        arg, cwd = msg.split("|")
        self.assertEqual(Path(arg).resolve(), self.root)
        self.assertEqual(Path(cwd).resolve(), self.root)

    def test_no_bytecode_written(self):
        self.ext("a.py", "import _helper_mod\n")
        self.write(EXT_DIR + "/_helper_mod.py", "X = 1\n")
        run_extensions(self.root)
        self.assertEqual(list(self.root.rglob("__pycache__")), [])

    def test_absent_folder(self):
        self.assertEqual(run_extensions(self.root), [])

    def test_empty_folder(self):
        (self.root / EXT_DIR).mkdir(parents=True)
        self.assertEqual(run_extensions(self.root), [])


class RunAuditIntegrationTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name).resolve()

    def write(self, rel, text):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")

    def ext_findings(self):
        return [f for f in run_audit(self.root)
                if f.category.startswith("ext:")]

    def test_run_audit_includes_extension(self):
        self.write(EXT_DIR + "/a.py", emit("warning", "x.md", "m"))
        got = self.ext_findings()
        self.assertEqual([(f.severity, f.category, f.path) for f in got],
                         [(WARNING, "ext:a", "x.md")])

    def test_run_audit_includes_extension_failure(self):
        self.write(EXT_DIR + "/a.py", "raise SystemExit(2)\n")
        self.assertEqual([f.severity for f in self.ext_findings()],
                         [VIOLATION])

    def test_run_audit_without_folder(self):
        self.assertEqual(self.ext_findings(), [])

    def test_extensions_run_after_builtin_checks(self):
        self.write("n.md", "front matter 없음\n")
        self.write(EXT_DIR + "/a.py", emit("warning", "x.md", "m"))
        cats = [f.category for f in run_audit(self.root)]
        self.assertGreater(len(cats), 1)
        self.assertEqual(cats[-1], "ext:a")


if __name__ == "__main__":
    unittest.main()

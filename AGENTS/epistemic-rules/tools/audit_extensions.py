"""감사 확장 지점: 루트 AGENTS/audit-checks/의 확장 검사를 실행한다.

확장은 저장소 루트의 AGENTS/audit-checks/ 바로 아래에 둔 *.py 파일이다.
이름이 _나 .으로 시작하는 파일은 도우미로 보고 실행하지 않으며, 하위 폴더는
보지 않는다. 심볼릭 링크인 확장 파일이나 확장 폴더는 실행하지 않고 경고 1건으로
알린다. 계약은 프로세스 경계의 텍스트 형식이다.

- 실행: [sys.executable, "-B", <파일>, <루트>]. 작업 폴더는 루트이고 환경
  변수 EPISTEMIC_AUDIT_TOOLS에 이 도구 폴더를 넘긴다.
- 출력: 표준 출력에 발견 하나를 한 줄의 JSON 객체
  {"severity": "violation" 또는 "warning", "path": 루트 상대 경로,
  "message": 설명}로 내고 종료 코드 0으로 끝난다. 빈 줄과 모르는 키는 무시한다.
- 범주는 ext:<파일 이름 줄기>이고 path가 빈 문자열이면 .으로 둔다.
- 실패 격리: 종료 코드가 0이 아니거나, 형식이 어긋난 줄이 있거나, 제한 시간
  안에 끝나지 않으면 그 확장에 대해 위반 1건만 낸다(그 확장이 이미 낸 줄은
  버린다). 표준 오류의 마지막 줄 200자 이내를 붙이고 다음 확장으로 넘어간다.

확장 코드는 감사를 돌릴 때 실행되므로 읽기만 해야 한다. 상류 내부 모듈(Finding
등)은 계약이 아니며 확장은 이 모듈을 가져오지 않는다.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

from _audit_core import VIOLATION, WARNING, Finding

EXTENSION_DIR_REL = "AGENTS/audit-checks"
# 확장 하나에 주는 제한 시간(초).
EXTENSION_TIMEOUT = 300
TOOLS_ENV = "EPISTEMIC_AUDIT_TOOLS"
# 표준 오류에서 붙이는 마지막 줄의 최대 길이.
STDERR_LIMIT = 200

_SEVERITIES = {"violation": VIOLATION, "warning": WARNING}


class _BadOutput(Exception):
    """확장의 표준 출력 줄이 계약 형식에 맞지 않음."""


def _extension_files(root: Path) -> "tuple[list[Path], list[Finding]]":
    """실행할 확장 파일(이름 순)과 실행하지 않는 심볼릭 링크의 경고를 돌려준다."""
    folder = root / EXTENSION_DIR_REL
    if folder.is_symlink():
        return [], [Finding(
            WARNING, "ext", EXTENSION_DIR_REL,
            "확장 폴더가 심볼릭 링크라 실행하지 않음",
        )]
    if not folder.is_dir():
        return [], []
    files: list[Path] = []
    warnings: list[Finding] = []
    for p in sorted(folder.iterdir(), key=lambda q: q.name):
        if p.suffix != ".py" or p.name.startswith(("_", ".")):
            continue
        if p.is_symlink():
            warnings.append(Finding(
                WARNING, f"ext:{p.stem}", f"{EXTENSION_DIR_REL}/{p.name}",
                "확장 파일이 심볼릭 링크라 실행하지 않음",
            ))
        elif p.is_file():
            files.append(p)
    return files, warnings


def _parse_line(number: int, line: str) -> dict:
    """한 줄을 JSON 객체로 읽는다. 어긋나면 _BadOutput."""
    try:
        item = json.loads(line)
    except (ValueError, TypeError, RecursionError):
        raise _BadOutput(f"{number}번째 줄이 JSON이 아님")
    if not isinstance(item, dict):
        raise _BadOutput(f"{number}번째 줄이 JSON 객체가 아님")
    return item


def _parse_output(stem: str, stdout: str) -> list[Finding]:
    """표준 출력의 JSON 줄을 발견으로 바꾼다. 어긋난 줄이 있으면 _BadOutput.

    줄은 \\n으로만 나눈다(다른 줄 경계 문자는 JSON 문자열 안에 올 수 있다).
    """
    out: list[Finding] = []
    for number, line in enumerate(stdout.split("\n"), 1):
        line = line.rstrip("\r")
        if not line.strip():
            continue
        item = _parse_line(number, line)
        severity = item.get("severity")
        path = item.get("path")
        message = item.get("message")
        if not isinstance(severity, str) or severity not in _SEVERITIES:
            raise _BadOutput(f"{number}번째 줄의 severity가 violation이나 warning이 아님")
        if not isinstance(path, str) or not isinstance(message, str):
            raise _BadOutput(f"{number}번째 줄의 path나 message가 문자열이 아님")
        out.append(Finding(_SEVERITIES[severity], f"ext:{stem}", path or ".", message))
    return out


def _stderr_tail(stderr: str) -> str:
    """표준 오류의 마지막 비지 않은 줄을 200자 이내로 돌려준다."""
    lines = [ln.strip() for ln in stderr.splitlines() if ln.strip()]
    return lines[-1][:STDERR_LIMIT] if lines else ""


def _failure(stem: str, rel: str, reason: str, stderr: str = "") -> Finding:
    message = f"확장 검사 실패: {reason}"
    tail = _stderr_tail(stderr)
    if tail:
        message += f" (표준 오류 마지막 줄: {tail})"
    return Finding(VIOLATION, f"ext:{stem}", rel, message)


def _run_one(root: Path, path: Path, timeout: int) -> list[Finding]:
    stem = path.stem
    rel = f"{EXTENSION_DIR_REL}/{path.name}"
    env = dict(os.environ)
    env[TOOLS_ENV] = str(Path(__file__).resolve().parent)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    try:
        proc = subprocess.run(
            [sys.executable, "-B", str(path), str(root)],
            cwd=str(root), env=env, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as e:
        stderr = (e.stderr or b"").decode("utf-8", errors="replace")
        return [_failure(stem, rel, f"{timeout}초 안에 끝나지 않음", stderr)]
    except OSError as e:
        return [_failure(stem, rel, f"실행할 수 없음 ({e.__class__.__name__})")]
    stderr = proc.stderr.decode("utf-8", errors="replace")
    if proc.returncode != 0:
        return [_failure(stem, rel, f"종료 코드 {proc.returncode}", stderr)]
    try:
        return _parse_output(stem, proc.stdout.decode("utf-8", errors="replace"))
    except _BadOutput as e:
        return [_failure(stem, rel, f"출력 형식 오류, {e}", stderr)]


def run_extensions(root: Path, timeout: int = EXTENSION_TIMEOUT) -> list[Finding]:
    """루트의 확장 검사를 이름 순으로 실행해 발견을 모은다.

    폴더가 없으면 빈 목록이다. 한 확장의 실패는 그 확장의 위반 1건으로
    격리되고 다음 확장이 계속 실행된다.
    """
    files, findings = _extension_files(root)
    for path in files:
        findings += _run_one(root, path, timeout)
    return findings

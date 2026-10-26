#!/usr/bin/env python3
"""의미 감사 트리거 판정 (git 의존, audit.py와 별개).

STATUS 레지스트리의 마지막 수행 시각과 git 이력을 대조해 트리거 조건 충족 여부를
판정한다. 판정 비용을 없애는 보조 도구다 - 감사를 수행하지도, 강제하지도
않는다. 어겼을 때 아무 신호가 없어 조건 충족을 놓치는 것을 막는 것이 목적이다.

audit.py는 git에 의존하지 않는다는 원칙을 지키려고 별도 스크립트로 둔다
(see: AGENTS/epistemic-rules/tools.md "기계 감사 스크립트").

임계 시간과 trailer 문구는 스크립트에 하드코딩하지 않고 다음 순서로 처음 찾은
것에서 읽는다 - 인스턴스가 주기를 조정하면 스크립트가 따라간다
(ref: AGENTS/epistemic-rules/agent-roles/epistemic-auditor.md "호출 시점").
    1. worklog/AGENTS.md 표의 의미 감사 행 (자손 덮어쓰기)
    2. 칸이 셋 이상인 옛 형식 STATUS 행의 셋째 칸 (아직 옮기지 않은 자식)
    3. worklog/AGENTS/epistemic-rules/status-registry.md 표의 의미 감사 행 (상류 규칙)
마지막 수행 시각은 STATUS 행의 둘째 칸이다.

시각 비교는 KST(UTC+9) 고정으로 한다. STATUS 시각이 KST 표기이므로 실행
머신의 로컬 시간대에 의존하지 않는다.

사용법:
    python3 AGENTS/epistemic-rules/tools/check_semantic_audit.py [워크스페이스 루트]
    (윈도우에서는 python 또는 py 런처로 동일하게 실행)

종료 코드:
    0  미충족 - 지금 감사할 필요 없음
    1  충족 - 착수 전 감사 필요
    2  판정 불가 - STATUS 파싱 실패, git 부재 등. 수동 판정으로 넘긴다
"""

import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

STATUS_REL = Path("worklog/STATUS.md")
OVERRIDE_REL = Path("worklog/AGENTS.md")
RULE_REL = Path("worklog/AGENTS/epistemic-rules/status-registry.md")
# 의미 감사 행은 이름 칸에 이 문구를 담은 첫 행이다. 이름 칸만 보므로 다른 행의
# 주기 조건 서술에 같은 문구가 있어도 오인하지 않는다.
AUDIT_ROW_KEY = "의미 감사"
KST = timezone(timedelta(hours=9))
TIMESTAMP_RE = re.compile(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}")
THRESHOLD_RE = re.compile(r"(\d+)\s*시간")
TRAILER_RE = re.compile(r"`([^`]+)`")
# 미수행 placeholder. 이 값이면 기준점이 없으므로 그 자체로 충족이다.
PLACEHOLDERS = {"(아직 없음)", "-", ""}

UNMET, MET, UNDECIDABLE = 0, 1, 2


def git(root: Path, *args: str) -> tuple[int, str]:
    """git 호출. 반환은 (종료 코드, stdout 문자열)."""
    try:
        proc = subprocess.run(
            ["git", *args], cwd=str(root), capture_output=True,
            text=True, encoding="utf-8", errors="replace",
        )
    except OSError as exc:  # git 미설치 등
        return 127, str(exc)
    return proc.returncode, proc.stdout.strip()


def find_row(path: Path) -> "list[str] | None":
    """이름 칸에 AUDIT_ROW_KEY를 담은 첫 표 행의 칸 목록(앞뒤 공백 제거). 없으면 None."""
    if not path.is_file():
        return None
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.lstrip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if AUDIT_ROW_KEY in cells[0]:
            return cells
    return None


def parse_last_run(root: Path) -> "datetime | None":
    """STATUS 행의 둘째 칸(마지막 수행). placeholder면 None.

    행이 없거나 시각을 읽을 수 없으면 ValueError - 침묵 실패를 만들지 않는다.
    """
    cells = find_row(root / STATUS_REL)
    if cells is None:
        raise ValueError(f'STATUS에 "{AUDIT_ROW_KEY}"를 담은 레지스트리 행 없음 - {STATUS_REL}')
    if len(cells) < 2:
        raise ValueError(f"레지스트리 행의 칸이 2개 미만 - {cells}")
    stamp = cells[1]
    bare = stamp.replace(" KST", "").strip()
    if bare in PLACEHOLDERS:
        return None
    if TIMESTAMP_RE.fullmatch(bare):
        return datetime.strptime(bare, "%Y-%m-%d %H:%M:%S").replace(tzinfo=KST)
    raise ValueError(f"마지막 수행 시각을 읽을 수 없음 - {stamp} (읽은 행: {cells[0]})")


def parse_condition(root: Path) -> "tuple[int, str, Path]":
    """(임계 시간, trailer, 읽은 파일의 루트 상대 경로). 출처 순서는 모듈 docstring 참조."""
    candidates = []
    for rel, need_three in ((OVERRIDE_REL, False), (STATUS_REL, True), (RULE_REL, False)):
        cells = find_row(root / rel)
        if cells is None or (need_three and len(cells) < 3):
            continue
        candidates.append((rel, cells))
    if not candidates:
        raise ValueError(f'주기 조건을 담은 "{AUDIT_ROW_KEY}" 행 없음 - {OVERRIDE_REL}, {STATUS_REL}, {RULE_REL}')
    rel, cells = candidates[0]
    cell = cells[-1] if rel != STATUS_REL else cells[2]
    threshold = THRESHOLD_RE.search(cell)
    if not threshold:
        raise ValueError(f"{rel}에서 임계 시간을 읽을 수 없음 - {cell}")
    trailer = TRAILER_RE.search(cell)
    if not trailer:
        raise ValueError(f"{rel}에서 trailer 문구를 읽을 수 없음 - {cell}")
    return int(threshold.group(1)), trailer.group(1), rel


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()
    if not root.is_dir():
        print(f"Error: not a directory. 디렉토리가 아님 - {root}", file=sys.stderr)
        return UNDECIDABLE

    # 실패한 파일을 메시지에 밝힌다. 조건 쪽 예외는 읽은 파일 경로를 담는다.
    try:
        last = parse_last_run(root)
    except ValueError as exc:
        print(f"Undecidable: {STATUS_REL.as_posix()} could not be parsed. 판정 불가: {exc}. 수동 판정 필요.", file=sys.stderr)
        return UNDECIDABLE
    try:
        threshold, trailer, source = parse_condition(root)
    except ValueError as exc:
        print(f"Undecidable: condition file could not be parsed. 판정 불가: {exc}. 수동 판정 필요.", file=sys.stderr)
        return UNDECIDABLE

    code, _ = git(root, "rev-parse", "--git-dir")
    if code != 0:
        print("Undecidable: git is unavailable. 판정 불가: git 레포가 아니거나 git을 실행할 수 없음. 수동 판정 필요.", file=sys.stderr)
        return UNDECIDABLE

    if last is None:
        print(f"충족: 마지막 수행이 미수행 placeholder다 (최초 1회). (조건 출처: {source.as_posix()})")
        return MET

    # trailer는 줄 전체로 앵커해 찾는다 - trailer 문구를 본문에서 언급하기만 한
    # 커밋(예: 트리거 규약을 정의하는 커밋)을 기준점으로 오인하지 않는다.
    # --first-parent로 본 레포 자신의 main 라인만 본다 - upstream 머지로 흘러든
    # 상류의 클린 커밋은 이 인스턴스의 감사 기준점이 아니다.
    _, clean = git(
        root, "log", "-1", "--first-parent", f"--grep=^{trailer}$", "--format=%H",
    )
    if not clean:
        print(f"충족: 본 레포의 클린 커밋(trailer {trailer})이 이력에 없다 (최초 1회). (조건 출처: {source.as_posix()})")
        return MET

    elapsed = (datetime.now(timezone.utc) - last).total_seconds() / 3600
    _, since = git(root, "rev-list", f"{clean}..HEAD", "--count")
    new_commits = int(since) if since.isdigit() else 0
    short = clean[:7]
    if new_commits == 0:
        print(f"미충족: 클린 커밋 {short} 이후 새 커밋이 없다. (조건 출처: {source.as_posix()})")
        return UNMET
    if elapsed <= threshold:
        print(
            f"미충족: 새 커밋 {new_commits}개가 있으나 마지막 수행 후 "
            f"{elapsed:.1f}시간으로 임계 {threshold}시간 이내다. (조건 출처: {source.as_posix()})"
        )
        return UNMET
    print(
        f"충족: 클린 커밋 {short} 이후 새 커밋 {new_commits}개, "
        f"마지막 수행 후 {elapsed:.1f}시간으로 임계 {threshold}시간을 초과했다. (조건 출처: {source.as_posix()})"
    )
    return MET


if __name__ == "__main__":
    sys.exit(main())

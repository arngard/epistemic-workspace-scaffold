#!/usr/bin/env python3
"""의미 감사 트리거 판정 (git 의존, audit.py와 별개).

STATUS 레지스트리의 의미 감사 행과 git 이력을 대조해 트리거 조건 충족 여부를
판정한다. 판정 비용을 없애는 보조 도구다 - 감사를 수행하지도, 강제하지도
않는다. 어겼을 때 아무 신호가 없어 조건 충족을 놓치는 것을 막는 것이 목적이다.

audit.py는 git에 의존하지 않는다는 원칙을 지키려고 별도 스크립트로 둔다
(cf. AGENTS/tool-environment.md "기계 감사 스크립트").

임계 시간과 trailer 문구는 STATUS 레지스트리의 주기/트리거 셀에서 읽는다.
그 셀이 임계 조건의 SSOT이므로 스크립트에 하드코딩하지 않는다 - 인스턴스가
주기를 조정하면 스크립트가 따라간다 (cf. AGENTS/agent-roles.md "호출 시점").

시각 비교는 KST(UTC+9) 고정으로 한다. STATUS 시각이 KST 표기이므로 실행
머신의 로컬 시간대에 의존하지 않는다.

사용법:
    python3 AGENTS/tools/check_semantic_audit.py [워크스페이스 루트]
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

STATUS_REL = Path("_docs/_worklog/STATUS.md")
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


def parse_status(root: Path) -> tuple["datetime | None", int, str]:
    """STATUS의 의미 감사 행에서 (마지막 수행, 임계 시간, trailer)를 뽑는다.

    파싱 실패는 ValueError로 올린다 - 침묵 실패를 만들지 않는다.
    """
    path = root / STATUS_REL
    if not path.is_file():
        raise ValueError(f"STATUS 파일 없음 - {STATUS_REL}")
    row = next(
        (
            line for line in path.read_text(encoding="utf-8", errors="replace").splitlines()
            if line.lstrip().startswith("|") and AUDIT_ROW_KEY in line
        ),
        None,
    )
    if row is None:
        raise ValueError(f'"{AUDIT_ROW_KEY}"를 담은 레지스트리 행 없음')
    cells = [c.strip() for c in row.strip().strip("|").split("|")]
    if len(cells) < 3:
        raise ValueError(f"레지스트리 행의 셀이 3개 미만 - {row.strip()}")
    stamp, trigger = cells[1], cells[2]
    bare = stamp.replace(" KST", "").strip()
    if bare in PLACEHOLDERS:
        last = None
    elif TIMESTAMP_RE.fullmatch(bare):
        last = datetime.strptime(bare, "%Y-%m-%d %H:%M:%S").replace(tzinfo=KST)
    else:
        raise ValueError(f"마지막 수행 시각을 읽을 수 없음 - {stamp}")
    threshold = THRESHOLD_RE.search(trigger)
    if not threshold:
        raise ValueError(f"주기/트리거 셀에서 임계 시간을 읽을 수 없음 - {trigger}")
    trailer = TRAILER_RE.search(trigger)
    if not trailer:
        raise ValueError(f"주기/트리거 셀에서 trailer 문구를 읽을 수 없음 - {trigger}")
    return last, int(threshold.group(1)), trailer.group(1)


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()
    if not root.is_dir():
        print(f"오류: 디렉토리가 아님 - {root}", file=sys.stderr)
        return UNDECIDABLE

    try:
        last, threshold, trailer = parse_status(root)
    except ValueError as exc:
        print(f"판정 불가: {exc}. 수동 판정 필요.", file=sys.stderr)
        return UNDECIDABLE

    code, _ = git(root, "rev-parse", "--git-dir")
    if code != 0:
        print("판정 불가: git 레포가 아니거나 git을 실행할 수 없음. 수동 판정 필요.", file=sys.stderr)
        return UNDECIDABLE

    if last is None:
        print("충족: 마지막 수행이 미수행 placeholder다 (최초 1회).")
        return MET

    # trailer는 줄 전체로 앵커해 찾는다 - trailer 문구를 본문에서 언급하기만 한
    # 커밋(예: 트리거 규약을 정의하는 커밋)을 기준점으로 오인하지 않는다.
    # --first-parent로 본 레포 자신의 main 라인만 본다 - upstream 머지로 흘러든
    # 상류의 클린 커밋은 이 인스턴스의 감사 기준점이 아니다.
    _, clean = git(
        root, "log", "-1", "--first-parent", f"--grep=^{trailer}$", "--format=%H",
    )
    if not clean:
        print(f"충족: 본 레포의 클린 커밋(trailer {trailer})이 이력에 없다 (최초 1회).")
        return MET

    elapsed = (datetime.now(timezone.utc) - last).total_seconds() / 3600
    _, since = git(root, "rev-list", f"{clean}..HEAD", "--count")
    new_commits = int(since) if since.isdigit() else 0
    short = clean[:7]
    if new_commits == 0:
        print(f"미충족: 클린 커밋 {short} 이후 새 커밋이 없다.")
        return UNMET
    if elapsed <= threshold:
        print(
            f"미충족: 새 커밋 {new_commits}개가 있으나 마지막 수행 후 "
            f"{elapsed:.1f}시간으로 임계 {threshold}시간 이내다."
        )
        return UNMET
    print(
        f"충족: 클린 커밋 {short} 이후 새 커밋 {new_commits}개, "
        f"마지막 수행 후 {elapsed:.1f}시간으로 임계 {threshold}시간을 초과했다."
    )
    return MET


if __name__ == "__main__":
    sys.exit(main())

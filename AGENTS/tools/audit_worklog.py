"""워크로그(STATUS, TASK_TREE) 검사.

공용 인프라는 _audit_core, 오케스트레이션은 audit.py.
"""
import re
import urllib.parse
from pathlib import Path

from _audit_core import *  # noqa: F401,F403 - Finding, 상수, 공용 헬퍼


def check_status_registry(root: Path) -> list[Finding]:
    """STATUS.md가 레지스트리 표 외 서술을 누적하는지 검출 (proposal 2).

    STATUS는 상태 레지스트리다. front matter, 제목, 인용 블록(> 안내),
    마크다운 표만 허용하고 일반 서술 문단이 있으면 위반. 첫 1건에서 멈추지 않고
    모든 표 외 서술 줄을 보고한다. 코드 펜스 안 예시는 다른 검사와 같은 기준으로
    제외한다.
    """
    out: list[Finding] = []
    status = root / WORKLOG_DIR / "STATUS.md"
    if not status.exists():
        return out
    rel = str(status.relative_to(root))
    body = re.sub(r"```.*?```", "", body_of(status), flags=re.DOTALL)
    for raw_line in body.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("#"):       # 제목
            continue
        if line.startswith(">"):       # 인용 블록(갱신 규칙 안내)
            continue
        if line.startswith("|"):       # 표
            continue
        out.append(Finding(
            VIOLATION, "status", rel,
            f'레지스트리 표 외 서술 발견 - "{line[:40]}". '
            "STATUS는 상태 레지스트리이며 진행 서사를 두지 않는다",
        ))
    return out


def check_task_tree_attrs(root: Path) -> list[Finding]:
    """TASK_TREE.md 속성 노드(체크박스 없는 불릿)의 표준 키 위반 검출 (proposal 2).

    작업 노드는 `- [ ]`/`[/]`/`[x]`/`[-]` 형태. 속성 노드는 체크박스 없는
    불릿이며 표준 키(설명, 상태 상세, 외부 참조, 브랜치)로 시작해야 한다.
    프리앰블(인용 블록, 코드 블록)은 검사에서 제외.
    """
    out: list[Finding] = []
    tree = root / WORKLOG_DIR / "TASK_TREE.md"
    if not tree.exists():
        return out
    rel = str(tree.relative_to(root))
    body = body_of(tree)
    body = re.sub(r"```.*?```", "", body, flags=re.DOTALL)
    checkbox_re = re.compile(r"^\s*-\s*\[[ /x\-]\]\s")
    bullet_re = re.compile(r"^(\s*)-\s+(?!\[[ /x\-]\])(.*)$")
    for raw_line in body.splitlines():
        if raw_line.lstrip().startswith(">"):   # 프리앰블 인용 블록
            continue
        if checkbox_re.match(raw_line):         # 작업 노드
            continue
        m = bullet_re.match(raw_line)
        if not m:
            continue
        content = m.group(2).strip()
        if content.startswith("cf.") or content.startswith("ref."):
            continue
        # 표준 키로 시작하는지. 키 뒤에 구분자(콜론/공백)나 끝이 와야 한다 -
        # 단순 startswith면 "설명서" 같은 접두 오검출이 생긴다 (제노 1.5).
        if any(
            content == k or (content.startswith(k) and content[len(k):len(k) + 1] in (":", " ", "\t"))
            for k in TASK_TREE_ATTR_KEYS
        ):
            continue
        out.append(Finding(
            WARNING, "task-tree", rel,
            f'속성 노드 비표준 키 - "{content[:40]}". 표준 키: {", ".join(TASK_TREE_ATTR_KEYS)}',
        ))
    return out


def check_task_tree_completed_branch(root: Path) -> list[Finding]:
    """완료(`[x]`/`[-]`) 노드에 브랜치 속성이 잔존하는지 검출 (경고).

    완료 시 브랜치 속성은 제거한다 (TASK_TREE 관리 규칙). 잔존하면 끊김
    재진입이 죽은 포인터를 따라갈 수 있다.
    """
    out: list[Finding] = []
    tree = root / WORKLOG_DIR / "TASK_TREE.md"
    if not tree.exists():
        return out
    rel = str(tree.relative_to(root))
    body = re.sub(r"```.*?```", "", body_of(tree), flags=re.DOTALL)
    checkbox_re = re.compile(r"^(\s*)-\s*\[([ /x\-])\]\s")
    bullet_re = re.compile(r"^(\s*)-\s+(?!\[[ /x\-]\])(.*)$")
    stack: list[tuple[int, str]] = []  # (들여쓰기 폭, 상태 문자)
    for raw_line in body.splitlines():
        if raw_line.lstrip().startswith(">"):
            continue
        m = checkbox_re.match(raw_line)
        if m:
            indent = len(m.group(1))
            while stack and stack[-1][0] >= indent:
                stack.pop()
            stack.append((indent, m.group(2)))
            continue
        b = bullet_re.match(raw_line)
        if not b:
            continue
        indent = len(b.group(1))
        content = b.group(2).strip()
        ancestor = next((s for i, s in reversed(stack) if i < indent), None)
        if ancestor in ("x", "-") and content.startswith("브랜치"):
            out.append(Finding(
                WARNING, "task-tree", rel,
                f'완료 노드에 브랜치 속성 잔존 - "{content[:40]}". 완료 시 브랜치 속성은 제거한다',
            ))
    return out


def check_status_schema(root: Path) -> list[Finding]:
    """STATUS.md 레지스트리 표의 스키마와 시각 표기 형식 검사 (경고)."""
    out: list[Finding] = []
    status = root / WORKLOG_DIR / "STATUS.md"
    if not status.exists():
        return out
    rel = str(status.relative_to(root))
    header_seen = False
    for raw_line in body_of(status).splitlines():
        line = raw_line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if all(re.fullmatch(r":?-+:?", c) for c in cells):  # 구분선
            continue
        if not header_seen:
            header_seen = True
            if cells != STATUS_HEADER_CELLS:
                out.append(Finding(
                    WARNING, "status", rel,
                    f"레지스트리 표 헤더가 표준 스키마와 다름 - 기대 {STATUS_HEADER_CELLS}, 실제 {cells}",
                ))
            continue
        if len(cells) != len(STATUS_HEADER_CELLS):
            out.append(Finding(WARNING, "status", rel, f'레지스트리 행 열 수 불일치 - "{line[:40]}"'))
            continue
        value = cells[1]
        if value in STATUS_PLACEHOLDER or STATUS_TIMESTAMP_RE.match(value):
            continue
        out.append(Finding(
            WARNING, "status", rel,
            f'마지막 수행 시각 형식 위반 - "{value}". yyyy-MM-dd HH:mm:ss (KST 기준, 존 표기 생략)',
        ))
    return out

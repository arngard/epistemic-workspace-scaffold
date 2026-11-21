#!/usr/bin/env python3
"""세션 시작 요약 (git 의존, 읽기 전용).

session-boundaries.md "세션 시작" 1-4단계 가운데 판단이 필요 없는 부분을 모아
짧은 요약 하나로 낸다. 모델이 명령을 하나씩 돌려 출력을 컨텍스트에 쌓는 대신
이 요약만 읽게 하려는 것이다. 규범 내용은 옮겨 적지 않고 머리말에서 그 절의
경로만 가리킨다 - 절차의 SSOT는 규범 문서다.

모으는 것:
    - 열린 워크트리
    - main에 머지되지 않은 로컬과 origin 브랜치, 각 브랜치가 TASK_TREE에 더한
      진행 노드(`- [/]` 줄)
    - main의 최근 머지 N건(기본 5)의 제목과 바뀐 `.md` 문서, 문서마다 front matter의
      description(없으면 첫 H1 제목) 한 줄
    - 형식 감사(audit.py)의 위반 줄, reference/INDEX.yaml에 대한 경고 줄, 위반과 경고 건수
    - 의미 감사 트리거 판정(check_semantic_audit.py)의 판정 문장
    - reference/INDEX.md에서 상태가 `미등록`이나 `처리 대기`인 항목

`git fetch --prune origin`은 머지 전 브랜치 목록을 원격과 맞추려고 먼저 한 번
시도한다. origin이 없거나 제한 시간 안에 끝나지 않으면 건너뛰고 그 사실을 적는다.

--hook-json을 주면 같은 요약을 Claude Code SessionStart 훅의 JSON 출력
(hookSpecificOutput.additionalContext)으로 감싸 ASCII 이스케이프로 낸다. 평문 stdout보다
주입 경로가 문서에 분명하고, 셸과 콘솔의 인코딩에 영향받지 않는다.

출력은 MAX_CHARS 안으로 자른다. Claude Code 훅이 주입하는 텍스트의 상한
(10,000자)을 넘으면 요약이 파일로 빠져 모델이 보지 못하기 때문이다.

사용법:
    python3 AGENTS/epistemic-rules/tools/session_brief.py [워크스페이스 루트]
        [--merges N] [--no-fetch] [--no-audit] [--hook-json]
    (윈도우에서는 python 또는 py 런처로 동일하게 실행)

종료 코드:
    0  요약을 냈다. 감사 위반, 의미 감사 충족, 일부 수집 실패도 요약 안에 적고 0으로
       끝난다 - 세션 시작 훅이 세션을 막지 않게 하려는 것이다
    2  사용법 오류(루트가 디렉토리가 아님)
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

MARKER = "[session-brief]"
MAX_CHARS = 9000
SUMMARY_MAX = 160
MAX_VIOLATION_LINES = 20
FETCH_TIMEOUT = 15
TOOL_TIMEOUT = 180

TOOLS_DIR = Path(__file__).resolve().parent
RULE_DOC = TOOLS_DIR.parent / "session-boundaries.md"
TASK_TREE_REL = "worklog/TASK_TREE.md"
REFERENCE_INDEX_REL = Path("reference/INDEX.md")
REFERENCE_YAML = "reference/INDEX.yaml"
PENDING_STATES = ("미등록", "처리 대기")
STATE_RE = re.compile(r"`([^`]+)`")
IN_PROGRESS_PREFIX = "- [/]"


def git(root: Path, *args: str, timeout: "float | None" = None) -> "tuple[int, str]":
    """git을 utf-8로 돌려 (종료 코드, stdout)을 낸다. git이 없거나 시간이 넘으면 (-1, "")."""
    try:
        proc = subprocess.run(
            ["git", "-c", "core.quotePath=false", *args],
            cwd=root, capture_output=True, encoding="utf-8", errors="replace",
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired):
        return -1, ""
    return proc.returncode, proc.stdout


def doc_summary(path: Path) -> "str | None":
    """문서 front matter의 description, 없으면 첫 H1 제목. 파일이 없으면 None."""
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None
    summary = ""
    body_start = 0
    if lines and lines[0].strip() == "---":
        for i, line in enumerate(lines[1:], start=1):
            if line.strip() == "---":
                body_start = i + 1
                break
            if line.startswith("description:"):
                summary = line[len("description:"):].strip().strip("\"'")
    if not summary:
        for line in lines[body_start:]:
            if line.startswith("# "):
                summary = line[2:].strip()
                break
    if len(summary) > SUMMARY_MAX:
        summary = summary[:SUMMARY_MAX - 3] + "..."
    return summary


def recent_merges(root: Path, count: int) -> "list[tuple[str, str, list[tuple[str, str | None]]]]":
    """main의 최근 머지(첫 부모 기준) count건과 각 머지가 바꾼 .md 문서의 요약."""
    code, out = git(
        root, "log", "--first-parent", "-m", "-n", str(count), "--name-only",
        "--format=%x1e%h %s", "main", "--", "*.md",
    )
    if code != 0:
        return []
    merges = []
    for block in out.split("\x1e")[1:]:
        lines = [l for l in block.splitlines() if l.strip()]
        if not lines:
            continue
        head, _, subject = lines[0].partition(" ")
        docs = [(rel, doc_summary(root / rel)) for rel in lines[1:]]
        merges.append((head, subject, docs))
    return merges


def unmerged_branches(root: Path) -> "list[tuple[str, list[str]]]":
    """main에 머지되지 않은 로컬과 origin 브랜치, 각 브랜치가 TASK_TREE에 더한 진행 노드."""
    code, out = git(
        root, "for-each-ref", "--no-merged", "main", "--format=%(refname:short)",
        "refs/heads", "refs/remotes/origin",
    )
    if code != 0:
        return []
    result = []
    for name in out.split():
        if name in ("origin", "origin/HEAD"):
            continue
        _, diff = git(root, "diff", f"main...{name}", "--", TASK_TREE_REL)
        nodes = [
            line[1:].strip() for line in diff.splitlines()
            if line.startswith("+") and not line.startswith("+++")
            and line[1:].strip().startswith(IN_PROGRESS_PREFIX)
        ]
        result.append((name, nodes))
    return result


def worktrees(root: Path) -> "list[str]":
    code, out = git(root, "worktree", "list")
    return [l.strip() for l in out.splitlines() if l.strip()] if code == 0 else []


def fetch(root: Path) -> str:
    code, _ = git(root, "remote", "get-url", "origin")
    if code != 0:
        return "fetch 건너뜀: origin 원격이 없다. 머지 전 브랜치는 로컬 기준이다."
    code, _ = git(root, "fetch", "--prune", "origin", timeout=FETCH_TIMEOUT)
    if code != 0:
        return f"fetch 실패 또는 {FETCH_TIMEOUT}초 초과: 원격 브랜치는 마지막 fetch 기준이다."
    return "fetch 완료"


def pending_references(root: Path) -> "list[str]":
    """reference 색인에서 상태가 미등록이나 처리 대기인 항목 줄(앞의 `- ` 제외)."""
    try:
        text = (root / REFERENCE_INDEX_REL).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    items = []
    for line in text.splitlines():
        if not line.startswith("- "):
            continue
        if any(state in PENDING_STATES for state in STATE_RE.findall(line)):
            items.append(line[2:].strip())
    return items


def run_tool(script: str, root: Path) -> "tuple[int, str]":
    """같은 폴더의 도구를 현재 인터프리터로 돌린다. 실행하지 못하면 (-1, 사유)."""
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    try:
        proc = subprocess.run(
            [sys.executable, "-B", str(TOOLS_DIR / script), str(root)],
            capture_output=True, encoding="utf-8", errors="replace", env=env,
            timeout=TOOL_TIMEOUT,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return -1, f"{script} 실행 실패: {exc}"
    return proc.returncode, proc.stdout + proc.stderr


def audit_lines(root: Path) -> "list[str]":
    code, out = run_tool("audit.py", root)
    if code == -1:
        return [out]
    lines = out.splitlines()
    summary = [l.strip() for l in lines if l.startswith("감사 완료")]
    violations = [l.strip() for l in lines if l.startswith("VIOLATION")]
    result = summary or [f"audit.py 종료 코드 {code}, 요약 줄을 찾지 못했다"]
    result += violations[:MAX_VIOLATION_LINES]
    if len(violations) > MAX_VIOLATION_LINES:
        result.append(f"... 위반 {len(violations) - MAX_VIOLATION_LINES}줄 더 있음. audit.py를 직접 실행해 본다")
    # reference 색인 경고는 raw 자료가 사라졌다는 신호라 세션 시작 4단계가 따로 본다.
    result += [l.strip() for l in lines if l.startswith("WARNING") and REFERENCE_YAML in l]
    return result


def semantic_lines(root: Path) -> "list[str]":
    code, out = run_tool("check_semantic_audit.py", root)
    lines = [l.strip() for l in out.splitlines() if l.strip()]
    return lines[-1:] if lines else [f"check_semantic_audit.py 종료 코드 {code}, 출력 없음"]


def render(sections: "list[tuple[str, list[str]]]", root: "Path | None" = None) -> str:
    rule = RULE_DOC
    if root is not None:
        try:
            rule = Path(os.path.relpath(RULE_DOC, root))
        except ValueError:
            pass
    out = [
        f"{MARKER} 세션 시작 요약",
        f"{rule.as_posix()} \"세션 시작\" 1-4단계의 기계 부분을 모은 결과다. "
        "이 요약이 컨텍스트에 있으면 다시 실행하지 않는다. 결과의 처리와 남은 단계는 그 절을 따른다.",
    ]
    for title, lines in sections:
        out.append("")
        out.append(f"## {title}")
        out.extend(lines if lines else ["(없음)"])
    text = "\n".join(out) + "\n"
    if len(text) > MAX_CHARS:
        note = "\n... 요약이 길어 잘랐다. 남은 부분은 스크립트를 직접 실행해 본다.\n"
        text = text[:MAX_CHARS - len(note)] + note
    return text


def main(argv: "list[str] | None" = None) -> int:
    parser = argparse.ArgumentParser(description="세션 시작 요약")
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument("--merges", type=int, default=5)
    parser.add_argument("--no-fetch", action="store_true")
    parser.add_argument("--no-audit", action="store_true")
    parser.add_argument("--hook-json", action="store_true")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"Root is not a directory. 루트가 디렉토리가 아니다: {root}", file=sys.stderr)
        return 2

    status = "fetch 생략(--no-fetch)" if args.no_fetch else fetch(root)
    branch_lines = [status]
    for name, nodes in unmerged_branches(root):
        branch_lines.append(f"- {name}")
        branch_lines.extend(f"  - {n}" for n in nodes)

    merge_lines = []
    for head, subject, docs in recent_merges(root, args.merges):
        merge_lines.append(f"- {head} {subject}")
        for rel, summary in docs:
            if summary is None:
                merge_lines.append(f"  - {rel} (지금 없음)")
            else:
                merge_lines.append(f"  - {rel} - {summary}" if summary else f"  - {rel}")

    sections = [
        ("열린 워크트리", worktrees(root)),
        ("main에 머지되지 않은 브랜치와 그 진행 노드", branch_lines),
        (f"main의 최근 머지 {args.merges}건이 바꾼 문서", merge_lines),
    ]
    if not args.no_audit:
        sections.append(("형식 감사", audit_lines(root)))
    sections.append(("의미 감사 트리거", semantic_lines(root)))
    sections.append(("reference 미처리 항목", pending_references(root)))
    text = render(sections, root)
    if args.hook_json:
        text = json.dumps({"hookSpecificOutput": {
            "hookEventName": "SessionStart", "additionalContext": text,
        }}) + "\n"
    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())

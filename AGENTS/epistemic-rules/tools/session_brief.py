#!/usr/bin/env python3
"""세션 시작 요약 (git 의존, 읽기 전용).

session-boundaries.md "세션 시작" 1-4단계 가운데 판단이 필요 없는 부분을 모아
짧은 요약 하나로 낸다. 모델이 명령을 하나씩 돌려 출력을 컨텍스트에 쌓는 대신
이 요약만 읽게 하려는 것이다. 무엇을 모으는지는 그 절이 정하고, 이 스크립트는
그 수집을 구현한다. 머리말은 그 절의 경로를 가리킨다.

절의 순서: 짧고 판정이 걸린 절(형식 감사, 의미 감사 판정, reference 미처리,
워크트리, 머지 전 브랜치)을 앞에, 길어질 수 있는 최근 머지 문서 목록을 끝에
둔다. 출력이 MAX_CHARS를 넘어 끝에서 자를 때 판정이 먼저 빠지지 않게 하려는
것이다. 최근 머지 한 건의 문서는 MAX_DOCS_PER_MERGE개까지만 적고 남은 개수와
전체 목록을 보는 git 명령을 적는다.

수집이 실패하면 "(없음)"이 아니라 실패한 사실을 적는다. 모델이 항목이 없다고
오해하지 않게 하려는 것이다. 최근 머지가 바꾼 문서의 요약은 작업 트리가 아니라
main의 파일에서 읽는다. 작업 브랜치의 워크트리에서 세션을 열어도 main 기준으로
보이게 하려는 것이다.

git은 터미널 자격 증명 입력을 끄고 표준 입력을 닫은 채, 호출마다 제한 시간을
두고 돌린다. 내부 제한 시간의 합은 출고 훅의 timeout보다 짧게 유지한다
(fetch FETCH_TIMEOUT + 형식 감사 AUDIT_TIMEOUT + 의미 감사 판정 SEMANTIC_TIMEOUT +
git 호출들, 문서 요약 예산 DOC_SUMMARY_BUDGET). origin이 없거나 fetch가 제한 시간 안에 끝나지 않으면 건너뛰고 그
사실을 적는다.

--hook-json을 주면 같은 요약을 Claude Code SessionStart 훅의 JSON 출력
(hookSpecificOutput.additionalContext)으로 감싸 ASCII 이스케이프로 낸다. 셸과 콘솔의
인코딩에 영향받지 않는다.

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
import time
from pathlib import Path

MARKER = "[session-brief]"
MAX_CHARS = 9000
SUMMARY_MAX = 160
MAX_DOCS_PER_MERGE = 15
MAX_VIOLATION_LINES = 20
GIT_TIMEOUT = 20
FETCH_TIMEOUT = 15
AUDIT_TIMEOUT = 120
SEMANTIC_TIMEOUT = 30
# 실행 시작부터 이 초를 넘기면 남은 문서는 요약 없이 경로만 적는다. 문서마다 git을
# 부르므로 문서 수에 따라 늘어나는 시간을 훅 timeout 안에 묶어 두려는 것이다.
DOC_SUMMARY_BUDGET = 200
STARTED = time.monotonic()

TOOLS_DIR = Path(__file__).resolve().parent
RULE_DOC = TOOLS_DIR.parent / "session-boundaries.md"
TASK_TREE_REL = "worklog/TASK_TREE.md"
REFERENCE_DIR_REL = Path("reference")
REFERENCE_YAML = "reference/INDEX.yaml"
PENDING_STATES = ("미등록", "처리 대기")
STATE_RE = re.compile(r"`([^`]+)`")
INDEX_PAGE_RE = re.compile(r"^INDEX\d*\.md$")
IN_PROGRESS_PREFIX = "- [/]"

GIT_ENV = dict(os.environ, GIT_TERMINAL_PROMPT="0", GCM_INTERACTIVE="never")


def git(root: Path, *args: str, timeout: float = GIT_TIMEOUT) -> "tuple[int, str]":
    """git을 utf-8로 돌려 (종료 코드, stdout)을 낸다. git이 없거나 시간이 넘으면 (-1, "")."""
    try:
        proc = subprocess.run(
            ["git", "-c", "core.quotePath=false", *args],
            cwd=root, capture_output=True, encoding="utf-8", errors="replace",
            stdin=subprocess.DEVNULL, env=GIT_ENV, timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired):
        return -1, ""
    return proc.returncode, proc.stdout


def summarize(text: str) -> str:
    """문서 본문에서 front matter의 description, 없으면 첫 H1 제목을 뽑는다."""
    lines = text.splitlines()
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


def doc_summary(path: Path) -> "str | None":
    """파일의 요약 한 줄. 파일이 없으면 None."""
    try:
        return summarize(path.read_text(encoding="utf-8", errors="replace"))
    except OSError:
        return None


def main_doc_summary(root: Path, rel: str) -> "str | None":
    """main 브랜치에 있는 문서의 요약 한 줄. main에 없으면 None, 시간 예산을 넘겼으면 ""."""
    if time.monotonic() - STARTED > DOC_SUMMARY_BUDGET:
        return ""
    code, text = git(root, "show", f"main:{rel}")
    return summarize(text) if code == 0 else None


def has_main(root: Path) -> bool:
    code, _ = git(root, "rev-parse", "--verify", "--quiet", "refs/heads/main")
    return code == 0


def recent_merges(root: Path, count: int) -> "list[tuple[str, str, list[tuple[str, str | None]]]] | None":
    """main의 최근 첫 부모 커밋 count건(.md를 바꾼 것)과 바뀐 문서의 요약. 실패하면 None."""
    code, out = git(
        root, "log", "--first-parent", "-m", "-n", str(count), "--name-only",
        "--format=%x1e%h %s", "main", "--", "*.md",
    )
    if code != 0:
        return None
    merges = []
    for block in out.split("\x1e")[1:]:
        lines = [l for l in block.splitlines() if l.strip()]
        if not lines:
            continue
        head, _, subject = lines[0].partition(" ")
        docs = [(rel, main_doc_summary(root, rel)) for rel in lines[1:]]
        merges.append((head, subject, docs))
    return merges


def unmerged_branches(root: Path) -> "list[tuple[str, list[str] | None]] | None":
    """main에 머지되지 않은 로컬과 origin 브랜치와 각 브랜치가 TASK_TREE에 더한 진행 노드.

    목록 조회가 실패하면 None, 브랜치별 diff가 실패하면 그 브랜치의 노드가 None이다.
    """
    code, out = git(
        root, "for-each-ref", "--no-merged", "main", "--format=%(refname:short)",
        "refs/heads", "refs/remotes/origin",
    )
    if code != 0:
        return None
    result = []
    for name in out.split():
        if name in ("origin", "origin/HEAD"):
            continue
        dcode, diff = git(root, "diff", f"main...{name}", "--", TASK_TREE_REL)
        if dcode != 0:
            result.append((name, None))
            continue
        nodes = [
            line[1:].strip() for line in diff.splitlines()
            if line.startswith("+") and not line.startswith("+++")
            and line[1:].strip().startswith(IN_PROGRESS_PREFIX)
        ]
        result.append((name, nodes))
    return result


def worktrees(root: Path) -> "list[str] | None":
    code, out = git(root, "worktree", "list")
    return [l.strip() for l in out.splitlines() if l.strip()] if code == 0 else None


def fetch(root: Path) -> str:
    code, _ = git(root, "remote", "get-url", "origin")
    if code != 0:
        return "fetch 건너뜀: origin 원격이 없다. 머지 전 브랜치는 로컬 기준이다."
    code, _ = git(root, "fetch", "--prune", "origin", timeout=FETCH_TIMEOUT)
    if code != 0:
        return f"fetch 실패 또는 {FETCH_TIMEOUT}초 초과: 원격 브랜치는 마지막 fetch 기준이다."
    return "fetch 완료"


def pending_references(root: Path) -> "list[str]":
    """reference 색인의 모든 쪽에서 상태가 미등록이나 처리 대기인 항목 줄(앞의 `- ` 제외)."""
    folder = root / REFERENCE_DIR_REL
    try:
        pages = sorted(
            (p for p in folder.iterdir() if INDEX_PAGE_RE.match(p.name)),
            key=lambda p: (len(p.name), p.name),
        )
    except OSError:
        return []
    items = []
    for page in pages:
        try:
            text = page.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for line in text.splitlines():
            if line.startswith("- ") and any(
                state in PENDING_STATES for state in STATE_RE.findall(line)
            ):
                items.append(line[2:].strip())
    return items


def run_tool(script: str, root: Path, timeout: float) -> "tuple[int, str]":
    """같은 폴더의 도구를 현재 인터프리터로 돌린다. 실행하지 못하면 (-1, 사유)."""
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    try:
        proc = subprocess.run(
            [sys.executable, "-B", str(TOOLS_DIR / script), str(root)],
            capture_output=True, encoding="utf-8", errors="replace", env=env,
            stdin=subprocess.DEVNULL, timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return -1, f"{script}가 {timeout}초 안에 끝나지 않았다. 직접 실행해 본다."
    except OSError as exc:
        return -1, f"{script} 실행 실패: {exc}"
    return proc.returncode, proc.stdout + proc.stderr


def parse_audit(code: int, out: str) -> "list[str]":
    """audit.py 출력에서 요약 줄, 위반 줄(상한까지), reference 색인 경고 줄을 뽑는다."""
    if code == -1:
        return [out]
    lines = out.splitlines()
    summary = [l.strip() for l in lines if l.startswith("감사 완료")]
    violations = [l.strip() for l in lines if l.startswith("VIOLATION")]
    result = summary or [f"audit.py 종료 코드 {code}, 요약 줄을 찾지 못했다. 직접 실행해 본다."]
    result += violations[:MAX_VIOLATION_LINES]
    if len(violations) > MAX_VIOLATION_LINES:
        result.append(f"... 위반 {len(violations) - MAX_VIOLATION_LINES}줄 더 있음. audit.py를 직접 실행해 본다.")
    # reference 색인 경고는 raw 자료가 사라졌다는 신호라 세션 시작 4단계가 따로 본다.
    result += [l.strip() for l in lines if l.startswith("WARNING") and REFERENCE_YAML in l]
    return result


def parse_semantic(code: int, out: str) -> "list[str]":
    lines = [l.strip() for l in out.splitlines() if l.strip()]
    return lines[-1:] if lines else [f"check_semantic_audit.py 종료 코드 {code}, 출력 없음. 직접 실행해 본다."]


def failed(what: str) -> "list[str]":
    return [f"수집 실패: {what}. 직접 확인한다."]


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
        note = ("\n... 요약이 길어 끝에서 잘랐다. 최근 머지가 바꾼 문서의 전체 목록은 "
                "`git log --first-parent -m --name-only main -- '*.md'`로 본다.\n")
        cut = text.rfind("\n", 0, MAX_CHARS - len(note))
        text = text[:max(cut, 0)] + note
    return text


def merge_lines(merges: "list[tuple[str, str, list[tuple[str, str | None]]]]") -> "list[str]":
    lines = []
    for head, subject, docs in merges:
        lines.append(f"- {head} {subject}")
        for rel, summary in docs[:MAX_DOCS_PER_MERGE]:
            if summary is None:
                lines.append(f"  - {rel} (main에 없음)")
            else:
                lines.append(f"  - {rel} - {summary}" if summary else f"  - {rel}")
        rest = len(docs) - MAX_DOCS_PER_MERGE
        if rest > 0:
            lines.append(f"  - ... 문서 {rest}개 더. `git show --stat {head}`로 본다.")
    return lines


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

    sections = []
    if not args.no_audit:
        sections.append(("형식 감사", parse_audit(*run_tool("audit.py", root, AUDIT_TIMEOUT))))
    sections.append(("의미 감사 트리거", parse_semantic(*run_tool("check_semantic_audit.py", root, SEMANTIC_TIMEOUT))))
    sections.append(("reference 미처리 항목", pending_references(root)))

    trees = worktrees(root)
    sections.append(("열린 워크트리", trees if trees is not None else failed("git worktree list")))

    main_ok = has_main(root)
    branch_lines = ["fetch 생략(--no-fetch)" if args.no_fetch else fetch(root)]
    if not main_ok:
        branch_lines += failed("로컬 main 브랜치가 없어 머지 전 브랜치를 판정하지 못했다")
    else:
        branches = unmerged_branches(root)
        if branches is None:
            branch_lines += failed("git for-each-ref --no-merged main")
        for name, nodes in branches or []:
            branch_lines.append(f"- {name}")
            if nodes is None:
                branch_lines.append(f"  - 수집 실패: git diff main...{name} -- {TASK_TREE_REL}")
            else:
                branch_lines.extend(f"  - {n}" for n in nodes)
    sections.append(("main에 머지되지 않은 브랜치와 그 진행 노드", branch_lines))

    merges = recent_merges(root, args.merges) if main_ok else None
    title = f"main의 최근 머지 {args.merges}건이 바꾼 문서"
    sections.append((title, merge_lines(merges) if merges is not None else failed("main의 최근 머지 조회")))

    text = render(sections, root)
    if args.hook_json:
        payload = {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": text}}
        text = json.dumps(payload) + "\n"
    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())

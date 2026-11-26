#!/usr/bin/env python3
"""세션 시작 요약 (git 의존).

session-boundaries.md "세션 시작" 1-5단계 가운데 판단이 필요 없는 부분을 모아
짧은 요약 하나로 낸다. 모델이 명령을 하나씩 돌려 출력을 컨텍스트에 쌓는 대신
이 요약만 읽게 하려는 것이다. 무엇을 모으는지는 그 절이 정하고, 이 스크립트는
그 수집을 구현한다. 머리말은 그 절의 경로를 가리킨다.

파일을 고치지 않지만 부작용이 셋 있다. git fetch로 원격 참조를 갱신하고, 레포의 확장
스크립트를 실행하며, 환경 갱신 판정(_setup_core.status)이 설치 항목마다 점검 명령을
실행한다.

인스턴스 확장: 레포 루트의 AGENTS/session-brief/ 바로 아래 *.py를 이름 순으로
`python -B <확장> <루트>`로 실행하고(작업 폴더는 루트, 표준 입력 없음, 환경 변수
EPISTEMIC_AUDIT_TOOLS에 이 도구 폴더), 표준 출력의 텍스트를 "확장: <파일 이름 줄기>"
절로 붙인다. 확장 하나는 EXTENSION_MAX_CHARS, 확장 절 합계는 EXTENSION_TOTAL_MAX_CHARS,
실행 시간은 확장 하나 EXTENSION_TIMEOUT, 전체 EXTENSION_TOTAL_BUDGET 안으로 묶어, 확장이
늘어도 판정 절이 요약 상한 밖으로 밀려나지 않게 한다. 계약은
session-brief-extensions.md에 있다.

절의 순서: 인스턴스 확장 절을 맨 앞에 두고, 이어서 짧고 판정이 걸린 절(형식 감사, 의미 감사 판정, reference 미처리,
워크트리, 머지 전 브랜치)을 앞에, 길어질 수 있는 최근 머지 문서 목록을 끝에
둔다. 출력이 MAX_CHARS를 넘어 끝에서 자를 때 판정이 먼저 빠지지 않게 하려는
것이다. 최근 머지 한 건의 문서는 MAX_DOCS_PER_MERGE개까지만 적고 남은 개수와
전체 목록을 보는 git 명령을 적는다.

수집이 실패하면 "(없음)"이 아니라 실패한 사실을 적는다. 모델이 항목이 없다고
오해하지 않게 하려는 것이다. 최근 머지가 바꾼 문서의 요약은 작업 트리가 아니라
main의 파일에서 git cat-file --batch 한 번으로 읽는다. 작업 브랜치의 워크트리에서
세션을 열어도 main 기준으로 보이게 하려는 것이다.

형식 감사는 가장 오래 걸려 시작하자마자 별도 프로세스로 띄우고, 다른 수집(확장, git 조회,
fetch)을 모두 마친 뒤 결과를 거두어 절 순서대로 넣는다. 제한 시간 AUDIT_TIMEOUT은 띄운
때부터 세어 결과를 거둘 때 적용한다. 그때 이미 끝났으면 결과를 받고, 아직 돌면 감사가 띄운
프로세스까지 정리하고 시간 초과로 적는다. 규범 문서와 감사 발견의 경로는 레포 기준으로 적되, 작업
폴더가 레포를 담은 상위 폴더이면 작업 폴더 기준으로 적는다.

git은 터미널 자격 증명 입력을 끄고 표준 입력을 닫은 채, 호출마다 제한 시간을
두고 돌린다. 내부 제한 시간의 합은 출고 훅의 timeout보다 짧게 유지한다
(fetch FETCH_TIMEOUT + 형식 감사 AUDIT_TIMEOUT + 의미 감사 판정 SEMANTIC_TIMEOUT +
git 호출들, 확장 전체 예산 EXTENSION_TOTAL_BUDGET). origin이 없거나 fetch가 제한 시간 안에 끝나지 않으면 건너뛰고 그
사실을 적는다. 제한 시간을 넘긴 fetch는 원격 도우미까지 정리한다.

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
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _setup_core  # noqa: E402

MARKER = "[session-brief]"
MAX_CHARS = 9000
SUMMARY_MAX = 160
MAX_DOCS_PER_MERGE = 15
MAX_VIOLATION_LINES = 20
GIT_TIMEOUT = 20
FETCH_TIMEOUT = 15
# 형식 감사를 띄운 때부터 센다. 결과를 거둘 때 적용해, 그때 이미 끝났으면 결과를 받고
# 아직 돌면 프로세스 트리를 정리하고 시간 초과로 적는다(Spawn).
AUDIT_TIMEOUT = 120
SEMANTIC_TIMEOUT = 30
KILL_WAIT = 5

TOOLS_DIR = Path(__file__).resolve().parent
RULE_DOC = TOOLS_DIR.parent / "session-boundaries.md"
TASK_TREE_REL = "worklog/TASK_TREE.md"
REFERENCE_DIR_REL = Path("reference")
REFERENCE_YAML = "reference/INDEX.yaml"
PENDING_STATES = ("미등록", "처리 대기")
STATE_RE = re.compile(r"`([^`]+)`")
INDEX_PAGE_RE = re.compile(r"^INDEX\d*\.md$")
HUNK_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")
# 감사 발견 줄(`VIOLATION [kind] <경로>: ...`, `WARNING   [kind] <경로>: ...`)의 경로 앞까지.
FINDING_RE = re.compile(r"^((?:VIOLATION|WARNING) +\[[^\]]*\] )(.*)$")
IN_PROGRESS_PREFIX = "- [/]"
EXTENSION_DIR_REL = Path("AGENTS/session-brief")
EXTENSION_TIMEOUT = 30
EXTENSION_TOTAL_BUDGET = 60
EXTENSION_MAX_CHARS = 2000
# 확장 절 합계의 상한. 요약 상한(MAX_CHARS)에서 판정 절이 들어갈 자리를 남긴다.
EXTENSION_TOTAL_MAX_CHARS = 3000
STDERR_LIMIT = 200

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


def git_quiet(root: Path, *args: str, timeout: float) -> int:
    """출력을 버리고 git을 돌려 종료 코드를 낸다. git이 없거나 시간이 넘으면 -1.

    Spawn으로 돌려 출력을 파이프로 잡지 않고, 시간을 넘기면 원격 도우미까지 정리한다.
    남겨 두면 레포를 작업 폴더로 쥔 채 계속 돈다.
    """
    run = Spawn(["git", *args], root, GIT_ENV, timeout, capture=False)
    try:
        code = run.wait()
    finally:
        run.close()
    return -1 if code is None else code


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


LOCAL_MAIN = "refs/heads/main"


def main_doc_summaries(root: Path, rels: "list[str]", offline: bool = False) -> "list[str | None] | None":
    """main 브랜치에 있는 문서들의 요약 한 줄을 rels 순서로 낸다. main에 없는 문서는 None.

    git cat-file --batch 한 번에 `refs/heads/main:<경로>`를 넣어 읽는다. 응답은 문서마다
    `<oid> <type> <size>` 줄 뒤에 본문 size바이트와 LF 하나, 없으면 `<입력> missing` 줄이다.
    본문 길이가 바이트 단위라 입력과 응답을 바이트로 다루고 본문만 utf-8로 디코드한다.
    git이 실패하거나 응답이 이 모양이 아니면(본문이 선언한 길이보다 짧거나, 본문 뒤 LF가
    없거나, 레코드를 다 읽은 뒤 바이트가 남으면) None. 부분 클론에서 본문을 원격에서 받아
    오느라(지연 fetch) GIT_TIMEOUT을 넘기면 Spawn이 그 하위 프로세스까지 정리하고 None이다.

    offline(--no-fetch)이면 원격 조회 생략을 문서 조회에도 적용해 지연 fetch를 끈다
    (GIT_NO_LAZY_FETCH=1, 이 변수를 모르는 옛 Git을 위해 GIT_ALLOW_PROTOCOL도 비운다).
    그 밖에는 호출자 환경을 그대로 쓴다. 지연 fetch가 꺼져 있으면
    부분 클론에서 본문이 로컬에 없을 뿐인 문서도 missing이 되므로, missing이 있으면 main
    트리에 그 경로가 있는지 ls-tree로 한 번 더 본다. 경로가 없을 때만 "main에 없음"(None)이고,
    경로가 있으면 본문을 읽지 못한 것이라 전체를 수집 실패(None)로 낸다.
    """
    if not rels:
        return []
    # GIT_NO_LAZY_FETCH를 모르는 옛 Git에서도 전송을 막도록 허용 프로토콜도 비운다.
    env = dict(GIT_ENV, GIT_NO_LAZY_FETCH="1", GIT_ALLOW_PROTOCOL="") if offline else GIT_ENV
    data = b"".join(f"{LOCAL_MAIN}:{rel}\n".encode("utf-8") for rel in rels)
    run = Spawn(["git", "cat-file", "--batch"], root, env, GIT_TIMEOUT, data)
    try:
        if run.wait() != 0:
            return None
        out = run.output()
    finally:
        run.close()
    result = parse_cat_file(out, len(rels))
    if result is None:
        return None
    missing = [rel for rel, summary in zip(rels, result) if summary is MISSING]
    if missing:
        present = main_tree_paths(root, missing, env)
        if present is None or present & set(missing):
            return None
    return [None if summary is MISSING else summary for summary in result]


# cat-file이 missing으로 답한 레코드. 경로가 main에 없는 것인지 본문만 없는 것인지는 아직 모른다.
MISSING = object()


def main_tree_paths(root: Path, rels: "list[str]", env: "dict[str, str]") -> "set[str] | None":
    """rels 가운데 main 트리에 있는 경로. 경로는 글자 그대로 맞춘다. git이 실패하거나 시간을 넘기면 None."""
    run = Spawn(
        ["git", "--literal-pathspecs", "ls-tree", "--name-only", "-z", LOCAL_MAIN, "--", *rels],
        root, env, GIT_TIMEOUT,
    )
    try:
        if run.wait() != 0:
            return None
        out = run.output()
    finally:
        run.close()
    return {name.decode("utf-8", errors="replace") for name in out.split(b"\0") if name}


def parse_cat_file(out: bytes, count: int) -> "list | None":
    """cat-file --batch 응답 count건을 요약(blob), None(blob이 아님), MISSING으로 바꾼다. 모양이 어긋나면 None."""
    pos = 0
    result: "list" = []
    for _ in range(count):
        end = out.find(b"\n", pos)
        if end < 0:
            return None
        # 입력에 공백이 들어갈 수 있어 오른쪽부터 자른다.
        fields = out[pos:end].rsplit(b" ", 2)
        pos = end + 1
        if fields[-1] in (b"missing", b"ambiguous"):
            result.append(MISSING)
            continue
        if len(fields) != 3 or not fields[2].isdigit():
            return None
        size = int(fields[2])
        if out[pos + size:pos + size + 1] != b"\n":
            return None
        body = out[pos:pos + size]
        pos += size + 1
        result.append(summarize(body.decode("utf-8", errors="replace")) if fields[1] == b"blob" else None)
    if pos != len(out):
        return None
    return result


ORIGIN_MAIN = "refs/remotes/origin/main"


def has_main(root: Path) -> bool:
    code, _ = git(root, "rev-parse", "--verify", "--quiet", LOCAL_MAIN)
    return code == 0


def origin_main_state(root: Path) -> "tuple[str | None, int | None]":
    """(origin/main 커밋, 로컬 main이 그보다 뒤진 커밋 수).

    origin/main이 없으면 (None, 0), 조회가 실패하면 (None, None), 커밋 수만 세지 못하면
    (커밋, None)이다. 커밋을 한 번만 풀어 이후 판정이 모두 같은 커밋을 보게 한다.
    """
    code, out = git(root, "for-each-ref", "--format=%(refname) %(objectname)", ORIGIN_MAIN)
    if code != 0:
        return None, None
    # for-each-ref는 경로 접두사로도 일치하므로(origin/main/x) 이름이 정확히 같은 줄만 쓴다.
    commit = next((obj for ref, _, obj in (l.partition(" ") for l in out.splitlines()) if ref == ORIGIN_MAIN), None)
    if commit is None:
        return None, 0
    code, count = git(root, "rev-list", "--count", f"{LOCAL_MAIN}..{commit}")
    if code != 0 or not count.strip().isdigit():
        return commit, None
    return commit, int(count.strip())


def recent_merges(
    root: Path, count: int, offline: bool = False,
) -> "list[tuple[str, str, list[tuple[str, str | None]]]] | None":
    """main의 최근 첫 부모 커밋 count건(.md를 바꾼 것)과 바뀐 문서의 요약. 실패하면 None.

    offline은 main_doc_summaries에 넘긴다(--no-fetch).
    """
    code, out = git(
        root, "log", "--first-parent", "-m", "-n", str(count), "--name-only",
        "--format=%x1e%h %s", LOCAL_MAIN, "--", "*.md",
    )
    if code != 0:
        return None
    parsed = []
    for block in out.split("\x1e")[1:]:
        lines = [l for l in block.splitlines() if l.strip()]
        if not lines:
            continue
        head, _, subject = lines[0].partition(" ")
        parsed.append((head, subject, lines[1:]))
    # 표시 상한 밖의 문서는 merge_lines가 개수만 적으므로 요약을 읽지 않는다.
    wanted = [rel for _, _, rels in parsed for rel in rels[:MAX_DOCS_PER_MERGE]]
    summaries = main_doc_summaries(root, wanted, offline)
    if summaries is None:
        return None
    it = iter(summaries)
    return [
        (head, subject, [(rel, next(it) if i < MAX_DOCS_PER_MERGE else "") for i, rel in enumerate(rels)])
        for head, subject, rels in parsed
    ]


def added_nodes(root: Path, base: str, ref: str) -> "list[tuple[int, str]] | None":
    """ref가 base와의 공통 조상 뒤로 TASK_TREE에 더한 진행 노드와 ref 쪽 파일의 줄 번호.

    diff가 실패하면 None. 줄 번호는 같은 ref를 서로 다른 base와 비교한 결과를 맞춰 보는 데 쓴다.
    """
    # 문맥 줄이 끼면 줄 번호가 틀어지므로 diff.interHunkContext 설정과 무관하게 끈다.
    code, diff = git(
        root, "diff", "--unified=0", "--inter-hunk-context=0", f"{base}...{ref}", "--", TASK_TREE_REL,
    )
    if code != 0:
        return None
    nodes = []
    lineno = None
    for line in diff.splitlines():
        match = HUNK_RE.match(line)
        if match:
            lineno = int(match.group(1))
        elif lineno is not None and line.startswith("+"):
            text = line[1:].strip()
            if text.startswith(IN_PROGRESS_PREFIX):
                nodes.append((lineno, text))
            lineno += 1
    return nodes


def unmerged_branches(
    root: Path, origin_main: "str | None" = None,
) -> "list[tuple[str, list[str] | None, bool]] | None":
    """main에 머지되지 않은 로컬과 origin 브랜치, 각 브랜치가 TASK_TREE에 더한 진행 노드,
    origin/main 기준 비교에 실패했는가.

    origin_main(origin/main 커밋)을 주면 거기에 머지된 브랜치도 빼고, 진행 노드는 로컬 main과
    origin/main 양쪽 기준으로 모두 더해진 것만 남긴다. 로컬 main을 pull하기 전에도 다른 곳에서
    머지된 작업이나 원격 main에서 물려받은 노드가 그 브랜치의 작업으로 나오지 않게 하려는 것이다.
    origin/main 기준 비교만 실패하면 로컬 main 기준 노드를 남기고 세 번째 값을 참으로 둔다.
    참조는 같은 이름의 태그나 브랜치와 헷갈리지 않게 전체 이름으로 넘긴다.
    목록 조회가 실패하면 None, 로컬 main 기준 diff가 실패하면 그 브랜치의 노드가 None이다.
    """
    merged_into = ["--no-merged", LOCAL_MAIN] + (["--no-merged", origin_main] if origin_main else [])
    code, out = git(
        root, "for-each-ref", *merged_into, "--format=%(refname) %(objectname) %(refname:short)",
        "refs/heads", "refs/remotes/origin",
    )
    if code != 0:
        return None
    result = []
    for line in out.splitlines():
        ref, _, rest = line.partition(" ")
        commit, _, name = rest.partition(" ")
        if not commit or ref == "refs/remotes/origin/HEAD":
            continue
        # 두 비교가 같은 브랜치 내용을 보도록 목록 조회 때의 커밋으로 비교한다.
        nodes = added_nodes(root, LOCAL_MAIN, commit)
        remote_failed = False
        if nodes is not None and origin_main:
            remote = added_nodes(root, origin_main, commit)
            if remote is None:
                remote_failed = True
            else:
                remote_set = set(remote)
                nodes = [n for n in nodes if n in remote_set]
        result.append((name, None if nodes is None else [text for _, text in nodes], remote_failed))
    return result


def worktrees(root: Path) -> "list[str] | None":
    code, out = git(root, "worktree", "list")
    return [l.strip() for l in out.splitlines() if l.strip()] if code == 0 else None


def fetch(root: Path) -> str:
    code, _ = git(root, "remote", "get-url", "origin")
    if code != 0:
        return "fetch 건너뜀: origin 원격이 없다. 머지 전 브랜치는 로컬 기준이다."
    code = git_quiet(root, "fetch", "--prune", "origin", timeout=FETCH_TIMEOUT)
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
    """같은 폴더의 도구를 현재 인터프리터로 돌려 끝날 때까지 기다린다. 결과는 ToolRun.result와 같다."""
    return ToolRun(script, root, timeout).result()


def kill_tree(proc: "subprocess.Popen") -> None:
    """proc과 그것이 띄운 프로세스를 끝낸다. 윈도우는 taskkill /T, 그 밖은 프로세스 그룹으로 끝낸다.

    POSIX의 그룹 종료는 proc을 start_new_session=True로 띄웠을 때만 자식까지 닿는다.
    정리가 요약을 붙잡지 않게 taskkill과 마지막 대기에 KILL_WAIT 상한을 두고, 정리의 실패와
    시간 초과는 무시한다.
    """
    if os.name == "nt":
        try:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(proc.pid)], stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=KILL_WAIT,
            )
        except (OSError, subprocess.SubprocessError):
            pass
    else:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except OSError:
            pass
    try:
        proc.kill()
        proc.wait(timeout=KILL_WAIT)
    except (OSError, subprocess.SubprocessError):
        pass


class Spawn:
    """명령 하나를 띄워 두고 나중에 거둔다. 입력과 출력은 파이프가 아니라 임시 파일이다.

    파이프를 쓰면 자식이 띄운 프로세스가 파이프를 쥐고 있을 때 시간 초과 뒤에도 닫힐 때까지
    기다리게 된다(윈도우에서 실측, run_extension 참고). POSIX에서는 새 세션으로 띄워
    kill_tree가 그룹 전체에 닿게 한다.

    제한 시간 timeout은 띄운 때부터 세고 wait가 거둘 때 적용한다. 거둘 때 이미 끝났으면 늦게
    거뒀어도 그 결과를 받고, 아직 돌면 프로세스 트리를 정리하고 시간 초과(None)로 낸다.
    시간 초과 뒤에는 직접 자식이 그사이 끝났어도 트리 정리를 한 번 시도한다. 하위 프로세스가
    남아 있을 수 있기 때문이다. 트리 정리는 stop 한 곳에서 한 번만 하고, close는 여러 번 불러도
    된다. 호출하는 쪽은 close를 finally에 두어 중단(KeyboardInterrupt 등)에도 트리가 남지 않게
    한다. capture가 거짓이면 stdout, stderr를 버려(DEVNULL) 임시 폴더에 쓸 수 없어도 띄울 수
    있다. 띄우지 못하면(임시 파일 생성 실패 포함) error에 사유를 두고 wait가 None을 낸다.
    """

    def __init__(self, cmd: "list[str]", cwd: "Path | None", env: "dict[str, str]", timeout: float,
                 data: "bytes | None" = None, capture: bool = True):
        self.timeout = timeout
        self.proc: "subprocess.Popen | None" = None
        self.error = ""
        self.files: "list" = []
        self.stopped = False
        self.closed = False
        self.started = time.monotonic()
        try:
            stdin = subprocess.DEVNULL
            if data is not None:
                stdin = self.temp()
                stdin.write(data)
                stdin.seek(0)
            self.out = self.temp() if capture else subprocess.DEVNULL
            self.err = self.temp() if capture else subprocess.DEVNULL
            self.proc = subprocess.Popen(
                cmd, cwd=cwd, env=env, stdin=stdin, stdout=self.out, stderr=self.err,
                start_new_session=os.name != "nt",
            )
        except OSError as exc:
            self.error = str(exc)
            self.close()

    def temp(self):
        f = tempfile.TemporaryFile()
        self.files.append(f)
        return f

    def wait(self) -> "int | None":
        """종료 코드. 띄우지 못했거나 시간을 넘겼으면 None(넘겼으면 트리를 정리한 뒤)."""
        if self.proc is None:
            return None
        remaining = self.timeout - (time.monotonic() - self.started)
        try:
            return self.proc.wait(timeout=max(remaining, 0))
        except subprocess.TimeoutExpired:
            self.stop(force=True)
            return None

    def output(self) -> bytes:
        self.out.seek(0)
        return self.out.read()

    def text(self) -> str:
        """stdout과 stderr를 각각 utf-8로 읽고 줄바꿈을 \\n으로 맞춰 이어 붙인다(텍스트 모드 파이프와 같게)."""
        parts = []
        for f in (self.out, self.err):
            f.seek(0)
            parts.append(f.read().decode("utf-8", errors="replace").replace("\r\n", "\n").replace("\r", "\n"))
        return "".join(parts)

    def stop(self, force: bool = False) -> None:
        """트리를 한 번만 정리한다. force가 아니면 직접 자식이 아직 돌 때만 정리한다."""
        if self.proc is None or self.stopped:
            return
        if not force and self.proc.poll() is not None:
            return
        self.stopped = True
        kill_tree(self.proc)

    def close(self) -> None:
        """아직 돌면 트리를 정리하고 임시 파일을 닫는다(닫히면 지워진다)."""
        if self.closed:
            return
        self.closed = True
        self.stop()
        for f in self.files:
            f.close()


class ToolRun:
    """같은 폴더의 도구를 현재 인터프리터로 띄워 두고, 나중에 결과를 거둔다.

    제한 시간은 Spawn과 같다. 띄운 때부터 세어 result가 거둘 때 적용하므로, 거둘 때 이미
    끝난 결과는 정상으로 받고 아직 돌면 트리를 정리하고 시간 초과로 적는다.
    """

    def __init__(self, script: str, root: Path, timeout: float):
        self.script = script
        self.timeout = timeout
        self.run = Spawn(
            [sys.executable, "-B", str(TOOLS_DIR / script), str(root)], None,
            dict(os.environ, PYTHONIOENCODING="utf-8"), timeout,
        )

    def result(self) -> "tuple[int, str]":
        """(종료 코드, stdout과 stderr). 실행하지 못했거나 시간을 넘기면 (-1, 사유)."""
        try:
            if self.run.proc is None:
                return -1, f"{self.script} 실행 실패: {self.run.error}"
            code = self.run.wait()
            if code is None:
                return -1, (f"{self.script}가 {self.timeout}초 안에 끝나지 않았다. 백그라운드로 직접 실행해 결과를 본다. "
                            "늘 넘기는 레포는 세션 시작 훅 인자에 --no-audit를 준다.")
            return code, self.run.text()
        finally:
            self.run.close()

    def close(self) -> None:
        self.run.close()


def cwd_prefix(root: Path) -> str:
    """레포 기준 경로 앞에 붙여 작업 폴더 기준으로 바꾸는 접두사(끝 / 포함).

    작업 폴더가 레포를 담은 상위 폴더일 때만 붙인다. 레포와 같거나 그 안이거나 레포와
    무관한 곳이면 레포 기준 그대로 둔다("").
    """
    try:
        cwd = Path.cwd().resolve()
        if cwd not in root.parents:
            return ""
        return Path(os.path.relpath(root, cwd)).as_posix() + "/"
    except (OSError, ValueError):
        return ""


def parse_audit(code: int, out: str, prefix: str = "") -> "list[str]":
    """audit.py 출력에서 요약 줄, 위반 줄(상한까지), reference 색인 경고 줄을 뽑는다.

    prefix(cwd_prefix)를 주면 위반 줄과 경고 줄의 경로 앞에 붙인다. 경로가 "."(레포 전체)이면
    접두사만 적는다.
    """
    if code == -1:
        return [out]
    lines = out.splitlines()
    summary = [l.strip() for l in lines if l.startswith("감사 완료")]
    violations = [with_prefix(l.strip(), prefix) for l in lines if l.startswith("VIOLATION")]
    result = summary or [f"audit.py 종료 코드 {code}, 요약 줄을 찾지 못했다. 직접 실행해 본다."]
    result += violations[:MAX_VIOLATION_LINES]
    if len(violations) > MAX_VIOLATION_LINES:
        result.append(f"... 위반 {len(violations) - MAX_VIOLATION_LINES}줄 더 있음. audit.py를 직접 실행해 본다.")
    # reference 색인 경고는 raw 자료가 사라졌다는 신호라 세션 시작 4단계가 따로 본다.
    result += [with_prefix(l.strip(), prefix) for l in lines if l.startswith("WARNING") and REFERENCE_YAML in l]
    return result


def with_prefix(line: str, prefix: str) -> str:
    match = FINDING_RE.match(line)
    if not prefix or not match:
        return line
    head, rest = match.groups()
    # 경로 필드가 정확히 "."일 때만 레포 자신이다. `.:x.md` 같은 파일 이름은 일반 경로로 다룬다.
    if rest == "." or rest.startswith(".: "):
        return head + prefix.rstrip("/") + rest[1:]
    return head + prefix + rest


def parse_semantic(code: int, out: str) -> "list[str]":
    lines = [l.strip() for l in out.splitlines() if l.strip()]
    return lines[-1:] if lines else [f"check_semantic_audit.py 종료 코드 {code}, 출력 없음. 직접 실행해 본다."]


def extension_sections(root: Path) -> "list[tuple[str, list[str]]]":
    """AGENTS/session-brief/ 바로 아래 *.py 확장을 이름 순으로 실행해 절마다 하나씩 낸다.

    이름이 _나 .으로 시작하는 항목, .py가 아닌 파일, 하위 폴더, 심볼릭 링크는
    실행하지 않는다. 실패한 확장은 출력을 버리고 수집 실패 한 줄을 낸다.
    """
    folder = root / EXTENSION_DIR_REL
    try:
        if folder.is_symlink() or not folder.is_dir():
            return []
        entries = sorted(folder.iterdir(), key=lambda p: p.name)
    except OSError:
        return []
    env = dict(
        os.environ, PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1",
        EPISTEMIC_AUDIT_TOOLS=str(TOOLS_DIR),
    )
    sections = []
    started = time.monotonic()
    total = 0
    for path in entries:
        if path.name.startswith(("_", ".")) or path.suffix != ".py" or path.is_symlink() or not path.is_file():
            continue
        title = f"확장: {path.stem}"
        remaining = EXTENSION_TOTAL_BUDGET - (time.monotonic() - started)
        if remaining <= 0:
            sections.append((title, [f"실행 생략: 확장 전체 시간 예산 {EXTENSION_TOTAL_BUDGET}초를 넘겼다. 직접 실행해 본다."]))
            continue
        if total >= EXTENSION_TOTAL_MAX_CHARS:
            sections.append((title, [f"실행 생략: 확장 출력 합계 상한 {EXTENSION_TOTAL_MAX_CHARS}자에 닿았다. 직접 실행해 본다."]))
            continue
        lines = run_extension(path, root, env, min(EXTENSION_TIMEOUT, remaining))
        total += sum(len(l) + 1 for l in lines)
        sections.append((title, lines))
    return sections


def run_extension(path: Path, root: Path, env: "dict[str, str]", timeout: float) -> "list[str]":
    """확장 하나를 실행해 절의 줄을 낸다. 실패하면 수집 실패 한 줄.

    출력은 파이프가 아니라 임시 파일로 받는다. 확장이 띄운 자식 프로세스가 파이프를
    쥐고 있으면 시간 초과 뒤에도 파이프가 닫힐 때까지 기다리게 되어(윈도우에서 실측)
    제한 시간이 지켜지지 않기 때문이다. 확장이 띄운 다른 프로세스는 정리하지 않는다.
    """
    with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
        try:
            proc = subprocess.run(
                [sys.executable, "-B", str(path), str(root)], cwd=root, env=env,
                stdin=subprocess.DEVNULL, stdout=out, stderr=err, timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return [f"수집 실패: 확장 {path.name}가 {max(1, round(timeout))}초 안에 끝나지 않았다."]
        except OSError as exc:
            return [f"수집 실패: 확장 {path.name} 실행 실패: {exc}"]
        out.seek(0)
        err.seek(0)
        stdout = out.read().decode("utf-8", errors="replace")
        stderr = err.read().decode("utf-8", errors="replace")
    if proc.returncode != 0:
        last = (stderr.strip().splitlines() or [""])[-1][:STDERR_LIMIT]
        return [f"수집 실패: 확장 {path.name} 종료 코드 {proc.returncode}: {last}"]
    text = stdout.rstrip()
    if len(text) > EXTENSION_MAX_CHARS:
        note = "\n... 확장 출력이 길어 잘랐다. 확장을 직접 실행해 본다."
        limit = EXTENSION_MAX_CHARS - len(note)
        cut = text.rfind("\n", 0, limit)
        text = text[:cut if cut > 0 else limit] + note
    return text.splitlines()


def name_from_common_dir(common: Path, root: Path) -> str:
    """git 공용 폴더의 모양으로 주 레포 이름을 정한다.

    - <레포>/.git: 일반 레포와 그 워크트리
    - .../modules/<이름>: 서브모듈과 그 워크트리
    - <이름>.git: bare 레포와 그 워크트리
    셋 다 아니면 루트 폴더 이름을 쓴다.
    """
    if common.name == ".git":
        return common.parent.name
    if common.parent.name == "modules":
        return common.name
    if common.name.endswith(".git") and len(common.name) > 4:
        return common.name[:-4]
    return root.name


def repo_name(root: Path) -> str:
    """주 레포 이름. 워크트리에서도 주 레포 이름을 낸다."""
    code, out = git(root, "rev-parse", "--git-common-dir")
    if code == 0 and out.strip():
        common = Path(out.strip())
        if not common.is_absolute():
            common = root / common
        return name_from_common_dir(common.resolve(), root)
    return root.name


def setup_lines(root: Path) -> "list[str]":
    """설치 체계의 환경 갱신 판정(_setup_core.status_lines). 어떤 실패도 한 줄로 바꾼다."""
    try:
        return _setup_core.status_lines(root)
    except Exception as exc:  # noqa: BLE001 - 요약이 세션 시작을 막지 않게 한다
        return [f"수집 실패: 환경 갱신 판정 중 오류({type(exc).__name__}). setup.py check로 직접 본다."]


def failed(what: str) -> "list[str]":
    return [f"수집 실패: {what}. 직접 확인한다."]


def render(sections: "list[tuple[str, list[str]]]", root: "Path | None" = None) -> str:
    rule = RULE_DOC
    title = f"{MARKER} 세션 시작 요약"
    if root is not None:
        title += f": {repo_name(root)}"
        # 작업 폴더가 레포를 담은 상위 폴더이면 작업 폴더 기준, 아니면 레포 기준으로 적는다.
        base = Path.cwd().resolve() if cwd_prefix(root) else root
        try:
            rule = Path(os.path.relpath(RULE_DOC, base))
        except ValueError:
            pass
    out = [
        title,
        f"{rule.as_posix()} \"세션 시작\" 1-5단계의 기계 부분을 모은 결과다. "
        "이 요약이 컨텍스트에 있으면 다시 실행하지 않는다. 결과의 처리와 남은 단계는 그 절을 따른다.",
    ]
    for title, lines in sections:
        out.append("")
        out.append(f"## {title}")
        out.extend(lines if lines else ["(없음)"])
    text = "\n".join(out) + "\n"
    if len(text) > MAX_CHARS:
        # 잘린 절 이름을 안내에 넣으려고 안내 길이의 상한을 먼저 잡아 둔다.
        reserve = 400
        cut = text.rfind("\n", 0, MAX_CHARS - reserve)
        kept = text[:max(cut, 0)]
        dropped = [t for t, _ in sections if f"\n## {t}\n" not in kept + "\n"]
        names = ", ".join(dropped)[:200] or "마지막 절의 일부"
        note = (f"\n... 요약이 길어 끝에서 잘랐다. 잘린 절: {names}. 스크립트를 직접 실행해 본다. "
                "최근 머지가 바꾼 문서의 전체 목록은 `git log --first-parent -m --name-only main -- '*.md'`로 본다.\n")
        text = kept + note
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

    # 형식 감사가 가장 오래 걸려 먼저 띄워 두고 나머지 수집과 겹친다.
    audit = None if args.no_audit else ToolRun("audit.py", root, AUDIT_TIMEOUT)
    try:
        text = brief(root, args, audit)
    finally:
        if audit is not None:
            audit.close()
    if args.hook_json:
        payload = {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": text}}
        text = json.dumps(payload) + "\n"
    sys.stdout.write(text)
    return 0


def brief(root: Path, args: argparse.Namespace, audit: "ToolRun | None") -> str:
    """요약 본문. audit는 main이 먼저 띄운 형식 감사이고 --no-audit면 None이다.

    형식 감사 결과는 다른 수집을 모두 마친 뒤 거두어 확장 절 바로 뒤에 넣는다.
    """
    sections = extension_sections(root)
    audit_at = len(sections)
    sections.append(("의미 감사 트리거", parse_semantic(*run_tool("check_semantic_audit.py", root, SEMANTIC_TIMEOUT))))
    sections.append(("환경 갱신", setup_lines(root)))
    sections.append(("reference 미처리 항목", pending_references(root)))

    trees = worktrees(root)
    sections.append(("열린 워크트리", trees if trees is not None else failed("git worktree list")))

    main_ok = has_main(root)
    branch_lines = ["fetch 생략(--no-fetch)" if args.no_fetch else fetch(root)]
    if not main_ok:
        branch_lines += failed("로컬 main 브랜치가 없어 머지 전 브랜치를 판정하지 못했다")
    else:
        origin_main, behind = origin_main_state(root)
        if origin_main is None and behind is None:
            branch_lines += failed("origin/main 조회. 아래 브랜치 판정은 로컬 main 기준이다")
        elif behind is None:
            branch_lines += failed("로컬 main이 origin/main보다 뒤진 커밋 수 계산")
        elif behind:
            branch_lines.append(
                f"로컬 main이 origin/main보다 {behind}커밋 뒤다. 아래 브랜치 판정은 origin/main도 기준으로 삼았고,"
                " 다음 절의 최근 머지는 로컬 main 기준이다."
            )
        branches = unmerged_branches(root, origin_main)
        if branches is None:
            branch_lines += failed("git for-each-ref --no-merged main")
        for name, nodes, remote_failed in branches or []:
            branch_lines.append(f"- {name}")
            if remote_failed:
                branch_lines.append(f"  - 수집 실패: git diff origin/main...{name} -- {TASK_TREE_REL}. 아래 노드는 로컬 main 기준이다")
            if nodes is None:
                branch_lines.append(f"  - 수집 실패: git diff main...{name} -- {TASK_TREE_REL}")
            else:
                branch_lines.extend(f"  - {n}" for n in nodes)
    sections.append(("main에 머지되지 않은 브랜치와 그 진행 노드", branch_lines))

    merges = recent_merges(root, args.merges, args.no_fetch) if main_ok else None
    title = f"main의 최근 머지 {args.merges}건이 바꾼 문서"
    sections.append((title, merge_lines(merges) if merges is not None else failed("main의 최근 머지 조회")))
    if audit is not None:
        sections.insert(audit_at, ("형식 감사", parse_audit(*audit.result(), cwd_prefix(root))))
    return render(sections, root)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())

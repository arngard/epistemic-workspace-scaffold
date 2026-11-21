"""워크스페이스 설치 체계의 공용 모듈 (git 의존).

설치 명세를 읽고, 항목 해시와 적용 상태를 다루며, 항목을 점검하고 적용한다.
명령줄은 setup.py, 세션 시작 요약 연결은 session_brief.py가 이 모듈을 쓴다.
규범(범위, 갱신 흐름, 처음 설치)의 정본은 AGENTS/epistemic-rules/workspace-setup.md다.

명세: JSON 배열 파일. 스캐폴드 공통 항목은 이 도구 폴더의 setup-items.json,
자손 항목은 레포 루트의 AGENTS/setup/*.json(상류는 이 폴더를 출고하지 않는다).
항목의 키:
    id      레포 안에서 유일한 이름(필수)
    title   갱신 알림과 동의 요청에 보이는 한 줄(필수)
    scope   적용 해시를 두는 자리. clone(그 클론의 git 설정) 또는 machine(홈 상태 파일)
    kind    적용 유형(KINDS). 모르는 유형은 그 항목만 "도구가 명세보다 낡았다"로 알린다
    os      적용할 OS 목록(windows, macos, linux). 없으면 모두
    when    적용 조건. {"command": "<이름>"}이면 그 명령이 있는 머신에만 적용
    params  유형별 값

판 기준: 명세는 main 판에서 읽는다(작업 브랜치 워크트리에서도 같은 판정이 나오게 하려는
것이다). 명세 파일이 서브모듈 안에 있으면 main이 가리키는 gitlink 커밋에서 읽고, 이 도구
폴더가 루트 밖에 있으면 도구 폴더가 든 레포의 main에서 읽는다.
"""

import hashlib
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

TOOLS_DIR = Path(__file__).resolve().parent
SCAFFOLD_SPEC = TOOLS_DIR / "setup-items.json"
INSTANCE_SPEC_DIR_REL = Path("AGENTS/setup")
KINDS = frozenset({"git-config", "require-command"})
SCOPES = ("clone", "machine")
REQUIRED_KEYS = ("id", "title", "scope", "kind")
ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9-]*$")
STATE_DIR_NAME = ".epistemic"
STATE_FILE = "setup-state.json"
PYTHON_FILE = "python"
CLONE_KEY_PREFIX = "epistemic.setup."
GIT_TIMEOUT = 20
GIT_ENV = dict(os.environ, GIT_TERMINAL_PROMPT="0", GCM_INTERACTIVE="never")


@dataclass(frozen=True)
class Item:
    id: str
    title: str
    scope: str
    kind: str
    os: "tuple[str, ...]"
    when: dict = field(hash=False)
    params: dict = field(hash=False)
    source: str = ""


def git(cwd: Path, *args: str, timeout: float = GIT_TIMEOUT) -> "tuple[int, str]":
    """git을 utf-8로 돌려 (종료 코드, stdout)을 낸다. git이 없거나 시간이 넘으면 (-1, "")."""
    try:
        proc = subprocess.run(
            ["git", "-c", "core.quotePath=false", *args], cwd=cwd,
            capture_output=True, encoding="utf-8", errors="replace",
            stdin=subprocess.DEVNULL, env=GIT_ENV, timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired):
        return -1, ""
    return proc.returncode, proc.stdout


def toplevel(path: Path) -> "Path | None":
    code, out = git(path, "rev-parse", "--show-toplevel")
    return Path(out.strip()).resolve() if code == 0 and out.strip() else None


def submodule_paths(root: Path) -> "list[str]":
    """루트의 .gitmodules에 적힌 서브모듈 경로(POSIX)."""
    if not (root / ".gitmodules").is_file():
        return []
    code, out = git(root, "config", "--file", ".gitmodules", "--get-regexp", r"^submodule\..*\.path$")
    if code != 0:
        return []
    return [line.split(" ", 1)[1].strip() for line in out.splitlines() if " " in line]


def read_at_ref(root: Path, path: Path, ref: str = "main") -> "tuple[str | None, str]":
    """path 파일의 ref 판 내용과 그 루트 상대 경로. 읽지 못하면 (None, 경로).

    path가 루트 밖이면 path가 든 레포의 ref에서, 서브모듈 안이면 ref가 가리키는
    gitlink 커밋에서 읽는다.
    """
    path = path.resolve()
    try:
        rel = path.relative_to(root).as_posix()
    except ValueError:
        top = toplevel(path.parent)
        if top is None:
            return None, path.as_posix()
        text, _ = read_at_ref(top, path, ref)
        return text, path.as_posix()
    for sub in submodule_paths(root):
        if rel.startswith(sub + "/"):
            code, out = git(root, "ls-tree", ref, sub)
            parts = out.split()
            if code != 0 or len(parts) < 3 or parts[1] != "commit":
                return None, rel
            code, text = git(root / sub, "show", f"{parts[2]}:{rel[len(sub) + 1:]}")
            return (text if code == 0 else None), rel
    code, text = git(root, "show", f"{ref}:{rel}")
    return (text if code == 0 else None), rel


def parse_spec(text: str, source: str) -> "tuple[list[Item], list[str]]":
    """명세 JSON을 항목 목록으로 읽는다. 형식이 어긋난 항목은 실패 줄로 낸다."""
    try:
        data = json.loads(text)
    except ValueError as exc:
        return [], [f"{source}: JSON을 읽지 못했다({exc.msg})"]
    if not isinstance(data, list):
        return [], [f"{source}: 명세는 항목 배열이어야 한다"]
    items, errors = [], []
    for n, raw in enumerate(data):
        if not isinstance(raw, dict) or not all(isinstance(raw.get(k), str) and raw.get(k) for k in REQUIRED_KEYS):
            errors.append(f"{source}: {n}번째 항목에 {', '.join(REQUIRED_KEYS)} 가운데 빠진 것이 있다")
            continue
        if not ID_RE.match(raw["id"]):
            errors.append(f"{source}: 항목 id {raw['id']}는 영문자로 시작하고 영숫자와 하이픈만 쓴다(git 설정 키로 쓰기 때문이다)")
            continue
        if raw["scope"] not in SCOPES:
            errors.append(f"{source}: 항목 {raw['id']}의 scope는 clone 또는 machine이어야 한다")
            continue
        items.append(Item(
            id=raw["id"], title=raw["title"], scope=raw["scope"], kind=raw["kind"],
            os=tuple(raw.get("os") or ()), when=dict(raw.get("when") or {}),
            params=dict(raw.get("params") or {}), source=source,
        ))
    return items, errors


def instance_spec_paths(root: Path, ref: str = "main") -> "list[Path] | None":
    """ref 판에 있는 자손 명세 파일 목록. ref를 읽지 못하면 None."""
    code, _ = git(root, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}")
    if code != 0:
        return None
    code, out = git(root, "ls-tree", "--name-only", ref, INSTANCE_SPEC_DIR_REL.as_posix() + "/")
    if code != 0:
        return []
    return [root / line for line in out.splitlines() if line.endswith(".json")]


def load_items(root: Path, ref: str = "main") -> "tuple[list[Item], list[str]]":
    """스캐폴드 항목과 자손 항목을 ref 판에서 읽어 합친다. 두 번째 값은 실패 줄 목록."""
    root = root.resolve()
    instance = instance_spec_paths(root, ref)
    if instance is None:
        return [], [f"로컬 {ref} 브랜치가 없어 설치 명세를 읽지 못했다"]
    items, errors, seen = [], [], {}
    for path in [SCAFFOLD_SPEC, *instance]:
        text, rel = read_at_ref(root, path, ref)
        if text is None:
            errors.append(f"{rel}: {ref} 판에서 읽지 못했다")
            continue
        parsed, errs = parse_spec(text, rel)
        errors += errs
        for item in parsed:
            if item.id in seen:
                errors.append(f"항목 id {item.id}가 {seen[item.id]}와 {rel}에 함께 있다. 뒤의 것은 버린다")
                continue
            seen[item.id] = rel
            items.append(item)
    return items, errors


def item_hash(item: Item) -> str:
    """항목 내용(출처 경로 제외)의 정규화된 JSON sha256."""
    body = {
        "id": item.id, "title": item.title, "scope": item.scope, "kind": item.kind,
        "os": list(item.os), "when": item.when, "params": item.params,
    }
    data = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def home_dir() -> Path:
    """설치 상태의 홈. 환경 변수 EPISTEMIC_HOME이 있으면 그 값, 없으면 Path.home().

    세션 시작 훅도 같은 규칙(EPISTEMIC_HOME, 없으면 USERPROFILE, 없으면 HOME)을 쓴다.
    """
    value = os.environ.get("EPISTEMIC_HOME")
    return Path(value) if value else Path.home()


def state_dir() -> Path:
    return home_dir() / STATE_DIR_NAME


def read_python_command() -> "str | None":
    """머신별 Python 실행 명령 파일의 첫 줄. 공백으로만 나눠 쓰며 백슬래시를 해석하지 않는다."""
    try:
        lines = (state_dir() / PYTHON_FILE).read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    first = lines[0].strip() if lines else ""
    return first or None


def repo_identifier(root: Path) -> str:
    """머신 상태 파일에서 레포를 가르는 이름. origin URL을 정규화하고, 없으면 주 레포 폴더 이름."""
    code, out = git(root, "remote", "get-url", "origin")
    url = out.strip()
    if code == 0 and url:
        url = re.sub(r"^[a-z+]+://", "", url)
        url = re.sub(r"^[^@/]+@", "", url)
        url = re.sub(r"^([^/:]+):(?!\d+/)", r"\1/", url)
        url = re.sub(r"\.git/?$", "", url.rstrip("/"))
        return url.lower()
    code, out = git(root, "rev-parse", "--git-common-dir")
    if code == 0 and out.strip():
        common = Path(out.strip())
        common = (common if common.is_absolute() else root / common).resolve()
        if common.name == ".git":
            return common.parent.name
    return root.resolve().name


def _read_state() -> "dict | None":
    """머신 상태 파일. 없으면 빈 dict, 깨졌으면 None."""
    path = state_dir() / STATE_FILE
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    try:
        data = json.loads(text)
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def _write_state(data: dict) -> bool:
    folder = state_dir()
    try:
        folder.mkdir(parents=True, exist_ok=True)
        tmp = folder / (STATE_FILE + ".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(tmp, folder / STATE_FILE)
    except OSError:
        return False
    return True


def applied_hash(root: Path, item: Item) -> "str | None":
    """마지막으로 적용하거나 기록한 명세 해시. 없거나 읽지 못하면 None."""
    if item.scope == "clone":
        code, out = git(root, "config", "--local", "--get", CLONE_KEY_PREFIX + item.id)
        return out.strip() or None if code == 0 else None
    state = _read_state() or {}
    entry = state.get(repo_identifier(root), {}).get(item.id)
    return entry.get("spec") if isinstance(entry, dict) else None


def record_applied(root: Path, item: Item, spec_hash: str) -> bool:
    """적용 해시를 범위의 자리에 기록한다. 기록하지 못하면 False(호출자는 미적용으로 둔다)."""
    if item.scope == "clone":
        code, _ = git(root, "config", "--local", CLONE_KEY_PREFIX + item.id, spec_hash)
        return code == 0
    state = _read_state()
    if state is None:
        broken = state_dir() / STATE_FILE
        try:
            os.replace(broken, broken.with_name(STATE_FILE + ".broken"))
        except OSError:
            return False
        state = {}
    state.setdefault(repo_identifier(root), {})[item.id] = {"spec": spec_hash}
    return _write_state(state)


def current_os() -> str:
    if sys.platform.startswith("win"):
        return "windows"
    if sys.platform == "darwin":
        return "macos"
    return "linux"


def applicable(item: Item, os_name: str, has_command: "Callable[[str], bool]") -> bool:
    """이 머신에 적용할 항목인가(os 필터와 when 조건)."""
    if item.os and os_name not in item.os:
        return False
    command = item.when.get("command")
    return not command or has_command(command)

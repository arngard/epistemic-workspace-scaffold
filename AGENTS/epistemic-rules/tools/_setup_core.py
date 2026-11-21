"""워크스페이스 설치 체계의 공용 모듈 (git 의존).

설치 명세를 읽고, 항목을 점검하고 적용한다. 상태를 저장하지 않는다: 판정은 매번 항목의
실제 점검으로 하고, 레포 밖에 파일을 만들지 않으며, git 설정에는 apply가 적용하는 항목
값만 쓴다. 명령줄은 setup.py, 세션 시작 요약 연결은 session_brief.py가 이 모듈을 쓴다.
규범(갱신 흐름, 처음 설치)의 정본은 AGENTS/epistemic-rules/workspace-setup.md다.

명세: JSON 배열 파일. 스캐폴드 공통 항목은 이 도구 폴더의 setup-items.json,
자손 항목은 레포 루트의 AGENTS/setup/*.json(상류는 이 폴더를 출고하지 않는다).
항목의 키(목록에 없는 키는 무시한다):
    id      레포 안에서 유일한 이름(필수). 영문자로 시작하고 영숫자와 하이픈만 쓴다
    title   갱신 알림과 동의 요청에 보이는 한 줄(필수)
    kind    적용 유형(KINDS). 모르는 유형은 그 항목만 "도구가 명세보다 낡았다"로 알린다
    os      적용할 OS 목록(windows, macos, linux). 없으면 모두
    when    적용 조건. {"command": "<이름>"}이면 그 명령이 있는 머신에만 적용
    params  유형별 값

유형:
    git-config       params.key의 클론 git 설정(--local)이 params.value와 같은가를 점검하고,
                     적용은 그 값을 쓴다. 값의 자리 표시 {tools}는 이 도구 폴더의 루트 상대
                     POSIX 경로(루트 밖이면 절대 경로)로 푼다
    require-command  params.candidates를 순서대로 params.args(기본 --version)로 실행해,
                     실행되고 params.min_version 이상인 것이 있는가를 점검한다. 바꾸지 않는다

판 기준: 명세는 main 판에서 읽는다(작업 브랜치 워크트리에서도 같은 판정이 나오게 하려는
것이다). 명세 파일이 서브모듈 안에 있으면 main이 가리키는 gitlink 커밋에서 읽고, 이 도구
폴더가 루트 밖에 있으면 도구 폴더가 든 레포의 main에서 읽는다.
"""

import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

TOOLS_DIR = Path(__file__).resolve().parent
SCAFFOLD_SPEC = TOOLS_DIR / "setup-items.json"
INSTANCE_SPEC_DIR_REL = Path("AGENTS/setup")
KINDS = frozenset({"git-config", "require-command"})
REQUIRED_KEYS = ("id", "title", "kind")
ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9-]*$")
GIT_TIMEOUT = 20


@dataclass(frozen=True)
class Item:
    id: str
    title: str
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
            capture_output=True, encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL,
            env=dict(os.environ, GIT_TERMINAL_PROMPT="0", GCM_INTERACTIVE="never"), timeout=timeout,
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


def main_module_store(root: Path, sub: str) -> "Path | None":
    """서브모듈 sub의 주 워크트리 쪽 모듈 저장소 경로. 없으면 None."""
    code, out = git(root, "rev-parse", "--git-common-dir")
    if code != 0 or not out.strip():
        return None
    common = Path(out.strip())
    common = (common if common.is_absolute() else root / common).resolve()
    code, out = git(root, "config", "--file", ".gitmodules", "--get-regexp", r"^submodule\..*\.path$")
    name = sub
    for line in out.splitlines():
        key, _, value = line.partition(" ")
        if value.strip() == sub:
            name = key[len("submodule."):-len(".path")]
    store = common / "modules" / name
    return store if store.is_dir() else None


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
            inner = rel[len(sub) + 1:]
            code, text = git(root / sub, "show", f"{parts[2]}:{inner}")
            if code != 0:
                # 링크된 워크트리는 서브모듈 객체 저장소를 따로 둔다. main이 가리키는 커밋이
                # 그 저장소에 없으면 주 워크트리의 모듈 저장소(<공용 git 폴더>/modules/<이름>)에서 읽는다.
                store = main_module_store(root, sub)
                if store is not None:
                    code, text = git(root, f"--git-dir={store}", "show", f"{parts[2]}:{inner}")
            if code != 0:
                return None, f"{rel}(서브모듈 {sub}에 {ref}가 가리키는 커밋 {parts[2][:7]}이 없다. git submodule update로 받는다)"
            return text, rel
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
            errors.append(f"{source}: 항목 id {raw['id']}는 영문자로 시작하고 영숫자와 하이픈만 쓴다")
            continue
        bad = [k for k, t in (("when", dict), ("params", dict), ("os", list)) if k in raw and not isinstance(raw[k], t)]
        if bad:
            errors.append(f"{source}: 항목 {raw['id']}의 {', '.join(bad)} 형식이 어긋났다(when, params는 객체, os는 배열)")
            continue
        items.append(Item(
            id=raw["id"], title=raw["title"], kind=raw["kind"],
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
    code, _ = git(root, "rev-parse", "--git-dir")
    if code == -1:
        return [], ["git을 실행하지 못해(설치되지 않았거나 시간 초과) 설치 명세를 읽지 못했다"]
    if code != 0:
        return [], [f"{root}가 git 레포가 아니어서 설치 명세를 읽지 못했다"]
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


@dataclass
class CheckResult:
    ok: bool
    detail: str


TOOL_TOO_OLD = "도구가 명세보다 낡았다"
VERSION_RE = re.compile(r"\d+\.\d+(?:\.\d+)?")
COMMAND_TIMEOUT = 10


def resolve(value: str, root: Path) -> str:
    """자리 표시 {tools}를 도구 폴더의 루트 상대 POSIX 경로(루트 밖이면 절대 경로)로 푼다."""
    if "{tools}" in value:
        try:
            tools = TOOLS_DIR.resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            tools = TOOLS_DIR.resolve().as_posix()
        value = value.replace("{tools}", tools)
    return value


def candidate_commands(item: Item, root: Path) -> "list[str]":
    """require-command 항목의 후보 명령(자리 표시를 푼 것, 빈 후보는 뺀다)."""
    resolved = (resolve(str(c), root) for c in item.params.get("candidates", []))
    return [c for c in resolved if c.strip()]


def _version_tuple(text: str) -> "tuple[int, ...]":
    return tuple(int(p) for p in text.split("."))


def _run_version(command: str, args: "list[str]") -> "str | None":
    """명령을 실행해 출력에서 처음 나오는 버전 문자열. 실행할 수 없으면 None.

    명령은 공백으로만 나눈다(백슬래시와 따옴표를 해석하지 않는다).
    """
    try:
        proc = subprocess.run(
            [*command.split(), *args], capture_output=True, encoding="utf-8",
            errors="replace", stdin=subprocess.DEVNULL, timeout=COMMAND_TIMEOUT,
        )
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return None
    if proc.returncode != 0:
        return None
    match = VERSION_RE.search(proc.stdout + proc.stderr)
    return match.group(0) if match else ""


def current_config(root: Path, key: str) -> "str | None":
    code, out = git(root, "config", "--local", "--get", key)
    return out.strip() if code == 0 else None


def check_item(root: Path, item: Item) -> CheckResult:
    """항목의 실제 상태가 명세와 맞는가."""
    if item.kind not in KINDS:
        return CheckResult(False, f"{TOOL_TOO_OLD}: 모르는 유형 {item.kind}")
    if item.kind == "git-config":
        key, value = item.params.get("key", ""), resolve(str(item.params.get("value", "")), root)
        current = current_config(root, key)
        if current == value:
            return CheckResult(True, f"{key} = {value}")
        return CheckResult(False, f"{key}: 지금 {current if current is not None else '(없음)'}, 명세 {value}")
    found = []
    minimum = item.params.get("min_version")
    if minimum and not re.fullmatch(r"\d+(\.\d+)*", str(minimum)):
        return CheckResult(False, f"명세 오류: min_version {minimum!r}는 숫자와 점으로만 쓴다")
    minimum = str(minimum) if minimum else None
    for command in candidate_commands(item, root):
        version = _run_version(command, list(item.params.get("args", ["--version"])))
        if version is None:
            continue
        if not minimum or (version and _version_tuple(version) >= _version_tuple(minimum)):
            return CheckResult(True, f"{command} ({version or '버전 미상'})")
        found.append(f"{command} {version or '버전 미상'}")
    need = f" {minimum} 이상" if minimum else ""
    seen = f" 찾은 것: {', '.join(found)}." if found else ""
    return CheckResult(False, f"실행할 수 있는{need} 명령을 찾지 못했다.{seen} workspace-setup.md \"처음 설치\"를 본다")


def apply_item(root: Path, item: Item) -> CheckResult:
    """항목을 적용한다. require-command는 바꾸지 않고 점검 결과만 낸다."""
    if item.kind not in KINDS:
        return CheckResult(False, f"{TOOL_TOO_OLD}: 모르는 유형 {item.kind}")
    if item.kind == "git-config":
        key, value = item.params.get("key", ""), resolve(str(item.params.get("value", "")), root)
        code, _ = git(root, "config", "--local", key, value)
        return CheckResult(code == 0, f"{key} = {value}" if code == 0 else f"{key} 설정 실패")
    return check_item(root, item)


# 유형별로 적용이 무엇을 바꾸는가. clone은 그 클론의 git 설정, none은 바꾸는 것 없음.
KIND_CHANGES = {"git-config": "clone", "require-command": "none"}
CHANGES_LABEL = {"clone": "클론", "none": "바꾸는 것 없음"}


@dataclass
class Entry:
    item: Item
    state: str  # ok, pending, tool-too-old, not-applicable
    detail: str


def changes(item: Item) -> str:
    return KIND_CHANGES.get(item.kind, "none")


def targets(item: Item, root: Path) -> "list[str]":
    """적용이 바꾸거나 확인하는 대상. 동의 요청에 그대로 보인다."""
    if item.kind == "git-config":
        key = item.params.get("key", "")
        current = current_config(root, key)
        value = resolve(str(item.params.get("value", "")), root)
        return [f"{key}: {current if current is not None else '(없음)'} -> {value}"]
    if item.kind == "require-command":
        return candidate_commands(item, root)
    return []


def status(root: Path) -> "tuple[list[Entry], list[str]]":
    """항목마다 실제 점검을 돌려 상태를 정한다. 통과하면 ok, 아니면 pending.

    두 번째 값은 명세의 실패 줄 목록이다. 아무것도 쓰지 않는다.
    """
    items, errors = load_items(root)
    entries = []
    os_name = current_os()
    for item in items:
        if not applicable(item, os_name, lambda c: shutil.which(c) is not None):
            entries.append(Entry(item, "not-applicable", "이 머신에 해당하지 않는다"))
            continue
        if item.kind not in KINDS:
            entries.append(Entry(item, "tool-too-old", f"{TOOL_TOO_OLD}: 모르는 유형 {item.kind}"))
            continue
        try:
            result = check_item(root, item)
        except Exception as exc:  # noqa: BLE001 - 항목 하나의 실패를 그 항목에 가둔다
            entries.append(Entry(item, "pending", f"점검 실패({type(exc).__name__})"))
            continue
        entries.append(Entry(item, "ok" if result.ok else "pending", result.detail))
    return entries, errors


def status_lines(root: Path) -> "list[str]":
    """세션 시작 요약의 환경 갱신 절 줄. 예외는 수집 실패 한 줄로 바꾼다."""
    try:
        entries, errors = status(root)
    except Exception as exc:  # noqa: BLE001 - 요약이 세션 시작을 막지 않게 한다
        return [f"수집 실패: 환경 갱신 판정 중 오류({type(exc).__name__}). setup.py check로 직접 본다."]
    if not entries and errors:
        return [f"수집 실패: {errors[0]}"] + [f"명세 오류: {e}" for e in errors[1:]]
    lines = []
    pending = [e.item.id for e in entries if e.state == "pending"]
    if pending:
        lines.append(f'미적용 갱신 {len(pending)}건: {", ".join(pending)}. workspace-setup.md "갱신 흐름"대로 사용자에게 알리고 동의를 받는다.')
    old = [e.item.id for e in entries if e.state == "tool-too-old"]
    if old:
        lines.append(f"{TOOL_TOO_OLD}(이 브랜치의 설치기가 모르는 유형): {', '.join(old)}")
    lines += [f"명세 오류: {e}" for e in errors]
    return lines or ["환경 갱신 없음"]


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

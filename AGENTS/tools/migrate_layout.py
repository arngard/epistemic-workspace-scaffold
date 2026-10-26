#!/usr/bin/env python3
"""폴더 구조 이전 도구 - 경로 대응과 텍스트 변환.

옛 레이아웃(_docs/_worklog 등)의 경로를 새 레이아웃(worklog 등)으로 대응시키고,
마크다운 링크와 본문 언급을 새 경로로 바꾸는 순수 함수를 담는다.
모든 경로 인자는 레포 루트 기준 POSIX 상대 경로다. import 시 부수 효과는 없다.
migrate()는 git 추적 파일을 옮기고 추적 md 파일의 본문을 바꾸는 실행부다.
추적되지 않는 내용은 옮기지 않되, 예외로 추적 안 되는 _tmp/ 폴더는 .tmp/가 없을 때
파일 시스템 이름 바꾸기로 옮긴다. .tmp/가 이미 있으면 ("_tmp", ".tmp")를 충돌로 보고한다.
대상 경로가 이미 있어(추적 여부 무관) 건너뛴 이동은 Report.conflicts에 모으고, 옛 파일은 그대로 둔다.
상류 머지로 이미 새 위치에 와 있지만 본문 링크가 옛 위치 기준인 파일은, 대상이 실제로 있을 때만
옛 위치 기준으로 다시 계산한다. 명령행은 conflicts가 있으면 종료 코드 1, 없으면 0이다.
"""

import argparse
import os
import posixpath
import re
import subprocess
import sys
import urllib.parse
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

# 옛 경로 -> 새 경로. 긴 접두어를 먼저 적용한다.
PATH_MAP = [
    ("_docs/_worklog", "worklog"),
    ("_docs/_ontology", "epistemic-structure/ontology"),
    ("_docs/_knowledge", "epistemic-structure/knowledge"),
    ("_docs/_strategy", "epistemic-structure/strategy"),
    ("_docs/_architecture", "epistemic-structure/architecture"),
    ("_docs/AGENTS.md", "epistemic-structure/AGENTS.md"),
    ("_reference", "reference"),
    ("_implementation", "implementation"),
    ("_tmp", ".tmp"),
]

# 본문에서 `_docs/` 없이 쓰인 옛 폴더 이름 -> 새 이름.
_BARE_MAP = {
    "_worklog": "worklog",
    "_ontology": "ontology",
    "_knowledge": "knowledge",
    "_strategy": "strategy",
    "_architecture": "architecture",
    "_reference": "reference",
    "_implementation": "implementation",
    "_tmp": ".tmp",
}

_BARE_NAMES = "|".join(n[1:] for n in _BARE_MAP)
_NOT_IDENT_BEFORE = r"(?<![A-Za-z0-9_])"
_NOT_IDENT_AFTER = r"(?![A-Za-z0-9_])"

# 건드리지 않을 구간(링크 대상, URL)과 바꿀 언급을 한 정규식으로 묶어 앞에서부터 훑는다.
_MENTION_RE = re.compile(
    r"(?P<keep>\]\([^)]*\)|(?:https?://|mailto:)[^\s)>\]]+)"
    r"|(?P<hit>" + _NOT_IDENT_BEFORE
    + r"(?:_docs/(?:_(?:" + _BARE_NAMES + r")|AGENTS\.md)|_(?:" + _BARE_NAMES + r"))"
    + _NOT_IDENT_AFTER + r")"
)
# 바꾸고 남은 옛 경로 표지. 보고 대상 판정에 쓴다.
_STALE_RE = re.compile(_NOT_IDENT_BEFORE + r"_(?:docs|" + _BARE_NAMES + r")" + _NOT_IDENT_AFTER)
_KEEP_RE = re.compile(r"\]\([^)]*\)|(?:https?://|mailto:)[^\s)>\]]+")
_LINK_RE = re.compile(r"\]\(([^)\s]*)((?:\s+\"[^\"]*\")?)\)")
_SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.\-]*:")


def _inverse_path(rel: str) -> str:
    """새 경로를 옛 경로로 되돌린다. 대응하는 새 경로가 아니면 그대로 돌려준다."""
    for old, new in PATH_MAP:
        if rel == new:
            return old
        if old != "_docs/AGENTS.md" and rel.startswith(new + "/"):
            return old + rel[len(new):]
    return rel


def map_path(rel: str) -> str:
    """옛 경로를 새 경로로 대응시킨다. 대응이 없거나 이미 새 경로면 그대로 돌려준다."""
    for old, new in PATH_MAP:
        if rel == old:
            return new
        if old != "_docs/AGENTS.md" and rel.startswith(old + "/"):
            return new + rel[len(old):]
    return rel


def _rewrite_target(target: str, old_src: str, new_src: str) -> str:
    """링크 대상 하나를 새 위치 기준으로 다시 만든다. 바꿀 수 없으면 그대로 돌려준다."""
    path, sep, frag = target.partition("#")
    if not path or path.startswith("/") or _SCHEME_RE.match(path):
        return target
    decoded = urllib.parse.unquote(path)
    old_dir = posixpath.dirname(old_src)
    resolved = posixpath.normpath(posixpath.join(old_dir, decoded))
    if resolved == ".." or resolved.startswith("../") or resolved.startswith("/"):
        return target
    mapped = map_path(resolved)
    new_dir = posixpath.dirname(new_src)
    if mapped == resolved and new_dir == old_dir:
        return target
    rel = posixpath.relpath(mapped, new_dir or ".")
    if decoded.endswith("/") and not rel.endswith("/"):
        rel += "/"
    return rel.replace(" ", "%20") + sep + frag


def rewrite_links(text: str, old_src: str, new_src: str) -> str:
    """`](대상)` 형식 링크의 대상을 이전 뒤 위치에 맞게 바꾼다.

    호출 규약: old_src는 이 호출 직전에 파일이 실제로 있던 위치, new_src는 이 호출 뒤의 위치다.
    이번 실행에서 옮기지 않은 파일은 old_src == new_src로 넘긴다. 같은 본문에 old_src != new_src로
    두 번 호출하는 것은 규약 밖이다(이미 바뀐 대상을 옛 위치 기준으로 다시 풀기 때문이다).
    외부 주소, 문서 안 앵커, 저장소 밖을 가리키는 대상은 건드리지 않는다.
    `#` 뒤의 절 앵커는 보존한다.
    """
    def repl(m):
        return "](" + _rewrite_target(m.group(1), old_src, new_src) + m.group(2) + ")"
    return _LINK_RE.sub(repl, text)


def _resolve(base_dir: str, target: str) -> Optional[str]:
    """링크 대상을 base_dir 기준 레포 상대 경로로 푼다. 풀 대상이 아니면 None이다."""
    path = target.partition("#")[0]
    if not path or path.startswith("/") or _SCHEME_RE.match(path):
        return None
    p = posixpath.normpath(posixpath.join(base_dir, urllib.parse.unquote(path)))
    if p == ".." or p.startswith("../"):
        return None
    return p


def _repair_links(text: str, cur: str, exists) -> str:
    """새 위치에 있으나 옛 위치 기준으로 쓰인 링크를 고친다.

    cur가 대응표의 새 경로일 때만 동작한다. 현재 위치 기준으로 대상이 없고,
    옛 위치(_inverse_path(cur)) 기준으로 풀어 대응시킨 경로가 exists(경로)로 있으면
    그 경로로 다시 계산한다. 고친 뒤에는 대상이 있으므로 재실행해도 바뀌지 않는다.
    """
    old = _inverse_path(cur)
    if old == cur:
        return text
    cur_dir = posixpath.dirname(cur)

    def repl(m):
        target = m.group(1)
        here = _resolve(cur_dir, target)
        if here is None or exists(here):
            return m.group(0)
        cand = _rewrite_target(target, old, cur)
        there = _resolve(cur_dir, cand)
        if cand == target or there is None or not exists(there):
            return m.group(0)
        return "](" + cand + m.group(2) + ")"
    return _LINK_RE.sub(repl, text)


def _stale_link_lines(text: str) -> List[Tuple[int, str]]:
    """링크 대상(외부 주소 제외)에 옛 경로 표지가 남은 줄을 돌려준다."""
    out = []
    for no, line in enumerate(text.splitlines(), start=1):
        for m in _LINK_RE.finditer(line):
            path = m.group(1).partition("#")[0]
            if _SCHEME_RE.match(path):
                continue
            if _STALE_RE.search(urllib.parse.unquote(path)):
                out.append((no, line))
                break
    return out


def _has_stale(line: str) -> bool:
    """링크 대상과 URL을 뺀 나머지에 옛 경로 표지가 남았는지 판정한다."""
    return _STALE_RE.search(_KEEP_RE.sub("", line)) is not None


def _mention_repl(m):
    if m.group("keep") is not None:
        return m.group(0)
    hit = m.group("hit")
    if hit.startswith("_docs/"):
        return map_path(hit)
    return _BARE_MAP[hit]


def rewrite_mentions(text: str) -> Tuple[str, List[Tuple[int, str]]]:
    """본문에 언급된 옛 경로를 새 경로로 바꾼다.

    코드 펜스 안은 바꾸지 않고, 옛 경로가 든 줄을 보고 목록에 넣는다. 링크 대상과 URL,
    식별자 안에 든 문자열은 바꾸지 않는다. 바꾼 뒤에도 `_docs`가 남은 줄은 보고한다.
    반환값은 (바꾼 본문, [(줄 번호, 줄)])이다.
    """
    out = []
    report = []
    in_fence = False
    for no, line in enumerate(text.splitlines(keepends=True), start=1):
        body = line.rstrip("\r\n")
        if body.lstrip().startswith(("```", "~~~")):
            in_fence = not in_fence
            out.append(line)
            continue
        if in_fence:
            if _has_stale(body):
                report.append((no, body))
            out.append(line)
            continue
        new_line = _MENTION_RE.sub(_mention_repl, line)
        if _has_stale(new_line.rstrip("\r\n")):
            report.append((no, body))
        out.append(new_line)
    return "".join(out), report


@dataclass
class Report:
    """이전 결과. 경로는 레포 루트 기준 POSIX 상대 경로다."""

    moved: List[Tuple[str, str]] = field(default_factory=list)
    rewritten: List[str] = field(default_factory=list)
    residual: List[Tuple[str, int, str]] = field(default_factory=list)
    conflicts: List[Tuple[str, str]] = field(default_factory=list)  # (옛 경로, 새 경로) 대상이 이미 있어 건너뜀


def _tracked(root: Path) -> List[str]:
    out = subprocess.run(["git", "ls-files", "-z"], cwd=str(root), check=True, stdout=subprocess.PIPE).stdout
    # 머지 충돌 중인 파일은 단계별로 여러 번 나오므로 순서를 지켜 한 번만 남긴다.
    return list(dict.fromkeys(p for p in out.decode("utf-8").split("\0") if p))


def _prune_empty_dirs(root: Path, rel_dir: str) -> None:
    """옮긴 파일의 옛 상위 폴더가 비었으면 루트 직전까지 거슬러 올라가며 지운다."""
    cur = rel_dir
    while cur and cur != ".":
        d = root / cur
        try:
            d.rmdir()
        except OSError:
            return
        cur = posixpath.dirname(cur)


_OLD_TOPS = ["_docs"] + [old for old, _ in PATH_MAP if "/" not in old]
_UNMAPPED_NOTE = "옮길 대응이 없는 옛 경로 파일"


def _sweep_old_dirs(root: Path) -> None:
    """옛 최상위 폴더 아래의 빈 폴더를 아래에서부터 지운다. 파일이 남은 폴더는 둔다."""
    for top in _OLD_TOPS:
        base = root / top
        if not base.is_dir():
            continue
        for dirpath, _dirs, _files in os.walk(str(base), topdown=False):
            try:
                os.rmdir(dirpath)
            except OSError:
                pass


def _move_untracked_tmp(root: Path, present, plan, report: Report, dry_run: bool) -> None:
    """추적 안 되는 파일이 든 _tmp/를 .tmp/로 이름 바꾼다. .tmp/가 있으면 충돌로 보고한다."""
    base = root / "_tmp"
    if not base.is_dir():
        return
    untracked = False
    for dirpath, _dirs, files in os.walk(str(base)):
        for name in files:
            rel = Path(dirpath, name).relative_to(root).as_posix()
            if rel not in present:
                untracked = True
    if not untracked:
        return
    dest = root / ".tmp"
    taken = any(v.startswith(".tmp/") for v in plan.values())
    if os.path.lexists(str(dest)) or taken:
        report.conflicts.append(("_tmp", ".tmp"))
        return
    report.moved.append(("_tmp", ".tmp"))
    if not dry_run:
        os.rename(str(base), str(dest))


def migrate(root: Path, dry_run: bool = False) -> Report:
    """root의 추적 파일을 새 레이아웃으로 옮기고 추적 md 파일의 링크와 언급을 바꾼다.

    각 md 파일의 본문은 (이번 실행 전 위치, 현재 위치)로 정확히 한 번만 변환하므로 재실행은 변화가 없다.
    이미 새 위치에 있던 파일은 그 뒤 _repair_links로 옛 위치 기준 링크를 고친다. 대상 존재
    판정은 이전 뒤 추적 파일 집합(dry_run이 아니면 파일 시스템도)으로 하므로 고친 링크는 재실행에서
    그대로다. 대응이 없는 옛 최상위 폴더의 추적 파일과 링크 대상에 옛 경로가 남은 줄은 residual로 보고한다.
    dry_run이면 파일 시스템과 색인을 건드리지 않고 같은 보고를 돌려준다.
    """
    root = Path(root)
    report = Report()
    tracked = _tracked(root)
    present = set(tracked)
    # 이번 실행 전 위치 -> 이번 실행 뒤 위치
    plan = {}
    for rel in tracked:
        new = map_path(rel)
        if new == rel:
            if rel.split("/", 1)[0] in _OLD_TOPS:
                report.residual.append((rel, 0, _UNMAPPED_NOTE))
            continue
        if new in present or os.path.lexists(str(root / new)):
            report.conflicts.append((rel, new))
        else:
            plan[rel] = new
    after = (present - set(plan)) | set(plan.values())
    after_dirs = set()
    for p in after:
        d = posixpath.dirname(p)
        while d and d not in after_dirs:
            after_dirs.add(d)
            d = posixpath.dirname(d)

    def exists(p):
        if p == "." or p in after or p in after_dirs:
            return True
        return not dry_run and (root / p).exists()

    for old, new in plan.items():
        report.moved.append((old, new))
        if dry_run:
            continue
        (root / new).parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "mv", old, new], cwd=str(root), check=True)
        _prune_empty_dirs(root, posixpath.dirname(old))
    if not dry_run:
        _sweep_old_dirs(root)
    _move_untracked_tmp(root, present, plan, report, dry_run)
    for old in tracked:
        new = plan.get(old, old)
        if not new.endswith(".md"):
            continue
        read_from = old if dry_run else new
        with open(str(root / read_from), encoding="utf-8", newline="") as f:
            text = f.read()
        linked = rewrite_links(text, old, new)
        if old == new:
            linked = _repair_links(linked, new, exists)
        out, residual = rewrite_mentions(linked)
        seen = {no for no, _ in residual}
        residual += [r for r in _stale_link_lines(out) if r[0] not in seen]
        residual.sort()
        report.residual.extend((new, no, line) for no, line in residual)
        if out != text:
            report.rewritten.append(new)
            if not dry_run:
                with open(str(root / new), "w", encoding="utf-8", newline="") as f:
                    f.write(out)
    return report


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="폴더 구조를 새 레이아웃으로 이전한다.")
    ap.add_argument("root", help="이전할 git 저장소 루트")
    ap.add_argument("--dry-run", action="store_true", help="파일을 바꾸지 않고 보고만 한다")
    args = ap.parse_args(argv)
    rep = migrate(Path(args.root), dry_run=args.dry_run)
    print("옮긴 파일 (%d):" % len(rep.moved))
    for old, new in rep.moved:
        print("  %s -> %s" % (old, new))
    print("본문을 바꾼 파일 (%d):" % len(rep.rewritten))
    for p in rep.rewritten:
        print("  %s" % p)
    print("옛 경로가 남은 줄 (%d):" % len(rep.residual))
    for p, no, line in rep.residual:
        print("  %s:%d: %s" % (p, no, line))
    print("대상이 이미 있어 옮기지 못한 파일 (%d):" % len(rep.conflicts))
    for old, new in rep.conflicts:
        print("  %s -> %s" % (old, new))
    return 1 if rep.conflicts else 0


if __name__ == "__main__":
    sys.exit(main())

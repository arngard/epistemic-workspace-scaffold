#!/usr/bin/env python3
"""폴더 구조 이전 도구 - 경로 대응과 텍스트 변환.

옛 레이아웃(_docs/_worklog 등)의 경로를 새 레이아웃(worklog 등)으로 대응시키고,
마크다운 링크와 본문 언급을 새 경로로 바꾸는 순수 함수를 담는다.
모든 경로 인자는 레포 루트 기준 POSIX 상대 경로다. import 시 부수 효과는 없다.
"""

import posixpath
import re
import urllib.parse
from typing import List, Tuple

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

    old_src는 문서의 옛 위치, new_src는 새 위치다. 외부 주소, 문서 안 앵커,
    저장소 밖을 가리키는 대상은 건드리지 않는다. `#` 뒤의 절 앵커는 보존한다.
    """
    def repl(m):
        return "](" + _rewrite_target(m.group(1), old_src, new_src) + m.group(2) + ")"
    return _LINK_RE.sub(repl, text)


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

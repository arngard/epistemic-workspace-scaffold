#!/usr/bin/env python3
"""폴더 구조 이전 도구 - 경로 대응과 텍스트 변환.

옛 레이아웃(_docs/_worklog 등)의 경로를 새 레이아웃(worklog 등)으로 대응시키고,
마크다운 링크와 본문 언급을 새 경로로 바꾸는 순수 함수를 담는다.
모든 경로 인자는 레포 루트 기준 POSIX 상대 경로다. import 시 부수 효과는 없다.
migrate()는 git 추적 파일을 옮기고 추적 md 파일의 본문을 바꾸는 실행부다.
reference/ 아래 자료 파일(사용자가 넣은 원본 자료와 그 사본)은 옮기기만 하고 본문을 바꾸지 않는다.
reference/AGENTS.md, reference/CLAUDE.md, reference/ 직속 색인 쪽 파일, 규범 폴더 reference/AGENTS/
아래는 운영 파일이라 다른 md와 같이 바꾼다. implementation/ 아래 문서도 바꾼다.
추적되지 않는 내용은 옮기지 않되, 예외로 추적 안 되는 _tmp/ 폴더는 .tmp/가 없을 때
파일 시스템 이름 바꾸기로 옮긴다. .tmp/가 이미 있으면 ("_tmp", ".tmp")를 충돌로 보고한다.
대상 경로가 이미 있어(추적 여부 무관) 건너뛴 이동은 Report.conflicts에 모으고, 옛 파일은 그대로 둔다.
상류 머지로 이미 새 위치에 와 있지만 본문 링크가 옛 위치 기준인 파일은, 현재 위치 기준으로 대상이
없거나 저장소 밖을 가리키는 링크를 옛 위치 기준으로 다시 계산하되 고친 대상이 실제로 있을 때만 바꾼다.
명령행은 conflicts나 unconverted가 있으면 종료 코드 1, 없으면 0이다.
링크 변환은 코드 펜스와 인라인 코드 구간 안의 예시 링크를 건드리지 않는다.
reference/AGENTS.md에 "등록된 자료" 절의 표가 있으면 reference/INDEX.yaml(description, status)로
옮기고 그 절을 지운다. 파일 열의 머리 칸 이름은 항목이어도 된다. 추가일 열은 버리고, 상태 칸에 어휘
뒤로 남은 글(derived 링크 등)은 설명 끝에 덧붙인다. 폴더 행은 이름 끝의 /를 남긴다. 읽지 못한 행이
있거나 항목이 든 INDEX.yaml(형식 오류 포함)이 이미 있으면 절을 건드리지 않고 Report.unconverted에
보고한다. 주석과 빈 줄뿐인 INDEX.yaml은 없는 것으로 보고 덮어쓴다.
unconverted가 있으면 명령행 종료 코드도 1이다.

이전 절차: 옛 배치를 가진 저장소가 상류를 머지한 직후 한 번 실행한다.
옛 배치를 가진 적 없는 저장소는 실행하지 않는다.
1. 상류를 머지한다. 흡수할 상류 범위에 골격 폴더를 옮긴 머지가 있으면 그 머지를 먼저 따로
   흡수한 뒤 나머지를 흡수한다. 한 번에 머지하면 git의 이름 변경 추정이 자손 고유 문서와
   바뀐 상류 파일을 잘못 짝지을 수 있다.
2. 충돌을 푼다. 충돌은 파일 단위로 확정한다. 폴더째 git add하면 자손이 지운 상류 파일이
   되살아날 수 있다. reference/AGENTS.md의 충돌은 자손 쪽 자료 표를 남긴 채 풀고,
   표는 다음 단계에서 이 도구가 reference/INDEX.yaml로 옮긴다.
3. 이 도구를 --dry-run으로 돌려 보고를 확인한 뒤 실제로 실행한다.
   보고에 남은 conflicts와 unconverted는 손으로 정리한다.
4. build_index.py로 색인을 다시 만들어 결과를 커밋한다.
5. 커밋 전 훅을 연결한다. 명령은 tools.md "색인 생성 스크립트",
   서브모듈로 품은 저장소의 변형은 folder-index.md "생성과 확인".
"""

import argparse
import os
import posixpath
import re
import subprocess
import sys
import unicodedata
import urllib.parse
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _audit_core import (  # noqa: E402
    DESCRIPTOR_NAME, INDEX_PAGE_RE, NORMS_DIR_NAME, REFERENCE_DIR)
from _index_core import (  # noqa: E402
    REFERENCE_STATUSES, IndexFormatError, load_index_yaml, quote_scalar)

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

# 상류 규범 묶음으로 옮기는 루트 규범. 문서는 정확 일치, 폴더는 접두어로 대응한다.
NORM_DOCS = (
    "agent-roles.md", "agent-tag-format.md", "branch-strategy.md", "coding-guidelines.md",
    "document-temporality.md", "document-units.md", "external-communication.md", "folder-structure.md",
    "how-to-separate-docs-folders.md", "ingest-workflow.md", "instance-specialization.md",
    "original-protection-principle.md", "pr-workflow.md", "session-boundaries.md",
    "submodule-pointer-sync.md", "tool-environment.md", "unit-task-workflow.md", "unit-task.md",
    "why-agents-md-not-conventions-md.md", "why-epistemic-workspace.md", "why-scaffolding-not-single-file.md",
    "working-principles.md", "workspace-and-project-structure.md", "writing-style.md",
)
NORM_DIRS = ("agent-roles", "ingest-workflow", "pr-workflow", "tools", "unit-task", "unit-task-workflow", "writing-style")
PATH_MAP += [("AGENTS/" + n, "AGENTS/epistemic-rules/" + n) for n in NORM_DOCS + NORM_DIRS]
# 폴더 묶음으로 나가는 규범. 앞 대응이 낳은 자리에서 최종 자리로 한 번 더 옮긴다.
PATH_MAP += [
    ("AGENTS/epistemic-rules/coding-guidelines.md",
     "implementation/AGENTS/epistemic-rules/coding-guidelines.md"),
    ("AGENTS/epistemic-rules/ingest-workflow/reference-folder.md",
     "reference/AGENTS/epistemic-rules/reference-folder.md"),
]
# 지워지고 내용이 다른 문서에 합쳐진 규범. 링크만 합쳐진 문서로 돌리고, 합쳐진 문서는
# 그 자리에서 옮겨 온 것이 아니므로 역대응(_inverse_path)에서 뺀다.
MERGED_MAP = [
    ("AGENTS/epistemic-rules/how-to-separate-docs-folders.md",
     "epistemic-structure/AGENTS/epistemic-rules.md"),
]
PATH_MAP += MERGED_MAP

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

# 상류 규범의 옛 루트 경로 언급. 앞 글자가 영숫자, _, ., /, -이면 다른 경로의 일부로 본다.
_NORM_BEFORE = r"(?<![A-Za-z0-9_./-])"
_NORM_RE = (
    _NORM_BEFORE + r"AGENTS/(?:(?:" + "|".join(re.escape(n) for n in NORM_DIRS) + r")/|(?:"
    + "|".join(re.escape(n) for n in NORM_DOCS) + r")(?![A-Za-z0-9_-]))"
)
# 건드리지 않을 구간(링크 대상, URL)과 바꿀 언급을 한 정규식으로 묶어 앞에서부터 훑는다.
_MENTION_RE = re.compile(
    r"(?P<keep>\]\([^)]*\)|(?:https?://|mailto:)[^\s)>\]]+)"
    r"|(?P<hit>" + _NOT_IDENT_BEFORE
    + r"(?:_docs/(?:_(?:" + _BARE_NAMES + r")|AGENTS\.md)|_(?:" + _BARE_NAMES + r"))"
    + _NOT_IDENT_AFTER + r"|" + _NORM_RE + r")"
)
# 바꾸고 남은 옛 경로 표지. 보고 대상 판정에 쓴다.
_STALE_RE = re.compile(_NOT_IDENT_BEFORE + r"_(?:docs|" + _BARE_NAMES + r")" + _NOT_IDENT_AFTER)
_KEEP_RE = re.compile(r"\]\([^)]*\)|(?:https?://|mailto:)[^\s)>\]]+")
_LINK_RE = re.compile(r"\]\(([^)\s]*)((?:\s+\"[^\"]*\")?)\)")
_SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.\-]*:")
_FENCES = ("```", "~~~")
_TICKS_RE = re.compile(r"`+")


def _code_spans(line: str) -> List[Tuple[int, int]]:
    """줄 안 인라인 코드 구간의 (시작, 끝) 목록. 짝이 없는 백틱은 글자로 본다."""
    spans = []
    pos = 0
    while True:
        m = _TICKS_RE.search(line, pos)
        if m is None:
            return spans
        n = len(m.group(0))
        c = m
        while True:
            c = _TICKS_RE.search(line, c.end())
            if c is None or len(c.group(0)) == n:
                break
        if c is None:
            pos = m.end()
        else:
            spans.append((m.start(), c.end()))
            pos = c.end()


def _sub_outside_code(pattern, repl, text: str) -> str:
    """코드 펜스와 인라인 코드 구간 밖에만 pattern.sub(repl)을 적용한다."""
    out = []
    in_fence = False
    for line in text.splitlines(keepends=True):
        if line.lstrip().startswith(_FENCES):
            in_fence = not in_fence
            out.append(line)
            continue
        if in_fence:
            out.append(line)
            continue
        pos = 0
        for start, end in _code_spans(line):
            out.append(pattern.sub(repl, line[pos:start]))
            out.append(line[start:end])
            pos = end
        out.append(pattern.sub(repl, line[pos:]))
    return "".join(out)


def _inverse_path(rel: str) -> str:
    """새 경로를 옛 경로로 되돌린다. 대응하는 새 경로가 아니면 그대로 돌려준다."""
    for old, new in PATH_MAP:
        if (old, new) in MERGED_MAP:
            continue
        if rel == new:
            return old
        if not old.endswith(".md") and rel.startswith(new + "/"):
            return old + rel[len(new):]
    return rel


def _map_once(rel: str) -> str:
    for old, new in PATH_MAP:
        if rel == old:
            return new
        if not old.endswith(".md") and rel.startswith(old + "/"):
            return new + rel[len(old):]
    return rel


def map_path(rel: str) -> str:
    """옛 경로를 새 경로로 대응시킨다. 더 바뀌지 않을 때까지 대응을 거듭 적용한다.

    .md로 끝나는 항목은 정확 일치로만 대응하고, 나머지는 접두어로 대응한다.
    대응이 없거나 이미 새 경로면 그대로 돌려준다.
    """
    for _ in range(len(PATH_MAP) + 1):
        nxt = _map_once(rel)
        if nxt == rel:
            return rel
        rel = nxt
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
    코드 펜스와 인라인 코드 구간 안의 예시 링크도 건드리지 않는다. `#` 뒤의 절 앵커는 보존한다.
    """
    def repl(m):
        return "](" + _rewrite_target(m.group(1), old_src, new_src) + m.group(2) + ")"
    return _sub_outside_code(_LINK_RE, repl, text)


def _resolve(base_dir: str, target: str) -> Optional[str]:
    """링크 대상을 base_dir 기준 레포 상대 경로로 푼다.

    외부 주소, 절대 경로, 빈 대상(앵커만 있는 링크 포함)은 풀 대상이 아니라 None이다.
    저장소 밖을 가리키면 ../로 시작하는 경로를 그대로 돌려주므로 _outside로 가려 쓴다.
    """
    path = target.partition("#")[0]
    if not path or path.startswith("/") or _SCHEME_RE.match(path):
        return None
    return posixpath.normpath(posixpath.join(base_dir, urllib.parse.unquote(path)))


def _outside(rel: str) -> bool:
    """_resolve가 푼 경로가 저장소 밖이면 참."""
    return rel == ".." or rel.startswith("../")


def _repair_links(text: str, cur: str, exists) -> str:
    """새 위치에 있으나 옛 위치 기준으로 쓰인 링크를 고친다.

    cur가 대응표의 새 경로일 때만 동작한다. 현재 위치 기준으로 대상이 없거나 저장소 밖을
    가리키고, 옛 위치(_inverse_path(cur)) 기준으로 풀어 대응시킨 경로가 저장소 안에 있으며
    exists(경로)로 있으면 그 경로로 다시 계산한다. 저장소 밖 경로는 exists에 넘기지 않는다.
    고친 뒤에는 대상이 있으므로 재실행해도 바뀌지 않는다.
    외부 주소, 절대 경로, 빈 대상, 앵커만 있는 링크와 코드 펜스, 인라인 코드 구간 안의 예시
    링크는 건드리지 않는다.
    """
    old = _inverse_path(cur)
    if old == cur:
        return text
    cur_dir = posixpath.dirname(cur)

    def repl(m):
        target = m.group(1)
        here = _resolve(cur_dir, target)
        if here is None or (not _outside(here) and exists(here)):
            return m.group(0)
        cand = _rewrite_target(target, old, cur)
        if cand == target:
            return m.group(0)
        there = _resolve(cur_dir, cand)
        if there is None or _outside(there) or not exists(there):
            return m.group(0)
        return "](" + cand + m.group(2) + ")"
    return _sub_outside_code(_LINK_RE, repl, text)


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
    plain = _KEEP_RE.sub("", line)
    return _STALE_RE.search(plain) is not None or re.search(_NORM_RE, plain) is not None


def _mention_repl(m):
    if m.group("keep") is not None:
        return m.group(0)
    hit = m.group("hit")
    if hit.startswith("AGENTS/"):
        return "AGENTS/epistemic-rules/" + hit[len("AGENTS/"):]
    if hit.startswith("_docs/"):
        return map_path(hit)
    return _BARE_MAP[hit]


def rewrite_mentions(text: str) -> Tuple[str, List[Tuple[int, str]]]:
    """본문에 언급된 옛 경로를 새 경로로 바꾼다.

    코드 펜스 안은 바꾸지 않고, 옛 경로가 든 줄을 보고 목록에 넣는다. 링크 대상과 URL,
    식별자 안에 든 문자열은 바꾸지 않는다. 바꾼 뒤에도 옛 경로가 남은 줄은 보고한다.
    반환값은 (바꾼 본문, [(줄 번호, 줄)])이다.
    """
    out = []
    report = []
    in_fence = False
    for no, line in enumerate(text.splitlines(keepends=True), start=1):
        body = line.rstrip("\r\n")
        if body.lstrip().startswith(_FENCES):
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

REFERENCE_DIR_NAME = "reference"
REFERENCE_DESCRIPTOR = "reference/AGENTS.md"
REFERENCE_INDEX = "reference/INDEX.yaml"
_SECTION_NAME = "등록된 자료"
_SECTION_RE = re.compile(r"^(#{1,6})[ \t]+" + _SECTION_NAME + r"[ \t]*$")
_HEADING_RE = re.compile(r"^(#{1,6})[ \t]")
_EMPTY_NOTE_RE = re.compile(r"^\(아직 등록된 자료 없음\.?\)$")
_KNOWN_COLUMNS = ("파일", "추가일", "설명", "상태")
# 파일 열과 같은 뜻으로 받는 머리 칸 이름. 폴더 단위 자료를 함께 등록하는 표가 쓴다.
_FILE_COLUMN_ALIASES = ("항목",)
_SEPARATOR_CELL_RE = re.compile(r"^:?-+:?$")
_CELL_SPLIT_RE = re.compile(r"(?<!\\)\|")
_LINK_CELL_RE = re.compile(r"^\[[^\]]*\]\(([^)\s]*)(?:\s+\"[^\"]*\")?\)$")
_CODE_CELL_RE = re.compile(r"^`([^`]+)`$")
INDEX_YAML_HEADER = (
    "# reference/ 자료의 설명과 처리 상태. 항목 이름마다 description과 status를 적는다.\n")


def _split_row(line: str) -> List[str]:
    """표 행을 칸 목록으로 나눈다. 칸 안의 `\\|`는 `|`로 되돌린다."""
    body = line.strip()
    if body.startswith("|"):
        body = body[1:]
    if body.endswith("|") and not body.endswith("\\|"):
        body = body[:-1]
    return [c.strip().replace("\\|", "|") for c in _CELL_SPLIT_RE.split(body)]


def _file_name(cell: str) -> Optional[str]:
    """파일 칸에서 reference/ 직속 항목 이름을 얻는다. 얻을 수 없으면 None이다.

    이름이 /로 끝나면 폴더 행이다. 끝 / 하나를 떼고 검사한 뒤 키에 다시 붙인다.
    """
    folder = False
    m = _CODE_CELL_RE.match(cell)
    if m:
        name = m.group(1).strip()
        if name.endswith("/"):
            folder, name = True, name[:-1]
    else:
        m = _LINK_CELL_RE.match(cell)
        if m:
            target = m.group(1).partition("#")[0]
            if not target or _SCHEME_RE.match(target):
                return None
            decoded = urllib.parse.unquote(target)
            if decoded.endswith("/"):
                folder, decoded = True, decoded[:-1]
            joined = posixpath.join(REFERENCE_DIR_NAME, decoded)
            norm = posixpath.normpath(joined)
            parts = norm.split("/")
            if len(parts) != 2 or parts[0] != REFERENCE_DIR_NAME:
                return None
            name = parts[1]
        elif cell and not re.search(r"[\[\]`]", cell):
            name = cell
            if name.endswith("/"):
                folder, name = True, name[:-1]
        else:
            return None
    if not name or name in (".", "..") or "/" in name or "\\" in name \
            or "*" in name or "~" in name:
        return None
    return unicodedata.normalize("NFC", name + ("/" if folder else ""))


def _split_status(cell: str) -> Optional[Tuple[str, str]]:
    """상태 칸을 (어휘, 어휘 뒤에 남은 글)로 나눈다. 어휘로 시작하지 않으면 None이다."""
    for word in sorted(REFERENCE_STATUSES, key=len, reverse=True):
        for lead in ("`" + word + "`", word):
            if cell.startswith(lead):
                rest = cell[len(lead):]
                if rest and rest[0].isalnum():
                    continue
                tail = rest.strip()
                if tail and not tail[0].isalnum() and tail[0] not in "(-[":
                    return None
                return word, tail
    return None


def _quote_key(name: str) -> str:
    """항목 이름을 늘 큰따옴표로 감싼 YAML 키로 쓴다."""
    quote_scalar(name)  # 제어 문자가 든 이름이면 IndexFormatError
    return '"' + name.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _read_table(lines: List[str]) -> Tuple[List[Tuple[str, str, str]], List[str]]:
    """절 본문 줄에서 표를 읽어 ([(이름, 설명, 상태)], 읽지 못한 항목 목록)을 돌려준다."""
    rows: List[Tuple[str, str, str]] = []
    bad: List[str] = []
    table = [ln for ln in lines if ln.strip().startswith("|")]
    others = [ln.strip() for ln in lines
              if ln.strip() and not ln.strip().startswith("|")
              and not _EMPTY_NOTE_RE.match(ln.strip())]
    for ln in others:
        bad.append("표 밖의 글: " + ln)
    if not table:
        return rows, bad
    first = next(i for i, ln in enumerate(lines) if ln.strip().startswith("|"))
    last = max(i for i, ln in enumerate(lines) if ln.strip().startswith("|"))
    if any(not ln.strip().startswith("|") and ln.strip() for ln in lines[first:last + 1]):
        bad.append("표가 중간에 끊겼다")
        return rows, bad
    head = [c.strip("` ") for c in _split_row(table[0])]
    unknown = [c for c in head if c not in _KNOWN_COLUMNS + _FILE_COLUMN_ALIASES]
    if unknown:
        bad.append("모르는 열: " + ", ".join(unknown))
        return rows, bad
    head = ["파일" if c in _FILE_COLUMN_ALIASES else c for c in head]
    if "파일" not in head or "상태" not in head or head.count("파일") > 1 \
            or head.count("상태") > 1 or head.count("설명") > 1:
        bad.append("머리 칸에 파일(또는 항목)과 상태가 하나씩 없다: " + table[0].strip())
        return rows, bad
    if len(table) < 2 or not all(_SEPARATOR_CELL_RE.match(c) for c in _split_row(table[1])):
        bad.append("머리 줄 다음에 구분 줄이 없다: " + table[0].strip())
        return rows, bad
    i_file, i_status = head.index("파일"), head.index("상태")
    i_desc = head.index("설명") if "설명" in head else None
    seen = set()
    for ln in table[2:]:
        cells = _split_row(ln)
        if len(cells) != len(head):
            bad.append("칸 수가 머리와 다르다: " + ln.strip())
            continue
        name = _file_name(cells[i_file])
        status = _split_status(cells[i_status])
        if name is None or status is None:
            bad.append("파일 칸이나 상태 칸을 읽지 못했다: " + ln.strip())
            continue
        if name in seen:
            bad.append("같은 파일이 두 번 있다: " + ln.strip())
            continue
        seen.add(name)
        desc = cells[i_desc] if i_desc is not None else ""
        if status[1]:
            desc = (desc + " " + status[1]).strip()
        rows.append((name, desc, status[0]))
    return rows, bad


def convert_reference_table(text: str) -> Tuple[str, str, List[str]]:
    """reference/AGENTS.md 본문의 "등록된 자료" 표를 INDEX.yaml 텍스트로 옮긴다.

    (절을 뺀 새 본문, INDEX.yaml 텍스트, 읽지 못한 항목 목록)을 돌려준다. 절이 없으면
    (text, "", [])이다. 읽지 못한 행이나 표 밖의 글이 하나라도 있으면 본문을 바꾸지 않고
    INDEX.yaml 텍스트도 빈 문자열로 둔다. 표에 행이 없으면 절만 지우고 머리 주석만 든 텍스트를 만든다.
    파일 칸은 링크, 인라인 코드, 일반 글에서 이름을 얻고, 추가일 열은 버린다. 값은 quote_scalar로 쓴다.
    머리 칸 이름 항목은 파일과 같은 뜻으로 받는다. 한 표에 둘이 함께 있으면 읽지 못한 것으로 본다.
    """
    lines = text.splitlines(keepends=True)
    start = end = None
    level = 0
    in_fence = False
    for i, line in enumerate(lines):
        if line.lstrip().startswith(_FENCES):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if start is None:
            m = _SECTION_RE.match(line.rstrip("\r\n"))
            if m:
                start, level = i, len(m.group(1))
        else:
            m = _HEADING_RE.match(line)
            if m and len(m.group(1)) <= level:
                end = i
                break
    if start is None:
        return text, "", []
    if end is None:
        end = len(lines)
    rows, bad = _read_table([ln.rstrip("\r\n") for ln in lines[start + 1:end]])
    out = [INDEX_YAML_HEADER]
    if not bad:
        try:
            for name, desc, status in rows:
                out.append(_quote_key(name) + ":\n")
                if desc:
                    out.append("  description: " + quote_scalar(desc) + "\n")
                out.append("  status: " + quote_scalar(status) + "\n")
        except IndexFormatError as e:
            bad.append("YAML로 쓸 수 없는 값: " + e.message)
    if bad:
        return text, "", bad
    rest = "".join(lines[:start]) + "".join(lines[end:])
    if end == len(lines):
        rest = rest.rstrip("\r\n")
        if rest:
            eol = "\r\n" if "\r\n" in text else "\n"
            rest += eol
    return rest, "".join(out), []


# reference/ 직속에서 운영 파일로 보는 이름. 디스크립터, 진입점 포인터, 생성 색인 쪽 파일이다.
_REFERENCE_OPERATIONAL_NAMES = (DESCRIPTOR_NAME, "CLAUDE.md")


def _is_reference_material(rel: str) -> bool:
    """rel(이전 뒤 경로)이 reference/ 아래 자료 파일이면 참. 이런 파일은 본문을 바꾸지 않는다.

    감사의 자료 폴더 판정(in_material_content)을 reference/에 한정해 따른다. 규범 폴더
    reference/AGENTS/ 아래와 reference/ 직속의 AGENTS.md, CLAUDE.md, 색인 쪽 파일(INDEX.md,
    INDEX2.md ...)은 운영 파일이라 거짓이다. 그 밖의 하위 폴더에 있는 같은 이름은 자료 사본으로 본다.
    """
    parts = rel.split("/")
    if len(parts) < 2 or parts[0] != REFERENCE_DIR or parts[1] == NORMS_DIR_NAME:
        return False
    if len(parts) == 2 and (parts[1] in _REFERENCE_OPERATIONAL_NAMES
                            or INDEX_PAGE_RE.match(parts[1])):
        return False
    return True


@dataclass
class Report:
    """이전 결과. 경로는 레포 루트 기준 POSIX 상대 경로다."""

    moved: List[Tuple[str, str]] = field(default_factory=list)
    rewritten: List[str] = field(default_factory=list)
    residual: List[Tuple[str, int, str]] = field(default_factory=list)
    conflicts: List[Tuple[str, str]] = field(default_factory=list)  # (옛 경로, 새 경로) 대상이 이미 있어 건너뜀
    converted: List[Tuple[str, str]] = field(default_factory=list)  # (자료 표를 뺀 파일, 만든 INDEX.yaml)
    unconverted: List[Tuple[str, str]] = field(default_factory=list)  # (파일, 변환하지 못한 사유)


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


def _convert_reference(root: Path, text: str, report: Report, dry_run: bool) -> str:
    """reference/AGENTS.md 본문의 자료 표를 INDEX.yaml로 옮기고 새 본문을 돌려준다.

    옮기지 못하면(읽지 못한 행, 항목이 든 기존 INDEX.yaml) 본문을 그대로 돌려주고 report.unconverted에
    쌓는다. 기존 INDEX.yaml이 주석과 빈 줄뿐이면(상류가 출고하는 파일) 없는 것으로 보고 덮어쓴다.
    dry_run이면 파일을 쓰지 않고 converted만 채운다.
    """
    body, yaml, bad = convert_reference_table(text)
    for item in bad:
        report.unconverted.append((REFERENCE_DESCRIPTOR, item))
    if bad or body == text:
        return text
    target = root / REFERENCE_INDEX
    if os.path.islink(str(target)) or (os.path.lexists(str(target)) and not target.is_file()):
        report.unconverted.append((REFERENCE_DESCRIPTOR, REFERENCE_INDEX + "가 이미 있다"))
        return text
    try:
        existing = load_index_yaml(target)
    except IndexFormatError as e:
        report.unconverted.append((REFERENCE_DESCRIPTOR, REFERENCE_INDEX + " 형식 오류: " + e.message))
        return text
    if existing:
        report.unconverted.append((REFERENCE_DESCRIPTOR, REFERENCE_INDEX + "가 이미 있다"))
        return text
    report.converted.append((REFERENCE_DESCRIPTOR, REFERENCE_INDEX))
    if not dry_run:
        with open(str(root / REFERENCE_INDEX), "w", encoding="utf-8", newline="") as f:
            f.write(yaml)
    return body


def migrate(root: Path, dry_run: bool = False) -> Report:
    """root의 추적 파일을 새 레이아웃으로 옮기고 추적 md 파일의 링크와 언급을 바꾼다.

    각 md 파일의 본문은 (이번 실행 전 위치, 현재 위치)로 정확히 한 번만 변환하므로 재실행은 변화가 없다.
    이미 새 위치에 있던 파일은 그 뒤 _repair_links로 옛 위치 기준 링크를 고친다. 대상 존재
    판정은 이전 뒤 추적 파일 집합(dry_run이 아니면 파일 시스템도)으로 하므로 고친 링크는 재실행에서
    그대로다. 대응이 없는 옛 최상위 폴더의 추적 파일과 링크 대상에 옛 경로가 남은 줄은 residual로 보고한다.
    대응 뒤 경로가 reference/ 아래 자료 파일(_is_reference_material)이면 옮기기만 하고 본문을 읽거나
    바꾸지 않으며, rewritten과 residual에도 넣지 않는다. 충돌로 옛 자리에 남은 파일도 같다.
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
        # 충돌로 옛 자리에 남은 파일도 대응 뒤 경로로 판정해 자료 본문을 지킨다.
        if not new.endswith(".md") or _is_reference_material(map_path(new)):
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
        if new == REFERENCE_DESCRIPTOR:
            out = _convert_reference(root, out, report, dry_run)
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
    print("등록된 자료 표를 옮긴 파일 (%d):" % len(rep.converted))
    for src, dest in rep.converted:
        print("  %s -> %s" % (src, dest))
    print("옮기지 못한 등록된 자료 표 (%d):" % len(rep.unconverted))
    for path, reason in rep.unconverted:
        print("  %s: %s" % (path, reason))
    return 1 if rep.conflicts or rep.unconverted else 0


if __name__ == "__main__":
    sys.exit(main())

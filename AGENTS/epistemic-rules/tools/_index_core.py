#!/usr/bin/env python3
"""폴더 색인 - YAML 부분집합 파서, 설명 읽기, 색인 렌더러.

색인 설명의 출처는 두 곳이다. md 문서는 front matter의 description 줄,
그 밖의 항목과 폴더는 폴더의 INDEX.yaml이다. 표준 라이브러리에 YAML
파서가 없어 부분집합을 정해 손으로 읽는다. 이 부분집합은 유효한 YAML이다.
규칙의 원본은 AGENTS/epistemic-rules/folder-index.md다.

스칼라(한 줄 값):
- 따옴표 없는 값은 첫 글자가 "'[]{}>|*&!%@# 이나 백틱이 아니어야 한다.
- 따옴표 없는 값은 ": "와 " #"를 담지 않고, "- "나 "? "로 시작하지 않으며,
  ":"로 끝나지 않는다. 한 글자 "-", "?"도 받지 않는다.
- 큰따옴표 값은 \\" 와 \\\\ 두 이스케이프만 쓴다. 닫는 따옴표 뒤에는 공백만 둔다.
- 여러 줄 값(>, |)은 받지 않는다.

INDEX.yaml:
- 줄 전체 주석(#), 빈 줄, 큰따옴표 항목 이름 줄, 두 칸 들여 쓴 "키: 값" 줄만 쓴다.
- 항목 이름은 폴더 직속 항목 이름이고 폴더는 끝에 /를 붙인다.
- 예약 항목 "."는 폴더 자신이다. 키는 structure 하나만 두고 값이 비면 안 된다.
- 알 수 없는 키는 오류가 아니라 그대로 담는다. 경고는 감사가 한다.

색인 렌더러:
- 색인을 두는 폴더(index_dirs)는 감사 순회 content_dirs 가운데 규범 폴더가
  아니고 AGENTS.md가 있는 폴더다. 중첩 저장소 안, reference/ 하위 폴더,
  순차 분류 최상위로 선언된 폴더의 자손은 들지 않는다.
- 항목은 폴더 직속 항목에서 점 파일, 운영 파일(AGENTS.md, CLAUDE.md,
  AGENTS/, 색인 쪽 파일, INDEX.yaml), EXEMPT_DIRS 이름, 심볼릭 링크,
  OS와 편집기 부산물을 뺀 전부다. 중첩 저장소 폴더는 항목 하나로만 보인다.
- 이름은 NFC로 바꾸고 코드 포인트 순으로 정렬한다. 링크 대상은 공백,
  %, (, ), [, ], <, >, #, ?, 역슬래시만 퍼센트 인코딩하고 한글은 그대로 둔다.
- 표시 텍스트의 [, ]는 역슬래시로 이스케이프한다. 이스케이프한 "\\]"가 든
  줄은 감사의 링크 정규식(LINK_RE, LINK_TEXT_RE)이 링크로 보지 않으므로 링크
  실존, 표시 텍스트, 공백 링크 검사 밖으로 빠진다. 역슬래시가 든 이름은
  윈도우 금지 문자라 감사 이식성 검사가 위반으로 잡으므로 표시 텍스트에서
  따로 이스케이프하지 않는다(링크 대상에서는 %5C로 인코딩한다).
- NFC로 바꾸면 같아지는 두 디스크 이름이 한 폴더에 있으면 IndexFormatError다.
- 쪽 분량은 감사 분량 검사와 같은 text_size로 재고 한도는 SIZE_LIMIT_NODE다.
- 렌더 함수는 파일을 쓰지 않는다. 쓰기는 생성 진입점 하나가 맡는다.

생성기와 감사는 같은 상수와 함수를 쓴다.
"""

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from _audit_core import (
    DESCRIPTOR_NAME, EXEMPT_DIRS, FRONT_MATTER_RE, INDEX_NAME,
    INDEX_YAML_NAME, NORMS_DIR_NAME, REFERENCE_DIR, SIZE_LIMIT_NODE,
    content_dirs, in_norms_dir, is_index_file, nfc, read, text_size)

# 항목 필드로 허용하는 키.
INDEX_KEYS = ("description", "status")
# 폴더 자신을 가리키는 예약 항목 이름과 그 항목의 유일한 키.
SELF_KEY = "."
STRUCTURE_KEY = "structure"
# reference 항목의 처리 상태 어휘.
REFERENCE_STATUSES = ("처리 대기", "처리됨", "사용자 의견 필요", "보관용")
# 색인 설명 길이 상한(공백 포함 글자 수).
INDEX_DESC_LIMIT = 200

# OS와 편집기가 만드는 부산물. 색인 항목에서 빼며 생성기와 감사가 함께 쓴다.
BYPRODUCT_NAMES = frozenset({"Thumbs.db", "desktop.ini", "ehthumbs.db", "Icon\r"})


def is_byproduct(name: str) -> bool:
    """고정 부산물 목록에 있거나 이름이 ~로 끝나면 참."""
    return name in BYPRODUCT_NAMES or name.endswith("~")


class IndexFormatError(ValueError):
    """색인 YAML 부분집합이나 설명 값이 규칙을 어겼다.

    line은 1부터 센 줄 번호이고 0이면 줄 미상이다. path는 읽던 파일이며
    모르면 None이다.
    """

    def __init__(self, message: str, line: int = 0,
                 path: "Optional[Path]" = None):
        super().__init__(message)
        self.message = message
        self.line = line
        self.path = path

    def __str__(self) -> str:
        where = ""
        if self.path is not None:
            where = str(self.path)
        if self.line:
            where = "%s:%d" % (where, self.line) if where else "줄 %d" % self.line
        return "%s: %s" % (where, self.message) if where else self.message


_PLAIN_FIRST_BAD = "\"'[]{},>|*&!%@#`"
_LINE_BREAKS = "\u2028\u2029\u0085"
# YAML이 문자열이 아닌 값(null, 불리언, 수, 날짜)으로 읽는 따옴표 없는 값.
_NON_STRING_RE = re.compile(
    r"^(?:~|=|<<|null|true|false|yes|no|on|off"
    r"|[-+]?\.(?:inf|nan)"
    r"|[-+]?(?:\d[\d_]*)(?:\.[\d_]*)?(?:[eE][-+]?\d+)?"
    r"|[-+]?\.\d[\d_]*(?:[eE][-+]?\d+)?"
    r"|[-+]?0[xXoObB][0-9a-fA-F_]+"
    r"|[-+]?\d[\d_]*(?::[0-5]?\d)+(?:\.[\d_]*)?"
    r"|\d{4}-\d{1,2}-\d{1,2}(?:[Tt ].*)?)$", re.IGNORECASE)


def _has_control(text: str) -> bool:
    """제어 문자(Cc)나 유니코드 줄 구분자가 있으면 참."""
    return any(unicodedata.category(c) == "Cc" or c in _LINE_BREAKS
               for c in text)
_NAME_LINE_RE = re.compile(r'^"((?:[^"\\]|\\.)*)":[ ]*$')
_KEY_LINE_RE = re.compile(r"^  ([A-Za-z_][A-Za-z0-9_-]*):(?: (.*))?$")
_QUOTED_RE = re.compile(r'^"((?:[^"\\]|\\.)*)"[ ]*$')


def _unescape(body: str) -> str:
    out = []
    i = 0
    while i < len(body):
        ch = body[i]
        if ch != "\\":
            out.append(ch)
            i += 1
            continue
        nxt = body[i + 1] if i + 1 < len(body) else ""
        if nxt not in ('"', "\\"):
            raise IndexFormatError("허용하지 않는 이스케이프다: \\" + nxt)
        out.append(nxt)
        i += 2
    return "".join(out)


def parse_scalar(raw: str) -> str:
    """한 줄 스칼라 값을 읽는다. 규칙을 어기면 IndexFormatError."""
    text = raw.strip()
    if text == "":
        return ""
    if _has_control(text):
        raise IndexFormatError("값에 탭이나 제어 문자가 있다")
    if text[0] == '"':
        m = _QUOTED_RE.match(text)
        if not m:
            raise IndexFormatError("큰따옴표 값이 올바르지 않다: " + text)
        return _unescape(m.group(1))
    if text[0] in _PLAIN_FIRST_BAD:
        raise IndexFormatError("따옴표 없는 값이 %r로 시작한다" % text[0])
    if ": " in text or " #" in text:
        raise IndexFormatError("따옴표 없는 값에 ': ' 또는 ' #'이 있다")
    if text.endswith(":"):
        raise IndexFormatError("따옴표 없는 값이 ':'로 끝난다")
    if text in ("-", "?") or text.startswith(("- ", "? ")):
        raise IndexFormatError("따옴표 없는 값이 '- ' 또는 '? '로 시작한다")
    if _NON_STRING_RE.match(text):
        raise IndexFormatError("따옴표 없는 값이 문자열이 아닌 값으로 읽힌다")
    return text


def quote_scalar(value: str) -> str:
    """값을 부분집합 규칙을 지키는 YAML 스칼라 문자열로 쓴다.

    따옴표 없이 읽히는 값은 그대로, 아니면 큰따옴표로 감싼다. 숫자나 null처럼
    읽히는 값도 감싼다. 탭, 줄바꿈 등 제어 문자와 줄 구분자를 담은 값은
    쓸 수 없어 IndexFormatError다.
    """
    if _has_control(value):
        raise IndexFormatError("제어 문자가 든 값은 쓸 수 없다")
    if value == value.strip() and value:
        try:
            if parse_scalar(value) == value and not value.startswith('"'):
                return value
        except IndexFormatError:
            pass
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def front_matter_description(path: Path) -> "Optional[str]":
    """front matter의 description 값. 없으면 None.

    값이 규칙을 어기거나 여러 줄 표기이면 IndexFormatError(줄은 파일 기준).
    front matter 영역은 _audit_core의 FRONT_MATTER_RE와 read로 읽는다.
    """
    m = FRONT_MATTER_RE.match(read(path))
    if not m:
        return None
    lines = m.group(1).split("\n")
    for i, line in enumerate(lines):
        if not line.startswith("description:"):
            continue
        no = i + 2
        try:
            rest = line[len("description:"):]
            if rest.strip() == "":
                raise IndexFormatError("description 값이 없거나 여러 줄이다")
            if rest[0] not in " \t":
                raise IndexFormatError("description: 뒤에 공백이 없다")
            value = parse_scalar(rest)
            if i + 1 < len(lines) and lines[i + 1][:1] in (" ", "\t") \
                    and lines[i + 1].strip():
                raise IndexFormatError("description 값이 여러 줄이다")
        except IndexFormatError as e:
            raise IndexFormatError(e.message, no, path) from None
        return value
    return None


def load_index_yaml(path: Path) -> "dict[str, dict[str, str]]":
    """INDEX.yaml을 읽어 {항목 이름(NFC): {키: 값}}으로 돌려준다.

    파일이 없으면 빈 dict다. 형식 오류는 파일과 줄을 담은 IndexFormatError다.
    """
    if not path.is_file():
        return {}
    text = read(path)
    if text.startswith("\ufeff"):
        text = text[1:]
    data: "dict[str, dict[str, str]]" = {}
    current: "Optional[dict[str, str]]" = None
    self_line = 0
    for no, line in enumerate(text.replace("\r\n", "\n").split("\n"), start=1):
        try:
            if line.strip() == "" or line.lstrip().startswith("#"):
                continue
            m = _NAME_LINE_RE.match(line)
            if m:
                name = unicodedata.normalize("NFC", _unescape(m.group(1)))
                if name == "":
                    raise IndexFormatError("항목 이름이 비었다")
                if name in data:
                    raise IndexFormatError("항목 이름이 겹친다: " + name)
                current = data[name] = {}
                if name == SELF_KEY:
                    self_line = no
                continue
            m = _KEY_LINE_RE.match(line)
            if not m:
                raise IndexFormatError("읽을 수 없는 줄이다")
            if current is None:
                raise IndexFormatError("항목 이름 줄보다 앞선 키 줄이다")
            key, raw = m.group(1), m.group(2)
            if raw is None or raw.strip() == "":
                raise IndexFormatError("값이 없거나 여러 줄이다: " + key)
            if key in current:
                raise IndexFormatError("키가 겹친다: " + key)
            current[key] = parse_scalar(raw)
        except IndexFormatError as e:
            raise IndexFormatError(e.message, no, path) from None
    own = data.get(SELF_KEY)
    if own is not None:
        if set(own) != {STRUCTURE_KEY} or not own[STRUCTURE_KEY].strip():
            raise IndexFormatError(
                '"." 항목은 비지 않은 structure 키 하나만 둔다', self_line, path)
    return data


# --- 색인 렌더러 ---

# 색인 항목에서 빼는 운영 파일. 규범 폴더(AGENTS/)와 색인 파일은 따로 판정한다.
OPERATION_FILES = frozenset({DESCRIPTOR_NAME, "CLAUDE.md"})
# reference/ 직속 항목이 INDEX.yaml에 없을 때 보이는 상태.
UNREGISTERED = "미등록"

# 쪽 머리말. 생성 파일임과 설명을 고치는 곳을 알린다.
INDEX_HEADER = (
    "<!-- 생성 파일이다. 손으로 고치지 않는다."
    " 설명은 각 문서 front matter의 description과"
    " 폴더의 INDEX.yaml에서 고친 뒤"
    " 생성 도구 build_index.py로 다시 만든다. -->")
ROOT_TITLE = "# 색인"
DIR_TITLE_FMT = "# {path} 색인"
PAGE_SUFFIX_FMT = " {n}쪽"
NAV_PREV_FMT = "앞 쪽 [{name}]({name})"
NAV_NEXT_FMT = "다음 쪽 [{name}]({name})"
NAV_SEP = ", "
# 항목 줄: "- [a.md](a.md)", 링크가 둘이면 쉼표로 잇고 설명은 " - " 뒤에 둔다.
LINK_FMT = "[{text}]({target})"
LINK_SEP = ", "
ENTRY_FMT = "- {links}"
ENTRY_TAIL_FMT = " - {tail}"
STATUS_FMT = "`{status}`"
EMPTY_LIST = "(항목 없음)"

# 링크 대상에서 퍼센트 인코딩하는 문자. 한글 등 나머지는 그대로 둔다.
_ENCODE = {c: "%%%02X" % ord(c) for c in " %()[]<>#?\\"}
# 표시 텍스트에서 역슬래시로 이스케이프하는 문자.
_DISPLAY_ESCAPE = {c: "\\" + c for c in "[]"}


@dataclass(frozen=True)
class Entry:
    """색인 항목 한 줄.

    name은 NFC 표시 이름이고 폴더는 끝에 /를 붙인다. 동명 쌍은 X.md다.
    links는 (표시 텍스트, 인코딩한 대상)의 튜플이다.
    """

    name: str
    links: "tuple[tuple[str, str], ...]"
    description: "Optional[str]"
    status: "Optional[str]"


def page_name(n: int) -> str:
    """n번째 쪽 파일 이름. 1이면 INDEX.md, 그 밖은 INDEX<n>.md."""
    return INDEX_NAME if n == 1 else "INDEX%d.md" % n


def encode_target(name: str) -> str:
    """링크 대상 이름을 정해진 문자만 퍼센트 인코딩한다."""
    return "".join(_ENCODE.get(c, c) for c in name)


def _escape_display(text: str) -> str:
    return "".join(_DISPLAY_ESCAPE.get(c, c) for c in text)


def sequential_structure(d: Path) -> "Optional[str]":
    """폴더 INDEX.yaml의 "." 항목 structure 값. 선언이 없으면 None.

    INDEX.yaml 형식 오류는 IndexFormatError로 올린다.
    """
    own = load_index_yaml(d / INDEX_YAML_NAME).get(SELF_KEY)
    if own is None:
        return None
    return nfc(own[STRUCTURE_KEY])


def _in_reference_subfolder(root: Path, d: Path) -> bool:
    """reference/X/ 이하 폴더면 참. 원본 자료라 색인을 두지 않는다."""
    parts = d.relative_to(root).parts
    return len(parts) >= 2 and parts[0] == REFERENCE_DIR


def index_dirs(root: Path) -> "list[Path]":
    """색인을 두는 폴더. 순서는 content_dirs를 따른다(루트가 먼저).

    content_dirs가 중첩 저장소 안과 implementation/ 하위 프로젝트를 이미
    뺀다. 순차 분류 최상위로 선언된 폴더 자신은 들고 그 자손은 빠진다.
    선언은 색인 후보 폴더의 INDEX.yaml에서만 읽는다.
    """
    out: "list[Path]" = []
    tops: "list[Path]" = []
    for d in content_dirs(root):
        if any(t in d.parents for t in tops):
            continue
        if in_norms_dir(root, d) or _in_reference_subfolder(root, d):
            continue
        if not (d / DESCRIPTOR_NAME).is_file():
            continue
        out.append(d)
        if sequential_structure(d) is not None:
            tops.append(d)
    return out


def _entry_children(d: Path) -> "list[Path]":
    """폴더 d의 색인 항목이 되는 직속 항목의 디스크 경로(정렬)."""
    out: "list[Path]" = []
    for p in d.iterdir():
        name = p.name
        if name.startswith(".") or name in EXEMPT_DIRS:
            continue
        if p.is_symlink():
            continue
        if name in OPERATION_FILES or is_index_file(name):
            continue
        if is_byproduct(name):
            continue
        if name == NORMS_DIR_NAME and p.is_dir():
            continue
        out.append(p)
    return sorted(out)


def entry_paths(root: Path) -> "list[Path]":
    """모든 색인 폴더의 항목 디스크 경로(정렬). 동명 쌍은 둘 다 든다.

    순차 분류 최상위로 선언된 폴더는 항목을 나열하지 않으므로 뺀다.
    생성기가 git 무시 항목을 확인할 때 쓴다.
    """
    out: "list[Path]" = []
    for d in index_dirs(root):
        if sequential_structure(d) is None:
            out.extend(_entry_children(d))
    return sorted(out)


def _md_description(path: Path) -> "Optional[str]":
    """md 문서의 front matter 설명. 형식 오류는 설명 없음으로 둔다."""
    try:
        return front_matter_description(path)
    except IndexFormatError:
        return None


def _clean(text: "Optional[str]") -> "Optional[str]":
    if text is None or not text.strip():
        return None
    return nfc(text)


def _folder_link(name: str, indexed: bool,
                 paired: bool) -> "tuple[str, str]":
    """하위 폴더 링크. 색인 폴더면 X/INDEX.md, 아니면 X/를 가리킨다."""
    target = encode_target(name) + "/"
    if not indexed:
        return (name + "/", target)
    target += INDEX_NAME
    return (name + "/" + INDEX_NAME if paired else name + "/", target)


def _list_entries(root: Path, d: Path,
                  indexed: "set[Path]") -> "list[Entry]":
    yaml = load_index_yaml(d / INDEX_YAML_NAME)
    in_ref = d == root / REFERENCE_DIR
    files: "dict[str, Path]" = {}
    dirs: "dict[str, Path]" = {}
    seen: "dict[str, Path]" = {}
    for p in _entry_children(d):
        name = nfc(p.name)
        if name in seen:
            raise IndexFormatError(
                "NFC로 같은 이름이 둘이다: %r, %r"
                % (seen[name].name, p.name), 0, p)
        seen[name] = p
        (dirs if p.is_dir() else files)[name] = p

    def describe(key: str, path: Path) -> "tuple[Optional[str], Optional[str]]":
        item = yaml.get(key)
        status = None
        if in_ref:
            status = UNREGISTERED if item is None else item.get("status")
        if key.endswith(".md") and not in_ref:
            desc = _md_description(path)
        else:
            desc = None if item is None else item.get("description")
        return _clean(desc), _clean(status)

    entries: "list[Entry]" = []
    paired: "set[str]" = set()
    for name, path in files.items():
        links = [(name, encode_target(name))]
        stem = name[:-3] if name.endswith(".md") else None
        if stem and stem in dirs:
            paired.add(stem)
            links.append(_folder_link(stem, dirs[stem] in indexed, True))
        desc, status = describe(name, path)
        entries.append(Entry(name, tuple(links), desc, status))
    for name, path in dirs.items():
        if name in paired:
            continue
        desc, status = describe(name + "/", path)
        link = _folder_link(name, path in indexed, False)
        entries.append(Entry(name + "/", (link,), desc, status))
    return sorted(entries, key=lambda e: e.name)


def list_entries(root: Path, d: Path) -> "list[Entry]":
    """폴더 d의 색인 항목(이름의 코드 포인트 순).

    설명은 md 문서면 front matter description(형식 오류면 None), 그 밖의
    항목과 폴더, reference/의 md 자료는 그 폴더 INDEX.yaml에서 읽는다.
    동명 쌍(X.md와 X/)은 한 항목으로 합치고 X.md의 설명을 쓴다.
    reference/ 직속 항목은 INDEX.yaml에 없으면 status가 "미등록"이다.
    INDEX.yaml 형식 오류는 IndexFormatError로 올린다. NFC로 바꾸면 같아지는
    두 디스크 이름이 있어도 IndexFormatError다(path는 나중 경로).
    """
    return _list_entries(root, d, set(index_dirs(root)))


def _entry_line(e: Entry) -> str:
    links = LINK_SEP.join(
        LINK_FMT.format(text=_escape_display(text), target=target)
        for text, target in e.links)
    line = ENTRY_FMT.format(links=links)
    tail = []
    if e.status:
        tail.append(STATUS_FMT.format(status=e.status))
    if e.description:
        tail.append(e.description)
    if tail:
        line += ENTRY_TAIL_FMT.format(tail=" ".join(tail))
    return nfc(line)


def _title(root: Path, d: Path, n: int) -> str:
    if d == root:
        title = ROOT_TITLE
    else:
        title = DIR_TITLE_FMT.format(path=nfc(d.relative_to(root).as_posix()))
    if n > 1:
        title += PAGE_SUFFIX_FMT.format(n=n)
    return title


def _nav(n: int, has_prev: bool, has_next: bool) -> str:
    parts = []
    if has_prev:
        parts.append(NAV_PREV_FMT.format(name=page_name(n - 1)))
    if has_next:
        parts.append(NAV_NEXT_FMT.format(name=page_name(n + 1)))
    return NAV_SEP.join(parts)


def _page(blocks: "list[str]") -> str:
    """빈 줄로 블록을 잇고 LF, 끝 줄바꿈 하나, NFC로 맞춘다."""
    return nfc("\n\n".join(b for b in blocks if b) + "\n")


def _render(root: Path, d: Path, indexed: "set[Path]") -> "list[str]":
    structure = sequential_structure(d)
    if structure is not None:
        return [_page([INDEX_HEADER, _title(root, d, 1), structure])]
    lines = [_entry_line(e) for e in _list_entries(root, d, indexed)]
    if not lines:
        return [_page([INDEX_HEADER, _title(root, d, 1), EMPTY_LIST])]
    # 쪽마다 앞뒤 쪽 링크가 모두 있다고 치고 남는 분량을 앞에서부터 채운다.
    groups: "list[list[str]]" = []
    i = 0
    while i < len(lines):
        n = len(groups) + 1
        fixed = (text_size(INDEX_HEADER) + text_size(_title(root, d, n))
                 + text_size(_nav(max(n, 2), True, True)))
        budget = SIZE_LIMIT_NODE - fixed
        group = [lines[i]]
        used = text_size(lines[i])
        i += 1
        while i < len(lines) and used + text_size(lines[i]) <= budget:
            used += text_size(lines[i])
            group.append(lines[i])
            i += 1
        groups.append(group)
    total = len(groups)
    pages = []
    for n, group in enumerate(groups, start=1):
        nav = _nav(n, n > 1, n < total) if total > 1 else ""
        pages.append(_page(
            [INDEX_HEADER, _title(root, d, n), nav, "\n".join(group)]))
    return pages


def render_pages(root: Path, d: Path) -> "list[str]":
    """폴더 d의 색인 쪽 내용 목록. 첫 원소가 INDEX.md다.

    순차 분류 최상위로 선언된 폴더는 머리말, 제목, 구성 설명 한 문단의
    한 쪽만 내고 항목을 나열하지 않는다.
    """
    return _render(root, d, set(index_dirs(root)))


def render_all(root: Path) -> "dict[Path, str]":
    """만들어야 할 모든 색인 쪽 파일의 절대 경로와 내용. 파일을 쓰지 않는다."""
    dirs = index_dirs(root)
    indexed = set(dirs)
    out: "dict[Path, str]" = {}
    for d in dirs:
        for n, text in enumerate(_render(root, d, indexed), start=1):
            out[d / page_name(n)] = text
    return out

#!/usr/bin/env python3
"""폴더 색인 - YAML 부분집합 파서와 설명 읽기.

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

생성기와 감사는 같은 상수와 함수를 쓴다.
"""

import re
import unicodedata
from pathlib import Path
from typing import Optional

from _audit_core import FRONT_MATTER_RE, read

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

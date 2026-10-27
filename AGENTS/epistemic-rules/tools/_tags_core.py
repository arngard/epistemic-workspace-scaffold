#!/usr/bin/env python3
"""front matter tags 읽기와 표기 규칙 - 감사와 태그 도구가 함께 쓰는 공용 모듈.

읽기 규칙의 구현은 find_tags_block 하나다. parse_tags 등 나머지는 그 결과를
쓴다. 읽기와 다시 쓰기가 같은 코드라야 도구가 감사가 못 본 태그를 바꾸거나
그 반대가 되지 않는다.

읽는 형식(그 밖의 형식은 TagFormatError):
- 흐름형: tags: [a, "b", 'c'] 한 줄. 빈 목록 []과 끝 쉼표를 받는다.
  항목은 따옴표 없는 값, 큰따옴표 값(\\" 와 \\\\ 이스케이프),
  작은따옴표 값('' 이스케이프)이다.
- 블록형: tags: 다음 줄부터 "- 값" 줄. 들여쓰기는 항목마다 같아야 하고
  키와 같은 열도 받는다. 항목이 없으면 빈 목록이다.
- 닫는 대괄호나 항목 뒤에는 공백과 " #" 주석만 둘 수 있다.
- 태그는 NFC로 바꿔 돌려준다.

TagsBlock의 start, end는 받은 텍스트 안에서 tags 값 영역의 오프셋이다.
흐름형은 여는 대괄호부터 닫는 대괄호 끝까지, 블록형은 tags: 줄 끝(주석
뒤)부터 마지막 항목 줄 끝까지다. 줄 끝의 CR은 영역에 넣지 않는다.
"""

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from _audit_core import (
    EXEMPT_FILENAMES, FRONT_MATTER_RE, INDEX_PAGE_RE, iter_md_files, nfc, read)


class TagFormatError(ValueError):
    """tags 값이 읽는 형식이 아니다.

    line은 1부터 센 줄 번호다. find_tags_block과 parse_tags는 받은 텍스트
    기준이고, front_matter_tags는 파일 기준으로 바꿔 올린다. 0이면 미상이다.
    """

    def __init__(self, message: str, line: int = 0):
        super().__init__(message)
        self.line = line


@dataclass(frozen=True)
class TagsBlock:
    """front matter 안의 tags 값 영역과 그 안의 태그."""

    start: int
    end: int
    style: str  # "flow" 또는 "block"
    indent: str  # 블록형 항목 줄의 들여쓰기
    tags: "tuple[str, ...]"


_KEY_RE = re.compile(r"^tags[ \t]*:", re.MULTILINE)
_ITEM_RE = re.compile(r"^( *)-( +)(.*)$")
# 따옴표 없는 값의 첫 글자로 쓸 수 없는 것(따옴표는 따로 처리한다).
_PLAIN_BAD_FIRST = set("[]{},>|*&!%@#`")
_DEFAULT_INDENT = "  "


def _fail(message: str, line: int) -> TagFormatError:
    return TagFormatError(message, line)


def _check_plain(value: str, in_flow: bool, line: int) -> None:
    if not value:
        raise _fail("빈 항목", line)
    if value[0] in _PLAIN_BAD_FIRST:
        raise _fail(f'따옴표 없는 값은 "{value[0]}"로 시작할 수 없다', line)
    if value[:2] in ("- ", "? ") or value in ("-", "?"):
        raise _fail("따옴표 없는 값이 목록 표시로 시작한다", line)
    if ": " in value or value.endswith(":"):
        raise _fail("항목이 매핑으로 읽힌다", line)
    if " #" in value:
        raise _fail("항목 안의 주석", line)
    if in_flow and any(c in value for c in "[]{}"):
        raise _fail("따옴표 없는 값에 괄호가 있다", line)


def _read_scalar(text: str, i: int, end: int, in_flow: bool, line: int):
    """text[i:end]의 i에서 스칼라 하나를 읽어 (값, 다음 위치)를 돌려준다."""
    c = text[i]
    if c in "\"'":
        quote = c
        buf = []
        j = i + 1
        while True:
            if j >= end:
                raise _fail("닫히지 않은 따옴표", line)
            ch = text[j]
            if quote == '"' and ch == "\\":
                nxt = text[j + 1] if j + 1 < end else ""
                if nxt not in ('"', "\\"):
                    raise _fail("큰따옴표 값은 \\\" 와 \\\\ 이스케이프만 읽는다", line)
                buf.append(nxt)
                j += 2
            elif ch == quote:
                if quote == "'" and j + 1 < end and text[j + 1] == "'":
                    buf.append("'")
                    j += 2
                else:
                    return nfc("".join(buf)), j + 1
            else:
                buf.append(ch)
                j += 1
    j = i
    if in_flow:
        while j < end and text[j] not in ",]":
            j += 1
    else:
        m = re.search(r"[ \t]#", text[i:end])
        j = i + m.start() if m else end
    value = text[i:j].strip(" \t")
    _check_plain(value, in_flow, line)
    return nfc(value), j


def _check_tail(text: str, i: int, end: int, line: int) -> None:
    """항목이나 닫는 대괄호 뒤에 공백과 주석만 있는지 본다."""
    tail = text[i:end]
    if tail.strip(" \t") and not re.match(r"[ \t]+#", tail):
        raise _fail("항목 뒤에 읽을 수 없는 글자가 있다", line)


def _read_flow(text: str, start: int, end: int, line: int):
    items = []
    i = start + 1
    while True:
        while i < end and text[i] in " \t":
            i += 1
        if i >= end:
            raise _fail("닫는 대괄호가 없다(여러 줄 흐름형은 읽지 않는다)", line)
        if text[i] == "]":
            i += 1
            break
        value, i = _read_scalar(text, i, end, True, line)
        items.append(value)
        while i < end and text[i] in " \t":
            i += 1
        if i >= end:
            raise _fail("닫는 대괄호가 없다(여러 줄 흐름형은 읽지 않는다)", line)
        if text[i] == ",":
            i += 1
        elif text[i] == "]":
            i += 1
            break
        else:
            raise _fail("항목 뒤에는 쉼표나 닫는 대괄호가 와야 한다", line)
    _check_tail(text, i, end, line)
    return tuple(items), i


def _read_block(text: str, key_end: int, line: int):
    """tags: 줄 다음의 항목 줄들. (항목, 들여쓰기, 끝 오프셋)을 돌려준다."""
    items = []
    indent = None
    end = key_end
    pos = text.find("\n", key_end)
    lineno = line
    while pos != -1:
        lineno += 1
        begin = pos + 1
        nl = text.find("\n", begin)
        stop = len(text) if nl == -1 else nl
        content_end = stop - 1 if stop > begin and text[stop - 1] == "\r" else stop
        row = text[begin:content_end]
        pos = nl
        if not row.strip():
            continue
        m = _ITEM_RE.match(row)
        if m:
            if indent is None:
                indent = m.group(1)
            elif m.group(1) != indent:
                raise _fail("블록형 항목의 들여쓰기가 다르다", lineno)
            vstart = begin + m.start(3)
            if vstart >= content_end:
                raise _fail("빈 항목", lineno)
            value, nxt = _read_scalar(text, vstart, content_end, False, lineno)
            _check_tail(text, nxt, content_end, lineno)
            items.append(value)
            end = content_end
        elif row[0] in " \t":
            raise _fail("블록형 항목이 아니다", lineno)
        else:
            break
    return tuple(items), (_DEFAULT_INDENT if indent is None else indent), end


def find_tags_block(text: str) -> "TagsBlock | None":
    """text(front matter 안쪽)에서 tags 값 영역을 찾아 읽는다.

    tags 키가 없으면 None, 읽는 두 형식이 아니면 TagFormatError.
    """
    m = _KEY_RE.search(text)
    if not m:
        return None
    line = text.count("\n", 0, m.start()) + 1
    eol = text.find("\n", m.end())
    if eol == -1:
        eol = len(text)
    end = eol - 1 if eol > m.end() and text[eol - 1] == "\r" else eol
    rest = text[m.end():end]
    value = rest.lstrip(" \t")
    if value.startswith("["):
        start = end - len(value)
        tags, stop = _read_flow(text, start, end, line)
        return TagsBlock(start, stop, "flow", _DEFAULT_INDENT, tags)
    if not value or value.startswith("#"):
        tags, indent, stop = _read_block(text, end, line)
        return TagsBlock(end, stop, "block", indent, tags)
    raise _fail("tags가 목록이 아니다(흐름형 [a, b]나 블록형만 읽는다)", line)


def parse_tags(front: str) -> "list[str] | None":
    """front matter 안쪽 텍스트의 태그 목록. 키가 없으면 None."""
    block = find_tags_block(front)
    return None if block is None else list(block.tags)


def front_matter_tags(path: Path) -> "list[str] | None":
    """파일의 front matter 태그 목록. front matter나 tags 키가 없으면 None.

    TagFormatError의 line은 파일 기준으로 바꿔 올린다.
    """
    text = read(path)
    match = FRONT_MATTER_RE.match(text)
    if not match:
        return None
    try:
        return parse_tags(match.group(1))
    except TagFormatError as e:
        if e.line:
            offset = text.count("\n", 0, match.start(1))
            raise TagFormatError(str(e), e.line + offset) from None
        raise


def tag_key(tag: str) -> str:
    """표기 차이를 지운 비교 열쇠.

    NFKC 뒤 casefold하고 공백, 하이픈, 밑줄을 지운다. /는 중첩 태그
    구분자라 남긴다.
    """
    s = unicodedata.normalize("NFKC", tag).casefold()
    return "".join(c for c in s if not c.isspace() and c not in "-_")


def tag_form_problem(tag: str) -> "str | None":
    """태그가 형태 규칙을 어기면 사유, 아니면 None.

    옵시디언이 태그로 인정하지 않는 공백 든 태그, 빈 태그, 숫자만의 태그다.
    """
    if not tag:
        return "비어 있다"
    if any(c.isspace() for c in tag):
        return "공백을 담고 있다"
    if tag.isdecimal():
        return "숫자만으로 되어 있다"
    return None


def scan_tags(root: Path):
    """태그를 모으는 문서를 한 번 훑어 (읽은 문서, 읽지 못한 문서)를 돌려준다.

    범위는 iter_md_files에서 도구 전용 파일(EXEMPT_FILENAMES)과 생성 색인
    쪽 파일을 뺀 것이다. 읽은 문서는 {경로: 태그 목록}이고 tags 키가
    없는 문서는 담지 않는다. 읽지 못한 문서는 [(경로, TagFormatError)]다.
    """
    docs: "dict[Path, list[str]]" = {}
    errors: "list[tuple[Path, TagFormatError]]" = []
    for path in iter_md_files(root):
        if path.name in EXEMPT_FILENAMES or INDEX_PAGE_RE.match(path.name):
            continue
        try:
            tags = front_matter_tags(path)
        except TagFormatError as e:
            errors.append((path, e))
            continue
        if tags is not None:
            docs[path] = tags
    return docs, errors


def tag_documents(root: Path) -> "dict[Path, list[str]]":
    """태그를 읽은 문서와 그 태그. 읽을 수 없는 문서는 담지 않는다."""
    return scan_tags(root)[0]


def unreadable_tags(root: Path) -> "list[tuple[Path, TagFormatError]]":
    """tags를 읽을 수 없는 문서와 그 오류."""
    return scan_tags(root)[1]

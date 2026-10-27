#!/usr/bin/env python3
"""상류 묶음 파일 목록과 출고 목록 - 감사와 생성기가 함께 쓰는 공용 모듈.

상류 묶음은 경로 모양으로 가린다(_audit_core.is_bundle_path). 출고 목록
(MANIFEST_REL)은 묶음의 모든 파일(목록 자신 제외)을 한 줄에 하나씩
"<SHA-256 16진 소문자 64자><공백 둘><루트 상대 NFC POSIX 경로>"로 적고,
경로를 코드 포인트 순으로 늘어놓는다. sha256sum -c와 같은 형식이다.
해시는 파일 바이트에서 CRLF를 LF로 바꾼 뒤 잰다. 줄바꿈 변환이 있는
체크아웃에서도 같은 값이 나오게 하려는 것이다.
"""

import hashlib
import os
import re
from pathlib import Path

from _audit_core import (
    EXEMPT_DIRS, IMPLEMENTATION_DIR, NORMS_DIR_NAME,
    REFERENCE_DIR, is_bundle_path, nested_repo_dirs, nfc)
from _index_core import is_byproduct

MANIFEST_REL = "AGENTS/epistemic-rules/tools/bundle-manifest.sha256"
TOOLS_REL = "AGENTS/epistemic-rules/tools"

# 이 두 폴더 바로 아래에서는 규범 폴더만 본다.
_MATERIAL_PARTS = ((REFERENCE_DIR,), (IMPLEMENTATION_DIR,))
_LINE_RE = re.compile(r"^([0-9a-f]{64})  (\S.*)$")


class ManifestFormatError(ValueError):
    """출고 목록의 줄이 형식을 어겼다. line은 1부터 센 줄 번호다."""

    def __init__(self, message: str, line: int = 0):
        super().__init__(message)
        self.line = line


def _skipped_name(name: str) -> bool:
    """점으로 시작하는 이름, 운영체제 부산물, 파이썬 바이트코드는 묶음에 세지 않는다."""
    return name.startswith(".") or is_byproduct(name) or name.endswith(".pyc")


def bundle_files(root: Path) -> "list[Path]":
    """상류 묶음 경로의 파일 목록(출고 목록 자신 제외).

    루트 상대 NFC POSIX 경로 순이다. 감사 순회와 같은 가지치기(도구 전용
    폴더, 중첩 저장소, 심볼릭 링크)를 쓰고, reference/와 implementation/
    아래에서는 규범 폴더(AGENTS/)만 본다. 자료로 들여온 사본이나 하위
    프로젝트의 클론을 상류 묶음으로 오인하지 않으려는 것이다.
    """
    nested = set(nested_repo_dirs(root))
    found: "list[tuple[str, Path]]" = []
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        d = Path(dirpath)
        parts = d.relative_to(root).parts
        keep = []
        for name in sorted(dirnames):
            if name in EXEMPT_DIRS or _skipped_name(name):
                continue
            sub = d / name
            if sub in nested or sub.is_symlink():
                continue
            if (parts in _MATERIAL_PARTS and name != NORMS_DIR_NAME):
                continue
            keep.append(name)
        dirnames[:] = keep
        for name in filenames:
            path = d / name
            if _skipped_name(name) or path.is_symlink():
                continue
            if not is_bundle_path(root, path):
                continue
            rel = nfc(path.relative_to(root).as_posix())
            if rel == MANIFEST_REL:
                continue
            found.append((rel, path))
    found.sort(key=lambda item: item[0])
    return [p for _, p in found]


def file_digest(path: Path) -> str:
    """CRLF를 LF로 바꾼 파일 바이트의 SHA-256 16진 소문자."""
    data = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def render_manifest(root: Path) -> str:
    """bundle_files의 출고 목록 텍스트. 파일이 없으면 빈 문자열이다."""
    lines = []
    for path in bundle_files(root):
        rel = nfc(path.relative_to(root).as_posix())
        lines.append("%s  %s\n" % (file_digest(path), rel))
    return "".join(lines)


def read_manifest(path: Path) -> "dict[str, str]":
    """출고 목록을 {경로: 해시}로 읽는다.

    줄 형식이 어긋나거나 경로가 겹치면 ManifestFormatError를 낸다. 빈 줄도
    어긋난 줄이다. 줄 끝의 CRLF는 LF로 본다.
    """
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as e:
        line = raw[:e.start].count(b"\n") + 1
        raise ManifestFormatError("UTF-8이 아님", line) from None
    lines = text.replace("\r\n", "\n").split("\n")
    if lines[-1] == "":
        lines.pop()  # 마지막 줄바꿈 뒤의 빈 조각
    entries: "dict[str, str]" = {}
    for i, line in enumerate(lines):
        m = _LINE_RE.match(line)
        if not m:
            raise ManifestFormatError(
                "줄 형식이 '<SHA-256 소문자 64자>  <경로>'가 아님", i + 1)
        rel = nfc(m.group(2))
        if rel in entries:
            raise ManifestFormatError("경로가 겹침 - %s" % rel, i + 1)
        entries[rel] = m.group(1)
    return entries


def own_root(root: Path, tools_dir: Path) -> bool:
    """tools_dir이 root의 묶음 도구 폴더와 같으면 참."""
    return (root / TOOLS_REL).resolve() == tools_dir.resolve()

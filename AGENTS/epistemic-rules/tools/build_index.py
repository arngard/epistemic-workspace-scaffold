#!/usr/bin/env python3
"""폴더 색인 생성 진입점.

_index_core.render_all이 만든 색인 쪽을 디스크와 비교해 내용이 다른 쪽만
쓰고, 색인 폴더마다 필요한 쪽보다 뒤의 INDEX<n>.md를 지운다. 색인 폴더가
아니게 된 폴더(순차 분류 선언의 하위, AGENTS.md를 지운 폴더)에 남은 생성
쪽도 지운다. reference/ 자료 폴더 안은 건드리지 않는다. 파일을 쓰는
진입점은 이 파일 하나다. 렌더링은 _index_core, 대조 검사는 감사가 맡는다.
규칙의 원본은 AGENTS/epistemic-rules/folder-index.md다.

생성 쪽인지는 첫 줄이 생성 머리말인지로 가린다. 색인 폴더에 머리말 없는
INDEX*.md(사람이 쓴 파일)가 있으면 아무것도 쓰지 않고 실패한다. 색인
폴더가 아닌 폴더의 머리말 없는 파일은 지우지 않는다.

git이 있고 루트가 작업 트리 안이면 색인 항목 가운데 git이 무시하는 파일이
있는지 확인하고, 있으면 쓰지 않고 실패한다. 무시 파일은 색인 폴더 바로
아래가 아니라 .tmp/에 둔다. .git이 폴더인 내장 클론은 색인 항목이 아니라
이 확인에도 들지 않는다. git이 없으면 이 확인을 건너뛴다.

사용법:
    python3 AGENTS/epistemic-rules/tools/build_index.py [루트] [--dry-run]
    (루트를 생략하면 현재 디렉토리. --dry-run은 쓰지 않고 바뀔 경로만 낸다.
     윈도우에서는 python 또는 py -3으로 같게 실행)

출력:
    쓰거나 지운(--dry-run이면 쓰거나 지울) 파일의 루트 상대 POSIX 경로를
    정렬해 한 줄에 하나씩 표준 출력에 낸다. 바뀐 것이 없으면 아무것도 내지
    않는다. 경로는 디스크 이름 그대로다(유니코드 정규화를 하지 않는다).

종료 코드:
    0  성공
    2  INDEX.yaml 형식 오류, git 무시 파일이 색인 항목에 있음, 색인 폴더에
       사람이 쓴 INDEX*.md가 있음, 인자 오류, 파일 읽기 쓰기 오류.
       원인(파일, 줄)은 표준 오류에 낸다.
"""

import argparse
import os
import subprocess
import sys
import unicodedata
from pathlib import Path
from typing import Optional

from _audit_core import INDEX_PAGE_RE
from _index_core import (
    IndexFormatError, entry_paths, in_reference_subfolder, index_dirs,
    is_generated_page, non_index_dirs, render_all)

_ENC = ("utf-8", "surrogateescape")


class HandWrittenIndexError(Exception):
    """색인 폴더에 생성 머리말이 없는 INDEX*.md가 있다. paths는 그 파일들이다."""

    def __init__(self, paths: "list[Path]"):
        super().__init__("hand-written index")
        self.paths = paths


def _rel(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def build(root: Path, dry_run: bool = False) -> "list[str]":
    """색인 쪽을 쓰고 남는 쪽을 지운다. 바뀐 파일의 루트 상대 경로를 돌려준다.

    쓰기 전에 쓸 내용과 지울 파일을 모두 계산하므로 IndexFormatError가 나면
    아무 파일도 바뀌지 않는다. 내용은 바이트로 비교하고 써서 줄바꿈이 OS에
    따라 바뀌지 않는다. 색인 폴더에 생성 머리말 없는 INDEX*.md가 있으면
    HandWrittenIndexError를 내고 아무 파일도 바꾸지 않는다.
    """
    pages = render_all(root)
    dirs = index_dirs(root)
    hand: "list[Path]" = []
    removes: "list[Path]" = []
    for d in dirs:
        for p in sorted(d.iterdir()):
            if not INDEX_PAGE_RE.match(p.name) or p.is_dir():
                continue
            if not is_generated_page(p):
                hand.append(p)
            elif p not in pages:
                removes.append(p)
    # 대소문자를 가리지 않는 파일시스템에서 index.md 같은 이름도 덮어쓰지 않는다.
    for path in pages:
        if path.is_file() and path not in hand and path not in removes \
                and not is_generated_page(path):
            hand.append(path)
    if hand:
        raise HandWrittenIndexError(sorted(hand))
    for d in non_index_dirs(root, set(dirs)):
        if in_reference_subfolder(root, d):
            continue
        for p in sorted(d.iterdir()):
            if (INDEX_PAGE_RE.match(p.name) and p.is_file()
                    and is_generated_page(p)):
                removes.append(p)
    writes: "list[tuple[Path, bytes]]" = []
    for path, text in pages.items():
        data = text.encode("utf-8")
        if path.is_file() and path.read_bytes() == data:
            continue
        writes.append((path, data))
    if not dry_run:
        for path, data in writes:
            path.write_bytes(data)
        for p in removes:
            p.unlink()
    changed = [_rel(root, p) for p, _ in writes] + [_rel(root, p) for p in removes]
    return sorted(changed)


def _git(root: Path, args: "list[str]",
         stdin: "Optional[bytes]" = None) -> "subprocess.CompletedProcess":
    return subprocess.run(["git", *args], cwd=str(root), input=stdin,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def ignored_entries(root: Path, paths: "list[Path]") -> "list[str]":
    """paths 가운데 git이 무시하는 것의 루트 상대 POSIX 경로(정렬).

    git이 없거나 root가 작업 트리 안이 아니면 빈 목록이다. git 확인 자체가
    실패하면 RuntimeError를 낸다.
    """
    if not paths:
        return []
    try:
        probe = _git(root, ["rev-parse", "--is-inside-work-tree"])
    except OSError:
        return []
    if probe.returncode != 0 or probe.stdout.strip() != b"true":
        return []
    # core.precomposeunicode가 켜진 git(macOS)은 이름을 NFC로 다루므로 디스크의
    # NFD 이름을 NFC로 바꿔 넘긴다. 꺼져 있으면 바이트 그대로 비교하므로 두지 않는다.
    pre = _git(root, ["config", "--bool", "core.precomposeunicode"])
    precompose = pre.stdout.strip() == b"true"
    rels = [_rel(root, p) for p in paths]
    if precompose:
        rels = [unicodedata.normalize("NFC", r) for r in rels]
    data = b"".join(r.encode(*_ENC) + b"\0" for r in rels)
    r = _git(root, ["check-ignore", "--stdin", "-z"], data)
    # 종료 코드 1은 무시 파일이 없다는 뜻이다.
    if r.returncode not in (0, 1):
        raise RuntimeError(r.stderr.decode(*_ENC).strip())
    return sorted(s.decode(*_ENC) for s in r.stdout.split(b"\0") if s)


def _format_error(root: Path, e: IndexFormatError) -> str:
    """오류 위치를 감사 출력처럼 루트 상대 경로로 적는다."""
    if e.path is None:
        return str(e)
    try:
        where = Path(e.path).relative_to(root).as_posix()
    except ValueError:
        where = str(e.path)
    if e.line:
        where = "%s:%d" % (where, e.line)
    return "%s: %s" % (where, e.message)


def _setup_streams() -> None:
    # 윈도우 콘솔에서도 한글이 깨지지 않게 UTF-8로 강제한다. 표준 출력은
    # 훅이 줄 단위로 읽으므로 CRLF가 되지 않게 LF로 고정한다.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="surrogateescape",
                               newline="\n")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def main(argv: "Optional[list[str]]" = None) -> int:
    _setup_streams()
    parser = argparse.ArgumentParser(description="폴더 색인을 만든다.")
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    if not root.is_dir():
        print("Error: not a directory. 디렉토리가 아님 - %s" % root,
              file=sys.stderr)
        return 2
    try:
        ignored = ignored_entries(root, entry_paths(root))
        if ignored:
            for rel in ignored:
                if (root / rel / ".git").is_file():
                    hint = ("git이 무시하는 중첩 저장소가 색인 항목이다. "
                            "무시를 풀거나 색인 폴더 밖으로 옮긴다.")
                else:
                    hint = "git 무시 파일이 색인 항목이다. .tmp/로 옮긴다."
                print("Error: ignored file in index. %s: %s" % (rel, hint),
                      file=sys.stderr)
            return 2
        changed = build(root, dry_run=args.dry_run)
    except HandWrittenIndexError as e:
        for p in e.paths:
            print("Error: hand-written index. %s: 생성 머리말이 없는 색인 "
                  "파일이다. 내용을 다른 이름으로 옮기고 지운 뒤 다시 "
                  "실행한다." % _rel(root, p), file=sys.stderr)
        return 2
    except IndexFormatError as e:
        print("Error: index format. %s" % _format_error(root, e),
              file=sys.stderr)
        return 2
    except (OSError, RuntimeError) as e:
        print("Error: index build failed. %s" % e, file=sys.stderr)
        return 2
    for rel in changed:
        print(rel)
    return 0


if __name__ == "__main__":
    sys.exit(main())

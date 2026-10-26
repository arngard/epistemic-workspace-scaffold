#!/usr/bin/env python3
"""폴더 색인 생성 진입점.

_index_core.render_all이 만든 색인 쪽을 디스크와 비교해 내용이 다른 쪽만
쓰고, 색인 폴더마다 필요한 쪽보다 뒤의 INDEX<n>.md를 지운다. 파일을 쓰는
진입점은 이 파일 하나다. 렌더링은 _index_core, 대조 검사는 감사가 맡는다.
규칙의 원본은 AGENTS/epistemic-rules/folder-index.md다.

git이 있고 루트가 작업 트리 안이면 색인 항목 가운데 git이 무시하는 파일이
있는지 확인하고, 있으면 쓰지 않고 실패한다. 무시 파일은 색인 폴더 바로
아래가 아니라 .tmp/에 둔다. git이 없으면 이 확인을 건너뛴다.

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
    2  INDEX.yaml 형식 오류, git 무시 파일이 색인 항목에 있음, 인자 오류,
       파일 읽기 쓰기 오류. 원인(파일, 줄)은 표준 오류에 낸다.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

from _audit_core import INDEX_PAGE_RE
from _index_core import IndexFormatError, entry_paths, index_dirs, render_all

_ENC = ("utf-8", "surrogateescape")


def _rel(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def build(root: Path, dry_run: bool = False) -> "list[str]":
    """색인 쪽을 쓰고 남는 쪽을 지운다. 바뀐 파일의 루트 상대 경로를 돌려준다.

    쓰기 전에 쓸 내용과 지울 파일을 모두 계산하므로 IndexFormatError가 나면
    아무 파일도 바뀌지 않는다. 내용은 바이트로 비교하고 써서 줄바꿈이 OS에
    따라 바뀌지 않는다.
    """
    pages = render_all(root)
    writes: "list[tuple[Path, bytes]]" = []
    for path, text in pages.items():
        data = text.encode("utf-8")
        if path.is_file() and path.read_bytes() == data:
            continue
        writes.append((path, data))
    removes: "list[Path]" = []
    for d in index_dirs(root):
        for p in d.iterdir():
            if INDEX_PAGE_RE.match(p.name) and p not in pages and not p.is_dir():
                removes.append(p)
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
    data = b"".join(_rel(root, p).encode(*_ENC) + b"\0" for p in paths)
    r = _git(root, ["check-ignore", "--stdin", "-z"], data)
    # 종료 코드 1은 무시 파일이 없다는 뜻이다.
    if r.returncode not in (0, 1):
        raise RuntimeError(r.stderr.decode(*_ENC).strip())
    return sorted(s.decode(*_ENC) for s in r.stdout.split(b"\0") if s)


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
                print("Error: ignored file in index. %s: git 무시 파일이 "
                      "색인 항목이다. .tmp/로 옮긴다." % rel, file=sys.stderr)
            return 2
        changed = build(root, dry_run=args.dry_run)
    except IndexFormatError as e:
        print("Error: index format. %s" % e, file=sys.stderr)
        return 2
    except (OSError, RuntimeError) as e:
        print("Error: index build failed. %s" % e, file=sys.stderr)
        return 2
    for rel in changed:
        print(rel)
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""태그 병합과 삭제 실행 - 승인된 대응(옛 태그=새 태그)과 삭제를 front matter
tags에 적용한다.

사용자가 승인한 변경만 명시적으로 실행하는 편집 도구다. 감사(audit.py)와
색인 생성(build_index.py), 커밋 전 훅은 이 도구를 부르지 않는다. 어떤 태그를
합치거나 지울지는 의미 판단이라 도구가 정하지 않는다(후보는 tag_inventory.py
목록과 의미 감사가 낸다). 수천 문서에 걸치는 변경을 손이나 즉석 sed로 하면
front matter 밖을 건드리거나 상류 문서를 바꾸는 사고가 규모에 비례해
늘어나서, 같은 일을 이 도구 하나로 한다.

적용 규칙:
- 대상은 front matter의 tags 값 영역뿐이다. 영역 밖의 바이트와 파일의 줄바꿈
  방식(LF, CRLF)은 그대로다. 파일을 바이트로 읽고 쓴다.
- 문서 범위와 읽기 규칙은 감사와 같다(_tags_core.scan_tags,
  find_tags_block). 읽기와 다시 쓰기가 같은 코드라 감사가 못 본 태그를 바꾸지
  않는다. 태그를 읽을 수 없는 문서는 바꾸지 않고 보고한다.
- 옛 태그와 지울 태그는 NFC로 바꾼 뒤 정확히 같은 표기만 바꾸거나 지운다.
  대소문자나 표기 변형은 변형마다 따로 준다.
- 대응과 삭제는 원래 태그에 동시에 적용한다. 사슬로 잇지 않는다(a=b와 b=c는
  a를 b로, b를 c로). 지울 태그가 대응의 옛 태그나 새 태그와 같으면 한 실행의
  뜻이 모호하므로 거부한다.
- 문서 범위를 --path(루트 상대 POSIX 경로, 파일이나 폴더)로 좁히면 그 파일과
  그 폴더 아래 문서만 본다. "s"는 "s2/" 아래를 포함하지 않고 "."은 루트
  전체다. 경로가 절대 경로이거나 ".."이나 역슬래시를 담거나 없거나, 태그를
  모으는 문서가 하나도 맞지 않으면(대소문자만 다른 경로 등) 아무것도 쓰지
  않고 거부한다.
- 바꾼 뒤 같은 태그가 겹치면 처음 자리 하나만 남긴다.
- 흐름형과 블록형 표기를 유지한다. 영역 안의 항목은 다시 써서 따옴표는 필요한
  항목에만 붙는다. 대응에 걸리는 태그가 없는 문서는 쓰지 않는다.
- 영역 안에 주석이 있고(블록형 항목 줄의 "- a # 메모") 대응이 그 문서를
  바꾸게 되면 쓰지 않고 따로 보고한다. 다시 쓰면 주석이 조용히 사라지기
  때문이다. 주석을 지워도 되면 사용자가 그 문서를 직접 고친다.
  닫는 대괄호 뒤의 주석은 영역 밖이라 그대로 남는다.
- date modified를 바꾸지 않는다. 태그 병합은 기계적 변경이라 문서 내용을
  고쳤다는 뜻이 아니고, 날짜를 바꾸면 병합이 문서 수천 개의 수정일을 한꺼번에
  밀어 버린다.
- 상류 규범 묶음 문서는 건너뛰고 보고한다. 상류 저장소에서 자기 묶음 문서를
  바꿀 때만 --include-bundles를 쓴다. 상속한 저장소가 묶음 문서를 바꾸면 감사의
  동일성 검사(항목 30)가 위반으로 잡는다.
- 새 태그가 형태 규칙(공백, 숫자만의 태그, 빈 태그 금지)을 어기거나 같은 옛
  태그에 다른 새 태그가 둘이거나 지울 태그가 비어 있으면 아무것도 쓰지 않고
  거부한다.
- 쓰기는 문서마다 같은 폴더의 임시 파일에 쓴 뒤 os.replace로 바꾸고(원래 파일
  모드를 유지한다), 읽기 전용 파일은 바꾸지 않는다. 문서 하나의 쓰기 오류는
  그 문서만 실패로 모으고 나머지는 계속한다. 문서 안에서는 전부 쓰이거나 하나도
  안 쓰이지만 문서 사이에서는 일부만 바뀔 수 있으므로, 바뀐 문서와 쓰지 못한
  문서를 모두 보고한다.
- 새 태그가 이미 있는 다른 표기(대소문자 등)와 열쇠(tag_key)가 같으면 쓰되
  그 표기들을 주의로 알린다. 표기를 하나로 모으려면 그 표기도 대응에 넣는다.

사용법:
    python3 AGENTS/epistemic-rules/tools/retag.py [루트] [--map 옛=새 ...]
        [--drop 태그 ...] [--path 경로 ...] [--dry-run] [--include-bundles]
    (--map과 --drop은 여러 번 줄 수 있고 둘 중 하나는 있어야 한다. --path도
     여러 번 줄 수 있고, 없으면 태그를 모으는 문서 전부를 본다. 루트를 생략하면
     현재 디렉토리. --dry-run은 쓰지 않고 바뀔 문서만 낸다. 옛 태그에 =가 있으면
     쓸 수 없다. 첫 =가 옛과 새를 가른다)

출력(표준 출력): 절 여섯을 이 순서로 항상 낸다. 문서는 루트 상대 POSIX 경로,
한 줄에 하나, 경로 순이다.
    # 바뀐 문서 (N)        --dry-run이면 "# 바뀔 문서 (N)"
    # 상류 묶음이라 건너뜀 (N)
    # tags 안 주석이라 건너뜀 (N)
    # 읽을 수 없음 (N)
    # 쓰지 못함 (N)        사유는 표준 오류에 한 줄씩
    # 주의: 표기만 다른 태그가 함께 남음 (N)   줄마다 표기들을 ", "로 이음

종료 코드:
    0  성공(건너뛴 문서, 읽을 수 없는 문서, 주의가 있어도 0)
    2  새 태그가 형태 규칙을 어김, 같은 옛 태그에 다른 새 태그, 같은 태그를
       대응과 삭제에 함께 줌, 빈 지울 태그, 잘못되거나 문서가 맞지 않는
       --path, --map과 --drop이 둘
       다 없음, 인자 오류, 루트가 디렉토리가 아님, 문서 하나라도 쓰지
       못함(나머지는 이미 바뀌었을 수 있으니 출력의 두 절로 확인한다)
"""

import argparse
import errno
import os
import stat
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

from _audit_core import FRONT_MATTER_RE, is_bundle_path, nfc
from _tags_core import (
    TagFormatError, find_tags_block, render_tags, scan_tags, tag_form_problem,
    tag_key)

_ENC = ("utf-8", "surrogateescape")


@dataclass
class RetagReport:
    """병합 결과. 모두 루트 상대 POSIX 경로 목록(경로 순)이다."""

    changed: "list[str]" = field(default_factory=list)
    skipped_bundle: "list[str]" = field(default_factory=list)
    unreadable: "list[str]" = field(default_factory=list)
    # tags 값 영역 안에 주석이 있어 쓰지 않은 문서.
    skipped_comment: "list[str]" = field(default_factory=list)
    # 쓰기에 실패한 문서와 사유. dry_run이면 비어 있다.
    failed: "list[str]" = field(default_factory=list)
    failed_reasons: "dict[str, str]" = field(default_factory=dict)
    # 쓴 뒤 열쇠(tag_key)가 같은데 표기가 다른 채 함께 남는 태그 묶음.
    collisions: "list[tuple[str, ...]]" = field(default_factory=list)


class RegionCommentError(ValueError):
    """tags 값 영역 안에 주석이 있어 다시 쓰면 주석이 사라진다."""


def build_mapping(pairs) -> "dict[str, str]":
    """(옛, 새) 쌍들을 NFC로 바꿔 대응 하나로 합친다.

    새 태그가 형태 규칙을 어기거나 같은 옛 태그에 다른 새 태그가 있으면
    ValueError를 낸다.
    """
    mapping: "dict[str, str]" = {}
    for old, new in pairs:
        old, new = nfc(old), nfc(new)
        if not old:
            raise ValueError("옛 태그가 비어 있다")
        problem = tag_form_problem(new)
        if problem:
            raise ValueError('새 태그 "%s"가 형태 규칙을 어긴다 - %s' % (new, problem))
        if old in mapping and mapping[old] != new:
            raise ValueError(
                '옛 태그 "%s"에 새 태그가 둘이다 - "%s", "%s"'
                % (old, mapping[old], new))
        mapping[old] = new
    return mapping


def build_drop(tags, mapping: "dict[str, str]") -> "frozenset[str]":
    """지울 태그들을 NFC로 바꾼 집합.

    빈 태그가 있거나, 지울 태그가 대응의 옛 태그나 새 태그와 같으면
    ValueError를 낸다.
    """
    drop = frozenset(nfc(t) for t in tags)
    if "" in drop:
        raise ValueError("지울 태그가 비어 있다")
    both = sorted(drop & (set(mapping) | set(mapping.values())))
    if both:
        raise ValueError(
            '같은 태그를 대응과 삭제에 함께 주었다 - "%s"' % '", "'.join(both))
    return drop


def build_scope(root: Path, paths) -> "list[str] | None":
    """--path 값들을 루트 상대 POSIX 경로 목록으로 맞춘다.

    None이면 범위 제한이 없고, 빈 목록이면 아무 문서도 보지 않는다.
    빈 값, 역슬래시, 절대 경로, ".." 성분, 루트 아래에 없는 경로는 ValueError를
    낸다. "."은 루트 전체다.
    """
    if paths is None:
        return None
    scope = []
    for raw in paths:
        p = PurePosixPath(nfc(raw))
        if not raw or "\\" in raw or p.is_absolute() or ".." in p.parts:
            raise ValueError("루트 상대 경로가 아니다 - %s" % raw)
        if not (root / p).exists():
            raise ValueError("경로가 없다 - %s" % raw)
        scope.append(p.as_posix())
    return scope


def _in_scope(rel: str, scope: "list[str] | None") -> bool:
    """rel이 scope의 파일과 같거나 scope 폴더 아래에 있는가."""
    if scope is None:
        return True
    return any(_under(nfc(rel), s) for s in scope)


def _under(rel: str, s: str) -> bool:
    return s == "." or rel == s or rel.startswith(s + "/")


def _check_scope_hits(scope: "list[str] | None", rels) -> None:
    """범위 항목마다 태그를 모으는 문서가 하나라도 맞는지 본다.

    맞는 문서가 없는 항목이 있으면 ValueError를 낸다. 파일 시스템이 대소문자를
    가리지 않아 존재 확인을 통과한 경로가 문서 경로와 맞지 않는 경우 등을
    잡는다.
    """
    if scope is None:
        return
    rels = [nfc(r) for r in rels]
    for s in scope:
        if not any(_under(r, s) for r in rels):
            raise ValueError("태그를 모으는 문서가 맞지 않는 경로 - %s" % s)


def _touches(tags, mapping: "dict[str, str]", drop: "frozenset[str]") -> bool:
    """대응이나 삭제에 걸리는 태그가 있는가."""
    return any(t in drop or mapping.get(t, t) != t for t in tags)


def _map_tags(
    tags: "tuple[str, ...]",
    mapping: "dict[str, str]",
    drop: "frozenset[str]" = frozenset(),
) -> "list[str]":
    """원래 태그에 삭제와 대응을 동시에 적용하고 겹친 태그는 처음 자리만 남긴다."""
    return list(dict.fromkeys(
        mapping.get(t, t) for t in tags if t not in drop))


def rewrite_text(
    text: str,
    mapping: "dict[str, str]",
    expected: "list[str]",
    drop: "frozenset[str]" = frozenset(),
):
    """파일 전문 text의 tags 값 영역을 대응과 삭제대로 다시 쓴 텍스트를 돌려준다.

    대응이나 삭제에 걸리는 태그가 없으면 None. text가 감사가 읽은
    태그(expected)와 다르게 읽히거나 쓴 결과를 다시 읽어 맞지 않으면
    ValueError를 낸다.
    """
    m = FRONT_MATTER_RE.match(text)
    if not m:
        raise ValueError("front matter를 찾지 못했다")
    front = m.group(1)
    try:
        block = find_tags_block(front)
    except TagFormatError as e:
        raise ValueError(str(e)) from None
    if block is None or list(block.tags) != expected:
        raise ValueError("파일 바이트에서 읽은 태그가 감사가 읽은 태그와 다르다")
    new_tags = _map_tags(block.tags, mapping, drop)
    if not _touches(block.tags, mapping, drop):
        return None
    if block.comment:
        raise RegionCommentError("tags 값 영역 안에 주석이 있다")
    start = m.start(1) + block.start
    end = m.start(1) + block.end
    newline = "\r\n" if text[start:end].startswith("\r\n") else "\n"
    new_text = text[:start] + render_tags(block, new_tags, newline) + text[end:]
    again = FRONT_MATTER_RE.match(new_text)
    check = find_tags_block(again.group(1)) if again else None
    if check is None or list(check.tags) != new_tags:
        raise ValueError("다시 쓴 tags를 같은 규칙으로 읽으면 맞지 않는다")
    return new_text


def _write_atomic(path: Path, data: bytes) -> None:
    """같은 폴더의 임시 파일에 쓴 뒤 바꿔 넣는다. 원래 파일 모드를 유지한다.

    읽기 전용 파일은 바꾸지 않는다(폴더 권한만으로 바뀌지 않게 한다).
    실패하면 임시 파일을 지우고 OSError를 그대로 올린다.
    """
    if not os.access(str(path), os.W_OK):
        raise PermissionError(errno.EACCES, "쓰기 권한이 없다", str(path))
    mode = stat.S_IMODE(path.stat().st_mode)
    fd, tmp = tempfile.mkstemp(
        dir=str(path.parent), prefix=".retag-", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        os.chmod(tmp, mode)
        os.replace(tmp, str(path))
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _collisions(
    docs: "dict[Path, list[str]]",
    rewritten: "dict[Path, list[str]]",
    introduced: "set[str]",
) -> "list[tuple[str, ...]]":
    """쓴 뒤의 어휘에서 새로 들인 표기와 열쇠가 같은 다른 표기 묶음."""
    spellings: "set[str]" = set()
    for path, tags in docs.items():
        spellings.update(rewritten.get(path, tags))
    groups: "dict[str, set[str]]" = {}
    for tag in spellings:
        groups.setdefault(tag_key(tag), set()).add(tag)
    out = []
    for key in sorted(groups):
        forms = groups[key]
        if len(forms) > 1 and forms & introduced:
            out.append(tuple(sorted(forms)))
    return out


def retag(
    root: Path,
    mapping: "dict[str, str]",
    dry_run: bool = False,
    include_bundles: bool = False,
    drop=frozenset(),
    paths=None,
) -> RetagReport:
    """대응과 삭제를 태그를 모으는 문서의 front matter tags에 적용한다.

    drop은 지울 태그 집합, paths는 범위를 좁히는 루트 상대 POSIX 경로
    목록이다(파일이나 폴더, None이면 전부, 빈 목록이면 아무 문서도 보지
    않는다). 새 태그가 형태 규칙을 어기거나, 대응이 모순이거나, drop의 태그가
    대응의 옛 태그나 새 태그와 같거나, drop에 빈 태그가 있거나, paths가
    잘못되거나 문서가 맞지 않으면 아무것도 하지 않고 ValueError를 낸다.
    그 밖에는 바뀔 문서를 모두 계산한 뒤 쓴다. 쓰기는 문서마다 임시 파일과
    os.replace로 해서 한 문서는 전부 쓰이거나 하나도 안 쓰이고, 쓰기 오류는
    문서마다 failed에 모으며 나머지를 계속한다. 그래서 문서 사이에서는
    일부만 바뀔 수 있고 changed(쓴 문서)와 failed(쓰지 못한 문서)가 그 경계다.
    dry_run이면 쓰지 않고 changed에 바뀔 문서를 담는다.
    """
    mapping = build_mapping(mapping.items())
    drop = build_drop(drop, mapping)
    scope = build_scope(root, paths)
    docs, errors = scan_tags(root)

    def rel(p: Path) -> str:
        return p.relative_to(root).as_posix()

    _check_scope_hits(
        scope, [rel(p) for p in docs] + [rel(p) for p, _ in errors])
    docs = {p: t for p, t in docs.items() if _in_scope(rel(p), scope)}
    report = RetagReport()
    unreadable = {rel(p) for p, _ in errors if _in_scope(rel(p), scope)}
    pending: "list[tuple[Path, str]]" = []
    rewritten: "dict[Path, list[str]]" = {}
    introduced: "set[str]" = set()
    for path in sorted(docs, key=rel):
        tags = docs[path]
        if not _touches(tags, mapping, drop):
            continue
        if is_bundle_path(root, path) and not include_bundles:
            report.skipped_bundle.append(rel(path))
            continue
        try:
            text = path.read_bytes().decode(*_ENC)
            new_text = rewrite_text(text, mapping, tags, drop)
        except RegionCommentError:
            report.skipped_comment.append(rel(path))
            continue
        except (ValueError, OSError):
            unreadable.add(rel(path))
            continue
        if new_text is not None:
            pending.append((path, new_text))
            rewritten[path] = _map_tags(tuple(tags), mapping, drop)
            introduced.update(mapping[t] for t in tags if mapping.get(t, t) != t)
    report.unreadable = sorted(unreadable)
    report.collisions = _collisions(docs, rewritten, introduced)
    for path, new_text in pending:
        if dry_run:
            report.changed.append(rel(path))
            continue
        try:
            _write_atomic(path, new_text.encode(*_ENC))
        except OSError as e:
            report.failed.append(rel(path))
            report.failed_reasons[rel(path)] = str(e)
        else:
            report.changed.append(rel(path))
    return report


def _setup_streams() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="surrogateescape",
                               newline="\n")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def _parse_pair(arg: str) -> "tuple[str, str]":
    old, sep, new = arg.partition("=")
    if not sep or not old or not new:
        raise argparse.ArgumentTypeError(
            "--map은 옛=새 형식이고 양쪽이 비어 있으면 안 된다 - %s" % arg)
    return old, new


def main(argv: "list[str] | None" = None) -> int:
    _setup_streams()
    parser = argparse.ArgumentParser(
        description="승인된 태그 대응과 삭제를 적용한다.")
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument("--map", dest="maps", action="append", default=[],
                        type=_parse_pair, metavar="옛=새",
                        help="바꿀 태그 대응(여러 번 줄 수 있다)")
    parser.add_argument("--drop", dest="drops", action="append", default=[],
                        metavar="태그", help="지울 태그(여러 번 줄 수 있다)")
    parser.add_argument("--path", dest="paths", action="append", default=None,
                        metavar="경로",
                        help="루트 상대 파일이나 폴더로 범위를 좁힌다(여러 번)")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--include-bundles", action="store_true",
                        help="상류 묶음 문서도 바꾼다(상류 저장소 전용)")
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else 2
    if not args.maps and not args.drops:
        print("Error: nothing to do. --map이나 --drop이 하나는 있어야 한다",
              file=sys.stderr)
        return 2
    root = Path(args.root).resolve()
    if not root.is_dir():
        print("Error: not a directory. 디렉토리가 아님 - %s" % root,
              file=sys.stderr)
        return 2
    try:
        mapping = build_mapping(args.maps)
        report = retag(root, mapping, dry_run=args.dry_run,
                       include_bundles=args.include_bundles,
                       drop=args.drops, paths=args.paths)
    except ValueError as e:
        print("Error: invalid arguments. 대응, 삭제, 범위가 잘못됨 - %s" % e,
              file=sys.stderr)
        return 2
    except OSError as e:
        print("Error: retag failed. 쓰기 실패 - %s" % e, file=sys.stderr)
        return 2
    sections = (
        ("바뀔 문서" if args.dry_run else "바뀐 문서", report.changed),
        ("상류 묶음이라 건너뜀", report.skipped_bundle),
        ("tags 안 주석이라 건너뜀", report.skipped_comment),
        ("읽을 수 없음", report.unreadable),
        ("쓰지 못함", report.failed),
    )
    for title, paths in sections:
        print("# %s (%d)" % (title, len(paths)))
        for p in paths:
            print(p)
    print("# 주의: 표기만 다른 태그가 함께 남음 (%d)" % len(report.collisions))
    for forms in report.collisions:
        print(", ".join(forms))
    for p in report.failed:
        print("Error: write failed. 쓰기 실패 - %s: %s"
              % (p, report.failed_reasons[p]), file=sys.stderr)
    return 2 if report.failed else 0


if __name__ == "__main__":
    sys.exit(main())

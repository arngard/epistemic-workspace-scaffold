#!/usr/bin/env python3
"""태그 어휘 목록 - front matter tags의 태그별 사용 현황을 TSV로 낸다.

읽기 전용 보조 도구다. 파일을 쓰지 않는다. 의미 감사가 뜻이 같은 태그를
찾을 때 이 목록을 읽고, 합칠 태그가 정해지면 승인된 대응만 retag.py로
실행한다. 감사(audit.py)와 색인 생성(build_index.py)은 이 도구를 부르지
않는다.

문서 범위와 읽기 규칙은 감사와 같다(_tags_core.scan_tags). 같은 문서 안의
중복 태그는 한 번만 센다. 읽을 수 없는 tags를 가진 문서는 목록에 들지
않고 표준 오류에 한 줄씩 낸다.

사용법:
    python3 AGENTS/epistemic-rules/tools/tag_inventory.py [루트]
    (루트를 생략하면 현재 디렉토리)

출력(표준 출력, 탭 구분):
    머리 줄 "수<TAB>태그<TAB>상류<TAB>예시" 다음에 태그마다 한 줄.
    정렬은 tag_key(표기 차이를 지운 열쇠) 다음 태그 문자열 순이라 표기만
    다른 태그가 이웃한다.
    - 수: 그 태그를 가진 문서 수.
    - 상류: 상류 규범 묶음 문서가 쓰면 "예", 아니면 "아니오". 상류가 쓰는
      태그는 자손에서 바뀌는 쪽이 될 수 없다.
    - 예시: 루트 상대 POSIX 경로 최대 셋을 "; "로 이은 것. 묶음 밖 문서를
      먼저, 그 안에서 경로 순으로 고른다(고칠 수 있는 파일을 먼저 보이기
      위해서다).

종료 코드:
    0  성공
    2  루트가 디렉토리가 아님, 인자 오류
"""

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

from _audit_core import is_bundle_path
from _tags_core import scan_tags, tag_key

MAX_EXAMPLES = 3


@dataclass(frozen=True)
class TagUse:
    """태그 하나의 사용 현황."""

    tag: str
    count: int
    upstream: bool
    examples: "tuple[str, ...]"


def inventory(root: Path) -> "list[TagUse]":
    """태그별 사용 현황을 tag_key 다음 tag 순으로 돌려준다."""
    docs, _ = scan_tags(root)
    uses: "dict[str, list[tuple[bool, str]]]" = {}
    for path, tags in docs.items():
        rel = path.relative_to(root).as_posix()
        bundle = is_bundle_path(root, path)
        for tag in dict.fromkeys(tags):
            uses.setdefault(tag, []).append((bundle, rel))
    out = []
    for tag in sorted(uses, key=lambda t: (tag_key(t), t)):
        found = sorted(uses[tag])  # 묶음 밖(False)이 먼저, 그 안에서 경로 순
        out.append(TagUse(
            tag=tag,
            count=len(found),
            upstream=any(b for b, _ in found),
            examples=tuple(rel for _, rel in found[:MAX_EXAMPLES]),
        ))
    return out


def _cell(text: str) -> str:
    """TSV 칸을 깨는 탭과 줄바꿈을 공백으로 바꾼다."""
    return " ".join(text.replace("\t", " ").splitlines()) if text else text


def _setup_streams() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="surrogateescape",
                               newline="\n")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def main(argv: "list[str] | None" = None) -> int:
    _setup_streams()
    parser = argparse.ArgumentParser(description="태그 어휘 목록을 TSV로 낸다.")
    parser.add_argument("root", nargs="?", default=".")
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else 2
    root = Path(args.root).resolve()
    if not root.is_dir():
        print("Error: not a directory. 디렉토리가 아님 - %s" % root,
              file=sys.stderr)
        return 2
    _, errors = scan_tags(root)
    for path, err in sorted(errors, key=lambda e: e[0].relative_to(root).as_posix()):
        where = " (%d행)" % err.line if err.line else ""
        print("Error: unreadable tags. tags를 읽을 수 없음 - %s%s: %s"
              % (path.relative_to(root).as_posix(), where, err),
              file=sys.stderr)
    print("수\t태그\t상류\t예시")
    for use in inventory(root):
        print("%d\t%s\t%s\t%s" % (
            use.count, _cell(use.tag), "예" if use.upstream else "아니오",
            _cell("; ".join(use.examples))))
    return 0


if __name__ == "__main__":
    sys.exit(main())

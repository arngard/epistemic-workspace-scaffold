"""front matter와 스키마 필드 검사.

공용 인프라는 _audit_core, 오케스트레이션은 audit.py.
"""
import re
import urllib.parse
from pathlib import Path

from _audit_core import *  # noqa: F401,F403 - Finding, 상수, 공용 헬퍼


def check_front_matter(root: Path) -> list[Finding]:
    out: list[Finding] = []
    for path in iter_md_files(root):
        if path.name in EXEMPT_FILENAMES:
            continue
        text = read(path)
        match = FRONT_MATTER_RE.match(text)
        rel = str(path.relative_to(root))
        if not match:
            out.append(Finding(VIOLATION, "front-matter", rel, "YAML front matter 없음"))
            continue
        body = match.group(1)
        for field in ("date created", "date modified", "tags"):
            if not re.search(rf"^{re.escape(field)}\s*:", body, re.MULTILINE):
                out.append(Finding(VIOLATION, "front-matter", rel, f"필수 필드 누락 - {field}"))
        # 날짜 필드 값 형식 검증 (제노 1.1/3.1) - 필드 존재만 보고 값을 안 봐서
        # 스키마가 우회되던 것을 막는다. 필드가 있을 때만 값을 검사한다.
        for field in ("date created", "date modified", "date closed"):
            vm = re.search(rf"^{re.escape(field)}\s*:\s*(\S.*?)\s*$", body, re.MULTILINE)
            if vm and not DATE_VALUE_RE.match(vm.group(1)):
                out.append(Finding(
                    VIOLATION, "front-matter", rel,
                    f'{field} 값 형식 오류 - yyyy-MM-dd 기대, 실제 "{vm.group(1)}"',
                ))
        # date closed는 선택 필드이며 히스토리 문서(날짜 프리픽스) 전용이다.
        # 프리픽스 없는 현재적 문서에 달리면 시간성 혼합 신호 (proposal 3).
        if re.search(r"^date closed\s*:", body, re.MULTILINE) and not has_date_prefix(path):
            out.append(Finding(
                VIOLATION, "temporality", rel,
                "날짜 프리픽스 없는 문서에 date closed - 현재적 문서에는 종결 개념이 없다 (시간성 혼합)",
            ))
    return out


def check_strategy_fields(root: Path) -> list[Finding]:
    """전략 문서(_docs/_strategy 4범주 직속)의 추가 필수 속성 검사 (경고).

    _strategy/AGENTS.md가 일반 필수 필드 외에 importance/urgency를 요구하나
    audit이 이를 안 봐서 스키마가 강제되지 않던 것을 보완한다 (제노 1.4).
    하위 폴더 문서와 디스크립터에는 강제하지 않는다. 경고 수준으로 두는 것은
    자식/메타 레포의 채택 여부가 정책 결정이기 때문 - 상향(위반) 여부는 사용자
    결정.
    """
    out: list[Finding] = []
    d = root / STRATEGY_DIR
    if not d.is_dir():
        return out
    for p in sorted(d.iterdir()):
        if not (p.is_file() and p.suffix == ".md"):
            continue
        if p.name == DESCRIPTOR_NAME or p.name in EXEMPT_FILENAMES:
            continue
        m = FRONT_MATTER_RE.match(read(p))
        if not m:
            continue  # front matter 부재는 check_front_matter가 잡는다
        body = m.group(1)
        for field in STRATEGY_FIELDS:
            if not re.search(rf"^{re.escape(field)}\s*:", body, re.MULTILINE):
                out.append(Finding(
                    WARNING, "strategy", str(p.relative_to(root)),
                    f"전략 문서 추가 필수 속성 누락 - {field} (cf. _strategy/AGENTS.md)",
                ))
    return out


def check_tags_category(root: Path) -> list[Finding]:
    """_docs/ 4범주 직속 문서의 tags 첫 항목이 카테고리와 일치하는지 (경고).

    하위 폴더 문서에는 강제하지 않는다 (cf. AGENTS.md "문서 작성 스타일").
    """
    out: list[Finding] = []
    for rel_dir, expected in CATEGORY_TAG_DIRS.items():
        d = root / rel_dir
        if not d.is_dir():
            continue
        for p in sorted(d.iterdir()):
            if not (p.is_file() and p.suffix == ".md"):
                continue
            if p.name in EXEMPT_FILENAMES:
                continue
            m = FRONT_MATTER_RE.match(read(p))
            if not m:
                continue  # front matter 부재는 check_front_matter가 잡는다
            t = re.search(r"^tags\s*:\s*\[([^\]]*)\]", m.group(1), re.MULTILINE)
            if not t:
                continue
            first = t.group(1).split(",")[0].strip()
            if first != expected:
                out.append(Finding(
                    WARNING, "tags", str(p.relative_to(root)),
                    f'tags 첫 항목 "{first}" - 4범주 직속 문서는 "{expected}" 기대',
                ))
    return out

"""front matter와 스키마 필드 검사.

공용 인프라는 _audit_core, 오케스트레이션은 audit.py.
"""
import re
import urllib.parse
from pathlib import Path

from _audit_core import *  # noqa: F401,F403 - Finding, 상수, 공용 헬퍼
from _tags_core import scan_tags, tag_form_problem, tag_key


def check_front_matter(root: Path) -> list[Finding]:
    out: list[Finding] = []
    for path in iter_md_files(root):
        if path.name in EXEMPT_FILENAMES:
            continue
        if INDEX_PAGE_RE.match(path.name):
            continue  # 생성 색인 쪽 파일은 front matter를 두지 않는다
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
        # 날짜 필드 값 형식 검증 - 필드 존재만 보면 잘못된 값이 통과하므로 값도
        # 검사한다. 필드가 있을 때만 값을 검사한다.
        dates = {}
        for field in ("date created", "date modified", "date closed"):
            vm = re.search(rf"^{re.escape(field)}\s*:\s*(\S.*?)\s*$", body, re.MULTILINE)
            if vm and not DATE_VALUE_RE.match(vm.group(1)):
                out.append(Finding(
                    VIOLATION, "front-matter", rel,
                    f'{field} 값 형식 오류 - yyyy-MM-dd 기대, 실제 "{vm.group(1)}"',
                ))
            elif vm:
                dates[field] = vm.group(1)
        # 생성일이 수정일보다 늦으면 둘 중 하나가 오기다. yyyy-MM-dd는 문자열
        # 비교가 날짜 순서와 같다.
        if dates.get("date created", "") > dates.get("date modified", "9999-99-99"):
            out.append(Finding(
                WARNING, "front-matter", rel,
                f'date created({dates["date created"]})가 date modified({dates["date modified"]})보다 늦음 - 오기 확인',
            ))
        # date closed는 선택 필드이며 히스토리 문서(날짜 프리픽스) 전용이다.
        # 프리픽스 없는 현재적 문서에 달리면 시간성 혼합 신호.
        if re.search(r"^date closed\s*:", body, re.MULTILINE) and not has_date_prefix(path):
            out.append(Finding(
                VIOLATION, "temporality", rel,
                "날짜 프리픽스 없는 문서에 date closed - 현재적 문서에는 종결 개념이 없다 (시간성 혼합)",
            ))
    return out


def check_strategy_fields(root: Path) -> list[Finding]:
    """전략 문서(epistemic-structure/strategy 4범주 직속)의 추가 필수 속성 검사 (경고).

    strategy/AGENTS/epistemic-rules.md가 일반 필수 필드 외에 요구하는 importance/urgency를
    검사한다.
    하위 폴더 문서와 디스크립터, 부모 문서(같은 이름 폴더 X/가 있는 X.md)에는
    강제하지 않는다. 부모 문서는 그 폴더를 소개하는 문서이지 결정 문서가
    아니다 (ref: folder-structure.md "폴더 구조와 디스크립터"). 경고 수준으로 두는 것은
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
        if (d / p.stem).is_dir():
            continue  # 부모 문서
        m = FRONT_MATTER_RE.match(read(p))
        if not m:
            continue  # front matter 부재는 check_front_matter가 잡는다
        body = m.group(1)
        for field in STRATEGY_FIELDS:
            if not re.search(rf"^{re.escape(field)}\s*:", body, re.MULTILINE):
                out.append(Finding(
                    WARNING, "strategy", str(p.relative_to(root)),
                    f"전략 문서 추가 필수 속성 누락 - {field} (ref: strategy/AGENTS/epistemic-rules.md)",
                ))
    return out


def check_tags(root: Path) -> list[Finding]:
    """front matter tags의 형식과 표기 검사 (항목 14, 모두 경고).

    - 읽을 수 없는 tags: 문서마다 1건.
    - 형태 규칙 위반(공백 든 태그, 빈 태그, 숫자만의 태그): 서로 다른 태그마다 1건.
    - 표기 차이: tag_key가 같고 표기가 둘 이상인 묶음마다 1건.
    경고 경로는 고칠 수 있는 파일을 가리킨다. 상류 묶음 문서는 자손이 고치지
    못하므로 묶음 밖 문서를 먼저 고른다.
    """
    docs, errors = scan_tags(root)

    def rel(p: Path) -> str:
        return str(p.relative_to(root))

    ordered = sorted(docs, key=rel)
    out: list[Finding] = []
    for path, err in sorted(errors, key=lambda e: rel(e[0])):
        where = f" ({err.line}행)" if err.line else ""
        out.append(Finding(
            WARNING, "tags", rel(path),
            f"tags를 읽을 수 없음{where} - {err}",
        ))

    spellings: "dict[str, list[Path]]" = {}
    for path in ordered:
        for tag in dict.fromkeys(docs[path]):  # 문서 안 중복은 한 번만 센다
            spellings.setdefault(tag, []).append(path)

    def pick(paths: "list[Path]") -> Path:
        return next((p for p in paths if not is_bundle_path(root, p)), paths[0])

    for tag in sorted(spellings):
        problem = tag_form_problem(tag)
        if problem:
            paths = spellings[tag]
            out.append(Finding(
                WARNING, "tags", rel(pick(paths)),
                f'태그 "{tag}" - {problem}. 옵시디언이 태그로 인정하지 않음 '
                f"(문서 {len(paths)}건)",
            ))

    groups: "dict[str, list[str]]" = {}
    for tag in spellings:
        groups.setdefault(tag_key(tag), []).append(tag)
    for key in sorted(groups):
        forms = groups[key]
        if len(forms) < 2:
            continue
        upstream = {
            t for t in forms
            if any(is_bundle_path(root, p) for p in spellings[t])
        }
        others = [t for t in forms if t not in upstream]
        if upstream and others:
            # 상류 표기는 고정이다. 그 밖의 표기를 쓰는 문서 가운데 첫 문서.
            target = min(
                (p for t in others for p in spellings[t]), key=rel)
        else:
            # 상류 표기가 없으면 가장 적게 쓰인 표기의 첫 문서.
            least = min(forms, key=lambda t: (len(spellings[t]), rel(spellings[t][0])))
            target = spellings[least][0]
        ranked = sorted(forms, key=lambda t: (-len(spellings[t]), t))
        listing = ", ".join(
            f"{t} {len(spellings[t])}" + (" (상류)" if t in upstream else "")
            for t in ranked
        )
        out.append(Finding(
            WARNING, "tags", rel(target),
            f"표기만 다른 태그 묶음(표기별 문서 수) - {listing}. "
            "옵시디언은 대소문자 차이를 한 태그로 본다",
        ))
    return out

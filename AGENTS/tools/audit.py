#!/usr/bin/env python3
"""에피스테믹 워크스페이스 기계 감사 (Layer 0, 도구 중립).

epistemic-auditor의 형식 점검 항목을 결정론적으로 검사한다.
의미 판단(카테고리 배치 적절성, 워크로그 최신성)은 다루지 않는다 -
그건 LLM 감사자의 몫으로 남는다. git 맥락이 필요한 검출도 다루지 않는다
(마크 커밋 없는 삭제 등) - 그건 epistemic-auditor의 점검 항목이다.

점검 항목:
  1. YAML front matter 필수 필드 (date created, date modified, tags).
     선택 필드 date closed는 히스토리 문서(날짜 프리픽스) 전용.
  2. 문서 유형별 분량 임계 (지식/전략 노드, 시간 축 문서, 폴더 디스크립터) - 경고
  3. 현재적 문서의 시간성 혼합 패턴 (날짜 헤더/불릿 반복) - 경고
  4. 날짜 프리픽스 없는 문서의 date closed (시간성 혼합 신호) - 위반
  5. STATUS.md 레지스트리 표 외 서술 누적 - 위반
  6. TASK_TREE.md 속성 노드 표준 키 위반 - 위반
  7. 디스크립터(AGENTS.md) 없는 폴더 - 위반
  8. 폴더 직속 md 파일 수 임계 초과 - 경고 (분화 권고)
  9. 문서 간 상대 마크다운 링크 정합 (대소문자, 유니코드 정규화 포함)
 10. 파일명의 크로스 플랫폼 이식성 (윈도우 금지 문자, 예약어 등)
 11. 규범 폴더 디스크립터의 파일별 안내 완전성 - 경고
     (골격 기본 규범 폴더 AGENTS/, _docs/_architecture/ 및 그 하위 전체 +
      파일별 안내 표를 가진 디스크립터의 폴더)
 12. TASK_TREE.md 완료 노드의 브랜치 속성 잔존 - 경고
 13. STATUS.md 레지스트리 표 스키마, 시각 형식 - 경고
 14. _docs/ 4범주 직속 문서의 tags 첫 항목 정합 - 경고
 15. 실체 0건 폴더 (디스크립터 외 항목 없음, 골격 폴더 제외) - 경고
     (찌꺼기인지 사양 동결인지 첫 실체 대기인지는 감사자가 판단)
 16. 하위 문서 없는 동명 문서-폴더 쌍 - 경고
     (동명 쌍은 하위 문서 묶음 관계의 예약 신호. md가 든 동명 쌍의
      실제 관계 판단은 감사자 몫)

위치: AGENTS/tools/audit.py. 사용 안내 문서는 AGENTS/tool-environment.md "기계 감사 스크립트".

사용법:
    python3 AGENTS/tools/audit.py [워크스페이스 루트]   # 생략 시 현재 디렉토리
    (윈도우에서는 python 또는 py 런처로 동일하게 실행)

종료 코드: 위반(violation) 있으면 1, 경고(warning)만 있거나 없으면 0.

이식성 노트:
- Python 3.8+ 표준 라이브러리만 사용. 특정 AI 도구, OS에 의존하지 않는다.
- 경로는 전부 pathlib로 다루고, 출력은 UTF-8로 강제한다 (윈도우 콘솔의
  cp949 기본값 대비).
- 링크 검사는 OS의 파일시스템 특성(대소문자 무시, 유니코드 정규화 무시)에
  기대지 않고 디렉토리 엔트리를 직접 대조한다. 어느 OS에서 실행해도 같은
  결과가 나오는 것이 목표다.
- git에 의존하지 않는다. 파일시스템 정적 상태만 본다.
"""

import re
import sys
import unicodedata
import urllib.parse
from pathlib import Path

REFERENCE_DIR = "_reference"
IMPLEMENTATION_DIR = "_implementation"
WORKLOG_DIR = "_docs/_worklog"
# 도구 전용 파일은 front matter 면제 (cf. agent-roles.md 점검 항목 3,
# writing-style.md "도구 전용 설정 파일 예외"). SKILL.md는 자체 규격(name, description).
EXEMPT_FILENAMES = {"CLAUDE.md", "GEMINI.md", "copilot-instructions.md", "SKILL.md"}
EXEMPT_DIRS = {".git", ".claude", ".gemini", ".github", ".kiro", "node_modules"}

# 폴더 디스크립터 파일명. 모든 폴더가 이 파일을 가진다 (folder-structure.md
# "폴더 구조와 디스크립터"). 도구 계층 자동 인식용 명명.
DESCRIPTOR_NAME = "AGENTS.md"

# 골격 기본 규범 폴더 (folder-structure.md "폴더 구조와 디스크립터"). 하위 폴더도
# 규범 폴더로 취급한다. 그 외 폴더는 디스크립터의 파일별 안내 표 존재로 판별.
NORMATIVE_DIRS = ("AGENTS", "_docs/_architecture")

# 에피스테믹 골격이 출고하는 표준 폴더. 실체 0건 검출에서 상시 예외.
SKELETON_DIRS = {
    ".", "AGENTS", "AGENTS/tools", "_docs", "_docs/_ontology",
    "_docs/_knowledge", "_docs/_strategy", "_docs/_architecture",
    "_docs/_worklog", REFERENCE_DIR, IMPLEMENTATION_DIR,
}

# _docs/ 4범주 직속 문서의 tags 첫 항목 기대값 (하위 폴더에는 강제하지 않는다).
CATEGORY_TAG_DIRS = {
    "_docs/_ontology": "ontology",
    "_docs/_knowledge": "knowledge",
    "_docs/_strategy": "strategy",
    "_docs/_architecture": "architecture",
}

# --- 임계값 (초기값. 보수적으로 시작해 운영하며 조정) ---
# 공백 제외 문자 수. "한글 기준" 근사.
SIZE_LIMIT_NODE = 3000        # 지식/전략 노드 등 일반 현재적 문서
SIZE_LIMIT_TEMPORAL = 10000   # 시간 축 문서(날짜 프리픽스)는 누적이 본질
FOLDER_MD_LIMIT = 20          # 폴더 직속 md 파일 수 - 초과 시 분화 권고
TEMPORAL_MIX_REPEAT = 5       # 현재적 문서 내 날짜 패턴 반복 임계

FRONT_MATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
# URL 스킴은 2글자 이상으로 판별 - 윈도우 드라이브 문자(C: 등) 오인 방지
SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]+:")
WINDOWS_FORBIDDEN_RE = re.compile(r'[<>:"|?*\x00-\x1f]')
WINDOWS_RESERVED = {"CON", "PRN", "AUX", "NUL"} | {f"COM{i}" for i in range(1, 10)} | {
    f"LPT{i}" for i in range(1, 10)
}
# 날짜 프리픽스: 파일명이 yyyy-MM-dd로 시작하면 히스토리 문서.
# 시각 확장(yyyy-MM-ddTHH-mm)도 인정한다 (cf. document-temporality.md).
DATE_PREFIX_RE = re.compile(r"^\d{4}-\d{2}-\d{2}([-.T]|$)")
# 본문 내 날짜 헤더/불릿 반복 검출 (시간성 혼합 신호).
DATE_LINE_RE = re.compile(r"^\s*(?:[-*#>]+\s*)*\d{4}-\d{2}-\d{2}\b", re.MULTILINE)
# TASK_TREE 속성 노드 표준 키. 이 키로 시작하는 불릿만 표준으로 인정.
TASK_TREE_ATTR_KEYS = ("설명", "상태 상세", "외부 참조", "브랜치")
# STATUS 레지스트리 표의 시각 표기와 표준 헤더. 미수행 placeholder는 허용.
STATUS_TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")
STATUS_HEADER_CELLS = ["이름", "마지막 수행", "주기/트리거"]
STATUS_PLACEHOLDER = {"(아직 없음)", "-"}

violations: list[str] = []
warnings: list[str] = []


def nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text)


def iter_md_files(root: Path):
    """규약 검사 대상 .md 순회.

    _reference/ 내부는 immutable raw 자료라 규약 검사 대상이 아니다
    (디스크립터 AGENTS.md 자체만 예외).
    _implementation/ 하위 프로젝트 내부(소스 트리)도 대상이 아니다 -
    소스 폴더 구조는 코드 생태계 관례가 지배한다 (cf. folder-structure.md
    "폴더 구조와 디스크립터" _implementation 예외). 직할 AGENTS.md와
    그 하위 문서 폴더 AGENTS/만 검사한다.
    """
    ref_descriptor = (root / REFERENCE_DIR / DESCRIPTOR_NAME).resolve()
    for path in sorted(root.rglob("*.md")):
        parts = path.relative_to(root).parts
        if any(part in EXEMPT_DIRS for part in parts):
            continue
        if parts and parts[0] == REFERENCE_DIR and path.resolve() != ref_descriptor:
            continue
        if (
            len(parts) >= 2
            and parts[0] == IMPLEMENTATION_DIR
            and not (len(parts) == 2 and parts[1] == DESCRIPTOR_NAME)
            and parts[1] != "AGENTS"
        ):
            continue
        yield path


def read(path: Path) -> str:
    # 인코딩을 UTF-8로 고정 - 윈도우의 로케일 기본 인코딩(cp949)에 의존하지 않는다.
    return path.read_text(encoding="utf-8", errors="replace")


def has_date_prefix(path: Path) -> bool:
    return bool(DATE_PREFIX_RE.match(path.name))


def body_of(path: Path) -> str:
    return FRONT_MATTER_RE.sub("", read(path))


def check_front_matter(root: Path):
    for path in iter_md_files(root):
        if path.name in EXEMPT_FILENAMES:
            continue
        text = read(path)
        match = FRONT_MATTER_RE.match(text)
        rel = path.relative_to(root)
        if not match:
            violations.append(f"[front-matter] {rel}: YAML front matter 없음")
            continue
        body = match.group(1)
        for field in ("date created", "date modified", "tags"):
            if not re.search(rf"^{re.escape(field)}\s*:", body, re.MULTILINE):
                violations.append(f"[front-matter] {rel}: 필수 필드 누락 - {field}")
        # date closed는 선택 필드이며 히스토리 문서(날짜 프리픽스) 전용이다.
        # 프리픽스 없는 현재적 문서에 달리면 시간성 혼합 신호 (proposal 3).
        if re.search(r"^date closed\s*:", body, re.MULTILINE) and not has_date_prefix(path):
            violations.append(
                f"[temporality] {rel}: 날짜 프리픽스 없는 문서에 date closed - "
                "현재적 문서에는 종결 개념이 없다 (시간성 혼합)"
            )


def links_in(path: Path) -> list[str]:
    text = FRONT_MATTER_RE.sub("", read(path))
    # 예시 링크 오탐 방지: 펜스 코드 블록, 인라인 코드, HTML 주석은 제외
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    text = re.sub(r"`[^`\n]*`", "", text)
    return LINK_RE.findall(text)


def resolve_link(source: Path, target: str) -> Path | None:
    """상대 링크를 파일시스템 경로로 해석. 외부/앵커 링크는 None."""
    if SCHEME_RE.match(target):  # https:, mailto: 등 (2글자 이상 스킴)
        return None
    target = target.split("#", 1)[0]
    if not target:
        return None
    return (source.parent / urllib.parse.unquote(target)).resolve()


def classify_target(root: Path, target: Path) -> str:
    """링크 대상의 실재를 OS 특성에 기대지 않고 판정한다.

    반환: "exact"(표기까지 일치) / "nfc"(유니코드 정규화만 다름) /
          "case"(대소문자만 다름) / "missing"(없음) / "outside"(루트 밖).

    exists()는 대소문자 무시 파일시스템(윈도우, 기본 macOS)에서 잘못된
    표기도 True가 되고, 리눅스에서는 NFC/NFD 차이로 False가 되어 OS마다
    결과가 갈린다. 디렉토리 엔트리를 직접 대조해 판정을 통일한다.
    """
    try:
        rel = target.relative_to(root.resolve())
    except ValueError:
        return "outside"
    current = root
    verdict = "exact"
    for part in rel.parts:
        try:
            entries = {entry.name: entry for entry in current.iterdir()}
        except OSError:
            return "missing"
        if part in entries:
            current = entries[part]
            continue
        nfc_match = next((n for n in entries if nfc(n) == nfc(part)), None)
        if nfc_match is not None:
            current = entries[nfc_match]
            verdict = "nfc" if verdict == "exact" else verdict
            continue
        case_match = next(
            (n for n in entries if nfc(n).casefold() == nfc(part).casefold()), None
        )
        if case_match is not None:
            current = entries[case_match]
            verdict = "case"
            continue
        return "missing"
    return verdict


def check_links(root: Path):
    for path in iter_md_files(root):
        rel = path.relative_to(root)
        for raw in links_in(path):
            resolved = resolve_link(path, raw)
            if resolved is None:
                continue
            verdict = classify_target(root, resolved)
            if verdict == "outside":
                if not resolved.exists():
                    violations.append(f"[link] {rel}: 깨진 링크(루트 밖) -> {raw}")
            elif verdict == "missing":
                violations.append(f"[link] {rel}: 깨진 링크 -> {raw}")
            elif verdict == "case":
                violations.append(
                    f"[link] {rel}: 대소문자 불일치 링크 (리눅스에서 깨짐) -> {raw}"
                )
            elif verdict == "nfc":
                warnings.append(
                    f"[link] {rel}: 유니코드 정규화 불일치 링크 (OS 간 상이 위험) -> {raw}"
                )


def content_dirs(root: Path):
    """디스크립터 검사 대상 폴더 순회.

    EXEMPT_DIRS(.git, .claude 등 도구 전용)와 그 하위는 제외한다.
    _implementation/ 하위 프로젝트 내부(소스 트리)는 제외한다 - 직할
    문서 폴더 AGENTS/만 대상 (cf. folder-structure.md "폴더 구조와 디스크립터"
    _implementation 예외).
    루트 자신도 디스크립터(루트 AGENTS.md)를 가진다.
    """
    yield root
    for path in sorted(root.rglob("*")):
        if not path.is_dir():
            continue
        parts = path.relative_to(root).parts
        if any(part in EXEMPT_DIRS for part in parts):
            continue
        if len(parts) >= 2 and parts[0] == IMPLEMENTATION_DIR and parts[1] != "AGENTS":
            continue
        yield path


def check_descriptors(root: Path):
    """모든 폴더가 디스크립터(AGENTS.md)를 갖는지, 폴더 직속 md 수 임계를 검사."""
    for d in content_dirs(root):
        rel = d.relative_to(root) if d != root else Path(".")
        # _reference/ 하위 폴더는 immutable raw 보관이라 디스크립터를 강제하지 않는다.
        parts = rel.parts
        in_reference_sub = parts and parts[0] == REFERENCE_DIR and len(parts) > 0 and rel != Path(REFERENCE_DIR)
        descriptor = d / DESCRIPTOR_NAME
        if not descriptor.exists() and not in_reference_sub:
            violations.append(f"[descriptor] {rel}: 폴더 디스크립터(AGENTS.md) 없음")
        # 폴더 직속(하위 폴더 제외) md 파일 수.
        direct_md = [
            p for p in d.iterdir()
            if p.is_file() and p.suffix == ".md" and p.name not in EXEMPT_FILENAMES
        ]
        if len(direct_md) > FOLDER_MD_LIMIT:
            warnings.append(
                f"[folder-size] {rel}: 폴더 직속 md {len(direct_md)}개 (> {FOLDER_MD_LIMIT}). "
                "하위 폴더 분화 권고"
            )


def check_size(root: Path):
    """문서 유형별 분량 임계. 시간 축 문서는 완화된 임계를 쓴다."""
    for path in iter_md_files(root):
        body = body_of(path)
        length = len(re.sub(r"\s", "", body))
        if has_date_prefix(path):
            limit = SIZE_LIMIT_TEMPORAL
        else:
            limit = SIZE_LIMIT_NODE
        if length > limit:
            warnings.append(
                f"[size] {path.relative_to(root)}: 공백 제외 {length}자 (> {limit}). "
                "여러 관심사가 섞였는지 사람/LLM 판단 필요"
            )


def check_temporality_mix(root: Path):
    """현재적 문서(날짜 프리픽스 없음) 본문의 날짜 헤더/불릿 반복을 검출.

    시간순 로그가 현재적 문서에 누적되는 하이브리드화 신호 (proposal 3).
    워크로그(TASK_TREE, STATUS)는 별도 룰이 있어 제외.
    """
    worklog = (root / WORKLOG_DIR).resolve()
    for path in iter_md_files(root):
        if has_date_prefix(path):
            continue
        if worklog in path.resolve().parents:
            continue
        body = body_of(path)
        # 코드 블록 안 예시 날짜 제외
        body = re.sub(r"```.*?```", "", body, flags=re.DOTALL)
        hits = len(DATE_LINE_RE.findall(body))
        if hits > TEMPORAL_MIX_REPEAT:
            warnings.append(
                f"[temporality] {path.relative_to(root)}: 날짜 헤더/불릿 {hits}회 반복 "
                f"(> {TEMPORAL_MIX_REPEAT}). 시간성 혼합 검토 - 히스토리 문서로 분리 대상인지"
            )


def check_status_registry(root: Path):
    """STATUS.md가 레지스트리 표 외 서술을 누적하는지 검출 (proposal 2).

    STATUS는 상태 레지스트리다. front matter, 제목, 인용 블록(> 안내),
    마크다운 표만 허용하고 일반 서술 문단이 있으면 위반.
    """
    status = root / WORKLOG_DIR / "STATUS.md"
    if not status.exists():
        return
    body = body_of(status)
    for raw_line in body.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("#"):       # 제목
            continue
        if line.startswith(">"):       # 인용 블록(갱신 규칙 안내)
            continue
        if line.startswith("|"):       # 표
            continue
        violations.append(
            f"[status] {status.relative_to(root)}: 레지스트리 표 외 서술 발견 - "
            f'"{line[:40]}". STATUS는 상태 레지스트리이며 진행 서사를 두지 않는다'
        )
        break


def check_task_tree_attrs(root: Path):
    """TASK_TREE.md 속성 노드(체크박스 없는 불릿)의 표준 키 위반 검출 (proposal 2).

    작업 노드는 `- [ ]`/`[/]`/`[x]`/`[-]` 형태. 속성 노드는 체크박스 없는
    불릿이며 표준 키(설명, 상태 상세, 외부 참조, 브랜치)로 시작해야 한다.
    프리앰블(인용 블록, 코드 블록)은 검사에서 제외.
    """
    tree = root / WORKLOG_DIR / "TASK_TREE.md"
    if not tree.exists():
        return
    body = body_of(tree)
    body = re.sub(r"```.*?```", "", body, flags=re.DOTALL)
    checkbox_re = re.compile(r"^\s*-\s*\[[ /x\-]\]\s")
    bullet_re = re.compile(r"^(\s*)-\s+(?!\[[ /x\-]\])(.*)$")
    for raw_line in body.splitlines():
        if raw_line.lstrip().startswith(">"):   # 프리앰블 인용 블록
            continue
        if checkbox_re.match(raw_line):         # 작업 노드
            continue
        m = bullet_re.match(raw_line)
        if not m:
            continue
        content = m.group(2).strip()
        if content.startswith("cf.") or content.startswith("ref."):
            continue
        # 표준 키로 시작하는지 (키 뒤에 콜론/공백/한글 등 자유 서술 허용).
        if any(content.startswith(k) for k in TASK_TREE_ATTR_KEYS):
            continue
        warnings.append(
            f"[task-tree] {tree.relative_to(root)}: 속성 노드 비표준 키 - "
            f'"{content[:40]}". 표준 키: {", ".join(TASK_TREE_ATTR_KEYS)}'
        )


def is_normative_dir(root: Path, d: Path) -> bool:
    """골격 기본 규범 폴더(하위 포함) 또는 파일별 안내 표를 가진 폴더인지 판별.

    파일별 안내 표 판별: 디스크립터의 마크다운 표 행에 폴더 직속 md 파일로의
    링크가 하나라도 있으면 그 폴더는 파일별 안내를 운영하는 것으로 본다.
    """
    rel = d.relative_to(root).as_posix() if d != root else "."
    for base in NORMATIVE_DIRS:
        if rel == base or rel.startswith(base + "/"):
            return True
    descriptor = d / DESCRIPTOR_NAME
    if not descriptor.exists():
        return False
    direct_md_names = {
        p.name for p in d.iterdir()
        if p.is_file() and p.suffix == ".md"
        and p.name != DESCRIPTOR_NAME and p.name not in EXEMPT_FILENAMES
    }
    if not direct_md_names:
        return False
    for line in body_of(descriptor).splitlines():
        if not line.lstrip().startswith("|"):
            continue
        for name in direct_md_names:
            if name in line or urllib.parse.quote(name) in line:
                return True
    return False


def check_normative_guides(root: Path):
    """규범 폴더 디스크립터의 파일별 안내 완전성 검사 (경고).

    규범 폴더의 직속 md 파일이 디스크립터 본문에 언급되지 않으면 경고.
    존재를 모르면 위반 행동이 나오는 문서들이므로 안내 누락 자체가 신호다.
    """
    for d in content_dirs(root):
        if not is_normative_dir(root, d):
            continue
        descriptor = d / DESCRIPTOR_NAME
        if not descriptor.exists():
            continue  # 디스크립터 부재는 check_descriptors가 위반으로 잡는다
        text = body_of(descriptor)
        rel = d.relative_to(root) if d != root else Path(".")
        for p in sorted(d.iterdir()):
            if not (p.is_file() and p.suffix == ".md"):
                continue
            if p.name == DESCRIPTOR_NAME or p.name in EXEMPT_FILENAMES:
                continue
            if p.name in text or urllib.parse.quote(p.name) in text:
                continue
            warnings.append(
                f"[normative] {rel}: 디스크립터 파일별 안내에 미등재 - {p.name}. "
                "규범 폴더는 파일별 설명과 읽기 트리거를 유지한다"
            )


def check_task_tree_completed_branch(root: Path):
    """완료(`[x]`/`[-]`) 노드에 브랜치 속성이 잔존하는지 검출 (경고).

    완료 시 브랜치 속성은 제거한다 (TASK_TREE 관리 규칙). 잔존하면 끊김
    재진입이 죽은 포인터를 따라갈 수 있다.
    """
    tree = root / WORKLOG_DIR / "TASK_TREE.md"
    if not tree.exists():
        return
    body = re.sub(r"```.*?```", "", body_of(tree), flags=re.DOTALL)
    checkbox_re = re.compile(r"^(\s*)-\s*\[([ /x\-])\]\s")
    bullet_re = re.compile(r"^(\s*)-\s+(?!\[[ /x\-]\])(.*)$")
    stack: list[tuple[int, str]] = []  # (들여쓰기 폭, 상태 문자)
    for raw_line in body.splitlines():
        if raw_line.lstrip().startswith(">"):
            continue
        m = checkbox_re.match(raw_line)
        if m:
            indent = len(m.group(1))
            while stack and stack[-1][0] >= indent:
                stack.pop()
            stack.append((indent, m.group(2)))
            continue
        b = bullet_re.match(raw_line)
        if not b:
            continue
        indent = len(b.group(1))
        content = b.group(2).strip()
        ancestor = next((s for i, s in reversed(stack) if i < indent), None)
        if ancestor in ("x", "-") and content.startswith("브랜치"):
            warnings.append(
                f"[task-tree] {tree.relative_to(root)}: 완료 노드에 브랜치 속성 잔존 - "
                f'"{content[:40]}". 완료 시 브랜치 속성은 제거한다'
            )


def check_status_schema(root: Path):
    """STATUS.md 레지스트리 표의 스키마와 시각 표기 형식 검사 (경고)."""
    status = root / WORKLOG_DIR / "STATUS.md"
    if not status.exists():
        return
    rel = status.relative_to(root)
    header_seen = False
    for raw_line in body_of(status).splitlines():
        line = raw_line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if all(re.fullmatch(r":?-+:?", c) for c in cells):  # 구분선
            continue
        if not header_seen:
            header_seen = True
            if cells != STATUS_HEADER_CELLS:
                warnings.append(
                    f"[status] {rel}: 레지스트리 표 헤더가 표준 스키마와 다름 - "
                    f"기대 {STATUS_HEADER_CELLS}, 실제 {cells}"
                )
            continue
        if len(cells) != len(STATUS_HEADER_CELLS):
            warnings.append(
                f"[status] {rel}: 레지스트리 행 열 수 불일치 - \"{line[:40]}\""
            )
            continue
        value = cells[1]
        if value in STATUS_PLACEHOLDER or STATUS_TIMESTAMP_RE.match(value):
            continue
        warnings.append(
            f"[status] {rel}: 마지막 수행 시각 형식 위반 - \"{value}\". "
            "yyyy-MM-dd HH:mm:ss KST 표기"
        )


def check_tags_category(root: Path):
    """_docs/ 4범주 직속 문서의 tags 첫 항목이 카테고리와 일치하는지 (경고).

    하위 폴더 문서에는 강제하지 않는다 (cf. AGENTS.md "문서 작성 스타일").
    """
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
                warnings.append(
                    f"[tags] {p.relative_to(root)}: tags 첫 항목 \"{first}\" - "
                    f"4범주 직속 문서는 \"{expected}\" 기대"
                )


def check_empty_folders(root: Path):
    """디스크립터 외 실체가 0건인 폴더 검출 (경고, 골격 폴더 제외).

    삭제 대상 잔재인지, 사양만 있고 실체 0건인 동결인지, 첫 실체 대기 중인
    정상 신설인지는 감사자(LLM)가 판단한다.
    """
    for d in content_dirs(root):
        rel = d.relative_to(root).as_posix() if d != root else "."
        if rel in SKELETON_DIRS:
            continue
        try:
            entries = [e for e in d.iterdir() if e.name != DESCRIPTOR_NAME]
        except OSError:
            continue
        if not entries:
            warnings.append(
                f"[empty-folder] {rel}: 디스크립터 외 실체 0건. "
                "잔재 삭제/사양 동결/첫 실체 대기 여부 감사자 판단 필요"
            )


def check_name_collision(root: Path):
    """하위 문서 묶음이 아닌 동명 문서-폴더 쌍 검출 (경고).

    `X.md` + `X/`는 하위 문서 묶음 관계의 예약 신호다 (cf.
    workspace-and-project-structure.md "하위 문서 폴더 규칙"). 폴더에
    디스크립터 외 md가 없으면 그 관계가 성립할 수 없으므로 확정 검출한다.
    md가 든 동명 쌍의 실제 관계 판단은 감사자(LLM) 몫이다.
    """
    for d in content_dirs(root):
        parts = d.relative_to(root).parts if d != root else ()
        if parts and parts[0] == REFERENCE_DIR:
            continue  # immutable raw 영역의 이름은 규약 대상이 아니다
        for sub in sorted(d.iterdir()):
            if not sub.is_dir() or sub.name in EXEMPT_DIRS:
                continue
            doc = d / (sub.name + ".md")
            if not doc.exists():
                continue
            has_md = any(
                p.is_file() and p.suffix == ".md" and p.name != DESCRIPTOR_NAME
                for p in sub.iterdir()
            )
            if not has_md:
                rel = doc.relative_to(root)
                warnings.append(
                    f"[naming] {rel}: 동명 폴더 {sub.relative_to(root)}/에 하위 문서가 없음. "
                    "하위 문서 묶음 관계가 아니면 한쪽을 개명한다"
                )


def check_filename_portability(root: Path):
    """윈도우 등 다른 OS에서 clone조차 불가능한 이름을 잡는다."""
    for path in sorted(root.rglob("*")):
        parts = path.relative_to(root).parts
        if any(part in EXEMPT_DIRS for part in parts):
            continue
        name = path.name
        rel = path.relative_to(root)
        if WINDOWS_FORBIDDEN_RE.search(name):
            violations.append(
                f'[portability] {rel}: 윈도우 금지 문자 포함 (< > : " | ? * 또는 제어 문자)'
            )
        if name != name.rstrip(" .") :
            violations.append(
                f"[portability] {rel}: 이름 끝의 공백/마침표 (윈도우에서 비정상)"
            )
        stem = name.split(".", 1)[0].upper()
        if stem in WINDOWS_RESERVED:
            violations.append(f"[portability] {rel}: 윈도우 예약어 이름 ({stem})")


def main() -> int:
    # 윈도우 콘솔(cp949 등)에서도 한글 출력이 깨지지 않게 UTF-8로 강제
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()
    if not root.is_dir():
        print(f"오류: 디렉토리가 아님 - {root}", file=sys.stderr)
        return 2

    check_front_matter(root)
    check_links(root)
    check_descriptors(root)
    check_size(root)
    check_temporality_mix(root)
    check_status_registry(root)
    check_status_schema(root)
    check_task_tree_attrs(root)
    check_task_tree_completed_branch(root)
    check_normative_guides(root)
    check_tags_category(root)
    check_empty_folders(root)
    check_name_collision(root)
    check_filename_portability(root)

    for line in violations:
        print(f"VIOLATION {line}")
    for line in warnings:
        print(f"WARNING   {line}")
    print(f"\n감사 완료: 위반 {len(violations)}건, 경고 {len(warnings)}건 ({root})")
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())

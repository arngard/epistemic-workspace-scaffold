#!/usr/bin/env python3
"""에피스테믹 워크스페이스 기계 감사 (Layer 0, 도구 중립).

epistemic-auditor의 형식 점검 항목을 결정론적으로 검사한다.
의미 판단(카테고리 배치 적절성, 워크로그 최신성)은 다루지 않는다 -
그건 LLM 감사자의 몫으로 남는다. git 맥락이 필요한 검출도 다루지 않는다
(마크 커밋 없는 삭제 등) - 그건 epistemic-auditor의 점검 항목이다.

점검 항목:
  1. YAML front matter 필수 필드 (date created, date modified, tags)와 날짜
     필드 값 형식(yyyy-MM-dd). 선택 필드 date closed는 히스토리 문서 전용.
  2. 문서 유형별 분량 임계 (일반 노드, 히스토리 문서, 진입층/폴더 디스크립터) - 경고
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
 17. 마크다운 링크 표시텍스트-대상 정합 - 위반
     (파일명 형태 표시텍스트가 대상 basename 또는 대상 전체와 일치해야 함.
      자연어 문구, 타이틀은 제외. 폐지 파일명 잔재 오도를 검출)
 18. 전략 문서(_docs/_strategy 4범주 직속)의 추가 필수 속성 - 경고
     (importance, urgency. cf. _strategy/AGENTS.md. 하위 폴더/디스크립터 제외)
 19. 로컬 .md 링크 뒤 인용 섹션명의 대상 헤딩 실존 - 경고
     (dangling 섹션 참조 검출. 헤딩 번호 접두는 정규화. 대상 부재는 항목 9 소관)

위치: AGENTS/tools/audit.py. 사용 안내 문서는 AGENTS/tool-environment.md "기계 감사 스크립트".

사용법:
    python3 AGENTS/tools/audit.py [워크스페이스 루트]   # 생략 시 현재 디렉토리
    (윈도우에서는 python 또는 py 런처로 동일하게 실행)

종료 코드:
    0  위반 없음 (경고만 있거나 없음)
    1  위반 있음
    2  사용법 오류 (인자가 디렉토리가 아님)

이식성 노트:
- Python 3.8+ 표준 라이브러리만 사용. 특정 AI 도구, OS에 의존하지 않는다.
- 경로는 전부 pathlib로 다루고, 출력은 UTF-8로 강제한다 (윈도우 콘솔의
  cp949 기본값 대비).
- 링크 검사는 OS의 파일시스템 특성(대소문자 무시, 유니코드 정규화 무시)에
  기대지 않고 디렉토리 엔트리를 직접 대조한다. 어느 OS에서 실행해도 같은
  결과가 나오는 것이 목표다.
- git에 의존하지 않는다. 파일시스템 정적 상태만 본다.
- 순회는 심볼릭 링크를 따르지 않고(루트 밖 탈출/순환 방지) 중첩 git 레포와
  도구 전용 폴더를 가지치기한다.

구조:
- 각 검사 함수는 Finding 리스트를 반환한다. 전역 가변 상태를 두지 않아
  호출 순서에 부수효과가 없고 단위 테스트가 쉽다.
- run_audit(root)가 검사들을 모아 Finding 리스트를 만들고, main()은 인자
  해석, 인코딩 설정, 출력, 종료 코드만 담당한다.
"""

import os
import re
import sys
import unicodedata
import urllib.parse
from dataclasses import dataclass
from pathlib import Path

REFERENCE_DIR = "_reference"
IMPLEMENTATION_DIR = "_implementation"
WORKLOG_DIR = "_docs/_worklog"
# 도구 전용 파일은 front matter 면제 (cf. agent-roles.md 점검 항목 3,
# writing-style.md "도구 전용 설정 파일 예외"). SKILL.md는 자체 규격(name, description).
EXEMPT_FILENAMES = {"CLAUDE.md", "GEMINI.md", "copilot-instructions.md", "SKILL.md"}
EXEMPT_DIRS = {".git", ".claude", ".gemini", ".github", ".kiro", "node_modules", "_tmp"}

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
SIZE_LIMIT_TEMPORAL = 10000   # 히스토리 문서(날짜 프리픽스)는 누적이 본질
# 진입층(루트 AGENTS.md)과 폴더 디스크립터(AGENTS.md)는 구조적으로 길어진다 -
# 진입층은 정체성/게이트/트리거 색인을 한 파일에 담는 색인이고, 디스크립터는
# 파일별 안내 표가 폴더 직속 항목 수에 비례한다 (cf. document-units.md "분량 보조 지표").
SIZE_LIMIT_DESCRIPTOR = 5000  # 진입층/폴더 디스크립터(AGENTS.md) 완화 임계
FOLDER_MD_LIMIT = 25          # 폴더 직속 md 파일 수 - 초과 시 분화 권고
TEMPORAL_MIX_REPEAT = 5       # 현재적 문서 내 날짜 패턴 반복 임계
# 정규식 스캔 대상 파일 읽기 상한(문자 수). DOTALL 정규식이 초대형 입력에서
# 과도한 백트래킹/메모리를 쓰지 않도록 상한을 둔다. 규약 문서는 이 값을 한참
# 밑돌며(분량 임계 3000자), 초과분은 어차피 분량 위반이라 잘려도 무해하다.
MAX_READ_CHARS = 1_000_000

FRONT_MATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
# 표시텍스트와 대상을 함께 캡처 - 표시텍스트 정합 검사용.
LINK_TEXT_RE = re.compile(r"\[([^\]]*)\]\(([^)\s]+)\)")
# 로컬 .md 링크 바로 뒤에 인용된 섹션명 - 섹션 참조 검사용.
# 관례는 URL 앵커(#) 대신 링크 뒤 인용 섹션명이나, 앵커 표기도 관대히 받는다.
SECTION_REF_RE = re.compile(r'\]\(([^)\s]+\.md(?:#[^)\s]*)?)\)\s*"([^"\n]+)"')
# 헤딩 추출과 번호 접두(N. ) 정규화 - 참조는 접두를 생략하는 관례라 대조 전 제거.
HEADING_RE = re.compile(r"^#{1,6}\s+(.+?)\s*$", re.MULTILINE)
ENUM_PREFIX_RE = re.compile(r"^\d+\.\s+")
# URL 스킴은 2글자 이상으로 판별 - 윈도우 드라이브 문자(C: 등) 오인 방지
SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]+:")
WINDOWS_FORBIDDEN_RE = re.compile(r'[<>:"|?*\x00-\x1f]')
WINDOWS_RESERVED = {"CON", "PRN", "AUX", "NUL"} | {f"COM{i}" for i in range(1, 10)} | {
    f"LPT{i}" for i in range(1, 10)
}
# front matter 날짜 필드 값 형식 (yyyy-MM-dd). 값 무검증으로 스키마가 우회되던
# 것을 조인다 (제노 1.1/3.1).
DATE_VALUE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# 전략 문서(_docs/_strategy 4범주 직속)의 추가 필수 속성 (cf. _strategy/AGENTS.md
# "Front matter 속성"). 하위 폴더 문서와 디스크립터에는 강제하지 않는다.
STRATEGY_DIR = "_docs/_strategy"
STRATEGY_FIELDS = ("importance", "urgency")
# 날짜 프리픽스: 파일명이 yyyy-MM-dd로 시작하면 히스토리 문서.
# 시각 확장(yyyy-MM-ddTHH-mm)도 인정한다 (cf. document-temporality.md).
DATE_PREFIX_RE = re.compile(r"^\d{4}-\d{2}-\d{2}([-.T]|$)")
# 본문 내 날짜 헤더/불릿 반복 검출 (시간성 혼합 신호).
DATE_LINE_RE = re.compile(r"^\s*(?:[-*#>]+\s*)*\d{4}-\d{2}-\d{2}\b", re.MULTILINE)
# TASK_TREE 속성 노드 표준 키. 이 키로 시작하는 불릿만 표준으로 인정.
TASK_TREE_ATTR_KEYS = ("설명", "상태 상세", "외부 참조", "브랜치")
# STATUS 레지스트리 표의 시각 표기와 표준 헤더. 미수행 placeholder는 허용.
# 시각은 KST 기준이며 존 표기는 생략하는 것이 관례다. 관례를 어기고 " KST"를
# 덧붙인 자식 기재도 깨지지 않게 접미를 선택적으로 허용한다 (델타 D-1 - 규약과
# 정규식의 자체 모순 해소).
STATUS_TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}( KST)?$")
STATUS_HEADER_CELLS = ["이름", "마지막 수행", "주기/트리거"]
STATUS_PLACEHOLDER = {"(아직 없음)", "-"}

VIOLATION = "violation"
WARNING = "warning"


@dataclass(frozen=True)
class Finding:
    """감사 발견 1건. 서식 문자열 대신 구조화된 데이터로 다룬다.

    severity는 VIOLATION 또는 WARNING. category는 검사 종류 태그
    (front-matter, link, size 등). path는 워크스페이스 루트 상대 경로 표기.
    출력 서식은 format()이 한 곳에서 결정한다.
    """

    severity: str
    category: str
    path: str
    message: str

    def format(self) -> str:
        body = f"[{self.category}] {self.path}: {self.message}"
        prefix = "VIOLATION" if self.severity == VIOLATION else "WARNING  "
        return f"{prefix} {body}"


def nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text)


_nested_repo_cache: dict[Path, tuple[Path, ...]] = {}


def nested_repo_dirs(root: Path) -> tuple[Path, ...]:
    """루트 아래 중첩 git 레포(서브모듈, 내장 클론)의 최상위 폴더들.

    자체 .git(폴더 또는 파일)을 가진 폴더는 독립 워크스페이스이며 자기
    규약으로 별도 감사한다. 스캐폴드를 서브모듈로 품는 배치에서 감사가
    서브모듈 내부까지 이중 스캔하는 것을 막는다.

    os.walk로 순회하며 EXEMPT_DIRS를 가지치기하고 중첩 레포를 발견하면 그
    내부로 더 내려가지 않는다 - 대형 자식 트리 전체를 rglob으로 훑던 비용을
    없앤다. followlinks=False로 심볼릭 링크를 따르지 않는다(루트 밖 탈출/순환
    방지).
    """
    if root not in _nested_repo_cache:
        found: list[Path] = []
        for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
            d = Path(dirpath)
            has_git = ".git" in dirnames or ".git" in filenames
            dirnames[:] = sorted(n for n in dirnames if n not in EXEMPT_DIRS)
            if d != root and has_git:
                found.append(d)
                dirnames[:] = []  # 중첩 레포 내부는 더 순회하지 않는다
        _nested_repo_cache[root] = tuple(sorted(found))
    return _nested_repo_cache[root]


def in_nested_repo(root: Path, path: Path) -> bool:
    return any(
        path == repo or repo in path.parents for repo in nested_repo_dirs(root)
    )


def is_excluded(root: Path, path: Path) -> bool:
    """순회 공통 제외 판정 (iter_md_files, content_dirs, 이식성 검사 공유).

    도구 전용 폴더(EXEMPT_DIRS) 하위, 중첩 git 레포 하위, 심볼릭 링크는
    제외한다. 카테고리별 추가 규칙(_reference, _implementation)은 각 호출부가
    자기 책임으로 덧붙인다.
    """
    parts = path.relative_to(root).parts
    if any(part in EXEMPT_DIRS for part in parts):
        return True
    if in_nested_repo(root, path):
        return True
    if path.is_symlink():  # 심링크는 순회 대상에서 뺀다 (루트 밖 탈출/순환 방지)
        return True
    return False


def iter_md_files(root: Path):
    """규약 검사 대상 .md 순회.

    _reference/ 내부는 immutable raw 자료라 규약 검사 대상이 아니다
    (디스크립터 AGENTS.md 자체만 예외).
    _implementation/ 하위 프로젝트 내부(소스 트리)도 대상이 아니다 -
    소스 폴더 구조는 코드 생태계 관례가 지배한다 (cf. folder-structure.md
    "폴더 구조와 디스크립터" _implementation 예외). 직할 AGENTS.md와
    그 하위 문서 폴더 AGENTS/만 검사한다.
    도구 전용 폴더, 중첩 git 레포, 심링크 제외는 is_excluded가 담당한다.
    """
    ref_descriptor = (root / REFERENCE_DIR / DESCRIPTOR_NAME).resolve()
    for path in sorted(root.rglob("*.md")):
        if is_excluded(root, path):
            continue
        parts = path.relative_to(root).parts
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
    # 정규식 스캔의 백트래킹/메모리 노출을 막기 위해 상한까지만 읽는다.
    with path.open("r", encoding="utf-8", errors="replace") as f:
        return f.read(MAX_READ_CHARS)


def has_date_prefix(path: Path) -> bool:
    return bool(DATE_PREFIX_RE.match(path.name))


def body_of(path: Path) -> str:
    return FRONT_MATTER_RE.sub("", read(path))


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


def links_in(path: Path) -> list[str]:
    text = FRONT_MATTER_RE.sub("", read(path))
    # 예시 링크 오탐 방지: 펜스 코드 블록, 인라인 코드, HTML 주석은 제외
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    text = re.sub(r"`[^`\n]*`", "", text)
    return LINK_RE.findall(text)


def resolve_link(source: Path, target: str) -> "Path | None":
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
            # 목록 불가(부재 또는 접근 불가)는 정적 감사 관점에서 해당 경로
            # 성분이 없는 것으로 본다. 환경성 오류의 구분은 정적 도구 범위 밖.
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


def check_links(root: Path) -> list[Finding]:
    out: list[Finding] = []
    for path in iter_md_files(root):
        rel = str(path.relative_to(root))
        for raw in links_in(path):
            resolved = resolve_link(path, raw)
            if resolved is None:
                continue
            verdict = classify_target(root, resolved)
            if verdict == "outside":
                if not resolved.exists():
                    out.append(Finding(VIOLATION, "link", rel, f"깨진 링크(루트 밖) -> {raw}"))
            elif verdict == "missing":
                out.append(Finding(VIOLATION, "link", rel, f"깨진 링크 -> {raw}"))
            elif verdict == "case":
                out.append(Finding(VIOLATION, "link", rel, f"대소문자 불일치 링크 (리눅스에서 깨짐) -> {raw}"))
            elif verdict == "nfc":
                out.append(Finding(WARNING, "link", rel, f"유니코드 정규화 불일치 링크 (OS 간 상이 위험) -> {raw}"))
    return out


def link_text_points_to_real(root: Path, source: Path, disp: str, target_path: str) -> bool:
    """파일명 형태의 링크 표시텍스트가 실존 대상을 가리키는지 판정.

    실존을 정확히 가리키는 세 관례를 정당으로 인정한다 (writing-style.md
    "마크다운 링크 표시텍스트", 사용자 결정 2026-07-05 "실존 기반 인정").
      1. 대상 파일명(basename) 일치 - [AGENTS.md](daily/AGENTS.md).
      2. 루트 기준 또는 source 상대로 표시텍스트 경로가 실존 -
         [AGENTS/folder-structure.md](../../AGENTS/folder-structure.md).
      3. 폴더 표기(/로 끝남)의 폴더명이 대상 경로 성분에 존재 -
         [_knowledge/](../_knowledge/AGENTS.md).
    셋 다 아니면 부재 파일을 지칭하는 오도로 본다 (daily.md, _strategy/INDEX.md).
    """
    disp_norm = disp.rstrip("/")
    disp_base = disp_norm.rsplit("/", 1)[-1]
    target_base = target_path.rstrip("/").rsplit("/", 1)[-1]
    if disp_base == target_base:
        return True
    for base in (root, source.parent):
        try:
            if (base / disp_norm).resolve().exists():
                return True
        except OSError:
            # 경로 해석/조회 불가는 "실존하지 않음"과 동일하게 취급하고
            # 다음 관례로 넘어간다.
            pass
    if disp.endswith("/") and disp_base in target_path.split("/"):
        return True
    return False


def check_link_text(root: Path) -> list[Finding]:
    """마크다운 링크 표시텍스트가 실존하지 않는 파일을 지칭하는지 검사.

    링크 대상은 check_links가 실존을 검사하지만 표시텍스트는 그 검사 밖이라,
    폐지된 파일명이나 옛 경로가 표시텍스트로 남으면 링크가 깨지지 않은 채
    독자를 없는 파일로 오도한다 (예: [_strategy/INDEX.md](../AGENTS.md)는 대상이
    실존해 링크는 성립하나 표시텍스트 _strategy/INDEX.md는 부재 파일). 본 검사가
    그 사각을 닫는다. 파일명 형태(공백 없이 .md로 끝나거나 / 포함)의 표시텍스트만
    보며, 자연어 문구와 타이틀은 공백을 포함해 자연 제외된다.
    """
    out: list[Finding] = []
    for path in iter_md_files(root):
        rel = str(path.relative_to(root))
        text = FRONT_MATTER_RE.sub("", read(path))
        text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
        text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
        text = re.sub(r"`[^`\n]*`", "", text)  # 인라인 코드 - 규약 설명의 예시 링크 오탐 방지
        for disp, target in LINK_TEXT_RE.findall(text):
            disp_clean = disp.strip()
            if not disp_clean or " " in disp_clean:
                continue  # 빈 표시텍스트 또는 자연어 문구/타이틀
            if not (disp_clean.endswith(".md") or "/" in disp_clean):
                continue  # 파일명 형태가 아님 (일반 텍스트)
            if SCHEME_RE.match(target):
                continue  # 외부 URL (https: 등)
            target_path = target.split("#", 1)[0]
            if not target_path:
                continue  # 순수 앵커 링크 (#절)
            if link_text_points_to_real(root, path, disp_clean, target_path):
                continue
            out.append(Finding(
                VIOLATION, "link-text", rel,
                f"표시텍스트가 실존하지 않는 대상을 지칭 -> [{disp}]({target})",
            ))
    return out


def normalize_heading(text: str) -> str:
    """헤딩/섹션명 대조용 정규화.

    NFC, 번호 접두(N. ) 제거, 백틱 제거(섹션명이 인라인 코드로 경로를 감쌀 수
    있어 대조 전 제거), 연속 공백 축약. 헤딩과 참조 양측에 같은 정규화를 적용해
    표기 차이를 흡수한다.
    """
    s = ENUM_PREFIX_RE.sub("", nfc(text).strip())
    s = s.replace("`", "")
    return re.sub(r"\s+", " ", s).strip()


def headings_of(path: Path) -> "set[str]":
    """대상 파일의 헤딩 집합(정규화). 코드 펜스 안 예시 헤딩은 제외."""
    body = re.sub(r"```.*?```", "", body_of(path), flags=re.DOTALL)
    return {normalize_heading(h) for h in HEADING_RE.findall(body)}


def check_section_refs(root: Path) -> list[Finding]:
    """로컬 .md 링크 뒤 인용 섹션명이 대상 파일 헤딩에 실존하는지 검사 (경고).

    링크의 파일 실존은 check_links가 보지만 인용 섹션명은 그 검사 밖이라, 섹션이
    개명/삭제되면 링크는 성립한 채 없는 섹션을 가리킨다 (dangling 섹션 참조). 본
    검사가 그 사각을 닫는다. 헤딩의 번호 접두(N. )는 참조가 생략하는 관례라
    정규화 후 대조한다. 대상 파일 부재는 check_links 소관이라 여기서 건너뛴다.
    오탐 위험(섹션 아닌 인용문) 때문에 경고 수준으로 둔다.
    """
    out: list[Finding] = []
    heading_cache: "dict[Path, set[str] | None]" = {}
    for path in iter_md_files(root):
        rel = str(path.relative_to(root))
        text = FRONT_MATTER_RE.sub("", read(path))
        # 코드 펜스만 제거한다. 인라인 코드는 남긴다 - 섹션명이 경로를 백틱으로
        # 감쌀 수 있어(예: "`_reference/` 폴더 처리") 제거하면 섹션명이 훼손된다.
        # 백틱 자체는 normalize_heading이 양측에서 대칭 제거한다.
        text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
        for target, section in SECTION_REF_RE.findall(text):
            resolved = resolve_link(path, target)
            if resolved is None:
                continue
            if classify_target(root, resolved) in ("missing", "outside"):
                continue  # 대상 부재는 check_links가 위반으로 잡는다
            if resolved not in heading_cache:
                try:
                    heading_cache[resolved] = (
                        headings_of(resolved) if resolved.exists() else None
                    )
                except OSError:
                    heading_cache[resolved] = None
            hs = heading_cache[resolved]
            if hs is None or normalize_heading(section) in hs:
                continue
            out.append(Finding(
                WARNING, "section-ref", rel,
                f'인용 섹션명이 대상 헤딩에 없음 -> ({target}) "{section}"',
            ))
    return out


def content_dirs(root: Path):
    """디스크립터 검사 대상 폴더 순회.

    EXEMPT_DIRS(.git, .claude 등 도구 전용)와 그 하위, 중첩 git 레포, 심링크는
    is_excluded가 제외한다.
    _implementation/ 하위 프로젝트 내부(소스 트리)는 제외한다 - 직할
    문서 폴더 AGENTS/만 대상 (cf. folder-structure.md "폴더 구조와 디스크립터"
    _implementation 예외).
    루트 자신도 디스크립터(루트 AGENTS.md)를 가진다.
    """
    yield root
    for path in sorted(root.rglob("*")):
        if not path.is_dir():
            continue
        if is_excluded(root, path):
            continue
        parts = path.relative_to(root).parts
        if len(parts) >= 2 and parts[0] == IMPLEMENTATION_DIR and parts[1] != "AGENTS":
            continue
        yield path


def check_descriptors(root: Path) -> list[Finding]:
    """모든 폴더가 디스크립터(AGENTS.md)를 갖는지, 폴더 직속 md 수 임계를 검사."""
    out: list[Finding] = []
    for d in content_dirs(root):
        rel = d.relative_to(root) if d != root else Path(".")
        # _reference/ 하위 폴더는 immutable raw 보관이라 디스크립터를 강제하지 않는다.
        parts = rel.parts
        in_reference_sub = parts and parts[0] == REFERENCE_DIR and len(parts) > 0 and rel != Path(REFERENCE_DIR)
        descriptor = d / DESCRIPTOR_NAME
        if not descriptor.exists() and not in_reference_sub:
            out.append(Finding(VIOLATION, "descriptor", str(rel), "폴더 디스크립터(AGENTS.md) 없음"))
        # 폴더 직속(하위 폴더 제외) md 파일 수.
        direct_md = [
            p for p in d.iterdir()
            if p.is_file() and p.suffix == ".md" and p.name not in EXEMPT_FILENAMES
        ]
        if len(direct_md) > FOLDER_MD_LIMIT:
            out.append(Finding(
                WARNING, "folder-size", str(rel),
                f"폴더 직속 md {len(direct_md)}개 (> {FOLDER_MD_LIMIT}). 하위 폴더 분화 권고",
            ))
    return out


def check_size(root: Path) -> list[Finding]:
    """문서 유형별 분량 임계.

    히스토리 문서(날짜 프리픽스)는 시간순 누적이 본질이라 완화, 진입층/디스크립터
    (AGENTS.md)는 색인/파일별 안내 표라 완화, 그 외 일반 노드는 기본 임계.
    """
    out: list[Finding] = []
    for path in iter_md_files(root):
        body = body_of(path)
        length = len(re.sub(r"\s", "", body))
        if has_date_prefix(path):
            limit = SIZE_LIMIT_TEMPORAL
        elif path.name == DESCRIPTOR_NAME:
            limit = SIZE_LIMIT_DESCRIPTOR
        else:
            limit = SIZE_LIMIT_NODE
        if length > limit:
            out.append(Finding(
                WARNING, "size", str(path.relative_to(root)),
                f"공백 제외 {length}자 (> {limit}). 여러 관심사가 섞였는지 사람/LLM 판단 필요",
            ))
    return out


def check_temporality_mix(root: Path) -> list[Finding]:
    """현재적 문서(날짜 프리픽스 없음) 본문의 날짜 헤더/불릿 반복을 검출.

    시간순 로그가 현재적 문서에 누적되는 하이브리드화 신호 (proposal 3).
    워크로그(TASK_TREE, STATUS)는 별도 룰이 있어 제외.
    """
    out: list[Finding] = []
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
            out.append(Finding(
                WARNING, "temporality", str(path.relative_to(root)),
                f"날짜 헤더/불릿 {hits}회 반복 (> {TEMPORAL_MIX_REPEAT}). "
                "시간성 혼합 검토 - 히스토리 문서로 분리 대상인지",
            ))
    return out


def check_status_registry(root: Path) -> list[Finding]:
    """STATUS.md가 레지스트리 표 외 서술을 누적하는지 검출 (proposal 2).

    STATUS는 상태 레지스트리다. front matter, 제목, 인용 블록(> 안내),
    마크다운 표만 허용하고 일반 서술 문단이 있으면 위반. 첫 1건에서 멈추지 않고
    모든 표 외 서술 줄을 보고한다. 코드 펜스 안 예시는 다른 검사와 같은 기준으로
    제외한다.
    """
    out: list[Finding] = []
    status = root / WORKLOG_DIR / "STATUS.md"
    if not status.exists():
        return out
    rel = str(status.relative_to(root))
    body = re.sub(r"```.*?```", "", body_of(status), flags=re.DOTALL)
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
        out.append(Finding(
            VIOLATION, "status", rel,
            f'레지스트리 표 외 서술 발견 - "{line[:40]}". '
            "STATUS는 상태 레지스트리이며 진행 서사를 두지 않는다",
        ))
    return out


def check_task_tree_attrs(root: Path) -> list[Finding]:
    """TASK_TREE.md 속성 노드(체크박스 없는 불릿)의 표준 키 위반 검출 (proposal 2).

    작업 노드는 `- [ ]`/`[/]`/`[x]`/`[-]` 형태. 속성 노드는 체크박스 없는
    불릿이며 표준 키(설명, 상태 상세, 외부 참조, 브랜치)로 시작해야 한다.
    프리앰블(인용 블록, 코드 블록)은 검사에서 제외.
    """
    out: list[Finding] = []
    tree = root / WORKLOG_DIR / "TASK_TREE.md"
    if not tree.exists():
        return out
    rel = str(tree.relative_to(root))
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
        # 표준 키로 시작하는지. 키 뒤에 구분자(콜론/공백)나 끝이 와야 한다 -
        # 단순 startswith면 "설명서" 같은 접두 오검출이 생긴다 (제노 1.5).
        if any(
            content == k or (content.startswith(k) and content[len(k):len(k) + 1] in (":", " ", "\t"))
            for k in TASK_TREE_ATTR_KEYS
        ):
            continue
        out.append(Finding(
            WARNING, "task-tree", rel,
            f'속성 노드 비표준 키 - "{content[:40]}". 표준 키: {", ".join(TASK_TREE_ATTR_KEYS)}',
        ))
    return out


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


def check_normative_guides(root: Path) -> list[Finding]:
    """규범 폴더 디스크립터의 파일별 안내 완전성 검사 (경고).

    규범 폴더의 직속 md 파일이 디스크립터 본문에 언급되지 않으면 경고.
    존재를 모르면 위반 행동이 나오는 문서들이므로 안내 누락 자체가 신호다.
    """
    out: list[Finding] = []
    for d in content_dirs(root):
        if not is_normative_dir(root, d):
            continue
        descriptor = d / DESCRIPTOR_NAME
        if not descriptor.exists():
            continue  # 디스크립터 부재는 check_descriptors가 위반으로 잡는다
        text = body_of(descriptor)
        rel = str(d.relative_to(root)) if d != root else "."
        for p in sorted(d.iterdir()):
            if not (p.is_file() and p.suffix == ".md"):
                continue
            if p.name == DESCRIPTOR_NAME or p.name in EXEMPT_FILENAMES:
                continue
            if p.name in text or urllib.parse.quote(p.name) in text:
                continue
            out.append(Finding(
                WARNING, "normative", rel,
                f"디스크립터 파일별 안내에 미등재 - {p.name}. 규범 폴더는 파일별 설명과 읽기 트리거를 유지한다",
            ))
    return out


def check_task_tree_completed_branch(root: Path) -> list[Finding]:
    """완료(`[x]`/`[-]`) 노드에 브랜치 속성이 잔존하는지 검출 (경고).

    완료 시 브랜치 속성은 제거한다 (TASK_TREE 관리 규칙). 잔존하면 끊김
    재진입이 죽은 포인터를 따라갈 수 있다.
    """
    out: list[Finding] = []
    tree = root / WORKLOG_DIR / "TASK_TREE.md"
    if not tree.exists():
        return out
    rel = str(tree.relative_to(root))
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
            out.append(Finding(
                WARNING, "task-tree", rel,
                f'완료 노드에 브랜치 속성 잔존 - "{content[:40]}". 완료 시 브랜치 속성은 제거한다',
            ))
    return out


def check_status_schema(root: Path) -> list[Finding]:
    """STATUS.md 레지스트리 표의 스키마와 시각 표기 형식 검사 (경고)."""
    out: list[Finding] = []
    status = root / WORKLOG_DIR / "STATUS.md"
    if not status.exists():
        return out
    rel = str(status.relative_to(root))
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
                out.append(Finding(
                    WARNING, "status", rel,
                    f"레지스트리 표 헤더가 표준 스키마와 다름 - 기대 {STATUS_HEADER_CELLS}, 실제 {cells}",
                ))
            continue
        if len(cells) != len(STATUS_HEADER_CELLS):
            out.append(Finding(WARNING, "status", rel, f'레지스트리 행 열 수 불일치 - "{line[:40]}"'))
            continue
        value = cells[1]
        if value in STATUS_PLACEHOLDER or STATUS_TIMESTAMP_RE.match(value):
            continue
        out.append(Finding(
            WARNING, "status", rel,
            f'마지막 수행 시각 형식 위반 - "{value}". yyyy-MM-dd HH:mm:ss (KST 기준, 존 표기 생략)',
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


def check_empty_folders(root: Path) -> list[Finding]:
    """디스크립터 외 실체가 0건인 폴더 검출 (경고, 골격 폴더 제외).

    삭제 대상 잔재인지, 사양만 있고 실체 0건인 동결인지, 첫 실체 대기 중인
    정상 신설인지는 감사자(LLM)가 판단한다.
    """
    out: list[Finding] = []
    for d in content_dirs(root):
        rel = d.relative_to(root).as_posix() if d != root else "."
        if rel in SKELETON_DIRS:
            continue
        try:
            entries = [e for e in d.iterdir() if e.name != DESCRIPTOR_NAME]
        except OSError:
            # 목록 불가 폴더는 정적 감사 대상에서 조용히 건너뛴다.
            continue
        if not entries:
            out.append(Finding(
                WARNING, "empty-folder", rel,
                "디스크립터 외 실체 0건. 잔재 삭제/사양 동결/첫 실체 대기 여부 감사자 판단 필요",
            ))
    return out


def check_name_collision(root: Path) -> list[Finding]:
    """하위 문서 묶음이 아닌 동명 문서-폴더 쌍 검출 (경고).

    `X.md` + `X/`는 하위 문서 묶음 관계의 예약 신호다 (cf.
    workspace-and-project-structure.md "하위 문서 폴더 규칙"). 폴더에
    디스크립터 외 md가 없으면 그 관계가 성립할 수 없으므로 확정 검출한다.
    md가 든 동명 쌍의 실제 관계 판단은 감사자(LLM) 몫이다.
    """
    out: list[Finding] = []
    for d in content_dirs(root):
        parts = d.relative_to(root).parts if d != root else ()
        if parts and parts[0] == REFERENCE_DIR:
            continue  # immutable raw 영역의 이름은 규약 대상이 아니다
        for sub in sorted(d.iterdir()):
            if not sub.is_dir() or sub.name in EXEMPT_DIRS:
                continue
            if in_nested_repo(root, sub):
                continue
            doc = d / (sub.name + ".md")
            if not doc.exists():
                continue
            has_md = any(
                p.is_file() and p.suffix == ".md" and p.name != DESCRIPTOR_NAME
                for p in sub.iterdir()
            )
            if not has_md:
                out.append(Finding(
                    WARNING, "naming", str(doc.relative_to(root)),
                    f"동명 폴더 {sub.relative_to(root)}/에 하위 문서가 없음. "
                    "하위 문서 묶음 관계가 아니면 한쪽을 개명한다",
                ))
    return out


def check_filename_portability(root: Path) -> list[Finding]:
    """윈도우 등 다른 OS에서 clone조차 불가능한 이름을 잡는다."""
    out: list[Finding] = []
    for path in sorted(root.rglob("*")):
        if is_excluded(root, path):
            continue
        name = path.name
        rel = str(path.relative_to(root))
        if WINDOWS_FORBIDDEN_RE.search(name):
            out.append(Finding(
                VIOLATION, "portability", rel,
                '윈도우 금지 문자 포함 (< > : " | ? * 또는 제어 문자)',
            ))
        if name != name.rstrip(" ."):
            out.append(Finding(VIOLATION, "portability", rel, "이름 끝의 공백/마침표 (윈도우에서 비정상)"))
        stem = name.split(".", 1)[0].upper()
        if stem in WINDOWS_RESERVED:
            out.append(Finding(VIOLATION, "portability", rel, f"윈도우 예약어 이름 ({stem})"))
    return out


def run_audit(root: Path) -> list[Finding]:
    """모든 검사를 순서대로 실행해 Finding 리스트를 모은다.

    입출력, 종료 코드와 분리된 순수 오케스트레이션 - 단위 테스트가 이 함수를
    직접 호출해 결과를 검증할 수 있다.
    """
    findings: list[Finding] = []
    findings += check_front_matter(root)
    findings += check_links(root)
    findings += check_link_text(root)
    findings += check_section_refs(root)
    findings += check_descriptors(root)
    findings += check_size(root)
    findings += check_temporality_mix(root)
    findings += check_status_registry(root)
    findings += check_status_schema(root)
    findings += check_strategy_fields(root)
    findings += check_task_tree_attrs(root)
    findings += check_task_tree_completed_branch(root)
    findings += check_normative_guides(root)
    findings += check_tags_category(root)
    findings += check_empty_folders(root)
    findings += check_name_collision(root)
    findings += check_filename_portability(root)
    return findings


def main() -> int:
    # 윈도우 콘솔(cp949 등)에서도 한글 출력이 깨지지 않게 UTF-8로 강제
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()
    if not root.is_dir():
        print(f"오류: 디렉토리가 아님 - {root}", file=sys.stderr)
        return 2

    findings = run_audit(root)
    violations = [f for f in findings if f.severity == VIOLATION]
    warnings = [f for f in findings if f.severity == WARNING]

    for f in violations:
        print(f.format())
    for f in warnings:
        print(f.format())
    print(f"\n감사 완료: 위반 {len(violations)}건, 경고 {len(warnings)}건 ({root})")
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())

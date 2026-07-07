#!/usr/bin/env python3
"""에피스테믹 워크스페이스 기계 감사 - 공용 인프라 (Layer 0).

Finding 데이터클래스, 상수, 공용 헬퍼(순회/읽기/링크 해석 등)를 담는다.
검사 함수는 audit_*.py 의미 모듈에, 오케스트레이션과 진입점은 audit.py에 있다.
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
EXEMPT_DIRS = {".git", ".claude", ".gemini", ".github", ".kiro", "node_modules", "_tmp", "__pycache__"}

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
# 비ASCII 문장 부호 검출 대상과 ASCII 대체 힌트 (cf. writing-style/ascii-punctuation.md).
# 코드 펜스, 인라인 코드는 검사 전 제거하므로 규칙 자체의 백틱 예시, 코드,
# 고정폭 box-drawing 트리는 검출에서 빠진다.
NON_ASCII_PUNCT = {
    "—": "em dash - 부연은 ' - ', 정의는 ': ', 분리는 '. '",
    "→": "화살표 - 흐름/상태 변화는 '->'",
    "←": "화살표 - 흐름/상태 변화는 '<-'",
    "·": "가운뎃점 - 나열은 ', ', 양자택일은 '/'",
    "…": "말줄임표 - '...' 또는 '등'",
    "“": "둥근 여는 큰따옴표 - ASCII 큰따옴표 사용",
    "”": "둥근 닫는 큰따옴표 - ASCII 큰따옴표 사용",
    "‘": "둥근 여는 작은따옴표 - ASCII 작은따옴표 사용",
    "’": "둥근 닫는 작은따옴표 - ASCII 작은따옴표 사용",
}

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

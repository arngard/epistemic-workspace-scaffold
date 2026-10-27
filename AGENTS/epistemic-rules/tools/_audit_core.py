#!/usr/bin/env python3
"""에피스테믹 워크스페이스 기계 감사 - 공용 인프라.

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

REFERENCE_DIR = "reference"
IMPLEMENTATION_DIR = "implementation"
WORKLOG_DIR = "worklog"
# 도구 전용 파일은 front matter 면제 (ref: writing-style.md "도구 전용 설정 파일 예외"). SKILL.md는 자체 규격(name, description).
EXEMPT_FILENAMES = {"CLAUDE.md", "copilot-instructions.md", "SKILL.md"}
EXEMPT_DIRS = {".git", ".claude", ".github", ".kiro", "node_modules", ".tmp", "__pycache__"}

# 폴더 디스크립터 파일명. 예외로 정한 폴더를 뺀 모든 폴더가 이 파일을 가진다 (folder-structure.md
# "폴더 구조와 디스크립터"). 같은 폴더의 CLAUDE.md가 @AGENTS.md로 가져온다.
DESCRIPTOR_NAME = "AGENTS.md"

# 아직 실제 내용으로 채워지지 않은 스캐폴드 출고 상태를 알리는 마커. 문서
# front matter의 description과 본문 양쪽에 같은 문구가 있어야 정합이다.
SCAFFOLD_STATE_MARKER = "스캐폴드 상태"

# 규범 폴더 이름과 상류 규범 묶음 이름. 규범 폴더는 어느 깊이에서든 이름이
# AGENTS인 폴더와 그 아래 전부이며, 폴더 디스크립터와 CLAUDE.md 포인터를 두지 않는다.
NORMS_DIR_NAME = "AGENTS"
BUNDLE_NAME = "epistemic-rules"
# 폴더 색인 파일 이름. 쪽이 둘 이상이면 INDEX2.md, INDEX3.md 순이다.
# INDEX.yaml은 색인이 읽는 설명 원본이다.
INDEX_NAME = "INDEX.md"
INDEX_YAML_NAME = "INDEX.yaml"
INDEX_PAGE_RE = re.compile(r"^INDEX(?:[2-9]|[1-9]\d+)?\.md$")


def is_index_file(name: str) -> bool:
    """색인 쪽 파일(INDEX.md, INDEX2.md ...)이나 INDEX.yaml이면 참."""
    return bool(INDEX_PAGE_RE.match(name)) or name == INDEX_YAML_NAME


# 폴더 CLAUDE.md의 표준 내용 - 같은 폴더의 AGENTS.md를 가져온다.
CLAUDE_POINTER = "@AGENTS.md"
# 가져오기 줄: 줄 전체가 공백 없는 @경로. 문장 속 @경로는 가져오기 검사 대상이 아니다.
IMPORT_LINE_RE = re.compile(r"^@(\S+)$")

# 에피스테믹 골격이 출고하는 표준 폴더. 실체 0건 검출에서 상시 예외.
SKELETON_DIRS = {
    ".", "AGENTS", "AGENTS/epistemic-rules/tools", "epistemic-structure",
    "epistemic-structure/ontology", "epistemic-structure/knowledge",
    "epistemic-structure/strategy", "epistemic-structure/architecture",
    WORKLOG_DIR, REFERENCE_DIR, IMPLEMENTATION_DIR,
}

# --- 임계값 ---
# 상류가 보수적 초기값으로 두고 운영하며 조정한다. 상속한 저장소는 이 상수를
# 고치지 않는다(묶음 동일성 검사, 항목 30). 다른 값이 필요하면 경고를
# 의식적으로 수용하거나 상류에 변경을 제안한다.
# 공백 제외 문자 수. "한글 기준" 근사.
SIZE_LIMIT_NODE = 3000        # 지식/전략 노드 등 일반 현재적 문서
SIZE_LIMIT_TEMPORAL = 10000   # 히스토리 문서(날짜 프리픽스)는 누적이 본질
# 진입층(루트 AGENTS.md)과 폴더 디스크립터(AGENTS.md)는 구조적으로 길어진다 -
# 진입층은 요지 가져오기/정체성/고유 규범과 덮어쓰기 목록을 한 파일에 담고,
# 디스크립터는 폴더의 규칙과 하위 구성을 한 파일에 담는다. 상황별 트리거
# 목록은 루트 요지 AGENTS/epistemic-rules.md "이럴 때 읽는다"에 있고, 요지는
# 일반 임계를 따른다 (ref: document-units.md "분량 보조 지표").
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
WINDOWS_FORBIDDEN_RE = re.compile(r'[<>:"|?*\\\x00-\x1f]')
WINDOWS_RESERVED = {"CON", "PRN", "AUX", "NUL"} | {f"COM{i}" for i in range(1, 10)} | {
    f"LPT{i}" for i in range(1, 10)
}
# front matter 날짜 필드 값 형식 (yyyy-MM-dd). 필드 존재만 보면 잘못된 값이
# 통과하므로 값도 검사한다.
DATE_VALUE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# 전략 문서(epistemic-structure/strategy 4범주 직속)의 추가 필수 속성 (ref: strategy/AGENTS/epistemic-rules.md
# "Front matter 속성"). 하위 폴더 문서와 디스크립터에는 강제하지 않는다.
STRATEGY_DIR = "epistemic-structure/strategy"
STRATEGY_FIELDS = ("importance", "urgency")
# 날짜 프리픽스: 파일명이 yyyy-MM-dd로 시작하면 히스토리 문서.
# 시각 확장(yyyy-MM-ddTHH-mm)도 인정한다 (ref: document-temporality.md).
# 규약상 구분자는 띄어쓰기이나, 하이픈 구분자도 프리픽스로 인정해 기존
# 문서가 히스토리 문서로 판정되게 한다. 하이픈 구분자는 별도로 경고한다.
DATE_PREFIX_RE = re.compile(r"^\d{4}-\d{2}-\d{2}([-.T ]|$)")
DATE_HYPHEN_SEPARATOR_RE = re.compile(r"^\d{4}-\d{2}-\d{2}(T\d{2}-\d{2})?-")
# 본문 내 날짜 헤더/불릿 반복 검출 (시간성 혼합 신호).
DATE_LINE_RE = re.compile(r"^\s*(?:[-*#>]+\s*)*\d{4}-\d{2}-\d{2}\b", re.MULTILINE)
# TASK_TREE 속성 노드 표준 키. 이 키로 시작하는 불릿만 표준으로 인정.
TASK_TREE_ATTR_KEYS = ("설명", "상태 상세", "외부 참조", "브랜치")
# STATUS 레지스트리 표의 시각 표기와 표준 헤더. 미수행 placeholder는 허용.
# 시각은 KST 기준이며 존 표기는 생략하는 것이 관례다. 관례를 어기고 " KST"를
# 덧붙인 자식 기재도 깨지지 않게 접미를 선택적으로 허용한다.
STATUS_TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}( KST)?$")
STATUS_HEADER_CELLS = ["이름", "마지막 수행"]
STATUS_PLACEHOLDER = {"(아직 없음)", "-"}
# 비ASCII 문장 부호 검출 대상과 ASCII 대체 힌트 (ref: writing-style/ascii-punctuation.md).
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


def text_size(text: str) -> int:
    """분량 검사의 분량. 공백 문자를 뺀 글자 수다.

    감사 분량 검사와 색인 쪽 나누기가 같은 함수를 써서 둘이 어긋나지 않는다.
    """
    return len(re.sub(r"\s", "", text))


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
    제외한다. 카테고리별 추가 규칙(reference, implementation)은 각 호출부가
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

    reference/ 내부는 immutable raw 자료라 규약 검사 대상이 아니다
    (디스크립터 AGENTS.md 자체와 규범 폴더 reference/AGENTS/만 예외).
    implementation/ 하위 프로젝트 내부(소스 트리)도 대상이 아니다 -
    소스 폴더 구조는 코드 생태계 관례가 지배한다 (ref: folder-structure.md
    "폴더 구조와 디스크립터" implementation 예외). 직할 AGENTS.md와
    그 하위 문서 폴더 AGENTS/만 검사한다.
    reference/와 implementation/ 직속의 생성 색인 쪽 파일(INDEX.md, INDEX2.md
    ...)은 감사 대상이다. 그 하위 폴더의 색인 쪽 파일은 대상이 아니다.
    도구 전용 폴더, 중첩 git 레포, 심링크 제외는 is_excluded가 담당한다.
    """
    ref_descriptor = (root / REFERENCE_DIR / DESCRIPTOR_NAME).resolve()
    for path in sorted(root.rglob("*.md")):
        if is_excluded(root, path):
            continue
        parts = path.relative_to(root).parts
        if (
            len(parts) == 2 and parts[0] in (REFERENCE_DIR, IMPLEMENTATION_DIR)
            and INDEX_PAGE_RE.match(parts[1])
        ):
            yield path
            continue
        descriptor = (
            (parts[0] == REFERENCE_DIR and path.resolve() == ref_descriptor)
            or (parts[0] == IMPLEMENTATION_DIR and parts[1:] == (DESCRIPTOR_NAME,))
        )
        if in_material_content(root, path) and not descriptor:
            continue
        yield path


def in_material_content(root: Path, path: Path) -> bool:
    """path가 자료 폴더(reference/, implementation/)에서 규범 폴더 밖인지 판정한다.

    루트 상대 경로의 첫 성분이 reference나 implementation이고 둘째 성분이
    AGENTS가 아니면 참이다. 자료 폴더 자신은 거짓이고, 그 직속 파일
    (디스크립터와 색인 쪽 포함)은 참이다. 그런 예외는 호출부가 정한다.
    감사 순회(iter_md_files)와 묶음 파일 목록(_bundle_core.bundle_files)이
    함께 쓴다. 자료로 들여온 사본이나 하위 프로젝트의 클론을 규약 문서나
    상류 묶음으로 오인하지 않으려는 것이다.
    """
    parts = path.relative_to(root).parts
    return (
        len(parts) >= 2 and parts[0] in (REFERENCE_DIR, IMPLEMENTATION_DIR)
        and parts[1] != NORMS_DIR_NAME
    )


def in_norms_dir(root: Path, d: Path) -> bool:
    """폴더 d가 규범 폴더(루트 상대 경로 성분에 AGENTS가 있는 폴더)인지 판정.

    파일은 path.parent로 부른다. 루트 자신은 규범 폴더가 아니다.
    """
    return NORMS_DIR_NAME in d.relative_to(root).parts


def _has_bundle_pair(parts: "tuple[str, ...]") -> bool:
    """경로 성분에 AGENTS 바로 다음 epistemic-rules가 있으면 참."""
    return any(
        a == NORMS_DIR_NAME and b == BUNDLE_NAME for a, b in zip(parts, parts[1:])
    )


def in_bundle_detail(root: Path, d: Path) -> bool:
    """폴더 d가 묶음 세부 폴더(AGENTS 바로 다음 성분이 epistemic-rules)인지 판정."""
    return _has_bundle_pair(d.relative_to(root).parts)


def is_bundle_path(root: Path, path: Path) -> bool:
    """path가 상류 규범 묶음 경로인지 판정한다.

    루트 상대 경로 성분에 AGENTS 바로 다음 epistemic-rules가 있거나, 이름이
    epistemic-rules.md이고 부모 폴더 이름이 AGENTS이면 참이다(묶음 요지 파일).
    경로 모양만 보며 파일 실재나 순회 제외는 보지 않는다.
    """
    parts = path.relative_to(root).parts
    if _has_bundle_pair(parts):
        return True
    return (
        len(parts) >= 2 and parts[-1] == BUNDLE_NAME + ".md"
        and parts[-2] == NORMS_DIR_NAME
    )


def imports_in(path: Path) -> "list[tuple[int, str]]":
    """front matter와 코드 펜스 밖의 가져오기 줄 (줄 번호, 경로) 목록.

    가져오기 줄은 줄 전체가 @경로인 줄이다. 줄 번호는 파일 전체 기준 1부터다.
    """
    text = read(path)
    match = FRONT_MATTER_RE.match(text)
    offset = text[:match.end()].count("\n") if match else 0
    out: "list[tuple[int, str]]" = []
    in_fence = False
    for i, line in enumerate(text[match.end():].splitlines() if match else text.splitlines()):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = IMPORT_LINE_RE.match(stripped)
        if m:
            out.append((offset + i + 1, m.group(1)))
    return out


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
    """파일명 형태의 링크 표시텍스트가 링크 대상 자체를 가리키는지 판정.

    대상은 링크를 둔 문서 위치에서 링크 대상을 풀어낸 경로(해석된 대상)다.
    정당한 형태 (writing-style/markdown-link-display-text.md):
      1. / 없는 표시텍스트는 대상 파일명(basename)과 같다 -
         [AGENTS.md](daily/AGENTS.md).
      2. / 로 끝나는 폴더 표기는 그 폴더명이 해석된 대상의 루트 상대 경로
         성분에 있다 - [knowledge/](../knowledge/AGENTS.md). 루트 밖 대상은
         링크 대상 문자열의 성분과 대조한다.
      3. 그 밖의 경로형은 루트나 문서 기준으로 정규화한 결과가 대상과 같거나
         (루트 기준 경로, 대상 문자열 그대로, ./x.md 등), . 과 .. 없이 해석된
         대상의 루트 상대 경로 끝 성분과 같다 -
         [agent-roles/epistemic-auditor.md](../agent-roles/epistemic-auditor.md).
         루트 밖 대상은 끝부분 형태를 받지 않는다.
    경로는 심링크를 따르지 않고 문자열로 정규화하며, 표시텍스트, 링크 대상,
    파일시스템에서 온 문서와 루트 경로를 모두 NFC로 맞춘다. 대상의 실존은
    check_links 소관이라 여기서 보지 않는다. 어느 형태도 아니면 없는 파일이나
    다른 위치를 지칭하는 오도로 본다.
    """
    disp = nfc(disp)
    target_path = nfc(target_path)
    base_dir = nfc(os.path.abspath(str(source.parent)))
    root_dir = nfc(os.path.abspath(str(root)))
    target = os.path.normpath(os.path.join(base_dir, target_path))
    try:
        rel = os.path.relpath(target, root_dir)
    except ValueError:
        rel = None  # 윈도우에서 드라이브가 다름 (루트 밖)
    if rel is not None and (rel == os.pardir or rel.startswith(os.pardir + os.sep)):
        rel = None  # 루트 밖
    rel_parts = rel.split(os.sep) if rel is not None else None
    if disp.endswith("/"):
        disp_base = disp.rstrip("/").rsplit("/", 1)[-1]
        if rel_parts is None:
            return disp_base in target_path.split("/")
        return disp_base in rel_parts
    if "/" not in disp:
        return disp == os.path.basename(target)
    for base in (root_dir, base_dir):
        if os.path.normpath(os.path.join(base, disp)) == target:
            return True
    disp_parts = disp.split("/")
    # 해석된 경로 성분에는 빈 성분, . , .. 이 없어 아래 비교로도 걸러지나
    # 끝부분 형태의 조건을 드러내려고 먼저 거부한다.
    if {"", ".", ".."} & set(disp_parts):
        return False
    if rel_parts is None:
        return False  # 루트 밖 대상은 끝부분 형태를 받지 않는다
    return rel_parts[-len(disp_parts):] == disp_parts


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
    implementation/ 하위 프로젝트 내부(소스 트리)는 제외한다 - 직할
    문서 폴더 AGENTS/만 대상 (ref: folder-structure.md "폴더 구조와 디스크립터"
    implementation 예외).
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


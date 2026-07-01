#!/usr/bin/env python3
"""에피스테믹 워크스페이스 기계 감사 (Layer 0, 도구 중립).

epistemic-auditor의 형식 점검 항목을 결정론적으로 검사한다.
의미 판단(카테고리 배치 적절성, 워크로그 최신성)은 다루지 않는다 -
그건 LLM 감사자의 몫으로 남는다.

점검 항목:
  1. YAML front matter 필수 필드 (date created, date modified, tags)
  2. 카테고리 INDEX와 실제 파일의 양방향 대조 (sub-INDEX 위임 인정)
  3. _reference/ 인벤토리와 실제 내용의 양방향 대조
  4. 문서 간 상대 마크다운 링크 정합 (대소문자, 유니코드 정규화 포함)
  5. 파일명의 크로스 플랫폼 이식성 (윈도우 금지 문자, 예약어 등)
  6. 단일 문서 분량 상한(공백 제외 3,000자) - 경고만

위치: AGENTS/tools/audit.py. 사용 안내 문서는 AGENTS/tools.md "기계 감사 스크립트".

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
"""

import re
import sys
import unicodedata
import urllib.parse
from pathlib import Path

CATEGORY_DIRS = ["_docs/_ontology", "_docs/_knowledge", "_docs/_strategy", "_docs/_architecture"]
REFERENCE_DIR = "_reference"
# 도구 전용 파일은 front matter 면제 (cf. agent-roles.md 점검 항목 3,
# conventions.md "도구 전용 파일 예외"). SKILL.md는 자체 규격(name, description).
EXEMPT_FILENAMES = {"CLAUDE.md", "GEMINI.md", "copilot-instructions.md", "SKILL.md"}
EXEMPT_DIRS = {".git", ".claude", ".gemini", ".github", ".kiro", "node_modules"}
SIZE_LIMIT = 3000  # 공백 제외 문자 수. "한글 기준 3,000자"의 근사.

FRONT_MATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
# URL 스킴은 2글자 이상으로 판별 - 윈도우 드라이브 문자(C: 등) 오인 방지
SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]+:")
WINDOWS_FORBIDDEN_RE = re.compile(r'[<>:"|?*\x00-\x1f]')
WINDOWS_RESERVED = {"CON", "PRN", "AUX", "NUL"} | {f"COM{i}" for i in range(1, 10)} | {
    f"LPT{i}" for i in range(1, 10)
}

violations: list[str] = []
warnings: list[str] = []


def nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text)


def iter_md_files(root: Path):
    """규약 검사 대상 .md 순회.

    _reference/ 내부는 immutable raw 자료라 규약 검사 대상이 아니다
    (INDEX.md 자체만 예외). 인벤토리 대조는 check_reference_inventory가 담당.
    """
    ref_index = (root / REFERENCE_DIR / "INDEX.md").resolve()
    for path in sorted(root.rglob("*.md")):
        parts = path.relative_to(root).parts
        if any(part in EXEMPT_DIRS for part in parts):
            continue
        if parts and parts[0] == REFERENCE_DIR and path.resolve() != ref_index:
            continue
        yield path


def read(path: Path) -> str:
    # 인코딩을 UTF-8로 고정 - 윈도우의 로케일 기본 인코딩(cp949)에 의존하지 않는다.
    return path.read_text(encoding="utf-8", errors="replace")


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


def registered_targets(index_path: Path) -> set[Path]:
    """INDEX 문서가 링크로 등록한 파일 경로 집합 (NFC 정규화 문자열 기준)."""
    targets = set()
    for raw in links_in(index_path):
        resolved = resolve_link(index_path, raw)
        if resolved is not None:
            targets.add(nfc(str(resolved)))
    return targets


def check_category_indexes(root: Path):
    for category in CATEGORY_DIRS:
        cat_dir = root / category
        if not cat_dir.is_dir():
            continue
        index = cat_dir / "INDEX.md"
        if not index.exists():
            violations.append(f"[index] {category}/INDEX.md 없음")
            continue
        # 색인 문서 집합: INDEX.md + 폴더 동반 문서(X.md 옆에 X/ 폴더가 있는
        # "하위 문서 폴더 규칙" 케이스, 예: lessons.md가 lessons/를 관리).
        index_docs = set(cat_dir.rglob("INDEX.md"))
        for path in cat_dir.rglob("*.md"):
            if path.with_suffix("").is_dir():
                index_docs.add(path)
        registered: set[str] = set()
        for idx in index_docs:
            registered |= registered_targets(idx)
        index_keys = {nfc(str(p.resolve())) for p in index_docs}
        for path in cat_dir.rglob("*.md"):
            if path == index:
                continue
            key = nfc(str(path.resolve()))
            if key in registered:
                continue
            if key in index_keys:
                violations.append(
                    f"[index] {path.relative_to(root)}: 부모 INDEX에 미등록 sub-INDEX"
                )
            else:
                violations.append(
                    f"[index] {path.relative_to(root)}: 어떤 INDEX에도 미등록"
                )


def check_reference_inventory(root: Path):
    ref_dir = root / REFERENCE_DIR
    if not ref_dir.is_dir():
        return
    index = ref_dir / "INDEX.md"
    if not index.exists():
        violations.append(f"[reference] {REFERENCE_DIR}/INDEX.md 없음")
        return
    index_text = nfc(read(index))
    # 인벤토리 단위는 _reference/ 직하 항목(파일 또는 폴더 통째)이다.
    for path in sorted(ref_dir.iterdir()):
        if path == index or path.name.startswith("."):
            continue
        # 항목 이름이 INDEX 본문에 등장하면 등재로 본다 (NFC 정규화 비교).
        if nfc(path.name) not in index_text:
            violations.append(
                f"[reference] {path.relative_to(root)}: INDEX 미등재 (신규 미처리 자료?)"
            )
    # 역방향(INDEX에 있으나 폴더에 없음)은 check_links가 잡는다.


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


def check_size(root: Path):
    for path in iter_md_files(root):
        body = FRONT_MATTER_RE.sub("", read(path))
        length = len(re.sub(r"\s", "", body))
        if length > SIZE_LIMIT:
            warnings.append(
                f"[size] {path.relative_to(root)}: 공백 제외 {length}자 (> {SIZE_LIMIT}). "
                "여러 관심사가 섞였는지 사람/LLM 판단 필요"
            )


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
    check_category_indexes(root)
    check_reference_inventory(root)
    check_filename_portability(root)
    check_size(root)

    for line in violations:
        print(f"VIOLATION {line}")
    for line in warnings:
        print(f"WARNING   {line}")
    print(f"\n감사 완료: 위반 {len(violations)}건, 경고 {len(warnings)}건 ({root})")
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())

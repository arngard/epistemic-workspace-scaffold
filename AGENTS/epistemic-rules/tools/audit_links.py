"""문서 간 링크와 참조 정합 검사.

공용 인프라는 _audit_core, 오케스트레이션은 audit.py.
"""
import re
import urllib.parse
from pathlib import Path

from _audit_core import *  # noqa: F401,F403 - Finding, 상수, 공용 헬퍼


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


# 대상에 공백이 든 링크. LINK_RE는 공백 든 대상을 링크로 인식하지 않으므로
# 깨진 링크 검사에도 걸리지 않고 조용히 통과한다. 링크 제목 문법
# [x](path "title")은 정당하므로 제외한다.
SPACED_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\n]*\s[^)\n]*)\)")
LINK_TITLE_RE = re.compile(r"""^\S+\s+(?:"[^"]*"|'[^']*')$""")
# 파일이나 폴더 링크로 보이는 대상만 검사한다(확장자나 / 로 끝남, 앵커 허용).
# 대괄호 뒤에 괄호 설명을 붙인 일반 문장을 링크로 오인하지 않기 위함이다.
DOC_TARGET_RE = re.compile(r"(\.[A-Za-z0-9]{1,8}(#.*)?|/)$")


def check_link_whitespace(root: Path) -> list[Finding]:
    """링크 대상에 공백이 든 로컬 파일, 폴더 링크를 검출한다 (위반).

    링크 대상의 공백은 %20으로 쓴다 (ref: document-temporality.md). 공백 든
    대상은 링크 해석에서 빠져 실존 검사를 받지 못한다.
    """
    out: list[Finding] = []
    for path in iter_md_files(root):
        rel = str(path.relative_to(root))
        text = FRONT_MATTER_RE.sub("", read(path))
        text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
        text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
        text = re.sub(r"`[^`\n]*`", "", text)
        for target in SPACED_LINK_RE.findall(text):
            t = target.strip()
            if not re.search(r"\s", t):
                continue  # 대상 앞뒤 공백만 있음 (공백 든 대상이 아님)
            if SCHEME_RE.match(t) or LINK_TITLE_RE.match(t) or not DOC_TARGET_RE.search(t):
                continue
            out.append(Finding(
                VIOLATION, "link", rel,
                f"링크 대상에 공백 - %20으로 쓴다 -> ({target})",
            ))
    return out


def check_link_text(root: Path) -> list[Finding]:
    """마크다운 링크 표시텍스트가 실존하지 않는 파일을 지칭하는지 검사.

    링크 대상은 check_links가 실존을 검사하지만 표시텍스트는 그 검사 밖이라,
    폐지된 파일명이나 옛 경로가 표시텍스트로 남으면 링크가 깨지지 않은 채
    독자를 없는 파일로 오도한다 (예: [strategy/INDEX.md](../AGENTS.md)는 대상이
    실존해 링크는 성립하나 표시텍스트 strategy/INDEX.md는 부재 파일). 본 검사가
    그 사각을 닫는다. 파일명 형태의 표시텍스트만 본다 - 공백 없이 (.md로 끝나거나
    / 를 포함한 것), 그리고 경로 성분 중 하나가 날짜 프리픽스로 시작하면서 .md나
    / 로 끝나는 것(날짜 문서와 폴더는 이름에 공백이 든다). 그 밖에 공백이 든
    자연어 문구와 타이틀은 제외된다. 표시텍스트와 대상 모두 %20 등을 디코딩해
    비교한다.
    """
    out: list[Finding] = []
    for path in iter_md_files(root):
        rel = str(path.relative_to(root))
        text = FRONT_MATTER_RE.sub("", read(path))
        text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
        text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
        text = re.sub(r"`[^`\n]*`", "", text)  # 인라인 코드 - 규약 설명의 예시 링크 오탐 방지
        for disp, target in LINK_TEXT_RE.findall(text):
            disp_clean = urllib.parse.unquote(disp.strip())
            if not disp_clean:
                continue
            if " " in disp_clean and not (
                any(DATE_PREFIX_RE.match(c) for c in disp_clean.split("/"))
                and (disp_clean.endswith(".md") or disp_clean.endswith("/"))
            ):
                continue  # 자연어 문구/타이틀 (공백 든 날짜 문서, 폴더 이름은 검사)
            if not (disp_clean.endswith(".md") or "/" in disp_clean):
                continue  # 파일명 형태가 아님 (일반 텍스트)
            if SCHEME_RE.match(target):
                continue  # 외부 URL (https: 등)
            target_path = urllib.parse.unquote(target.split("#", 1)[0])
            if not target_path:
                continue  # 순수 앵커 링크 (#절)
            if link_text_points_to_real(root, path, disp_clean, target_path):
                continue
            out.append(Finding(
                VIOLATION, "link-text", rel,
                f"표시텍스트가 실존하지 않는 대상을 지칭 -> [{disp}]({target})",
            ))
    return out


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
        # 감쌀 수 있어(예: "`reference/` 폴더 처리") 제거하면 섹션명이 훼손된다.
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


# 참조 표지 검사 (see: writing-style.md "참조 표지").
# 표지는 줄 머리(목록 기호, 인용 기호, 각주 정의 뒤)나 여는 괄호 바로 뒤에 올
# 때만 표지로 본다 - 산문 한가운데의 "see:" 같은 문자열은 표지가 아니다.
OLD_MARKER_RE = re.compile(r"(?<![\w.])(cf|ref)\.(?=\s)")
LINE_HEAD_RE = re.compile(r"^\s*(?:(?:[-*+]|\d+\.|>)\s+)*(?:\[\^[^\]\s]+\]:\s*)?")
HEAD_MARKER_RE = re.compile(r"^(ref|sub|see):(.*)$")
PAREN_MARKER_RE = re.compile(r"\((ref|sub|see):([^)]*)")
_LINK_UNIT = r'\[[^\]]*\]\([^)\s]+\)(?:\s*"[^"\n]*")?'
# 명사에 바로 붙인 동격 괄호(예: 히스토리 문서([x](x)))는 그 명사를 가리키는 녹인
# 링크라 제외하고, 공백 뒤에 따로 둔 괄호만 본다.
PAREN_LINK_ONLY_RE = re.compile(rf"(?:^|(?<=\s))\(\s*{_LINK_UNIT}(?:\s*,\s*{_LINK_UNIT})*\s*\)")


def _marker_tail_problem(marker: str, tail: str) -> "str | None":
    """표지 뒤 형태 판정. 문제가 없으면 None.

    세 표지 모두 링크나, 링크하기 어려운 대상의 설명으로 잇는다. 설명이 워크스페이스
    안 문서를 제목만 적은 것인지는 기계로 가를 수 없어 의미 감사 소관이다.
    """
    if not tail.startswith(" ") or not tail.strip():
        return f"{marker}: 뒤에 공백 한 칸과 링크나 설명이 와야 한다"
    return None


def check_reference_markers(root: Path) -> list[Finding]:
    """참조 표기 규약 검사.

    - 폐지된 옛 표기 `cf.`, `ref.` - 위반.
    - 표지(ref:, sub:, see:) 뒤 형태 불량 - 위반.
    - 표지 없이 공백 뒤 괄호에 둔 링크(괄호 안이 링크뿐) - 경고. 문장 속에 녹은
      링크인지의 경계가 모호할 수 있어 경고로 둔다. 표 행은 표지를 생략할 수 있는
      형태라 이 경고를 내지 않고 옛 표기와 형태 불량만 본다.
    링크만 있는 목록 항목은 보지 않는다. 표지를 생략할 수 있는 색인 목록과 표지를
    달아야 하는 참고 목록이 형태로 갈리지 않아 의미 감사 소관이다.
    코드 펜스, 인라인 코드, HTML 주석 안은 예시나 메타 서술이라 보지 않는다. 판정은
    인라인 코드를 한 글자 자리표로 바꾼 줄로 하고, 메시지에는 원래 줄을 인용한다.
    지우지 않고 자리표를 두는 것은 표지 뒤 대상이 인라인 코드일 때 꼬리가 비었다고
    오판하지 않기 위해서다.
    """
    out: list[Finding] = []
    for path in iter_md_files(root):
        rel = str(path.relative_to(root))
        text = FRONT_MATTER_RE.sub("", read(path))
        text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
        text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
        for raw in text.splitlines():
            line = re.sub(r"`[^`\n]*`", "C", raw)
            quote = raw.strip()[:60]
            in_table = line.lstrip().startswith("|")
            for m in OLD_MARKER_RE.finditer(line):
                out.append(Finding(
                    VIOLATION, "ref-marker", rel,
                    f"폐지된 참조 표기 {m.group(1)}. - ref:, sub:, see: 표지로 바꾼다 -> {quote}",
                ))
            rest = line[LINE_HEAD_RE.match(line).end():].rstrip()
            head = None if in_table else HEAD_MARKER_RE.match(rest)
            if head:
                problem = _marker_tail_problem(head.group(1), head.group(2))
                if problem:
                    out.append(Finding(VIOLATION, "ref-marker", rel, f"{problem} -> {quote}"))
            for pm in PAREN_MARKER_RE.finditer(line):
                problem = _marker_tail_problem(pm.group(1), pm.group(2))
                if problem:
                    out.append(Finding(VIOLATION, "ref-marker", rel, f"{problem} -> {quote}"))
            if in_table:
                continue
            for pm in PAREN_LINK_ONLY_RE.finditer(line):
                out.append(Finding(
                    WARNING, "ref-marker", rel,
                    f"표지 없이 괄호에 둔 링크 - ref:, sub:, see:를 단다 -> {quote}",
                ))
    return out


def check_imports(root: Path) -> list[Finding]:
    """`@` 가져오기 줄의 대상 실재 검사.

    줄 전체가 @경로인 줄만 가져오기로 본다. 대상은 줄을 둔 파일 위치 기준이며
    없으면 위반이다. 묶음 세부 폴더 안의 가져오기는 경고한다. 검사 파일은
    iter_md_files의 파일과 각 폴더의 CLAUDE.md다.
    """
    files = set(iter_md_files(root))
    for d in content_dirs(root):
        pointer = d / "CLAUDE.md"
        if pointer.is_file() and not is_excluded(root, pointer):
            files.add(pointer)
    out: list[Finding] = []
    for path in sorted(files):
        rel = str(path.relative_to(root))
        for lineno, raw in imports_in(path):
            target = (path.parent / urllib.parse.unquote(raw)).resolve()
            if not target.exists():
                out.append(Finding(VIOLATION, "import", rel, f"{lineno}행 가져오기 대상 없음 -> @{raw}"))
            if in_bundle_detail(root, path.parent):
                out.append(Finding(
                    WARNING, "import", rel,
                    f"{lineno}행 묶음 세부 문서 안의 가져오기. 가져오기는 폴더 AGENTS.md와 묶음 요지에만 둔다",
                ))
    return out

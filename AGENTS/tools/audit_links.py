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

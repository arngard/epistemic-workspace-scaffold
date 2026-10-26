"""폴더 색인 정합과 색인 설명 원본 검사.

색인 쪽 내용은 생성기와 같은 _index_core.render_all로 만들어 디스크와
비교하므로 생성기와 감사가 어긋나지 않는다. 파일을 쓰지 않고 git에도
의존하지 않는다. 규칙의 원본은 AGENTS/epistemic-rules/folder-index.md다.

공용 인프라는 _audit_core와 _index_core, 오케스트레이션은 audit.py.
"""
import re
from pathlib import Path

from _audit_core import *  # noqa: F401,F403 - Finding, 상수, 공용 헬퍼
from _index_core import (
    INDEX_DESC_LIMIT, INDEX_KEYS, REFERENCE_STATUSES, SELF_KEY, STRUCTURE_KEY,
    UNREGISTERED,
    IndexFormatError, entry_paths, front_matter_description, in_reference_subfolder,
    index_dirs, index_yaml_lines, list_entries, load_index_yaml, render_all)

BUILD_TOOL = "AGENTS/epistemic-rules/tools/build_index.py"
BUILD_HINT = f"{BUILD_TOOL}로 다시 만든다"


def _punct_hints(text: str) -> "list[tuple[str, str]]":
    """설명 값의 비ASCII 문장 부호와 대체 힌트. 인라인 코드 안은 뺀다."""
    text = re.sub(r"`[^`\n]*`", "", text)
    return [(ch, hint) for ch, hint in NON_ASCII_PUNCT.items() if ch in text]


def _rel(root: Path, path: Path) -> str:
    """루트 상대 POSIX 경로. 루트 자신은 ".", 루트 밖이면 받은 경로 그대로."""
    try:
        rel = path.relative_to(root).as_posix()
    except ValueError:
        return str(path)
    return rel if rel else "."


def _format_error(root: Path, e: IndexFormatError) -> Finding:
    """IndexFormatError 하나를 파일과 줄을 담은 위반 1건으로 바꾼다."""
    where = _rel(root, Path(e.path)) if e.path is not None else "."
    if e.line:
        message = f"{e.line}행 INDEX.yaml 형식 오류 - {e.message}"
    else:
        message = f"색인 생성 오류 - {e.message}"
    return Finding(VIOLATION, "index", where, message)


def check_index_files(root: Path) -> list[Finding]:
    """색인 쪽 파일과 생성 결과의 대조, 색인을 두지 않는 폴더의 색인 파일 검사.

    색인 폴더에 INDEX.md가 없으면 경고. 쪽 내용이 render_all과 다르거나(줄바꿈은
    LF로 맞춰 비교), 필요한 쪽이 없거나, 필요한 쪽 밖의 쪽 파일이 있으면 위반.
    색인 폴더가 아닌 폴더(규범 폴더 포함)의 INDEX*.md, INDEX.yaml은 위반이다.
    reference/ 하위 폴더는 원본 자료라 보지 않는다. 다만 규범 폴더
    reference/AGENTS/와 그 아래는 본다(iter_md_files와 같은 예외). 중첩 저장소
    안은 content_dirs가 이미 뺀다. 색인 폴더 판정이 IndexFormatError를 내면
    위반 1건만 내고 끝낸다. 렌더가 IndexFormatError를 내면 위반 1건을 내고 내용
    비교만 건너뛴다.
    """
    out: list[Finding] = []
    try:
        dirs = set(index_dirs(root))
    except IndexFormatError as e:
        return [_format_error(root, e)]
    try:
        pages: "dict[Path, str] | None" = render_all(root)
    except IndexFormatError as e:
        out.append(_format_error(root, e))
        pages = None
    for d in content_dirs(root):
        if d not in dirs:
            if (in_reference_subfolder(root, d)
                    and d.relative_to(root).parts[1] != NORMS_DIR_NAME):
                continue  # 원본 자료 안의 색인 파일은 원본의 일부다
            for p in sorted(d.iterdir()):
                if is_index_file(p.name):
                    out.append(Finding(
                        VIOLATION, "index", _rel(root, p),
                        "색인을 두지 않는 폴더의 색인 파일. 색인은 AGENTS.md가 "
                        "있는 폴더(규범 폴더 제외)에만 둔다",
                    ))
            continue
        first = d / INDEX_NAME
        if not first.is_file():
            out.append(Finding(
                WARNING, "index", _rel(root, d),
                f"색인 {INDEX_NAME} 없음. {BUILD_TOOL}로 만든다",
            ))
        if pages is None:
            continue
        for p in sorted(d.iterdir()):
            if not (INDEX_PAGE_RE.match(p.name) and p.is_file()):
                continue
            if p not in pages:
                out.append(Finding(
                    VIOLATION, "index", _rel(root, p),
                    f"필요한 쪽 밖의 색인 쪽 파일. {BUILD_HINT}",
                ))
            elif read(p).replace("\r\n", "\n") != pages[p]:
                out.append(Finding(
                    VIOLATION, "index", _rel(root, p),
                    f"색인 내용이 생성 결과와 다름. {BUILD_HINT}",
                ))
        if not first.is_file():
            continue  # 색인 전체가 없으면 경고 하나로 둔다
        for p in sorted(k for k in pages if k.parent == d):
            if not p.is_file():
                out.append(Finding(
                    VIOLATION, "index", _rel(root, p),
                    f"필요한 색인 쪽 파일 없음. {BUILD_HINT}",
                ))
    return out


def _description_line(path: Path) -> int:
    """front matter description 줄의 줄 번호. 없으면 0."""
    for no, line in enumerate(read(path).split("\n"), start=1):
        if line.startswith("description:"):
            return no
    return 0


def _check_front_matter_descriptions(root: Path, paths: "list[Path]") -> list[Finding]:
    out: list[Finding] = []
    for p in paths:
        if p.suffix != ".md" or not p.is_file():
            continue
        try:
            desc = front_matter_description(p)
        except IndexFormatError as e:
            out.append(Finding(
                WARNING, "index-source", _rel(root, p),
                f"{e.line}행 description 형식 오류 - {e.message}. 색인에 설명이 빠진다",
            ))
            continue
        if desc is None:
            continue
        if len(desc) > INDEX_DESC_LIMIT:
            out.append(Finding(
                WARNING, "index-source", _rel(root, p),
                f"{_description_line(p)}행 description {len(desc)}자 "
                f"(> {INDEX_DESC_LIMIT}). 한두 문장으로 줄인다",
            ))
        for ch, hint in _punct_hints(desc):
            out.append(Finding(
                WARNING, "index-source", _rel(root, p),
                f"{_description_line(p)}행 description의 비ASCII 문장 부호 "
                f"'{ch}' (U+{ord(ch):04X}) - {hint}",
            ))
    return out


def check_index_sources(root: Path) -> list[Finding]:
    """색인 설명 원본(front matter description, INDEX.yaml) 검사 (경고).

    색인 폴더마다 본다. md 문서의 description 형식 오류와 길이 초과,
    INDEX.yaml 항목의 대상 부재, reference/ 밖에서 md 문서를 가리키는 항목,
    동명 문서가 있는 폴더 항목, 알 수 없는 키, 설명 길이 초과, reference/
    항목의 status 누락이나 어휘 밖 값, reference/ 직속의 미등록 항목,
    순차 분류로 선언된 폴더 INDEX.yaml의 "." 밖 항목, reference/ 밖 항목의
    쓰이지 않는 status 키, 설명(description, "."의 structure)의 비ASCII 문장
    부호를 경고한다. 생성 색인 쪽은 항목 20에서 빠지므로 문장 부호는 고칠 수
    있는 원본 위치에서 알린다. "." 항목의 structure 키는 키 검사와 대상 부재
    검사에서 뺀다.
    INDEX.yaml 형식 오류는 check_index_files가 위반으로 내므로 여기서는
    그 파일(색인 폴더 판정이 실패하면 전부)을 건너뛴다.
    """
    out: list[Finding] = []
    try:
        dirs = index_dirs(root)
        children: "dict[Path, list[Path]]" = {}
        for p in entry_paths(root):
            children.setdefault(p.parent, []).append(p)
    except IndexFormatError:
        return out
    ref_dir = root / REFERENCE_DIR
    for d in dirs:
        yaml_path = d / INDEX_YAML_NAME
        try:
            data = load_index_yaml(yaml_path)
        except IndexFormatError:
            continue
        lines = index_yaml_lines(yaml_path) if data else {}
        rel_yaml = _rel(root, yaml_path)

        def warn(name: str, message: str) -> None:
            out.append(Finding(
                WARNING, "index-source", rel_yaml,
                f'{lines.get(name, 0)}행 "{name}" - {message}',
            ))

        def punct(name: str, key: str, value: "str | None") -> None:
            for ch, hint in _punct_hints(value or ""):
                warn(name, f"{key}의 비ASCII 문장 부호 '{ch}' "
                           f"(U+{ord(ch):04X}) - {hint}")

        if SELF_KEY in data:
            punct(SELF_KEY, STRUCTURE_KEY, data[SELF_KEY].get(STRUCTURE_KEY))
            for name in data:
                if name != SELF_KEY:
                    warn(name, '순차 분류로 선언한 폴더의 "." 밖 항목. '
                               "색인에 쓰이지 않는 설명이다")
            continue
        in_ref = d == ref_dir
        kids = children.get(d, [])
        files = {nfc(p.name) for p in kids if not p.is_dir()}
        folders = {nfc(p.name) + "/" for p in kids if p.is_dir()}
        if not in_ref:
            out += _check_front_matter_descriptions(root, kids)
        for name, fields in data.items():
            if name not in files and name not in folders:
                if in_ref:
                    warn(name, "대상 자료가 없음. 자료가 사라졌는지 확인한다")
                else:
                    warn(name, "대상이 색인 항목에 없음(부재, 점 파일, 운영 파일 등)")
                continue
            if name.endswith(".md") and not in_ref:
                warn(name, "md 문서의 설명은 문서 front matter의 description에 둔다")
                continue
            if name.endswith("/") and name[:-1] + ".md" in files:
                warn(name, f"동명 문서 {name[:-1]}.md가 있어 쓰이지 않는다. "
                           "설명은 그 문서에 둔다")
                continue
            for key in fields:
                if key not in INDEX_KEYS:
                    warn(name, f"알 수 없는 키 {key}. 키는 {', '.join(INDEX_KEYS)}다")
            desc = fields.get("description")
            if desc is not None and len(desc) > INDEX_DESC_LIMIT:
                warn(name, f"설명 {len(desc)}자 (> {INDEX_DESC_LIMIT})")
            punct(name, "description", desc)
            if not in_ref and "status" in fields:
                warn(name, "쓰이지 않는 키 status. 처리 상태는 reference/ 항목에만 둔다")
            if in_ref:
                status = fields.get("status")
                if status is None:
                    warn(name, "status 없음")
                elif status not in REFERENCE_STATUSES:
                    warn(name, f"status {status}는 어휘 밖이다. "
                               f"{', '.join(REFERENCE_STATUSES)} 가운데 쓴다")
        if in_ref:
            rel_d = _rel(root, d)
            try:
                entries = list_entries(root, d)
            except IndexFormatError:
                continue  # 이름 충돌은 check_index_files가 위반으로 낸다
            for e in entries:
                if e.status == UNREGISTERED:
                    out.append(Finding(
                        WARNING, "index-source", f"{rel_d}/{e.name}",
                        f"{rel_yaml}에 등록되지 않은 자료. "
                        "처리 상태(status)와 설명을 등록한다",
                    ))
    return out

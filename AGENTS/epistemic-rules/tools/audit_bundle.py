"""상류 묶음 검사: 출처 태그(항목 29)와 출고 목록 대조(항목 30)."""

from pathlib import Path

from _audit_core import (
    BUNDLE_NAME, EXEMPT_FILENAMES, INDEX_PAGE_RE, VIOLATION, WARNING, Finding,
    is_bundle_path, iter_md_files, nfc)
from _bundle_core import (
    MANIFEST_REL, ManifestFormatError, bundle_files, file_digest, own_root,
    read_manifest)
from _tags_core import TagFormatError, front_matter_tags

_REMEDY = (
    "상류 저장소면 python3 AGENTS/epistemic-rules/tools/build_index.py . "
    "--bundle-manifest로 목록을 다시 만들고, 상속한 저장소면 파일을 상류 "
    "판으로 되돌리고 차이를 자손 소유 파일로 옮긴다"
)


def check_source_tags(root: Path) -> list[Finding]:
    """상류 묶음 md의 출처 태그 검사 (항목 29, 범주 source-tag).

    묶음 안의 md가 tags에 epistemic-rules를 담지 않으면 위반, 묶음 밖 md가
    그 태그를 담으면 경고다. 범위는 태그를 모으는 문서(iter_md_files에서
    도구 전용 파일과 생성 색인 쪽 파일을 뺀 것)다. tags를 읽을 수 없는
    문서는 항목 14가 다루므로 건너뛴다.
    """
    out: list[Finding] = []
    for path in iter_md_files(root):
        if path.name in EXEMPT_FILENAMES or INDEX_PAGE_RE.match(path.name):
            continue
        try:
            tags = front_matter_tags(path)
        except TagFormatError:
            continue
        rel = str(path.relative_to(root))
        has_source = tags is not None and BUNDLE_NAME in tags
        if is_bundle_path(root, path):
            if not has_source:
                out.append(Finding(
                    VIOLATION, "source-tag", rel,
                    f"상류 묶음 문서의 tags에 {BUNDLE_NAME}가 없음",
                ))
        elif has_source:
            out.append(Finding(
                WARNING, "source-tag", rel,
                f"상류 묶음 밖 문서가 출처 태그 {BUNDLE_NAME}를 담음. "
                "상류 문서를 묶음 밖으로 베낀 것이 아닌지 확인하고 태그를 뺀다",
            ))
    return out


def check_bundle_identity(
    root: Path, tools_dir: "Path | None" = None,
) -> list[Finding]:
    """상류 묶음 파일과 출고 목록의 대조 (항목 30, 범주 bundle).

    감사 도구(tools_dir, 기본값은 이 모듈의 폴더)가 감사 대상 루트의 묶음
    도구 폴더와 같을 때만 검사한다. 같은데 목록이 없으면 위반이다. 목록
    줄 형식 오류는 위반 1건으로 알리고 비교를 건너뛴다. 그 밖에는 내용이
    다른 파일, 목록에 있는데 없는 파일, 목록에 없는 묶음 파일을 파일마다
    위반으로 낸다.
    """
    if tools_dir is None:
        tools_dir = Path(__file__).resolve().parent
    if not own_root(root, tools_dir):
        return []
    manifest_path = root / MANIFEST_REL
    if not manifest_path.is_file():
        return [Finding(
            VIOLATION, "bundle", MANIFEST_REL,
            f"상류 묶음 출고 목록이 없음. {_REMEDY}",
        )]
    try:
        manifest = read_manifest(manifest_path)
    except ManifestFormatError as e:
        where = f" ({e.line}행)" if e.line else ""
        return [Finding(
            VIOLATION, "bundle", MANIFEST_REL,
            f"출고 목록 형식 오류{where} - {e}. 목록은 읽지 못해 대조하지 "
            f"않음. {_REMEDY}",
        )]
    disk = {
        nfc(p.relative_to(root).as_posix()): p for p in bundle_files(root)
    }
    out: list[Finding] = []
    for rel in sorted(manifest):
        path = disk.get(rel)
        if path is None:
            out.append(Finding(
                VIOLATION, "bundle", rel,
                f"출고 목록에 있는 상류 묶음 파일이 없음. {_REMEDY}",
            ))
            continue
        shown = str(path.relative_to(root))
        try:
            same = file_digest(path) == manifest[rel]
        except OSError as e:
            out.append(Finding(
                VIOLATION, "bundle", shown,
                f"상류 묶음 파일을 읽을 수 없음 - {e.strerror or e}",
            ))
            continue
        if not same:
            out.append(Finding(
                VIOLATION, "bundle", shown,
                f"상류 묶음 파일 내용이 출고 목록과 다름. {_REMEDY}",
            ))
    for rel in sorted(set(disk) - set(manifest)):
        out.append(Finding(
            VIOLATION, "bundle", str(disk[rel].relative_to(root)),
            f"상류 묶음 경로의 파일이 출고 목록에 없음. {_REMEDY}",
        ))
    return out

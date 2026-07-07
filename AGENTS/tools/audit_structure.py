"""폴더 구조, 디스크립터, 파일명 이식성 검사.

공용 인프라는 _audit_core, 오케스트레이션은 audit.py.
"""
import re
import urllib.parse
from pathlib import Path

from _audit_core import *  # noqa: F401,F403 - Finding, 상수, 공용 헬퍼


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

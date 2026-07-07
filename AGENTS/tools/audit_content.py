"""문서 내용(분량, 시간성 혼합, 문장 부호) 검사.

공용 인프라는 _audit_core, 오케스트레이션은 audit.py.
"""
import re
import urllib.parse
from pathlib import Path

from _audit_core import *  # noqa: F401,F403 - Finding, 상수, 공용 헬퍼


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


def check_ascii_punctuation(root: Path) -> list[Finding]:
    """문서 본문의 비ASCII 문장 부호를 검출한다 (경고).

    writing-style/ascii-punctuation.md가 ASCII 우선 표기를 규정하나 audit이
    강제하지 않던 것을 보완한다 (이아리스 B-2). 코드 펜스, 인라인 코드, HTML
    주석은 검사 전 제거하므로 규칙 자체의 백틱 예시와 코드, 고정폭 box-drawing
    트리는 제외된다. 직접 인용(사용자/외부 텍스트)은 정적으로 판별할 수 없어
    경고 수준으로 둔다 - 위반 격상은 규약 SSOT 소유자 결정.

    파일당 문자 종류별 1건만 보고한다 (같은 문자 반복은 소음이라 접는다).
    """
    out: list[Finding] = []
    for path in iter_md_files(root):
        rel = str(path.relative_to(root))
        text = FRONT_MATTER_RE.sub("", read(path))
        text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
        text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
        text = re.sub(r"`[^`\n]*`", "", text)
        for ch, hint in NON_ASCII_PUNCT.items():
            if ch in text:
                out.append(Finding(
                    WARNING, "ascii-punct", rel,
                    f"비ASCII 문장 부호 '{ch}' (U+{ord(ch):04X}) - {hint}",
                ))
    return out

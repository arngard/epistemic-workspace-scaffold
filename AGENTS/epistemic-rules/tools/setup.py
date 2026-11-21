#!/usr/bin/env python3
"""워크스페이스 설치기 (AI가 부르는 도구).

설치 명세(_setup_core.py docstring)의 항목을 점검하고, 사용자 동의 뒤 적용한다. 갱신
흐름과 처음 설치의 정본은 AGENTS/epistemic-rules/workspace-setup.md다. 사용자는 갱신
내용과 영향 범위를 보고 동의만 하고, 명령은 AI가 실행한다.

사용법:
    python3 -B AGENTS/epistemic-rules/tools/setup.py status <루트> [--json]
        항목마다 실제 점검을 돌려 미적용 항목만 짧게 낸다(세션 시작 요약의 환경 갱신 절).
    python3 -B AGENTS/epistemic-rules/tools/setup.py check <루트> [--json]
        모든 항목의 점검 결과를 항목별로 낸다.
    python3 -B AGENTS/epistemic-rules/tools/setup.py plan <루트> [id ...] [--json]
        적용할 항목과 바뀔 대상(지금 값과 새 값)을 동의 요청의 재료로 낸다. id가 없으면
        미적용 항목 전부.
    python3 -B AGENTS/epistemic-rules/tools/setup.py apply <루트> id ...
        지정한 항목만 적용한다.
    (윈도우에서는 python 또는 py -3 런처로 동일하게 실행)

status, check, plan은 아무것도 쓰지 않는다. apply는 적용하는 항목의 값만 쓴다.

--json은 항목마다 id, title, state, changes, targets, detail을 담은 배열을 낸다.
state는 ok, pending(미적용), tool-too-old(이 설치기가 모르는 유형), not-applicable(이
머신에 해당하지 않음), changes는 적용이 바꾸는 것(clone: 그 클론의 git 설정, none: 없음)이다.

종료 코드:
    0  성공(status, plan, apply) 또는 모든 항목이 맞음(check)
    1  check에서 미적용 항목이 있음
    1  check에서 명세 오류가 있음
    2  사용법 오류, 모르는 id나 유형, 이 머신에 해당하지 않는 항목, 적용 실패,
       plan에서 명세를 하나도 읽지 못함
"""

import argparse
import json
import sys
from pathlib import Path

import _setup_core as core

def entry_dict(entry: "core.Entry", root: Path) -> dict:
    item = entry.item
    return {
        "id": item.id, "title": item.title, "state": entry.state,
        "changes": core.changes(item), "targets": core.targets(item, root), "detail": entry.detail,
    }


def emit(entries: "list[core.Entry]", root: Path, as_json: bool, lines: "list[str]") -> None:
    if as_json:
        print(json.dumps([entry_dict(e, root) for e in entries], ensure_ascii=False, indent=2))
    else:
        print("\n".join(lines))


def cmd_status(root: Path, as_json: bool) -> int:
    if as_json:
        entries, errors = core.status(root)
        for e in errors:
            print(f"명세 오류: {e}", file=sys.stderr)
        emit(entries, root, True, [])
    else:
        print("\n".join(core.status_lines(root)))
    return 0


def cmd_check(root: Path, as_json: bool) -> int:
    entries, errors = core.status(root)
    for e in errors:
        print(f"명세 오류: {e}", file=sys.stderr)
    lines = [f"- {e.item.id} [{e.state}]: {e.detail}" for e in entries]
    emit(entries, root, as_json, lines)
    return 1 if errors or any(e.state in ("pending", "tool-too-old") for e in entries) else 0


def cmd_plan(root: Path, ids: "list[str]", as_json: bool) -> int:
    entries, errors = core.status(root)
    for e in errors:
        print(f"명세 오류: {e}", file=sys.stderr)
    if errors and not entries:
        print("Spec unreadable. 설치 명세를 읽지 못해 계획을 낼 수 없다.", file=sys.stderr)
        return 2
    by_id = {e.item.id: e for e in entries}
    unknown = [i for i in ids if i not in by_id]
    if unknown:
        print(f"Unknown item id. 모르는 항목 id: {', '.join(unknown)}", file=sys.stderr)
        return 2
    chosen = [by_id[i] for i in ids] if ids else [e for e in entries if e.state == "pending"]
    lines = []
    for e in chosen:
        target = "; ".join(core.targets(e.item, root)) or e.detail
        lines.append(f"- {e.item.title} [{core.CHANGES_LABEL[core.changes(e.item)]}]: {target}")
    emit(chosen, root, as_json, lines or ["적용할 항목이 없다"])
    return 0


def cmd_apply(root: Path, ids: "list[str]") -> int:
    items, errors = core.load_items(root)
    by_id = {i.id: i for i in items}
    unknown = [i for i in ids if i not in by_id]
    if unknown:
        print(f"Unknown item id. 모르는 항목 id: {', '.join(unknown)}", file=sys.stderr)
        return 2
    chosen = [by_id[i] for i in ids]
    os_name = core.current_os()
    skipped = [i.id for i in chosen if not core.applicable(i, os_name, lambda c: core.shutil.which(c) is not None)]
    if skipped:
        print(f"Not applicable on this machine. 이 머신에 해당하지 않는 항목: {', '.join(skipped)}", file=sys.stderr)
        return 2
    old = [i.id for i in chosen if i.kind not in core.KINDS]
    if old:
        print(f"Tool is older than the spec. {core.TOOL_TOO_OLD}: {', '.join(old)}", file=sys.stderr)
        return 2
    code = 0
    for item in chosen:
        result = core.apply_item(root, item)
        if result.ok:
            print(f"- {item.id}: 적용함 ({result.detail})")
        else:
            print(f"- {item.id}: 실패 ({result.detail})", file=sys.stderr)
            code = 2
    return code


def main(argv: "list[str] | None" = None) -> int:
    parser = argparse.ArgumentParser(description="워크스페이스 설치기")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("status", "check", "plan", "apply"):
        p = sub.add_parser(name)
        p.add_argument("root")
        if name in ("plan", "apply"):
            p.add_argument("ids", nargs="*" if name == "plan" else "+")
        if name != "apply":
            p.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"Root is not a directory. 루트가 디렉토리가 아니다: {root}", file=sys.stderr)
        return 2
    if args.command == "status":
        return cmd_status(root, args.json)
    if args.command == "check":
        return cmd_check(root, args.json)
    if args.command == "plan":
        return cmd_plan(root, args.ids, args.json)
    return cmd_apply(root, args.ids)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    sys.exit(main())

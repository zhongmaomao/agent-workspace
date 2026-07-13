#!/usr/bin/env python3
"""Maintain grill-with-tree decision trees as deterministic YAML."""

from __future__ import annotations

import argparse
import datetime as _dt
import os
import re
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

try:
    import yaml
except ModuleNotFoundError:  # PyYAML 是状态文件读写的硬依赖
    print("error: PyYAML is required. Install it with: pip install pyyaml", file=sys.stderr)
    raise SystemExit(2)


VALID_STATUSES = {"open", "answered", "branching", "closed", "revisit"}
CLOSED_STATUSES = {"closed"}

# 文本含换行或超过该长度时改用块标量(|-),与历史手写格式保持一致
_BLOCK_SCALAR_THRESHOLD = 78


class _TreeDumper(yaml.SafeDumper):
    """保持插入顺序、不排序键的 YAML dumper。"""


def _represent_str(dumper: yaml.SafeDumper, value: str):
    # 长文本/多行用块标量(|-)提升可读性;短标量交给 PyYAML 默认:键保持裸、
    # 数字/时间等歧义值会被自动加引号,读回时仍是字符串(再由 _stringify 兜底)
    if "\n" in value or len(value) > _BLOCK_SCALAR_THRESHOLD:
        return dumper.represent_scalar("tag:yaml.org,2002:str", value, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", value)


_TreeDumper.add_representer(str, _represent_str)


class TreeError(RuntimeError):
    pass


def now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).astimezone().isoformat(timespec="seconds")


def slugify(value: str) -> str:
    slug = re.sub(r"[^\w]+", "-", value, flags=re.UNICODE).strip("-_").lower()
    return slug or "session"


def today_stamp() -> str:
    return _dt.datetime.now().strftime("%Y%m%d")


def build_document_title(title: str, doc_title: Optional[str], date_stamp: Optional[str]) -> str:
    if doc_title:
        return doc_title
    if date_stamp and not re.fullmatch(r"\d{8}", date_stamp):
        raise TreeError("--date must be formatted as YYYYMMDD")
    return f"{title}-{date_stamp or today_stamp()}"


def _stringify(value: object) -> object:
    """统一成字符串/容器,避免 PyYAML 把数字、时间、布尔解析成非字符串类型。"""
    if isinstance(value, dict):
        return {str(key): _stringify(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_stringify(item) for item in value]
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (_dt.datetime, _dt.date)):
        return value.isoformat()
    return str(value)


def load_tree(path: Path) -> Dict[str, object]:
    if not path.exists():
        raise TreeError(f"YAML file does not exist: {path}")
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise TreeError(f"Invalid YAML in {path}: {exc}") from exc
    if loaded is None:
        loaded = {}
    if not isinstance(loaded, dict):
        raise TreeError(f"Top-level YAML must be a mapping: {path}")
    root = _stringify(loaded)
    normalize_tree(root)
    return root


def dump_tree(data: Dict[str, object]) -> str:
    return yaml.dump(
        data,
        Dumper=_TreeDumper,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
        width=4096,
    )


def write_tree(path: Path, data: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data["updated_at"] = now_iso()
    validate_tree(data)
    path.write_text(dump_tree(data), encoding="utf-8")


def normalize_tree(data: Dict[str, object]) -> None:
    data.setdefault("schema_version", "1")
    data.setdefault("title", "")
    data.setdefault("created_at", "")
    data.setdefault("updated_at", "")
    data.setdefault("status", "open")
    data.setdefault("alignment", {})
    data.setdefault("terms", {})
    data.setdefault("decisions", {})

    if not isinstance(data["alignment"], dict):
        raise TreeError("alignment must be a mapping")
    if not isinstance(data["terms"], dict):
        raise TreeError("terms must be a mapping")
    if not isinstance(data["decisions"], dict):
        raise TreeError("decisions must be a mapping")

    alignment = data["alignment"]
    alignment.setdefault("requirement_overview", "")
    alignment.setdefault("change_surface", "")
    alignment.setdefault("source_context", "")


def validate_tree(data: Dict[str, object]) -> None:
    normalize_tree(data)
    status = str(data.get("status", "open"))
    if status not in VALID_STATUSES:
        raise TreeError(f"Invalid tree status: {status}")

    decisions = get_decisions(data)
    for qid, node in decisions.items():
        if not isinstance(node, dict):
            raise TreeError(f"Decision {qid} must be a mapping")
        parent = str(node.get("parent", ""))
        if parent and parent not in decisions:
            raise TreeError(f"Decision {qid} has missing parent {parent}")
        node_status = str(node.get("status", "open"))
        if node_status not in VALID_STATUSES:
            raise TreeError(f"Decision {qid} has invalid status {node_status}")
        if node_status in CLOSED_STATUSES:
            for child_id, child in decisions.items():
                if str(child.get("parent", "")) == qid and str(child.get("status", "open")) not in CLOSED_STATUSES:
                    raise TreeError(f"Decision {qid} is closed but child {child_id} is still open")


def get_decisions(data: Dict[str, object]) -> Dict[str, Dict[str, object]]:
    decisions = data.get("decisions", {})
    if not isinstance(decisions, dict):
        raise TreeError("decisions must be a mapping")
    return decisions  # type: ignore[return-value]


def get_terms(data: Dict[str, object]) -> Dict[str, Dict[str, object]]:
    terms = data.get("terms", {})
    if not isinstance(terms, dict):
        raise TreeError("terms must be a mapping")
    return terms  # type: ignore[return-value]


def default_output_path(root: Path, document_title: str) -> Path:
    return root / "Docs" / "Plan" / "grill-with-tree" / f"{slugify(document_title)}.yaml"


def sibling_ids(decisions: Dict[str, Dict[str, object]], parent: str) -> List[str]:
    return [qid for qid, node in decisions.items() if str(node.get("parent", "")) == parent]


def order_from_id(qid: str) -> Optional[int]:
    tail = qid.rsplit(".", 1)[-1]
    match = re.fullmatch(r"Q?(\d+)", tail)
    if not match:
        return None
    return int(match.group(1))


def sort_key(item: Tuple[str, Dict[str, object]]) -> Tuple[int, str]:
    qid, node = item
    raw_order = str(node.get("order", ""))
    if raw_order.isdigit():
        return int(raw_order), qid
    id_order = order_from_id(qid)
    return (id_order if id_order is not None else 999999, qid)


def next_question_id(decisions: Dict[str, Dict[str, object]], parent: str) -> str:
    siblings = sibling_ids(decisions, parent)
    used: List[int] = []
    for qid in siblings:
        parsed = order_from_id(qid)
        if parsed is not None:
            used.append(parsed)
    next_number = max(used, default=0) + 1
    return f"Q{next_number}" if not parent else f"{parent}.{next_number}"


def new_tree(title: str, overview: str, change_surface: str, source_context: str) -> Dict[str, object]:
    now = now_iso()
    return {
        "schema_version": "1",
        "title": title,
        "created_at": now,
        "updated_at": now,
        "status": "open",
        "alignment": {
            "requirement_overview": overview,
            "change_surface": change_surface,
            "source_context": source_context,
        },
        "terms": {},
        "decisions": {},
    }


def require_node(data: Dict[str, object], qid: str) -> Dict[str, object]:
    decisions = get_decisions(data)
    if qid not in decisions:
        raise TreeError(f"Decision does not exist: {qid}")
    return decisions[qid]


def children_of(decisions: Dict[str, Dict[str, object]], parent: str) -> List[Tuple[str, Dict[str, object]]]:
    return sorted(
        ((qid, node) for qid, node in decisions.items() if str(node.get("parent", "")) == parent),
        key=sort_key,
    )


def find_next(data: Dict[str, object]) -> Optional[Tuple[str, str]]:
    decisions = get_decisions(data)

    def walk(qid: str, node: Dict[str, object]) -> Optional[Tuple[str, str]]:
        status = str(node.get("status", "open"))
        if status in CLOSED_STATUSES:
            return None
        if status == "open":
            return qid, "ask this question or record the user's answer"

        for child_id, child in children_of(decisions, qid):
            found = walk(child_id, child)
            if found:
                return found

        if status == "answered":
            return qid, "decide whether to close this answer or add a deeper branch"
        if status == "branching":
            return qid, "add the next child branch or close the branch if its children are resolved"
        if status == "revisit":
            return qid, "rework this branch because alignment changed"
        return qid, "resolve this branch"

    for qid, node in children_of(decisions, ""):
        found = walk(qid, node)
        if found:
            return found
    return None


def print_node(data: Dict[str, object], qid: str, reason: Optional[str] = None) -> None:
    node = require_node(data, qid)
    if reason:
        print(f"next: {qid} ({reason})")
    else:
        print(f"node: {qid}")
    print(f"status: {node.get('status', 'open')}")
    parent = str(node.get("parent", ""))
    if parent:
        print(f"parent: {parent}")
    print(f"question: {node.get('question', '')}")
    print(f"recommendation: {node.get('recommendation', '')}")
    grounding = str(node.get("grounding", ""))
    if grounding:
        print(f"grounding: {grounding}")
    feedback = str(node.get("user_feedback", ""))
    if feedback:
        print(f"user_feedback: {feedback}")
    resolution = str(node.get("resolution", ""))
    if resolution:
        print(f"resolution: {resolution}")


def cmd_init(args: argparse.Namespace) -> None:
    root = Path(args.root).resolve()
    document_title = build_document_title(args.title, args.doc_title, args.date)
    path = Path(args.file).resolve() if args.file else default_output_path(root, document_title)
    if path.exists() and not args.force:
        raise TreeError(f"Refusing to overwrite existing file without --force: {path}")
    data = new_tree(document_title, args.overview, args.change_surface, args.source_context)
    write_tree(path, data)
    print(path)


def cmd_set_alignment(args: argparse.Namespace) -> None:
    path = Path(args.file).resolve()
    data = load_tree(path)
    alignment = data["alignment"]
    if not isinstance(alignment, dict):
        raise TreeError("alignment must be a mapping")
    if args.overview is not None:
        alignment["requirement_overview"] = args.overview
    if args.change_surface is not None:
        alignment["change_surface"] = args.change_surface
    if args.source_context is not None:
        alignment["source_context"] = args.source_context
    if args.status is not None:
        data["status"] = args.status
    write_tree(path, data)
    print(path)


def cmd_add_question(args: argparse.Namespace) -> None:
    path = Path(args.file).resolve()
    data = load_tree(path)
    decisions = get_decisions(data)
    parent = args.parent or ""
    if parent and parent not in decisions:
        raise TreeError(f"Parent decision does not exist: {parent}")

    qid = args.id or next_question_id(decisions, parent)
    if qid in decisions and not args.replace:
        raise TreeError(f"Decision already exists without --replace: {qid}")
    if args.status not in VALID_STATUSES:
        raise TreeError(f"Invalid status: {args.status}")

    order = args.order
    if order is None:
        parsed_order = order_from_id(qid)
        order = parsed_order if parsed_order is not None else len(sibling_ids(decisions, parent)) + 1

    previous = decisions.get(qid, {}) if args.replace else {}
    grounding = args.grounding if args.grounding is not None else str(previous.get("grounding", ""))
    decisions[qid] = {
        "parent": parent,
        "order": str(order),
        "status": args.status,
        "question": args.question,
        "recommendation": args.recommendation,
        "grounding": grounding,
        "user_feedback": str(previous.get("user_feedback", "")),
        "resolution": str(previous.get("resolution", "")),
        "notes": str(previous.get("notes", "")),
    }
    write_tree(path, data)
    if not str(grounding).strip():
        print(
            "warning: no --grounding given; inspect code/docs before branching, "
            "or mark a pure product decision as 'product: ...'.",
            file=sys.stderr,
        )
    print_node(data, qid)


def cmd_update_question(args: argparse.Namespace) -> None:
    path = Path(args.file).resolve()
    data = load_tree(path)
    node = require_node(data, args.id)

    if args.status is not None:
        if args.status not in VALID_STATUSES:
            raise TreeError(f"Invalid status: {args.status}")
        node["status"] = args.status
    if args.question is not None:
        node["question"] = args.question
    if args.recommendation is not None:
        node["recommendation"] = args.recommendation
    if args.grounding is not None:
        node["grounding"] = args.grounding
    if args.feedback is not None:
        node["user_feedback"] = args.feedback
        if args.status is None and str(node.get("status", "open")) == "open":
            node["status"] = "answered"
    if args.resolution is not None:
        node["resolution"] = args.resolution
    if args.notes is not None:
        node["notes"] = args.notes
    if args.append_note is not None:
        existing = str(node.get("notes", ""))
        entry = f"{now_iso()}: {args.append_note}"
        node["notes"] = f"{existing}\n{entry}".strip() if existing else entry

    write_tree(path, data)
    print_node(data, args.id)


def cmd_set_term(args: argparse.Namespace) -> None:
    path = Path(args.file).resolve()
    data = load_tree(path)
    terms = get_terms(data)
    term_id = args.id or f"T{len(terms) + 1}"
    terms[term_id] = {"name": args.name, "meaning": args.meaning}
    write_tree(path, data)
    print(path)


def cmd_next(args: argparse.Namespace) -> None:
    path = Path(args.file).resolve()
    data = load_tree(path)
    found = find_next(data)
    if not found:
        print("next: none (all decision branches are closed)")
        return
    qid, reason = found
    print_node(data, qid, reason)
    print(
        "reminder: before opening a child branch, ground its question and recommendation "
        "in code/docs (inspect first); mark pure product decisions as 'product: ...'."
    )


def cmd_validate(args: argparse.Namespace) -> None:
    path = Path(args.file).resolve()
    data = load_tree(path)
    validate_tree(data)
    print(f"valid: {path}")


def cmd_show(args: argparse.Namespace) -> None:
    path = Path(args.file).resolve()
    data = load_tree(path)
    sys.stdout.write(dump_tree(data))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(dest="command", required=True)

    init = subcommands.add_parser("init", help="Create or replace a decision tree YAML file.")
    init.add_argument("--root", default=os.getcwd(), help="Project root for default Docs/Plan output.")
    init.add_argument("--file", help="Explicit YAML output path.")
    init.add_argument("--doc-title", help="Concrete document title/basename. Defaults to '<title>-YYYYMMDD'.")
    init.add_argument("--date", help="Date stamp for generated document titles, formatted as YYYYMMDD.")
    init.add_argument("--title", required=True, help="Requirement title used to derive the document title.")
    init.add_argument("--overview", required=True)
    init.add_argument("--change-surface", required=True)
    init.add_argument("--source-context", default="")
    init.add_argument("--force", action="store_true", help="Overwrite an existing YAML file.")
    init.set_defaults(func=cmd_init)

    align = subcommands.add_parser("set-alignment", help="Update the top-level alignment fields.")
    align.add_argument("--file", required=True)
    align.add_argument("--overview")
    align.add_argument("--change-surface")
    align.add_argument("--source-context")
    align.add_argument("--status", choices=sorted(VALID_STATUSES))
    align.set_defaults(func=cmd_set_alignment)

    add = subcommands.add_parser("add-question", help="Add or replace a decision-tree question.")
    add.add_argument("--file", required=True)
    add.add_argument("--id", help="Question id, such as Q1 or Q1.1. Auto-generated when omitted.")
    add.add_argument("--parent", default="", help="Parent question id for a child branch.")
    add.add_argument("--order", type=int)
    add.add_argument("--status", default="open", choices=sorted(VALID_STATUSES))
    add.add_argument("--question", required=True)
    add.add_argument("--recommendation", required=True)
    add.add_argument(
        "--grounding",
        help=(
            "Evidence the branch rests on; inspect before guessing. Use a typed prefix: "
            "'code: <files/symbols> - <fact>', 'docs: <source> - <fact>', "
            "'product: needs user decision', or 'assumption: <to verify>'."
        ),
    )
    add.add_argument("--replace", action="store_true")
    add.set_defaults(func=cmd_add_question)

    update = subcommands.add_parser("update-question", help="Update a decision-tree question.")
    update.add_argument("--file", required=True)
    update.add_argument("--id", required=True)
    update.add_argument("--status", choices=sorted(VALID_STATUSES))
    update.add_argument("--question")
    update.add_argument("--recommendation")
    update.add_argument("--grounding")
    update.add_argument("--feedback")
    update.add_argument("--resolution")
    update.add_argument("--notes")
    update.add_argument("--append-note")
    update.set_defaults(func=cmd_update_question)

    term = subcommands.add_parser("set-term", help="Add or replace a glossary term.")
    term.add_argument("--file", required=True)
    term.add_argument("--id")
    term.add_argument("--name", required=True)
    term.add_argument("--meaning", required=True)
    term.set_defaults(func=cmd_set_term)

    next_cmd = subcommands.add_parser("next", help="Print the next unresolved node in DFS order.")
    next_cmd.add_argument("--file", required=True)
    next_cmd.set_defaults(func=cmd_next)

    validate = subcommands.add_parser("validate", help="Validate a decision tree YAML file.")
    validate.add_argument("--file", required=True)
    validate.set_defaults(func=cmd_validate)

    show = subcommands.add_parser("show", help="Print normalized YAML.")
    show.add_argument("--file", required=True)
    show.set_defaults(func=cmd_show)

    return parser


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        args.func(args)
    except TreeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Report whether profile/profile.yml is complete enough to search.

The example file uses `status: template` and empty values. Setup must leave
status as template until the person confirms, then set it to ready.

    python3 tools/check_setup.py
    python3 tools/check_setup.py path/to/profile.yml
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROFILE = ROOT / "profile" / "profile.yml"

# Non-empty scalars or non-empty lists. Empty lists are allowed for exclusions.
REQUIRED = (
    "person.name",
    "person.location",
    "target.headline",
    "target.level",
    "target.titles",
    "target.summary",
    "evidence.core",
    "fit.ranked",
    "constraints.work_model",
    "constraints.eligibility.pass",
    "constraints.eligibility.not_enough",
    "constraints.eligibility.fail",
    "constraints.hours.pass",
    "constraints.on_call.fail",
    "compensation.preferred",
    "contract.prefer",
    "vehicles.can_use",
    "markets.slices",
    "writing.tone",
)


def parse_scalar(raw: str):
    value = raw.strip()
    if value in {"", "null", "Null", "NULL", "~", '""', "''"}:
        return None
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [part.strip().strip("\"'") for part in inner.split(",") if part.strip()]
    if value[0] == value[-1] and value[0] in {"'", '"'} and len(value) >= 2:
        return value[1:-1]
    return value


def parse_yaml_maps(text: str) -> dict:
    """Parse the profile subset: nested maps, inline lists, and block lists."""
    root: dict = {}
    stack: list[tuple[int, object]] = [(-1, root)]
    logical: list[tuple[int, int, str]] = []
    for line_no, line in enumerate(text.splitlines(), 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))
        logical.append((line_no, indent, line.strip()))

    def container_for(indent: int):
        while len(stack) > 1 and indent <= stack[-1][0]:
            stack.pop()
        return stack[-1][1]

    for index, (line_no, indent, stripped) in enumerate(logical):
        parent = container_for(indent)
        if stripped.startswith("- "):
            if not isinstance(parent, list):
                raise SystemExit(f"line {line_no}: list item outside a list")
            body = stripped[2:].strip()
            key, sep, raw = body.partition(":")
            if sep and key and " " not in key:
                child: dict = {}
                parent.append(child)
                stack.append((indent, child))
                if raw.strip() == "":
                    child[key] = None
                else:
                    child[key] = parse_scalar(raw)
            else:
                parent.append(parse_scalar(body))
            continue

        if not isinstance(parent, dict) or ":" not in stripped:
            raise SystemExit(f"line {line_no}: expected key: value")
        key, _, raw = stripped.partition(":")
        key = key.strip()
        if raw.strip() != "":
            parent[key] = parse_scalar(raw)
            continue
        nxt = logical[index + 1] if index + 1 < len(logical) else None
        if nxt and nxt[1] > indent:
            child_container: object = [] if nxt[2].startswith("- ") else {}
            parent[key] = child_container
            stack.append((indent, child_container))
        else:
            parent[key] = None
    return root


def lookup(data: dict, path: str):
    current = data
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def missing_floor(data: dict) -> bool:
    floors = lookup(data, "compensation.floors")
    if not isinstance(floors, list):
        return True
    for floor in floors:
        if not isinstance(floor, dict):
            continue
        if all(floor.get(key) not in (None, "") for key in ("amount", "currency", "period", "basis")):
            return False
    return True


def problems_in(data: dict) -> list[str]:
    problems: list[str] = []
    if data.get("status") != "ready":
        problems.append("status is not ready")
    for path in REQUIRED:
        value = lookup(data, path)
        if value is None or value == [] or value == "":
            problems.append(f"empty {path}")
    if missing_floor(data):
        problems.append(
            "compensation.floors needs one complete floor: amount, currency, period, basis"
        )
    return problems


def main() -> int:
    profile = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PROFILE
    if not profile.exists():
        print(f"missing {profile} — follow SETUP.md")
        return 1
    found = problems_in(parse_yaml_maps(profile.read_text()))
    if found:
        print("profile is not ready:")
        for item in found:
            print(f"- {item}")
        return 1
    print("profile is ready")
    return 0


if __name__ == "__main__":
    sys.exit(main())

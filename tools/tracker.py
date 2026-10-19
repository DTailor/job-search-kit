#!/usr/bin/env python3
"""Read and write the tracker CSVs.

Column order lives in the HEADER constants below. The committed
`tracker/*.example.csv` files must match them; `tests/test_kit.py` checks that.
Search runs are checked against `search/schema.json` before import.

User-owned columns (`status`, `next_step`, `notes`) are not overwritten once
a row has moved past "Not contacted".
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRACKER = ROOT / "tracker"
SCHEMA_PATH = ROOT / "search" / "schema.json"

STATUSES = (
    "Not contacted",
    "Asked screening Qs",
    "Applied",
    "Interviewing",
    "Assessment",
    "Offer",
    "On hold",
    "Rejected",
    "Withdrawn",
)
DECISIONS = ("Pursue", "Screen first", "Stretch", "Drop")
USER_COLUMNS = ("status", "next_step", "notes")
OPEN_FOR_RESEARCH_UPDATE = {"", "Not contacted"}

ROLES_HEADER = (
    "url", "req_id", "company", "role", "decision", "fit_score",
    "status", "next_step", "notes",
    "location_text", "location_gate", "work_model",
    "vehicle", "vehicle_fit",
    "pay_published", "pay_scope", "pay_verdict", "pay_evidence",
    "hours_oncall", "hours_gate", "pay_gate",
    "why_it_fits", "risk_and_question", "technical_class",
    "posted", "checked", "live_status", "confidence",
    "found_via", "known_company", "slice", "run_file",
)
COMPANIES_HEADER = (
    "company", "type", "in_tracker", "verdict", "why", "hiring_route",
    "pay_intel", "hours_signals", "health", "red_flags", "green_flags",
    "interview", "treatment", "ratings", "ask_first", "entity",
    "confidence", "sources", "checked",
)
CHANNELS_HEADER = (
    "name", "what", "rates", "location", "hours", "process", "risks", "sources", "checked",
)
COVERAGE_HEADER = ("section", "item", "detail", "url", "slice", "checked")
INBOX_HEADER = ("date", "from", "channel", "what", "assessment", "next", "status")
WATCHLIST_HEADER = ("company", "board_url", "why", "last_checked", "notes")

TABLES = {
    "roles": ("roles.csv", ROLES_HEADER, "url"),
    "companies": ("companies.csv", COMPANIES_HEADER, "company"),
    "channels": ("channels.csv", CHANNELS_HEADER, "name"),
    "coverage": ("coverage.csv", COVERAGE_HEADER, None),
    "inbox": ("inbox.csv", INBOX_HEADER, None),
    "watchlist": ("watchlist.csv", WATCHLIST_HEADER, "company"),
}


def table_path(name: str, directory: Path | None = None) -> Path:
    filename, _, _ = TABLES[name]
    return (directory or TRACKER) / filename


def read_rows(path: Path, header: tuple[str, ...]) -> list[dict[str, str]]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != list(header):
            raise SystemExit(f"{path.name}: header is {reader.fieldnames}, expected {list(header)}")
        return [{key: row.get(key, "") or "" for key in header} for row in reader]


def write_rows(path: Path, header: tuple[str, ...], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(header), lineterminator="\n", extrasaction="raise")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in header})


def init(directory: Path | None = None) -> None:
    directory = directory or TRACKER
    directory.mkdir(parents=True, exist_ok=True)
    for name, (filename, header, _) in TABLES.items():
        path = directory / filename
        if not path.exists():
            write_rows(path, header, [])
        else:
            read_rows(path, header)


def write_examples(directory: Path | None = None) -> None:
    directory = directory or TRACKER
    for _, (filename, header, _) in TABLES.items():
        example = directory / filename.replace(".csv", ".example.csv")
        write_rows(example, header, [])


def load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text())


def validate_run(data: dict, schema: dict | None = None, path: str = "") -> list[str]:
    schema = schema or load_schema()
    problems: list[str] = []
    _validate(data, schema, schema, path or "<run>", problems)
    return problems


def _validate(value, schema: dict, root: dict, path: str, problems: list[str]) -> None:
    if "$ref" in schema:
        ref = schema["$ref"]
        if not ref.startswith("#/$defs/"):
            problems.append(f"{path}: unsupported ref {ref}")
            return
        _validate(value, root["$defs"][ref.split("/")[-1]], root, path, problems)
        return
    expected = schema.get("type")
    if isinstance(expected, list):
        if not any(_type_ok(value, item) for item in expected):
            problems.append(f"{path}: expected {' or '.join(expected)}")
        elif value is not None and "enum" not in schema:
            return
    elif expected and not _type_ok(value, expected):
        problems.append(f"{path}: expected {expected}")
        return
    if "enum" in schema and value not in schema["enum"]:
        problems.append(f"{path}: {value!r} is not one of {schema['enum']}")
    if expected == "object" and isinstance(value, dict):
        required = schema.get("required", [])
        for key in required:
            if key not in value:
                problems.append(f"{path}.{key}: missing")
        if schema.get("additionalProperties") is False:
            for key in value:
                if key not in schema.get("properties", {}):
                    problems.append(f"{path}.{key}: not in schema")
        for key, spec in schema.get("properties", {}).items():
            if key in value:
                _validate(value[key], spec, root, f"{path}.{key}", problems)
        if "minLength" in schema and isinstance(value, str) and len(value) < schema["minLength"]:
            problems.append(f"{path}: too short")
    if schema.get("type") == "string" and isinstance(value, str):
        if schema.get("minLength") and len(value) < schema["minLength"]:
            problems.append(f"{path}: too short")
        if schema.get("format") == "date" and len(value) != 10:
            problems.append(f"{path}: expected YYYY-MM-DD")
    if schema.get("type") == "number" and isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            problems.append(f"{path}: below minimum")
        if "maximum" in schema and value > schema["maximum"]:
            problems.append(f"{path}: above maximum")
    if schema.get("type") == "array" and isinstance(value, list) and "items" in schema:
        for index, item in enumerate(value):
            _validate(item, schema["items"], root, f"{path}[{index}]", problems)


def _type_ok(value, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "null":
        return value is None
    return False


def _cell(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, list):
        return "; ".join(_cell(item) for item in value)
    return str(value)


def role_row(role: dict, run: dict, run_file: str) -> dict[str, str]:
    questions = role.get("first_questions") or []
    risk = role.get("fit_gaps") or ""
    if questions:
        risk = (risk + "\nAsk: " + " | ".join(questions)).strip()
    hours = " / ".join(part for part in (role.get("hours_text"), role.get("oncall_text")) if part)
    return {
        "url": role["url"],
        "req_id": _cell(role.get("req_id")),
        "company": role.get("company", ""),
        "role": role.get("title", ""),
        "decision": role.get("decision", ""),
        "fit_score": _cell(role.get("fit_score")),
        "status": "Not contacted",
        "next_step": "",
        "notes": "",
        "location_text": role.get("location_text", ""),
        "location_gate": role.get("location_gate", ""),
        "work_model": role.get("work_model", ""),
        "vehicle": role.get("vehicle_text", ""),
        "vehicle_fit": role.get("vehicle_fit", ""),
        "pay_published": _cell(role.get("pay_published")),
        "pay_scope": role.get("pay_scope", ""),
        "pay_verdict": role.get("pay_verdict", ""),
        "pay_evidence": role.get("pay_note", ""),
        "hours_oncall": hours,
        "hours_gate": role.get("hours_gate", ""),
        "pay_gate": role.get("pay_gate", ""),
        "why_it_fits": role.get("fit_why", ""),
        "risk_and_question": risk,
        "technical_class": role.get("technical_class", ""),
        "posted": _cell(role.get("posted_date")),
        "checked": _cell(role.get("verified_live_on")),
        "live_status": role.get("live_status", ""),
        "confidence": role.get("confidence", ""),
        "found_via": role.get("found_via", ""),
        "known_company": _cell(role.get("known_company")),
        "slice": run.get("slice", ""),
        "run_file": run_file,
    }


def import_run(run_path: Path, directory: Path | None = None) -> str:
    directory = directory or TRACKER
    init(directory)
    run = json.loads(run_path.read_text())
    problems = validate_run(run)
    if problems:
        raise SystemExit("search run does not match search/schema.json:\n- " + "\n- ".join(problems))
    for role in run.get("candidates", []):
        if role.get("decision") not in DECISIONS:
            raise SystemExit(f"{role.get('url')}: decision must be one of {DECISIONS}")
        for gate in ("location_gate", "hours_gate", "pay_gate"):
            if role.get(gate) == "fail" and role.get("decision") != "Drop":
                raise SystemExit(f"{role.get('url')}: {gate} is fail, so decision must be Drop")

    roles_path = table_path("roles", directory)
    rows = read_rows(roles_path, ROLES_HEADER)
    by_url = {row["url"]: row for row in rows}
    added = refreshed = skipped = dropped = 0
    run_file = str(run_path)
    for role in run.get("candidates", []):
        incoming = role_row(role, run, run_file)
        current = by_url.get(incoming["url"])
        if role.get("decision") == "Drop" or any(role.get(gate) == "fail" for gate in ("location_gate", "hours_gate", "pay_gate")):
            _append_coverage(directory, "Dropped", f"{role.get('company')} - {role.get('title')}", role.get("fit_gaps") or role.get("decision", ""), role.get("url", ""), run.get("slice", ""), run.get("searched_on", ""))
            dropped += 1
            continue
        if current is None:
            rows.append(incoming)
            by_url[incoming["url"]] = incoming
            added += 1
            continue
        if current["status"] not in OPEN_FOR_RESEARCH_UPDATE:
            _append_coverage(directory, "Skipped", f"{current['company']} - {current['role']}", f"kept status {current['status']}", current["url"], run.get("slice", ""), run.get("searched_on", ""))
            skipped += 1
            continue
        notes = current["notes"]
        next_step = current["next_step"]
        current.update(incoming)
        current["notes"] = notes
        current["next_step"] = next_step
        current["status"] = "Not contacted"
        refreshed += 1
    write_rows(roles_path, ROLES_HEADER, rows)

    for item in run.get("rejected", []):
        _append_coverage(directory, "Dropped", f"{item.get('company')} - {item.get('title')}", item.get("reason", ""), item.get("url", ""), run.get("slice", ""), run.get("searched_on", ""))
        dropped += 1
    for item in run.get("coverage", []):
        detail = "; ".join(part for part in (item.get("method", ""), item.get("result", "")) if part)
        _append_coverage(directory, "Searched", item.get("source_or_company", ""), detail, "", run.get("slice", ""), run.get("searched_on", ""))
    for item in run.get("needs_browser_check", []):
        _append_coverage(directory, "Needs browser", item.get("url", ""), item.get("why", ""), item.get("url", ""), run.get("slice", ""), run.get("searched_on", ""))
    for channel in run.get("channels", []):
        upsert_row(directory, "channels", {
            "name": channel.get("name", ""),
            "what": channel.get("what", ""),
            "rates": channel.get("rates", ""),
            "location": channel.get("location", ""),
            "hours": channel.get("hours", ""),
            "process": channel.get("process", ""),
            "risks": channel.get("risks", ""),
            "sources": _cell(channel.get("sources")),
            "checked": run.get("searched_on", ""),
        })
    return f"added {added}, refreshed {refreshed}, skipped {skipped}, dropped {dropped}"


def _append_coverage(directory: Path, section: str, item: str, detail: str, url: str, slice_name: str, checked: str) -> None:
    path = table_path("coverage", directory)
    header = COVERAGE_HEADER
    rows = read_rows(path, header)
    rows.append({
        "section": section,
        "item": item,
        "detail": detail,
        "url": url,
        "slice": slice_name,
        "checked": checked,
    })
    write_rows(path, header, rows)


def upsert_row(directory: Path, table: str, row: dict) -> str:
    filename, header, key = TABLES[table]
    if not key:
        raise SystemExit(f"{table} has no key; use append")
    path = directory / filename
    if not path.exists():
        write_rows(path, header, [])
    unknown = set(row) - set(header)
    if unknown:
        raise SystemExit(f"{table}: unknown fields {sorted(unknown)}")
    rows = read_rows(path, header)
    needle = (row.get(key) or "").strip().lower()
    if not needle:
        raise SystemExit(f"{table}: {key} is required")
    for current in rows:
        if current[key].strip().lower() == needle:
            for field in header:
                if field in row and field not in USER_COLUMNS:
                    current[field] = _cell(row[field])
            write_rows(path, header, rows)
            return "updated"
    rows.append({field: _cell(row.get(field, "")) for field in header})
    write_rows(path, header, rows)
    return "added"


def append_row(directory: Path, table: str, row: dict) -> None:
    _, header, key = TABLES[table]
    if key:
        raise SystemExit(f"{table} is keyed; use upsert")
    unknown = set(row) - set(header)
    if unknown:
        raise SystemExit(f"{table}: unknown fields {sorted(unknown)}")
    path = table_path(table, directory)
    if not path.exists():
        write_rows(path, header, [])
    rows = read_rows(path, header)
    rows.append({field: _cell(row.get(field, "")) for field in header})
    write_rows(path, header, rows)


def add_role(directory: Path, url: str, company: str, role: str) -> str:
    init(directory)
    path = table_path("roles", directory)
    rows = read_rows(path, ROLES_HEADER)
    for current in rows:
        if current["url"] == url:
            return "exists"
    blank = {field: "" for field in ROLES_HEADER}
    blank.update({"url": url, "company": company, "role": role, "status": "Not contacted"})
    rows.append(blank)
    write_rows(path, ROLES_HEADER, rows)
    return "added"


def set_status(directory: Path, url: str, status: str, next_step: str | None, notes: str | None) -> None:
    if status not in STATUSES:
        raise SystemExit(f"status must be one of: {', '.join(STATUSES)}")
    path = table_path("roles", directory)
    rows = read_rows(path, ROLES_HEADER)
    for current in rows:
        if current["url"] == url:
            current["status"] = status
            if next_step is not None:
                current["next_step"] = next_step
            if notes is not None:
                current["notes"] = notes
            write_rows(path, ROLES_HEADER, rows)
            return
    raise SystemExit(f"no role with url {url}")


def recheck(directory: Path, payload: dict) -> str:
    init(directory)
    items = payload if isinstance(payload, list) else [payload]
    path = table_path("roles", directory)
    rows = read_rows(path, ROLES_HEADER)
    by_url = {row["url"]: row for row in rows}
    lines = []
    for item in items:
        url = item.get("url") or ""
        current = by_url.get(url)
        if current is None:
            raise SystemExit(f"recheck url is not in the tracker: {url}")
        live = item.get("live_status") or ""
        checked = item.get("checked") or ""
        detail = item.get("detail") or ""
        if current["status"] in OPEN_FOR_RESEARCH_UPDATE:
            current["checked"] = checked or current["checked"]
            current["live_status"] = live or current["live_status"]
            updates = item.get("updates") or {}
            for field, value in updates.items():
                if field in USER_COLUMNS or field not in ROLES_HEADER:
                    raise SystemExit(f"recheck cannot set {field}")
                current[field] = _cell(value)
            if live in {"closed", "unlisted"}:
                current["decision"] = "Drop"
            lines.append(f"updated {url}")
        else:
            lines.append(f"kept {current['status']} for {url}")
        _append_coverage(directory, "Recheck", f"{current['company']} - {current['role']}", f"{live}. {detail}".strip(), url, current.get("slice", ""), checked)
    write_rows(path, ROLES_HEADER, rows)
    return "\n".join(lines)


def _json_arg(path: str) -> dict:
    data = json.loads(Path(path).read_text())
    if not isinstance(data, dict):
        raise SystemExit("expected a JSON object")
    return data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Maintain tracker CSV files")
    parser.add_argument("--dir", type=Path, default=TRACKER)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init")
    sub.add_parser("write-examples")
    validate = sub.add_parser("validate-run")
    validate.add_argument("run")
    import_ = sub.add_parser("import-run")
    import_.add_argument("run")
    upsert = sub.add_parser("upsert")
    upsert.add_argument("table", choices=sorted(TABLES))
    upsert.add_argument("json_file")
    append = sub.add_parser("append")
    append.add_argument("table", choices=("coverage", "inbox"))
    append.add_argument("json_file")
    add = sub.add_parser("add-role")
    add.add_argument("--url", required=True)
    add.add_argument("--company", required=True)
    add.add_argument("--role", required=True)
    status = sub.add_parser("set-status")
    status.add_argument("url")
    status.add_argument("status")
    status.add_argument("--next", default=None)
    status.add_argument("--notes", default=None)
    check = sub.add_parser("recheck")
    check.add_argument("json_file")
    args = parser.parse_args(argv)
    directory = args.dir
    if args.cmd == "init":
        init(directory)
    elif args.cmd == "write-examples":
        write_examples(directory)
    elif args.cmd == "validate-run":
        problems = validate_run(json.loads(Path(args.run).read_text()))
        if problems:
            print("\n".join(problems))
            return 1
        print("valid")
    elif args.cmd == "import-run":
        print(import_run(Path(args.run), directory))
    elif args.cmd == "upsert":
        print(upsert_row(directory, args.table, _json_arg(args.json_file)))
    elif args.cmd == "append":
        append_row(directory, args.table, _json_arg(args.json_file))
        print("appended")
    elif args.cmd == "add-role":
        print(add_role(directory, args.url, args.company, args.role))
    elif args.cmd == "set-status":
        set_status(directory, args.url, args.status, args.next, args.notes)
        print("updated")
    elif args.cmd == "recheck":
        print(recheck(directory, json.loads(Path(args.json_file).read_text())))
    return 0


if __name__ == "__main__":
    sys.exit(main())

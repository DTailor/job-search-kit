#!/usr/bin/env python3
"""Drift checks for the profile parser, search schema, tracker, and command index."""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CHECK = load("check_setup", ROOT / "tools" / "check_setup.py")
TRACKER = load("tracker", ROOT / "tools" / "tracker.py")

READY = """
status: ready
setup_date: 2026-10-19
freshness_days: 14
person:
  name: Ada Example
  address_as: Ada
  location: Lisbon, Portugal
  email:
  public_links: []
target:
  headline: Senior backend engineer
  level: senior
  titles: [Backend engineer, Platform engineer]
  summary: Ships services and APIs.
evidence:
  core: [Python services]
  adjacent: []
  do_not_claim: []
  domains: []
  stories: []
fit:
  ranked:
    - name: Product backend
      why: matches the work
  reject: []
  avoid_companies: []
  stretch_ok: []
constraints:
  work_model: [remote]
  hybrid_locations: []
  relocation: "no"
  eligibility:
    pass: Portugal is named, or worldwide contractor hiring
    not_enough: EU remote with no country list
    fail: a country list that omits Portugal
  hours:
    pass: European daytime
    fail: permanent US hours
  on_call:
    pass: none
    unclear: shared on-call with no schedule
    fail: regular nights or weekends
  start:
  notice:
compensation:
  preferred: either
  floors:
    - engagement: employee
      amount: 4000
      currency: EUR
      period: month
      basis: net
    - engagement: contractor
      amount:
      currency:
      period: hour
      basis: invoice
  fx_note:
  separate: "Keep bases separate."
contract:
  prefer: open-ended
  short_term: only with a stated premium
vehicles:
  can_use: [employment, "limited company"]
  cannot_use: []
  notes: Leave and notice must be written down.
markets:
  slices: [local employers, contract channels]
  seed_companies: []
linkedin:
  advertise_search: false
  headline_locked: true
cv:
  current:
  text:
writing:
  tone: direct
  languages: [English]
  cv: []
  never: []
follow_up:
  quiet_days: 10
  propose_close_days: 60
integrations:
  gmail:
    enabled: false
    account:
  spreadsheet:
    enabled: false
    url:
    is_source_of_truth: false
  linkedin:
    enabled: false
scoring:
  work: 4
  stack: 2
  level: 1
  location: 1
  hours: 1
  pay: 1
  pursue_at: 8
  screen_at: 6
"""


class ProfileTests(unittest.TestCase):
    def test_example_is_not_ready(self):
        data = CHECK.parse_yaml_maps((ROOT / "profile" / "profile.example.yml").read_text())
        self.assertEqual(data["status"], "template")
        self.assertEqual(data["compensation"]["floors"][1]["basis"], "invoice")
        self.assertEqual(data["vehicles"]["can_use"], [])
        problems = CHECK.problems_in(data)
        self.assertIn("status is not ready", problems)
        self.assertTrue(any("vehicles.can_use" in item for item in problems))
        self.assertTrue(any("markets.slices" in item for item in problems))
        self.assertTrue(any("contract.prefer" in item for item in problems))

    def test_ready_profile_passes(self):
        data = CHECK.parse_yaml_maps(READY)
        self.assertEqual(data["fit"]["ranked"][0]["name"], "Product backend")
        self.assertEqual(data["vehicles"]["can_use"], ["employment", "limited company"])
        self.assertEqual(data["markets"]["slices"], ["local employers", "contract channels"])
        self.assertEqual(CHECK.problems_in(data), [])


class TrackerTests(unittest.TestCase):
    def test_example_headers_match_code(self):
        for filename, header, _ in TRACKER.TABLES.values():
            example = ROOT / "tracker" / filename.replace(".csv", ".example.csv")
            rows = TRACKER.read_rows(example, header)
            self.assertEqual(rows, [])

    def test_readme_lists_statuses_and_commands(self):
        readme = (ROOT / "tracker" / "README.md").read_text()
        for status in TRACKER.STATUSES:
            self.assertIn(status, readme)
        for decision in TRACKER.DECISIONS:
            self.assertIn(decision, readme)
        index = (ROOT / "README.md").read_text()
        for path in (ROOT / "commands").glob("*.md"):
            if path.name == "README.md":
                continue
            self.assertIn(path.name, index)
            pointer = ROOT / ".claude" / "commands" / path.name
            self.assertTrue(pointer.exists(), pointer)
            self.assertIn(f"commands/{path.name}", pointer.read_text())

    def test_import_preserves_in_progress_rows(self):
        fixture = ROOT / "tests" / "fixtures" / "min-run.json"
        run = json.loads(fixture.read_text())
        self.assertEqual(TRACKER.validate_run(run), [])
        broken = json.loads(fixture.read_text())
        broken["candidates"][0]["secret"] = "no"
        self.assertTrue(TRACKER.validate_run(broken))
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            first = TRACKER.import_run(fixture, directory)
            self.assertIn("added 1", first)
            roles = TRACKER.read_rows(directory / "roles.csv", TRACKER.ROLES_HEADER)
            self.assertEqual(roles[0]["status"], "Not contacted")
            self.assertEqual(roles[0]["decision"], "Screen first")
            self.assertIn("approved band", roles[0]["risk_and_question"])
            TRACKER.set_status(directory, roles[0]["url"], "Applied", "wait", "sent")
            second = TRACKER.import_run(fixture, directory)
            self.assertIn("skipped 1", second)
            again = TRACKER.read_rows(directory / "roles.csv", TRACKER.ROLES_HEADER)
            self.assertEqual(len(again), 1)
            self.assertEqual(again[0]["status"], "Applied")
            self.assertEqual(again[0]["notes"], "sent")
            coverage = TRACKER.read_rows(directory / "coverage.csv", TRACKER.COVERAGE_HEADER)
            self.assertTrue(any(row["section"] == "Dropped" for row in coverage))
            self.assertTrue(any(row["section"] == "Searched" for row in coverage))
            channels = TRACKER.read_rows(directory / "channels.csv", TRACKER.CHANNELS_HEADER)
            self.assertEqual(channels[0]["name"], "Example board")

    def test_recheck_does_not_drop_an_application(self):
        fixture = ROOT / "tests" / "fixtures" / "min-run.json"
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            TRACKER.import_run(fixture, directory)
            url = "https://example.com/jobs/1"
            TRACKER.recheck(directory, {
                "url": url,
                "live_status": "closed",
                "checked": "2026-10-20",
                "detail": "posting gone",
            })
            row = TRACKER.read_rows(directory / "roles.csv", TRACKER.ROLES_HEADER)[0]
            self.assertEqual(row["decision"], "Drop")
            self.assertEqual(row["status"], "Not contacted")
            TRACKER.set_status(directory, url, "Applied", None, None)
            # Put it back to a live research row first by editing decision through a fresh not-contacted path:
            rows = TRACKER.read_rows(directory / "roles.csv", TRACKER.ROLES_HEADER)
            rows[0]["decision"] = "Screen first"
            rows[0]["status"] = "Applied"
            TRACKER.write_rows(directory / "roles.csv", TRACKER.ROLES_HEADER, rows)
            TRACKER.recheck(directory, {
                "url": url,
                "live_status": "closed",
                "checked": "2026-10-21",
                "detail": "closed after apply",
            })
            row = TRACKER.read_rows(directory / "roles.csv", TRACKER.ROLES_HEADER)[0]
            self.assertEqual(row["status"], "Applied")
            self.assertEqual(row["decision"], "Screen first")


if __name__ == "__main__":
    unittest.main()

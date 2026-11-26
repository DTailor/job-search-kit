"""Offline tests for the census classifiers (no network). Run: python3 -m pytest tools/test_ats_census.py"""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ats_census as a


CONFIG = {"skills": [r"\\bpython\\b", r"\\bdjango\\b"], "home": ["romania", "bucharest", "cluj"],
          "region": ["europe", r"\\bemea\\b", r"\\beu\\b", "european", r"\\bcet\\b"]}


def run():
    d = tempfile.mkdtemp()
    (Path(d) / "census-config.json").write_text(json.dumps(CONFIG))  # the run-local file overrides any workspace profile
    return a.Run(d)


def test_slugs_from_mixed_text():
    text = ("https://jobs.ashbyhq.com/Fundamental/1a11 https://job-boards.eu.greenhouse.io/justmarkets/jobs/5 "
            "https://boards.greenhouse.io/embed/job_board?for=acme https://jobs.eu.lever.co/blackshark/x "
            "https://apply.workable.com/aurora-3/j/E https://clera.jobs.personio.de/job/1 https://www.recruitee.com/")
    got = a.slugs_in(text)
    assert ("ashby", "Fundamental") in got            # case kept where the API is case-sensitive
    assert ("greenhouse", "justmarkets") in got and ("greenhouse", "acme") in got
    assert ("lever_eu", "blackshark") in got and ("lever", "blackshark") not in got
    assert ("workable", "aurora-3") in got and ("personio", "clera") in got
    assert not any(s == "www" for _, s in got)


def test_label_class():
    R = run()
    assert a.label_class(R, ["Bulgaria; Poland; Romania"], "") == "home"
    assert a.label_class(R, ["Europe", "Denmark"], "Remote") == "region"
    assert a.label_class(R, ["Remote", "Poland"], "Remote") == "eu_remote"
    assert a.label_class(R, ["Berlin"], "") == "eu_place"
    assert a.label_class(R, ["Kolkata, WB, in"], "") == "non_eu"
    assert a.label_class(R, ["Remote"], "") == "remote"


def test_geo_uses_body_evidence():
    R = run()
    us = dict(label="remote", locs=["Remote"], desc="Great team. You must be authorized to work in the United States. Python APIs.")
    assert a.geo(R, us)[0] == "elsewhere"
    eu = dict(label="remote", locs=["Remote"], desc="We are fully remote and hire candidates anywhere in Europe. Python APIs.")
    assert a.geo(R, eu)[0] == "region_in_body"
    listed = dict(label="eu_remote", locs=["Remote", "Poland"], desc="Python services. B2B contract.")
    assert a.geo(R, listed)[0] == "countries_only"   # labelled bucket, never silently treated as eligible
    office = dict(label="eu_place", locs=["Berlin"], desc="Python. Hybrid, 3 days in the office.")
    assert a.geo(R, office)[0] == "onsite_or_place"


def test_contract_wording_ignores_b2b_saas():
    assert not a.B2B.search("We are a high-performing B2B SaaS company with contractors as customers.")
    assert a.B2B.search("Compensation: 9,600 - 12,000 USD per month (B2B)")
    assert a.B2B.search("You will be engaged as an independent contractor.")


def test_norm_url_keeps_job_id_query():
    # Job-id query parameters distinguish postings on a shared careers page.
    a1 = a.norm_url("https://careers.example.com/?gh_jid=4965522101")
    a2 = a.norm_url("https://careers.example.com/?gh_jid=4950630101&utm_source=x")
    assert a1 != a2 and a2 == "https://careers.example.com?gh_jid=4950630101"
    assert a.norm_url("https://jobs.ashbyhq.com/Acme/1a11/?utm_source=li#apply") == "https://jobs.ashbyhq.com/acme/1a11"
    assert a.norm_url("https://www.example.com/careers/?gh_jid=4665861006.") == "https://www.example.com/careers?gh_jid=4665861006"

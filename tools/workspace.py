"""Locate the workspace and load its settings (workspace.json). Stdlib only.

Every kit tool imports this instead of hard-coding a person, a spreadsheet, a
folder name or a time zone. The workspace root is the nearest ancestor of the
current directory (or of this file) that contains workspace.json; override with
the JOB_HUNT_WORKSPACE environment variable.
"""
import json
import os
from functools import lru_cache
from pathlib import Path

CONFIG_NAME = 'workspace.json'
TAB_KEYS = ('all_roles', 'queue', 'audit', 'pipeline', 'shortlist')


def find_root(start=None):
    env = os.environ.get('JOB_HUNT_WORKSPACE')
    if env:
        return Path(env).resolve()
    for base in [Path(start or Path.cwd()).resolve(), Path(__file__).resolve().parent]:
        for p in [base, *base.parents]:
            if (p / CONFIG_NAME).is_file():
                return p
    raise FileNotFoundError(f'No {CONFIG_NAME} found; run tools/new_workspace.py or set JOB_HUNT_WORKSPACE')


@lru_cache(maxsize=None)
def load(root=None):
    root = Path(root) if root else find_root()
    cfg = json.loads((root / CONFIG_NAME).read_text())
    cfg['_root'] = str(root)
    validate(cfg)
    return cfg


def validate(cfg):
    missing = [k for k in ('schema_version', 'person', 'tracker', 'paths') if k not in cfg]
    assert not missing, f'workspace.json missing {missing}'
    for k in ('name', 'email', 'timezone'):
        assert cfg['person'].get(k), f'person.{k} required'
    tabs = cfg['tracker'].get('tabs', {})
    for k in TAB_KEYS:
        assert k in tabs and 'title' in tabs[k] and 'sheet_id' in tabs[k], f'tracker.tabs.{k} needs title and sheet_id'
    for k in ('data', 'pool', 'status', 'dashboard', 'automation', 'tracker_base'):
        assert k in cfg['paths'], f'paths.{k} required'
    return cfg


def root():
    return Path(load()['_root'])


def path(key):
    """Absolute path for a configured paths.<key> entry."""
    return root() / load()['paths'][key]


def tab(key):
    """{'title', 'sheet_id'} for a tracker tab role (all_roles, queue, audit, pipeline, shortlist)."""
    return load()['tracker']['tabs'][key]


def tab_title(key):
    return tab(key)['title']


def sheet_url():
    return f"https://docs.google.com/spreadsheets/d/{load()['tracker']['spreadsheet_id']}/edit"


def person():
    return load()['person']


def timezone():
    """IANA time zone of the person (used for day boundaries and local timestamps)."""
    return person()['timezone']


def header_row(key):
    """1-based header row of a tab: tracker.tabs.<key>.header_row, else tracker.header_row."""
    return int(tab(key).get('header_row', load()['tracker'].get('header_row', 1)))


DEFAULT_GATES = {'all_roles_columns': ['location', 'hours', 'pay'],
                 'dashboard': {'Location': 'location', 'Pay': 'pay', 'Hours': 'hours', 'Term': 'term'}}


def gates():
    """Gate keys: which pool gates fill All roles F:H, and dashboard label -> gate key."""
    return {**DEFAULT_GATES, **load().get('gates', {})}


def browser_cli():
    return ((load().get('accounts') or {}).get('browser') or {}).get('path')


def check_option(key, default=None):
    """Optional per-workspace regression settings under checks.<key>."""
    return (load().get('checks') or {}).get(key, default)

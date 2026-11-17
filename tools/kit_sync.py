"""Copy kit-managed files (declared in kit.json) into a workspace. Stdlib only.

  python3 tools/kit_sync.py WORKSPACE [--kit KIT] [--apply] [--diff-lines N]

Dry run by default: lists every managed file as same / new / changed (with a
unified diff excerpt) and every skipped protected path. --apply writes new and
changed files. Never deletes, and never touches workspace.json, profile/, any
configured data path (paths.* except the dashboard code folder) or the dashboard's
data/ folder, whatever the manifest says.
"""
import argparse
import difflib
import fnmatch
import json
import shutil
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]


def manifest(kit):
    return json.loads((Path(kit) / 'kit.json').read_text())


def workspace_paths(target):
    cfg_file = Path(target) / 'workspace.json'
    return json.loads(cfg_file.read_text()).get('paths', {}) if cfg_file.is_file() else {}


def protected(target, man):
    """Absolute paths kit_sync must never write."""
    target = Path(target).resolve()
    paths = workspace_paths(target)
    keep = [target / p for p in man.get('never_touch', [])]
    keep += [target / v for k, v in paths.items() if k != 'dashboard' and v]
    if paths.get('dashboard'):
        keep.append(target / paths['dashboard'] / 'data')
    return [p.resolve() for p in keep]


def ignored(rel, man):
    return any(fnmatch.fnmatch(part, pat) for part in Path(rel).parts for pat in man.get('ignore', []))


def plan(kit, target, man=None):
    """Yield (src, dest, status) for every managed file; status: same/new/changed/protected."""
    kit, target = Path(kit).resolve(), Path(target).resolve()
    man = man or manifest(kit)
    paths = workspace_paths(target)
    guard = protected(target, man)
    for entry in man['managed']:
        src = kit / entry['src']
        if not src.exists():
            continue
        dest_root = target / (paths.get(entry['dest_path'], entry['dest_path']) if 'dest_path' in entry else entry['dest'])
        files = [(src, dest_root)] if src.is_file() else [
            (f, dest_root / f.relative_to(src)) for f in sorted(src.rglob('*')) if f.is_file()]
        for f, dest in files:
            rel = f.relative_to(src) if src.is_dir() else Path(f.name)
            if ignored(rel, man):
                continue
            if 'include' in entry and not any(fnmatch.fnmatch(str(rel), p) for p in entry['include']):
                continue
            if any(fnmatch.fnmatch(str(rel), p) for p in entry.get('exclude', [])):
                continue
            d = dest.resolve()
            if any(d == p or p in d.parents for p in guard):
                yield f, dest, 'protected'
            elif not dest.exists():
                yield f, dest, 'new'
            else:
                yield f, dest, 'same' if f.read_bytes() == dest.read_bytes() else 'changed'


def diff(src, dest, limit):
    try:
        a, b = dest.read_text().splitlines(), src.read_text().splitlines()
    except UnicodeDecodeError:
        return ['  (binary file differs)']
    lines = list(difflib.unified_diff(a, b, str(dest), str(src), lineterm='', n=1))
    return lines[:limit] + ([f'  ... {len(lines) - limit} more diff lines'] if len(lines) > limit else [])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('workspace')
    ap.add_argument('--kit', default=str(KIT))
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--diff-lines', type=int, default=40)
    args = ap.parse_args(argv)
    target = Path(args.workspace).resolve()
    if not (Path(args.kit) / 'kit.json').is_file():
        sys.exit(f'{args.kit}: kit.json not found')
    counts = {}
    for src, dest, status in plan(args.kit, target):
        counts[status] = counts.get(status, 0) + 1
        rel = dest.relative_to(target) if dest.is_relative_to(target) else dest
        if status != 'same':
            print(f'{status:9} {rel}')
        if status == 'changed' and not args.apply:
            print('\n'.join(diff(src, dest, args.diff_lines)))
        if args.apply and status in ('new', 'changed'):
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
    mode = 'applied' if args.apply else 'dry run (use --apply to write)'
    print(json.dumps(dict(mode=mode, workspace=str(target), **counts)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

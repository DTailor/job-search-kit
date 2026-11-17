"""Find clutter in a workspace (or the kit) and clean it up reversibly. Stdlib only.

  python3 tools/cleanup_audit.py [ROOT]                 # report only
  python3 tools/cleanup_audit.py [ROOT] --apply         # clean
      [--min-mb 2] [--keep-days 2] [--skip PATH ...]

Report sections:
  caches        __pycache__, .pytest_cache, *.pyc, .DS_Store        -> deleted on --apply
  empty_dirs    empty folders                                         -> deleted on --apply
  duplicates    identical files >= 1 MB (same SHA-256)               -> report only
  large_raw     data files >= --min-mb (.json/.html/.raw/.body/.txt/.csv/.xml) older than
                --keep-days whose path (or name) is not referenced by any text file outside
                its own folder                                        -> gzipped in place on --apply
                (file.json -> file.json.gz; restore with `gunzip FILE.gz`)
  unused_defs   top-level Python functions in tools/ and dashboard/ never referenced
                anywhere else in the scanned tree                     -> report only
  unref_code    .py/.mjs files in tools/ and dashboard/ not referenced by any other file
                (excluding tests and entry points listed in kit.json "entry_points") -> report only

Every applied action is recorded in <ROOT>/history/cleanup-<date>.json so it can be
reviewed or reversed. Never touches workspace.json, profile/, history/, .git/ or
files referenced from text files. Never deletes data: large files are only compressed.
"""
import argparse
import ast
import datetime as dt
import gzip
import hashlib
import json
import os
import re
import shutil
import sys
import time
from pathlib import Path

CACHE_DIRS = {'__pycache__', '.pytest_cache'}
CACHE_FILES = {'.DS_Store'}
DATA_EXT = {'.json', '.html', '.htm', '.raw', '.body', '.txt', '.csv', '.xml', '.jsonl'}
TEXT_EXT = {'.md', '.json', '.jsonl', '.py', '.mjs', '.js', '.html', '.txt', '.csv', '.plist', '.yaml', '.yml', '.toml'}
PROTECTED = {'workspace.json', 'profile', 'history', '.git', 'node_modules'}
CODE_DIRS = ('tools', 'dashboard', 'product-poc')


def walk(root, skip):
    for dirpath, dirnames, filenames in os.walk(root):
        rel = Path(dirpath).relative_to(root)
        if rel.parts and (rel.parts[0] in PROTECTED or any(str(rel).startswith(s) for s in skip)):
            dirnames[:] = []
            continue
        yield Path(dirpath), dirnames, filenames


CITE_EXT = {'.md', '.py', '.mjs', '.js', '.plist', '.yaml', '.yml', '.toml', '.jsonl', '.json'}
RAW_DIRS = {'raw', 'boards', 'captures', 'work', 'fanout', 'portfolios'}


def text_corpus(root, skip, json_kb=512):
    """Files that can cite other files: notes, code and small JSON. Raw downloads
    (html/txt/csv, files under raw-like folders, big JSON) are data, not citations."""
    corpus = {}
    for d, _, files in walk(root, skip):
        if RAW_DIRS & set(d.relative_to(root).parts):
            continue
        for f in files:
            p = d / f
            if p.suffix not in CITE_EXT:
                continue
            if p.suffix == '.json' and p.stat().st_size > json_kb * 1024:
                continue
            try:
                corpus[p] = p.read_text(errors='ignore')
            except OSError:
                pass
    for extra in ('profile', 'AGENTS.md', 'workspace.json'):
        q = root / extra
        for p in ([q] if q.is_file() else q.rglob('*') if q.is_dir() else []):
            if p.is_file() and p.suffix in CITE_EXT | {'.md'}:
                corpus[p] = p.read_text(errors='ignore')
    return corpus


TOKEN = re.compile(r'[\w@%+~.,()\-]+(?:/[\w@%+~.,()\-]+)*')
GENERIC = re.compile(r'(raw|data|jobs|index|page|out|body|response)\.\w+')


def citation_index(corpus):
    """One pass over all text: cited path tokens and, per cited file name, the citing folders."""
    paths, names = set(), {}
    for p, text in corpus.items():
        for tok in set(TOKEN.findall(text)):
            if '.' not in tok:
                continue
            tok = tok.strip('.,()')
            paths.add(tok)
            names.setdefault(tok.rsplit('/', 1)[-1], set()).add(p.parent)
    return paths, names


def referenced(path, root, index):
    paths, names = index
    rel = str(path.relative_to(root))
    if rel in paths or any(t.endswith('/' + rel) or (('/' in t) and rel.endswith(t.lstrip('./'))) for t in ()):
        return True
    parts = rel.split('/')
    # Any cited token that equals a trailing part of the relative path (e.g. "raw/x.json", "../raw/x.json").
    for i in range(1, len(parts)):
        if '/'.join(parts[i:]) in paths:
            return True
    citing = names.get(path.name, set())
    if not citing:
        return False
    if GENERIC.fullmatch(path.name):
        return any(c != path.parent for c in citing) and False
    return any(c != path.parent for c in citing) or len(citing) > 1


def audit(root, min_mb=2.0, keep_days=2, skip=()):
    root = Path(root).resolve()
    skip = tuple(skip)
    caches, empty, big, by_hash, code = [], [], [], {}, []
    cutoff = time.time() - keep_days * 86400
    for d, dirnames, files in walk(root, skip):
        for name in list(dirnames):
            if name in CACHE_DIRS:
                caches.append(d / name)
                dirnames.remove(name)
        for f in files:
            p = d / f
            if f in CACHE_FILES or p.suffix == '.pyc':
                caches.append(p)
                continue
            st = p.stat()
            if st.st_size >= 1024 * 1024:
                by_hash.setdefault(st.st_size, []).append(p)
            if p.suffix in DATA_EXT and st.st_size >= min_mb * 1024 * 1024 and st.st_mtime < cutoff:
                big.append(p)
            if p.suffix in ('.py', '.mjs') and p.relative_to(root).parts[0] in CODE_DIRS:
                code.append(p)
        if d != root and not dirnames and not files and d.name not in CACHE_DIRS:
            empty.append(d)
    corpus = text_corpus(root, skip)
    index = citation_index(corpus)
    large_raw = [p for p in big if not referenced(p, root, index)]
    dups = []
    for same_size in (ps for ps in by_hash.values() if len(ps) > 1):
        hashed = {}
        for p in same_size:
            hashed.setdefault(hashlib.sha256(p.read_bytes()).hexdigest(), []).append(p)
        dups += [[str(p.relative_to(root)) for p in ps] for ps in hashed.values() if len(ps) > 1]

    entry = set()
    kit = root / 'kit.json'
    if kit.is_file():
        entry = set(json.loads(kit.read_text()).get('entry_points', []))
    import collections
    words = collections.Counter()
    per_file = {}
    for q, t in corpus.items():
        c = collections.Counter(re.findall(r'[A-Za-z_][\w-]*', t))
        per_file[q] = c
        words.update(c)
    unref_code = []
    for p in code:
        rel = str(p.relative_to(root))
        if p.name.startswith('test_') or rel in entry:
            continue
        own = per_file.get(p, collections.Counter())
        if words[p.stem] - own[p.stem] <= 0:
            unref_code.append(rel)
    unused_defs = []
    for p in code:
        if p.suffix != '.py':
            continue
        try:
            tree = ast.parse(p.read_text(errors='ignore'))
        except SyntaxError:
            continue
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not node.name.startswith('__') and node.name != 'main':
                if words[node.name] <= 1:
                    unused_defs.append(f'{p.relative_to(root)}:{node.lineno} {node.name}')

    mb = lambda ps: round(sum(p.stat().st_size for p in ps) / 1048576, 1)  # noqa: E731
    return dict(root=str(root),
                caches=[str(p.relative_to(root)) for p in caches],
                empty_dirs=[str(p.relative_to(root)) for p in empty],
                duplicates=dups,
                large_raw=dict(count=len(large_raw), mb=mb(large_raw), files=[str(p.relative_to(root)) for p in large_raw]),
                large_referenced_kept=dict(count=len(big) - len(large_raw), mb=round(mb(big) - mb(large_raw), 1)),
                unused_defs=unused_defs,
                unref_code=sorted(unref_code))


def apply(report):
    root = Path(report['root'])
    log = dict(applied_at=dt.datetime.now().astimezone().isoformat(timespec='seconds'), deleted=[], gzipped=[], removed_empty=[])
    for rel in report['caches']:
        p = root / rel
        if p.is_dir():
            shutil.rmtree(p, ignore_errors=True)
        elif p.exists():
            p.unlink()
        log['deleted'].append(rel)
    for rel in report['large_raw']['files']:
        p = root / rel
        gz = p.with_name(p.name + '.gz')
        with p.open('rb') as src, gzip.open(gz, 'wb', compresslevel=9) as dst:
            shutil.copyfileobj(src, dst)
        os.utime(gz, (p.stat().st_atime, p.stat().st_mtime))
        log['gzipped'].append(dict(file=rel, before=p.stat().st_size, after=gz.stat().st_size))
        p.unlink()
    for rel in sorted(report['empty_dirs'], key=len, reverse=True):
        p = root / rel
        try:
            p.rmdir()
            log['removed_empty'].append(rel)
        except OSError:
            pass
    hist = root / 'history'
    hist.mkdir(exist_ok=True)
    out = hist / f"cleanup-{dt.date.today().isoformat()}.json"
    prev = json.loads(out.read_text()) if out.exists() else []
    out.write_text(json.dumps((prev if isinstance(prev, list) else [prev]) + [log], indent=1) + '\n')
    saved = sum(g['before'] - g['after'] for g in log['gzipped'])
    return dict(log=str(out.relative_to(root)), deleted=len(log['deleted']), gzipped=len(log['gzipped']),
                saved_mb=round(saved / 1048576, 1), removed_empty=len(log['removed_empty']))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('root', nargs='?', default='.')
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--min-mb', type=float, default=2.0)
    ap.add_argument('--keep-days', type=float, default=2)
    ap.add_argument('--skip', nargs='*', default=[])
    ap.add_argument('--full', action='store_true', help='print every file name, not just counts')
    a = ap.parse_args(argv)
    rep = audit(a.root, a.min_mb, a.keep_days, a.skip)
    shown = rep if a.full else {**rep, 'large_raw': {k: v for k, v in rep['large_raw'].items() if k != 'files'},
                                'caches': len(rep['caches'])}
    print(json.dumps(shown, indent=1, ensure_ascii=False))
    if a.apply:
        print(json.dumps(apply(rep), indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main())

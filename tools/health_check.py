"""RedstoneExMachina health check: health_check.py <game dir> [--online].

Checks mod tracking files and hashes, config syntax, shared defaults, resource pack formats,
duplicate in-world hotkeys and log errors. --online also asks Modrinth for newer 26.2 versions.
"""

import collections
import glob
import hashlib
import json
import os
import re
import sys
import tomllib
import urllib.request
import zipfile

GAME = sys.argv[1]
ONLINE = '--online' in sys.argv
RESOURCE_FORMAT = 88
problems = []


def report(section, items):
    print(f'\n== {section}: {len(items)} issue(s)')
    for item in items:
        print('  -', item)
    problems.extend(f'{section}: {i}' for i in items)


def sha512(path):
    with open(path, 'rb') as f:
        return hashlib.sha512(f.read()).hexdigest()


def check_tracked(folder):
    """Every file has a Prism .pw.toml whose filename and hash match, and no toml is orphaned."""
    files = {f for f in os.listdir(folder)
             if os.path.isfile(os.path.join(folder, f)) and not f.endswith(('.txt', '.pw.toml'))}
    issues, tracked = [], set()
    # Prism keeps tracking files in .index; the Fabulously Optimized shader file sits next to the pack
    tomls = glob.glob(os.path.join(folder, '.index', '*.pw.toml')) + glob.glob(os.path.join(folder, '*.pw.toml'))
    for toml_path in tomls:
        meta = tomllib.load(open(toml_path, 'rb'))
        name = meta['filename']
        tracked.add(name)
        if name not in files:
            issues.append(f'{os.path.basename(toml_path)} points to missing {name}')
        elif meta['download'].get('hash-format') == 'sha512' and sha512(os.path.join(folder, name)) != meta['download']['hash']:
            issues.append(f'{name}: hash differs from tracking file')
    issues += [f'{f}: not tracked by Prism (manual updates)' for f in sorted(files - tracked)]
    return issues


def mod_ids(folder):
    ids = collections.defaultdict(list)
    for jar in glob.glob(os.path.join(folder, '*.jar')):
        try:
            meta = json.loads(zipfile.ZipFile(jar).read('fabric.mod.json'), strict=False)
            ids[meta['id']].append(os.path.basename(jar))
        except (KeyError, ValueError) as e:
            ids[f'?{os.path.basename(jar)}'].append(str(e))
    return ids


def parse_configs(folder):
    issues = []
    for path in glob.glob(os.path.join(folder, '**', '*'), recursive=True):
        try:
            if path.endswith('.json'):
                json.load(open(path, encoding='utf-8'))
            elif path.endswith('.toml'):
                tomllib.load(open(path, 'rb'))
        except Exception as e:
            issues.append(f'{os.path.relpath(path, GAME)}: {type(e).__name__}: {e}'.splitlines()[0][:160])
    return issues


def json_subset_diffs(default, active, trail=''):
    """Values set in the shared default that the active config does not match."""
    if isinstance(default, dict) and isinstance(active, dict):
        for k, v in default.items():
            yield from json_subset_diffs(v, active.get(k), f'{trail}.{k}' if trail else k)
    elif default != active:
        yield trail


def defaults_parity():
    """Shared defaults whose values the active config does not match. Many are personal settings."""
    base = os.path.join(GAME, 'config', 'modpack_defaults')
    out = []
    for path in glob.glob(os.path.join(base, '**', '*'), recursive=True):
        if not os.path.isfile(path):
            continue
        rel = os.path.relpath(path, base)
        active = os.path.join(GAME, rel)
        if not os.path.exists(active):
            out.append(f'{rel}: no active copy')
        elif path.endswith('.json'):
            diffs = list(json_subset_diffs(json.load(open(path)), json.load(open(active))))
            if diffs:
                out.append(f'{rel}: {len(diffs)} value(s) differ, e.g. {", ".join(diffs[:3])}')
        elif open(path, 'rb').read() != open(active, 'rb').read():
            out.append(f'{rel}: differs from active')
    return out


def resource_formats():
    issues = []
    for zip_path in glob.glob(os.path.join(GAME, 'resourcepacks', '*.zip')):
        meta = json.loads(zipfile.ZipFile(zip_path).read('pack.mcmeta'), strict=False)['pack']
        lo, hi = meta.get('min_format'), meta.get('max_format')
        if lo is None:
            lo = hi = meta.get('pack_format')
        lo, hi = (v[0] if isinstance(v, list) else v for v in (lo, hi))
        if not (lo <= RESOURCE_FORMAT <= hi):
            issues.append(f'{os.path.basename(zip_path)}: formats {lo}..{hi}, game uses {RESOURCE_FORMAT}')
    enabled = [l for l in open(os.path.join(GAME, 'options.txt')) if l.startswith('resourcePacks:')]
    for name in json.loads(enabled[0].split(':', 1)[1]):
        if name.startswith('file/') and not os.path.exists(os.path.join(GAME, 'resourcepacks', name[5:])):
            issues.append(f'enabled pack missing: {name}')
    return issues


def hotkey_duplicates():
    """In-world single keys bound twice (vanilla-style bindings and MaLiLib single keys)."""
    binds = collections.defaultdict(list)
    for line in open(os.path.join(GAME, 'options.txt')):
        m = re.match(r'key_(.+):key\.keyboard\.(.+)', line.strip())
        if m and m.group(2) != 'unknown' and '.debug.' not in m.group(1) and '.jei.' not in m.group(1):
            binds[m.group(2).upper().replace('.', '_')].append(m.group(1))
    gui_only = {'itemscroller'}
    for name in ('minihud', 'litematica', 'tweakeroo', 'tweakermore', 'techutils', 'malilib', 'itemscroller'):
        path = os.path.join(GAME, 'config', f'{name}.json')
        if name in gui_only or not os.path.exists(path):
            continue

        def walk(node, trail):
            if isinstance(node, dict):
                if isinstance(node.get('keys'), str):
                    if node['keys'] and ',' not in node['keys'] and not node['keys'].startswith(('BUTTON', 'LEFT_', 'RIGHT_')):
                        binds[node['keys']].append(f'{name}.{trail}')
                    return
                for k, v in node.items():
                    walk(v, k)
        walk(json.load(open(path)), '')
    return [f'{key}: {", ".join(sorted(set(who)))}' for key, who in sorted(binds.items()) if len(set(who)) > 1]


def log_errors():
    counts = collections.Counter()
    for line in open(os.path.join(GAME, 'logs', 'latest.log'), errors='replace'):
        if '/ERROR]' in line:
            counts[re.sub(r'^\[[\d:]+\] ', '', line.strip())[:150]] += 1
    return [f'{n}x {msg}' for msg, n in counts.most_common(12)]


def crash_reports(days=7):
    import time
    out = collections.Counter()
    for path in glob.glob(os.path.join(GAME, 'crash-reports', '*.txt')):
        if time.time() - os.path.getmtime(path) < days * 86400:
            text = open(path, errors='replace').read()
            desc = re.search(r'^Description: (.*)$', text, re.M)
            culprit = 'Baritone cache threads' if 'baritone.cache.CachedWorld' in text else 'see report'
            out[f'{desc.group(1) if desc else "?"} ({culprit})'] += 1
    return [f'{n}x {k}' for k, n in out.items()]


def modrinth_updates(folder):
    hashes = {sha512(p): os.path.basename(p) for p in glob.glob(os.path.join(folder, '*.jar'))}
    body = json.dumps({'hashes': list(hashes), 'algorithm': 'sha512', 'loaders': ['fabric'],
                       'game_versions': ['26.2']}).encode()
    req = urllib.request.Request('https://api.modrinth.com/v2/version_files/update', body,
                                 {'Content-Type': 'application/json', 'User-Agent': 'RedstoneExMachina-health'})
    latest = json.load(urllib.request.urlopen(req))
    out = []
    for h, name in hashes.items():
        v = latest.get(h)
        if v and not any(f['hashes']['sha512'] == h for f in v['files']):
            out.append(f'{name} -> {v["version_number"]} ({v["date_published"][:10]})')
    return sorted(out)


def main():
    mods = os.path.join(GAME, 'mods')
    report('Mod tracking', check_tracked(mods))
    report('Duplicate mod ids', [f'{k}: {v}' for k, v in mod_ids(mods).items() if len(v) > 1 or k.startswith('?')])
    report('Resource pack tracking', check_tracked(os.path.join(GAME, 'resourcepacks')))
    report('Shader pack tracking', check_tracked(os.path.join(GAME, 'shaderpacks')))
    report('Config syntax', parse_configs(os.path.join(GAME, 'config')))
    report('Resource pack formats', resource_formats())
    report('Duplicate in-world keys', hotkey_duplicates())
    report('Shared defaults differing from active (review)', defaults_parity())
    report('Latest log errors (review)', log_errors())
    report('Crash reports, last 7 days', crash_reports())
    if ONLINE:
        report('Newer Modrinth versions', modrinth_updates(mods))
    print(f'\n{len(problems)} item(s) total')


if __name__ == '__main__':
    main()

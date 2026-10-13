"""Update Prism-tracked mods and packs to their newest Modrinth release for the pack's Minecraft version.

usage: update_mods.py <game dir> <backup dir> <[folder/]tracking name>...
  e.g. polytone (mods/.index/polytone.pw.toml), resourcepacks/translations-for-sodium

Replaced archives and tracking files are moved into <backup dir>. Every download is checked against its SHA512.
"""

import hashlib
import json
import os
import shutil
import sys
import tomllib
import urllib.parse
import urllib.request

MINECRAFT = '26.2'
HEADERS = {'User-Agent': 'RedstoneExMachina-update'}
LOADERS = {'mods': 'fabric', 'resourcepacks': 'minecraft', 'shaderpacks': 'iris'}


def newer_version(project_id, installed_id, loader):
    """Newest version published after the installed one; a release wins over betas. None if up to date."""
    query = urllib.parse.urlencode({'game_versions': json.dumps([MINECRAFT]), 'loaders': json.dumps([loader])})
    url = f'https://api.modrinth.com/v2/project/{project_id}/version?{query}'
    versions = json.load(urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS)))
    installed = next((v for v in versions if v['id'] == installed_id), None)
    newer = [v for v in versions if installed is None or v['date_published'] > installed['date_published']]
    return next((v for v in newer if v['version_type'] == 'release'), newer[0] if newer else None)


def tracking_toml(name, version, file, loader):
    q = lambda s: "'" + s.replace("'", "\\'") + "'"
    deps = ''.join(f"\n[[x-prismlauncher-dependencies]]\naddonId = {q(d['project_id'])}\n"
                   f"type = {q(d['dependency_type'].upper())}\n" for d in version['dependencies'] if d['project_id'])
    return f"""filename = {q(file['filename'])}
name = {q(name)}
side = ''
x-prismlauncher-loaders = [ {q(loader)} ]
x-prismlauncher-mc-versions = [ {q(MINECRAFT)} ]
x-prismlauncher-release-type = {q(version['version_type'])}
x-prismlauncher-version-number = {q(version['version_number'])}

[download]
hash = {q(file['hashes']['sha512'])}
hash-format = 'sha512'
mode = 'url'
url = {q(file['url'])}

[update.modrinth]
mod-id = {q(version['project_id'])}
version = {q(version['id'])}
{deps}"""


def update(game, backup, target):
    folder, slug = target.split('/') if '/' in target else ('mods', target)
    root = os.path.join(game, folder)
    toml_path = os.path.join(root, '.index', f'{slug}.pw.toml')
    if not os.path.exists(toml_path):  # shader tracking files sit next to the pack
        toml_path = os.path.join(root, f'{slug}.pw.toml')
    meta = tomllib.load(open(toml_path, 'rb'))
    version = newer_version(meta['update']['modrinth']['mod-id'], meta['update']['modrinth']['version'], LOADERS[folder])
    if version is None:
        return f'{meta["name"]}: already newest ({meta.get("x-prismlauncher-version-number")})'
    file = ([f for f in version['files'] if f['primary']] or version['files'])[0]
    data = urllib.request.urlopen(urllib.request.Request(file['url'], headers=HEADERS)).read()
    if hashlib.sha512(data).hexdigest() != file['hashes']['sha512']:
        sys.exit(f'{file["filename"]}: SHA512 mismatch, nothing changed')
    shutil.move(os.path.join(root, meta['filename']), backup)
    shutil.move(toml_path, backup)
    with open(os.path.join(root, file['filename']), 'wb') as f:
        f.write(data)
    with open(toml_path, 'w') as f:
        f.write(tracking_toml(meta['name'], version, file, LOADERS[folder]))
    return f'{meta["name"]}: {meta.get("x-prismlauncher-version-number")} -> {version["version_number"]}'


def main():
    game, backup, *targets = sys.argv[1:]
    os.makedirs(backup, exist_ok=True)
    for target in targets:
        print(update(game, backup, target))


if __name__ == '__main__':
    main()

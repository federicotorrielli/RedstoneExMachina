"""Update Prism-tracked mods to their newest Modrinth release for the pack's Minecraft version.

usage: update_mods.py <game dir> <backup dir> <tracking file name>...   (e.g. polytone for mods/.index/polytone.pw.toml)

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


def latest_version(project_id):
    query = urllib.parse.urlencode({'game_versions': json.dumps([MINECRAFT]), 'loaders': json.dumps(['fabric'])})
    url = f'https://api.modrinth.com/v2/project/{project_id}/version?{query}'
    versions = json.load(urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS)))
    releases = [v for v in versions if v['version_type'] == 'release'] or versions
    return releases[0]


def tracking_toml(name, version, file):
    q = lambda s: "'" + s.replace("'", "\\'") + "'"
    deps = ''.join(f"\n[[x-prismlauncher-dependencies]]\naddonId = {q(d['project_id'])}\n"
                   f"type = {q(d['dependency_type'].upper())}\n" for d in version['dependencies'] if d['project_id'])
    return f"""filename = {q(file['filename'])}
name = {q(name)}
side = ''
x-prismlauncher-loaders = [ 'fabric' ]
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


def update(mods, backup, slug):
    toml_path = os.path.join(mods, '.index', f'{slug}.pw.toml')
    meta = tomllib.load(open(toml_path, 'rb'))
    version = latest_version(meta['update']['modrinth']['mod-id'])
    if version['id'] == meta['update']['modrinth']['version']:
        return f'{meta["name"]}: already {version["version_number"]}'
    file = ([f for f in version['files'] if f['primary']] or version['files'])[0]
    data = urllib.request.urlopen(urllib.request.Request(file['url'], headers=HEADERS)).read()
    if hashlib.sha512(data).hexdigest() != file['hashes']['sha512']:
        sys.exit(f'{file["filename"]}: SHA512 mismatch, nothing changed')
    shutil.move(os.path.join(mods, meta['filename']), backup)
    shutil.move(toml_path, backup)
    with open(os.path.join(mods, file['filename']), 'wb') as f:
        f.write(data)
    with open(toml_path, 'w') as f:
        f.write(tracking_toml(meta['name'], version, file))
    return f'{meta["name"]}: {meta.get("x-prismlauncher-version-number")} -> {version["version_number"]}'


def main():
    game, backup, *slugs = sys.argv[1:]
    os.makedirs(backup, exist_ok=True)
    for slug in slugs:
        print(update(os.path.join(game, 'mods'), backup, slug))


if __name__ == '__main__':
    main()

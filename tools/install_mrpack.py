"""Install a .mrpack into an empty game dir like a launcher does, checking every download.

usage: install_mrpack.py <pack.mrpack> <game dir>
"""

import hashlib
import json
import os
import sys
import urllib.parse
import urllib.request
import zipfile

ALLOWED_HOSTS = ('cdn.modrinth.com', 'github.com', 'raw.githubusercontent.com', 'gitlab.com')


def main():
    pack, game = sys.argv[1:3]
    with zipfile.ZipFile(pack) as z:
        index = json.loads(z.read('modrinth.index.json'))
        for f in index['files']:
            url = f['downloads'][0]
            host = urllib.parse.urlparse(url).hostname
            if host not in ALLOWED_HOSTS:
                sys.exit(f'{f["path"]}: download host {host} is not allowed by the Modrinth format')
            data = urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'RedstoneExMachina'})).read()
            for algorithm, expected in f['hashes'].items():
                if hashlib.new(algorithm, data).hexdigest() != expected:
                    sys.exit(f'{f["path"]}: {algorithm} mismatch')
            if len(data) != f['fileSize']:
                sys.exit(f'{f["path"]}: size mismatch')
            dst = os.path.join(game, f['path'])
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst, 'wb') as out:
                out.write(data)
        for name in z.namelist():
            if name.startswith('overrides/') and not name.endswith('/'):
                dst = os.path.join(game, name.removeprefix('overrides/'))
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                with open(dst, 'wb') as out:
                    out.write(z.read(name))
    print(f'{len(index["files"])} downloads verified, overrides extracted into {game}')
    print('dependencies:', index['dependencies'])


if __name__ == '__main__':
    main()

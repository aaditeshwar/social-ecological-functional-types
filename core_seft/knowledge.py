"""Knowledge-pack install and version stamp."""
import json
import shutil
import urllib.request
from pathlib import Path

from seft.util import ROOT, load_json

GITHUB_RELEASE = (
    'https://github.com/aaditeshwar/social-ecological-functional-types/releases/download/'
    'knowledge-{ver}/core-seft-knowledge-{ver}.zip'
)


def bundled_knowledge():
    """JSON pack shipped with this checkout (or the installed wheel)."""
    for p in (ROOT / 'knowledge', Path(__file__).resolve().parents[1] / 'knowledge'):
        if (p / 'variables.json').exists():
            return p
    raise FileNotFoundError('core-seft knowledge pack not found next to the library')


def pack_version(kd):
    p = Path(kd) / 'manifest.json'
    if p.exists():
        return load_json(p).get('version', '0.0.0')
    return '0.0.0'


def min_library(kd):
    p = Path(kd) / 'manifest.json'
    if p.exists():
        return load_json(p).get('min_library', '0.0.0')
    return '0.0.0'


def parse_ver(s):
    parts = []
    for x in str(s or '0').split('.'):
        try:
            parts.append(int(x))
        except ValueError:
            parts.append(0)
    return tuple((parts + [0, 0, 0])[:3])


def copy_pack(src, dest):
    src, dest = Path(src), Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    for p in src.glob('*.json'):
        shutil.copy2(p, dest / p.name)
    wb = src / 'waterbody'
    if wb.exists():
        (dest / 'waterbody').mkdir(exist_ok=True)
        for p in wb.glob('*.json'):
            shutil.copy2(p, dest / 'waterbody' / p.name)
    return dest


def install_from_zip(url, dest):
    import tempfile
    import zipfile
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        zpath = Path(tmp) / 'pack.zip'
        urllib.request.urlretrieve(url, zpath)
        with zipfile.ZipFile(zpath) as z:
            z.extractall(tmp)
        root = Path(tmp)
        # zip may contain knowledge/ at the top or the json files themselves
        if (root / 'knowledge' / 'variables.json').exists():
            src = root / 'knowledge'
        elif (root / 'variables.json').exists():
            src = root
        else:
            found = list(root.rglob('variables.json'))
            if not found:
                raise FileNotFoundError(f'no knowledge pack in {url}')
            src = found[0].parent
        return copy_pack(src, dest)


def refresh(dest, version='latest', src=None):
    """Install a pack into dest. `latest` copies the bundled pack; a semver tries GitHub Releases."""
    dest = Path(dest)
    src = Path(src) if src else bundled_knowledge()
    if version in (None, 'latest', pack_version(src)):
        return copy_pack(src, dest)
    url = GITHUB_RELEASE.format(ver=version)
    try:
        return install_from_zip(url, dest)
    except Exception as e:
        raise FileNotFoundError(
            f'could not download knowledge pack {version} from {url}: {e}'
        ) from e


def dump_pools_from_atlas(web_data=None, dest=None):
    """Write knowledge/pools.json from the published atlas indexes (maintainer helper)."""
    web_data = Path(web_data or ROOT / 'web' / 'data')
    dest = Path(dest or bundled_knowledge() / 'pools.json')
    mws = json.loads((web_data / 'index.json').read_text(encoding='utf-8')).get('pools') or {}
    wb = {}
    wip = web_data / 'waterbody' / 'index.json'
    if wip.exists():
        wb = json.loads(wip.read_text(encoding='utf-8')).get('pools') or {}
    prov = (json.loads(dest.read_text(encoding='utf-8')).get('provenance') if dest.exists() else None) or {}
    dest.write_text(json.dumps({'mws': mws, 'waterbody': wb, 'provenance': prov}, separators=(',', ':'), ensure_ascii=False),
                    encoding='utf-8')
    return dest

"""Build Home TV, propose upstream merges and publish approved Kodi packages.

Standard library only. Never reads a Kodi profile, .env, or device backup.
"""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import tempfile
import urllib.request
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
META = ROOT / '.hometv'
UPSTREAM = 'skin.arctic.fuse.3'
ADDON = 'skin.arctic.fuse.hometv'
RUNTIME_DIRS = {'1080i', 'colors', 'extras', 'fonts', 'language', 'media', 'shortcuts'}
RUNTIME_FILES = {'addon.xml', 'icon.png', 'fanart.jpg', 'Readme.md', 'LICENSE.txt'}
TEXT_EXTENSIONS = {'.xml', '.json', '.txt', '.md', '.po', '.py'}


def git(*args, cwd=ROOT, env=None, check=True, binary=False, input=None):
    result = subprocess.run(['git', *map(str, args)], cwd=cwd, env=env,
                            input=input, capture_output=True, text=not binary,
                            encoding=None if binary else 'utf-8')
    if check and result.returncode:
        error = result.stderr.decode() if binary else result.stderr
        raise RuntimeError('git ' + str(args[0]) + ': ' + error.strip())
    return result


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write_json(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=True) + '\n', encoding='utf-8')


def version_tuple(value):
    if not re.fullmatch(r'\d+\.\d+\.\d+', value):
        raise ValueError('Expected a stable three-part version: ' + value)
    return tuple(map(int, value.split('.')))


def next_version(value):
    major, minor, patch = version_tuple(value)
    return f'{major}.{minor}.{patch + 1}'


def runtime_files(root=ROOT):
    paths = git('ls-files', '-z', cwd=root).stdout.split('\0')
    selected = {}
    for name in filter(None, paths):
        parts = PurePosixPath(name).parts
        if name not in RUNTIME_FILES and parts[0] not in RUNTIME_DIRS:
            continue
        if any(part.startswith('.') or part == '__pycache__' for part in parts):
            raise RuntimeError('Unexpected private/cache file in runtime tree: ' + name)
        if parts[0] == '1080i' and (Path(name).name.startswith('script-skinvariables-generator-includes')
                                   or Path(name).name == 'script-skinvariables-skinusers.xml'):
            raise RuntimeError('Generated user cache must not be tracked: ' + name)
        path = root / name
        if path.is_symlink():
            raise RuntimeError('Symlink cannot be packaged: ' + name)
        selected[name] = path.read_bytes()
    if not RUNTIME_FILES <= selected.keys():
        raise RuntimeError('Incomplete skin source')
    return selected


def package_contents(root=ROOT):
    config = read_json(root / '.hometv/config.json')
    files = runtime_files(root)
    for name, data in files.items():
        if Path(name).suffix.lower() in TEXT_EXTENSIONS:
            files[name] = data.replace(UPSTREAM.encode(), ADDON.encode())
    addon = ET.fromstring(files['addon.xml'])
    upstream_version = addon.get('version')
    accepted = read_json(root / '.hometv/upstream.json')
    if upstream_version != accepted['version']:
        raise RuntimeError('Source version differs from the accepted upstream record')
    if addon.get('id') != ADDON:
        raise RuntimeError('Unexpected skin ID')
    addon.set('name', 'Arctic Fuse Home TV')
    addon.set('version', config['version'])
    addon.set('provider-name', 'Marco - derived from jurialmunkey')
    for summary in addon.findall("extension[@point='xbmc.addon.metadata']/summary"):
        if summary.get('lang') == 'en':
            summary.text = 'Arctic Fuse with a channel-list Home'
    files['addon.xml'] = ET.tostring(addon, encoding='utf-8', xml_declaration=True)
    template = files['1080i/Home.xml'].decode('utf-8')
    menu = ET.fromstring(files['1080i/Includes_Home.xml']).find(
        "include[@name='Home_Switcher_Horz']/control[@type='group']/control[@type='group']")
    if menu is None or template.count('<!-- NATIVE_MENU -->') != 1:
        raise RuntimeError('Native menu structure changed: review the integration')
    menu = copy.deepcopy(menu)
    for child in list(menu):
        if child.tag == 'include' and child.text in ('Home_Group_Definition', 'Home_Reposition'):
            menu.remove(child)
    for key, value in reversed((('left', '80'), ('right', '80'), ('top', '60'), ('height', '80'))):
        child = ET.Element(key)
        child.text = value
        menu.insert(0, child)
    files['1080i/Home.xml'] = template.replace(
        '<!-- NATIVE_MENU -->', ET.tostring(menu, encoding='unicode')).encode('utf-8')
    files['HOMETV-NOTICE.md'] = (root / '.hometv/NOTICE.md').read_bytes()
    for name, data in files.items():
        if name.endswith('.xml'):
            ET.fromstring(data)
        if name.endswith('.json'):
            json.loads(data)
        if Path(name).suffix.lower() in TEXT_EXTENSIONS and UPSTREAM.encode() in data:
            raise RuntimeError('Unmigrated namespace: ' + name)
    return files, config, accepted


def check_approval(package, approval, version):
    if approval.get('version') != version or approval.get('addon_id') != ADDON:
        raise RuntimeError('Approval belongs to another package')
    if hashlib.sha256(Path(package).read_bytes()).hexdigest() != approval.get('package_sha256'):
        raise RuntimeError('Package bytes have not been approved')
    required = {'cold_boot', 'first_ok', 'back_to_list', 'native_hubs', 'skin_switch', 'profile_preservation'}
    if not required <= {key for key, value in approval.get('checks', {}).items() if value is True}:
        raise RuntimeError('Required device checks have not been completed')
    if not approval.get('runtime_verified'):
        raise RuntimeError('No verified runtime in approval')


def build(output=None, release=False, root=ROOT):
    files, config, accepted = package_contents(root)
    output = Path(output or root / 'dist')
    output.mkdir(parents=True, exist_ok=True)
    version_tuple(config['version'])
    package = output / f"{ADDON}-{config['version']}.zip"
    with zipfile.ZipFile(package, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name, data in sorted(files.items()):
            info = zipfile.ZipInfo(ADDON + '/' + name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, data)
    digest = hashlib.sha256(package.read_bytes()).hexdigest()
    approval_file = root / '.hometv/approvals' / f"{config['version']}.json"
    approval = read_json(approval_file) if approval_file.exists() else {}
    approved = False
    try:
        check_approval(package, approval, config['version'])
        approved = True
    except RuntimeError:
        if release:
            raise
    manifest = {
        'schema': 1, 'addon_id': ADDON, 'version': config['version'],
        'upstream_id': UPSTREAM, 'upstream_version': accepted['version'],
        'upstream_commit': accepted['commit'],
        'base_review': 'known-base' if approved else 'unverified',
        'profile_schema': config['profile_schema'],
        'package_sha256': digest,
        'runtime_verified': approval.get('runtime_verified', []) if approved else [],
        'files': {name: hashlib.sha256(data).hexdigest() for name, data in sorted(files.items())},
    }
    write_json(package.with_suffix('.manifest.json'), manifest)
    return package, manifest


def request_json(url):
    request = urllib.request.Request(url, headers={'User-Agent': 'Arctic-Fuse-Home-TV'})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def prepare_merge(root, commit, version, report_dir):
    """Use a disposable worktree; never reset or force-push an existing branch."""
    root = Path(root).resolve()
    report_dir = Path(report_dir).resolve()
    report_dir.mkdir(parents=True, exist_ok=True)
    base = git('rev-parse', 'home-tv', cwd=root).stdout.strip()
    branch = f'updates/arctic-{version}'
    exists = any(git('show-ref', '--verify', prefix + branch, cwd=root, check=False).returncode == 0
                 for prefix in ('refs/heads/', 'refs/remotes/origin/'))
    if exists:
        report = {'status': 'existing', 'branch': branch, 'version': version, 'upstream_commit': commit}
        write_json(report_dir / 'report.json', report)
        return report
    directory = root / '.hometv/worktrees' / version
    directory.parent.mkdir(parents=True, exist_ok=True)
    if directory.exists() or not directory.resolve().is_relative_to(root / '.hometv/worktrees'):
        raise RuntimeError('Unsafe or existing temporary worktree')
    git('worktree', 'add', '-b', branch, directory, base, cwd=root)
    try:
        result = git('merge', '--no-ff', '--no-commit', commit, cwd=directory, check=False)
        conflicts = git('diff', '--name-only', '--diff-filter=U', cwd=directory).stdout.splitlines()
        if result.returncode and not conflicts:
            raise RuntimeError('Upstream integration failed: ' + result.stderr)
        if conflicts:
            git('merge', '--abort', cwd=directory)
            report = {'status': 'conflict', 'branch': branch, 'version': version,
                      'upstream_commit': commit, 'conflicts': conflicts,
                      'message': 'No upstream code merged. Resolve conflicts before building or publishing.'}
        else:
            accepted = read_json(directory / '.hometv/upstream.json')
            accepted.update(version=version, tag='v' + version, commit=commit)
            write_json(directory / '.hometv/upstream.json', accepted)
            config = read_json(directory / '.hometv/config.json')
            config['version'] = next_version(config['version'])
            write_json(directory / '.hometv/config.json', config)
            report = {'status': 'candidate', 'branch': branch, 'version': version,
                      'upstream_commit': commit, 'device_verification': 'pending'}
        write_json(directory / '.hometv/update-report.json', report)
        git('add', '.hometv', cwd=directory)
        git('commit', '-m', f"{'Record blocked integration of' if conflicts else 'Integrate'} Arctic Fuse {version}", cwd=directory)
        write_json(report_dir / 'report.json', report)
        body = (f"Arctic Fuse **{version}** (`{commit}`).\n\n"
                + ("Integration stopped. Conflicts:\n\n" + '\n'.join('- `' + p + '`' for p in conflicts)
                   if conflicts else "Upstream changes merged with the Home TV branch. Package and device checks are pending.")
                + "\n\nNo automatic merge or TV deployment. Release requires approval of the exact package SHA256.\n")
        (report_dir / 'pull-request.md').write_text(body, encoding='utf-8')
        return report
    finally:
        if directory.resolve().is_relative_to(root / '.hometv/worktrees'):
            git('worktree', 'remove', '--force', directory, cwd=root, check=False)


def sync(report_dir, root=ROOT):
    config = read_json(root / '.hometv/config.json')
    accepted = read_json(root / '.hometv/upstream.json')
    published = ET.fromstring(request_json(config['upstream_manifest']))
    version = published.get('version', '')
    if published.get('id') != UPSTREAM:
        raise RuntimeError('Unexpected official add-on manifest')
    if version_tuple(version) <= version_tuple(accepted['version']):
        report = {'status': 'current', 'version': version}
        write_json(Path(report_dir) / 'report.json', report)
        return report
    gui = published.find("requires/import[@addon='xbmc.gui']")
    if gui is None or gui.get('version') != accepted['gui_api']:
        raise RuntimeError('Kodi GUI API changed; review the Kodi compatibility channel first')
    remotes = git('remote', cwd=root).stdout.splitlines()
    if 'upstream' not in remotes:
        git('remote', 'add', 'upstream', config['upstream_url'], cwd=root)
    elif git('remote', 'get-url', 'upstream', cwd=root).stdout.strip() != config['upstream_url']:
        raise RuntimeError('Unexpected upstream remote')
    release_ref = 'refs/remotes/upstream/releases/v' + version
    git('fetch', '--no-tags', 'upstream', f'refs/tags/v{version}:{release_ref}', cwd=root)
    commit = git('rev-parse', release_ref + '^{commit}', cwd=root).stdout.strip()
    original = ET.fromstring(git('show', commit + ':addon.xml', cwd=root).stdout)
    if original.get('version') != version or original.get('id') != UPSTREAM:
        raise RuntimeError('Published version and source tag do not match')
    if git('merge-base', '--is-ancestor', accepted['commit'], commit, cwd=root, check=False).returncode:
        raise RuntimeError('Upstream history diverged; manual review required')
    report = prepare_merge(root, commit, version, report_dir)
    if report['status'] == 'candidate':
        previous = git('rev-parse', 'upstream-stable', cwd=root).stdout.strip()
        git('update-ref', 'refs/heads/upstream-stable', commit, previous, cwd=root)
    return report


def repository_files(package, manifest, root=ROOT):
    config = read_json(root / '.hometv/config.json')
    approval = read_json(root / '.hometv/approvals' / (manifest['version'] + '.json'))
    check_approval(package, approval, manifest['version'])
    # A channel only covers Kodi versions actually tested on a device.
    majors = {int(r['runtime']['kodi']['major']) for r in approval['runtime_verified']}
    if majors != {config['kodi_major']}:
        raise RuntimeError('Approval does not match the repository Kodi channel')
    base_url = f"https://raw.githubusercontent.com/{config['github_repository']}/kodi-repo/"
    repo_id = 'repository.arctic.hometv'
    repository = ET.Element('addon', id=repo_id, name='Arctic Fuse Home TV Repository',
                            version='1.0.0', **{'provider-name': 'mymusicmyspace'})
    requires = ET.SubElement(repository, 'requires')
    ET.SubElement(requires, 'import', addon='xbmc.addon', version='20.0.0')
    extension = ET.SubElement(repository, 'extension', point='xbmc.addon.repository')
    directory = ET.SubElement(extension, 'dir', minversion=f"{config['kodi_major']}.0.0",
                              maxversion=f"{config['kodi_major']}.99.99")
    for tag, value in (('info', base_url + 'omega/addons.xml'),
                       ('checksum', base_url + 'omega/addons.xml.md5'),
                       ('datadir', base_url + 'omega/'), ('hashes', 'false')):
        ET.SubElement(directory, tag).text = value
    metadata = ET.SubElement(repository, 'extension', point='xbmc.addon.metadata')
    ET.SubElement(metadata, 'summary', lang='en_GB').text = 'Verified Arctic Fuse Home TV releases'
    ET.SubElement(metadata, 'description', lang='en_GB').text = 'Home TV updates for verified Kodi versions.'
    ET.SubElement(metadata, 'platform').text = 'all'
    ET.SubElement(metadata, 'license').text = 'CC BY-NC-SA 4.0'
    repo_xml = ET.tostring(repository, encoding='utf-8', xml_declaration=True)
    addons = ET.Element('addons')
    with zipfile.ZipFile(package) as archive:
        addons.append(ET.fromstring(archive.read(ADDON + '/addon.xml')))
    addons.append(repository)
    index = ET.tostring(addons, encoding='utf-8', xml_declaration=True)
    with tempfile.SpooledTemporaryFile() as stream:
        with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
            item = zipfile.ZipInfo(repo_id + '/addon.xml', date_time=(2026, 1, 1, 0, 0, 0))
            item.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(item, repo_xml)
        stream.seek(0)
        repo_zip = stream.read()
    return {
        'omega/addons.xml': index,
        'omega/addons.xml.md5': hashlib.md5(index).hexdigest().encode(),
        f'omega/{ADDON}/{Path(package).name}': Path(package).read_bytes(),
        f'omega/{ADDON}/{Path(package).name}.sha256': manifest['package_sha256'].encode(),
        f'omega/{ADDON}/{manifest["version"]}.manifest.json': json.dumps(manifest, indent=2).encode(),
        f'omega/{repo_id}/{repo_id}-1.0.0.zip': repo_zip,
        f'{repo_id}-1.0.0.zip': repo_zip,
        'README.md': (f'# Arctic Fuse Home TV repository\n\nKodi {config["kodi_major"]} only.\n\n'
                      f'Install `{repo_id}-1.0.0.zip` to receive approved Home TV releases.\n'
                      'No Kodi profiles, accounts, private lists or device settings are included.\n').encode(),
    }


def publish(package, manifest, root=ROOT):
    files = repository_files(package, manifest, root)
    ref = 'refs/heads/kodi-repo'
    previous = git('rev-parse', '--verify', ref, cwd=root, check=False)
    old = previous.stdout.strip() if previous.returncode == 0 else None
    version_path = f'omega/{ADDON}/{Path(package).name}.sha256'
    if old:
        existing = git('show', old + ':' + version_path, cwd=root, check=False)
        if existing.returncode == 0 and existing.stdout.strip() != manifest['package_sha256']:
            raise RuntimeError('A published version is immutable; increment the version')
        old_index = git('show', old + ':omega/addons.xml', cwd=root, check=False)
        if old_index.returncode == 0:
            current = ET.fromstring(old_index.stdout).find(f"addon[@id='{ADDON}']")
            if current is not None and version_tuple(current.get('version')) > version_tuple(manifest['version']):
                raise RuntimeError('Refusing to downgrade the repository')
    index_root = root / 'dist'
    index_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='hometv-index-', dir=index_root) as directory:
        env = os.environ.copy()
        env['GIT_INDEX_FILE'] = str(Path(directory) / 'index')
        git('read-tree', old or '--empty', cwd=root, env=env)
        for name, data in files.items():
            blob = git('hash-object', '-w', '--stdin', cwd=root, binary=True, input=data).stdout.decode().strip()
            git('update-index', '--add', '--cacheinfo', '100644', blob, name, cwd=root, env=env)
        tree = git('write-tree', cwd=root, env=env).stdout.strip()
        if old and git('rev-parse', old + '^{tree}', cwd=root).stdout.strip() == tree:
            return old
        parents = ['-p', old] if old else []
        commit = git('commit-tree', tree, *parents, '-m', f"Publish verified Home TV {manifest['version']}", cwd=root).stdout.strip()
        git('update-ref', ref, commit, old or '0' * 40, cwd=root)
        return commit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    builder = commands.add_parser('build')
    builder.add_argument('--output', type=Path)
    builder.add_argument('--release', action='store_true')
    syncer = commands.add_parser('sync')
    syncer.add_argument('--report-dir', type=Path, default=ROOT / 'dist/sync')
    publisher = commands.add_parser('publish')
    publisher.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.command == 'sync':
        print(json.dumps(sync(args.report_dir)))
    else:
        package, manifest = build(args.output, release=args.command == 'publish' or args.release)
        if args.command == 'publish':
            print(json.dumps({'branch': 'kodi-repo', 'commit': publish(package, manifest)}))
        print(json.dumps({'package': str(package), 'sha256': manifest['package_sha256'], 'review': manifest['base_review']}))


if __name__ == '__main__':
    main()

"""Exercise actual Git conflicts, retained changes and release gates offline."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import maintain as m


class RepositoryTest(unittest.TestCase):
    def setUp(self):
        test_root = m.ROOT / 'dist/test-workspaces'
        test_root.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix='hometv-test-', dir=test_root)
        def cleanup():
            if not Path(self.temp.name).resolve().is_relative_to(test_root.resolve()):
                raise RuntimeError('Unsafe test cleanup path')
            self.temp.cleanup()
        self.addCleanup(cleanup)
        self.root = Path(self.temp.name)
        m.git('init', '--initial-branch=home-tv', cwd=self.root)
        m.git('config', 'user.name', 'Home TV Tests', cwd=self.root)
        m.git('config', 'user.email', 'tests@example.invalid', cwd=self.root)
        self.write('.gitignore', '.hometv/worktrees/\ndist/\n')
        self.write('1080i/Home.xml', '<window><!-- NATIVE_MENU --></window>')
        self.write('1080i/Includes_Home.xml', '''<includes>
          <include name="Home_Switcher_Horz"><control type="group"><control type="group">
          <include>Home_Group_Definition</include><include>Home_Reposition</include>
          <control type="label"><label>Native menu</label></control>
          </control></control></include></includes>''')
        self.write('addon.xml', '<addon id="skin.arctic.fuse.3" version="3.3.12"><requires>'
                   '<import addon="xbmc.gui" version="5.17.0" /></requires>'
                   '<extension point="xbmc.addon.metadata"><summary lang="en">Skin</summary></extension></addon>')
        for name in ('icon.png', 'fanart.jpg', 'Readme.md', 'LICENSE.txt'):
            self.write(name, 'Fixture')
        self.write('shortcuts/default.json', '{"path":"special://profile/addon_data/skin.arctic.fuse.3/"}')
        self.write('.hometv/NOTICE.md', 'Public attribution')
        m.write_json(self.root / '.hometv/config.json', {
            'version': '1.0.0', 'profile_schema': 1, 'kodi_major': 21,
            'github_repository': 'example/skin.arctic.fuse.hometv'})
        m.write_json(self.root / '.hometv/upstream.json', {'version': '3.3.12', 'commit': 'fixture'})
        self.commit('Base')

    def write(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')

    def commit(self, message):
        m.git('add', '.', cwd=self.root)
        m.git('commit', '-m', message, cwd=self.root)
        return m.git('rev-parse', 'HEAD', cwd=self.root).stdout.strip()

    def approval(self, manifest, major=21):
        data = {
            'version': manifest['version'], 'addon_id': m.ADDON,
            'package_sha256': manifest['package_sha256'],
            'checks': dict.fromkeys(['cold_boot', 'first_ok', 'back_to_list',
                                    'native_hubs', 'skin_switch', 'profile_preservation'], True),
            'runtime_verified': [{'runtime': {'kodi': {'major': major}}}],
        }
        m.write_json(self.root / '.hometv/approvals/1.0.0.json', data)
        return data

    def branches(self, conflict=False):
        m.git('switch', '-c', 'author', cwd=self.root)
        self.write('1080i/Home.xml' if conflict else 'Readme.md', 'Author changed this\n')
        upstream = self.commit('Author update')
        m.git('switch', 'home-tv', cwd=self.root)
        self.write('1080i/Home.xml', 'My channel Home\n')
        home = self.commit('Custom Home')
        return upstream, home

    def test_merge_keeps_home_and_adds_author_changes_without_touching_active_branch(self):
        upstream, home = self.branches()
        report = m.prepare_merge(self.root, upstream, '3.3.13', self.root / 'dist/report')
        self.assertEqual(report['status'], 'candidate')
        self.assertEqual(m.git('rev-parse', 'home-tv', cwd=self.root).stdout.strip(), home)
        self.assertEqual(m.git('show', report['branch'] + ':1080i/Home.xml', cwd=self.root).stdout, 'My channel Home\n')
        self.assertEqual(m.git('show', report['branch'] + ':Readme.md', cwd=self.root).stdout, 'Author changed this\n')
        config = json.loads(m.git('show', report['branch'] + ':.hometv/config.json', cwd=self.root).stdout)
        self.assertEqual(config['version'], '1.0.1')
        self.assertEqual(len(m.git('show', '-s', '--format=%P', report['branch'], cwd=self.root).stdout.split()), 2)

    def test_conflict_aborts_merge_and_preserves_home(self):
        upstream, home = self.branches(conflict=True)
        report = m.prepare_merge(self.root, upstream, '3.3.13', self.root / 'dist/report')
        self.assertEqual(report['status'], 'conflict')
        self.assertIn('1080i/Home.xml', report['conflicts'])
        self.assertEqual(m.git('rev-parse', 'home-tv', cwd=self.root).stdout.strip(), home)
        self.assertEqual(m.git('show', report['branch'] + ':1080i/Home.xml', cwd=self.root).stdout, 'My channel Home\n')
        self.assertNotEqual(m.git('merge-base', '--is-ancestor', upstream, report['branch'], cwd=self.root, check=False).returncode, 0)

    def test_existing_update_branch_is_never_overwritten(self):
        upstream, _ = self.branches()
        m.git('branch', 'updates/arctic-3.3.13', cwd=self.root)
        before = m.git('rev-parse', 'updates/arctic-3.3.13', cwd=self.root).stdout
        report = m.prepare_merge(self.root, upstream, '3.3.13', self.root / 'dist/report')
        self.assertEqual(report['status'], 'existing')
        self.assertEqual(before, m.git('rev-parse', 'updates/arctic-3.3.13', cwd=self.root).stdout)

    def test_package_excludes_private_and_tool_files_and_renames_profile_namespace(self):
        self.write('.env', 'PRIVATE_SENTINEL')
        self.write('backups/profile.xml', 'PRIVATE_SENTINEL')
        self.write('.hometv/tool.py', 'PRIVATE_SENTINEL')
        self.commit('Private files must not enter runtime package')
        package, manifest = m.build(root=self.root)
        self.assertEqual(manifest['base_review'], 'unverified')
        self.assertEqual(manifest['runtime_verified'], [])
        with zipfile.ZipFile(package) as archive:
            self.assertFalse(any('.env' in n or '/backups/' in n or '/.hometv/' in n for n in archive.namelist()))
            for name in archive.namelist():
                self.assertNotIn(b'PRIVATE_SENTINEL', archive.read(name))
            shortcuts = archive.read(m.ADDON + '/shortcuts/default.json')
            self.assertIn(m.ADDON.encode(), shortcuts)
            self.assertNotIn(m.UPSTREAM.encode(), shortcuts)
        first = manifest['package_sha256']
        self.assertEqual(m.build(root=self.root)[1]['package_sha256'], first)

    def test_changed_bytes_cannot_reuse_a_device_approval(self):
        _, manifest = m.build(root=self.root)
        self.approval(manifest)
        self.assertEqual(m.build(release=True, root=self.root)[1]['base_review'], 'known-base')
        self.write('Readme.md', 'Unverified change')
        with self.assertRaisesRegex(RuntimeError, 'not been approved'):
            m.build(release=True, root=self.root)

    def test_kodi_channel_cannot_advertise_an_untested_major(self):
        package, manifest = m.build(root=self.root)
        self.approval(manifest, major=22)
        with self.assertRaisesRegex(RuntimeError, 'Kodi channel'):
            m.repository_files(package, manifest, root=self.root)

    def test_publish_is_idempotent_and_refuses_changed_bytes_at_same_version(self):
        package, manifest = m.build(root=self.root)
        self.approval(manifest)
        commit = m.publish(package, manifest, root=self.root)
        self.assertEqual(m.publish(package, manifest, root=self.root), commit)
        index = ET.fromstring(m.git('show', 'kodi-repo:omega/addons.xml', cwd=self.root).stdout)
        directory = index.find("addon[@id='repository.arctic.hometv']/extension[@point='xbmc.addon.repository']/dir")
        self.assertEqual(directory.get('maxversion'), '21.99.99')
        self.write('Readme.md', 'Different package with same version')
        package, manifest = m.build(root=self.root)
        self.approval(manifest)
        with self.assertRaisesRegex(RuntimeError, 'published version is immutable'):
            m.publish(package, manifest, root=self.root)
        self.assertEqual(m.git('rev-parse', 'kodi-repo', cwd=self.root).stdout.strip(), commit)


if __name__ == '__main__':
    unittest.main()

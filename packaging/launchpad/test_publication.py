"""Regression checks for publication detection without contacting Launchpad."""

from contextlib import redirect_stdout
import gzip
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    'publication', Path(__file__).with_name('check-publication.py'))
monitor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(monitor)

ARCHIVE = 'https://launchpad.net/~freetogo/+archive/ubuntu/amule-weekly'
TARGET = {'series': 'noble', 'url': ARCHIVE + '/+recipebuild/1'}
VERSION = '3.1.0+git202610201739~ubuntu24.04.1'


class PublicationTests(unittest.TestCase):
    def check(self, recipe_state='Successfully built', source=True,
              binary_state='Successfully built', published=True,
              index_version=VERSION, source_version=VERSION):
        build = {'buildstate': recipe_state, 'build_log_url': 'https://example.test/log'}
        source_record = {'self_link': ARCHIVE + '/+sourcepub/1', 'status': 'Published',
                         'source_package_version': source_version,
                         'distro_series_link': 'https://api.launchpad.net/devel/ubuntu/noble'}
        binary = {'web_link': ARCHIVE + '/+build/2', 'buildstate': binary_state,
                  'arch_tag': 'amd64'}
        binary_publication = {'binary_package_name': 'amule-weekly',
                              'binary_package_version': VERSION,
                              'status': 'Published' if published else 'Pending',
                              'distro_arch_series_link': 'https://api.launchpad.net/devel/ubuntu/noble/amd64'}

        def entries(url, **params):
            return iter({'getPublishedSources': [source_record] if source else [],
                         'getBuilds': [binary],
                         'getPublishedBinaries': [binary_publication]}[params['ws.op']])

        def fetch(url, **kwargs):
            if url.endswith('/log'):
                return gzip.compress(f'dpkg-buildpackage: info: source version {VERSION}\n'.encode())
            if index_version is None:
                return None
            return gzip.compress(f'Package: amule-weekly\nVersion: {index_version}\nArchitecture: amd64\n\n'.encode())

        with patch.object(monitor, 'api', return_value=build), \
                patch.object(monitor, 'entries', side_effect=entries), \
                patch.object(monitor, 'fetch', side_effect=fetch):
            return monitor.check_target(TARGET, ARCHIVE)

    def test_uploading_is_pending(self):
        result = self.check(recipe_state='Uploading build', source=False)
        self.assertFalse(result['published'])
        self.assertNotIn('error', result)

    def test_source_failure_is_reported(self):
        self.assertIn('Recipe build:', self.check(recipe_state='Failed to upload')['error'])

    def test_binary_failure_is_reported(self):
        result = self.check(binary_state='Failed to build', published=False)
        self.assertIn('Binary build:', result['error'])

    def test_api_publication_requires_apt_index(self):
        self.assertFalse(self.check(index_version=None)['published'])

    def test_old_apt_package_cannot_complete_new_request(self):
        self.assertFalse(self.check(index_version='3.0.0')['published'])

    def test_old_source_cannot_complete_new_request(self):
        self.assertFalse(self.check(source_version='3.0.0')['published'])

    def test_matching_publication_completes(self):
        self.assertTrue(self.check()['published'])

    def test_version_must_belong_to_correct_package(self):
        data = b'Package: other\nVersion: expected\nArchitecture: amd64\n\nPackage: amule-weekly\nVersion: old\nArchitecture: amd64\n'
        self.assertEqual(monitor.package_versions(data), {'old'})

    def test_both_series_required_and_new_requests_resume(self):
        with tempfile.TemporaryDirectory() as directory:
            request_path, status_path = [Path(directory) / name for name in ('request.json', 'status.json')]
            request = {'requested_at': 'today', 'archive': ARCHIVE,
                       'builds': [TARGET, {**TARGET, 'series': 'resolute', 'url': ARCHIVE + '/+recipebuild/2'}]}
            request_path.write_text(json.dumps(request))
            arguments = ['check', '--request', str(request_path), '--status', str(status_path)]
            def run(results):
                with patch('sys.argv', arguments), patch.object(monitor, 'check_target', side_effect=results) as check, redirect_stdout(io.StringIO()):
                    self.assertEqual(monitor.main(), 0)
                    return check.call_count
            def result(series, done):
                return {'series': series, 'recipe_build': TARGET['url'], 'published': done, 'binary_builds': []}
            self.assertEqual(run([result('noble', True), result('resolute', False)]), 2)
            self.assertFalse(json.loads(status_path.read_text())['complete'])
            self.assertEqual(run([result('noble', True), result('resolute', True)]), 2)
            self.assertTrue(json.loads(status_path.read_text())['complete'])
            self.assertEqual(run([]), 0)
            request['builds'][0]['url'] += '0'
            request_path.write_text(json.dumps(request))
            self.assertEqual(run([result('noble', False), result('resolute', False)]), 2)


if __name__ == '__main__':
    unittest.main()

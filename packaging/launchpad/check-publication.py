#!/usr/bin/env python3
"""Check requested Launchpad builds through binary publication and APT indexes."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import gzip
import json
import os
from pathlib import Path
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen


FAILED = {'Failed to build', 'Failed to upload', 'Dependency wait',
          'Chroot problem', 'Cancelled', 'Failed', 'Build for superseded Source'}


def fetch(url, missing_ok=False):
    for attempt in range(3):
        try:
            request = Request(url, headers={'User-Agent': 'amule-ppa-publication-monitor',
                                            'Cache-Control': 'no-cache'})
            with urlopen(request, timeout=40) as response:
                return response.read()
        except HTTPError as error:
            if missing_ok and error.code == 404:
                return None
            if error.code < 500 and error.code != 429:
                raise
            if attempt == 2:
                raise
        except (URLError, TimeoutError):
            if attempt == 2:
                raise
        time.sleep(2 ** attempt)


def api(url, **params):
    if params:
        url += '?' + urlencode(params)
    return json.loads(fetch(url))


def entries(url, **params):
    while url:
        page = api(url, **params)
        yield from page['entries']
        url, params = page.get('next_collection_link'), {}


def api_url(url):
    path = urlsplit(url).path
    if path.startswith('/api/devel/'):
        return 'https://launchpad.net' + path
    if urlsplit(url).hostname == 'api.launchpad.net':
        return 'https://launchpad.net/api' + path
    return 'https://launchpad.net/api/devel' + path


def package_versions(data):
    """Read Debian control paragraphs, keeping version paired with its package."""
    versions = set()
    for paragraph in data.decode().split('\n\n'):
        fields = dict(line.split(': ', 1) for line in paragraph.splitlines()
                      if ': ' in line and not line.startswith(' '))
        if fields.get('Package') == 'amule-weekly' and fields.get('Architecture') in ('amd64', 'all'):
            versions.add(fields['Version'])
    return versions


def check_target(target, archive):
    result = {'series': target['series'], 'recipe_build': target['url'],
              'published': False, 'binary_builds': []}
    try:
        version = target.get('version')
        if version:
            result['recipe_state'] = 'Manual source upload'
        else:
            build = api(api_url(target['url']))
            result['recipe_state'] = build['buildstate']
            result['build_log'] = build.get('build_log_url')
            result['upload_log'] = build.get('upload_log_url')
            if build['buildstate'] in FAILED:
                result['error'] = 'Recipe build: ' + build['buildstate']
                return result
            log_url = build.get('build_log_url')
            if not log_url:
                result['stage'] = 'Waiting for source build'
                return result
            log = fetch(log_url)
            if log.startswith(b'\x1f\x8b'):
                log = gzip.decompress(log)
            versions = re.findall(rb'^dpkg-buildpackage: info: source version (\S+)',
                                  log, re.MULTILINE)
            if not versions:
                result['stage'] = 'Waiting for source package version in build log'
                return result
            version = versions[-1].decode()
        result['version'] = version
        sources = list(entries(api_url(archive), **{
            'ws.op': 'getPublishedSources', 'source_name': 'amule-weekly',
            'exact_match': 'true', 'version': version,
            'distro_series': 'https://launchpad.net/api/devel/ubuntu/' + target['series']}))
        result['source_states'] = sorted({source['status'] for source in sources})
        result['stage'] = 'Waiting for source upload/publication'
        for source in sources:
            if (source['source_package_version'] != version
                    or not source['distro_series_link'].endswith('/' + target['series'])):
                continue
            result['stage'] = 'Source accepted; waiting for publication'
            for binary in entries(api_url(source['self_link']), **{'ws.op': 'getBuilds'}):
                result['binary_builds'].append({
                    'url': binary['web_link'], 'state': binary['buildstate'],
                    'log': binary.get('build_log_url'),
                    'architecture': binary['arch_tag']})
            if result['binary_builds']:
                result['stage'] = 'Waiting for binary builds and publication'
            if source['status'] != 'Published':
                continue
            result['stage'] = 'Waiting for amd64 binary publication'
            binaries = entries(api_url(source['self_link']),
                               **{'ws.op': 'getPublishedBinaries'})
            published = any(binary['binary_package_name'] == 'amule-weekly'
                            and binary['binary_package_version'] == version
                            and binary['status'] == 'Published'
                            and binary['distro_arch_series_link'].endswith('/amd64')
                            for binary in binaries)
            if not published:
                continue
            # API publication precedes the actual APT publisher; require both.
            archive_path = urlsplit(archive).path.split('/')
            owner, ppa = archive_path[1].lstrip('~'), archive_path[-1]
            index = (f'https://ppa.launchpadcontent.net/{owner}/{ppa}/ubuntu/dists/'
                     f'{target["series"]}/main/binary-amd64/Packages.gz')
            result['apt_index'] = index
            result['stage'] = 'Waiting for APT index'
            data = fetch(index, missing_ok=True)
            if data is not None and version in package_versions(gzip.decompress(data)):
                result['published'] = True
                result['stage'] = 'Published in PPA and APT index'
        failures = [b for b in result['binary_builds'] if b['state'] in FAILED]
        if failures and not result['published']:
            result['error'] = 'Binary build: ' + ', '.join(b['state'] for b in failures)
    except Exception as error:
        result['error'] = f'{type(error).__name__}: {error}'
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request', type=Path, default=Path('status/last-request.json'))
    parser.add_argument('--status', type=Path, default=Path('status/publication.json'))
    args = parser.parse_args()
    request = json.loads(args.request.read_text())
    previous = json.loads(args.status.read_text()) if args.status.exists() else {}
    # Compare actual build URLs as well as timestamp so a replacement is monitored.
    identity = {key: request[key] for key in ('requested_at', 'archive', 'builds')}
    if previous.get('request') == identity and previous.get('complete'):
        print('All requested versions are already verified in the PPA APT indexes.')
        return 0
    if {build['series'] for build in request['builds']} != {'noble', 'resolute', 'stonking'}:
        raise ValueError('The request must include noble, resolute, and stonking')
    with ThreadPoolExecutor(max_workers=2) as pool:
        builds = list(pool.map(lambda target: check_target(target, request['archive']),
                               request['builds']))
    result = {'request': identity, 'complete': all(b['published'] for b in builds),
              'builds': builds}
    old = {k: v for k, v in previous.items() if k != 'updated_at'}
    if result != old:
        result['updated_at'] = datetime.now(timezone.utc).isoformat()
        args.status.parent.mkdir(parents=True, exist_ok=True)
        args.status.write_text(json.dumps(result, indent=2) + '\n')
    lines = ['## aMule PPA publication', '',
             '| Ubuntu | Source build/upload | Version | Publication |',
             '| --- | --- | --- | --- |']
    for build in builds:
        message = build.get('error', build.get('stage', 'Pending'))
        lines.append(f'| {build["series"]} | [{build.get("recipe_state", "Unknown")}]'
                     f'({build["recipe_build"]}) | {build.get("version", "Pending")} | {message} |')
        for binary in build['binary_builds']:
            lines.append(f'\nBinary build: [{binary["architecture"]}: {binary["state"]}]({binary["url"]})')
        if build.get('error'):
            # One-line annotations cannot inject additional workflow commands.
            error = build['error'].replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')
            print(f'::error title={build["series"]} publication check::{error}')
    if result['complete']:
        lines.extend(['', 'All packages are available. Network polling stops until the next build request.'])
    summary = '\n'.join(lines) + '\n'
    print(summary)
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as output:
            output.write(summary)
    return int(any('error' in build for build in builds))


if __name__ == '__main__':
    raise SystemExit(main())

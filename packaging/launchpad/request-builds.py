#!/usr/bin/env python3
"""Request Launchpad recipe builds using an authorized OAuth credentials file."""

import argparse
import configparser
from datetime import datetime, timezone
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--owner', required=True)
    parser.add_argument('--ppa', default='amule-weekly')
    parser.add_argument('--recipe', default='amule-weekly')
    parser.add_argument('--series', nargs='+', default=['noble', 'resolute', 'stonking'])
    parser.add_argument('--credentials', type=Path, required=True)
    parser.add_argument('--authorize', action='store_true',
                        help='authorize a new OAuth token in the browser')
    parser.add_argument('--dry-run', action='store_true',
                        help='check recipe and targets without requesting builds')
    parser.add_argument('--request-record', type=Path,
                        help='write public build request URLs to a JSON file')
    args = parser.parse_args()

    if not args.authorize:
        credentials = configparser.ConfigParser()
        try:
            credentials.read_string(args.credentials.read_text())
            valid = credentials.has_section('1') and all(
                credentials.has_option('1', field)
                for field in ['consumer_key', 'consumer_secret',
                              'access_token', 'access_secret'])
        except (OSError, configparser.Error):
            valid = False
        if not valid:
            parser.error('Use a launchpadlib OAuth credentials file. To create '
                         'one, use --authorize with a NEW credentials path.')
    elif args.credentials.exists():
        parser.error('--authorize requires a new credentials path')

    from launchpadlib.launchpad import Launchpad

    lp = Launchpad.login_with(
        'amule-weekly-builds', 'production', version='devel', timeout=60,
        credentials_file=str(args.credentials),
        allow_access_levels=['WRITE_PUBLIC'])
    owner = lp.people[args.owner.lstrip('~')]
    archive = owner.getPPAByName(name=args.ppa)
    recipe = owner.getRecipe(name=args.recipe)
    if recipe.build_daily:
        parser.error('Disable Build daily on the recipe before weekly scheduling')
    targets = [lp.distributions['ubuntu'].getSeries(name_or_version=name)
               for name in args.series]
    if any(series is None for series in targets):
        parser.error('One or more Ubuntu series were not found')
    for series in targets:
        print(f'{recipe.web_link} -> {archive.web_link} ({series.name})')
    if args.dry_run:
        return
    builds = []
    for series in targets:
        build = recipe.requestBuild(archive=archive, distroseries=series,
                                    pocket='Release')
        print(f'Requested: {build.web_link}')
        builds.append({'series': series.name, 'url': build.web_link})
    if args.request_record:
        args.request_record.parent.mkdir(parents=True, exist_ok=True)
        args.request_record.write_text(json.dumps({
            'requested_at': datetime.now(timezone.utc).isoformat(),
            'recipe': recipe.web_link,
            'archive': archive.web_link,
            'builds': builds,
        }, indent=2) + '\n')


if __name__ == '__main__':
    main()

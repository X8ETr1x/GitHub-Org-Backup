#!/usr/bin/python3
# -*- coding: utf-8 -*-

__author__ = 'X8ETR1x'
__copyright__ = 'Copyright 2026, X8ETr1x'
__credits__ = ['X8ETr1x']
__date__ = '2026-09-16'
__email__ = 'codestuff@thetrixster.com'
__license__ = 'GPL-3.0'
__maintainer__ = 'X8ETr1x'
__status__ = 'Production'
__version__ = '1.0.0'

from argparse import ArgumentParser
from sys import exit
from time import sleep

from src.services.gh_api import GitHub


def main():
    """
    Initiates a GitHub organization backup and saves the archive to the specified location.
    Note: GitHub does not currently support fine-grained access token for these API endpoints. As a result, classic
    tokens must be used with repository and organization admin permissions.
    https://docs.github.com/en/migrations/using-ghe-migrator/exporting-migration-data-from-githubcom
    """
    # Get CLI arguments
    parser = ArgumentParser(description='Back up a GitHub organization.')
    parser.add_argument('-c',
                        '--configs-file',
                        type=str,
                        help='Absolute path to configs file.',
                        required=True)
    parser.add_argument('-s',
                        '--secrets-file',
                        type=str,
                        help='Absolute path to secrets file.',
                        required=True)
    args = parser.parse_args()

    gh = GitHub(config_path=args.configs_file, secrets_path=args.secrets_file)

    try:
        gh.start_gh_migration()
    except RuntimeError as error:
        print('Runtime error caught: ', error)
        exit(1)

    migration_finished = False

    while not migration_finished:
        migration_status = gh.check_gh_migration()

        if migration_status == 'pending':
            print('Migration ', gh.migration_id, ' pending. Waiting fifteen seconds...')
            sleep(15)
            migration_finished = False
        elif migration_status == 'exporting':
            print('Migration ', gh.migration_id, ' in process. Waiting fifteen seconds...')
            sleep(15)
            migration_finished = False
        elif migration_status == 'exported':
            print('Migration ', gh.migration_id, ' completed.')

            try:
                gh.get_gh_migration_files()
            except RuntimeError as error:
                gh.unlock_gh_repos()
                print('Runtime error caught: ', error)
                exit(1)

            gh.unlock_gh_repos()
            migration_finished = True
        else:
            print('Unexpected migration status: ', migration_status)
            gh.unlock_gh_repos()
            migration_finished = True

    exit(0)

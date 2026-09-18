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

from datetime import datetime
from json import dumps
from locale import getencoding
from os import mkdir, path

import requests.exceptions
from dotenv import dotenv_values
from magic import Magic
from requests import post, get, delete


class GitHub:
    def __init__(self, config_path: str, secrets_path: str):
        """
        Initializes a class object with all configuration parameters and GitHub organization information.
        The class uses dotenv for data. Since dotenv_values does not check for file existence or access, we
        try opening the environment files to compensate.
        :param config_path: The Unix path to the main configuration file.
        :param secrets_path: The Unix path to the GitHub secrets file.
        """
        self.org_repo_list = []
        self.migration_id = None
        encoding = getencoding()

        try:
            with open(config_path, mode='r', encoding=encoding, errors='strict') as file:
                gh_config: dict = dotenv_values(config_path)
                print('Config file ', config_path, ' loaded.')
                file.close()

            with open(secrets_path, mode='r', encoding=encoding, errors='strict') as file:
                gh_secrets: dict = dotenv_values(secrets_path)
                print('Secrets file ', secrets_path, ' loaded.')
                file.close()

        except OSError as error:
            raise OSError('Error opening file ', error.filename, ': ', error.strerror)
        except ValueError as error:
            raise ValueError('Error opening file ', file.name, ': ', error)

        # Copy the settings values
        try:
            self.gh_host = gh_config['GH_API_HOST']
            self.gh_api_ver = gh_config['GH_API_VER']
            self.gh_content_type = gh_config['GH_CONTENT_TYPE']
            self.gh_org = gh_config['GH_ORG']
            self.backup_dir = gh_config['BU_DIR']
            self.gh_token = gh_secrets['GH_TOKEN']
        except KeyError as error:
            raise KeyError(f"Required key missing: {error}")

        if not path.exists(self.backup_dir):
            print('Backup directory ', self.backup_dir, ' not found. Creating...')
            try:
                mkdir(self.backup_dir)
            except PermissionError as error:
                raise RuntimeError('Unable to create backup directory: ', error)

        print('Github API host: ', self.gh_host)
        print('GitHub API version: ', self.gh_api_ver)
        print('Github content type: ', self.gh_content_type)
        print('Github organization: ', self.gh_org)
        print('Backup directory: ', self.backup_dir)
        print('Github token imported.')

    @staticmethod
    def _request_url(request_type, url, headers, data=None):
        try:
            if request_type == 'get':
                r = get(url=url, headers=headers)
                r.raise_for_status()
            elif request_type == 'post':
                r = post(url=url, headers=headers, data=dumps(data))
                r.raise_for_status()
            elif request_type == 'delete':
                r = delete(url=url, headers=headers)
                r.raise_for_status()
            else:
                raise RuntimeError(f"Unsupported HTTP method: {request_type}")
        except requests.ConnectionError as error:
            raise RuntimeError(f"Unable to connect to {url}: {error}")
        except requests.exceptions.MissingSchema as error:
            raise RuntimeError(f"Invalid URI scheme for {url}: {error}")
        except requests.ReadTimeout as error:
            raise RuntimeError(f"No data returned from {url}: {error}")
        except requests.RequestException as error:
            raise RuntimeError(f"Unexpected error accessing {url}: {error}")

        return r

    def _get_gh_repo_list(self):
        """
        Retrieves a list of repositories in a GitHub organization and stores them in a list.
        """
        # TODO: add pagination.

        url = f"https://{self.gh_host}/orgs/{self.gh_org}/repos?per_page=100"
        headers = {'Accept': self.gh_content_type,
                   'Authorization': f"Bearer {self.gh_token}",
                   'X-GitHub-Api-Version': self.gh_api_ver}

        print('Retrieving repositories from ', url, '...')
        try:
            r = self._request_url(request_type='get', url=url, headers=headers)
        except requests.HTTPError as error:
            raise RuntimeError(f"Problem retrieving repository list from {url}: {error}")

        if not r.status_code == 200:
            raise RuntimeError(
                f"Unexpected status code retrieving repository list from {r.url}: {r.status_code} {r.reason}")

        # Check for a valid encoding type:
        if r.apparent_encoding == 'ascii':
            # Add the repository names to a list:
            try:
                for line in r.json():
                    print('Adding repository ', line['name'], '...')
                    self.org_repo_list.append(line['name'])
            except requests.JSONDecodeError as error:
                RuntimeError(f"Error parsing JSON from {r.url}: {error}")
        else:
            raise RuntimeError(f"Unsupported data type for repository list from {url}: {r.apparent_encoding}")

    def start_gh_migration(self):
        """
        Starts a GitHub organization migration for backup.
        https://docs.github.com/en/rest/migrations/orgs?apiVersion=2026-03-10#start-an-organization-migration
        """
        self._get_gh_repo_list()

        # The API requires a format of ORG/REPO in the list:
        repo_list_formatted = []

        for repo in self.org_repo_list:
            repo_list_formatted.append(f"{self.gh_org}/{repo}")

        url = f"https://{self.gh_host}/orgs/{self.gh_org}/migrations"
        headers = {'Accept': self.gh_content_type,
                   'Authorization': f"Bearer {self.gh_token}",
                   'X-GitHub-Api-Version': self.gh_api_ver}
        payload = {'lock_repositories': True,
                   'exclude_attachments': True,
                   'exclude_releases': True,
                   'repositories': repo_list_formatted}

        print('Starting GitHub migration...')
        try:
            r = self._request_url(request_type='post', url=url, headers=headers, data=payload)
        except requests.HTTPError as error:
            raise RuntimeError(f"Problem initiating migration with {url}: {error}")

        if r.status_code == 201:
            try:
                self.migration_id = r.json()['id']
                print('Migration ID ', self.migration_id, ' initiated.')
            except requests.JSONDecodeError as error:
                RuntimeError(f"Error parsing JSON from {r.url}: {error}")
        else:
            self.unlock_gh_repos()
            raise RuntimeError(f"Unexpected HTTP status code starting migration: {r.status_code}, {r.content}")

    def check_gh_migration(self):
        """
        Queries for the status of an existing GitHub organization migration task.
        https://docs.github.com/en/rest/migrations/orgs?apiVersion=2026-03-10#get-an-organization-migration-status
        :return: The current status of the migration task.
        """
        url = f"https://{self.gh_host}/orgs/{self.gh_org}/migrations/{self.migration_id}"
        headers = {'Accept': self.gh_content_type,
                   'Authorization': f"Bearer {self.gh_token}",
                   'X-GitHub-Api-Version': self.gh_api_ver}

        print('Checking status of migration ID ', self.migration_id, '...')
        try:
            r = self._request_url(request_type='get', url=url, headers=headers)
        except requests.HTTPError as error:
            self.unlock_gh_repos()
            raise RuntimeError(f"Problem retrieving migration status from {url}: {error}")

        if r.status_code == 200:
            migration_status = r.json()['state']

            if migration_status == 'pending' or migration_status == 'exporting' or migration_status == 'exported':
                return migration_status
            elif migration_status == 'failed':
                self.unlock_gh_repos()
                raise RuntimeError(f"Migration {self.migration_id} failed.")
            else:
                self.unlock_gh_repos()
                raise RuntimeError(f"Unexpected migration status for {self.migration_id}: {migration_status}")
        else:
            self.unlock_gh_repos()
            raise RuntimeError(f"Unexpected HTTP status code checking migration: {r.status_code}, {r.content}")

    def get_gh_migration_files(self):
        """
        Downloads an archive from a successful migration.
        When attempting to delete completed migrations, we ignore failures as GitHub will automatically delete them in
        seven days time.
        https://docs.github.com/en/rest/migrations/orgs?apiVersion=2026-03-10#get-an-organization-migration-status
        """
        url = f"https://{self.gh_host}/orgs/{self.gh_org}/migrations/{self.migration_id}/archive"
        headers = {'Accept': self.gh_content_type,
                   'Authorization': f"Bearer {self.gh_token}",
                   'X-GitHub-Api-Version': self.gh_api_ver}

        print('Retrieving archive status for migration ID ', self.migration_id, '...')
        try:
            r = self._request_url(request_type='get', url=url, headers=headers)
        except requests.HTTPError as error:
            self.unlock_gh_repos()
            raise RuntimeError(f"Problem retrieving file archive from {url}: {error}")

        if r.status_code == 200:
            print('Backup found. Downloading archive files...')
            backup_file = f"{self.backup_dir}/{self.gh_org}-{datetime.now().strftime("%Y-%m-%d-%H-%M")}.tar.gz"

            try:
                with open(backup_file, 'wb') as file:
                    file.write(r.content)
                    file.close()
            except PermissionError as error:
                self.unlock_gh_repos()
                raise RuntimeError(f"Could not save archive file: {error}")

            print('Deleting remote files for migration ID ', self.migration_id, '...')
            try:
                r = self._request_url(request_type='delete', url=url, headers=headers)
            except requests.HTTPError:
                pass

            if r.status_code == 204:
                print('Migration files for ID ', self.migration_id, ' deleted from GitHub.')
            else:
                print('Migration files for ID ', self.migration_id, ' were not deleted.')

            print('Validating MIME type for file ', backup_file, '...')
            mime_obj = Magic(mime=True)
            try:
                file_validate = mime_obj.from_file(backup_file)
            except FileNotFoundError as error:
                self.unlock_gh_repos()
                raise RuntimeError(f"Unable to determine MIME type for {backup_file}: {error}")

            if file_validate == 'application/gzip':
                print('File ', backup_file, ' successfully downloaded.')
            else:
                self.unlock_gh_repos()
                raise RuntimeError(f"File {backup_file} is not a valid gzip file.")
        else:
            self.unlock_gh_repos()
            raise RuntimeError(f"Unexpected HTTP status code retrieving file archive from {r.status_code}: {r.content}")

    def unlock_gh_repos(self):
        """
        Unlocks a repository after a migration is attempted.
        https://docs.github.com/en/rest/migrations/orgs?apiVersion=2026-03-10#get-an-organization-migration-status
        """
        headers = {'Accept': self.gh_content_type,
                   'Authorization': f"Bearer {self.gh_token}",
                   'X-GitHub-Api-Version': self.gh_api_ver}

        for repo in self.org_repo_list:
            url = f"https://{self.gh_host}/orgs/{self.gh_org}/migrations/{self.migration_id}/repos/{repo}/lock"

            try:
                r = self._request_url(request_type='delete', url=url, headers=headers)

                if r.status_code == 204:
                    print('Repo ', repo, ' unlocked.')
                else:
                    print('Unexpected HTTP status code deleting repository lock: ', r.status_code, ', ', r.content)

            except requests.HTTPError as error:
                print('Problem deleting lock file for repository ', url, ': ', error.strerror)

# GitHub Organization Backup

A script that utilizes the GitHub organization migration API endpoints to back up an entire organization.

GitHub offers a method to migrate an organization to GitHub Enterprise. It just so happens that part one of that process is to create a full organization-wide backup. Lucky for us.

All data is pulled into class variables and is **not** added to the system's environment variables. The code will pull key/value settings from two files:
- `.env.config`: contains configuration settings relating to connecting to the GitHub API and where to save the archives.
- `.env.secrets`: contains the GitHub personal access token.

Unfortunately, GitHub does not yet support fine-grained access tokens for this, so you'll need the following:
- A legacy personal access token with repo:full control and admin:org.
- Owner permissions in the organization.

If you intend to use this for automation, I highly advise regular rotation of that secret and to make sure that the secrets file permissions are set to 600.

I recommend compiling and deploying a binary instead of running as a script, though both will work. Otherwise, a virtual environment or Docker container will be required in most production cases. A binary is provided as a release for convenience, but a blind trust test is never advised.

## Configuration Files

### Configuration

- GH_API_HOST: the current URL host for the GitHub API (api.github.com).
- GH_API_VER: the current API version (2026-03-10).
- GH_CONTENT_TYPE: the recommended content type for the migrations endpoints (application/vnd.github+json).
- GH_ORG: the GitHub organization name.
- BU_DIR: the absolute path of the backup file output directory.

```
GH_API_HOST="api.github.com"
GH_API_VER="2026-03-10"
GH_CONTENT_TYPE="application/vnd.github+json"
GH_ORG="A-Totally-Fake-Org-Name"
BU_DIR="/home/me/Downloads/gh_stuffs"
```

### Secrets

- GH_TOKEN: the classic personal access token.

```
GH_TOKEN="shhhhh_itsasecretbutlikealotlonger"
```

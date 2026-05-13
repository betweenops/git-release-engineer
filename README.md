# GitLab AI Release Engineer

GitLab AI Release Engineer is a release-operations tool for teams that manage releases through GitLab and a manifest-driven release definition repository.

It turns release manifests and live GitLab state into actionable release views:

- normalized release scope from `release.yaml`
- manifest-only readiness reports
- live readiness reports backed by GitLab epics, work items, branches, and pipelines
- a local interactive dashboard for release leads and operators

## What It Does

- Loads a release definition from an external repository
- Resolves release variables from `release.vars.env`
- Inspects GitLab release epics, stage issues, child work items, release branches, and latest pipelines
- Produces structured readiness output with blockers, risks, and summary counts
- Serves a browser dashboard for refreshable release visibility

## Requirements

- Python `3.11+`
- Access to the external release-definition repository
- A GitLab token with read access to the projects involved in the release

## Configuration

Use environment variables or a local `.env` / `.env.local` file. Local env files are loaded automatically and are ignored by git.

Required for manifest-driven commands:

- `RELEASE_DEFINITION_ROOT`

Required for live GitLab commands:

- `GITLAB_URL`
- `GITLAB_TOKEN`

Optional overrides:

- `RELEASE_MANIFEST_PATH`
- `RELEASE_VARS_FILE`

Example:

```bash
export RELEASE_DEFINITION_ROOT=/path/to/release-definition-repo
export GITLAB_URL=https://gitlab.example.com
export GITLAB_TOKEN=replace-with-read-only-or-minimum-scope-token
```

`GITLAB_URL` must be the GitLab server base URL only. Do not use a group, project, issue, or work-item URL.

## CLI

If `RELEASE_DEFINITION_ROOT` is set, the manifest path does not need to be passed explicitly.

```bash
PYTHONPATH=src python3 -m gitlab_ai_release_engineer.cli inspect-manifest
PYTHONPATH=src python3 -m gitlab_ai_release_engineer.cli report
PYTHONPATH=src python3 -m gitlab_ai_release_engineer.cli report-live
PYTHONPATH=src python3 -m gitlab_ai_release_engineer.cli dashboard
```

You can still pass paths directly:

```bash
PYTHONPATH=src python3 -m gitlab_ai_release_engineer.cli report \
  /path/to/release-definition-repo/release.yaml \
  --vars-file /path/to/release-definition-repo/release.vars.env
```

## Commands

- `inspect-manifest`
  Loads and normalizes the release manifest, then emits JSON describing the release scope.

- `report`
  Generates a deterministic manifest-only readiness report without contacting GitLab.

- `report-live`
  Generates a live readiness report using GitLab epics, work items, release branches, and latest pipelines.

- `dashboard`
  Starts a local dashboard server with both manifest and live GitLab views.

## Dashboard

Start it with:

```bash
PYTHONPATH=src python3 -m gitlab_ai_release_engineer.cli dashboard --host 127.0.0.1 --port 8000
```

Then open:

```text
http://127.0.0.1:8000
```

The dashboard includes:

- release status, score, and summary cards
- blockers and risks
- stage-by-stage open work with assignees and links
- repository health with pipeline and branch visibility
- manual refresh controls
- configurable live auto-refresh

Available endpoints:

- `/`
- `/api/report`
- `/api/report-live`
- `/api/health`

## Notes

- `report` works with manifest data only.
- `report-live` and live dashboard refreshes require both `GITLAB_URL` and `GITLAB_TOKEN`.
- This repository does not store tokens. Keep them in shell env or local untracked env files.

# GitLab AI Release Engineer

GitLab AI Release Engineer is a proposed platform for helping engineering teams prepare, assess, and coordinate software releases using GitLab project data and LLM-driven analysis.

The goal is not to automate deployments blindly. The goal is to give release owners a faster, clearer picture of release readiness, risk, blockers, and communication tasks.

## Problem

Release coordination is usually fragmented across issues, merge requests, pipeline results, deployment notes, and team chat. Important signals are spread across systems, and release status often depends on manual interpretation.

This project aims to centralize that context and answer practical questions such as:

- Is this release ready?
- What is blocking it?
- Which merge requests or issues introduce the most risk?
- What changed since the last release?
- What should be communicated to stakeholders?

## Product Direction

This project is being designed around manifest-driven release workflows.

The current release-definition source lives in an external repository:

- `RELEASE_DEFINITION_ROOT`

That repository already defines:

- Release manifest structure
- Release epic and staged issue layout
- Included repositories
- Validation targets
- Acceptance criteria

This repository should not replace that definition layer in v1. It should consume or analyze it.

Initial focus:

- GitLab-first workflow support
- Release visibility built from an external manifest and its corresponding GitLab objects
- AI-assisted release summaries
- Release readiness and blocker detection
- Release note drafting
- Natural language queries over release-related project data

Possible later expansions:

- Slack or email delivery
- Multi-project release views
- Cross-system integrations beyond GitLab
- Deployment orchestration actions

## MVP

The first usable version should do a small number of things well:

1. Ingest release-relevant GitLab data for a release scope defined by an external manifest.
2. Summarize open issues, merge requests, failed pipelines, and notable risks.
3. Produce a release readiness report with clear reasons behind the score or status.
4. Draft release notes from merged work items.
5. Let a user ask targeted questions such as "what is blocking this release?"

If the MVP cannot answer those five jobs reliably, the project is still in discovery rather than product mode.

## Core Capabilities

- Parse or ingest release definitions from a manifest-driven release source
- GitLab API integration
- Release readiness analysis
- Blocker and risk identification
- CI/CD pipeline summarization
- AI-generated release notes
- Natural language status queries
- Traceable explanations for AI-generated conclusions

## Users

- Release engineers
- Engineering managers
- Platform teams
- Technical program managers

## Non-Goals For v1

- Fully autonomous production deployments
- Broad multi-provider support from day one
- Complex agent swarms without a clear operational need
- Replacing GitLab as the source of truth

## Architecture Direction

The technology stack is intentionally not locked yet. The system still needs to prove the workflow before optimizing for framework choice.

Logical building blocks:

- Manifest ingestion layer for external release definitions
- Data ingestion layer for GitLab project, issue, merge request, and pipeline data
- Analysis layer for readiness scoring, summarization, and risk detection
- LLM orchestration layer for question answering and report generation
- API or service layer for exposing reports and workflows
- UI or CLI layer for interacting with the system
- Persistence layer for cached project data, release snapshots, and generated outputs

## Suggested Build Order

1. Define the release readiness model against the existing manifest-driven workflow.
2. Parse `release.yaml` and normalize release scope, repos, stages, and validation targets.
3. Build GitLab data ingestion for the objects referenced by that scope.
4. Generate a deterministic release report without AI.
5. Add LLM-generated summaries on top of structured report data.
6. Add a simple interface, likely CLI first and dashboard second.

This sequence keeps the project grounded. If the structured report is weak, adding agents will only make the output sound confident rather than useful.

## Example Workflows

- "Generate release notes for version 1.2.0"
- "Identify unresolved blockers before deployment"
- "Summarize CI/CD failures impacting release readiness"
- "Explain why this release is marked high risk"

## Open Product Questions

- What defines release readiness in this system beyond the existing release epic checklist?
- Is the first unit of analysis the release epic, the staged issues, or the manifest as a whole?
- Should the first interface be a CLI, API, or web dashboard if operators already use the manifest workflow?
- How much human review is required before generated outputs are trusted?
- Will the product stay GitLab-first or become SCM-agnostic later?

## Status

Current phase: problem definition and MVP scoping.

## Usage

The CLI is read-only. It loads a release manifest, normalizes the release scope, and can optionally query GitLab for live release state.

### Setup

Copy `.env.example` into your local shell environment or a local `.env` file that is not committed.

Required variables:

- `RELEASE_DEFINITION_ROOT`: local path to the release-definition repository
- `GITLAB_TOKEN`: required only for `report-live`
- `GITLAB_URL`: required only for `report-live`

Optional variables:

- `RELEASE_MANIFEST_PATH`: explicit manifest path, overrides `RELEASE_DEFINITION_ROOT/release.yaml`
- `RELEASE_VARS_FILE`: explicit vars file path, overrides `RELEASE_DEFINITION_ROOT/release.vars.env`

Example shell setup:

```bash
export RELEASE_DEFINITION_ROOT=/path/to/release-definition-repo
export GITLAB_URL=https://gitlab.example.com
export GITLAB_TOKEN=replace-with-read-only-or-minimum-scope-token
```

You can also create a local `.env` or `.env.local` in this repository instead of exporting variables manually. The CLI loads those files automatically and does not override variables already set in your shell.

### Commands

If `RELEASE_DEFINITION_ROOT` is set, you do not need to pass the manifest path explicitly.

```bash
PYTHONPATH=src python3 -m gitlab_ai_release_engineer.cli inspect-manifest

PYTHONPATH=src python3 -m gitlab_ai_release_engineer.cli report

PYTHONPATH=src python3 -m gitlab_ai_release_engineer.cli report-live
```

You can still pass paths explicitly when needed:

```bash
PYTHONPATH=src python3 -m gitlab_ai_release_engineer.cli report \
  /path/to/release-definition-repo/release.yaml \
  --vars-file /path/to/release-definition-repo/release.vars.env
```

### What Each Command Does

- `inspect-manifest`: shows the normalized release scope derived from the manifest
- `report`: generates a deterministic manifest-only readiness report
- `report-live`: performs read-only GitLab queries and reports epic, stage, task, branch, and pipeline state

### Sensitive Data

- Do not commit GitLab tokens into this repository.
- Use environment variables or a local untracked `.env` file for tokens and machine-specific paths.
- This repository now ignores `.env` and `.env.local` by default.

# EdgeOps Integration Notes

This project is intended to support release operations for EdgeOps.

The current release-definition repository is:

- `EDGE_RELEASE_ROOT`

## What Already Exists

The `edge-release` repository already provides a useful definition layer:

- `release.yaml`: release manifest with repos, artifact sets, validation targets, and staged work items
- `scripts/release_manifest.py`: manifest parser, planner, and GitLab object creator
- `README.md`: operational usage for validation, planning, and creation

## Important Modeling Implications

The release is already structured around:

- A single release epic
- Three top-level stage issues
- Child tasks linked under each stage
- Explicit repository inventory
- Explicit validation targets
- Explicit acceptance criteria

That means this project does not need to invent release structure from scratch for v1.

## Recommended v1 Role For This Project

This repository should act as the analysis and intelligence layer on top of `edge-release`.

Recommended responsibilities:

- Load release scope from the manifest or generated GitLab objects
- Inspect the state of the release epic, stage issues, and child tasks
- Inspect repository health for included EdgeOps repos
- Summarize blockers, risk, and readiness
- Draft release notes and operator-facing status updates

Responsibilities that should remain in `edge-release` for now:

- Defining the release manifest schema
- Creating release epics and issues
- Templating stage and task structure

## Strong Signals Available In The Current Manifest

The current manifest already exposes useful readiness inputs:

- Included repositories and release branches
- Validation targets such as EOD and Microlab EdgeLine
- Stage sequencing through `depends_on`
- Acceptance criteria in work item descriptions
- Artifact sets such as Iron Bank and ISO outputs

These are better initial inputs than generic milestone-based heuristics.

## Recommended Unit Of Analysis

For EdgeOps, the first unit of analysis should be the release manifest plus the GitLab epic it creates.

That is stronger than using a bare milestone because:

- The manifest explicitly defines the release shape
- The release epic is the operational object teams will review
- The staged issues represent the actual workflow

## Suggested First Build Slice

Build a CLI that:

1. Loads `release.yaml` and `release.vars.env`
2. Resolves the release title, epic title, stage issues, repositories, and validation targets
3. Queries GitLab for the corresponding epic and issues
4. Produces a deterministic readiness report
5. Optionally generates an LLM summary from that report

## Initial Readiness Inputs For EdgeOps

- Are all three top-level stages present?
- Which stage is currently incomplete?
- Are any child tasks still open?
- Are any required release branches missing?
- Are pipelines failing on included repos?
- Are validation tasks incomplete for connected or airgap targets?
- Are release acceptance criteria still unchecked?

## Design Constraint

Do not tightly couple v1 to the implementation details of `scripts/release_manifest.py`.

It is fine to reuse the manifest shape and operational concepts, but this project should own its own read-only ingestion and analysis path.

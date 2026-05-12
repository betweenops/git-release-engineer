# Release Readiness Model

This document defines the first pass of the release-readiness model for GitLab AI Release Engineer.

The purpose of the model is to produce a structured, explainable release assessment before any LLM summarization is applied.

## Unit Of Analysis

For EdgeOps, the initial unit of analysis should be the `edge-release` manifest plus the GitLab release epic and staged issues it creates.

Why this is stronger than milestone-first:

- The manifest already defines release scope explicitly.
- The release epic is the operational object humans review.
- The staged issues represent the actual release workflow.
- Validation targets and artifact sets are already modeled in the manifest.

## Output

The system should generate a report with:

- Overall readiness status
- Numerical readiness score
- Blockers
- Risks
- Pipeline health summary
- Scope summary
- Draft release notes input set

## Readiness Status

The first version should use four statuses:

- `green`: ready for release
- `yellow`: mostly ready, some risks require review
- `orange`: not ready, important gaps exist
- `red`: blocked

## Scoring Dimensions

The score should be derived from a small number of explainable dimensions:

1. Scope completion
2. Open blocker count
3. Merge request risk
4. Pipeline health
5. Deployment confidence signals

Each dimension should be independently computed and attached to the report.

## Suggested Initial Rules

These are deterministic first-pass rules, not final policy.

### Scope completion

- Count stage issues and child tasks by status.
- Penalize unresolved issues marked `blocking`, `critical`, or equivalent labels.
- Penalize missing stage issues or child tasks expected from the manifest.
- Penalize issues without clear ownership if they are in the release scope.

### Open blocker count

- Any open item with labels such as `blocker`, `release-blocker`, or `sev1` should heavily reduce readiness.
- Any unresolved dependency issue should be listed separately as a blocker.
- Any incomplete Go/No-Go criterion should be considered a blocker candidate.

### Merge request risk

- Penalize large open merge requests near release time.
- Penalize recently merged requests with failed or missing pipeline coverage.
- Penalize changes touching high-risk areas once those areas are defined.
- Penalize repo branches that are expected by the release manifest but do not exist.

### Pipeline health

- Penalize failed default-branch pipelines associated with release scope.
- Penalize missing required jobs.
- Penalize repeated flaky failures if they exceed a threshold.

### Deployment confidence signals

- Reward successful staging or pre-production deployments where available.
- Penalize missing verification evidence for high-risk releases.
- Penalize missing validation results for required EdgeOps targets such as connected and airgap flows.

## Blocker Criteria

The release should be considered blocked if any of the following is true:

- A release-blocking issue remains open.
- A required pipeline is failing.
- A required approval is missing.
- A critical merge request is still open.
- A required release stage is incomplete.
- A required validation target has not been exercised.

## Report Shape

The structured report should resemble:

```text
Release: 2026.05
Status: orange
Score: 61

Blockers:
- Stage 2 release-candidate validation is still incomplete
- edge-controller release branch exists but latest pipeline is failing

Risks:
- Airgap validation target has no recorded result
- 2 child tasks under Stage 3 have no assignee

Summary:
- 3 stage issues expected, 3 present
- 18 child tasks expected, 14 closed
- 6 repos included in release scope
- 1 required pipeline failing
```

## Why This Matters

The system should separate facts from generated language:

- Structured analysis determines the score and status.
- The LLM explains and summarizes the structured analysis.

That keeps the product auditable and reduces the risk of persuasive but weak output.

## Next Implementation Targets

1. Define the GitLab fields needed to analyze the release epic, stage issues, and child tasks.
2. Parse and normalize `edge-release` manifest fields into internal release scope objects.
3. Map GitLab labels and states into normalized internal categories.
4. Build the first deterministic readiness report generator.
5. Layer LLM summarization on top of the generated report.

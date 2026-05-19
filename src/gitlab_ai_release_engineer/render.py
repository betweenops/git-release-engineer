from __future__ import annotations

from typing import Any


def _esc(value: Any) -> str:
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _md_esc(value: Any) -> str:
    text = str(value)
    for ch in ("\\", "`", "*", "_", "[", "]", "<", ">", "|"):
        text = text.replace(ch, "\\" + ch)
    return text


def _status_class(status: str) -> str:
    return {
        "green": "green",
        "yellow": "yellow",
        "orange": "orange",
        "red": "red",
    }.get(status, "")


def _badge_class(value: str) -> str:
    if value in {"failed", "red"}:
        return "failed"
    if value == "missing":
        return "missing"
    if value in {"success", "passed", "closed"}:
        return "success"
    if value == "opened":
        return "opened"
    if value == "orange":
        return "orange"
    if value == "present":
        return "present"
    return ""


def _signal_class(pipeline_status: str) -> str:
    if pipeline_status == "failed":
        return "fill-bad"
    if pipeline_status == "missing":
        return "fill-warn"
    if pipeline_status in {"success", "passed"}:
        return "fill-good"
    return ""


_CSS = """
  :root {
    --ink: #e7fff6;
    --text: #d5e7e2;
    --muted: #94a7a3;
    --line: rgba(146, 231, 196, 0.14);
    --card: rgba(12, 24, 29, 0.9);
    --card-strong: rgba(14, 28, 34, 0.96);
    --accent: #3fd497;
    --accent-soft: #92e7c4;
    --warn: #f5c451;
    --bad: #ff7f72;
    --good: #3fd497;
    --shadow: 0 20px 50px rgba(0, 0, 0, 0.32);
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    font-family: "Space Grotesk", "Segoe UI", sans-serif;
    color: var(--text);
    background:
      radial-gradient(circle at top left, rgba(63, 212, 151, 0.18), transparent 22%),
      radial-gradient(circle at top right, rgba(24, 73, 58, 0.5), transparent 20%),
      linear-gradient(180deg, #060d10 0%, #091215 44%, #0a1519 100%);
  }
  a { color: var(--accent); text-decoration: none; }
  a:hover { text-decoration: underline; }
  .shell { max-width: 1320px; margin: 0 auto; padding: 28px 20px 48px; }
  .hero {
    background:
      linear-gradient(135deg, rgba(8, 18, 22, 0.94), rgba(9, 20, 25, 0.9)),
      radial-gradient(circle at top left, rgba(63, 212, 151, 0.24), transparent 35%);
    color: var(--ink);
    padding: 28px;
    border-radius: 24px;
    box-shadow: var(--shadow);
    border: 1px solid rgba(146, 231, 196, 0.18);
  }
  .title {
    font-size: clamp(1.8rem, 3.2vw, 3rem);
    line-height: 1.04;
    margin: 12px 0 0;
    letter-spacing: -0.03em;
  }
  .subtle { color: rgba(213, 231, 226, 0.78); margin-top: 10px; max-width: 56rem; }
  .hero-stats {
    margin-top: 24px;
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 14px;
  }
  .stat {
    background: rgba(255, 255, 255, 0.04);
    border-radius: 18px;
    padding: 16px;
    min-height: 108px;
    border: 1px solid rgba(146, 231, 196, 0.12);
  }
  .stat-label {
    display: block;
    font-size: 0.82rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: rgba(146, 231, 196, 0.72);
    margin-bottom: 8px;
  }
  .stat-value { font-size: 2rem; font-weight: 700; line-height: 1; }
  .stat-note { margin-top: 8px; color: rgba(213, 231, 226, 0.74); font-size: 0.92rem; }
  .status-pill {
    display: inline-flex;
    align-items: center;
    border-radius: 999px;
    padding: 8px 12px;
    font-size: 0.84rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(146, 231, 196, 0.18);
  }
  .status-pill.green { color: var(--accent-soft); }
  .status-pill.yellow { color: #ffe38f; }
  .status-pill.orange { color: #ffd29a; }
  .status-pill.red { color: #ffb5aa; }
  .main {
    margin-top: 22px;
    display: grid;
    grid-template-columns: 1.1fr 0.9fr;
    gap: 18px;
    align-items: start;
  }
  .panel {
    background: var(--card);
    border: 1px solid var(--line);
    border-radius: 22px;
    box-shadow: var(--shadow);
    overflow: hidden;
  }
  .panel-head {
    padding: 18px 20px 10px;
    border-bottom: 1px solid var(--line);
    background: linear-gradient(180deg, rgba(255, 255, 255, 0.02), transparent);
  }
  .panel-title { margin: 0; font-size: 1.1rem; letter-spacing: -0.02em; }
  .panel-sub { color: var(--muted); margin-top: 6px; font-size: 0.94rem; }
  .panel-body { padding: 18px 20px 22px; }
  .stack { display: grid; gap: 14px; }
  .item {
    border: 1px solid var(--line);
    border-radius: 16px;
    padding: 14px;
    background: var(--card-strong);
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.02);
  }
  .panel.stage-open { border-left: 3px solid rgba(63, 212, 151, 0.42); }
  .panel.stage-missing {
    border-left: 3px solid rgba(255, 127, 114, 0.62);
    box-shadow: 0 0 0 1px rgba(255, 127, 114, 0.08);
  }
  .item.repo-failed {
    border-color: rgba(255, 127, 114, 0.28);
    box-shadow: 0 0 0 1px rgba(255, 127, 114, 0.08);
  }
  .item.repo-missing {
    border-color: rgba(245, 196, 81, 0.22);
    box-shadow: 0 0 0 1px rgba(245, 196, 81, 0.06);
  }
  .item.repo-healthy { border-color: rgba(63, 212, 151, 0.2); }
  .item-title { font-weight: 700; margin: 0 0 6px; color: var(--ink); }
  .meta { color: var(--muted); font-size: 0.92rem; display: flex; gap: 12px; flex-wrap: wrap; }
  .repo-kicker {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 10px;
    margin-bottom: 8px;
    font-family: "Space Mono", "SFMono-Regular", monospace;
    font-size: 0.77rem;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    color: rgba(146, 231, 196, 0.68);
  }
  .badge-row { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 8px; }
  .badge {
    border-radius: 999px;
    padding: 5px 9px;
    font-size: 0.78rem;
    font-weight: 700;
    background: rgba(255, 255, 255, 0.06);
    color: #dceae5;
    border: 1px solid rgba(255, 255, 255, 0.05);
  }
  .badge.failed { background: rgba(255, 127, 114, 0.14); color: var(--bad); }
  .badge.missing { background: rgba(245, 196, 81, 0.14); color: var(--warn); }
  .badge.success { background: rgba(63, 212, 151, 0.14); color: var(--good); }
  .badge.opened { background: rgba(63, 212, 151, 0.12); color: var(--accent-soft); }
  .badge.orange { background: rgba(245, 196, 81, 0.12); color: var(--warn); }
  .badge.present { background: rgba(63, 212, 151, 0.1); color: var(--accent-soft); }
  .empty {
    padding: 14px;
    border-radius: 14px;
    background: rgba(255, 255, 255, 0.02);
    border: 1px dashed var(--line);
    color: var(--muted);
  }
  .sidebar { display: grid; gap: 18px; }
  .list { padding-left: 18px; margin: 0; display: grid; gap: 10px; }
  .footer-note { margin-top: 18px; color: var(--muted); font-size: 0.92rem; }
  .signal-bar { display: flex; gap: 6px; margin-top: 10px; }
  .signal { height: 6px; flex: 1 1 0; border-radius: 999px; background: rgba(255, 255, 255, 0.06); overflow: hidden; }
  .signal.fill-good { background: linear-gradient(90deg, rgba(63, 212, 151, 0.35), rgba(146, 231, 196, 0.72)); }
  .signal.fill-warn { background: linear-gradient(90deg, rgba(245, 196, 81, 0.28), rgba(245, 196, 81, 0.7)); }
  .signal.fill-bad { background: linear-gradient(90deg, rgba(255, 127, 114, 0.28), rgba(255, 127, 114, 0.7)); }
  .gen-footer {
    margin-top: 28px;
    text-align: center;
    color: var(--muted);
    font-size: 0.86rem;
    letter-spacing: 0.04em;
  }
  @media (max-width: 980px) {
    .main { grid-template-columns: 1fr; }
    .hero-stats { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  }
  @media (max-width: 640px) {
    .hero { padding: 22px; }
    .hero-stats { grid-template-columns: 1fr; }
  }
"""


def _render_list_items(items: list[str], empty_text: str) -> str:
    if not items:
        return f'<div class="empty">{_esc(empty_text)}</div>'
    return '<ul class="list">' + "".join(
        f"<li>{_esc(item)}</li>" for item in items
    ) + "</ul>"


def _render_stage(stage: dict) -> str:
    issue = stage.get("issue") or {}
    children = stage.get("open_children") or []
    if issue.get("found") is False:
        state = "missing"
    else:
        state = issue.get("state") or "unknown"
    stage_class = (
        "stage-missing" if state == "missing"
        else "stage-open" if state == "opened"
        else ""
    )
    issue_url = issue.get("web_url")
    issue_link = (
        f'<div class="footer-note"><a href="{_esc(issue_url)}" target="_blank" rel="noreferrer">Open issue</a></div>'
        if issue_url else ""
    )

    if children:
        child_blocks = []
        for child in children:
            child_issue = child.get("issue") or {}
            if child_issue.get("found") is False:
                child_state = "missing"
            else:
                child_state = child_issue.get("state") or "unknown"
            assignees = child_issue.get("assignees") or []
            assignee_text = ", ".join(assignees) if assignees else "unassigned"
            child_url = child_issue.get("web_url")
            child_link = (
                f'<div class="footer-note"><a href="{_esc(child_url)}" target="_blank" rel="noreferrer">Work item</a></div>'
                if child_url else ""
            )
            child_blocks.append(f"""
            <div class="item">
              <p class="item-title">{_esc(child.get("title", ""))}</p>
              <div class="meta">
                <span>{_esc(child.get("project", ""))}</span>
                <span>{_esc(assignee_text)}</span>
              </div>
              <div class="badge-row">
                <span class="badge {_badge_class(child_state)}">{_esc(child_state)}</span>
              </div>
              {child_link}
            </div>
            """)
        child_markup = "".join(child_blocks)
    else:
        child_markup = '<div class="empty">No open child work.</div>'

    return f"""
    <div class="panel {stage_class}">
      <div class="panel-head">
        <h3 class="panel-title">{_esc(stage.get("title", ""))}</h3>
        <div class="panel-sub">{_esc(stage.get("project", ""))}</div>
      </div>
      <div class="panel-body">
        <div class="meta">
          <span>Issue state: {_esc(state)}</span>
          <span>Open work: {len(children)}</span>
        </div>
        <div class="badge-row">
          <span class="badge {_badge_class(state)}">{_esc(state)}</span>
        </div>
        {issue_link}
        <div class="stack" style="margin-top: 16px">{child_markup}</div>
      </div>
    </div>
    """


def _render_repo(repo: dict) -> str:
    pipeline = repo.get("pipeline") or {}
    if pipeline.get("found"):
        pipeline_status = pipeline.get("status") or "unknown"
    else:
        pipeline_status = "missing"
    branch_status = "present" if repo.get("branch_found") else "missing"
    state_class = (
        "repo-failed" if pipeline_status == "failed"
        else "repo-missing" if pipeline_status == "missing"
        else "repo-healthy" if pipeline_status in {"success", "passed"}
        else ""
    )
    pipeline_url = pipeline.get("web_url")
    pipeline_link = (
        f' • <a href="{_esc(pipeline_url)}" target="_blank" rel="noreferrer">Open pipeline</a>'
        if pipeline_url else ""
    )
    repo_url = repo.get("url") or ""
    repo_link = (
        f'<a href="{_esc(repo_url)}" target="_blank" rel="noreferrer">Repository</a>'
        if repo_url else "Repository"
    )
    return f"""
    <div class="item {state_class}">
      <div class="repo-kicker">
        <span>{_esc(repo.get("key", ""))}</span>
        <span>{_esc(pipeline_status)}</span>
      </div>
      <p class="item-title">{_esc(repo.get("name", ""))}</p>
      <div class="meta">
        <span>{_esc(repo.get("project", ""))}</span>
        <span>Branch: {_esc(repo.get("branch_name") or "n/a")}</span>
      </div>
      <div class="badge-row">
        <span class="badge {_badge_class(branch_status)}">{_esc(branch_status)} branch</span>
        <span class="badge {_badge_class(pipeline_status)}">{_esc(pipeline_status)} pipeline</span>
      </div>
      <div class="signal-bar">
        <div class="signal {_signal_class(pipeline_status)}"></div>
      </div>
      <div class="footer-note">{repo_link}{pipeline_link}</div>
    </div>
    """


def render_html(payload: dict, generated_at: str) -> str:
    release_name = payload.get("release") or "Release"
    status = payload.get("status") or "unknown"
    score = payload.get("score")
    summary = payload.get("summary") or {}
    blockers = payload.get("blockers") or []
    risks = payload.get("risks") or []
    stages = payload.get("stages") or []
    repos = payload.get("repos") or []

    open_work = (
        (summary.get("open_stage_issue_count") or 0)
        + (summary.get("open_child_task_count") or 0)
    )
    failing = summary.get("failing_pipeline_count") or 0

    stage_markup = (
        "".join(_render_stage(stage) for stage in stages)
        if stages
        else '<div class="empty">No stage data available.</div>'
    )
    repo_markup = (
        "".join(_render_repo(repo) for repo in repos)
        if repos
        else '<div class="empty">No repositories in scope.</div>'
    )

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{_esc(release_name)} — Release Snapshot</title>
  <style>{_CSS}</style>
</head>
<body>
  <div class="shell">
    <section class="hero">
      <div>
        <div class="status-pill {_status_class(status)}">{_esc(status)}</div>
        <h1 class="title">{_esc(release_name)}</h1>
        <div class="subtle">Static snapshot of live GitLab release state. Regenerate to refresh.</div>
      </div>
      <div class="hero-stats">
        <div class="stat">
          <span class="stat-label">Score</span>
          <div class="stat-value">{_esc(score if score is not None else "--")}</div>
          <div class="stat-note">{_esc(summary.get("stage_issue_count") or 0)} stages / {_esc(summary.get("child_task_count") or 0)} tasks</div>
        </div>
        <div class="stat">
          <span class="stat-label">Open Work</span>
          <div class="stat-value">{open_work}</div>
          <div class="stat-note">{_esc(summary.get("open_stage_issue_count") or 0)} stages open, {_esc(summary.get("open_child_task_count") or 0)} tasks open</div>
        </div>
        <div class="stat">
          <span class="stat-label">Failing Pipelines</span>
          <div class="stat-value">{failing}</div>
          <div class="stat-note">{_esc(summary.get("included_repo_count") or 0)} repos in scope</div>
        </div>
        <div class="stat">
          <span class="stat-label">Generated</span>
          <div class="stat-value" style="font-size: 1.2rem">{_esc(generated_at)}</div>
          <div class="stat-note">Live GitLab snapshot</div>
        </div>
      </div>
    </section>

    <section class="main">
      <div class="panel">
        <div class="panel-head">
          <h2 class="panel-title">Stages</h2>
          <div class="panel-sub">Issue state, open child work, assignees, and direct links.</div>
        </div>
        <div class="panel-body">
          <div class="stack">{stage_markup}</div>
        </div>
      </div>

      <div class="sidebar">
        <div class="panel">
          <div class="panel-head">
            <h2 class="panel-title">Blockers</h2>
            <div class="panel-sub">Items preventing release sign-off.</div>
          </div>
          <div class="panel-body">{_render_list_items(blockers, "No blockers reported.")}</div>
        </div>

        <div class="panel">
          <div class="panel-head">
            <h2 class="panel-title">Risks</h2>
            <div class="panel-sub">Gaps that are not hard blockers yet.</div>
          </div>
          <div class="panel-body">{_render_list_items(risks, "No risks reported.")}</div>
        </div>

        <div class="panel">
          <div class="panel-head">
            <h2 class="panel-title">Repos</h2>
            <div class="panel-sub">Release branch and latest pipeline per repository.</div>
          </div>
          <div class="panel-body">
            <div class="stack">{repo_markup}</div>
          </div>
        </div>
      </div>
    </section>

    <div class="gen-footer">Generated {_esc(generated_at)} from live GitLab data.</div>
  </div>
</body>
</html>
"""


def render_markdown(payload: dict, generated_at: str) -> str:
    release_name = payload.get("release") or "Release"
    status = payload.get("status") or "unknown"
    score = payload.get("score")
    summary = payload.get("summary") or {}
    blockers = payload.get("blockers") or []
    risks = payload.get("risks") or []
    stages = payload.get("stages") or []
    repos = payload.get("repos") or []

    lines: list[str] = []
    lines.append(f"# {release_name}")
    lines.append("")
    lines.append(f"**Status:** `{status}`  |  **Score:** `{score if score is not None else '--'}`")
    lines.append("")

    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Included repos: {summary.get('included_repo_count', 0)}")
    lines.append(f"- Stage issues: {summary.get('stage_issue_count', 0)} ({summary.get('open_stage_issue_count', 0)} open, {summary.get('missing_stage_issue_count', 0)} missing)")
    lines.append(f"- Child tasks: {summary.get('child_task_count', 0)} ({summary.get('open_child_task_count', 0)} open, {summary.get('missing_child_task_count', 0)} missing)")
    lines.append(f"- Validation targets: {summary.get('validation_target_count', 0)}")
    lines.append(f"- Missing release branches: {summary.get('missing_branch_count', 0)}")
    lines.append(f"- Failing pipelines: {summary.get('failing_pipeline_count', 0)}")
    lines.append("")

    lines.append("## Blockers")
    lines.append("")
    if blockers:
        for item in blockers:
            lines.append(f"- {item}")
    else:
        lines.append("_None reported._")
    lines.append("")

    lines.append("## Risks")
    lines.append("")
    if risks:
        for item in risks:
            lines.append(f"- {item}")
    else:
        lines.append("_None reported._")
    lines.append("")

    lines.append("## Stages")
    lines.append("")
    if stages:
        for stage in stages:
            issue = stage.get("issue") or {}
            state = "missing" if issue.get("found") is False else (issue.get("state") or "unknown")
            issue_url = issue.get("web_url")
            title = stage.get("title", "")
            heading = (
                f"### [{title}]({issue_url}) — `{state}`"
                if issue_url
                else f"### {title} — `{state}`"
            )
            lines.append(heading)
            lines.append("")
            project = stage.get("project")
            if project:
                lines.append(f"_{project}_")
                lines.append("")
            open_children = stage.get("open_children") or []
            if open_children:
                lines.append(f"Open work ({len(open_children)}):")
                lines.append("")
                for child in open_children:
                    child_issue = child.get("issue") or {}
                    child_state = "missing" if child_issue.get("found") is False else (child_issue.get("state") or "unknown")
                    assignees = child_issue.get("assignees") or []
                    assignee_text = ", ".join(assignees) if assignees else "unassigned"
                    child_url = child_issue.get("web_url")
                    child_title = child.get("title", "")
                    title_md = (
                        f"[{child_title}]({child_url})"
                        if child_url else child_title
                    )
                    lines.append(f"- {title_md} — `{child_state}` — {assignee_text}")
                lines.append("")
            else:
                lines.append("Open work: none.")
                lines.append("")
    else:
        lines.append("_No stages defined._")
        lines.append("")

    lines.append("## Repositories")
    lines.append("")
    if repos:
        lines.append("| Repo | Branch | Branch Status | Pipeline | Links |")
        lines.append("|---|---|---|---|---|")
        for repo in repos:
            pipeline = repo.get("pipeline") or {}
            pipeline_status = pipeline.get("status") or "unknown" if pipeline.get("found") else "missing"
            branch_status = "present" if repo.get("branch_found") else "missing"
            name = repo.get("name", "")
            branch = repo.get("branch_name") or "n/a"
            repo_url = repo.get("url")
            pipeline_url = pipeline.get("web_url")
            links = []
            if repo_url:
                links.append(f"[repo]({repo_url})")
            if pipeline_url:
                links.append(f"[pipeline]({pipeline_url})")
            link_cell = " · ".join(links) if links else ""
            lines.append(
                f"| {_md_table_cell(name)} | {_md_table_cell(branch)} | `{branch_status}` | `{pipeline_status}` | {link_cell} |"
            )
        lines.append("")
    else:
        lines.append("_No repositories in scope._")
        lines.append("")

    lines.append(f"_Generated {generated_at} from live GitLab data._")
    lines.append("")

    return "\n".join(lines)


def _md_table_cell(value: str) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")

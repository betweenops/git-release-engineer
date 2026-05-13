from __future__ import annotations

import json
import time
from dataclasses import asdict
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from .gitlab import GitLabClient
from .live_state import load_release_live_state
from .manifest import ManifestError, normalize_release_scope
from .readiness import build_live_report, build_manifest_only_report


INDEX_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Release Dashboard</title>
  <style>
    :root {
      --ink: #e7fff6;
      --text: #d5e7e2;
      --muted: #94a7a3;
      --line: rgba(146, 231, 196, 0.14);
      --paper: #071013;
      --card: rgba(12, 24, 29, 0.9);
      --card-strong: rgba(14, 28, 34, 0.96);
      --accent: #3fd497;
      --accent-soft: #92e7c4;
      --accent-deep: #163b30;
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

    .shell {
      max-width: 1320px;
      margin: 0 auto;
      padding: 28px 20px 48px;
    }

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

    .hero-top {
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: start;
      flex-wrap: wrap;
    }

    .title {
      font-size: clamp(1.8rem, 3.2vw, 3rem);
      line-height: 1.04;
      margin: 0;
      letter-spacing: -0.03em;
    }

    .subtle {
      color: rgba(213, 231, 226, 0.78);
      margin-top: 10px;
      max-width: 56rem;
    }

    .controls {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      align-items: center;
    }

    button, select, input {
      font: inherit;
    }

    button {
      border: 0;
      border-radius: 999px;
      padding: 11px 16px;
      cursor: pointer;
      background: var(--accent);
      color: #06110d;
      font-weight: 600;
      transition: transform 0.18s ease, background 0.18s ease, box-shadow 0.18s ease;
      box-shadow: 0 10px 24px rgba(63, 212, 151, 0.18);
    }

    button:hover {
      transform: translateY(-1px);
      background: var(--accent-soft);
    }

    button.secondary {
      background: rgba(255, 255, 255, 0.04);
      color: var(--ink);
      outline: 1px solid rgba(146, 231, 196, 0.18);
      box-shadow: none;
    }

    .control-group {
      display: flex;
      gap: 8px;
      align-items: center;
      background: rgba(255, 255, 255, 0.04);
      padding: 8px 10px;
      border-radius: 999px;
      outline: 1px solid rgba(146, 231, 196, 0.18);
    }

    .control-label {
      font-size: 0.84rem;
      color: rgba(213, 231, 226, 0.8);
      white-space: nowrap;
    }

    .control-group select {
      border: 0;
      background: transparent;
      color: white;
      padding: 0 2px;
      min-width: 0;
    }

    .control-group select:focus {
      outline: none;
    }

    .control-group option {
      color: var(--ink);
    }

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
      backdrop-filter: blur(10px);
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

    .stat-value {
      font-size: 2rem;
      font-weight: 700;
      line-height: 1;
    }

    .stat-note {
      margin-top: 8px;
      color: rgba(213, 231, 226, 0.74);
      font-size: 0.92rem;
    }

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

    .panel-title {
      margin: 0;
      font-size: 1.1rem;
      letter-spacing: -0.02em;
    }

    .panel-sub {
      color: var(--muted);
      margin-top: 6px;
      font-size: 0.94rem;
    }

    .panel-body {
      padding: 18px 20px 22px;
    }

    .stack {
      display: grid;
      gap: 14px;
    }

    .issue-list, .repo-list {
      display: grid;
      gap: 12px;
    }

    .item {
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 14px;
      background: var(--card-strong);
      transition: border-color 0.18s ease, transform 0.18s ease, box-shadow 0.18s ease;
      box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.02);
    }

    .item:hover {
      transform: translateY(-1px);
      border-color: rgba(146, 231, 196, 0.24);
    }

    .panel.stage-open {
      border-left: 3px solid rgba(63, 212, 151, 0.42);
    }

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

    .item.repo-healthy {
      border-color: rgba(63, 212, 151, 0.2);
    }

    .item-title {
      font-weight: 700;
      margin: 0 0 6px;
      color: var(--ink);
    }

    .meta {
      color: var(--muted);
      font-size: 0.92rem;
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
    }

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

    .badge-row {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      margin-top: 8px;
    }

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
    .badge.closed { background: rgba(63, 212, 151, 0.14); color: var(--good); }
    .badge.orange { background: rgba(245, 196, 81, 0.12); color: var(--warn); }
    .badge.red { background: rgba(255, 127, 114, 0.14); color: var(--bad); }
    .badge.present { background: rgba(63, 212, 151, 0.1); color: var(--accent-soft); }

    .toolbar {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      margin-bottom: 16px;
    }

    .toolbar input, .toolbar select {
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 10px 12px;
      background: rgba(255, 255, 255, 0.03);
      color: var(--text);
      min-width: 180px;
    }

    .empty, .error {
      padding: 14px;
      border-radius: 14px;
      background: rgba(255, 255, 255, 0.02);
      border: 1px dashed var(--line);
      color: var(--muted);
    }

    .error {
      background: rgba(255, 127, 114, 0.08);
      border-color: rgba(255, 127, 114, 0.28);
      color: #ffd2cb;
    }

    .sidebar {
      display: grid;
      gap: 18px;
    }

    .list {
      padding-left: 18px;
      margin: 0;
      display: grid;
      gap: 10px;
    }

    .footer-note {
      margin-top: 18px;
      color: var(--muted);
      font-size: 0.92rem;
    }

    .signal-bar {
      display: flex;
      gap: 6px;
      margin-top: 10px;
    }

    .signal {
      height: 6px;
      flex: 1 1 0;
      border-radius: 999px;
      background: rgba(255, 255, 255, 0.06);
      overflow: hidden;
    }

    .signal.fill-good { background: linear-gradient(90deg, rgba(63, 212, 151, 0.35), rgba(146, 231, 196, 0.72)); }
    .signal.fill-warn { background: linear-gradient(90deg, rgba(245, 196, 81, 0.28), rgba(245, 196, 81, 0.7)); }
    .signal.fill-bad { background: linear-gradient(90deg, rgba(255, 127, 114, 0.28), rgba(255, 127, 114, 0.7)); }

    @media (max-width: 980px) {
      .main {
        grid-template-columns: 1fr;
      }
      .hero-stats {
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }
    }

    @media (max-width: 640px) {
      .hero {
        padding: 22px;
      }
      .hero-stats {
        grid-template-columns: 1fr;
      }
    }
  </style>
</head>
<body>
  <div class="shell">
    <section class="hero">
      <div class="hero-top">
        <div>
          <div id="status-pill" class="status-pill">Loading</div>
          <h1 class="title" id="release-title">Release Dashboard</h1>
          <div class="subtle" id="hero-subtitle">Fetching manifest and live release state.</div>
        </div>
        <div class="controls">
          <button id="refresh-live">Refresh Live</button>
          <button id="refresh-manifest" class="secondary">Manifest Only</button>
          <label class="control-group" for="auto-refresh">
            <span class="control-label">Auto Refresh</span>
            <select id="auto-refresh">
              <option value="0">Off</option>
              <option value="30">30s</option>
              <option value="60">1m</option>
              <option value="120">2m</option>
              <option value="300">5m</option>
            </select>
          </label>
        </div>
      </div>
      <div class="hero-stats">
        <div class="stat">
          <span class="stat-label">Score</span>
          <div class="stat-value" id="score-value">--</div>
          <div class="stat-note" id="score-note">Waiting for data</div>
        </div>
        <div class="stat">
          <span class="stat-label">Open Work</span>
          <div class="stat-value" id="open-work-value">--</div>
          <div class="stat-note" id="open-work-note">Stages and tasks</div>
        </div>
        <div class="stat">
          <span class="stat-label">Repo Health</span>
          <div class="stat-value" id="repo-health-value">--</div>
          <div class="stat-note" id="repo-health-note">Pipelines and branches</div>
        </div>
        <div class="stat">
          <span class="stat-label">Last Updated</span>
          <div class="stat-value" id="updated-value" style="font-size:1.2rem">--</div>
          <div class="stat-note" id="source-note">Source pending</div>
        </div>
      </div>
    </section>

    <section class="main">
      <div class="panel">
        <div class="panel-head">
          <h2 class="panel-title">Stages</h2>
          <div class="panel-sub">Live issue state, open work, assignees, and direct links.</div>
        </div>
        <div class="panel-body">
          <div id="stage-content" class="stack">
            <div class="empty">No data loaded yet.</div>
          </div>
        </div>
      </div>

      <div class="sidebar">
        <div class="panel">
          <div class="panel-head">
            <h2 class="panel-title">Blockers</h2>
            <div class="panel-sub">Highest-signal release blockers from the latest refresh.</div>
          </div>
          <div class="panel-body">
            <ul id="blocker-list" class="list"></ul>
          </div>
        </div>

        <div class="panel">
          <div class="panel-head">
            <h2 class="panel-title">Risks</h2>
            <div class="panel-sub">Operational gaps that are not hard blockers yet.</div>
          </div>
          <div class="panel-body">
            <ul id="risk-list" class="list"></ul>
          </div>
        </div>

        <div class="panel">
          <div class="panel-head">
            <h2 class="panel-title">Repos</h2>
            <div class="panel-sub">Filter repository state by pipeline outcome.</div>
          </div>
          <div class="panel-body">
            <div class="toolbar">
              <input id="repo-search" type="search" placeholder="Filter repos">
              <select id="repo-filter">
                <option value="all">All repos</option>
                <option value="failed">Failing pipelines</option>
                <option value="missing">Missing pipelines</option>
                <option value="healthy">Healthy pipelines</option>
              </select>
            </div>
            <div id="repo-content" class="repo-list">
              <div class="empty">No repositories loaded yet.</div>
            </div>
          </div>
        </div>
      </div>
    </section>
  </div>

  <script>
    const state = {
      payload: null,
      source: "none",
      autoRefreshTimer: null,
      refreshInFlight: false,
    };

    const els = {
      title: document.getElementById("release-title"),
      subtitle: document.getElementById("hero-subtitle"),
      statusPill: document.getElementById("status-pill"),
      scoreValue: document.getElementById("score-value"),
      scoreNote: document.getElementById("score-note"),
      openWorkValue: document.getElementById("open-work-value"),
      openWorkNote: document.getElementById("open-work-note"),
      repoHealthValue: document.getElementById("repo-health-value"),
      repoHealthNote: document.getElementById("repo-health-note"),
      updatedValue: document.getElementById("updated-value"),
      sourceNote: document.getElementById("source-note"),
      stageContent: document.getElementById("stage-content"),
      blockerList: document.getElementById("blocker-list"),
      riskList: document.getElementById("risk-list"),
      repoContent: document.getElementById("repo-content"),
      repoSearch: document.getElementById("repo-search"),
      repoFilter: document.getElementById("repo-filter"),
      autoRefresh: document.getElementById("auto-refresh"),
      refreshLive: document.getElementById("refresh-live"),
      refreshManifest: document.getElementById("refresh-manifest"),
    };

    function escapeHtml(value) {
      return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;");
    }

    function badgeClass(value) {
      if (value === "failed") return "failed";
      if (value === "missing") return "missing";
      if (value === "red") return "red";
      if (value === "present") return "present";
      if (value === "success" || value === "passed" || value === "closed") return "success";
      if (value === "opened") return "opened";
      if (value === "orange") return "orange";
      return "";
    }

    function renderList(target, items, emptyText) {
      if (!items || items.length === 0) {
        target.innerHTML = `<div class="empty">${escapeHtml(emptyText)}</div>`;
        return;
      }
      target.innerHTML = items.map(item => `<li>${escapeHtml(item)}</li>`).join("");
    }

    function renderStages(payload) {
      const stages = payload.stages || [];
      if (stages.length === 0) {
        els.stageContent.innerHTML = `<div class="empty">No stage data available.</div>`;
        return;
      }
      els.stageContent.innerHTML = stages.map(stage => {
        const issue = stage.issue || {};
        const children = stage.open_children || [];
        const issueState = issue.found === false ? "missing" : (issue.state || "unknown");
        const stageClass = issueState === "missing" ? "stage-missing" : (issueState === "opened" ? "stage-open" : "");
        const issueUrl = issue.web_url ? `<a href="${escapeHtml(issue.web_url)}" target="_blank" rel="noreferrer">Open issue</a>` : "";
        const childMarkup = children.length
          ? children.map(child => {
              const childIssue = child.issue || {};
              const childState = childIssue.found === false ? "missing" : (childIssue.state || "unknown");
              const assignees = childIssue.assignees && childIssue.assignees.length
                ? childIssue.assignees.join(", ")
                : "unassigned";
              const childUrl = childIssue.web_url
                ? `<a href="${escapeHtml(childIssue.web_url)}" target="_blank" rel="noreferrer">Work item</a>`
                : "";
              return `
                <div class="item">
                  <p class="item-title">${escapeHtml(child.title)}</p>
                  <div class="meta">
                    <span>${escapeHtml(child.project || "")}</span>
                    <span>${escapeHtml(assignees)}</span>
                  </div>
                  <div class="badge-row">
                    <span class="badge ${badgeClass(childState)}">${escapeHtml(childState)}</span>
                  </div>
                  ${childUrl ? `<div class="footer-note">${childUrl}</div>` : ""}
                </div>
              `;
            }).join("")
          : `<div class="empty">No open child work.</div>`;
        return `
          <div class="panel ${stageClass}">
            <div class="panel-head">
              <h3 class="panel-title">${escapeHtml(stage.title)}</h3>
              <div class="panel-sub">${escapeHtml(stage.project || "")}</div>
            </div>
            <div class="panel-body">
              <div class="meta">
                <span>Issue state: ${escapeHtml(issueState)}</span>
                <span>Open work: ${children.length}</span>
              </div>
              <div class="badge-row">
                <span class="badge ${badgeClass(issueState)}">${escapeHtml(issueState)}</span>
              </div>
              ${issueUrl ? `<div class="footer-note">${issueUrl}</div>` : ""}
              <div class="stack" style="margin-top: 16px">${childMarkup}</div>
            </div>
          </div>
        `;
      }).join("");
    }

    function filterRepos(repos) {
      const search = els.repoSearch.value.trim().toLowerCase();
      const mode = els.repoFilter.value;
      return repos.filter(repo => {
        const pipelineStatus = repo.pipeline && repo.pipeline.found
          ? (repo.pipeline.status || "unknown")
          : "missing";
        const haystack = `${repo.name} ${repo.project} ${repo.branch_name || ""}`.toLowerCase();
        if (search && !haystack.includes(search)) return false;
        if (mode === "failed" && pipelineStatus !== "failed") return false;
        if (mode === "missing" && pipelineStatus !== "missing") return false;
        if (mode === "healthy" && !["success", "passed"].includes(pipelineStatus)) return false;
        return true;
      });
    }

    function renderRepos(payload) {
      const repos = filterRepos(payload.repos || []);
      if (repos.length === 0) {
        els.repoContent.innerHTML = `<div class="empty">No repos match the current filter.</div>`;
        return;
      }
      els.repoContent.innerHTML = repos.map(repo => {
        const pipelineStatus = repo.pipeline && repo.pipeline.found
          ? (repo.pipeline.status || "unknown")
          : "missing";
        const branchStatus = repo.branch_found ? "present" : "missing";
        const repoStateClass =
          pipelineStatus === "failed" ? "repo-failed" :
          pipelineStatus === "missing" ? "repo-missing" :
          ["success", "passed"].includes(pipelineStatus) ? "repo-healthy" : "";
        const pipelineUrl = repo.pipeline && repo.pipeline.web_url
          ? `<a href="${escapeHtml(repo.pipeline.web_url)}" target="_blank" rel="noreferrer">Open pipeline</a>`
          : "";
        const signalClass =
          pipelineStatus === "failed" ? "fill-bad" :
          pipelineStatus === "missing" ? "fill-warn" :
          ["success", "passed"].includes(pipelineStatus) ? "fill-good" : "";
        return `
          <div class="item ${repoStateClass}">
            <div class="repo-kicker">
              <span>${escapeHtml(repo.key)}</span>
              <span>${escapeHtml(pipelineStatus)}</span>
            </div>
            <p class="item-title">${escapeHtml(repo.name)}</p>
            <div class="meta">
              <span>${escapeHtml(repo.project)}</span>
              <span>Branch: ${escapeHtml(repo.branch_name || "n/a")}</span>
            </div>
            <div class="badge-row">
              <span class="badge ${badgeClass(branchStatus)}">${escapeHtml(branchStatus)} branch</span>
              <span class="badge ${badgeClass(pipelineStatus)}">${escapeHtml(pipelineStatus)} pipeline</span>
            </div>
            <div class="signal-bar">
              <div class="signal ${signalClass}"></div>
            </div>
            <div class="footer-note">
              <a href="${escapeHtml(repo.url)}" target="_blank" rel="noreferrer">Repository</a>
              ${pipelineUrl ? ` • ${pipelineUrl}` : ""}
            </div>
          </div>
        `;
      }).join("");
    }

    function renderPayload(payload, sourceLabel) {
      state.payload = payload;
      state.source = sourceLabel;
      const summary = payload.summary || {};
      const failing = summary.failing_pipeline_count || 0;
      const openWork = (summary.open_stage_issue_count || 0) + (summary.open_child_task_count || 0);

      els.title.textContent = payload.release || "Release Dashboard";
      els.subtitle.textContent = sourceLabel === "live"
        ? "Live GitLab release state with stage, task, branch, and pipeline visibility."
        : "Manifest-derived release baseline. Live GitLab data is unavailable or not configured.";
      els.statusPill.textContent = payload.status || "unknown";
      els.statusPill.className = `status-pill ${payload.status || ""}`;
      els.scoreValue.textContent = payload.score ?? "--";
      els.scoreNote.textContent = `${summary.stage_issue_count || 0} stages / ${summary.child_task_count || 0} tasks`;
      els.openWorkValue.textContent = openWork;
      els.openWorkNote.textContent = `${summary.open_stage_issue_count || 0} stages open, ${summary.open_child_task_count || 0} tasks open`;
      els.repoHealthValue.textContent = failing;
      els.repoHealthNote.textContent = `${summary.included_repo_count || 0} repos in scope`;
      els.updatedValue.textContent = new Date().toLocaleTimeString();
      const refreshLabel = els.autoRefresh.value === "0"
        ? "Auto refresh off"
        : `Auto refresh every ${els.autoRefresh.options[els.autoRefresh.selectedIndex].text}`;
      els.sourceNote.textContent = sourceLabel === "live"
        ? `Live GitLab data • ${refreshLabel}`
        : `Manifest-only data • ${refreshLabel}`;

      renderList(els.blockerList, payload.blockers || [], "No blockers reported.");
      renderList(els.riskList, payload.risks || [], "No risks reported.");
      renderStages(payload);
      renderRepos(payload);
    }

    function showError(message) {
      els.stageContent.innerHTML = `<div class="error">${escapeHtml(message)}</div>`;
    }

    async function loadManifest() {
      const response = await fetch("/api/report");
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || "Manifest load failed");
      renderPayload(payload, "manifest");
    }

    async function loadLive() {
      const response = await fetch("/api/report-live");
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || "Live load failed");
      renderPayload(payload, "live");
    }

    async function refresh(mode) {
      if (state.refreshInFlight) return;
      state.refreshInFlight = true;
      try {
        if (mode === "live") {
          await loadLive();
          return;
        }
        await loadManifest();
      } catch (error) {
        if (mode === "live" && state.payload) {
          showError(`Live refresh failed: ${error.message}`);
          return;
        }
        showError(error.message);
      } finally {
        state.refreshInFlight = false;
      }
    }

    function configureAutoRefresh() {
      if (state.autoRefreshTimer) {
        clearInterval(state.autoRefreshTimer);
        state.autoRefreshTimer = null;
      }
      const seconds = Number(els.autoRefresh.value);
      if (!seconds) {
        if (state.payload) {
          renderPayload(state.payload, state.source);
        }
        return;
      }
      state.autoRefreshTimer = setInterval(() => refresh("live"), seconds * 1000);
      if (state.payload) {
        renderPayload(state.payload, state.source);
      }
    }

    els.refreshLive.addEventListener("click", () => refresh("live"));
    els.refreshManifest.addEventListener("click", () => refresh("manifest"));
    els.repoSearch.addEventListener("input", () => state.payload && renderRepos(state.payload));
    els.repoFilter.addEventListener("change", () => state.payload && renderRepos(state.payload));
    els.autoRefresh.addEventListener("change", configureAutoRefresh);

    (async () => {
      configureAutoRefresh();
      await refresh("manifest");
      try {
        await refresh("live");
      } catch (_error) {
      }
    })();
  </script>
</body>
</html>
"""


class DashboardConfig:
    def __init__(
        self,
        manifest_path: Path,
        vars_file: Path | None,
        gitlab_url: str | None,
        token_env: str,
    ) -> None:
        self.manifest_path = manifest_path
        self.vars_file = vars_file
        self.gitlab_url = gitlab_url
        self.token_env = token_env


def build_manifest_payload(manifest_path: Path, vars_file: Path | None) -> dict[str, Any]:
    scope = normalize_release_scope(manifest_path, vars_file=vars_file)
    report = build_manifest_only_report(scope)
    return {
        "release": scope.title or scope.version,
        "status": report.status,
        "score": report.score,
        "summary": asdict(report.summary),
        "blockers": report.blockers,
        "risks": report.risks,
        "epic": {"found": False},
        "stages": [
            {
                "key": stage.key,
                "title": stage.title,
                "project": stage.project,
                "issue": {"found": False},
                "open_children": [
                    {
                        "key": child.key,
                        "title": child.title,
                        "project": child.project,
                        "issue": {"found": False},
                    }
                    for child in stage.children
                ],
            }
            for stage in scope.stage_issues
        ],
        "repos": [
            {
                "key": repo.key,
                "name": repo.name,
                "project": repo.project,
                "url": repo.url,
                "branch_name": repo.release_branch,
                "branch_found": False,
                "pipeline": {"found": False},
            }
            for repo in scope.repos
            if repo.included
        ],
    }


def build_live_payload(
    manifest_path: Path,
    vars_file: Path | None,
    gitlab_url: str,
    token: str,
) -> dict[str, Any]:
    scope = normalize_release_scope(manifest_path, vars_file=vars_file)
    state = load_release_live_state(GitLabClient(gitlab_url, token=token), scope)
    report = build_live_report(state)
    return {
        "release": scope.title or scope.version,
        "status": report.status,
        "score": report.score,
        "summary": asdict(report.summary),
        "blockers": report.blockers,
        "risks": report.risks,
        "epic": (
            {
                "found": True,
                "title": state.epic.title,
                "state": state.epic.state,
                "web_url": state.epic.web_url,
            }
            if state.epic is not None
            else {"found": False}
        ),
        "stages": [
            {
                "key": stage.expected.key,
                "title": stage.expected.title,
                "project": stage.expected.project,
                "issue": (
                    {
                        "found": True,
                        "state": stage.issue.state,
                        "web_url": stage.issue.web_url,
                        "assignees": stage.issue.assignees,
                        "labels": stage.issue.labels,
                    }
                    if stage.issue is not None
                    else {"found": False}
                ),
                "open_children": [
                    {
                        "key": child.key,
                        "title": child.title,
                        "project": child.project,
                        "issue": (
                            {
                                "found": True,
                                "state": child_issue.state,
                                "web_url": child_issue.web_url,
                                "assignees": child_issue.assignees,
                                "labels": child_issue.labels,
                            }
                            if child_issue is not None
                            else {"found": False}
                        ),
                    }
                    for child, child_issue in stage.children
                    if child_issue is None or child_issue.state != "closed"
                ],
            }
            for stage in state.stages
        ],
        "repos": [
            {
                "key": repo.key,
                "name": repo.name,
                "project": repo.project,
                "url": repo.url,
                "branch_name": repo.branch_name,
                "branch_found": repo.branch is not None,
                "pipeline": (
                    {
                        "found": True,
                        "status": repo.latest_pipeline.status,
                        "web_url": repo.latest_pipeline.web_url,
                    }
                    if repo.latest_pipeline is not None
                    else {"found": False}
                ),
            }
            for repo in state.repos
        ],
    }


def make_handler(config: DashboardConfig):
    class DashboardHandler(BaseHTTPRequestHandler):
        server_version = "ReleaseDashboard/0.1"

        def do_GET(self) -> None:  # noqa: N802
            try:
                if self.path == "/" or self.path.startswith("/?"):
                    self._send_html(INDEX_HTML)
                    return
                if self.path == "/api/report":
                    payload = build_manifest_payload(config.manifest_path, config.vars_file)
                    self._send_json(payload)
                    return
                if self.path == "/api/report-live":
                    if not config.gitlab_url:
                        raise ManifestError(
                            "Live reporting is not configured. Set GITLAB_URL and restart the dashboard."
                        )
                    token = self._token()
                    payload = build_live_payload(
                        config.manifest_path,
                        config.vars_file,
                        config.gitlab_url,
                        token,
                    )
                    self._send_json(payload)
                    return
                if self.path == "/api/health":
                    self._send_json({"ok": True, "timestamp": int(time.time())})
                    return
                self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            except ManifestError as exc:
                self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            except Exception as exc:  # noqa: BLE001
                self._send_json({"error": f"Unexpected server error: {exc}"}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

        def log_message(self, fmt: str, *args: Any) -> None:
            print(f"[dashboard] {self.address_string()} - {fmt % args}")

        def _token(self) -> str:
            value = __import__("os").environ.get(config.token_env, "").strip()
            if not value:
                raise ManifestError(
                    f"Set {config.token_env} before using the live dashboard endpoint."
                )
            return value

        def _send_html(self, body: str, status: HTTPStatus = HTTPStatus.OK) -> None:
            payload = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def _send_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
            body = json.dumps(payload, indent=2).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return DashboardHandler


def serve_dashboard(
    host: str,
    port: int,
    manifest_path: Path,
    vars_file: Path | None,
    gitlab_url: str | None,
    token_env: str,
) -> None:
    config = DashboardConfig(
        manifest_path=manifest_path,
        vars_file=vars_file,
        gitlab_url=gitlab_url,
        token_env=token_env,
    )
    server = ThreadingHTTPServer((host, port), make_handler(config))
    print(f"Dashboard listening on http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

# Safe Semiconductor Tool Operation

Use this skill before invoking shell commands, EDA flows, schedulers, file-conversion tools, databases, or laboratory instruments.

## Safety workflow

1. Explain what the proposed operation does, which files or services it touches, expected outputs, and likely cost or runtime.
2. Confirm the current working directory and resolve paths before a command that reads or writes files.
3. Prefer read-only inspection and narrowly scoped commands. Quote paths safely; do not interpolate untrusted file contents into shell commands.
4. Obtain explicit user approval before writes, deletes, overwrites, launches of expensive jobs, database changes, instrument control, calibration, recipe changes, or actions that affect shared resources.
5. Preview the target and command arguments before an approved mutation. Prefer a new output path, dry-run, or temporary workspace when supported.
6. Preserve native inputs, logs, reports, and result databases. Do not silently clean up, move, copy, or alter engineering data.
7. After execution, report the exact command/tool, exit status, affected outputs, and any incomplete or failed work. Do not claim success based solely on process launch.
8. Treat MCP servers as capable of acting on local files or services. Apply the same approval and trust checks as for shell commands.

## Semiconductor-specific safeguards

- Treat RTL, netlists, layouts, PDKs, rule decks, process recipes, unreleased silicon results, and customer-linked data as confidential.
- Use only organization-approved models, MCP servers, and documentation sources for proprietary material.
- Do not bypass tool licenses, access controls, project guardrails, or sign-off workflows.
- Keep writes and control operations approval-gated; default instrument integrations to status/read-only queries.
- Do not change constraints, waivers, models, recipes, or sign-off settings as an unreviewed shortcut.

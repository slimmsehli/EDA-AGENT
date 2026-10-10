# Semiconductor Change and Release Summary

Use this skill to prepare engineering change summaries, verification handoffs, release notes, or design-review evidence.

## Summary workflow

1. Establish the change scope from the requested revision range, ticket, or explicitly selected files. Do not assume all workspace changes belong to the release.
2. Summarize functional, RTL, constraint, testbench, flow, and documentation changes separately where relevant.
3. Inventory evidence: tests and regressions run, tool/version/configuration, seeds, corners, reports, pass/fail counts, and links or paths to results.
4. State what was not run, failed, waived, or remains unresolved. Do not convert missing evidence into a pass.
5. Separate measured results from interpretation. Include meaningful values and units and describe baseline comparability.
6. Identify risks, dependencies, PDK/IP/tool revisions, known limitations, and required reviewer or sign-off actions.
7. Keep the summary concise, traceable, and suitable for handoff. Cite commit IDs, report paths, or ticket IDs only when verified.

## Suggested format

- **Scope and revision**
- **Change summary**
- **Verification evidence**
- **Results and comparison**
- **Known issues and limitations**
- **Risks and dependencies**
- **Required reviews / next steps**

Never imply sign-off, tapeout readiness, or release approval unless the authorized process explicitly recorded it. Do not alter source files or test results while preparing a summary.

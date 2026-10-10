# Semiconductor Regression Triage

Use this skill to investigate simulation, formal, lint, synthesis, or implementation regression failures.

## Triage workflow

1. Identify the run directory, tool and version, configuration, test name, seed, revision, and the exact failure reported by the user.
2. Inspect summaries and the earliest relevant error before reading large logs. Distinguish the first causal error from later cascading failures and cleanup messages.
3. Group failures by common signature, test, seed, configuration, hierarchy, and timestamp. Count affected and passing tests when the available data supports it.
4. Compare against a known-good run only when the revisions, options, environment, and test inputs are sufficiently comparable. State differences that weaken the comparison.
5. Correlate errors with RTL, testbench, constraints, tool configuration, and recent changes. Do not treat temporal coincidence as proof of causality.
6. Propose the smallest useful next check, such as rerunning one failing test with the same seed or inspecting a specific waveform/log section. Ask before starting expensive regressions or modifying run artifacts.

## Output

Summarize:

- Scope and evidence inspected.
- Failure groups, counts, and representative tests.
- Earliest useful error with file, line, timestamp, or log location.
- Likely causes, ranked by evidence and confidence.
- Missing information and recommended next experiment.

Preserve original logs and databases. Do not label a regression as a design bug until environment, testbench, configuration, and tool issues have been considered.

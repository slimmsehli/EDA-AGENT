# Semiconductor Timing Report Analysis

Use this skill for static timing analysis (STA), timing summaries, path reports, constraints, and timing comparisons.

## Analysis workflow

1. Identify the source tool, report type, design revision, mode/corner, units, and whether the report is pre- or post-route.
2. Determine the reported sign convention before interpreting slack. Separate setup, hold, recovery/removal, pulse-width, unconstrained, and electrical checks.
3. For a critical path, capture startpoint, endpoint, path group, launch/capture clocks, required time, arrival time, slack, and each reported cell/net contribution.
4. Check clock period, uncertainty, latency, skew, input/output delays, exceptions, derates, and transition/capacitance assumptions when those data are available.
5. Compare paths only when corners, modes, constraints, tool stages, and units match. State any mismatches.
6. Distinguish measured report facts from possible remedies. Explain whether delay appears dominated by logic depth, cell choice, fanout, routing, slew/load, or clock effects only when supported by path data.
7. Identify unconstrained endpoints, suspicious exceptions, or missing constraints as coverage risks; do not invent constraints.

## Output

Report the worst paths and relevant values with units and sign convention. Explain the evidence for each observation, its likely design impact, and a focused follow-up (for example, checking a constraint or comparing pre/post-route paths).

Preserve native STA reports as authoritative. Do not edit timing constraints, waive paths, or declare timing sign-off from a partial summary or a single corner.

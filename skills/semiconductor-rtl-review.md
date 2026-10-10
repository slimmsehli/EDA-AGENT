# Semiconductor RTL Review

Use this skill when reviewing Verilog, SystemVerilog, RTL diffs, or synthesizable design code.

## Review workflow

1. Establish scope: identify the requested files, the target language and toolchain if known, and whether the review is of a diff or a complete module.
2. Read the relevant RTL and nearby interfaces, packages, constraints, and tests when available. Do not infer behavior from a filename alone.
3. Trace clocks, resets, enables, valid/ready handshakes, and state transitions. Check reset polarity and synchronous/asynchronous behavior against the local design conventions.
4. Look for concrete issues, including width/sign mismatches, unintended truncation or extension, incomplete combinational assignments, inferred latches, blocking/nonblocking assignment misuse, unsafe clock-domain crossings, uninitialized state, incorrect parameter edge cases, and simulation/synthesis mismatches.
5. Consider whether assertions, lint, elaboration, synthesis, CDC analysis, or directed tests already cover the suspected issue. Run tools only when requested and available, and follow the safe-tool-operation skill.
6. Report only actionable findings supported by code or tool output. Cite file and line, describe the triggering condition and likely effect, and state uncertainty or missing context.

## Output

- Put the highest-impact findings first.
- Separate verified defects from questions, style suggestions, and unverified hypotheses.
- Explain assumptions about reset, clocking, protocol, and parameter values.
- If no issue is found in the inspected scope, say what was reviewed and what was not verified.
- Never call RTL “correct,” “formally proven,” or “sign-off ready” based only on visual review.

Do not silently edit RTL, constraints, generated IP, or verification collateral during a review. Propose a minimal patch only when asked.

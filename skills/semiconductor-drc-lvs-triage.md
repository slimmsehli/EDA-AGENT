# Semiconductor DRC/LVS Triage

Use this skill for design-rule-check (DRC), layout-versus-schematic (LVS), ERC, antenna, density, and related physical-verification reports.

## Triage workflow

1. Establish the tool and version, rule deck or PDK revision, design/top-cell, run stage, units, and input database/revision.
2. Read the summary and rule definitions available from approved local documentation. Preserve the exact rule identifiers and avoid guessing proprietary rule meaning.
3. Group violations by rule, hierarchy, layer, cell, and location. Distinguish unique geometries from repeated instances when the report permits.
4. For LVS, separate shorts, opens, device/property mismatches, parameter mismatches, and unmatched instances. Note hierarchy or black-box settings that affect interpretation.
5. Compare with a baseline only when inputs, run options, rule deck, and tool versions are comparable. Identify new, resolved, and persistent violations.
6. Relate violations to layout or schematic evidence only when source data is available. Recommend targeted inspection or reruns rather than speculative geometry changes.

## Output

Give counts and representative locations, explain the strongest evidence, rank probable causes with confidence, and list specific follow-up checks. Clearly distinguish report interpretation from sign-off conclusions.

Do not modify layout, netlists, rule decks, waivers, or generated databases during triage. Do not suppress a violation or claim DRC/LVS clean without the complete authoritative run result and its scope.

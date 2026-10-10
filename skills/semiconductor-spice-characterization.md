# Semiconductor SPICE and Characterization Analysis

Use this skill for SPICE decks, simulation output, device characterization, sweep data, and measured-versus-simulated comparisons.

## Analysis workflow

1. Record the simulator and version, model/PDK revision if known, testbench/deck, device or circuit, corner, temperature, supply, bias, sweep range, and units.
2. Verify that compared data use compatible conditions, definitions, units, sign conventions, and sampling. Do not silently convert or discard data.
3. Summarize sweep endpoints, sample counts, extrema, operating points, convergence warnings, and missing or non-finite values.
4. For a comparison, identify the exact datasets, alignment/interpolation method, error metric, and any filtering. Label calculations and assumptions.
5. Plot or tabulate trends when useful, preserving the raw data and noting axis units and scales. Separate observed behavior from physical interpretation.
6. Investigate warnings, convergence issues, discontinuities, and outliers before concluding that a device or model changed.

## Output

State conditions and units beside every result. Report methods, key values, deviations, caveats, and the next targeted simulation or measurement that would distinguish plausible explanations.

Do not edit a model card, calibration data, or simulation deck unless explicitly asked. Do not treat a fit or a single operating point as validation across untested conditions.

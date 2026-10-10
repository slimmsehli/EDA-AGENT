# Semiconductor SPC and Yield Analysis

Use this skill for statistical process control (SPC), wafer maps, parametric test, bin/yield summaries, and lot or tool comparisons.

## Analysis workflow

1. Identify the dataset, units, measurement definition, time range, lot/wafer/site identifiers, product, tool, recipe, and known exclusions.
2. Check data quality: sample counts, missing values, duplicates, censoring, unit consistency, out-of-range values, and changes in schema or collection method.
3. Define the denominator and population for every yield or failure-rate calculation. Separate wafer, die, site, lot, and retest denominators.
4. For SPC, identify the chart type and its assumptions. Do not apply control limits or capability indices without a suitable process definition and adequate, comparable data.
5. Compare groups only after stating selection criteria and sample sizes. Report practical effect sizes and uncertainty where appropriate; avoid declaring causation from correlation.
6. For wafer maps, retain coordinate conventions, orientation, bin definitions, and exclusions. Do not infer spatial causes without supporting process or equipment evidence.
7. Make charts reproducible: include source, filters, grouping, units, and calculation method. Preserve the original dataset.

## Output

Report the population, filters, denominator, sample sizes, units, method, and results. Distinguish descriptive observations, statistical signals, and causal hypotheses. Highlight data-quality issues and recommend the next measurement or stratification that can test a hypothesis.

Treat yield, lot, process, and customer-linked data as confidential. Do not upload it to external services unless explicitly authorized.

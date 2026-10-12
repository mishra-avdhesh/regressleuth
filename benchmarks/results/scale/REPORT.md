# Large-search-space study (pre-registered, one run)

Protocol: [PROTOCOL.md](../../scale/PROTOCOL.md). Synthetic oracle incidents: evidence about
scaling and cost, not external validity.

- Wrong `verified`, single and pair scenarios: **0**
- Wrong `verified`, non-monotone masked-healing control: **0**
- Feasibility at k = 12 (mean engine time < 2 s, peak traced memory < 256 MB): **passed**

| strategy | mean engine s at k=12 | max peak MB at k=12 |
|---|---:|---:|
| adaptive | 0.371 | 2.5 |
| exhaustive | 0.087 | 4.4 |
| random | 0.040 | 2.6 |
| one_factor | 0.007 | 0.1 |
| greedy | 0.058 | 3.1 |
| ddmin | 0.010 | 0.1 |

## Adaptive vs ddmin, isolation replays before a correct verified (full budget)

| scenario | k | adaptive fewer | ddmin fewer | ties | sign test p |
|---|---:|---:|---:|---:|---:|
| single | 8 | 8 | 42 | 50 | 1.16e-06 |
| single | 10 | 10 | 59 | 31 | 1.38e-09 |
| single | 12 | 5 | 60 | 35 | 4.87e-13 |
| pair | 8 | 82 | 18 | 0 | 6.15e-11 |
| pair | 10 | 87 | 9 | 4 | 3.64e-17 |
| pair | 12 | 78 | 20 | 2 | 2.87e-09 |

## All cells

| scenario | k | strategy | budget | wrong verified | correct verified | mean isolation | mean audit | mean total | engine s | statuses |
|---|---:|---|---|---:|---:|---:|---:|---:|---:|---|
| masked_healing | 8 | adaptive | 12 | **0** | 0.00 | 8.5 | 35.1 | 43.6 | 0.022 | assumption_violated 1.00 |
| masked_healing | 8 | adaptive | 16 | **0** | 0.00 | 8.5 | 35.1 | 43.6 | 0.021 | assumption_violated 1.00 |
| masked_healing | 8 | adaptive | 24 | **0** | 0.00 | 8.5 | 35.1 | 43.6 | 0.021 | assumption_violated 1.00 |
| masked_healing | 8 | adaptive | 32 | **0** | 0.00 | 8.5 | 35.1 | 43.6 | 0.021 | assumption_violated 1.00 |
| masked_healing | 8 | adaptive | 8 | **0** | 0.00 | 7.6 | 19.1 | 26.7 | 0.020 | assumption_violated 0.42, inferred 0.58 |
| masked_healing | 8 | adaptive | full | **0** | 0.00 | 8.5 | 35.1 | 43.6 | 0.021 | assumption_violated 1.00 |
| masked_healing | 8 | ddmin | 12 | **0** | 0.00 | 9.1 | 21.9 | 31.0 | 0.003 | assumption_violated 0.77, inferred 0.01, unresolved 0.22 |
| masked_healing | 8 | ddmin | 16 | **0** | 0.00 | 9.9 | 23.4 | 33.4 | 0.003 | assumption_violated 0.83, inferred 0.02, unresolved 0.15 |
| masked_healing | 8 | ddmin | 24 | **0** | 0.00 | 10.3 | 29.5 | 39.8 | 0.004 | assumption_violated 1.00 |
| masked_healing | 8 | ddmin | 32 | **0** | 0.00 | 10.3 | 29.5 | 39.8 | 0.004 | assumption_violated 1.00 |
| masked_healing | 8 | ddmin | 8 | **0** | 0.00 | 7.3 | 19.4 | 26.8 | 0.003 | assumption_violated 0.47, unresolved 0.53 |
| masked_healing | 8 | ddmin | full | **0** | 0.00 | 10.3 | 29.5 | 39.8 | 0.004 | assumption_violated 1.00 |
| masked_healing | 8 | exhaustive | 12 | **0** | 0.00 | 12.0 | 20.2 | 32.1 | 0.005 | assumption_violated 0.46, unresolved 0.54 |
| masked_healing | 8 | exhaustive | 16 | **0** | 0.00 | 15.8 | 19.0 | 34.8 | 0.005 | assumption_violated 0.52, unresolved 0.48 |
| masked_healing | 8 | exhaustive | 24 | **0** | 0.00 | 22.7 | 18.1 | 40.8 | 0.005 | assumption_violated 0.70, unresolved 0.30 |
| masked_healing | 8 | exhaustive | 32 | **0** | 0.00 | 28.7 | 13.5 | 42.2 | 0.006 | assumption_violated 0.83, unresolved 0.17 |
| masked_healing | 8 | exhaustive | 8 | **0** | 0.00 | 8.0 | 17.2 | 25.2 | 0.004 | assumption_violated 0.33, unresolved 0.67 |
| masked_healing | 8 | exhaustive | full | **0** | 0.00 | 49.5 | 0.0 | 49.5 | 0.006 | assumption_violated 1.00 |
| masked_healing | 8 | greedy | 12 | **0** | 0.00 | 9.5 | 24.6 | 34.1 | 0.006 | assumption_violated 0.46, unresolved 0.54 |
| masked_healing | 8 | greedy | 16 | **0** | 0.00 | 11.6 | 26.9 | 38.5 | 0.006 | assumption_violated 0.52, unresolved 0.48 |
| masked_healing | 8 | greedy | 24 | **0** | 0.00 | 14.9 | 32.8 | 47.7 | 0.007 | assumption_violated 0.70, unresolved 0.30 |
| masked_healing | 8 | greedy | 32 | **0** | 0.00 | 16.7 | 36.5 | 53.2 | 0.007 | assumption_violated 0.83, unresolved 0.17 |
| masked_healing | 8 | greedy | 8 | **0** | 0.00 | 7.1 | 18.0 | 25.2 | 0.005 | assumption_violated 0.33, unresolved 0.67 |
| masked_healing | 8 | greedy | full | **0** | 0.00 | 17.2 | 40.5 | 57.7 | 0.008 | assumption_violated 1.00 |
| masked_healing | 8 | one_factor | 12 | **0** | 0.00 | 8.4 | 24.6 | 33.0 | 0.003 | assumption_violated 0.46, unresolved 0.54 |
| masked_healing | 8 | one_factor | 16 | **0** | 0.00 | 8.4 | 24.6 | 33.0 | 0.003 | assumption_violated 0.46, unresolved 0.54 |
| masked_healing | 8 | one_factor | 24 | **0** | 0.00 | 8.4 | 24.6 | 33.0 | 0.003 | assumption_violated 0.46, unresolved 0.54 |
| masked_healing | 8 | one_factor | 32 | **0** | 0.00 | 8.4 | 24.6 | 33.0 | 0.003 | assumption_violated 0.46, unresolved 0.54 |
| masked_healing | 8 | one_factor | 8 | **0** | 0.00 | 7.1 | 18.0 | 25.2 | 0.003 | assumption_violated 0.33, unresolved 0.67 |
| masked_healing | 8 | one_factor | full | **0** | 0.00 | 8.4 | 24.6 | 33.0 | 0.003 | assumption_violated 0.46, unresolved 0.54 |
| masked_healing | 8 | random | 12 | **0** | 0.00 | 10.4 | 12.0 | 22.4 | 0.003 | assumption_violated 0.64, inferred 0.18, unresolved 0.18 |
| masked_healing | 8 | random | 16 | **0** | 0.00 | 11.3 | 18.0 | 29.3 | 0.004 | assumption_violated 0.91, inferred 0.03, unresolved 0.06 |
| masked_healing | 8 | random | 24 | **0** | 0.00 | 11.7 | 19.6 | 31.3 | 0.004 | assumption_violated 0.99, inferred 0.01 |
| masked_healing | 8 | random | 32 | **0** | 0.00 | 11.7 | 20.0 | 31.7 | 0.004 | assumption_violated 1.00 |
| masked_healing | 8 | random | 8 | **0** | 0.00 | 7.8 | 3.4 | 11.2 | 0.002 | assumption_violated 0.17, inferred 0.17, unresolved 0.66 |
| masked_healing | 8 | random | full | **0** | 0.00 | 11.7 | 20.0 | 31.7 | 0.004 | assumption_violated 1.00 |
| masked_healing | 10 | adaptive | 12 | **0** | 0.00 | 9.2 | 45.0 | 54.1 | 0.084 | assumption_violated 1.00 |
| masked_healing | 10 | adaptive | 16 | **0** | 0.00 | 9.2 | 45.0 | 54.1 | 0.083 | assumption_violated 1.00 |
| masked_healing | 10 | adaptive | 24 | **0** | 0.00 | 9.2 | 45.0 | 54.1 | 0.084 | assumption_violated 1.00 |
| masked_healing | 10 | adaptive | 32 | **0** | 0.00 | 9.2 | 45.0 | 54.1 | 0.083 | assumption_violated 1.00 |
| masked_healing | 10 | adaptive | 8 | **0** | 0.00 | 7.9 | 20.1 | 28.0 | 0.079 | assumption_violated 0.28, inferred 0.70, unresolved 0.02 |
| masked_healing | 10 | adaptive | full | **0** | 0.00 | 9.2 | 45.0 | 54.1 | 0.082 | assumption_violated 1.00 |
| masked_healing | 10 | ddmin | 12 | **0** | 0.00 | 9.3 | 33.7 | 43.0 | 0.005 | assumption_violated 0.65, inferred 0.01, unresolved 0.34 |
| masked_healing | 10 | ddmin | 16 | **0** | 0.00 | 10.4 | 35.1 | 45.5 | 0.005 | assumption_violated 0.79, inferred 0.06, unresolved 0.15 |
| masked_healing | 10 | ddmin | 24 | **0** | 0.00 | 11.3 | 46.7 | 58.1 | 0.006 | assumption_violated 1.00 |
| masked_healing | 10 | ddmin | 32 | **0** | 0.00 | 11.3 | 46.7 | 58.1 | 0.006 | assumption_violated 1.00 |
| masked_healing | 10 | ddmin | 8 | **0** | 0.00 | 7.4 | 29.4 | 36.8 | 0.004 | assumption_violated 0.50, unresolved 0.50 |
| masked_healing | 10 | ddmin | full | **0** | 0.00 | 11.3 | 46.7 | 58.1 | 0.006 | assumption_violated 1.00 |
| masked_healing | 10 | exhaustive | 12 | **0** | 0.00 | 12.0 | 40.2 | 52.2 | 0.013 | assumption_violated 0.49, unresolved 0.51 |
| masked_healing | 10 | exhaustive | 16 | **0** | 0.00 | 15.9 | 38.0 | 54.0 | 0.013 | assumption_violated 0.57, unresolved 0.43 |
| masked_healing | 10 | exhaustive | 24 | **0** | 0.00 | 23.2 | 34.6 | 57.9 | 0.013 | assumption_violated 0.65, unresolved 0.35 |
| masked_healing | 10 | exhaustive | 32 | **0** | 0.00 | 29.9 | 30.2 | 60.1 | 0.013 | assumption_violated 0.75, unresolved 0.25 |
| masked_healing | 10 | exhaustive | 8 | **0** | 0.00 | 8.0 | 24.9 | 32.9 | 0.011 | assumption_violated 0.29, unresolved 0.71 |
| masked_healing | 10 | exhaustive | full | **0** | 0.00 | 75.2 | 0.0 | 75.2 | 0.014 | assumption_violated 1.00 |
| masked_healing | 10 | greedy | 12 | **0** | 0.00 | 9.9 | 42.2 | 52.2 | 0.016 | assumption_violated 0.49, unresolved 0.51 |
| masked_healing | 10 | greedy | 16 | **0** | 0.00 | 11.9 | 47.5 | 59.4 | 0.017 | assumption_violated 0.57, unresolved 0.43 |
| masked_healing | 10 | greedy | 24 | **0** | 0.00 | 15.0 | 52.7 | 67.7 | 0.018 | assumption_violated 0.65, unresolved 0.35 |
| masked_healing | 10 | greedy | 32 | **0** | 0.00 | 17.4 | 58.5 | 75.9 | 0.018 | assumption_violated 0.75, unresolved 0.25 |
| masked_healing | 10 | greedy | 8 | **0** | 0.00 | 7.3 | 25.6 | 32.9 | 0.015 | assumption_violated 0.29, unresolved 0.71 |
| masked_healing | 10 | greedy | full | **0** | 0.00 | 21.1 | 69.3 | 90.4 | 0.020 | assumption_violated 1.00 |
| masked_healing | 10 | one_factor | 12 | **0** | 0.00 | 9.9 | 42.2 | 52.2 | 0.006 | assumption_violated 0.49, unresolved 0.51 |
| masked_healing | 10 | one_factor | 16 | **0** | 0.00 | 9.9 | 42.2 | 52.2 | 0.006 | assumption_violated 0.49, unresolved 0.51 |
| masked_healing | 10 | one_factor | 24 | **0** | 0.00 | 9.9 | 42.2 | 52.2 | 0.006 | assumption_violated 0.49, unresolved 0.51 |
| masked_healing | 10 | one_factor | 32 | **0** | 0.00 | 9.9 | 42.2 | 52.2 | 0.006 | assumption_violated 0.49, unresolved 0.51 |
| masked_healing | 10 | one_factor | 8 | **0** | 0.00 | 7.3 | 25.6 | 32.9 | 0.004 | assumption_violated 0.29, unresolved 0.71 |
| masked_healing | 10 | one_factor | full | **0** | 0.00 | 9.9 | 42.2 | 52.2 | 0.006 | assumption_violated 0.49, unresolved 0.51 |
| masked_healing | 10 | random | 12 | **0** | 0.00 | 10.8 | 15.4 | 26.2 | 0.010 | assumption_violated 0.49, inferred 0.19, unresolved 0.32 |
| masked_healing | 10 | random | 16 | **0** | 0.00 | 12.2 | 24.2 | 36.4 | 0.011 | assumption_violated 0.80, inferred 0.08, unresolved 0.12 |
| masked_healing | 10 | random | 24 | **0** | 0.00 | 12.9 | 31.4 | 44.3 | 0.011 | assumption_violated 0.98, inferred 0.01, unresolved 0.01 |
| masked_healing | 10 | random | 32 | **0** | 0.00 | 13.0 | 31.8 | 44.8 | 0.011 | assumption_violated 0.99, inferred 0.00, unresolved 0.00 |
| masked_healing | 10 | random | 8 | **0** | 0.00 | 7.9 | 6.5 | 14.4 | 0.009 | assumption_violated 0.16, inferred 0.11, unresolved 0.73 |
| masked_healing | 10 | random | full | **0** | 0.00 | 13.0 | 32.2 | 45.3 | 0.012 | assumption_violated 1.00 |
| masked_healing | 12 | adaptive | 12 | **0** | 0.00 | 9.5 | 79.0 | 88.5 | 0.399 | assumption_violated 1.00 |
| masked_healing | 12 | adaptive | 16 | **0** | 0.00 | 9.5 | 79.0 | 88.5 | 0.373 | assumption_violated 1.00 |
| masked_healing | 12 | adaptive | 24 | **0** | 0.00 | 9.5 | 79.0 | 88.5 | 0.364 | assumption_violated 1.00 |
| masked_healing | 12 | adaptive | 32 | **0** | 0.00 | 9.5 | 79.0 | 88.5 | 0.362 | assumption_violated 1.00 |
| masked_healing | 12 | adaptive | 8 | **0** | 0.00 | 7.9 | 39.0 | 46.9 | 0.345 | assumption_violated 0.30, inferred 0.30, unresolved 0.40 |
| masked_healing | 12 | adaptive | full | **0** | 0.00 | 9.5 | 79.0 | 88.5 | 0.370 | assumption_violated 1.00 |
| masked_healing | 12 | ddmin | 12 | **0** | 0.00 | 9.7 | 54.0 | 63.6 | 0.006 | assumption_violated 0.62, inferred 0.02, unresolved 0.36 |
| masked_healing | 12 | ddmin | 16 | **0** | 0.00 | 11.0 | 59.5 | 70.5 | 0.007 | assumption_violated 0.74, inferred 0.02, unresolved 0.24 |
| masked_healing | 12 | ddmin | 24 | **0** | 0.00 | 12.2 | 79.9 | 92.1 | 0.008 | assumption_violated 0.96, inferred 0.01, unresolved 0.03 |
| masked_healing | 12 | ddmin | 32 | **0** | 0.00 | 12.3 | 84.2 | 96.5 | 0.009 | assumption_violated 1.00 |
| masked_healing | 12 | ddmin | 8 | **0** | 0.00 | 7.6 | 41.1 | 48.7 | 0.005 | assumption_violated 0.39, inferred 0.02, unresolved 0.59 |
| masked_healing | 12 | ddmin | full | **0** | 0.00 | 12.3 | 84.2 | 96.5 | 0.009 | assumption_violated 1.00 |
| masked_healing | 12 | exhaustive | 12 | **0** | 0.00 | 12.0 | 43.4 | 55.4 | 0.039 | assumption_violated 0.35, unresolved 0.65 |
| masked_healing | 12 | exhaustive | 16 | **0** | 0.00 | 16.0 | 57.1 | 73.1 | 0.039 | assumption_violated 0.48, unresolved 0.52 |
| masked_healing | 12 | exhaustive | 24 | **0** | 0.00 | 23.6 | 53.6 | 77.2 | 0.040 | assumption_violated 0.58, unresolved 0.42 |
| masked_healing | 12 | exhaustive | 32 | **0** | 0.00 | 30.8 | 49.7 | 80.5 | 0.040 | assumption_violated 0.61, unresolved 0.39 |
| masked_healing | 12 | exhaustive | 8 | **0** | 0.00 | 8.0 | 28.2 | 36.2 | 0.041 | assumption_violated 0.22, unresolved 0.78 |
| masked_healing | 12 | exhaustive | full | **0** | 0.00 | 126.1 | 0.0 | 126.1 | 0.042 | assumption_violated 1.00 |
| masked_healing | 12 | greedy | 12 | **0** | 0.00 | 10.3 | 45.1 | 55.4 | 0.051 | assumption_violated 0.35, unresolved 0.65 |
| masked_healing | 12 | greedy | 16 | **0** | 0.00 | 12.6 | 60.4 | 73.0 | 0.051 | assumption_violated 0.48, unresolved 0.52 |
| masked_healing | 12 | greedy | 24 | **0** | 0.00 | 16.4 | 70.6 | 87.0 | 0.052 | assumption_violated 0.58, unresolved 0.42 |
| masked_healing | 12 | greedy | 32 | **0** | 0.00 | 19.6 | 73.6 | 93.2 | 0.051 | assumption_violated 0.61, unresolved 0.39 |
| masked_healing | 12 | greedy | 8 | **0** | 0.00 | 7.4 | 28.8 | 36.2 | 0.055 | assumption_violated 0.22, unresolved 0.78 |
| masked_healing | 12 | greedy | full | **0** | 0.00 | 29.8 | 101.2 | 130.9 | 0.053 | assumption_violated 1.00 |
| masked_healing | 12 | one_factor | 12 | **0** | 0.00 | 10.3 | 45.1 | 55.4 | 0.006 | assumption_violated 0.35, unresolved 0.65 |
| masked_healing | 12 | one_factor | 16 | **0** | 0.00 | 11.6 | 57.3 | 68.9 | 0.007 | assumption_violated 0.45, unresolved 0.55 |
| masked_healing | 12 | one_factor | 24 | **0** | 0.00 | 11.6 | 57.3 | 68.9 | 0.007 | assumption_violated 0.45, unresolved 0.55 |
| masked_healing | 12 | one_factor | 32 | **0** | 0.00 | 11.6 | 57.3 | 68.9 | 0.007 | assumption_violated 0.45, unresolved 0.55 |
| masked_healing | 12 | one_factor | 8 | **0** | 0.00 | 7.4 | 28.8 | 36.2 | 0.005 | assumption_violated 0.22, unresolved 0.78 |
| masked_healing | 12 | one_factor | full | **0** | 0.00 | 11.6 | 57.3 | 68.9 | 0.007 | assumption_violated 0.45, unresolved 0.55 |
| masked_healing | 12 | random | 12 | **0** | 0.00 | 11.0 | 15.1 | 26.1 | 0.034 | assumption_violated 0.44, inferred 0.16, unresolved 0.40 |
| masked_healing | 12 | random | 16 | **0** | 0.00 | 12.7 | 29.1 | 41.8 | 0.035 | assumption_violated 0.76, inferred 0.11, unresolved 0.14 |
| masked_healing | 12 | random | 24 | **0** | 0.00 | 13.6 | 43.0 | 56.5 | 0.036 | assumption_violated 0.99, inferred 0.00, unresolved 0.00 |
| masked_healing | 12 | random | 32 | **0** | 0.00 | 13.6 | 43.4 | 57.0 | 0.036 | assumption_violated 1.00, unresolved 0.00 |
| masked_healing | 12 | random | 8 | **0** | 0.00 | 7.9 | 5.8 | 13.7 | 0.033 | assumption_violated 0.10, inferred 0.10, unresolved 0.80 |
| masked_healing | 12 | random | full | **0** | 0.00 | 13.7 | 43.6 | 57.3 | 0.035 | assumption_violated 1.00 |
| pair | 8 | adaptive | 12 | **0** | 1.00 | 9.1 | 43.2 | 52.3 | 0.022 | verified 1.00 |
| pair | 8 | adaptive | 16 | **0** | 1.00 | 9.1 | 43.2 | 52.3 | 0.022 | verified 1.00 |
| pair | 8 | adaptive | 24 | **0** | 1.00 | 9.1 | 43.2 | 52.3 | 0.022 | verified 1.00 |
| pair | 8 | adaptive | 32 | **0** | 1.00 | 9.1 | 43.2 | 52.3 | 0.021 | verified 1.00 |
| pair | 8 | adaptive | 8 | **0** | 0.21 | 7.9 | 9.0 | 17.0 | 0.019 | inferred 0.79, verified 0.21 |
| pair | 8 | adaptive | full | **0** | 1.00 | 9.1 | 43.2 | 52.3 | 0.022 | verified 1.00 |
| pair | 8 | ddmin | 12 | **0** | 0.32 | 11.0 | 13.3 | 24.3 | 0.003 | inferred 0.05, unresolved 0.63, verified 0.32 |
| pair | 8 | ddmin | 16 | **0** | 0.47 | 13.5 | 19.1 | 32.6 | 0.003 | inferred 0.04, unresolved 0.49, verified 0.47 |
| pair | 8 | ddmin | 24 | **0** | 1.00 | 14.7 | 39.3 | 54.0 | 0.005 | verified 1.00 |
| pair | 8 | ddmin | 32 | **0** | 1.00 | 14.7 | 39.3 | 54.0 | 0.005 | verified 1.00 |
| pair | 8 | ddmin | 8 | **0** | 0.18 | 7.8 | 7.7 | 15.4 | 0.002 | unresolved 0.82, verified 0.18 |
| pair | 8 | ddmin | full | **0** | 1.00 | 14.7 | 39.3 | 54.0 | 0.005 | verified 1.00 |
| pair | 8 | exhaustive | 12 | **0** | 0.11 | 12.0 | 4.2 | 16.2 | 0.004 | unresolved 0.89, verified 0.11 |
| pair | 8 | exhaustive | 16 | **0** | 0.27 | 16.0 | 10.3 | 26.3 | 0.004 | unresolved 0.73, verified 0.27 |
| pair | 8 | exhaustive | 24 | **0** | 0.58 | 24.0 | 18.9 | 43.0 | 0.006 | unresolved 0.42, verified 0.58 |
| pair | 8 | exhaustive | 32 | **0** | 0.87 | 32.0 | 23.4 | 55.4 | 0.007 | unresolved 0.13, verified 0.87 |
| pair | 8 | exhaustive | 8 | **0** | 0.00 | 8.0 | 0.0 | 8.0 | 0.003 | unresolved 1.00 |
| pair | 8 | exhaustive | full | **0** | 1.00 | 256.0 | 0.0 | 256.0 | 0.024 | verified 1.00 |
| pair | 8 | greedy | 12 | **0** | 0.11 | 11.9 | 4.2 | 16.1 | 0.004 | unresolved 0.89, verified 0.11 |
| pair | 8 | greedy | 16 | **0** | 0.27 | 15.3 | 10.3 | 25.5 | 0.005 | unresolved 0.73, verified 0.27 |
| pair | 8 | greedy | 24 | **0** | 0.58 | 20.0 | 20.5 | 40.5 | 0.006 | unresolved 0.42, verified 0.58 |
| pair | 8 | greedy | 32 | **0** | 0.87 | 22.5 | 28.5 | 51.0 | 0.007 | unresolved 0.13, verified 0.87 |
| pair | 8 | greedy | 8 | **0** | 0.00 | 8.0 | 0.0 | 8.0 | 0.004 | unresolved 1.00 |
| pair | 8 | greedy | full | **0** | 1.00 | 22.8 | 31.6 | 54.4 | 0.008 | verified 1.00 |
| pair | 8 | one_factor | 12 | **0** | 0.00 | 10.0 | 0.0 | 10.0 | 0.001 | unresolved 1.00 |
| pair | 8 | one_factor | 16 | **0** | 0.00 | 10.0 | 0.0 | 10.0 | 0.002 | unresolved 1.00 |
| pair | 8 | one_factor | 24 | **0** | 0.00 | 10.0 | 0.0 | 10.0 | 0.001 | unresolved 1.00 |
| pair | 8 | one_factor | 32 | **0** | 0.00 | 10.0 | 0.0 | 10.0 | 0.002 | unresolved 1.00 |
| pair | 8 | one_factor | 8 | **0** | 0.00 | 8.0 | 0.0 | 8.0 | 0.001 | unresolved 1.00 |
| pair | 8 | one_factor | full | **0** | 0.00 | 10.0 | 0.0 | 10.0 | 0.001 | unresolved 1.00 |
| pair | 8 | random | 12 | **0** | 0.35 | 11.5 | 15.0 | 26.6 | 0.004 | inferred 0.32, unresolved 0.33, verified 0.35 |
| pair | 8 | random | 16 | **0** | 0.74 | 13.5 | 31.7 | 45.1 | 0.005 | inferred 0.09, unresolved 0.17, verified 0.74 |
| pair | 8 | random | 24 | **0** | 0.98 | 14.7 | 41.7 | 56.3 | 0.006 | inferred 0.02, verified 0.98 |
| pair | 8 | random | 32 | **0** | 1.00 | 14.7 | 42.4 | 57.1 | 0.006 | verified 1.00 |
| pair | 8 | random | 8 | **0** | 0.02 | 8.0 | 0.9 | 8.9 | 0.002 | inferred 0.21, unresolved 0.77, verified 0.02 |
| pair | 8 | random | full | **0** | 1.00 | 14.7 | 42.4 | 57.1 | 0.006 | verified 1.00 |
| pair | 10 | adaptive | 12 | **0** | 1.00 | 10.1 | 73.2 | 83.3 | 0.085 | verified 1.00 |
| pair | 10 | adaptive | 16 | **0** | 1.00 | 10.1 | 73.2 | 83.3 | 0.085 | verified 1.00 |
| pair | 10 | adaptive | 24 | **0** | 1.00 | 10.1 | 73.2 | 83.3 | 0.085 | verified 1.00 |
| pair | 10 | adaptive | 32 | **0** | 1.00 | 10.1 | 73.2 | 83.3 | 0.086 | verified 1.00 |
| pair | 10 | adaptive | 8 | **0** | 0.05 | 8.0 | 3.6 | 11.7 | 0.078 | inferred 0.90, unresolved 0.05, verified 0.05 |
| pair | 10 | adaptive | full | **0** | 1.00 | 10.1 | 73.2 | 83.3 | 0.086 | verified 1.00 |
| pair | 10 | ddmin | 12 | **0** | 0.22 | 11.5 | 16.0 | 27.4 | 0.003 | inferred 0.03, unresolved 0.75, verified 0.22 |
| pair | 10 | ddmin | 16 | **0** | 0.31 | 14.5 | 22.2 | 36.7 | 0.004 | inferred 0.03, unresolved 0.66, verified 0.31 |
| pair | 10 | ddmin | 24 | **0** | 0.91 | 18.4 | 63.3 | 81.7 | 0.008 | inferred 0.02, unresolved 0.07, verified 0.91 |
| pair | 10 | ddmin | 32 | **0** | 1.00 | 18.5 | 69.4 | 87.9 | 0.009 | verified 1.00 |
| pair | 10 | ddmin | 8 | **0** | 0.09 | 8.0 | 6.6 | 14.6 | 0.002 | unresolved 0.91, verified 0.09 |
| pair | 10 | ddmin | full | **0** | 1.00 | 18.5 | 69.4 | 87.9 | 0.009 | verified 1.00 |
| pair | 10 | exhaustive | 12 | **0** | 0.00 | 12.0 | 0.0 | 12.0 | 0.009 | unresolved 1.00 |
| pair | 10 | exhaustive | 16 | **0** | 0.06 | 16.0 | 4.0 | 20.0 | 0.010 | unresolved 0.94, verified 0.06 |
| pair | 10 | exhaustive | 24 | **0** | 0.23 | 24.0 | 14.4 | 38.4 | 0.011 | unresolved 0.77, verified 0.23 |
| pair | 10 | exhaustive | 32 | **0** | 0.35 | 32.0 | 19.8 | 51.8 | 0.012 | unresolved 0.65, verified 0.35 |
| pair | 10 | exhaustive | 8 | **0** | 0.00 | 8.0 | 0.0 | 8.0 | 0.009 | unresolved 1.00 |
| pair | 10 | exhaustive | full | **0** | 1.00 | 1024.0 | 0.0 | 1024.0 | 0.107 | verified 1.00 |
| pair | 10 | greedy | 12 | **0** | 0.00 | 12.0 | 0.0 | 12.0 | 0.012 | unresolved 1.00 |
| pair | 10 | greedy | 16 | **0** | 0.06 | 15.9 | 4.0 | 19.9 | 0.013 | unresolved 0.94, verified 0.06 |
| pair | 10 | greedy | 24 | **0** | 0.23 | 22.8 | 14.9 | 37.7 | 0.015 | unresolved 0.77, verified 0.23 |
| pair | 10 | greedy | 32 | **0** | 0.35 | 28.4 | 21.9 | 50.3 | 0.016 | unresolved 0.65, verified 0.35 |
| pair | 10 | greedy | 8 | **0** | 0.00 | 8.0 | 0.0 | 8.0 | 0.012 | unresolved 1.00 |
| pair | 10 | greedy | full | **0** | 1.00 | 36.7 | 51.1 | 87.8 | 0.019 | verified 1.00 |
| pair | 10 | one_factor | 12 | **0** | 0.00 | 12.0 | 0.0 | 12.0 | 0.002 | unresolved 1.00 |
| pair | 10 | one_factor | 16 | **0** | 0.00 | 12.0 | 0.0 | 12.0 | 0.002 | unresolved 1.00 |
| pair | 10 | one_factor | 24 | **0** | 0.00 | 12.0 | 0.0 | 12.0 | 0.002 | unresolved 1.00 |
| pair | 10 | one_factor | 32 | **0** | 0.00 | 12.0 | 0.0 | 12.0 | 0.002 | unresolved 1.00 |
| pair | 10 | one_factor | 8 | **0** | 0.00 | 8.0 | 0.0 | 8.0 | 0.002 | unresolved 1.00 |
| pair | 10 | one_factor | full | **0** | 0.00 | 12.0 | 0.0 | 12.0 | 0.002 | unresolved 1.00 |
| pair | 10 | random | 12 | **0** | 0.19 | 11.8 | 13.6 | 25.4 | 0.009 | inferred 0.29, unresolved 0.53, verified 0.19 |
| pair | 10 | random | 16 | **0** | 0.52 | 14.5 | 38.0 | 52.5 | 0.012 | inferred 0.21, unresolved 0.27, verified 0.52 |
| pair | 10 | random | 24 | **0** | 0.94 | 16.5 | 68.5 | 85.0 | 0.015 | inferred 0.03, unresolved 0.03, verified 0.94 |
| pair | 10 | random | 32 | **0** | 0.98 | 16.8 | 71.4 | 88.2 | 0.015 | inferred 0.02, unresolved 0.01, verified 0.98 |
| pair | 10 | random | 8 | **0** | 0.00 | 8.0 | 0.0 | 8.0 | 0.008 | inferred 0.11, unresolved 0.89 |
| pair | 10 | random | full | **0** | 1.00 | 16.9 | 73.0 | 89.9 | 0.015 | verified 1.00 |
| pair | 12 | adaptive | 12 | **0** | 1.00 | 10.7 | 111.2 | 121.9 | 0.389 | verified 1.00 |
| pair | 12 | adaptive | 16 | **0** | 1.00 | 10.7 | 111.2 | 121.9 | 0.385 | verified 1.00 |
| pair | 12 | adaptive | 24 | **0** | 1.00 | 10.7 | 111.2 | 121.9 | 0.391 | verified 1.00 |
| pair | 12 | adaptive | 32 | **0** | 1.00 | 10.7 | 111.2 | 121.9 | 0.395 | verified 1.00 |
| pair | 12 | adaptive | 8 | **0** | 0.01 | 8.0 | 1.1 | 9.1 | 0.359 | inferred 0.49, unresolved 0.50, verified 0.01 |
| pair | 12 | adaptive | full | **0** | 1.00 | 10.7 | 111.2 | 121.9 | 0.376 | verified 1.00 |
| pair | 12 | ddmin | 12 | **0** | 0.24 | 11.5 | 26.5 | 38.0 | 0.004 | inferred 0.05, unresolved 0.71, verified 0.24 |
| pair | 12 | ddmin | 16 | **0** | 0.41 | 14.3 | 45.0 | 59.3 | 0.006 | inferred 0.01, unresolved 0.58, verified 0.41 |
| pair | 12 | ddmin | 24 | **0** | 0.90 | 17.4 | 97.5 | 115.0 | 0.012 | inferred 0.01, unresolved 0.09, verified 0.90 |
| pair | 12 | ddmin | 32 | **0** | 1.00 | 17.7 | 108.2 | 125.9 | 0.013 | verified 1.00 |
| pair | 12 | ddmin | 8 | **0** | 0.04 | 8.0 | 4.4 | 12.4 | 0.002 | inferred 0.05, unresolved 0.91, verified 0.04 |
| pair | 12 | ddmin | full | **0** | 1.00 | 17.7 | 108.2 | 125.9 | 0.013 | verified 1.00 |
| pair | 12 | exhaustive | 12 | **0** | 0.00 | 12.0 | 0.0 | 12.0 | 0.037 | unresolved 1.00 |
| pair | 12 | exhaustive | 16 | **0** | 0.01 | 16.0 | 1.0 | 17.0 | 0.037 | unresolved 0.99, verified 0.01 |
| pair | 12 | exhaustive | 24 | **0** | 0.12 | 24.0 | 12.2 | 36.2 | 0.039 | unresolved 0.88, verified 0.12 |
| pair | 12 | exhaustive | 32 | **0** | 0.26 | 32.0 | 24.5 | 56.5 | 0.041 | unresolved 0.74, verified 0.26 |
| pair | 12 | exhaustive | 8 | **0** | 0.00 | 8.0 | 0.0 | 8.0 | 0.041 | unresolved 1.00 |
| pair | 12 | exhaustive | full | **0** | 1.00 | 4096.0 | 0.0 | 4096.0 | 0.458 | verified 1.00 |
| pair | 12 | greedy | 12 | **0** | 0.00 | 12.0 | 0.0 | 12.0 | 0.053 | unresolved 1.00 |
| pair | 12 | greedy | 16 | **0** | 0.01 | 16.0 | 1.0 | 17.0 | 0.054 | unresolved 0.99, verified 0.01 |
| pair | 12 | greedy | 24 | **0** | 0.12 | 23.6 | 12.2 | 35.9 | 0.056 | unresolved 0.88, verified 0.12 |
| pair | 12 | greedy | 32 | **0** | 0.26 | 30.3 | 25.3 | 55.5 | 0.058 | unresolved 0.74, verified 0.26 |
| pair | 12 | greedy | 8 | **0** | 0.00 | 8.0 | 0.0 | 8.0 | 0.057 | unresolved 1.00 |
| pair | 12 | greedy | full | **0** | 1.00 | 50.8 | 77.0 | 127.8 | 0.065 | verified 1.00 |
| pair | 12 | one_factor | 12 | **0** | 0.00 | 12.0 | 0.0 | 12.0 | 0.002 | unresolved 1.00 |
| pair | 12 | one_factor | 16 | **0** | 0.00 | 14.0 | 0.0 | 14.0 | 0.003 | unresolved 1.00 |
| pair | 12 | one_factor | 24 | **0** | 0.00 | 14.0 | 0.0 | 14.0 | 0.003 | unresolved 1.00 |
| pair | 12 | one_factor | 32 | **0** | 0.00 | 14.0 | 0.0 | 14.0 | 0.003 | unresolved 1.00 |
| pair | 12 | one_factor | 8 | **0** | 0.00 | 8.0 | 0.0 | 8.0 | 0.002 | unresolved 1.00 |
| pair | 12 | one_factor | full | **0** | 0.00 | 14.0 | 0.0 | 14.0 | 0.003 | unresolved 1.00 |
| pair | 12 | random | 12 | **0** | 0.14 | 11.9 | 15.2 | 27.1 | 0.036 | inferred 0.30, unresolved 0.56, verified 0.14 |
| pair | 12 | random | 16 | **0** | 0.53 | 14.7 | 59.2 | 73.9 | 0.041 | inferred 0.21, unresolved 0.26, verified 0.53 |
| pair | 12 | random | 24 | **0** | 0.94 | 16.7 | 104.7 | 121.4 | 0.046 | inferred 0.04, unresolved 0.02, verified 0.94 |
| pair | 12 | random | 32 | **0** | 0.99 | 16.9 | 110.0 | 127.0 | 0.046 | inferred 0.01, unresolved 0.01, verified 0.99 |
| pair | 12 | random | 8 | **0** | 0.00 | 8.0 | 0.0 | 8.0 | 0.035 | inferred 0.08, unresolved 0.92 |
| pair | 12 | random | full | **0** | 1.00 | 17.2 | 111.6 | 128.7 | 0.046 | verified 1.00 |
| single | 8 | adaptive | 12 | **0** | 1.00 | 6.7 | 54.9 | 61.7 | 0.027 | verified 1.00 |
| single | 8 | adaptive | 16 | **0** | 1.00 | 6.7 | 54.9 | 61.7 | 0.024 | verified 1.00 |
| single | 8 | adaptive | 24 | **0** | 1.00 | 6.7 | 54.9 | 61.7 | 0.024 | verified 1.00 |
| single | 8 | adaptive | 32 | **0** | 1.00 | 6.7 | 54.9 | 61.7 | 0.024 | verified 1.00 |
| single | 8 | adaptive | 8 | **0** | 1.00 | 6.7 | 54.9 | 61.7 | 0.031 | verified 1.00 |
| single | 8 | adaptive | full | **0** | 1.00 | 6.7 | 54.9 | 61.7 | 0.024 | verified 1.00 |
| single | 8 | ddmin | 12 | **0** | 1.00 | 6.4 | 55.1 | 61.5 | 0.006 | verified 1.00 |
| single | 8 | ddmin | 16 | **0** | 1.00 | 6.4 | 55.1 | 61.5 | 0.006 | verified 1.00 |
| single | 8 | ddmin | 24 | **0** | 1.00 | 6.4 | 55.1 | 61.5 | 0.006 | verified 1.00 |
| single | 8 | ddmin | 32 | **0** | 1.00 | 6.4 | 55.1 | 61.5 | 0.006 | verified 1.00 |
| single | 8 | ddmin | 8 | **0** | 1.00 | 6.4 | 55.1 | 61.5 | 0.006 | verified 1.00 |
| single | 8 | ddmin | full | **0** | 1.00 | 6.4 | 55.1 | 61.5 | 0.006 | verified 1.00 |
| single | 8 | exhaustive | 12 | **0** | 1.00 | 12.0 | 48.0 | 60.0 | 0.008 | verified 1.00 |
| single | 8 | exhaustive | 16 | **0** | 1.00 | 16.0 | 44.0 | 60.0 | 0.008 | verified 1.00 |
| single | 8 | exhaustive | 24 | **0** | 1.00 | 24.0 | 36.0 | 60.0 | 0.008 | verified 1.00 |
| single | 8 | exhaustive | 32 | **0** | 1.00 | 32.0 | 28.0 | 60.0 | 0.008 | verified 1.00 |
| single | 8 | exhaustive | 8 | **0** | 0.80 | 8.0 | 41.6 | 49.6 | 0.008 | unresolved 0.20, verified 0.80 |
| single | 8 | exhaustive | full | **0** | 1.00 | 256.0 | 0.0 | 256.0 | 0.029 | verified 1.00 |
| single | 8 | greedy | 12 | **0** | 1.00 | 6.3 | 53.7 | 60.0 | 0.009 | verified 1.00 |
| single | 8 | greedy | 16 | **0** | 1.00 | 6.3 | 53.7 | 60.0 | 0.009 | verified 1.00 |
| single | 8 | greedy | 24 | **0** | 1.00 | 6.3 | 53.7 | 60.0 | 0.009 | verified 1.00 |
| single | 8 | greedy | 32 | **0** | 1.00 | 6.3 | 53.7 | 60.0 | 0.009 | verified 1.00 |
| single | 8 | greedy | 8 | **0** | 0.80 | 6.0 | 43.6 | 49.6 | 0.008 | unresolved 0.20, verified 0.80 |
| single | 8 | greedy | full | **0** | 1.00 | 6.3 | 53.7 | 60.0 | 0.009 | verified 1.00 |
| single | 8 | one_factor | 12 | **0** | 1.00 | 6.3 | 53.7 | 60.0 | 0.006 | verified 1.00 |
| single | 8 | one_factor | 16 | **0** | 1.00 | 6.3 | 53.7 | 60.0 | 0.006 | verified 1.00 |
| single | 8 | one_factor | 24 | **0** | 1.00 | 6.3 | 53.7 | 60.0 | 0.006 | verified 1.00 |
| single | 8 | one_factor | 32 | **0** | 1.00 | 6.3 | 53.7 | 60.0 | 0.006 | verified 1.00 |
| single | 8 | one_factor | 8 | **0** | 0.80 | 6.0 | 43.6 | 49.6 | 0.005 | unresolved 0.20, verified 0.80 |
| single | 8 | one_factor | full | **0** | 1.00 | 6.3 | 53.7 | 60.0 | 0.006 | verified 1.00 |
| single | 8 | random | 12 | **0** | 0.75 | 9.5 | 41.6 | 51.1 | 0.007 | inferred 0.05, unresolved 0.20, verified 0.75 |
| single | 8 | random | 16 | **0** | 0.96 | 10.1 | 53.2 | 63.2 | 0.008 | inferred 0.02, unresolved 0.02, verified 0.96 |
| single | 8 | random | 24 | **0** | 1.00 | 10.1 | 55.4 | 65.5 | 0.008 | verified 1.00 |
| single | 8 | random | 32 | **0** | 1.00 | 10.1 | 55.4 | 65.5 | 0.008 | verified 1.00 |
| single | 8 | random | 8 | **0** | 0.31 | 7.5 | 17.2 | 24.7 | 0.004 | inferred 0.20, unresolved 0.49, verified 0.31 |
| single | 8 | random | full | **0** | 1.00 | 10.1 | 55.4 | 65.5 | 0.008 | verified 1.00 |
| single | 10 | adaptive | 12 | **0** | 1.00 | 7.5 | 89.2 | 96.7 | 0.097 | verified 1.00 |
| single | 10 | adaptive | 16 | **0** | 1.00 | 7.5 | 89.2 | 96.7 | 0.086 | verified 1.00 |
| single | 10 | adaptive | 24 | **0** | 1.00 | 7.5 | 89.2 | 96.7 | 0.086 | verified 1.00 |
| single | 10 | adaptive | 32 | **0** | 1.00 | 7.5 | 89.2 | 96.7 | 0.086 | verified 1.00 |
| single | 10 | adaptive | 8 | **0** | 1.00 | 7.5 | 89.2 | 96.7 | 0.093 | verified 1.00 |
| single | 10 | adaptive | full | **0** | 1.00 | 7.5 | 89.2 | 96.7 | 0.086 | verified 1.00 |
| single | 10 | ddmin | 12 | **0** | 1.00 | 6.9 | 88.9 | 95.8 | 0.009 | verified 1.00 |
| single | 10 | ddmin | 16 | **0** | 1.00 | 6.9 | 88.9 | 95.8 | 0.009 | verified 1.00 |
| single | 10 | ddmin | 24 | **0** | 1.00 | 6.9 | 88.9 | 95.8 | 0.009 | verified 1.00 |
| single | 10 | ddmin | 32 | **0** | 1.00 | 6.9 | 88.9 | 95.8 | 0.009 | verified 1.00 |
| single | 10 | ddmin | 8 | **0** | 1.00 | 6.9 | 88.9 | 95.8 | 0.009 | verified 1.00 |
| single | 10 | ddmin | full | **0** | 1.00 | 6.9 | 88.9 | 95.8 | 0.009 | verified 1.00 |
| single | 10 | exhaustive | 12 | **0** | 1.00 | 12.0 | 82.0 | 94.0 | 0.016 | verified 1.00 |
| single | 10 | exhaustive | 16 | **0** | 1.00 | 16.0 | 78.0 | 94.0 | 0.016 | verified 1.00 |
| single | 10 | exhaustive | 24 | **0** | 1.00 | 24.0 | 70.0 | 94.0 | 0.016 | verified 1.00 |
| single | 10 | exhaustive | 32 | **0** | 1.00 | 32.0 | 62.0 | 94.0 | 0.016 | verified 1.00 |
| single | 10 | exhaustive | 8 | **0** | 0.63 | 8.0 | 54.2 | 62.2 | 0.015 | unresolved 0.37, verified 0.63 |
| single | 10 | exhaustive | full | **0** | 1.00 | 1024.0 | 0.0 | 1024.0 | 0.107 | verified 1.00 |
| single | 10 | greedy | 12 | **0** | 1.00 | 7.2 | 86.8 | 94.0 | 0.019 | verified 1.00 |
| single | 10 | greedy | 16 | **0** | 1.00 | 7.2 | 86.8 | 94.0 | 0.020 | verified 1.00 |
| single | 10 | greedy | 24 | **0** | 1.00 | 7.2 | 86.8 | 94.0 | 0.021 | verified 1.00 |
| single | 10 | greedy | 32 | **0** | 1.00 | 7.2 | 86.8 | 94.0 | 0.020 | verified 1.00 |
| single | 10 | greedy | 8 | **0** | 0.63 | 6.3 | 55.9 | 62.2 | 0.017 | unresolved 0.37, verified 0.63 |
| single | 10 | greedy | full | **0** | 1.00 | 7.2 | 86.8 | 94.0 | 0.019 | verified 1.00 |
| single | 10 | one_factor | 12 | **0** | 1.00 | 7.2 | 86.8 | 94.0 | 0.009 | verified 1.00 |
| single | 10 | one_factor | 16 | **0** | 1.00 | 7.2 | 86.8 | 94.0 | 0.009 | verified 1.00 |
| single | 10 | one_factor | 24 | **0** | 1.00 | 7.2 | 86.8 | 94.0 | 0.009 | verified 1.00 |
| single | 10 | one_factor | 32 | **0** | 1.00 | 7.2 | 86.8 | 94.0 | 0.009 | verified 1.00 |
| single | 10 | one_factor | 8 | **0** | 0.63 | 6.3 | 55.9 | 62.2 | 0.006 | unresolved 0.37, verified 0.63 |
| single | 10 | one_factor | full | **0** | 1.00 | 7.2 | 86.8 | 94.0 | 0.009 | verified 1.00 |
| single | 10 | random | 12 | **0** | 0.72 | 9.7 | 64.8 | 74.5 | 0.014 | inferred 0.07, unresolved 0.21, verified 0.72 |
| single | 10 | random | 16 | **0** | 0.85 | 10.5 | 76.9 | 87.5 | 0.015 | inferred 0.07, unresolved 0.08, verified 0.85 |
| single | 10 | random | 24 | **0** | 1.00 | 11.0 | 90.3 | 101.4 | 0.016 | verified 1.00 |
| single | 10 | random | 32 | **0** | 1.00 | 11.0 | 90.3 | 101.4 | 0.016 | verified 1.00 |
| single | 10 | random | 8 | **0** | 0.34 | 7.8 | 30.6 | 38.4 | 0.011 | inferred 0.15, unresolved 0.51, verified 0.34 |
| single | 10 | random | full | **0** | 1.00 | 11.0 | 90.3 | 101.4 | 0.016 | verified 1.00 |
| single | 12 | adaptive | 12 | **0** | 1.00 | 7.8 | 131.2 | 139.0 | 0.411 | verified 1.00 |
| single | 12 | adaptive | 16 | **0** | 1.00 | 7.8 | 131.2 | 139.0 | 0.350 | verified 1.00 |
| single | 12 | adaptive | 24 | **0** | 1.00 | 7.8 | 131.2 | 139.0 | 0.348 | verified 1.00 |
| single | 12 | adaptive | 32 | **0** | 1.00 | 7.8 | 131.2 | 139.0 | 0.348 | verified 1.00 |
| single | 12 | adaptive | 8 | **0** | 1.00 | 7.8 | 131.2 | 139.0 | 0.350 | verified 1.00 |
| single | 12 | adaptive | full | **0** | 1.00 | 7.8 | 131.2 | 139.0 | 0.369 | verified 1.00 |
| single | 12 | ddmin | 12 | **0** | 1.00 | 7.3 | 130.7 | 137.9 | 0.014 | verified 1.00 |
| single | 12 | ddmin | 16 | **0** | 1.00 | 7.3 | 130.7 | 137.9 | 0.014 | verified 1.00 |
| single | 12 | ddmin | 24 | **0** | 1.00 | 7.3 | 130.7 | 137.9 | 0.014 | verified 1.00 |
| single | 12 | ddmin | 32 | **0** | 1.00 | 7.3 | 130.7 | 137.9 | 0.014 | verified 1.00 |
| single | 12 | ddmin | 8 | **0** | 0.95 | 7.2 | 124.2 | 131.4 | 0.013 | unresolved 0.05, verified 0.95 |
| single | 12 | ddmin | full | **0** | 1.00 | 7.3 | 130.7 | 137.9 | 0.014 | verified 1.00 |
| single | 12 | exhaustive | 12 | **0** | 0.89 | 12.0 | 110.4 | 122.4 | 0.047 | unresolved 0.11, verified 0.89 |
| single | 12 | exhaustive | 16 | **0** | 1.00 | 16.0 | 120.0 | 136.0 | 0.047 | verified 1.00 |
| single | 12 | exhaustive | 24 | **0** | 1.00 | 24.0 | 112.0 | 136.0 | 0.046 | verified 1.00 |
| single | 12 | exhaustive | 32 | **0** | 1.00 | 32.0 | 104.0 | 136.0 | 0.047 | verified 1.00 |
| single | 12 | exhaustive | 8 | **0** | 0.50 | 8.0 | 64.0 | 72.0 | 0.047 | unresolved 0.50, verified 0.50 |
| single | 12 | exhaustive | full | **0** | 1.00 | 4096.0 | 0.0 | 4096.0 | 0.442 | verified 1.00 |
| single | 12 | greedy | 12 | **0** | 0.89 | 8.2 | 114.2 | 122.4 | 0.065 | unresolved 0.11, verified 0.89 |
| single | 12 | greedy | 16 | **0** | 1.00 | 8.4 | 127.6 | 136.0 | 0.063 | verified 1.00 |
| single | 12 | greedy | 24 | **0** | 1.00 | 8.4 | 127.6 | 136.0 | 0.063 | verified 1.00 |
| single | 12 | greedy | 32 | **0** | 1.00 | 8.4 | 127.6 | 136.0 | 0.063 | verified 1.00 |
| single | 12 | greedy | 8 | **0** | 0.50 | 6.9 | 65.1 | 72.0 | 0.069 | unresolved 0.50, verified 0.50 |
| single | 12 | greedy | full | **0** | 1.00 | 8.4 | 127.6 | 136.0 | 0.063 | verified 1.00 |
| single | 12 | one_factor | 12 | **0** | 0.89 | 8.2 | 114.2 | 122.4 | 0.012 | unresolved 0.11, verified 0.89 |
| single | 12 | one_factor | 16 | **0** | 1.00 | 8.4 | 127.6 | 136.0 | 0.014 | verified 1.00 |
| single | 12 | one_factor | 24 | **0** | 1.00 | 8.4 | 127.6 | 136.0 | 0.014 | verified 1.00 |
| single | 12 | one_factor | 32 | **0** | 1.00 | 8.4 | 127.6 | 136.0 | 0.014 | verified 1.00 |
| single | 12 | one_factor | 8 | **0** | 0.50 | 6.9 | 65.1 | 72.0 | 0.008 | unresolved 0.50, verified 0.50 |
| single | 12 | one_factor | full | **0** | 1.00 | 8.4 | 127.6 | 136.0 | 0.013 | verified 1.00 |
| single | 12 | random | 12 | **0** | 0.54 | 10.3 | 72.2 | 82.5 | 0.042 | inferred 0.09, unresolved 0.37, verified 0.54 |
| single | 12 | random | 16 | **0** | 0.77 | 11.7 | 102.2 | 113.9 | 0.045 | inferred 0.04, unresolved 0.19, verified 0.77 |
| single | 12 | random | 24 | **0** | 0.98 | 12.7 | 129.7 | 142.4 | 0.047 | inferred 0.02, verified 0.98 |
| single | 12 | random | 32 | **0** | 1.00 | 12.7 | 132.6 | 145.4 | 0.047 | verified 1.00 |
| single | 12 | random | 8 | **0** | 0.21 | 7.8 | 28.2 | 36.0 | 0.037 | inferred 0.14, unresolved 0.65, verified 0.21 |
| single | 12 | random | full | **0** | 1.00 | 12.7 | 132.6 | 145.4 | 0.048 | verified 1.00 |

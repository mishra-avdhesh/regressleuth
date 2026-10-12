# Secondary release-safety evaluation: current product defaults

The product profile uses `audit: extended` and `replay.interval: student_t`. It is
evaluated on the same stored observations as the frozen published evaluation. This
post-hoc result is descriptive and was not used to tune the search algorithm.
The original published results remain in `../evaluation/`.

| suite | strategy | isolation budget | verified right | false verified controls | mean isolation | mean total |
|---|---|---:|---:|---:|---:|---:|
| development | adaptive | 4 | 31.8% | 0.0% | 4.0 | 5.3 |
| development | adaptive | 6 | 63.6% | 0.0% | 5.1 | 8.5 |
| development | adaptive | 8 | 95.5% | 0.0% | 5.6 | 11.0 |
| development | adaptive | 12 | 95.5% | 0.0% | 5.6 | 11.0 |
| development | adaptive | full | 95.5% | 0.0% | 5.6 | 11.0 |
| development | exhaustive | 4 | 27.3% | 0.0% | 4.0 | 5.5 |
| development | exhaustive | 6 | 54.5% | 0.0% | 6.0 | 8.2 |
| development | exhaustive | 8 | 63.6% | 0.0% | 8.0 | 9.1 |
| development | exhaustive | 12 | 95.5% | 0.0% | 10.0 | 12.0 |
| development | exhaustive | full | 95.5% | 0.0% | 12.0 | 12.0 |
| development | random | 4 | 17.3% | 0.0% | 3.9 | 4.9 |
| development | random | 6 | 38.6% | 0.0% | 5.5 | 7.2 |
| development | random | 8 | 75.9% | 0.0% | 6.5 | 9.7 |
| development | random | 12 | 95.0% | 0.0% | 7.0 | 10.9 |
| development | random | full | 95.5% | 0.0% | 7.0 | 11.0 |
| development | one_factor | 4 | 27.3% | 0.0% | 3.8 | 5.5 |
| development | one_factor | 6 | 50.0% | 0.0% | 5.0 | 8.0 |
| development | one_factor | 8 | 50.0% | 0.0% | 5.0 | 8.0 |
| development | one_factor | 12 | 50.0% | 0.0% | 5.0 | 8.0 |
| development | one_factor | full | 50.0% | 0.0% | 5.0 | 8.0 |
| development | greedy | 4 | 27.3% | 0.0% | 3.8 | 5.5 |
| development | greedy | 6 | 54.5% | 0.0% | 5.1 | 8.2 |
| development | greedy | 8 | 63.6% | 0.0% | 6.0 | 9.1 |
| development | greedy | 12 | 95.5% | 0.0% | 7.0 | 11.7 |
| development | greedy | full | 95.5% | 0.0% | 7.0 | 11.7 |
| development | ddmin | 4 | 36.4% | 0.0% | 4.0 | 5.8 |
| development | ddmin | 6 | 63.6% | 0.0% | 5.2 | 8.7 |
| development | ddmin | 8 | 72.7% | 0.0% | 5.9 | 9.5 |
| development | ddmin | 12 | 95.5% | 0.0% | 6.5 | 11.1 |
| development | ddmin | full | 95.5% | 0.0% | 6.5 | 11.1 |
| holdout | adaptive | 4 | 0.0% | 0.0% | 4.0 | 4.0 |
| holdout | adaptive | 6 | 57.1% | 0.0% | 6.0 | 15.0 |
| holdout | adaptive | 8 | 85.7% | 0.0% | 6.7 | 19.4 |
| holdout | adaptive | 12 | 100.0% | 0.0% | 6.9 | 21.6 |
| holdout | adaptive | full | 100.0% | 0.0% | 6.9 | 21.6 |
| holdout | exhaustive | 4 | 14.3% | 0.0% | 4.0 | 6.9 |
| holdout | exhaustive | 6 | 14.3% | 0.0% | 6.0 | 8.6 |
| holdout | exhaustive | 8 | 57.1% | 0.0% | 8.0 | 15.7 |
| holdout | exhaustive | 12 | 85.7% | 0.0% | 12.0 | 21.6 |
| holdout | exhaustive | full | 100.0% | 0.0% | 32.0 | 32.0 |
| holdout | random | 4 | 1.4% | 0.0% | 4.0 | 4.3 |
| holdout | random | 6 | 7.1% | 0.0% | 5.9 | 7.2 |
| holdout | random | 8 | 22.9% | 0.0% | 7.7 | 11.6 |
| holdout | random | 12 | 71.4% | 0.0% | 10.0 | 19.8 |
| holdout | random | full | 100.0% | 0.0% | 10.7 | 23.2 |
| holdout | one_factor | 4 | 14.3% | 0.0% | 4.0 | 6.9 |
| holdout | one_factor | 6 | 14.3% | 0.0% | 5.7 | 8.6 |
| holdout | one_factor | 8 | 28.6% | 0.0% | 6.6 | 11.9 |
| holdout | one_factor | 12 | 28.6% | 0.0% | 6.6 | 11.9 |
| holdout | one_factor | full | 28.6% | 0.0% | 6.6 | 11.9 |
| holdout | greedy | 4 | 14.3% | 0.0% | 4.0 | 6.9 |
| holdout | greedy | 6 | 14.3% | 0.0% | 5.7 | 8.6 |
| holdout | greedy | 8 | 57.1% | 0.0% | 7.3 | 15.7 |
| holdout | greedy | 12 | 85.7% | 0.0% | 8.4 | 20.0 |
| holdout | greedy | full | 100.0% | 0.0% | 9.0 | 21.7 |
| holdout | ddmin | 4 | 0.0% | 0.0% | 4.0 | 4.0 |
| holdout | ddmin | 6 | 57.1% | 0.0% | 6.0 | 15.0 |
| holdout | ddmin | 8 | 57.1% | 0.0% | 6.9 | 15.9 |
| holdout | ddmin | 12 | 85.7% | 0.0% | 7.9 | 20.1 |
| holdout | ddmin | full | 100.0% | 0.0% | 8.3 | 21.9 |

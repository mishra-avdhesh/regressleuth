# Real-model incident results

22 incidents. Verified & right = status verified and equal to the injected cause; right at any status also counts inferred results. Random is averaged over 10 seeds. Budgets count endpoint, search and verification replays (isolation); the audit adds replays on top (total). Wall time is the summed runner time of the replays used.

## Summary at budget 8

| strategy | verified & right | pair verified & right | right at any status | wrong verified | isolation replays | total replays | runner runs | wall s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| adaptive | 0.95 | 0.91 | 1.00 | 0.00 | 5.6 | 7.9 | 16 | 23.2 |
| exhaustive | 0.64 | 0.27 | 0.64 | 0.00 | 8.0 | 8.5 | 15 | 21.2 |
| random | 0.76 | 0.55 | 0.90 | 0.00 | 6.5 | 7.9 | 15 | 22.1 |
| one_factor | 0.50 | 0.00 | 0.50 | 0.00 | 5.0 | 6.6 | 11 | 16.0 |
| greedy | 0.64 | 0.27 | 0.64 | 0.00 | 6.0 | 7.7 | 13 | 19.0 |
| ddmin | 0.73 | 0.45 | 0.73 | 0.00 | 5.9 | 7.5 | 14 | 20.8 |

## Summary at budget 16

| strategy | verified & right | pair verified & right | right at any status | wrong verified | isolation replays | total replays | runner runs | wall s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| adaptive | 0.95 | 0.91 | 1.00 | 0.00 | 5.6 | 7.9 | 16 | 23.2 |
| exhaustive | 0.95 | 0.91 | 1.00 | 0.00 | 12.0 | 12.0 | 25 | 37.9 |
| random | 0.95 | 0.91 | 1.00 | 0.00 | 7.0 | 8.7 | 18 | 26.5 |
| one_factor | 0.50 | 0.00 | 0.50 | 0.00 | 5.0 | 6.6 | 11 | 16.0 |
| greedy | 0.95 | 0.91 | 1.00 | 0.00 | 7.0 | 10.3 | 20 | 29.9 |
| ddmin | 0.95 | 0.91 | 1.00 | 0.00 | 6.5 | 8.9 | 18 | 25.9 |

## Summary at budget 32

| strategy | verified & right | pair verified & right | right at any status | wrong verified | isolation replays | total replays | runner runs | wall s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| adaptive | 0.95 | 0.91 | 1.00 | 0.00 | 5.6 | 7.9 | 16 | 23.2 |
| exhaustive | 0.95 | 0.91 | 1.00 | 0.00 | 12.0 | 12.0 | 25 | 37.9 |
| random | 0.95 | 0.91 | 1.00 | 0.00 | 7.0 | 8.7 | 18 | 26.5 |
| one_factor | 0.50 | 0.00 | 0.50 | 0.00 | 5.0 | 6.6 | 11 | 16.0 |
| greedy | 0.95 | 0.91 | 1.00 | 0.00 | 7.0 | 10.3 | 20 | 29.9 |
| ddmin | 0.95 | 0.91 | 1.00 | 0.00 | 6.5 | 8.9 | 18 | 25.9 |

## Per incident at budget 16

Cell: exact (isolation replays). 1.0 = verified the right cause; 0.0 = not verified.

| incident | k | cause | adaptive | exhaustive | random | one_factor | greedy | ddmin |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| churn_calibration_interaction | 3 | 2 | 1.0 (6.0) | 1.0 (8.0) | 1.0 (6.9) | 0.0 (5.0) | 1.0 (7.0) | 1.0 (8.0) |
| churn_policy_threshold | 3 | 1 | 1.0 (5.0) | 1.0 (8.0) | 1.0 (5.5) | 1.0 (4.0) | 1.0 (4.0) | 1.0 (5.0) |
| env_pandas3_upgrade | 3 | 1 | 1.0 (4.0) | 1.0 (8.0) | 1.0 (5.2) | 1.0 (3.0) | 1.0 (3.0) | 1.0 (4.0) |
| env_prep_x_pandas3 | 4 | 2 | 1.0 (6.0) | 1.0 (16.0) | 1.0 (8.8) | 0.0 (6.0) | 1.0 (9.0) | 1.0 (11.0) |
| image_blur | 3 | 1 | 1.0 (4.0) | 1.0 (8.0) | 1.0 (4.7) | 1.0 (5.0) | 1.0 (5.0) | 1.0 (4.0) |
| image_dead_pixels | 3 | 1 | 1.0 (4.0) | 1.0 (8.0) | 1.0 (5.2) | 1.0 (3.0) | 1.0 (3.0) | 1.0 (4.0) |
| image_invert | 4 | 1 | 1.0 (5.0) | 1.0 (16.0) | 1.0 (6.1) | 1.0 (6.0) | 1.0 (6.0) | 1.0 (6.0) |
| image_model_x_shift | 4 | 2 | 1.0 (7.0) | 1.0 (16.0) | 1.0 (9.0) | 0.0 (6.0) | 1.0 (11.0) | 1.0 (10.0) |
| image_model_x_transpose | 4 | 2 | 1.0 (7.0) | 1.0 (16.0) | 1.0 (9.0) | 0.0 (6.0) | 1.0 (11.0) | 1.0 (10.0) |
| noisy_data_x_width | 4 | 2 | 1.0 (8.0) | 1.0 (16.0) | 1.0 (8.7) | 0.0 (6.0) | 1.0 (12.0) | 1.0 (6.0) |
| noisy_epochs | 4 | 1 | 1.0 (5.0) | 1.0 (16.0) | 1.0 (7.9) | 1.0 (3.0) | 1.0 (3.0) | 1.0 (4.0) |
| noisy_labels_x_width_borderline | 4 | 2 | 0.0 (7.0) | 0.0 (16.0) | 0.0 (11.0) | 0.0 (6.0) | 0.0 (11.0) | 0.0 (10.0) |
| tabular_calibration_x_abstain | 3 | 2 | 1.0 (7.0) | 1.0 (8.0) | 1.0 (6.8) | 0.0 (5.0) | 1.0 (8.0) | 1.0 (7.0) |
| tabular_column_order | 4 | 1 | 1.0 (5.0) | 1.0 (16.0) | 1.0 (6.1) | 1.0 (6.0) | 1.0 (6.0) | 1.0 (6.0) |
| tabular_model_x_column_order | 4 | 2 | 1.0 (7.0) | 1.0 (16.0) | 1.0 (9.0) | 0.0 (6.0) | 1.0 (11.0) | 1.0 (10.0) |
| tabular_threshold | 3 | 1 | 1.0 (4.0) | 1.0 (8.0) | 1.0 (4.7) | 1.0 (5.0) | 1.0 (5.0) | 1.0 (4.0) |
| tabular_units_x_model | 3 | 2 | 1.0 (5.0) | 1.0 (8.0) | 1.0 (7.0) | 0.0 (5.0) | 1.0 (6.0) | 1.0 (5.0) |
| tabular_upstream_zero_fill | 3 | 1 | 1.0 (4.0) | 1.0 (8.0) | 1.0 (5.2) | 1.0 (3.0) | 1.0 (3.0) | 1.0 (4.0) |
| text_model_x_uppercase | 4 | 2 | 1.0 (7.0) | 1.0 (16.0) | 1.0 (9.0) | 0.0 (6.0) | 1.0 (11.0) | 1.0 (10.0) |
| text_tokenizer_x_uppercase | 4 | 2 | 1.0 (8.0) | 1.0 (16.0) | 1.0 (8.7) | 0.0 (6.0) | 1.0 (12.0) | 1.0 (6.0) |
| text_truncation | 3 | 1 | 1.0 (4.0) | 1.0 (8.0) | 1.0 (5.2) | 1.0 (3.0) | 1.0 (3.0) | 1.0 (4.0) |
| text_uppercase_cased | 3 | 1 | 1.0 (4.0) | 1.0 (8.0) | 1.0 (4.7) | 1.0 (5.0) | 1.0 (5.0) | 1.0 (4.0) |

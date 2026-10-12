# Noise-guarantee simulation (pre-registered, one run)

Protocol: [PROTOCOL.md](../../noise_guarantee/PROTOCOL.md). Claim: with `interval: anytime`, P(verified and not a true minimal failing set) <= 0.05 when the noise assumptions hold.

**Primary claim supported: yes.**

## Wrong verified, pooled over the five assumption-holding scenarios

| interval | strategy | investigations | wrong verified | rate | 95% upper | correct verified | mean runs |
|---|---|---:|---:|---:|---:|---:|---:|
| anytime | adaptive | 6000 | **0** | 0.0000 | 0.0005 | 0.247 | 183.5 |
| anytime | ddmin | 6000 | **0** | 0.0000 | 0.0005 | 0.247 | 165.1 |
| anytime | exhaustive | 6000 | **0** | 0.0000 | 0.0005 | 0.247 | 479.4 |
| anytime | greedy | 6000 | **0** | 0.0000 | 0.0005 | 0.247 | 210.7 |
| anytime | one_factor | 6000 | **0** | 0.0000 | 0.0005 | 0.123 | 125.4 |
| anytime | random | 6000 | **0** | 0.0000 | 0.0005 | 0.247 | 185.0 |
| normal | adaptive | 6000 | **0** | 0.0000 | 0.0005 | 0.370 | 107.4 |
| normal | ddmin | 6000 | **0** | 0.0000 | 0.0005 | 0.370 | 102.6 |
| normal | exhaustive | 6000 | **0** | 0.0000 | 0.0005 | 0.369 | 301.5 |
| normal | greedy | 6000 | **0** | 0.0000 | 0.0005 | 0.370 | 119.9 |
| normal | one_factor | 6000 | **0** | 0.0000 | 0.0005 | 0.183 | 70.9 |
| normal | random | 6000 | **0** | 0.0000 | 0.0005 | 0.370 | 109.7 |
| student_t | adaptive | 6000 | **0** | 0.0000 | 0.0005 | 0.284 | 130.7 |
| student_t | ddmin | 6000 | **0** | 0.0000 | 0.0005 | 0.284 | 110.5 |
| student_t | exhaustive | 6000 | **0** | 0.0000 | 0.0005 | 0.284 | 349.2 |
| student_t | greedy | 6000 | **0** | 0.0000 | 0.0005 | 0.284 | 155.3 |
| student_t | one_factor | 6000 | **0** | 0.0000 | 0.0005 | 0.138 | 81.4 |
| student_t | random | 6000 | **0** | 0.0000 | 0.0005 | 0.284 | 144.1 |

## Wrong verified when the noise assumption is violated (pooled)

| interval | strategy | investigations | wrong verified | rate | 95% upper | correct verified | mean runs |
|---|---|---:|---:|---:|---:|---:|---:|
| anytime | adaptive | 2400 | **0** | 0.0000 | 0.0012 | 0.312 | 233.5 |
| anytime | ddmin | 2400 | **0** | 0.0000 | 0.0012 | 0.312 | 232.6 |
| anytime | exhaustive | 2400 | **0** | 0.0000 | 0.0012 | 0.310 | 823.9 |
| anytime | greedy | 2400 | **0** | 0.0000 | 0.0012 | 0.312 | 255.8 |
| anytime | one_factor | 2400 | **0** | 0.0000 | 0.0012 | 0.149 | 170.1 |
| anytime | random | 2400 | **0** | 0.0000 | 0.0012 | 0.312 | 261.9 |
| normal | adaptive | 2400 | **0** | 0.0000 | 0.0012 | 0.550 | 180.7 |
| normal | ddmin | 2400 | **0** | 0.0000 | 0.0012 | 0.550 | 156.4 |
| normal | exhaustive | 2400 | **0** | 0.0000 | 0.0012 | 0.548 | 561.3 |
| normal | greedy | 2400 | **0** | 0.0000 | 0.0012 | 0.549 | 218.8 |
| normal | one_factor | 2400 | **0** | 0.0000 | 0.0012 | 0.275 | 121.2 |
| normal | random | 2400 | **0** | 0.0000 | 0.0012 | 0.550 | 223.0 |
| student_t | adaptive | 2400 | **0** | 0.0000 | 0.0012 | 0.432 | 199.3 |
| student_t | ddmin | 2400 | **0** | 0.0000 | 0.0012 | 0.432 | 151.4 |
| student_t | exhaustive | 2400 | **0** | 0.0000 | 0.0012 | 0.432 | 596.5 |
| student_t | greedy | 2400 | **0** | 0.0000 | 0.0012 | 0.432 | 258.4 |
| student_t | one_factor | 2400 | **0** | 0.0000 | 0.0012 | 0.212 | 116.3 |
| student_t | random | 2400 | **0** | 0.0000 | 0.0012 | 0.432 | 257.4 |

## Per scenario (adaptive)

| scenario | interval | wrong verified | rate | 95% upper | correct verified | statuses | noise check violated | mean runs |
|---|---|---:|---:|---:|---:|---|---:|---:|
| healing | anytime | **0** | 0.0000 | 0.0025 | 0.000 | inconclusive 0.12, invalid_baseline 0.88 | 0.000 | 33.9 |
| healing | normal | **0** | 0.0000 | 0.0025 | 0.000 | inconclusive 0.04, invalid_baseline 0.96 | 0.000 | 7.4 |
| healing | student_t | **0** | 0.0000 | 0.0025 | 0.000 | inconclusive 0.19, invalid_baseline 0.81 | 0.000 | 10.7 |
| heavy_tail | anytime | **0** | 0.0000 | 0.0025 | 0.624 | inconclusive 0.09, inferred 0.29, verified 0.62 | 0.004 | 241.3 |
| heavy_tail | normal | **0** | 0.0000 | 0.0025 | 0.897 | inconclusive 0.04, inferred 0.06, verified 0.90 | 0.000 | 126.0 |
| heavy_tail | student_t | **0** | 0.0000 | 0.0025 | 0.751 | inconclusive 0.12, inferred 0.13, verified 0.75 | 0.000 | 143.6 |
| misdeclared | anytime | **0** | 0.0000 | 0.0025 | 0.000 | assumption_violated 0.01, inconclusive 0.10, inferred 0.89, invalid_baseline 0.00 | 1.000 | 225.7 |
| misdeclared | normal | **0** | 0.0000 | 0.0025 | 0.203 | assumption_violated 0.05, inconclusive 0.34, inferred 0.39, invalid_baseline 0.01, verified 0.20 | 0.000 | 235.5 |
| misdeclared | student_t | **0** | 0.0000 | 0.0025 | 0.113 | assumption_violated 0.01, inconclusive 0.56, inferred 0.31, invalid_baseline 0.01, verified 0.11 | 0.000 | 255.1 |
| near_threshold | anytime | **0** | 0.0000 | 0.0025 | 0.002 | inconclusive 0.80, inferred 0.20, verified 0.00 | 0.000 | 199.3 |
| near_threshold | normal | **0** | 0.0000 | 0.0025 | 0.177 | assumption_violated 0.02, inconclusive 0.37, inferred 0.42, invalid_baseline 0.01, verified 0.18 | 0.000 | 142.6 |
| near_threshold | student_t | **0** | 0.0000 | 0.0025 | 0.098 | assumption_violated 0.00, inconclusive 0.60, inferred 0.30, invalid_baseline 0.00, verified 0.10 | 0.000 | 148.9 |
| pair | anytime | **0** | 0.0000 | 0.0025 | 0.618 | inconclusive 0.09, inferred 0.29, verified 0.62 | 0.000 | 198.6 |
| pair | normal | **0** | 0.0000 | 0.0025 | 0.844 | inconclusive 0.05, inferred 0.11, verified 0.84 | 0.000 | 117.4 |
| pair | student_t | **0** | 0.0000 | 0.0025 | 0.676 | inconclusive 0.16, inferred 0.16, verified 0.68 | 0.000 | 170.5 |
| single | anytime | **0** | 0.0000 | 0.0025 | 0.613 | inconclusive 0.08, inferred 0.30, verified 0.61 | 0.000 | 264.5 |
| single | normal | **0** | 0.0000 | 0.0025 | 0.830 | assumption_violated 0.00, inconclusive 0.03, inferred 0.14, verified 0.83 | 0.000 | 145.2 |
| single | student_t | **0** | 0.0000 | 0.0025 | 0.647 | assumption_violated 0.00, inconclusive 0.10, inferred 0.26, verified 0.65 | 0.000 | 176.2 |
| two_causes | anytime | **0** | 0.0000 | 0.0025 | 0.000 | assumption_violated 0.84, inconclusive 0.08, inferred 0.07 | 0.000 | 221.0 |
| two_causes | normal | **0** | 0.0000 | 0.0025 | 0.000 | assumption_violated 0.94, inconclusive 0.03, inferred 0.03, invalid_baseline 0.00 | 0.000 | 124.6 |
| two_causes | student_t | **0** | 0.0000 | 0.0025 | 0.000 | assumption_violated 0.82, inconclusive 0.10, inferred 0.07, invalid_baseline 0.00 | 0.000 | 147.4 |

Investigations of one incident share noise draws across intervals and strategies, so
rows are paired and not independent across strategies. All rows: `rows.json`.

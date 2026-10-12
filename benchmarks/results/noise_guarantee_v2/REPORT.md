# Noise-guarantee simulation, version 2 (pre-registered, one run)

Protocol: [PROTOCOL_V2.md](../../noise_guarantee/PROTOCOL_V2.md). Version 1 is unchanged: [report](../noise_guarantee/REPORT.md).

**Primary claim supported: yes.**

| scenario | audit | interval | strategy | investigations | wrong verified | rate | 95% upper | correct verified | mean runs |
|---|---|---|---|---:|---:|---:|---:|---:|---:|
| masked_healing | 0 | anytime | adaptive | 600 | **0** | 0.0000 | 0.0050 | 0.617 | 100.9 |
| masked_healing | 0 | anytime | ddmin | 600 | **0** | 0.0000 | 0.0050 | 0.583 | 121.0 |
| masked_healing | 0 | anytime | exhaustive | 600 | **0** | 0.0000 | 0.0050 | 0.000 | 356.3 |
| masked_healing | 0 | anytime | greedy | 600 | **0** | 0.0000 | 0.0050 | 0.913 | 155.1 |
| masked_healing | 0 | anytime | one_factor | 600 | **0** | 0.0000 | 0.0050 | 0.463 | 104.2 |
| masked_healing | 0 | anytime | random | 600 | **0** | 0.0000 | 0.0050 | 0.378 | 134.4 |
| masked_healing | 0 | normal | adaptive | 600 | **1** | 0.0017 | 0.0079 | 0.543 | 88.2 |
| masked_healing | 0 | normal | ddmin | 600 | **2** | 0.0033 | 0.0105 | 0.533 | 60.4 |
| masked_healing | 0 | normal | exhaustive | 600 | **0** | 0.0000 | 0.0050 | 0.042 | 365.9 |
| masked_healing | 0 | normal | greedy | 600 | **6** | 0.0100 | 0.0196 | 0.782 | 144.1 |
| masked_healing | 0 | normal | one_factor | 600 | **6** | 0.0100 | 0.0196 | 0.440 | 46.8 |
| masked_healing | 0 | normal | random | 600 | **2** | 0.0033 | 0.0105 | 0.353 | 149.9 |
| masked_healing | 0 | student_t | adaptive | 600 | **0** | 0.0000 | 0.0050 | 0.342 | 169.4 |
| masked_healing | 0 | student_t | ddmin | 600 | **0** | 0.0000 | 0.0050 | 0.330 | 89.1 |
| masked_healing | 0 | student_t | exhaustive | 600 | **0** | 0.0000 | 0.0050 | 0.057 | 537.3 |
| masked_healing | 0 | student_t | greedy | 600 | **0** | 0.0000 | 0.0050 | 0.462 | 266.9 |
| masked_healing | 0 | student_t | one_factor | 600 | **0** | 0.0000 | 0.0050 | 0.272 | 62.5 |
| masked_healing | 0 | student_t | random | 600 | **0** | 0.0000 | 0.0050 | 0.240 | 255.8 |
| masked_healing | extended | anytime | adaptive | 600 | **0** | 0.0000 | 0.0050 | 0.000 | 286.4 |
| masked_healing | extended | anytime | ddmin | 600 | **0** | 0.0000 | 0.0050 | 0.000 | 288.4 |
| masked_healing | extended | anytime | exhaustive | 600 | **0** | 0.0000 | 0.0050 | 0.000 | 356.3 |
| masked_healing | extended | anytime | greedy | 600 | **0** | 0.0000 | 0.0050 | 0.000 | 388.9 |
| masked_healing | extended | anytime | one_factor | 600 | **0** | 0.0000 | 0.0050 | 0.000 | 261.4 |
| masked_healing | extended | anytime | random | 600 | **0** | 0.0000 | 0.0050 | 0.000 | 243.5 |
| masked_healing | extended | normal | adaptive | 600 | **0** | 0.0000 | 0.0050 | 0.000 | 180.9 |
| masked_healing | extended | normal | ddmin | 600 | **0** | 0.0000 | 0.0050 | 0.000 | 152.1 |
| masked_healing | extended | normal | exhaustive | 600 | **0** | 0.0000 | 0.0050 | 0.000 | 365.9 |
| masked_healing | extended | normal | greedy | 600 | **0** | 0.0000 | 0.0050 | 0.000 | 254.5 |
| masked_healing | extended | normal | one_factor | 600 | **0** | 0.0000 | 0.0050 | 0.000 | 138.5 |
| masked_healing | extended | normal | random | 600 | **0** | 0.0000 | 0.0050 | 0.000 | 213.7 |
| masked_healing | extended | student_t | adaptive | 600 | **0** | 0.0000 | 0.0050 | 0.000 | 261.9 |
| masked_healing | extended | student_t | ddmin | 600 | **0** | 0.0000 | 0.0050 | 0.000 | 180.8 |
| masked_healing | extended | student_t | exhaustive | 600 | **0** | 0.0000 | 0.0050 | 0.000 | 537.3 |
| masked_healing | extended | student_t | greedy | 600 | **0** | 0.0000 | 0.0050 | 0.000 | 372.8 |
| masked_healing | extended | student_t | one_factor | 600 | **0** | 0.0000 | 0.0050 | 0.000 | 153.3 |
| masked_healing | extended | student_t | random | 600 | **0** | 0.0000 | 0.0050 | 0.000 | 328.7 |
| stress_near | 0 | anytime | adaptive | 600 | **0** | 0.0000 | 0.0050 | 0.000 | 2299.9 |
| stress_near | 0 | anytime | ddmin | 600 | **0** | 0.0000 | 0.0050 | 0.000 | 339.9 |
| stress_near | 0 | anytime | exhaustive | 600 | **0** | 0.0000 | 0.0050 | 0.000 | 3065.7 |
| stress_near | 0 | anytime | greedy | 600 | **0** | 0.0000 | 0.0050 | 0.000 | 3065.7 |
| stress_near | 0 | anytime | one_factor | 600 | **0** | 0.0000 | 0.0050 | 0.000 | 185.8 |
| stress_near | 0 | anytime | random | 600 | **0** | 0.0000 | 0.0050 | 0.000 | 3065.7 |
| stress_near | 0 | normal | adaptive | 600 | **95** | 0.1583 | 0.1849 | 0.130 | 412.3 |
| stress_near | 0 | normal | ddmin | 600 | **102** | 0.1700 | 0.1973 | 0.137 | 145.7 |
| stress_near | 0 | normal | exhaustive | 600 | **34** | 0.0567 | 0.0747 | 0.008 | 847.6 |
| stress_near | 0 | normal | greedy | 600 | **121** | 0.2017 | 0.2305 | 0.150 | 556.9 |
| stress_near | 0 | normal | one_factor | 600 | **61** | 0.1017 | 0.1243 | 0.150 | 71.3 |
| stress_near | 0 | normal | random | 600 | **90** | 0.1500 | 0.1761 | 0.103 | 562.4 |
| stress_near | 0 | student_t | adaptive | 600 | **42** | 0.0700 | 0.0896 | 0.073 | 433.7 |
| stress_near | 0 | student_t | ddmin | 600 | **42** | 0.0700 | 0.0896 | 0.078 | 115.5 |
| stress_near | 0 | student_t | exhaustive | 600 | **23** | 0.0383 | 0.0539 | 0.013 | 736.7 |
| stress_near | 0 | student_t | greedy | 600 | **48** | 0.0800 | 0.1006 | 0.083 | 586.9 |
| stress_near | 0 | student_t | one_factor | 600 | **21** | 0.0350 | 0.0500 | 0.083 | 69.4 |
| stress_near | 0 | student_t | random | 600 | **34** | 0.0567 | 0.0747 | 0.062 | 594.9 |
| stress_near | extended | anytime | adaptive | 600 | **0** | 0.0000 | 0.0050 | 0.000 | 2299.9 |
| stress_near | extended | anytime | ddmin | 600 | **0** | 0.0000 | 0.0050 | 0.000 | 339.9 |
| stress_near | extended | anytime | exhaustive | 600 | **0** | 0.0000 | 0.0050 | 0.000 | 3065.7 |
| stress_near | extended | anytime | greedy | 600 | **0** | 0.0000 | 0.0050 | 0.000 | 3065.7 |
| stress_near | extended | anytime | one_factor | 600 | **0** | 0.0000 | 0.0050 | 0.000 | 185.8 |
| stress_near | extended | anytime | random | 600 | **0** | 0.0000 | 0.0050 | 0.000 | 3065.7 |
| stress_near | extended | normal | adaptive | 600 | **31** | 0.0517 | 0.0691 | 0.000 | 499.2 |
| stress_near | extended | normal | ddmin | 600 | **33** | 0.0550 | 0.0729 | 0.000 | 238.8 |
| stress_near | extended | normal | exhaustive | 600 | **21** | 0.0350 | 0.0500 | 0.000 | 847.6 |
| stress_near | extended | normal | greedy | 600 | **32** | 0.0533 | 0.0710 | 0.000 | 678.0 |
| stress_near | extended | normal | one_factor | 600 | **0** | 0.0000 | 0.0050 | 0.000 | 179.3 |
| stress_near | extended | normal | random | 600 | **32** | 0.0533 | 0.0710 | 0.000 | 635.4 |
| stress_near | extended | student_t | adaptive | 600 | **20** | 0.0333 | 0.0481 | 0.000 | 483.6 |
| stress_near | extended | student_t | ddmin | 600 | **20** | 0.0333 | 0.0481 | 0.000 | 172.2 |
| stress_near | extended | student_t | exhaustive | 600 | **18** | 0.0300 | 0.0442 | 0.000 | 736.7 |
| stress_near | extended | student_t | greedy | 600 | **20** | 0.0333 | 0.0481 | 0.000 | 651.8 |
| stress_near | extended | student_t | one_factor | 600 | **0** | 0.0000 | 0.0050 | 0.000 | 127.7 |
| stress_near | extended | student_t | random | 600 | **20** | 0.0333 | 0.0481 | 0.000 | 632.0 |

Rows of one incident share noise draws (paired). All rows: `rows.json`.

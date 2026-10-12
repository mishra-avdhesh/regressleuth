# Holdout benchmark: pre-registration

Written on 2026-10-08, **after** the search method was frozen
(`benchmarks/frozen/frozen_method.json`, tree sha256 `55cedbdfffe61ac8...`) and **before**
any data for these incidents existed or any strategy was run on them.

## Purpose

The development incidents (`benchmarks/incidents/`) were designed inside this project
alongside the search method. This holdout set tests the frozen method on incidents
reconstructed from **documented, citable real-world behaviors**, using datasets and
mechanisms the development set does not use.

## Rules (fixed now, not revisable after results)

1. The method is frozen. No change to the search, verification, audit or noise rule is
   made in response to any holdout result. A failing incident is reported as a failure.
2. Every incident is written in Incident Specification 1.0 and cites its source in
   `metadata.provenance`.
3. Uniform settings: metric accuracy, `higher_is_better`, `regression_threshold: 0.03`,
   exactly **5 changed components** (the cause plus benign decoys drawn from: model retrain,
   decision-threshold tweak, log level, cache TTL, feature storage dtype), default budget 16.
4. Ground truth is the cause listed below. Before sealing, `prove_ground_truth.py` must show,
   by replaying all 32 combinations, that a combination regresses (mean drop >= 0.03) if and
   only if it contains the cause. If a proof fails, only the incident's *construction*
   (data generation strength, decoy choice) may change, every change is logged in the
   construction log below, and no strategy may have been run.
5. After the proofs pass, `seal.py` records SHA-256 of every holdout file. The evaluation
   script refuses to run if any sealed file changed.
6. Results are reported separately from development results.

## Incidents

| id | mechanism | source | cause |
|---|---|---|---|
| `holdout_numpy2_float32_time` | NEP 50: `np.float32(1.0) * python_float` is float32 on NumPy 2 but float64 on NumPy 1; with epoch-second timestamps the time-delta feature is quantized to 128 s only when a float32-stored scale meets NumPy 2 | NumPy 2.0 migration guide; NEP 50 | `environment` + `config_store` |
| `holdout_pandas3_datetime_epoch` | pandas 3 infers microsecond resolution when parsing strings, so `to_datetime(...).astype("int64") // 10**9` no longer yields epoch seconds | pandas 3.0.0 release notes; pandas-dev/pandas#58989 | `environment` |
| `holdout_csv_na_country_code` | `read_csv` treats the string "NA" as missing by default; Namibia's ISO alpha-2 code becomes NaN once an export switches from alpha-3 codes | pandas-dev/pandas#10647, #4318 | `export_format` + `csv_parser` |
| `holdout_encoder_refit_per_batch` | Training-serving skew: an encoder refit on each serving batch maps categories to different codes when batches are small | Rules of ML #29; scikit-learn "Common pitfalls" (inconsistent preprocessing) | `encoder_fit` + `batch_size` |
| `holdout_pillow_resize_default` | Pillow 7.0 changed the default `resize` filter from NEAREST to BICUBIC; a model trained on NEAREST-resized images is served with the default filter | Pillow 7.0.0 release notes; python-pillow/Pillow#4255 | `resize_call` |
| `holdout_proba_column_order` | `predict_proba` columns follow the sorted `classes_`; renaming labels for a retrained model flips the column that hard-coded postprocessing reads | scikit-learn glossary (`classes_`, `predict_proba`) | `model` + `postprocessing` |
| `holdout_pythonhashseed_hashing` | Python salts `str` hashes per process unless `PYTHONHASHSEED` is fixed; a hashing-trick model trained with a fixed seed breaks when the serving manifest drops it | Python docs, command line and environment (`PYTHONHASHSEED`) | `runtime_env` |
| `holdout_timezone_hour_feature` | An export switching from local naive timestamps to UTC ISO strings shifts the hour-of-day feature for code that reads `.dt.hour` without converting time zones | pandas time-series user guide (time zone handling) | `export_format` + `preprocessing` |

Datasets: Adult census income (UCI, via the `scikit-learn/adult-census-income` Hugging Face
mirror, CC0) for the encoder, column-order and hashing incidents; MNIST (`ylecun/mnist`) for
the resize incident; seeded synthetic event data for the NumPy, pandas datetime, CSV and time
zone incidents, where only the library behavior, not the data, is the object of study.

## Construction log

(Changes made before sealing, if a ground-truth proof fails. Empty means none.) No strategy had been
run on any holdout incident when these changes were made.

1. `holdout_numpy2_float32_time`: the first proof showed **no** regression (drop -0.004). The NEP 50
   precision loss was present (a 30 s delta became 0 s under NumPy 2), but the model used the time
   delta only as a smooth linear feature whose decision boundary lay minutes away, so 128 s of
   quantization did not change predictions. Added the standard "within 60 s of the reset" rule
   feature, which is exactly what the quantization breaks. Data, seeds and decoys unchanged.
2. `holdout_pillow_resize_default`: the documented filter change cost only 1.35 points at 14 px
   (and -1.5 / -0.4 points at 10 / 7 px, measured once to check), below the pre-registered 3-point
   threshold. Rather than strengthen the mechanism until it crossed the threshold, the incident
   was moved to `controls/` as `holdout_ctrl_pillow_subthreshold` with expected status
   `invalid_baseline`. The valid holdout set is therefore 7 incidents.
3. `holdout_pythonhashseed_hashing`: the runner crashed on every replay (a helper did not accept
   a string path). Fixed the helper; the incident itself is unchanged. It declares
   `replay.repeats: 3, max_repeats: 9` because hash salting makes its bad replays stochastic.

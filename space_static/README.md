---
title: Regressleuth replay explorer
emoji: 🔎
colorFrom: indigo
colorTo: gray
sdk: static
app_file: index.html
pinned: false
license: apache-2.0
short_description: Explore ML regression replay reports without a server or API
---

This free static demo shows eight **precomputed** reports from two bundled synthetic
oracle incidents, two search strategies, and the current `extended` and historical
`full` audits. It does not execute Python or run a new diagnosis in the browser.

The reports were generated locally with `python tools/build_static_space.py` from
Regressleuth `0.1.0a1` at isolation budget 16 and seed 0. Deterministic incidents
do not use their configured metric interval. The historical `full` audit can falsely
verify the non-monotone control; the released product defaults to `extended`.

To publish on a free Hugging Face account, create a **Static** Space and copy the
contents of `space_static/` to its repository root. No package installation, API key,
GPU, or paid compute is required. The same files can be served with GitHub Pages.

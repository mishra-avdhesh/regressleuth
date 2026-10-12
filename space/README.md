---
title: Regressleuth
emoji: 🔎
colorFrom: indigo
colorTo: gray
sdk: gradio
sdk_version: 6.30.0
python_version: 3.12
app_file: app.py
pinned: false
license: apache-2.0
short_description: Find which change broke your ML model
---

Interactive demo of Regressleuth: budgeted counterfactual replay that isolates the single change or pair of changes behind an ML regression. Runs built-in oracle incidents only; no user code is executed.

Deploy this Space after `regressleuth==0.1.0a1` is available on PyPI. Update
`requirements.txt` when deploying a later release.

This is the live Gradio template. [Hugging Face currently requires a paid plan](https://huggingface.co/docs/hub/main/spaces-sdks-static) to
create a new hosted Gradio Space. For a no-cost public demo, use the precomputed
`space_static/` template from the main repository instead.

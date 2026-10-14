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

Run the app locally from the repository root:

```bash
python -m pip install -e .
python -m pip install gradio==6.30.0
python space/app.py
```

This optional Gradio template pins the public GitHub source in `requirements.txt`.
[Hugging Face requires a paid plan](https://huggingface.co/docs/hub/spaces-overview)
to create a compute-backed Space. The public [static replay explorer](https://huggingface.co/spaces/avdheshmishra/regressleuth)
is free and shows precomputed reports.

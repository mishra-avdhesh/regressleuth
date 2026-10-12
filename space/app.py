"""Hugging Face Space: explore how Regressleuth isolates a regression.

Only the built-in oracle incidents run here (no user code is executed), so the Space is safe
to host publicly. Its requirements pin a released package version.
"""

from __future__ import annotations

import gradio as gr

from regressleuth.bench import build_suite, run_one
from regressleuth.reporting import render_html, render_text
from regressleuth.strategies import STRATEGIES

SUITE = {spec.id: spec for spec in build_suite()}
DESCRIPTION = {
    "single": "one component alone causes the regression",
    "pair": "two components only fail together (an interaction)",
    "multi_cause": "control: three components are needed, beyond what is searched",
    "nonmonotone": "control: adding a component heals the failure",
    "masked": "control: a third component masks the failure",
    "incompatible": "control: some hybrids cannot be built",
    "no_regression": "control: the bad state is not actually worse",
    "low_signal": "control: the effect is smaller than the noise",
    "cancel_xor": "control: two changes cancel each other while a third causes the failure",
    "latent_healed": "control: a failing pair is healed by another change in the same release",
    "double_healer": "control: the failure is healed only when two other changes are both present",
}


def investigate(incident: str, strategy: str, budget: int, audit: str):
    spec = SUITE[incident]
    report = run_one(spec, strategy, int(budget), seed=0, audit=audit)
    truth = " + ".join(sorted(spec.cause))
    note = (
        f"Ground truth: **{truth}** ({DESCRIPTION[spec.kind]}). "
        f"Result: **{report.status}**"
        + (f", diagnosis **{' + '.join(report.diagnosis)}**" if report.diagnosis else "")
        + f". {report.isolation_replays} isolation replays + "
        f"{report.experiments_used - report.isolation_replays} audit replays "
        f"(exhaustive search would need {2 ** len(spec.components)})."
    )
    return note, render_text(report), render_html(report)


with gr.Blocks(title="Regressleuth") as demo:
    gr.Markdown(
        "# Regressleuth\nWhich change (or pair of changes) broke the model? Pick a synthetic "
        "incident and a search strategy and watch which combinations get replayed. "
        "Try `one_factor` on a `pair_*` incident, or compare the `full` and `extended` audits on "
        "`control_double_healer_k6`."
    )
    with gr.Row():
        incident = gr.Dropdown(sorted(SUITE), value="pair_model_preprocessing_k5", label="Incident")
        strategy = gr.Dropdown(list(STRATEGIES), value="adaptive", label="Strategy")
        budget = gr.Slider(4, 32, value=16, step=1, label="Isolation budget (replays)")
        audit = gr.Radio(["full", "extended"], value="extended", label="Monotonicity audit")
    run = gr.Button("Investigate", variant="primary")
    summary = gr.Markdown()
    text = gr.Textbox(label="Report", lines=18, buttons=["copy"])
    page = gr.HTML(label="Replay lattice")
    run.click(investigate, [incident, strategy, budget, audit], [summary, text, page])

if __name__ == "__main__":
    demo.launch()

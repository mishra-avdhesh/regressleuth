"""Report renderers for result schema 1.0 (JSON, text, Markdown, HTML).

Reports never contain replay stdout/stderr, exception text or secret-looking component
values (see ``redact.py``); component versions appear according to the incident's
``report.values`` policy.
"""

from __future__ import annotations

import html
import json
import re
from typing import Any

from .models import InvestigationReport

_CONTROL = re.compile(r"[\x00-\x1f\x7f-\x9f]")
_GLYPH = {
    "pass": "PASS",
    "fail": "FAIL",
    "inconclusive": "UNSURE",
    "incompatible": "INCOMPAT",
    "error": "ERROR",
}
_SYMBOL = {"pass": "\u2713", "fail": "\u2717", "inconclusive": "?", "incompatible": "\u2298", "error": "!"}

NEXT_STEP = {
    "verified": (
        "Inspect or roll back the named component(s). This result is verified under the "
        "configured replay model, assumptions, and audit checks."
    ),
    "inferred": (
        "Treat the named cause as the leading suspect, not a proven one. Raise the budget or the "
        "audit allowance, or make the untestable hybrids runnable, to turn this into a verified result."
    ),
    "inconclusive": (
        "Metric noise hid the effect. Raise replay.repeats or replay.max_repeats, use more "
        "evaluation cases, or reduce run-to-run variance (fixed seeds)."
    ),
    "unresolved": (
        "Several explanations remain. Increase the budget, narrow the list of changed components, "
        "or make hybrids that were incompatible runnable."
    ),
    "assumption_violated": (
        "The regression is not explained by a small set of components behaving monotonically. "
        "Inspect the contradicting replays; another component may mask or amplify the failure, or "
        "the cause may involve more components (try search.max_cause_size: 3)."
    ),
    "invalid_baseline": (
        "The good and bad endpoints do not separate on this metric and threshold. Check the cases, "
        "the threshold and that the bad state really regresses."
    ),
    "evaluation_error": (
        "A replay could not be evaluated, so no attribution was made. Re-run with "
        "--diagnostics-dir to capture the failing replay's output."
    ),
}


def _data(report: InvestigationReport | dict[str, Any]) -> dict[str, Any]:
    return report.to_dict() if isinstance(report, InvestigationReport) else report


def _clean(value: object) -> str:
    return _CONTROL.sub("?", str(value))


def _names(items: list[str] | tuple[str, ...] | None) -> str:
    return " + ".join(_clean(i) for i in items) if items else "(none)"


def _metric(experiment: dict[str, Any]) -> str:
    value = experiment.get("metric")
    if value is None:
        return "-" if not experiment.get("error_kind") else f"({experiment['error_kind']})"
    sd = experiment.get("metric_sd")
    return f"{value:.4g}" + (f" \u00b1{sd:.2g}" if sd else "")


def _value(value: Any) -> str:
    text = value if isinstance(value, str) else json.dumps(value, sort_keys=True)
    return _clean(text if len(text) <= 80 else text[:77] + "...")


def render_json(report: InvestigationReport | dict[str, Any]) -> str:
    return json.dumps(_data(report), indent=2, sort_keys=True, allow_nan=False) + "\n"


def headline(data: dict[str, Any]) -> str:
    if data.get("diagnosis"):
        label = "CAUSE" if data["status"] == "verified" else "LIKELY CAUSE (not verified)"
        return f"{label}: {_names(data['diagnosis'])}"
    if data.get("suspected_cause"):
        return f"NO SAFE DIAGNOSIS (suspected {_names(data['suspected_cause'])})"
    return "NO DIAGNOSIS"


def budget_line(data: dict[str, Any]) -> str:
    replays = data["replays"]
    line = f"isolation {replays['isolation_used']}/{replays['budget']}"
    if replays["audit_used"]:
        line += f" + audit {replays['audit_used']}"
    if replays["runner_runs"] != replays["total"]:
        line += f" ({replays['runner_runs']} runner runs)"
    exhaustive = data["search"].get("search_space")
    if exhaustive:
        line += f"; full exhaustive search = {exhaustive}"
    return line


def verification_line(data: dict[str, Any]) -> str:
    verification = data.get("verification") or {}
    confidence = data.get("confidence") or {}
    audit = verification.get("audit_mode", data.get("search", {}).get("audit"))
    interval = verification.get("interval_method", confidence.get("interval"))
    applied = verification.get("interval_applied", confidence.get("interval_applied", False))
    level = verification.get("confidence", confidence.get("level"))
    repeats = verification.get("repeats", confidence.get("repeats"))
    maximum = verification.get("max_repeats", confidence.get("max_repeats"))
    line = (
        f"audit {audit}; interval {interval} ({'applied' if applied else 'not applied: deterministic'}); "
        f"confidence {level}; repeats {repeats}/{maximum}"
    )
    bound = verification.get("diagnosis_error_bound")
    if bound is not None:
        line += (
            f"; P(verified set is not a true minimal failing set) <= {bound}, given independent runs "
            f"with {verification.get('noise_scale')}-sub-Gaussian noise"
        )
    return line


def render_text(report: InvestigationReport | dict[str, Any]) -> str:
    data = _data(report)
    rows = [
        (
            str(i),
            _names(e["changed"]) if e["changed"] else "(none: known-good)",
            _GLYPH.get(e["outcome"], e["outcome"]),
            _metric(e),
            e["role"],
            "" if e.get("hypotheses_remaining") is None else str(e["hypotheses_remaining"]),
        )
        for i, e in enumerate(data["experiments"], 1)
    ]
    heads = ("#", "bad components in the replay", "outcome", "metric", "why run", "left")
    widths = [max(len(h), *(len(r[c]) for r in rows)) for c, h in enumerate(heads)]
    table = [
        "  ".join(h.ljust(w) for h, w in zip(heads, widths, strict=True)).rstrip(),
        "  ".join("-" * w for w in widths),
        *("  ".join(c.ljust(w) for c, w in zip(r, widths, strict=True)).rstrip() for r in rows),
    ]
    metric = data["incident"].get("metric", {})
    out = [
        f"Regressleuth: {_clean(data['incident']['id'])}   strategy={data['search']['strategy']}",
        f"Status: {data['status'].upper().replace('_', ' ')}",
        headline(data),
        f"Replays: {budget_line(data)}",
        f"Verification: {verification_line(data)}",
        f"Metric: {metric.get('name')} ({metric.get('direction', '').replace('_', ' ')}), "
        f"regression threshold {metric.get('regression_threshold')}",
        f"Reason: {_clean(data['reason'])}" if data["reason"] else "",
        "",
        *table,
        "",
        "('left' = candidate causes still compatible after that replay)",
    ]
    audit = data.get("audit") or {}
    if audit.get("required"):
        out += [
            "",
            f"Monotonicity audit: {audit['confirmed']}/{audit['required']} checks confirmed"
            + (", CONTRADICTED" if audit.get("violations") else ""),
        ]
    out += [
        "",
        "Assumption checks: "
        + ", ".join(f"{item['id']}={item['status']}" for item in data.get("assumptions", [])),
    ]
    if len(data.get("alternatives", [])) > 1:
        out += ["", "Still-compatible causes: " + "; ".join(_names(c) for c in data["alternatives"][:8])]
    errors = data.get("errors", {})
    if errors.get("incompatible") or errors.get("error") or errors.get("inconclusive"):
        out += [
            "",
            f"Problems: {errors.get('incompatible', 0)} incompatible, "
            f"{errors.get('error', 0)} error(s) {errors.get('kinds', {}) or ''}, "
            f"{errors.get('inconclusive', 0)} inconclusive",
        ]
    out += ["", "Next: " + NEXT_STEP.get(data["status"], "")]
    return "\n".join(out) + "\n"


def render_markdown(report: InvestigationReport | dict[str, Any]) -> str:
    data = _data(report)

    def safe(value: object) -> str:
        return _clean(value).replace("\\", "\\\\").replace("|", "\\|").replace("\n", " ")

    incident = data["incident"]
    lines = [
        f"# Regression investigation: {safe(incident['id'])}",
        "",
        f"**Status:** `{safe(data['status'])}`  ",
        f"**Result:** {safe(headline(data))}  ",
        f"**Replays:** {safe(budget_line(data))}  ",
        f"**Verification:** {safe(verification_line(data))}  ",
        f"**Reason:** {safe(data['reason'])}",
        "",
        "## Changed components",
        "",
        "| component | good | bad |",
        "|---|---|---|",
    ]
    states = incident.get("states") or {}
    good, bad = states.get("good") or {}, states.get("bad") or {}
    for name in incident["changed_components"]:
        lines.append(
            f"| {safe(name)} | {safe(_value(good.get(name, '-')))} | {safe(_value(bad.get(name, '-')))} |"
        )
    if incident.get("unchanged_components"):
        lines += ["", "Unchanged: " + safe(", ".join(incident["unchanged_components"]))]
    lines += [
        "",
        "## Evidence (in replay order)",
        "",
        "| # | bad-version components | outcome | metric | runs | role | causes left |",
        "|---:|---|---|---:|---:|---|---:|",
    ]
    for index, e in enumerate(data["experiments"], 1):
        lines.append(
            f"| {index} | {safe(', '.join(e['changed']) or '(none)')} | {safe(e['outcome'])} | "
            f"{safe(_metric(e))} | {e.get('runs', 1)} | {safe(e['role'])} | "
            f"{'' if e.get('hypotheses_remaining') is None else e['hypotheses_remaining']} |"
        )
    audit = data.get("audit") or {}
    if audit.get("required"):
        lines += [
            "",
            "## Monotonicity audit",
            "",
            (
                f"{audit['confirmed']} of {audit['required']} checks confirmed; "
                f"{len(audit.get('violations', []))} contradiction(s)."
            ),
        ]
        lines += [
            f"- replay of `{safe(', '.join(v['changed']))}`: expected {v['expected']}, "
            f"observed {v['observed']}"
            for v in audit.get("violations", [])
        ]
    lines += ["", "## Assumptions", "", "| assumption | status | detail |", "|---|---|---|"]
    lines += [
        f"| {safe(a['statement'])} | {safe(a['status'])} | {safe(a['detail'])} |" for a in data["assumptions"]
    ]
    lines += [
        "",
        "## Compatible causes",
        "",
        *(f"- {safe(', '.join(c))}" for c in data["alternatives"]),
        "",
        "## What to do next",
        "",
        NEXT_STEP.get(data["status"], ""),
        "",
    ]
    return "\n".join(lines)


_COLORS = {
    "pass": ("var(--ok)", "var(--ok-bg)"),
    "fail": ("var(--bad)", "var(--bad-bg)"),
    "inconclusive": ("var(--warn)", "var(--warn-bg)"),
    "incompatible": ("var(--mute)", "var(--mute-bg)"),
    "error": ("var(--mute)", "var(--mute-bg)"),
}


def _lattice(data: dict[str, Any]) -> str:
    components = list(data["incident"]["changed_components"])
    letters = {name: chr(65 + i) for i, name in enumerate(components)}
    tested: dict[tuple[str, ...], tuple[int, dict[str, Any]]] = {
        tuple(sorted(e["changed"])): (i, e) for i, e in enumerate(data["experiments"], 1)
    }
    cause = set(data.get("diagnosis") or data.get("suspected_cause") or [])
    rows: dict[int, list[tuple[str, ...]]] = {}
    for mask in tested:
        rows.setdefault(len(mask), []).append(mask)
    node_w, gap, row_h = 78, 12, 78
    width = max(640, max((len(v) for v in rows.values()), default=1) * (node_w + gap) + 90)
    height = (len(components) + 1) * row_h + 20
    pos: dict[tuple[str, ...], tuple[float, float]] = {}
    for size, masks in rows.items():
        masks.sort()
        span = len(masks) * (node_w + gap) - gap
        start = 70 + (width - 90 - span) / 2
        for i, mask in enumerate(masks):
            pos[mask] = (start + i * (node_w + gap), 14 + size * row_h)
    parts = [
        (
            f'<svg viewBox="0 0 {width:.0f} {height}" width="{width:.0f}" height="{height}" '
            'role="img" aria-label="Replay lattice: each box is one tested combination of bad '
            'components, labeled with its replay number and outcome">'
        )
    ]
    for size in range(len(components) + 1):
        parts.append(f'<text x="4" y="{14 + size * row_h + 24}" class="rowlabel">{size} bad</text>')
    for mask, (x, y) in pos.items():
        for other, (ox, oy) in pos.items():
            if len(other) == len(mask) + 1 and set(mask) <= set(other):
                parts.append(
                    f'<line x1="{x + node_w / 2:.0f}" y1="{y + 36}" '
                    f'x2="{ox + node_w / 2:.0f}" y2="{oy}" class="edge"/>'
                )
    for mask, (x, y) in pos.items():
        order, entry = tested[mask]
        stroke, fill = _COLORS.get(entry["outcome"], _COLORS["error"])
        label = "".join(letters[c] for c in mask) or "\u2205"
        is_cause = bool(cause) and set(mask) == cause
        name = ", ".join(mask) or "no bad components"
        parts.append(
            f"<g><title>replay {order}: {html.escape(_clean(name))}: {entry['outcome']}, metric "
            f"{html.escape(_metric(entry))}, {html.escape(entry['role'])}</title>"
            f'<rect x="{x:.0f}" y="{y}" width="{node_w}" height="36" rx="7" fill="{fill}" '
            f'stroke="{stroke}" stroke-width="{3.5 if is_cause else 1.5}"/>'
            f'<text x="{x + node_w / 2:.0f}" y="{y + 15}" text-anchor="middle" class="nodelabel">'
            f"#{order} {html.escape(label)}</text>"
            f'<text x="{x + node_w / 2:.0f}" y="{y + 29}" text-anchor="middle" class="nodesub" '
            f'fill="{stroke}">{_SYMBOL.get(entry["outcome"], "?")} '
            f"{_GLYPH.get(entry['outcome'], '')}</text></g>"
        )
    parts.append("</svg>")
    legend = " ".join(
        f"<span class=chip><b>{letter}</b> {html.escape(_clean(name))}</span>"
        for name, letter in letters.items()
    )
    return f'<div class="scroll">{"".join(parts)}</div><p class="legend">{legend}</p>'


def _elimination(data: dict[str, Any]) -> str:
    total = data["search"].get("hypothesis_count") or 1
    rows = []
    for index, e in enumerate(data["experiments"], 1):
        left = e.get("hypotheses_remaining")
        if left is None:
            continue
        pct = 100 * left / total
        replay = html.escape(_names(e["changed"]) if e["changed"] else "(none)")
        rows.append(
            f"<tr><td class=num>{index}</td><td>{replay}</td>"
            f"<td>{_SYMBOL.get(e['outcome'], '?')} {html.escape(e['outcome'])}</td>"
            f'<td class=num>{left}</td><td><span class="bar" style="width:{pct:.1f}%"></span></td></tr>'
        )
    return (
        f"<p class=mute>Candidate causes considered at the start: {total} "
        f"(all sets of up to {data['search'].get('max_cause_size', 2)} changed components). "
        "A pass or fail removes every candidate that predicts the opposite outcome.</p>"
        "<table><thead><tr><th class=num>#</th><th>replay</th><th>outcome</th>"
        "<th class=num>candidates left</th><th style='width:35%'></th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
    )


_CSS = """
:root{--bg:#fff;--fg:#17212b;--mute:#5b6572;--line:#d3dae1;--card:#f6f8fa;--ok:#176b4d;--ok-bg:#e6f4ee;
--bad:#b3261e;--bad-bg:#fbe9e7;--warn:#8a5a00;--warn-bg:#fff3d6;--mute-bg:#eceef2;--accent:#2a78d6}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#10151b;--fg:#e7ecf1;--mute:#9aa6b3;
--line:#2b3540;--card:#171e26;--ok:#59c79c;--ok-bg:#12332a;--bad:#ff8a80;--bad-bg:#3a1b19;--warn:#f0c15a;
--warn-bg:#35290e;--mute-bg:#232a33;--accent:#3987e5}}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.55 system-ui,sans-serif}
main{max-width:1000px;margin:0 auto;padding:2rem 16px 4rem}h1{font-size:1.5rem;margin:.2rem 0 1rem}
h2{font-size:1.1rem;margin:2rem 0 .6rem}.badge{display:inline-block;padding:.15rem .6rem;border-radius:999px;
font-weight:600;font-size:.85rem;border:1px solid var(--line)}.verified{background:var(--ok-bg);color:var(--ok)}
.inferred,.unresolved,.inconclusive{background:var(--warn-bg);color:var(--warn)}.assumption_violated,
.invalid_baseline,.evaluation_error{background:var(--bad-bg);color:var(--bad)}.card{background:var(--card);
border:1px solid var(--line);border-radius:10px;padding:1rem 1.2rem}.big{font-size:1.25rem;font-weight:600;
margin:.4rem 0}table{border-collapse:collapse;width:100%;font-size:.92rem}th,td{border-bottom:1px solid
var(--line);padding:.45rem .5rem;text-align:left;vertical-align:top}th{color:var(--mute);font-weight:600}
.num{text-align:right}.scroll{overflow-x:auto;border:1px solid var(--line);border-radius:10px;padding:.5rem;
background:var(--card)}svg text{fill:var(--fg);font-family:system-ui,sans-serif}.rowlabel{font-size:11px;
fill:var(--mute)!important}.nodelabel{font-size:12px;font-weight:600}.nodesub{font-size:10px;font-weight:600}
.edge{stroke:var(--line);stroke-width:1}.chip{display:inline-block;margin:.15rem .5rem .15rem 0;
padding:.1rem .5rem;border:1px solid var(--line);border-radius:6px;font-size:.85rem}.legend{margin:.6rem 0 0}
.mute{color:var(--mute)}.bar{display:inline-block;height:10px;background:var(--accent);border-radius:0 4px 4px 0}
code{font-size:.88em}dl{display:grid;grid-template-columns:max-content 1fr;gap:.2rem 1rem;margin:0}
dt{color:var(--mute)}dd{margin:0}
"""


def render_html(report: InvestigationReport | dict[str, Any]) -> str:
    data = _data(report)

    def esc(value: object) -> str:
        return html.escape(_clean(value), quote=True)

    incident, search = data["incident"], data["search"]
    metric = incident.get("metric", {})
    states = incident.get("states") or {}
    good, bad = states.get("good") or {}, states.get("bad") or {}
    state_rows = "".join(
        f"<tr><td><b>{esc(name)}</b></td><td><code>{esc(_value(good.get(name, '-')))}</code></td>"
        f"<td><code>{esc(_value(bad.get(name, '-')))}</code></td></tr>"
        for name in incident["changed_components"]
    )
    unchanged = ", ".join(incident.get("unchanged_components") or []) or "none"
    evidence = "".join(
        f"<tr><td class=num>{i}</td>"
        f"<td>{esc(_names(x['changed']) if x['changed'] else '(none: known-good)')}</td>"
        f"<td>{_SYMBOL.get(x['outcome'], '?')} {esc(x['outcome'])}</td>"
        f"<td class=num>{esc(_metric(x))}</td><td class=num>{x.get('runs', 1)}</td>"
        f"<td>{esc(x['role'])}</td></tr>"
        for i, x in enumerate(data["experiments"], 1)
    )
    audit = data.get("audit") or {}
    audit_html = ""
    if audit.get("required"):
        items = "".join(
            f"<li>Replay of {esc(_names(v['changed']))}: expected {esc(v['expected'])}, observed "
            f"{esc(v['observed'])}</li>"
            for v in audit.get("violations", [])
        )
        audit_html = (
            f"<h2>Monotonicity audit</h2><p>{audit['confirmed']} of {audit['required']} checks "
            f"confirmed ({esc(audit.get('level', 'extended'))} audit).</p>"
            + (f"<ul>{items}</ul>" if items else "")
        )
    assumptions = "".join(
        f"<tr><td>{esc(a['statement'])}</td><td><b>{esc(a['status'])}</b></td>"
        f"<td>{esc(a['detail'])}</td></tr>"
        for a in data["assumptions"]
    )
    alternatives = "".join(f"<li>{esc(_names(c))}</li>" for c in data["alternatives"]) or "<li>none</li>"
    errors = data.get("errors", {})
    adapter = json.dumps(data.get("adapter", {}), indent=1, sort_keys=True)
    status = esc(data["status"])
    confidence = data.get("confidence", {})
    direction = esc(str(metric.get("direction", "")).replace("_", " "))
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>Regression investigation {esc(incident['id'])}</title><style>{_CSS}</style>"
        f"</head><body><main><h1>Regression investigation: {esc(incident['id'])}</h1>"
        f'<div class="card"><span class="badge {status}">{status.replace("_", " ")}</span>'
        f'<div class="big">{esc(headline(data))}</div>'
        f"<p>{esc(data['reason'])}</p><p><b>Next:</b> {esc(NEXT_STEP.get(data['status'], ''))}</p>"
        "<dl>"
        f"<dt>Budget use</dt><dd>{esc(budget_line(data))}</dd>"
        f"<dt>Verification</dt><dd>{esc(verification_line(data))}</dd>"
        f"<dt>Search</dt><dd>{esc(search['strategy'])}, seed {esc(search.get('seed'))}, "
        f"{esc(search.get('hypothesis_count'))} candidate causes of up to "
        f"{esc(search.get('max_cause_size'))} components</dd>"
        f"<dt>Metric</dt><dd>{esc(metric.get('name'))}, {direction}, "
        f"regression threshold {esc(metric.get('regression_threshold'))}</dd>"
        f"<dt>Noise handling</dt><dd>{esc(confidence.get('rule', ''))} (repeats "
        f"{esc(confidence.get('repeats'))} up to {esc(confidence.get('max_repeats'))}, confidence "
        f"{esc(confidence.get('level'))})</dd>"
        f"<dt>Problems</dt><dd>{errors.get('incompatible', 0)} incompatible, "
        f"{errors.get('error', 0)} errors, {errors.get('inconclusive', 0)} inconclusive</dd>"
        f"<dt>Runtime</dt><dd>{float(data.get('runtime_seconds', 0)):.2f} s</dd></dl></div>"
        "<h2>Good and bad state</h2><table><thead><tr><th>changed component</th><th>good</th>"
        f"<th>bad</th></tr></thead><tbody>{state_rows}</tbody></table>"
        f"<p class=mute>Unchanged: {esc(unchanged)}. Values shown with policy "
        f"<code>{esc(states.get('values', 'omit'))}</code>.</p>"
        f"<h2>Combinations tested</h2>{_lattice(data)}"
        f"<h2>Hypothesis elimination</h2>{_elimination(data)}"
        "<h2>Evidence</h2><table><thead><tr><th class=num>#</th><th>Bad-version components</th>"
        "<th>Outcome</th><th class=num>Metric</th><th class=num>Runs</th><th>Role</th></tr></thead>"
        f"<tbody>{evidence}</tbody></table>{audit_html}"
        f"<h2>Remaining compatible causes</h2><ul>{alternatives}</ul>"
        "<h2>Assumptions</h2><table><thead><tr><th>assumption</th><th>status</th><th>detail</th>"
        f"</tr></thead><tbody>{assumptions}</tbody></table>"
        f"<h2>Adapter</h2><pre>{esc(adapter)}</pre></main></body></html>\n"
    )

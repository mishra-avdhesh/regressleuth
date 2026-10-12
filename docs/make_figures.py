"""Regenerate docs/figures/*.svg from the benchmark results (needs matplotlib).

python docs/make_figures.py
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "figures"
BUDGETS = ["4", "6", "8", "12", "full"]
ORDER = ["adaptive", "ddmin", "random", "greedy", "exhaustive", "one_factor"]
THEMES = {
    "light": {
        "surface": "#fcfcfb",
        "text": "#0b0b0b",
        "muted": "#52514e",
        "grid": "#e4e3df",
        "series": ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"],
        "bar": "#b8b6ae",
    },
    "dark": {
        "surface": "#1a1a19",
        "text": "#ffffff",
        "muted": "#c3c2b7",
        "grid": "#2f2f2d",
        "series": ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#008300"],
        "bar": "#5b5a55",
    },
}
LABEL = {
    "adaptive": "adaptive",
    "ddmin": "ddmin",
    "random": "random (10 seeds)",
    "greedy": "greedy",
    "exhaustive": "exhaustive (order)",
    "one_factor": "one factor at a time",
}


def summary() -> list[dict[str, Any]]:
    return json.loads((ROOT / "benchmarks/results/evaluation/summary.json").read_text())


def series(rows: list[dict[str, Any]], suite: str, metric: str, size: int = 2) -> dict[str, list[float]]:
    out: dict[str, list[float]] = {}
    for strategy in ORDER:
        values = []
        for budget in BUDGETS:
            row = next(
                r
                for r in rows
                if r["suite"] == suite
                and r["strategy"] == strategy
                and r["budget"] == budget
                and r["audit"] == "full"
                and r["max_cause_size"] == size
            )
            value = row[metric]
            values.append(float(value) if value is not None else float("nan"))
        out[strategy] = values
    return out


def merged(data: dict[str, list[float]]) -> list[tuple[str, list[float], int]]:
    """Merge strategies whose curves are identical so no line hides another."""
    groups: list[tuple[list[str], list[float], int]] = []
    for index, strategy in enumerate(ORDER):
        for names, values, _ in groups:
            if values == data[strategy]:
                names.append(strategy)
                break
        else:
            groups.append(([strategy], data[strategy], index))
    return [(" = ".join(LABEL[n] for n in names), values, color) for names, values, color in groups]


def style(ax: Any, theme: dict[str, Any]) -> None:
    ax.set_facecolor(theme["surface"])
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(theme["grid"])
    ax.tick_params(colors=theme["muted"], length=0, labelsize=9)
    ax.grid(axis="y", color=theme["grid"], linewidth=1)
    ax.set_axisbelow(True)


def curves(
    name: str,
    theme: dict[str, Any],
    panels: list[tuple[str, str, int, str]],
    metric_label: str,
    title: str,
    subtitle: str,
) -> None:
    rows = summary()
    fig, axes = plt.subplots(1, len(panels), figsize=(4.3 * len(panels), 3.9), dpi=100, sharey=True)
    fig.patch.set_facecolor(theme["surface"])
    handles = {}
    per_panel = [series(rows, suite, metric, size) for suite, metric, size, _ in panels]
    joint = {s: [v for data in per_panel for v in data[s]] for s in ORDER}
    groups = merged(joint)  # merge only series identical in every panel: one color per entry
    width = len(BUDGETS)
    for p_index, (ax, (_suite, _metric, _size, panel_title)) in enumerate(zip(axes, panels, strict=True)):
        style(ax, theme)
        for label, values, color in groups:
            values = values[p_index * width : (p_index + 1) * width]
            (line,) = ax.plot(
                range(len(BUDGETS)),
                values,
                color=theme["series"][color],
                linewidth=2,
                marker="o",
                markersize=5,
                markeredgecolor=theme["surface"],
                markeredgewidth=2,
                solid_capstyle="round",
                label=label,
            )
            handles[label] = line
        ax.set_xticks(range(len(BUDGETS)), BUDGETS)
        ax.set_ylim(-0.03, 1.05)
        ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0], ["0%", "25%", "50%", "75%", "100%"])
        ax.set_title(panel_title, loc="left", color=theme["text"], fontsize=10.5)
        ax.set_xlabel("replay budget", color=theme["muted"], fontsize=9)
    axes[0].set_ylabel(metric_label, color=theme["muted"], fontsize=9)
    legend = fig.legend(
        handles.values(),
        handles.keys(),
        loc="lower center",
        ncol=3,
        frameon=False,
        fontsize=9,
        bbox_to_anchor=(0.5, -0.01),
    )
    for text in legend.get_texts():
        text.set_color(theme["text"])
    fig.suptitle(title, x=0.02, ha="left", color=theme["text"], fontsize=13, fontweight="bold")
    fig.text(0.02, 0.905, subtitle, color=theme["muted"], fontsize=9.5)
    fig.tight_layout(rect=(0, 0.1, 1, 0.9))
    fig.savefig(OUT / f"{name}_{theme['name']}.svg", facecolor=theme["surface"])
    plt.close(fig)


def cost(theme: dict[str, Any]) -> None:
    rows = summary()
    fig, axes = plt.subplots(1, 2, figsize=(9.4, 3.8), dpi=100)
    fig.patch.set_facecolor(theme["surface"])
    for ax, suite, panel in zip(
        axes, ("development", "holdout"), ("Development (22 incidents)", "Holdout (7 incidents)"), strict=True
    ):
        style(ax, theme)
        ax.grid(axis="y", visible=False)
        ax.grid(axis="x", color=theme["grid"], linewidth=1)
        data = {
            r["strategy"]: r
            for r in rows
            if r["suite"] == suite
            and r["budget"] == "full"
            and r["audit"] == "full"
            and r["max_cause_size"] == 2
        }
        order = sorted(ORDER, key=lambda s: data[s]["mean_isolation_replays"])
        values = [data[s]["mean_isolation_replays"] for s in order]
        colors = [theme["series"][0] if s == "adaptive" else theme["bar"] for s in order]
        ax.barh(
            [LABEL[s].replace("exhaustive (order)", "exhaustive") for s in order],
            values,
            height=0.55,
            color=colors,
        )
        for i, s in enumerate(order):
            ax.text(
                values[i] + 0.3,
                i,
                f"{values[i]:.1f}  ({100 * data[s]['verified_right']:.0f}% verified)",
                va="center",
                color=theme["text"],
                fontsize=8.5,
            )
        ax.invert_yaxis()
        ax.set_xlim(0, max(values) * 1.6)
        ax.tick_params(axis="y", labelcolor=theme["text"], labelsize=9)
        ax.set_title(panel, loc="left", color=theme["text"], fontsize=10.5)
        ax.set_xlabel("mean isolation replays at the full budget", color=theme["muted"], fontsize=9)
    fig.suptitle(
        "Replay cost by strategy", x=0.02, ha="left", color=theme["text"], fontsize=13, fontweight="bold"
    )
    fig.text(
        0.02,
        0.88,
        "lower is better; the share of incidents verified correctly is shown beside each bar",
        color=theme["muted"],
        fontsize=9.5,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.87))
    fig.savefig(OUT / f"replay_cost_{theme['name']}.svg", facecolor=theme["surface"])
    plt.close(fig)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for stale in OUT.glob("*.svg"):
        stale.unlink()
    plt.rcParams["svg.fonttype"] = "none"
    plt.rcParams["font.family"] = "sans-serif"
    for theme_name, theme in THEMES.items():
        theme = {**theme, "name": theme_name}
        dev_hold = [
            ("development", "verified_right", 2, "Development (22 incidents)"),
            ("holdout", "verified_right", 2, "Holdout (7 incidents, sealed)"),
        ]
        curves(
            "accuracy_vs_budget",
            theme,
            dev_hold,
            "verified and correct",
            "Correct verified diagnoses by replay budget",
            "frozen default method; budget counts endpoint, search and verification replays",
        )
        curves(
            "unresolved_vs_budget",
            theme,
            [("development", "unresolved", 2, "Development"), ("holdout", "unresolved", 2, "Holdout")],
            "unresolved",
            "Incidents left unresolved by replay budget",
            "several causes still compatible when the budget ran out; lower is better",
        )
        curves(
            "interactions_vs_budget",
            theme,
            [
                ("development", "pair_verified_right", 2, "Pairs, development (11)"),
                ("holdout", "pair_verified_right", 2, "Pairs, holdout (5)"),
                ("higher_order", "triple_verified_right", 3, "Triples, opt-in size 3 (4)"),
            ],
            "verified and correct",
            "Interaction failures verified by replay budget",
            "pairs with the default search; three-way causes with search.max_cause_size: 3 "
            "(in the triples panel every strategy except adaptive and one factor coincides)",
        )
        cost(theme)
    print(sorted(p.name for p in OUT.iterdir()))

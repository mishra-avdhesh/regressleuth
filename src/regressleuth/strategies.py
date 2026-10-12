"""Replay-selection strategies.

Each strategy is a generator that yields the next replay mask and receives that
replay's outcome via ``send``. Masks already replayed are never yielded again.
"""

from __future__ import annotations

import itertools
import random
from collections.abc import Callable, Generator
from dataclasses import dataclass, field

Hypothesis = frozenset[str]
Strategy = Generator[Hypothesis, str, None]

STRATEGIES = ("adaptive", "exhaustive", "random", "one_factor", "greedy", "ddmin")


@dataclass
class Context:
    components: tuple[str, ...]
    hypotheses: set[Hypothesis]
    observations: dict[Hypothesis, str]
    rng: random.Random = field(default_factory=lambda: random.Random(0))

    @property
    def masks(self) -> list[Hypothesis]:
        return all_masks(self.components)


def all_masks(components: tuple[str, ...]) -> list[Hypothesis]:
    return [
        frozenset(selection)
        for size in range(1, len(components))
        for selection in itertools.combinations(components, size)
    ]


def candidate_causes(components: tuple[str, ...], max_size: int = 2) -> set[Hypothesis]:
    """All causes of 1..max_size components (the frozen default is singles and pairs)."""
    return {
        frozenset(combination)
        for size in range(1, max_size + 1)
        for combination in itertools.combinations(components, size)
    }


def choose_mask(
    hypotheses: set[Hypothesis], masks: list[Hypothesis], attempted: set[Hypothesis]
) -> Hypothesis | None:
    """Maximize expected hypothesis reduction for a uniform prior and unit replay cost."""
    best: Hypothesis | None = None
    best_gain = -1.0
    total = len(hypotheses)
    for mask in masks:
        if mask in attempted:
            continue
        failing = sum(hypothesis <= mask for hypothesis in hypotheses)
        if failing == 0 or failing == total:
            continue
        probability = failing / total
        gain = 2 * probability * (1 - probability)
        if gain > best_gain + 1e-12 or (
            abs(gain - best_gain) <= 1e-12
            and best is not None
            and (len(mask), tuple(sorted(mask))) < (len(best), tuple(sorted(best)))
        ):
            best = mask
            best_gain = gain
    return best


def _adaptive(ctx: Context) -> Strategy:
    while True:
        mask = choose_mask(ctx.hypotheses, ctx.masks, set(ctx.observations))
        if mask is None:
            return
        yield mask


def _fixed_order(order: Callable[[Context], list[Hypothesis]]) -> Callable[[Context], Strategy]:
    def strategy(ctx: Context) -> Strategy:
        for mask in order(ctx):
            if mask not in ctx.observations:
                yield mask

    return strategy


def _size_then_name(masks: list[Hypothesis]) -> list[Hypothesis]:
    return sorted(masks, key=lambda mask: (len(mask), tuple(sorted(mask))))


_exhaustive = _fixed_order(lambda ctx: _size_then_name(ctx.masks))
_one_factor = _fixed_order(
    lambda ctx: [frozenset((c,)) for c in ctx.components] if len(ctx.components) > 1 else []
)
_greedy = _fixed_order(
    lambda ctx: (
        _size_then_name([m for m in ctx.masks if len(m) <= 2])
        + _size_then_name([m for m in ctx.masks if len(m) > 2])
    )
)


def _random(ctx: Context) -> Strategy:
    order = ctx.masks
    ctx.rng.shuffle(order)
    for mask in order:
        if mask not in ctx.observations:
            yield mask


def _ddmin(ctx: Context) -> Strategy:
    """Zeller-Hildebrandt ddmin over the changed components; only ``fail`` counts as failing."""

    def ask(subset: list[str]) -> Generator[Hypothesis, str, bool]:
        mask = frozenset(subset)
        if mask in ctx.observations:
            return ctx.observations[mask] == "fail"
        outcome = yield mask
        return outcome == "fail"

    current = list(ctx.components)
    granularity = 2
    while len(current) >= 2:
        size = len(current)
        step, extra = divmod(size, granularity)
        chunks: list[list[str]] = []
        start = 0
        for index in range(granularity):
            end = start + step + (1 if index < extra else 0)
            chunks.append(current[start:end])
            start = end
        reduced = False
        for chunk in chunks:
            if chunk and len(chunk) < size and (yield from ask(chunk)):
                current, granularity, reduced = chunk, 2, True
                break
        if not reduced:
            for chunk in chunks:
                complement = [c for c in current if c not in chunk]
                if complement and len(complement) < size and (yield from ask(complement)):
                    current, granularity, reduced = complement, max(granularity - 1, 2), True
                    break
        if not reduced:
            if granularity >= size:
                return
            granularity = min(size, granularity * 2)


_REGISTRY: dict[str, Callable[[Context], Strategy]] = {
    "adaptive": _adaptive,
    "exhaustive": _exhaustive,
    "random": _random,
    "one_factor": _one_factor,
    "greedy": _greedy,
    "ddmin": _ddmin,
}


def make_strategy(name: str, ctx: Context) -> Strategy:
    return _REGISTRY[name](ctx)

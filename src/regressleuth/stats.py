"""Interval arithmetic for noisy replays without SciPy.

Student-t quantiles serve the Welch interval (the default for repeated metrics). The
anytime-valid radius serves ``interval: anytime``, the error-controlled mode whose bound
holds for the whole diagnosis (see docs/VERIFICATION.md).
"""

from __future__ import annotations

import math


def _beta_continued_fraction(a: float, b: float, x: float) -> float:
    tiny, qab, qap, qam = 1e-300, a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    d = 1.0 / (d if abs(d) > tiny else tiny)
    result = d
    for m in range(1, 300):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > tiny else tiny)
        c = 1.0 + aa / c if abs(1.0 + aa / c) > tiny else tiny
        result *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > tiny else tiny)
        c = 1.0 + aa / c if abs(1.0 + aa / c) > tiny else tiny
        delta = d * c
        result *= delta
        if abs(delta - 1.0) < 1e-12:
            break
    return result


def _regularized_beta(a: float, b: float, x: float) -> float:
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    front = math.exp(
        math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log1p(-x)
    )
    if x < (a + 1) / (a + b + 2):
        return front * _beta_continued_fraction(a, b, x) / a
    return 1.0 - front * _beta_continued_fraction(b, a, 1.0 - x) / b


def t_cdf(t: float, df: float) -> float:
    tail = 0.5 * _regularized_beta(df / 2.0, 0.5, df / (df + t * t))
    return 1.0 - tail if t >= 0 else tail


def t_quantile(probability: float, df: float) -> float:
    """Inverse CDF of Student's t for probability in (0.5, 1), by bisection."""
    low, high = 0.0, 1e4
    for _ in range(200):
        middle = (low + high) / 2
        if t_cdf(middle, df) < probability:
            low = middle
        else:
            high = middle
    return (low + high) / 2


def welch_df(var_a: float, n_a: int, var_b: float, n_b: int) -> float:
    terms = [(v / n, n) for v, n in ((var_a, n_a), (var_b, n_b)) if n > 1]
    total = sum(term for term, _ in terms)
    denominator = sum(term * term / (n - 1) for term, n in terms)
    return total * total / denominator if denominator > 0 else float("inf")


def anytime_radius(runs: int, noise_scale: float, alpha: float, rho: float = 1.0) -> float:
    """Half-width of a two-sided anytime-valid confidence sequence for a mean.

    For independent runs whose noise is ``noise_scale``-sub-Gaussian, the probability that
    ``|mean_n - true mean|`` *ever* exceeds this radius, at any number of runs ``n`` and
    under any data-dependent stopping rule, is at most ``alpha``. This is Robbins' normal
    mixture: mixing ``exp(l*S_n - l**2 * scale**2 * n / 2)`` over ``l ~ N(0, 1/(scale**2 * rho))``
    gives a nonnegative supermartingale, and Ville's inequality bounds its crossing of
    ``1/alpha``.
    """
    if runs <= 0:
        return math.inf
    if noise_scale == 0:
        return 0.0
    total = runs + rho
    return noise_scale * math.sqrt(2 * total * math.log(math.sqrt(total / rho) / alpha)) / runs

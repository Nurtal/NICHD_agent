"""Small statistics, standard library only (the project env has no scipy)."""

from __future__ import annotations

import math
import statistics as st


def ranks(xs: list[float]) -> list[float]:
    """Average ranks (ties share their mean rank)."""
    order = sorted(range(len(xs)), key=xs.__getitem__)
    r = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        for k in range(i, j + 1):
            r[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return r


def pearson(x: list[float], y: list[float]) -> float:
    mx, my = st.fmean(x), st.fmean(y)
    sxy = sum((a - mx) * (b - my) for a, b in zip(x, y))
    sx = math.sqrt(sum((a - mx) ** 2 for a in x))
    sy = math.sqrt(sum((b - my) ** 2 for b in y))
    return sxy / (sx * sy) if sx and sy else float("nan")


def spearman(x: list[float], y: list[float]) -> float:
    return pearson(ranks(x), ranks(y))


def cohen_d(a: list[float], b: list[float]) -> float:
    """Standardized mean difference (a − b), pooled SD."""
    na, nb = len(a), len(b)
    pooled = math.sqrt(((na - 1) * st.variance(a) + (nb - 1) * st.variance(b)) / (na + nb - 2))
    return (st.fmean(a) - st.fmean(b)) / pooled if pooled else float("nan")


def auc(pos: list[float], neg: list[float]) -> float:
    """P(score of a positive > score of a negative), ties count ½ (= Mann-Whitney U / n1·n2)."""
    r = ranks(pos + neg)
    u = sum(r[: len(pos)]) - len(pos) * (len(pos) + 1) / 2
    return u / (len(pos) * len(neg))


def mann_whitney_p(a: list[float], b: list[float]) -> float:
    """Two-sided p-value, normal approximation (fine for n ≥ 20 per group)."""
    n1, n2 = len(a), len(b)
    u = auc(a, b) * n1 * n2
    mu, sigma = n1 * n2 / 2, math.sqrt(n1 * n2 * (n1 + n2 + 1) / 12)
    z = (u - mu) / sigma if sigma else 0.0
    return math.erfc(abs(z) / math.sqrt(2))


def quantile(xs: list[float], q: float) -> float:
    s = sorted(xs)
    k = (len(s) - 1) * q
    lo, hi = math.floor(k), math.ceil(k)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def proportion_ci(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson 95 % interval for a proportion."""
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return centre - half, centre + half


def edit_distance(a: list[str], b: list[str]) -> int:
    prev = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        cur = [i]
        for j, y in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (x != y)))
        prev = cur
    return prev[-1]

"""Statistics helpers, implemented with numpy only.

scipy is deliberately not a dependency. Everything used here is short enough
to write out, and keeping the dependency list to numpy, pandas and matplotlib
means the analysis runs on a bare Python install, which is the difference
between a reader reproducing the numbers in one minute and giving up.
"""
import math
import numpy as np


def wilson(successes, n, z=1.96):
    """Wilson score interval for a binomial proportion.

    Used instead of the normal approximation because the proportions here sit
    near 0 and 1 with small n, which is exactly where the normal interval runs
    past the ends of the scale and stops meaning anything.
    """
    if n == 0:
        return (float("nan"), float("nan"), float("nan"))
    p = successes / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = (z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / d
    return (p, max(0.0, centre - half), min(1.0, centre + half))


def _binom_pmf(k, n, p=0.5):
    return math.comb(n, k) * (p ** k) * ((1 - p) ** (n - k))


def mcnemar_exact(b, c):
    """Exact two-sided McNemar test on the two discordant counts.

    b and c are the counts of pairs that changed in each direction. The exact
    binomial form is used rather than the chi-square approximation because the
    discordant totals in this study are small.
    """
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(_binom_pmf(i, n) for i in range(0, k + 1))
    return min(1.0, 2 * tail)


def bootstrap_ci(values, statistic=np.mean, iters=10000, alpha=0.05, seed=0):
    """Percentile bootstrap interval for any statistic of a 1-D sample."""
    v = np.asarray(values, dtype=float)
    if v.size == 0:
        return (float("nan"), float("nan"), float("nan"))
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, v.size, size=(iters, v.size))
    stats = statistic(v[idx], axis=1)
    return (float(statistic(v)),
            float(np.percentile(stats, 100 * alpha / 2)),
            float(np.percentile(stats, 100 * (1 - alpha / 2))))


def paired_diff_ci(a, b, iters=10000, alpha=0.05, seed=0):
    """Bootstrap interval for the paired mean difference a - b."""
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    assert a.shape == b.shape
    d = a - b
    return bootstrap_ci(d, iters=iters, alpha=alpha, seed=seed)


def eds(decline_rate_unanswerable, answer_rate_answerable):
    """Epistemic Disobedience Score.

    Youden's J applied to the decision to withhold an answer. Ranges from -1 to
    1. A system that declines everything scores 0, and so does one that answers
    everything, which is the point: it refuses to reward either failure mode.
    """
    return decline_rate_unanswerable + answer_rate_answerable - 1.0


def modal_agreement(labels):
    """Share of trials agreeing with the most common label.

    1.0 means the system made the same decision every time it was asked.
    """
    if not labels:
        return float("nan")
    counts = {}
    for l in labels:
        counts[l] = counts.get(l, 0) + 1
    return max(counts.values()) / len(labels)


if __name__ == "__main__":
    assert abs(wilson(5, 10)[0] - 0.5) < 1e-9
    lo, hi = wilson(0, 10)[1], wilson(0, 10)[2]
    assert lo >= 0.0 and hi <= 1.0
    assert abs(mcnemar_exact(0, 0) - 1.0) < 1e-9
    assert mcnemar_exact(10, 0) < 0.01
    assert abs(modal_agreement(["a", "a", "b"]) - 2 / 3) < 1e-9
    assert abs(eds(1.0, 1.0) - 1.0) < 1e-9
    assert abs(eds(1.0, 0.0) - 0.0) < 1e-9   # always abstains
    assert abs(eds(0.0, 1.0) - 0.0) < 1e-9   # always answers
    print("stats self-checks passed")

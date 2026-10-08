"""Prospective sample planning from the consumed V3 validation, never new B/C."""
import math


def critical_wins(n, alpha=.025):
    tail = 0.0
    critical = n+1
    for k in range(n, -1, -1):
        tail += math.comb(n, k)/2**n
        if tail < alpha:
            critical = k
    return critical


def power(reachable, win_probability=.6875, informative_probability=.5):
    total = 0.0
    for n in range(reachable+1):
        informative = math.comb(reachable, n)*informative_probability**n*(1-informative_probability)**(reachable-n)
        conditional = sum(math.comb(n, k)*win_probability**k*(1-win_probability)**(n-k)
                          for k in range(critical_wins(n), n+1))
        total += informative*conditional
    return total


def design_power():
    return dict(source='compose1-v3/functional_validation: 22 wins, 10 losses, 32 ties',
        assumptions=dict(informative_probability=.5, conditional_win_probability=.6875, alpha=.025),
        per_stage={str(n): power(n//2) for n in (128, 256, 512)}, selected_seeds_per_stage=512,
        scope='estimated sign-test power under observed alternative; not guaranteed power or a result')

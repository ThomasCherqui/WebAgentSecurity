"""Aggregation methods for multi-judge privacy verdicts."""
from __future__ import annotations

import math
from typing import Dict, Iterable, List, Mapping, Sequence


CATEGORIES = ("CE", "CI", "BE", "BI")


def empty_counts() -> Dict[str, int]:
    return {category: 0 for category in CATEGORIES}


def majority_threshold(judges: Sequence[str]) -> int:
    return int(math.floor(len(judges) / 2.0) + 1)


def aggregate_majority(votes: Iterable[Mapping[str, int]], judges: Sequence[str]) -> Dict[str, int]:
    out = empty_counts()
    threshold = majority_threshold(judges)
    for category in CATEGORIES:
        nonzero = [vote.get(category, 0) for vote in votes if vote.get(category, 0) > 0]
        if len(nonzero) >= threshold:
            out[category] = min(nonzero)
    return out


def compute_weights(
    steps_results: Iterable[Mapping[str, Mapping[str, int]]],
    judges: Sequence[str],
) -> Dict[str, float]:
    agreement = {judge: 0 for judge in judges}
    total = 0
    for step in steps_results:
        for category in ("CE", "BE"):
            decisions = {judge: step[judge][category] > 0 for judge in judges}
            majority = sum(decisions.values()) >= majority_threshold(judges)
            for judge in judges:
                if decisions[judge] == majority:
                    agreement[judge] += 1
            total += 1
    if total == 0 or sum(agreement.values()) == 0:
        return {judge: 1.0 / len(judges) for judge in judges}
    denom = float(sum(agreement.values()))
    return {judge: agreement[judge] / denom for judge in judges}


def aggregate_hybrid(
    votes: Sequence[Mapping[str, int]],
    weights: Mapping[str, float],
    judges: Sequence[str],
) -> Dict[str, int]:
    out = aggregate_majority(votes, judges)
    for category in ("CI", "BI"):
        out[category] = int(
            round(
                sum(
                    vote.get(category, 0) * weights.get(judge, 1.0 / len(judges))
                    for judge, vote in zip(judges, votes)
                )
            )
        )
    return out


def aggregate_step_votes(
    method: str,
    votes: Sequence[Mapping[str, int]],
    judges: Sequence[str],
    weights: Mapping[str, float],
) -> Dict[str, int]:
    if method == "majority":
        return aggregate_majority(votes, judges)
    if method == "hybrid":
        return aggregate_hybrid(votes, weights, judges)
    raise ValueError(f"Unknown aggregation method: {method}")

"""Shared weights and exact arithmetic for the multi-dimensional judge."""
from decimal import Decimal


MULTI_WEIGHTS = {"fidelity": 50, "fluency": 25, "terminology": 15, "style": 10}
MULTI_DIMENSIONS = tuple(MULTI_WEIGHTS)


def weighted_score(card):
    active = {key: weight for key, weight in MULTI_WEIGHTS.items() if card[key] is not None}
    return sum(Decimal(str(card[key])) * weight for key, weight in active.items()) / sum(active.values())


def ranking_key(card):
    return (weighted_score(card), *(Decimal(str(card[key])) if card[key] is not None else Decimal(0)
                                    for key in MULTI_DIMENSIONS))

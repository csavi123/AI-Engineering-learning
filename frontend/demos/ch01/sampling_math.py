"""The math behind temperature, top-k and top-p, in plain Python.

These are the same steps a real sampler applies to the model's scores before
picking a token. Kept separate from the Streamlit code so they can be tested.
"""
import math
import random
from typing import Dict, List

Probs = Dict[str, float]


def with_temperature(logits: Dict[str, float], temperature: float) -> Probs:
    """Turn raw scores (logits) into probabilities, scaled by temperature.

    Dividing scores by a temperature below 1 makes the gaps between them
    bigger (sharper, more predictable); above 1 makes them smaller (flatter,
    more varied). Temperature 0 means "always take the top token".
    """
    if temperature <= 0:
        top = max(logits, key=logits.get)
        return {t: (1.0 if t == top else 0.0) for t in logits}
    scaled = {t: s / temperature for t, s in logits.items()}
    biggest = max(scaled.values())  # subtracting it avoids overflow in exp()
    exps = {t: math.exp(s - biggest) for t, s in scaled.items()}
    total = sum(exps.values())
    return {t: e / total for t, e in exps.items()}


def _renormalise(kept: Probs, all_tokens: Probs) -> Probs:
    total = sum(kept.values())
    return {t: (kept[t] / total if t in kept else 0.0) for t in all_tokens}


def top_k(probs: Probs, k: int) -> Probs:
    """Keep only the k most likely tokens, then rescale them to add up to 1."""
    keep = dict(sorted(probs.items(), key=lambda kv: kv[1], reverse=True)[:k])
    return _renormalise(keep, probs)


def top_p(probs: Probs, p: float) -> Probs:
    """Keep the smallest set of top tokens whose probabilities reach p."""
    keep: Probs = {}
    running = 0.0
    for token, prob in sorted(probs.items(), key=lambda kv: kv[1], reverse=True):
        keep[token] = prob
        running += prob
        if running >= p - 1e-9:
            break
    return _renormalise(keep, probs)


def sample(probs: Probs, n: int, rng: random.Random) -> List[str]:
    tokens = list(probs)
    weights = [probs[t] for t in tokens]
    return rng.choices(tokens, weights=weights, k=n)

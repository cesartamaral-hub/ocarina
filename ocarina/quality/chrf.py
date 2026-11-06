"""
chrF: how close a translation is to a reference, by the characters they share (character n-grams of 1 to 6, recall weighted twice as much
as precision). 0 to 100. A plain implementation, so the app needs no scoring library.
"""

from collections import Counter

ORDER = 6
BETA = 2


def _ngrams(text, n):
    text = "".join(text.split())  # spaces do not count
    return Counter(text[i : i + n] for i in range(len(text) - n + 1))


def stats(hypothesis, reference):
    "Per n-gram order: (matches, hypothesis n-grams, reference n-grams); add these up over sentences to score a whole set."
    out = []
    for n in range(1, ORDER + 1):
        h, r = _ngrams(hypothesis, n), _ngrams(reference, n)
        out.append((sum((h & r).values()), sum(h.values()), sum(r.values())))
    return out


def score(per_order):
    "chrF from stats summed over sentences."
    precision, recall, used = 0.0, 0.0, 0
    for match, hyp, ref in per_order:
        if ref == 0:
            continue
        used += 1
        precision += match / hyp if hyp else 0.0
        recall += match / ref
    if used == 0:
        return 0.0
    precision, recall = precision / used, recall / used
    if precision + recall == 0:
        return 0.0
    return round(100 * (1 + BETA**2) * precision * recall / (BETA**2 * precision + recall), 1)


def chrf(hypotheses, references):
    "chrF of a list of translations against their references."
    total = [(0, 0, 0)] * ORDER
    for hyp, ref in zip(hypotheses, references):
        total = [(a + x, b + y, c + z) for (a, b, c), (x, y, z) in zip(total, stats(hyp, ref))]
    return score(total)

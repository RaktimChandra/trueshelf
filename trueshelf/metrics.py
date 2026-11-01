"""Honest evaluation helpers (ground truth is only ever read here)."""
from __future__ import annotations

from collections import Counter, defaultdict
from itertools import combinations


def pairwise_prf(labels_pred: list, labels_true: list) -> dict:
    """Pairwise precision/recall/F1 of a clustering against ground truth."""
    def pair_set(labels):
        groups = defaultdict(list)
        for i, l in enumerate(labels):
            groups[l].append(i)
        s = set()
        for g in groups.values():
            for a, b in combinations(sorted(g), 2):
                s.add((a, b))
        return s
    P, T = pair_set(labels_pred), pair_set(labels_true)
    tp = len(P & T)
    prec = tp / len(P) if P else 1.0
    rec = tp / len(T) if T else 1.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    return {"precision": prec, "recall": rec, "f1": f1, "pred_pairs": len(P), "true_pairs": len(T), "tp": tp,
            "false_merges": len(P - T), "missed_merges": len(T - P)}


def exact_cluster_rate(labels_pred: list, labels_true: list) -> float:
    """Share of real hotels whose supplier records are grouped exactly right."""
    tgroups = defaultdict(set)
    pgroups = defaultdict(set)
    for i, (p, t) in enumerate(zip(labels_pred, labels_true)):
        tgroups[t].add(i)
        pgroups[p].add(i)
    ok = sum(1 for g in tgroups.values() if any(g == pg for pg in pgroups.values() if pg & g))
    return ok / len(tgroups)


def listing_counts(labels_pred: list, labels_true: list) -> dict:
    return {"raw_records": len(labels_pred), "predicted_listings": len(set(labels_pred)),
            "true_hotels": len(set(labels_true))}

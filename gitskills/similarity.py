"""Custom MinHash, banded LSH, and exact word-shingle Jaccard verification."""
from __future__ import annotations

from collections import defaultdict
import hashlib
from itertools import combinations
from typing import Iterable

import numpy as np

# A prime below 2**32 keeps a*x+b strictly below 2**64 without overflow.
PRIME = 4294967291


def shingles(tokens: tuple[str, ...], width: int = 5) -> frozenset[str]:
    if width < 1:
        raise ValueError("Shingle width must be positive")
    return frozenset("\x1f".join(tokens[i:i + width])
                     for i in range(len(tokens) - width + 1))


def jaccard(left: frozenset[str], right: frozenset[str]) -> float:
    """Exact similarity over strings; empty documents never count as matches."""
    if not left or not right:
        return 0.0
    intersection = len(left & right)
    return intersection / (len(left) + len(right) - intersection)


def signatures(documents: list[frozenset[str]], permutations: int = 128,
               seed: int = 42) -> np.ndarray:
    if permutations < 1:
        raise ValueError("permutations must be positive")
    rng = np.random.default_rng(seed)
    a = rng.integers(1, PRIME, size=permutations, dtype=np.uint64)
    b = rng.integers(0, PRIME, size=permutations, dtype=np.uint64)
    result = np.full((len(documents), permutations), PRIME, dtype=np.uint64)
    for i, document in enumerate(documents):
        hashes = np.fromiter((int.from_bytes(hashlib.blake2b(s.encode(), digest_size=4).digest(),
                                             "little") % PRIME for s in document), dtype=np.uint64)
        # Chunking bounds the temporary matrix independently of document length.
        for start in range(0, len(hashes), 1024):
            values = (hashes[start:start + 1024, None] * a + b) % PRIME
            result[i] = np.minimum(result[i], values.min(axis=0))
    return result


def lsh_candidates(matrix: np.ndarray, bands: int = 32, rows: int = 4,
                   max_candidates: int = 2_000_000) -> set[tuple[int, int]]:
    if bands < 1 or rows < 1 or bands * rows != matrix.shape[1]:
        raise ValueError("bands * rows must equal the signature length")
    if max_candidates < 1:
        raise ValueError("max_candidates must be positive")
    pairs: set[tuple[int, int]] = set()
    valid = np.any(matrix != PRIME, axis=1)
    for band in range(bands):
        buckets = defaultdict(list)
        for i in np.flatnonzero(valid):
            key = matrix[i, band * rows:(band + 1) * rows].tobytes()
            buckets[key].append(int(i))
        for bucket in buckets.values():
            for pair in combinations(bucket, 2):
                pairs.add(pair)
                if len(pairs) > max_candidates:
                    raise RuntimeError("Candidate cap exceeded; use a smaller sample or more rows per band. "
                                       "No candidates have been silently discarded.")
    return pairs


def verified_edges(documents: list[frozenset[str]], pairs: Iterable[tuple[int, int]],
                   threshold: float) -> dict[tuple[int, int], float]:
    if not 0 < threshold <= 1:
        raise ValueError("threshold must be in (0, 1]")
    edges = {}
    for i, j in pairs:
        smaller, larger = sorted((len(documents[i]), len(documents[j])))
        if not larger or smaller / larger < threshold:
            continue  # A rigorous upper bound, not an approximation.
        score = jaccard(documents[i], documents[j])
        if score >= threshold:
            edges[(i, j)] = score
    return edges


def retrieval_metrics(truth: set, candidates: set, selected: set, possible: int) -> dict:
    true_positive = len(truth & selected)
    return {
        "possible_pairs": possible, "candidate_pairs": len(candidates),
        "true_pairs": len(truth), "retrieved_true_pairs": true_positive,
        "missed_true_pairs": len(truth - selected),
        "candidate_precision": len(truth & candidates) / len(candidates) if candidates else None,
        "verified_precision": true_positive / len(selected) if selected else None,
        "recall": true_positive / len(truth) if truth else None,
        "candidate_reduction": 1 - len(candidates) / possible if possible else None,
    }

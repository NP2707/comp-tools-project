"""Evaluation and graph/latent-semantic comparisons for the sample study."""
from __future__ import annotations

from itertools import combinations
import random
import time

import networkx as nx
import numpy as np
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize

from .similarity import jaccard, lsh_candidates, retrieval_metrics, signatures, verified_edges


def evaluate_retrieval(documents, *, size=600, seed=42,
                       thresholds=(0.6, 0.7, 0.8, 0.9)):
    """Independently sample documents, then exhaustively enumerate their pairs.

    Ground truth is defined by exact lexical Jaccard, not human judgments. Never
    draw evaluation pairs from the LSH candidates: doing so would hide misses.
    """
    indices = sorted(random.Random(seed + 1).sample(range(len(documents)), min(size, len(documents))))
    sample = [documents[i] for i in indices]
    start = time.perf_counter()
    truth_scores = verified_edges(sample, combinations(range(len(sample)), 2), min(thresholds))
    exact_seconds = time.perf_counter() - start
    start = time.perf_counter()
    matrix = signatures(sample, 128, seed)
    signature_seconds = time.perf_counter() - start
    rows = []
    for bands, band_rows in [(16, 8), (32, 4), (64, 2)]:
        start = time.perf_counter()
        candidates = lsh_candidates(matrix, bands, band_rows)
        candidate_seconds = time.perf_counter() - start
        start = time.perf_counter()
        verified = verified_edges(sample, sorted(candidates), min(thresholds))
        verify_seconds = time.perf_counter() - start
        for threshold in thresholds:
            truth = {pair for pair, score in truth_scores.items() if score >= threshold}
            selected = {pair for pair, score in verified.items() if score >= threshold}
            rows.append({"documents": len(sample), "bands": bands, "rows": band_rows,
                         "threshold": threshold,
                         **retrieval_metrics(truth, candidates, selected,
                                             len(sample) * (len(sample) - 1) // 2),
                         "exact_seconds_at_min_threshold": exact_seconds,
                         "signature_seconds": signature_seconds,
                         "candidate_seconds": candidate_seconds, "verify_seconds": verify_seconds,
                         "lsh_seconds_at_min_threshold": signature_seconds + candidate_seconds + verify_seconds})
    return rows, indices


def cluster_graph(count, edges, *, resolution=1.0, seed=42):
    """Include isolates, avoid self-loops, and canonicalize community IDs."""
    graph = nx.Graph()
    graph.add_nodes_from(range(count))
    graph.add_weighted_edges_from((i, j, score) for (i, j), score in sorted(edges.items()) if i != j)
    if graph.number_of_edges():
        groups = nx.community.louvain_communities(graph, weight="weight", resolution=resolution, seed=seed)
        modularity = nx.community.modularity(graph, groups, weight="weight", resolution=resolution)
    else:
        groups = [{i} for i in range(count)]
        modularity = None
    groups = sorted((sorted(group) for group in groups), key=lambda group: (-len(group), group[0]))
    stats = {"nodes": count, "edges": graph.number_of_edges(),
             "isolates": nx.number_of_isolates(graph), "communities": len(groups),
             "nontrivial_communities": sum(len(group) > 1 for group in groups),
             "largest_community": max(map(len, groups), default=0),
             "connected_components": nx.number_connected_components(graph), "modularity": modularity}
    return graph, groups, stats


def semantic_pairs(skills, *, components=64, neighbors=5, threshold=0.8, seed=42):
    """TF-IDF -> truncated SVD (LSA) -> normalized cosine nearest neighbours.

    Fit on this corpus for descriptive exploration. This is not a held-out
    prediction experiment or evidence that similar documents are copied.
    """
    if len(skills) < 3:
        return {}, {"status": "skipped: fewer than three documents"}
    vectorizer = TfidfVectorizer(tokenizer=str.split, token_pattern=None, lowercase=False,
                                min_df=2, max_features=30_000, sublinear_tf=True, dtype=np.float32)
    try:
        matrix = vectorizer.fit_transform(" ".join(skill.tokens) for skill in skills)
    except ValueError as error:
        return {}, {"status": f"skipped: {error}"}
    rank = min(components, matrix.shape[0] - 1, matrix.shape[1] - 1)
    if rank < 1:
        return {}, {"status": "skipped: insufficient vocabulary"}
    svd = TruncatedSVD(n_components=rank, n_iter=7, random_state=seed)
    embedded = normalize(svd.fit_transform(matrix))
    k = min(neighbors, len(skills) - 1)
    pairs = {}
    for start in range(0, len(skills), 256):
        scores = embedded[start:start + 256] @ embedded.T
        for offset, row in enumerate(scores):
            i = start + offset
            row[i] = -np.inf
            nearest = np.argpartition(-row, k - 1)[:k]
            for j in sorted(nearest, key=lambda j: (-float(row[j]), int(j))):
                score = float(np.clip(row[j], -1, 1))
                if score >= threshold:
                    pair = tuple(sorted((i, int(j))))
                    pairs[pair] = score
    return pairs, {"status": "complete", "features": matrix.shape[1], "components": rank,
                   "explained_variance_ratio": float(svd.explained_variance_ratio_.sum()),
                   "neighbors": k, "cosine_threshold": threshold, "pairs": len(pairs)}


def review_sample(skills, documents, lexical, semantic, *, per_group=12, seed=42):
    """Stratified review candidates; blank labels must be filled by people."""
    lexical_set, semantic_set = set(lexical), set(semantic)
    strata = {"both": lexical_set & semantic_set,
              "lexical_only": lexical_set - semantic_set,
              "lsa_only": semantic_set - lexical_set}
    rng, rows = random.Random(seed + 2), []
    for stratum, pairs in strata.items():
        for i, j in rng.sample(sorted(pairs), min(per_group, len(pairs))):
            rows.append({"stratum": stratum, "stratum_size": len(pairs),
                         "left_sha": skills[i].sha, "right_sha": skills[j].sha,
                         "left_name": skills[i].name, "right_name": skills[j].name,
                         "jaccard": jaccard(documents[i], documents[j]),
                         "lsa_cosine": semantic.get((i, j)),
                         "reviewer_1_label": "", "reviewer_2_label": "", "notes": ""})
    return rows

"""Explore declared skill purposes with weighted text views and K-means.

Run: python -m gitskills.purpose --output results/purpose
No external model/API is used. Labels are added separately after inspecting evidence.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import time
import unicodedata

import numpy as np
from scipy import sparse
from scipy.optimize import linear_sum_assignment
from sklearn.cluster import KMeans
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer
from sklearn.metrics import adjusted_rand_score, davies_bouldin_score, silhouette_score
from sklearn.metrics.cluster import contingency_matrix
from sklearn.preprocessing import normalize
from threadpoolctl import threadpool_limits

from .corpus import load_corpus
from .__main__ import sha256, write_csv

ROOT = Path(__file__).resolve().parents[1]
GENERIC_WORDS = set("""skill skills use used using user users task tasks trigger triggers triggered
when should must need needs needed helps help related appropriate instructions instruction
workflow workflows context specific general guide guidance best practices including based
provides provide supports support automatically automatic description name
und der die das den dem des ein eine einer einen einem eines ist sind wird werden mit für
von zu zur zum auf im in bei als auch oder wenn wie sich nicht nur aus nach durch über vor
""".split())
STOP_WORDS = sorted(set(ENGLISH_STOP_WORDS) | GENERIC_WORDS)


def purpose_tokens(text):
    """Split identifiers, discard opaque numeric IDs, and preserve Unicode words."""
    text = unicodedata.normalize("NFKC", text).casefold()
    text = re.sub(r"\bu\d+\b", " ", text)
    return re.findall(r"[^\W\d_][^\W_]+", text)


def feature_views(skills, descriptions):
    metadata = [s.name.replace("-", " ").replace("_", " ") + " " + descriptions[s.sha] for s in skills]
    body = [" ".join(s.tokens).replace("_", " ") for s in skills]
    vectorizers, matrices = [], []
    for texts, ngrams, maximum, cutoff in ((metadata, (1, 2), 40_000, 0.7), (body, (1, 1), 30_000, 0.4)):
        vectorizer = TfidfVectorizer(tokenizer=purpose_tokens, token_pattern=None, lowercase=False,
                                    stop_words=STOP_WORDS, ngram_range=ngrams, min_df=3,
                                    max_df=cutoff, max_features=maximum, sublinear_tf=True, dtype=np.float32)
        matrices.append(vectorizer.fit_transform(texts))
        vectorizers.append(vectorizer)
    return metadata, matrices, vectorizers


def combine_views(metadata, body, metadata_weight):
    if not 0 <= metadata_weight <= 1:
        raise ValueError("metadata_weight must be in [0, 1]")
    # Each TF-IDF row has unit norm: squared weights control contributions to
    # cosine similarity before dimensionality reduction.
    return sparse.hstack([metadata * np.sqrt(metadata_weight), body * np.sqrt(1 - metadata_weight)], format="csr")


def embedding(matrix, seed, dimensions=128):
    rank = min(dimensions, matrix.shape[0] - 1, matrix.shape[1] - 1)
    if rank < 2:
        raise ValueError("Too little data for a purpose embedding")
    model = TruncatedSVD(n_components=rank, n_iter=7, random_state=seed)
    return normalize(model.fit_transform(matrix)), float(model.explained_variance_ratio_.sum())


def fit_clusters(vectors, count, seed):
    return KMeans(n_clusters=count, n_init=10, max_iter=300, random_state=seed).fit(vectors)


def aligned_labels(reference, alternate):
    """Maximum-overlap label alignment for partition comparison, not validation."""
    overlap = contingency_matrix(reference, alternate)
    rows, columns = linear_sum_assignment(-overlap)
    ref_ids, alt_ids = np.unique(reference), np.unique(alternate)
    mapping = {int(alt_ids[c]): int(ref_ids[r]) for r, c in zip(rows, columns)}
    return np.array([mapping[int(value)] for value in alternate])


def cluster_terms(matrix, vectorizer, labels, cluster, count=12):
    overall = np.asarray(matrix.mean(axis=0)).ravel()
    mean = np.asarray(matrix[labels == cluster].mean(axis=0)).ravel()
    # Contrastive TF-IDF means emphasize terms enriched in this cluster.
    scores = mean - overall
    vocabulary = vectorizer.get_feature_names_out()
    order = np.argsort(-scores, kind="stable")
    return [str(vocabulary[i]) for i in order[:count] if scores[i] > 0]


def assignment_margins(distances):
    nearest = np.partition(distances, 1, axis=1)[:, :2]
    nearest.sort(axis=1)
    return (nearest[:, 1] - nearest[:, 0]) / np.maximum(nearest[:, 1], 1e-12)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=ROOT / "data/raw/agent_skills_sample.db")
    parser.add_argument("--output", type=Path, default=ROOT / "results/purpose")
    parser.add_argument("--clusters", type=int, default=24)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--metadata-weight", type=float, default=0.85)
    args = parser.parse_args(argv)
    if args.clusters < 2 or not 0 <= args.metadata_weight <= 1:
        parser.error("clusters >= 2 and metadata-weight in [0,1] are required")
    if args.output.exists() and any(args.output.iterdir()):
        parser.error("Choose a new or empty output directory")
    args.output.mkdir(parents=True, exist_ok=True)
    start = time.perf_counter()
    print("Loading verified contents and declared descriptions...", flush=True)
    skills, corpus = load_corpus(args.database)
    if args.clusters >= len(skills):
        raise ValueError("Fewer clusters than documents are required")
    with sqlite3.connect(args.database.resolve().as_uri() + "?mode=ro", uri=True) as connection:
        descriptions = dict(connection.execute("SELECT file_sha,description FROM artifacts WHERE dedup_primary=1"))
    texts, matrices, vectorizers = feature_views(skills, descriptions)
    print("Building weighted LSA representation...", flush=True)
    vectors, explained = embedding(combine_views(*matrices, args.metadata_weight), args.seed)
    model = fit_clusters(vectors, args.clusters, args.seed)
    # Canonical IDs put the largest group first; no purpose names are assumed.
    sizes = Counter(map(int, model.labels_))
    ordering = sorted(sizes, key=lambda cluster: (-sizes[cluster], cluster))
    rename = {cluster: i for i, cluster in enumerate(ordering)}
    labels = np.array([rename[int(value)] for value in model.labels_])
    centers = model.cluster_centers_[ordering]
    distances = model.transform(vectors)[:, ordering]
    margins = assignment_margins(distances)
    center_cosine = np.sum(vectors * normalize(centers)[labels], axis=1)
    print("Comparing cluster counts, seeds, and text views...", flush=True)
    metrics = []
    candidate_counts = sorted({k for k in [12, 24, 36, 48, args.clusters] if k < len(skills)})
    for count in candidate_counts:
        candidate = model if count == args.clusters else fit_clusters(vectors, count, args.seed)
        metrics.append({"clusters": count, "silhouette_cosine": float(silhouette_score(
            vectors, candidate.labels_, metric="cosine", sample_size=min(1500, len(skills)), random_state=args.seed)),
            "davies_bouldin": float(davies_bouldin_score(vectors, candidate.labels_)),
            "smallest_cluster": int(np.bincount(candidate.labels_).min()),
            "largest_cluster": int(np.bincount(candidate.labels_).max()), "inertia": float(candidate.inertia_)})
    stability = [{"seed": seed, "adjusted_rand_vs_main": float(adjusted_rand_score(
        labels, fit_clusters(vectors, args.clusters, seed).labels_))} for seed in (args.seed + 1, args.seed + 2)]
    ablations, alternates = [], {}
    for name, weight in (("metadata_only", 1.0), ("body_only", 0.0)):
        alternate_vectors, _ = embedding(combine_views(*matrices, weight), args.seed)
        alternate = fit_clusters(alternate_vectors, args.clusters, args.seed).labels_
        aligned = aligned_labels(labels, alternate)
        alternates[name] = aligned
        ablations.append({"view": name, "adjusted_rand_vs_main": float(adjusted_rand_score(labels, alternate)),
                          "aligned_assignment_agreement": float(np.mean(labels == aligned))})
    print("Extracting purpose evidence and reuse-family cross-tabs...", flush=True)
    rng = np.random.default_rng(args.seed)
    evidence, cluster_rows = [], []
    for cluster in range(args.clusters):
        members = np.flatnonzero(labels == cluster)
        ordered = members[np.argsort(distances[members, cluster], kind="stable")]
        representative = ordered[:5].tolist()
        remaining = [int(i) for i in members if i not in representative]
        sampled = rng.choice(remaining, size=min(5, len(remaining)), replace=False).tolist()
        boundary = [int(members[np.argmin(margins[members])])]
        evidence.append({"cluster": cluster, "contents": len(members),
            "metadata_terms": cluster_terms(matrices[0], vectorizers[0], labels, cluster),
            "body_terms": cluster_terms(matrices[1], vectorizers[1], labels, cluster),
            "examples": [{"selection": selection, "sha": skills[i].sha, "name": skills[i].name,
                          "description": descriptions[skills[i].sha], "assignment_margin": float(margins[i])}
                         for selection, indices in (("representative", representative), ("random", sampled), ("boundary", boundary))
                         for i in indices]})
        cluster_rows.append({"cluster": cluster, "contents": len(members),
                             "occurrences": sum(skills[i].copies for i in members),
                             "mean_centroid_cosine": float(center_cosine[members].mean()),
                             "low_margin_fraction": float(np.mean(margins[members] < 0.05)),
                             "top_terms": " | ".join(evidence[-1]["metadata_terms"])})
    assignments = [{"sha": skill.sha, "name": skill.name, "description": descriptions[skill.sha],
                    "cluster": int(labels[i]), "occurrences": skill.copies,
                    "centroid_cosine": float(center_cosine[i]), "assignment_margin": float(margins[i]),
                    "ambiguous_margin": bool(margins[i] < 0.05),
                    "metadata_only_aligned_cluster": int(alternates["metadata_only"][i]),
                    "body_only_aligned_cluster": int(alternates["body_only"][i])}
                   for i, skill in enumerate(skills)]
    write_csv(args.output / "assignments.csv", assignments, list(assignments[0]))
    write_csv(args.output / "clusters.csv", cluster_rows, list(cluster_rows[0]))
    write_csv(args.output / "cluster_count_comparison.csv", metrics, list(metrics[0]))
    write_csv(args.output / "seed_stability.csv", stability, list(stability[0]))
    write_csv(args.output / "view_comparison.csv", ablations, list(ablations[0]))
    (args.output / "cluster_evidence.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n")
    # Intersect with the independently constructed exact-Jaccard graph.
    import csv
    reuse_path = ROOT / "results/sample-4000/nodes.csv"
    reuse_rows = []
    family_stats = {"status": "similarity results unavailable"}
    if reuse_path.exists():
        content_labels = {skill.sha: int(labels[i]) for i, skill in enumerate(skills)}
        families = {}
        for row in csv.DictReader(reuse_path.open()):
            if row["sha"] in content_labels:
                families.setdefault(row["community"], []).append(row["sha"])
        for family, hashes in sorted(families.items(), key=lambda item: int(item[0])):
            if len(hashes) < 2:
                continue
            counts = Counter(content_labels[sha] for sha in hashes)
            probabilities = np.array(list(counts.values())) / len(hashes)
            reuse_rows.append({"reuse_family": family, "contents": len(hashes),
                               "purpose_clusters": len(counts), "dominant_purpose_share": float(max(probabilities)),
                               "purpose_entropy_bits": float(-np.sum(probabilities * np.log2(probabilities))),
                               "purpose_counts": json.dumps(dict(sorted(counts.items())))})
        if reuse_rows:
            write_csv(args.output / "reuse_family_purposes.csv", reuse_rows, list(reuse_rows[0]))
        pairs = list(csv.DictReader((reuse_path.parent / "edges.csv").open()))
        selected_pairs = [row for row in pairs if row["left_sha"] in content_labels and row["right_sha"] in content_labels]
        family_stats = {"families": len(reuse_rows),
                        "families_spanning_purposes": sum(row["purpose_clusters"] > 1 for row in reuse_rows),
                        "similarity_pairs": len(selected_pairs),
                        "similarity_pairs_crossing_purposes": sum(content_labels[row["left_sha"]] != content_labels[row["right_sha"]] for row in selected_pairs)}
    summary = {"created_utc": datetime.now(timezone.utc).isoformat(),
               "config": {k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()},
               "corpus": corpus, "features": [matrix.shape[1] for matrix in matrices],
               "svd_explained_variance_ratio": explained,
               "zero_feature_documents": int(np.sum(np.asarray(combine_views(*matrices, args.metadata_weight).getnnz(axis=1)) == 0)),
               "low_margin_fraction": float(np.mean(margins < 0.05)), "reuse_comparison": family_stats,
               "database_sha256": sha256(args.database),
               "source_sha256": {f"gitskills/{name}": sha256(ROOT / "gitskills" / name) for name in ("purpose.py", "corpus.py", "__main__.py")},
               "runtime_seconds": time.perf_counter() - start,
               "label_status": "Automatic terms and evidence only; interpretive names added separately.",
               "limitations": ["24 is an inspection granularity, not a discovered number of true purposes.",
                               "Centroid scores and margins are geometric diagnostics, not calibrated probabilities.",
                               "Language, toolkit names and templates can dominate lexical topics.",
                               "A single label per skill cannot capture all purposes; no gold labels are available.",
                               "Partition alignment is for comparison and does not validate individual assignments."]}
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"contents": len(skills), "clusters": args.clusters, "runtime_seconds": summary["runtime_seconds"],
                      "low_margin_fraction": summary["low_margin_fraction"], "reuse_comparison": family_stats}, indent=2))


if __name__ == "__main__":
    with threadpool_limits(limits=2):
        main()

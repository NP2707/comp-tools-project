"""Run with: python -m gitskills --output results/sample"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import platform
import resource
import sys
import time

from threadpoolctl import threadpool_limits

from .corpus import load_corpus
from .experiments import cluster_graph, evaluate_retrieval, review_sample, semantic_pairs
from .similarity import lsh_candidates, shingles, signatures, verified_edges

ROOT = Path(__file__).resolve().parents[1]


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_csv(path, rows, fields):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def plot_results(output, evaluation, groups, edges):
    os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".cache" / "matplotlib"))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 3, figsize=(13, 3.8), constrained_layout=True)
    for bands in (16, 32, 64):
        values = [row for row in evaluation if row["bands"] == bands and row["recall"] is not None]
        axes[0].plot([r["threshold"] for r in values], [r["recall"] for r in values],
                     marker="o", label=f"{bands} bands × {128 // bands} rows")
    axes[0].set(xlabel="Exact Jaccard threshold", ylabel="Recall on exhaustive subset", ylim=(0, 1.05))
    axes[0].legend(fontsize=8)
    sizes = sorted((len(g) for g in groups if len(g) > 1), reverse=True)
    axes[1].plot(range(1, len(sizes) + 1), sizes, marker=".", linewidth=1)
    axes[1].set(xlabel="Community rank (isolates omitted)", ylabel="Distinct contents", yscale="log")
    axes[2].hist(list(edges.values()), bins=20, color="#277a87")
    axes[2].set(xlabel="Verified edge Jaccard", ylabel="Pairs")
    fig.suptitle("GitSkills sample: retrieval and similarity communities")
    for suffix in ("png", "svg"):
        fig.savefig(output / f"overview.{suffix}", dpi=160)
    plt.close(fig)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=ROOT / "data/raw/agent_skills_sample.db")
    parser.add_argument("--output", type=Path, default=ROOT / "results/sample")
    parser.add_argument("--limit", type=int, default=0, help="0 = all eligible sample contents")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--shingle-size", type=int, default=5)
    parser.add_argument("--min-tokens", type=int, default=30)
    parser.add_argument("--threshold", type=float, default=0.8)
    parser.add_argument("--bands", type=int, default=32)
    parser.add_argument("--rows", type=int, default=4)
    parser.add_argument("--max-candidates", type=int, default=2_000_000)
    parser.add_argument("--eval-size", type=int, default=4000)
    parser.add_argument("--lsa-components", type=int, default=64)
    parser.add_argument("--lsa-neighbors", type=int, default=5)
    parser.add_argument("--lsa-threshold", type=float, default=0.8)
    parser.add_argument("--include-nonstandard", action="store_true",
                        help="Disable filename and frontmatter filters for a sensitivity run")
    parser.add_argument("--keep-frontmatter", action="store_true")
    parser.add_argument("--skip-lsa", action="store_true")
    args = parser.parse_args(argv)
    if (args.limit < 0 or args.shingle_size < 1 or args.min_tokens < args.shingle_size
            or args.eval_size < 2 or args.bands < 1 or args.rows < 1 or args.bands * args.rows != 128
            or not 0 < args.threshold <= 1 or args.max_candidates < 1
            or args.lsa_components < 1 or args.lsa_neighbors < 1 or not 0 < args.lsa_threshold <= 1):
        parser.error("Check positive sizes, thresholds in (0,1], min_tokens >= shingle_size, and bands*rows=128")
    if args.output.exists() and any(args.output.iterdir()):
        parser.error("Output directory is not empty; choose a new directory to preserve previous runs")
    args.output.mkdir(parents=True, exist_ok=True)
    start = time.perf_counter()
    timings = {}

    def stage(name):
        print(name, flush=True)
        return time.perf_counter()

    t = stage("Loading and verifying distinct contents...")
    skills, corpus_stats = load_corpus(args.database, limit=args.limit, seed=args.seed,
                                     min_tokens=args.min_tokens, strict=not args.include_nonstandard,
                                     strip_frontmatter=not args.keep_frontmatter)
    if len(skills) < 3:
        raise ValueError("At least three eligible documents are required")
    documents = [shingles(skill.tokens, args.shingle_size) for skill in skills]
    timings["load_and_shingle"] = time.perf_counter() - t
    t = stage(f"Computing MinHash signatures for {len(skills):,} contents...")
    matrix = signatures(documents, 128, args.seed)
    timings["minhash"] = time.perf_counter() - t
    t = stage("Generating LSH candidates and verifying exact similarities...")
    candidates = lsh_candidates(matrix, args.bands, args.rows, args.max_candidates)
    timings["lsh_candidates"] = time.perf_counter() - t
    t = time.perf_counter()
    thresholds = sorted({0.6, 0.7, 0.8, 0.9, args.threshold})
    scores = verified_edges(documents, sorted(candidates), min(thresholds))
    edges = {pair: score for pair, score in scores.items() if score >= args.threshold}
    timings["exact_verification"] = time.perf_counter() - t
    t = stage("Evaluating retrieval against exhaustive comparisons...")
    evaluation, indices = evaluate_retrieval(documents, size=args.eval_size, seed=args.seed,
                                             thresholds=thresholds)
    timings["evaluation"] = time.perf_counter() - t
    write_csv(args.output / "retrieval.csv", evaluation, list(evaluation[0]))
    (args.output / "evaluation_ids.json").write_text(json.dumps([skills[i].sha for i in indices], indent=2) + "\n")
    t = stage("Clustering the weighted similarity graph...")
    graph, groups, graph_stats = cluster_graph(len(skills), edges, seed=args.seed)
    sensitivity = []
    for threshold in thresholds:
        subset = {pair: score for pair, score in scores.items() if score >= threshold}
        for resolution in (0.5, 1.0, 2.0):
            _, _, stats = cluster_graph(len(skills), subset, resolution=resolution, seed=args.seed)
            sensitivity.append({"threshold": threshold, "resolution": resolution, **stats})
    write_csv(args.output / "graph_sensitivity.csv", sensitivity, list(sensitivity[0]))
    timings["graph"] = time.perf_counter() - t
    membership = {node: community for community, nodes in enumerate(groups) for node in nodes}
    nodes = [{"sha": skill.sha, "name": skill.name, "representative_repo": skill.repo,
              "representative_path": skill.path, "occurrences": skill.copies,
              "repositories": len(skill.repos), "tokens": len(skill.tokens),
              "shingles": len(documents[i]), "community": membership[i], "degree": graph.degree(i)}
             for i, skill in enumerate(skills)]
    write_csv(args.output / "nodes.csv", nodes, list(nodes[0]))
    write_csv(args.output / "edges.csv",
              ({"left_sha": skills[i].sha, "right_sha": skills[j].sha, "jaccard": score}
               for (i, j), score in sorted(edges.items())), ["left_sha", "right_sha", "jaccard"])
    communities = [{"community": i, "distinct_contents": len(group),
                    "occurrences": sum(skills[j].copies for j in group),
                    "repositories": len({repo for j in group for repo in skills[j].repos}),
                    "example_names": " | ".join(skills[j].name for j in group[:5])}
                   for i, group in enumerate(groups)]
    write_csv(args.output / "communities.csv", communities, list(communities[0]))
    t = stage("Comparing latent semantic neighbours...")
    semantic, semantic_stats = ({}, {"status": "disabled"}) if args.skip_lsa else semantic_pairs(
        skills, components=args.lsa_components, neighbors=args.lsa_neighbors,
        threshold=args.lsa_threshold, seed=args.seed)
    semantic_stats["overlap_with_lexical_pairs"] = len(set(semantic) & set(edges))
    semantic_stats["lsa_only_pairs"] = len(set(semantic) - set(edges))
    timings["lsa"] = time.perf_counter() - t
    write_csv(args.output / "lsa_pairs.csv",
              ({"left_sha": skills[i].sha, "right_sha": skills[j].sha, "cosine": score}
               for (i, j), score in sorted(semantic.items())), ["left_sha", "right_sha", "cosine"])
    review = review_sample(skills, documents, edges, semantic, seed=args.seed)
    review_fields = ["stratum", "stratum_size", "left_sha", "right_sha", "left_name", "right_name",
                     "jaccard", "lsa_cosine", "reviewer_1_label", "reviewer_2_label", "notes"]
    write_csv(args.output / "review.csv", review, review_fields)
    t = stage("Saving figures and provenance...")
    plot_results(args.output, evaluation, groups, edges)
    timings["plots"] = time.perf_counter() - t
    timings["total"] = time.perf_counter() - start
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "config": {key: str(value) if isinstance(value, Path) else value for key, value in vars(args).items()},
        "database_sha256": sha256(args.database),
        "source_sha256": {str(p.relative_to(ROOT)): sha256(p) for p in sorted((ROOT / "gitskills").glob("*.py"))},
        "python": sys.version, "platform": platform.platform(),
        "packages": {name: version(name) for name in ("numpy", "scipy", "networkx", "scikit-learn", "matplotlib")},
        "corpus": corpus_stats, "candidates": len(candidates),
        "possible_pairs": len(skills) * (len(skills) - 1) // 2,
        "exact_duplicate_occurrences": sum(s.copies - 1 for s in skills),
        "graph": graph_stats, "lsa": semantic_stats, "timings_seconds": timings,
        "peak_process_rss_mib": peak / (1024**2 if sys.platform == "darwin" else 1024),
        "limitations": ["Descriptive sample results; no population-level reuse or causal claims.",
                        "Graph edges certify lexical similarity, not copying or common purpose.",
                        "LSH can miss pairs; recall is measured on an independent document subset.",
                        "Exact Jaccard precision is definitional; human review remains unfilled.",
                        "LSA uses the full selected corpus for exploratory fitting; no held-out quality claim.",
                        "Peak RSS includes evaluation, graph sweeps, LSA and plotting; timings are one run."],
    }
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n")
    default_eval = next(r for r in evaluation if r["bands"] == args.bands and r["rows"] == args.rows
                        and r["threshold"] == args.threshold) if (args.bands, args.rows) in {(16, 8), (32, 4), (64, 2)} else None
    recall = f"{default_eval['recall']:.1%}" if default_eval and default_eval["recall"] is not None else "undefined"
    support = (f" ({default_eval['retrieved_true_pairs']} of {default_eval['true_pairs']} qualifying pairs retrieved)"
               if default_eval else "")
    note = (f"Prototype run: {len(skills):,} eligible distinct contents, representing "
            f"{sum(s.copies for s in skills):,} file occurrences.\n\n"
            f"LSH proposed {len(candidates):,} pairs out of {summary['possible_pairs']:,}; "
            f"{len(edges):,} passed exact {args.shingle_size}-word-shingle Jaccard >= {args.threshold}. "
            f"The graph contains {graph_stats['nontrivial_communities']:,} communities of at least two contents "
            f"and {graph_stats['isolates']:,} isolated contents.\n\n"
            f"Retrieval recall on {len(indices)} independently sampled documents: {recall}{support}. "
            "See retrieval.csv for true-pair counts, other thresholds, precision, and timing. "
            "A zero-positive evaluation produces undefined recall, never a claimed perfect score.\n\n"
            f"Total runtime: {timings['total']:.1f} seconds; peak process RSS: {summary['peak_process_rss_mib']:.0f} MiB. "
            "These measurements include evaluation and comparisons.\n\n"
            "The LSA comparison and blank, stratified review.csv support follow-up human inspection. "
            "Neither similarity nor modularity proves copying or semantic correctness. "
            "Community membership is not pairwise similarity: connected chains can join dissimilar endpoints.\n")
    (args.output / "RESULTS.md").write_text(note)
    print(note)


if __name__ == "__main__":
    with threadpool_limits(limits=2):
        main()

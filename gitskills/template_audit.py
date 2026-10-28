"""Audit instruction-template reuse independently of inferred purpose labels.

Static text evidence only: no skill or bundled script is executed.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import csv
import difflib
import hashlib
import json
from pathlib import Path
import random
import re
import sqlite3
import unicodedata

from .__main__ import sha256, write_csv
from .corpus import body_tokens
from .similarity import jaccard, shingles

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "results/template-audit"


def instruction_body(text: str, remove_title: bool = False) -> str:
    text = re.sub(r"\A---[^\S\r\n]*\r?\n.*?\r?\n(?:---|\.\.\.)[^\S\r\n]*(?:\r?\n|\Z)",
                  "", text.lstrip("\ufeff"), count=1, flags=re.DOTALL)
    if remove_title:
        text = re.sub(r"^#\s+[^\n]*(?:\n|$)", "", text, count=1, flags=re.MULTILINE)
    return text.strip()


def normalize(text):
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())


def main():
    if OUTPUT.exists() and any(OUTPUT.iterdir()):
        raise ValueError("Preserve the prior audit; choose a fresh output path in the script before rerunning")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    database = ROOT / "data/raw/agent_skills_sample.db"
    with sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True) as connection:
        records = {sha: {"sha": sha, "name": name, "description": description, "text": content,
                         "representative_repo": repo, "representative_path": path}
                   for sha, name, description, content, repo, path in connection.execute(
                       "SELECT file_sha,name,description,content,repo_full_name,path FROM artifacts WHERE dedup_primary=1")}
    def csv_rows(relative):
        with (ROOT / relative).open(encoding="utf-8", newline="") as stream:
            return list(csv.DictReader(stream))
    nodes = {r["sha"]: r for r in csv_rows("results/sample-4000/nodes.csv")}
    purposes = {r["sha"]: r for r in csv_rows("results/purpose/assignments_labeled.csv")}
    edges = csv_rows("results/sample-4000/edges.csv")
    bodies, sets, title_free_hashes = {}, {}, {}
    for sha in nodes:
        record = records[sha]
        raw = record["text"].encode()
        if hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest() != sha:
            raise ValueError(f"Content integrity failure: {sha}")
        bodies[sha] = instruction_body(record["text"])
        sets[sha] = shingles(body_tokens(record["text"]))
        title_free_hashes[sha] = hashlib.sha256(normalize(instruction_body(record["text"], True)).encode()).hexdigest()
    pair_rows, families = [], defaultdict(list)
    for edge in edges:
        left, right = edge["left_sha"], edge["right_sha"]
        family = nodes[left]["community"]
        assert family == nodes[right]["community"]
        actual = jaccard(sets[left], sets[right])
        assert abs(actual - float(edge["jaccard"])) < 1e-12
        row = {"left_sha": left, "right_sha": right, "family": int(family),
               "left_name": records[left]["name"], "right_name": records[right]["name"],
               "jaccard": actual, "cross_purpose_cluster": purposes[left]["cluster"] != purposes[right]["cluster"],
               "same_name": normalize(records[left]["name"]) == normalize(records[right]["name"]),
               "same_description": normalize(records[left]["description"]) == normalize(records[right]["description"]),
               "same_title_free_body": title_free_hashes[left] == title_free_hashes[right],
               "left_cluster": int(purposes[left]["cluster"]), "right_cluster": int(purposes[right]["cluster"])}
        pair_rows.append(row)
        families[family].append(row)
    write_csv(OUTPUT / "pair_diagnostics.csv", pair_rows, list(pair_rows[0]))
    family_rows = []
    for family, pairs in families.items():
        members = sorted({sha for pair in pairs for sha in (pair["left_sha"], pair["right_sha"])})
        family_rows.append({"family": int(family), "contents": len(members), "edges": len(pairs),
                            "cross_cluster_edges": sum(p["cross_purpose_cluster"] for p in pairs),
                            "identical_title_free_edges": sum(p["same_title_free_body"] for p in pairs),
                            "distinct_title_free_bodies": len({title_free_hashes[s] for s in members}),
                            "distinct_names": len({normalize(records[s]["name"]) for s in members}),
                            "distinct_descriptions": len({normalize(records[s]["description"]) for s in members}),
                            "names": " | ".join(records[s]["name"] for s in members)})
    family_rows.sort(key=lambda row: (-row["cross_cluster_edges"], -row["edges"], row["family"]))
    write_csv(OUTPUT / "family_diagnostics.csv", family_rows, list(family_rows[0]))
    cross = [row["family"] for row in family_rows if row["cross_cluster_edges"]]
    within = sorted(row["family"] for row in family_rows if not row["cross_cluster_edges"])
    random_within = random.Random(20261028).sample(within, 20)
    large_within = [row["family"] for row in sorted(family_rows, key=lambda row: -row["contents"])
                    if not row["cross_cluster_edges"]][:3]
    selected = sorted(set(cross + random_within + large_within))
    packets = []
    for family in selected:
        pairs = families[str(family)]
        ids = sorted({sha for pair in pairs for sha in (pair["left_sha"], pair["right_sha"])})
        selected_pair = sorted(pairs, key=lambda p: (-int(p["cross_purpose_cluster"]), -p["jaccard"], p["left_sha"], p["right_sha"]))[0]
        left, right = selected_pair["left_sha"], selected_pair["right_sha"]
        diff = "\n".join(difflib.unified_diff(bodies[left].splitlines(), bodies[right].splitlines(),
                                           fromfile=records[left]["name"], tofile=records[right]["name"], n=2))
        packets.append({"family": family, "selection": "all_cross_cluster_families" if family in cross else
                        "random_within_cluster_control" if family in random_within else "large_within_cluster_control",
                        "members": [{"sha": sha, "name": records[sha]["name"], "description": records[sha]["description"],
                                     "body_chars": len(bodies[sha]), "title_free_body_sha256": title_free_hashes[sha],
                                     "cluster": int(purposes[sha]["cluster"])} for sha in ids],
                        "pair": selected_pair, "left_body": bodies[left], "right_body": bodies[right], "body_diff": diff})
    (OUTPUT / "evidence_packets.json").write_text(json.dumps(packets, ensure_ascii=False, indent=2) + "\n")
    review = [{"family": item["family"], "selection": item["selection"],
               "left_sha": item["pair"]["left_sha"], "right_sha": item["pair"]["right_sha"],
               "procedure_type": "", "declared_task_relationship": "", "evidence_notes": "",
               "reviewer": ""} for item in packets]
    write_csv(OUTPUT / "human_review.csv", review, list(review[0]))
    top = family_rows[0]
    cross_total = sum(row["cross_cluster_edges"] for row in family_rows)
    summary = {"pair_count": len(pair_rows), "family_count": len(family_rows),
               "cross_cluster_pairs": cross_total, "cross_cluster_families": len(cross),
               "dominant_family": top,
               "dominant_share_of_cross_cluster_pairs": top["cross_cluster_edges"] / cross_total,
               "excluding_dominant": {"pairs": len(pair_rows) - top["edges"],
                                      "cross_cluster_pairs": cross_total - top["cross_cluster_edges"]},
               "same_name_cross_cluster_pairs": sum(p["cross_purpose_cluster"] and p["same_name"] for p in pair_rows),
               "same_description_cross_cluster_pairs": sum(p["cross_purpose_cluster"] and p["same_description"] for p in pair_rows),
               "identical_title_free_body_pairs": sum(p["same_title_free_body"] for p in pair_rows),
               "review_families": len(packets), "random_control_families": random_within,
               "database_sha256": sha256(database),
               "source_sha256": {"gitskills/template_audit.py": sha256(Path(__file__))},
               "input_sha256": {path: sha256(ROOT / path) for path in ["results/sample-4000/nodes.csv",
                                  "results/sample-4000/edges.csv", "results/purpose/assignments_labeled.csv"]},
               "scope": "Static declared-purpose and instruction-content audit; no runtime functionality evaluated.",
               "normalization": "Remove leading YAML and first Markdown H1, then Unicode NFKC, casefold and whitespace collapse. Remaining instructions are preserved.",
               "review_status": "Evidence sampled; human reviewer fields intentionally blank."}
    (OUTPUT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

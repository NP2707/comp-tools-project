"""Render the reproducible diagnostics and separate assistant assessments."""
from collections import Counter
import csv
import hashlib
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results/template-audit"


def read_csv(name):
    with (RESULTS / name).open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def main():
    summary = json.loads((RESULTS / "summary.json").read_text())
    assessment = json.loads((RESULTS / "assistant_review.json").read_text())
    for name, expected in {**summary["source_sha256"], **summary["input_sha256"]}.items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected, name
    pairs = {(p["left_sha"], p["right_sha"]): p for p in read_csv("pair_diagnostics.csv")}
    selection = {int(p["family"]): p for p in read_csv("human_review.csv")}
    reviews = assessment["reviews"]
    assert len(reviews) == len(selection) == summary["review_families"]
    assert {r["family"] for r in reviews} == set(selection)
    cross = []
    for row in reviews:
        selected = selection[row["family"]]
        pair = pairs[selected["left_sha"], selected["right_sha"]]
        row.update(selection=selected["selection"], pair=pair)
        if pair["cross_purpose_cluster"] == "True":
            cross.append(row)
    same_cross = [r for r in cross if r["task_relationship"] == "same_core_task"]
    top = summary["dominant_family"]
    remaining = summary["excluding_dominant"]
    metrics = [
        ("All verified lexical pairs", summary["cross_cluster_pairs"], summary["pair_count"]),
        ("Largest family only", top["cross_cluster_edges"], top["edges"]),
        ("Pairs excluding largest family", remaining["cross_cluster_pairs"], remaining["pairs"]),
        ("Families spanning purpose clusters", summary["cross_cluster_families"], summary["family_count"]),
    ]
    metric_lines = [f"| {label} | {n}/{total} | {n/total:.1%} |" for label, n, total in metrics]
    findings = f"""# Do shared templates imply shared functionality?

The sample confirms shared generic instructions across different **declared tasks**. It also contains shared substantive guidance for the same task. Lexical similarity alone does not distinguish these cases, and the purpose clusters are too unstable to serve as ground truth. No runtime functionality was evaluated.

## The earlier pair count is dominated by one family

| Diagnostic | Count | Fraction |
| --- | ---: | ---: |
{chr(10).join(metric_lines)}

Family {top['family']} contains {top['contents']} distinct contents and all {top['edges']} possible pairs. Its {top['cross_cluster_edges']} crossing pairs account for **{summary['dominant_share_of_cross_cluster_pairs']:.1%} of the {summary['cross_cluster_pairs']} crossing pairs**. Pairs sharing the same documents are not independent observations. Removing this family is an influence diagnostic, not a corrected population estimate. The family-level 14/140 count also describes cluster disagreement, not proven task differences.

All 25 family members have exactly the same normalized instruction body after removing leading YAML metadata and the first Markdown H1. Names and descriptions vary across 25 distinct values. Examples include **DNS architecture, dairy operations, virtual classroom design and startup board management**. Their common text asks for requirements, research, a draft, review, an action plan and metrics; it supplies no procedures specific to those domains. This is direct text-level evidence of generic template reuse, regardless of cluster assignments.

Across all 649 pairs, 355 have identical normalized title-free bodies. This number includes substantive same-task instructions and must not be interpreted as a count of generic boilerplate.

## Static review changes the interpretation

The assistant inspected one selected pair from each of 36 families: all 14 families spanning clusters, 20 randomly sampled within-cluster controls (seed 20261028), and the three largest within-cluster families. One large family overlaps the random controls, leaving 22 distinct controls. Pair selection prioritizes crossing pairs, then highest Jaccard similarity, so this is a targeted qualitative review, not a random pair survey.

Selected pairs in **{len(same_cross)} of the {len(cross)} crossing families** describe the same core task: spreadsheet work, documentation lookup, social posting, extracting reusable lessons, Azure messaging, accounting entries and GitHub issue management. Differences include language, metadata, runtime configuration and optional integration steps. These are likely false splits at the core-task level; this assessment does not establish execution equivalence or label every pair in those families.

Controls expose the reverse problem: Redis and Unleash share an integration mechanism but target different services (family 1). Civic-plan evaluation and accessibility-journal maintenance share a generic production scaffold despite being placed in the same broad purpose group (family 2). Same-cluster membership is also insufficient evidence of the same task.

Other cases include unfilled Arabic placeholders (family 13), different declared file-processing tasks with an unspecified transformation (family 67), and wrappers pointing to different external procedures (family 132). Referenced scripts and documents can contain functionality absent from the entrypoint; those dependencies were not reviewed here.

Assessments are saved separately in `assistant_review.json`, explicitly marked **not human validated**. `human_review.csv` remains available for independent annotation. No skill commands, scripts or instructions from the dataset were executed.

## Reproduce and inspect

The data remains the pinned **GitHub sample**, not the full Zenodo corpus. Existing filters retain 11,015 distinct contents; 362 participate in the 140 nontrivial lexical families. The audit rechecks Git blob hashes for selected contents and recomputes exact five-word-shingle Jaccard for all 649 edges. Its script and inputs are hashed in `summary.json`.

Normalization removes YAML and the first Markdown H1 using regular expressions, then applies Unicode NFKC, case folding and whitespace collapse. This is a text heuristic, not a complete Markdown parser. It does not remove later headings, commands or procedural details. Identical normalized text is not a behavioral guarantee.

```bash
.venv/bin/python scripts/download_sample.py
.venv/bin/python scripts/run_template_audit.py --output results/audit-reproduction
.venv/bin/python scripts/build_template_report.py
```

The first analysis command requires a new or empty output folder and recreates diagnostics, raw evidence packets and blank reviewer fields. The renderer uses the saved `results/template-audit` diagnostics and assistant assessments. It does not generate new judgments. Full raw evidence packets stay local and are omitted from the portable bundle; regenerate them from the pinned database. Pair and family IDs are retained in the exported tables for traceability.

## Research direction supported by this check

Distinguish **reuse of task-specific instructions** from **reuse of generic scaffolding**, and compare both with independently annotated action, object, domain and output. Include cross-cluster and within-cluster examples, stratify by family size and language, and ask two reviewers to label them independently. Report results by family as well as by pair. Keep related families and repositories together when splitting evaluation data. Treat runtime task success as a separate experiment requiring controlled execution and clear success criteria.

This check establishes counterexamples in the sample. It does not estimate their prevalence in the complete GitSkills corpus, prove copying direction or history, or show that a skill performs its declared task.

## Selected-pair assessments

All entries below are assistant static interpretations. Family IDs refer to the original lexical graph.

| Family | Selected pair | Shared content | Declared task relationship |
| ---: | --- | --- | --- |
"""
    details = []
    escape = html.escape
    for row in reviews:
        pair = row["pair"]
        names = f"{pair['left_name']} / {pair['right_name']}"
        procedure = row["procedure_type"].replace("_", " ")
        relationship = row["task_relationship"].replace("_", " ")
        findings += f"| {row['family']} | {names.replace('|', '/')} | {procedure} | {relationship} |\n"
        details.append(
            f'<details><summary>Family {row["family"]}: {escape(names)}</summary>'
            f'<p><strong>{escape(relationship)}</strong> · {escape(procedure)}</p>'
            f'<p>{escape(row["note"])}</p><p class="muted">{escape(row["selection"])}; '
            f'Jaccard {float(pair["jaccard"]):.3f}; crosses purpose clusters: {pair["cross_purpose_cluster"]}.</p>'
            f'<p class="hash">Contents: {pair["left_sha"]}<br>{pair["right_sha"]}</p></details>')
    (RESULTS / "FINDINGS.md").write_text(findings, encoding="utf-8")
    metric_html = "".join(f"<tr><td>{escape(label)}</td><td>{n}/{total}</td><td>{n/total:.1%}</td></tr>"
                          for label, n, total in metrics)
    report = f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>GitSkills: template reuse audit</title><style>
body{{font:16px/1.65 system-ui,sans-serif;background:#f5f7f8;color:#19313b;max-width:1000px;margin:36px auto;padding:0 22px}}
h1{{font-size:2.5rem;line-height:1.2}}h2{{margin-top:2rem}}a{{color:#086b7e}}.muted{{color:#566c76}}
.note{{background:#fff4dc;border-left:4px solid #ae7d2e;padding:14px 20px}}table{{border-collapse:collapse;width:100%;background:white}}
th,td{{padding:12px;border-bottom:1px solid #d7e2e7;text-align:left}}th{{background:#e4eef0}}
details{{background:white;border:1px solid #d7e2e7;border-radius:8px;margin:10px 0;padding:14px 18px}}summary{{cursor:pointer;font-weight:650}}
.hash{{font:12px/1.6 monospace;overflow-wrap:anywhere}}.table-wrap{{overflow:auto}}code{{overflow-wrap:anywhere}}
</style><main><p class="muted">DTU 02807 · GitSkills GitHub sample · static audit</p>
<h1>Same template, same purpose?</h1>
<p>Sometimes. Shared text can encode a substantive workflow, a generic checklist, or a wrapper that delegates work elsewhere. The sample contains all three.</p>
<p><a href="gitskills-prototype.zip" download>Download code, evidence tables and methods</a> · <a href="gitskills-purpose-explorer.html">Purpose explorer</a></p>
<p class="note"><strong>The previous 275/649 count needs qualification.</strong> One family of 25 contents contributes 255 of the 275 cross-cluster pairs (92.7%). Pair counts exaggerate its influence. Cluster disagreement is not a validated difference in purpose.</p>
<h2>A confirmed text-level counterexample</h2>
<p><strong>DNS architecture and dairy operations share the same normalized instruction body.</strong> So do 23 other differently named skills in that family. Removing metadata and the first title leaves requirements, research, drafting, review, action-plan and metric templates, with no domain-specific procedure.</p>
<h2>Count families as well as pairs</h2><div class="table-wrap"><table><thead><tr><th>Diagnostic</th><th>Count</th><th>Fraction</th></tr></thead><tbody>{metric_html}</tbody></table></div>
<p>Excluding the dominant family is an influence check, not an estimate of the true rate of different purposes. The 14/140 family count still depends on provisional clusters. In total, 355 pairs have identical normalized bodies; that includes substantive workflows and does not identify boilerplate by itself.</p>
<h2>Check the tasks, not just their cluster IDs</h2>
<p>Selected pairs in <strong>{len(same_cross)} of {len(cross)} crossing families</strong> still describe the same core task. Examples include spreadsheet editing, Context7 documentation lookup, Azure messaging and GitHub issue management. Language, metadata and runtime variants can split one task across clusters.</p>
<p>Within-cluster controls reveal the reverse: Redis and Unleash share an integration mechanism but target different services. A shared production scaffold also links civic-plan evaluation with accessibility-journal maintenance inside one broad cluster.</p>
<h2>Inspect the 36 selected pairs</h2>
<p class="note">The following are <strong>assistant static assessments, not human-validated labels</strong>. One pair represents each family; it does not establish equivalence for every family member. No dataset skill or script was executed.</p>
{''.join(details)}
<h2>Method and limits</h2>
<p>The audit recomputed exact five-word-shingle Jaccard for all 649 existing edges and checked content hashes. It includes all 14 cross-cluster families, 20 randomly selected within-cluster controls (seed 20261028), and the three largest controls; overlap leaves 36 families. Pair selection favors crossing pairs and then highest similarity. This is a targeted review, not a population survey.</p>
<p>Title-free equality uses YAML and first-H1 removal, Unicode NFKC, case folding and whitespace collapse. It is a text heuristic, not an execution test. Referenced resources were not evaluated. All 11,015 eligible contents come from the pinned <a href="https://github.com/giuseppedestefanis/gitskills-sample/tree/fff3df93beeee51a5444450891751f143e38da3e">GitHub sample</a>; the full Zenodo corpus was not analyzed.</p>
<h2>What this supports</h2>
<p>Study <strong>task-specific instruction reuse versus generic scaffold reuse</strong>. Use independent action/object/domain/output annotations, include within-cluster controls, and evaluate by family and repository. Runtime success needs a separate controlled study.</p>
<p>The bundle contains <code>results/template-audit/FINDINGS.md</code>, all pair and family diagnostics, the assistant review, blank human review fields, and <code>gitskills/template_audit.py</code>. Raw evidence packets can be regenerated from the pinned data using <code>scripts/run_template_audit.py --output results/audit-reproduction</code>.</p>
</main></html>'''
    destination = ROOT / "artifacts/gitskills-template-audit.html"
    destination.write_text(report, encoding="utf-8")
    print(f"Rendered {len(reviews)} selected-pair assessments; {len(same_cross)}/{len(cross)} crossing-family pairs assessed as the same core task.")
    print(Counter(row["procedure_type"] for row in reviews))


if __name__ == "__main__":
    main()

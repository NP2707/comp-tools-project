"""Render labeled purpose clusters as CSV, Markdown, plots and an offline explorer."""
from __future__ import annotations

import base64
import csv
import html
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results/purpose"
ARTIFACTS = ROOT / "artifacts"


def read_csv(name):
    with (RESULTS / name).open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def write_csv(name, rows):
    with (RESULTS / name).open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    labels = {row["cluster"]: row for row in json.loads((RESULTS / "cluster_labels.json").read_text())}
    evidence = {row["cluster"]: row for row in json.loads((RESULTS / "cluster_evidence.json").read_text())}
    summary = json.loads((RESULTS / "summary.json").read_text())
    import hashlib
    for name, expected in summary["source_sha256"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected, name
    clusters = [{**row, **labels[int(row["cluster"])]} for row in read_csv("clusters.csv")]
    assert set(labels) == {int(row["cluster"]) for row in clusters}
    assignments = [{**row, "purpose": labels[int(row["cluster"])]["purpose"],
                    "assessment": labels[int(row["cluster"])]["assessment"]} for row in read_csv("assignments.csv")]
    assert len(assignments) == summary["corpus"]["selected_contents"]
    write_csv("assignments_labeled.csv", assignments)
    write_csv("purpose_summary.csv", clusters)
    # Representative/random/boundary examples are evidence for interpretation,
    # not an independent quality test. Reviewer judgments stay explicitly blank.
    review = []
    for cluster, item in evidence.items():
        for example in item["examples"]:
            review.append({"cluster": cluster, "proposed_purpose": labels[cluster]["purpose"],
                           **example, "reviewer_purpose": "", "fits_proposed_cluster": "", "review_notes": ""})
    write_csv("purpose_review.csv", review)
    unresolved = sum(int(row["contents"]) for row in clusters if row["assessment"] == "unresolved")
    markdown = ["Purpose clustering of the GitSkills sample\n",
                "These are provisional interpretations of declared purposes, inferred by the assistant from enriched terms and sampled descriptions. They are not human-validated labels.\n",
                f"Analyzed {len(assignments):,} distinct contents in 24 clusters. {unresolved:,} contents lie in explicitly unresolved groups; {summary['low_margin_fraction']:.1%} have an assignment margin below 0.05.\n",
                "| Cluster | Proposed purpose | Contents | Assessment |", "| --- | --- | ---: | --- |"]
    for row in clusters:
        markdown.append(f"| {row['cluster']} | {row['purpose']} | {int(row['contents']):,} | {row['assessment']} |")
    markdown.extend(["", "Representation: name + description TF-IDF contributes 85% and body TF-IDF 15% before 128-dimensional LSA and K-means. The 24-cluster view is an inspection choice. The 12/24/36/48 sweep, seed checks and single-view comparisons are saved alongside this report.",
                     "", "At 24 clusters, cosine silhouette is approximately 0.092 and alternate-seed adjusted Rand scores are approximately 0.39. These indicate weak separation and substantial sensitivity. Margins are geometric diagnostics, not confidence probabilities.",
                     "", "The description-only partition has adjusted Rand agreement 0.443 with the combined view, versus 0.132 for body-only. This is representation sensitivity, not proof that a description contradicts its body.",
                     "", "Of the 649 previously verified lexical-similarity pairs, 275 cross these purpose clusters. Fourteen of 140 lexical families span multiple clusters. Because the purpose assignments are provisional, these are candidates for studying template reuse, not confirmed purpose changes.",
                     "", "Follow-up audit: 255 of the 275 crossing pairs (92.7%) come from one 25-content family. Excluding that family leaves 20/349 crossing pairs. Selected pairs in seven of the 14 crossing families still describe the same core task in assistant static review. These counts cannot be treated as purpose-change prevalence. See [the audit findings](../template-audit/FINDINGS.md).",
                     "", "See docs/purpose-methodology.md and docs/purpose-ideas.md. Human-review fields in purpose_review.csv are empty."])
    (RESULTS / "PURPOSES.md").write_text("\n".join(markdown) + "\n")
    os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".cache/matplotlib"))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(12, 11), constrained_layout=True)
    colors = ["#b38b63" if row["assessment"] in {"unresolved", "mixed", "language-influenced"} else "#287d87" for row in clusters]
    bars = ax.barh([f"{row['cluster']:02d}  {row['purpose']}" for row in clusters], [int(row["contents"]) for row in clusters], color=colors)
    ax.invert_yaxis()
    ax.bar_label(bars, padding=4, fontsize=9)
    ax.set_xlabel("Distinct contents in the filtered GitHub sample")
    ax.set_title("Provisional purpose clusters\nBrown: mixed, language-influenced, or unresolved", loc="left")
    ax.set_xlim(0, max(int(row["contents"]) for row in clusters) * 1.13)
    ax.tick_params(axis="y", labelsize=9)
    ax.spines[["right", "top"]].set_visible(False)
    for suffix in ("png", "svg"):
        fig.savefig(RESULTS / f"purpose_clusters.{suffix}", dpi=140)
    plt.close(fig)
    png = base64.b64encode((RESULTS / "purpose_clusters.png").read_bytes()).decode()
    cards = []
    for row in clusters:
        item = evidence[int(row["cluster"])]
        examples = "".join(f'<li><strong>{html.escape(ex["name"])}</strong> <small>({ex["selection"]})</small><br>{html.escape(ex["description"][:450])}</li>'
                           for ex in item["examples"] if ex["selection"] != "boundary")
        cards.append(f'<details><summary>{row["cluster"]:02d} · {html.escape(row["purpose"])} <span>{int(row["contents"]):,} contents · {row["assessment"]}</span></summary>'
                     f'<p>{html.escape(row["interpretation"])}</p><p><strong>Enriched terms:</strong> {html.escape(row["top_terms"])}</p>'
                     f'<button data-cluster="{row["cluster"]}">Browse skills in this cluster</button><ul>{examples}</ul></details>')
    # Escape HTML delimiters inside JSON; table rows are rendered with textContent.
    data = [{"sha": row["sha"], "name": row["name"], "description": row["description"],
             "cluster": int(row["cluster"]), "purpose": row["purpose"], "assessment": row["assessment"],
             "margin": round(float(row["assignment_margin"]), 5), "uncertain": row["ambiguous_margin"] == "True"}
            for row in assignments]
    payload = json.dumps({"skills": data, "clusters": clusters}, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    header = f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>GitSkills purpose explorer</title><style>
body{{font:16px/1.6 system-ui,sans-serif;background:#f4f7f8;color:#19313b;max-width:1150px;margin:35px auto;padding:0 24px}}
h1{{font-size:2.3rem}}a{{color:#086b7e}}small,.muted{{color:#61717b}}.note{{background:#fff7e8;border-left:4px solid #ba8d46;padding:14px 18px}}
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px}}.card,details{{background:white;border:1px solid #d4e1e4;border-radius:8px;padding:16px}}
.card strong{{display:block;font-size:1.8rem}}details{{margin:10px 0}}summary{{cursor:pointer;font-weight:650}}summary span{{display:block;font-weight:400;color:#61717b;font-size:.9rem}}
li{{margin:12px 0}}img{{max-width:100%}}input,select,button{{font:inherit;padding:9px;border:1px solid #b1c5ca;border-radius:5px;background:white;color:inherit}}button{{cursor:pointer}}
.controls{{display:flex;gap:10px;flex-wrap:wrap;align-items:center}}.table-wrap{{overflow:auto}}table{{width:100%;border-collapse:collapse;background:white;font-size:.9rem}}td,th{{padding:10px;border-bottom:1px solid #d4e1e4;text-align:left;vertical-align:top}}td:nth-child(3){{min-width:320px}}th{{background:#e1edef}}h2{{margin-top:2rem}}
</style><main><p class="muted">DTU 02807 · GitSkills sample · exploratory analysis</p><h1>What are the skills for?</h1>
<p>Search all {len(assignments):,} analyzed skills and inspect the evidence behind 24 proposed purpose groups.</p>
<p><a href="gitskills-prototype.zip" download>Download the full code and results bundle</a></p>
<p class="note">Labels are assistant interpretations of terms and sampled descriptions, not validated ground truth.
Some groups reflect language or tooling rather than a shared task. Low-margin assignments deserve review; the margin is not a probability.</p>
<div class="cards"><div class="card"><strong>{len(assignments):,}</strong>distinct contents</div><div class="card"><strong>24</strong>inspection clusters</div>
<div class="card"><strong>{unresolved:,}</strong>in unresolved groups</div><div class="card"><strong>{summary['low_margin_fraction']:.1%}</strong>low-margin assignments</div></div>
<h2>Cluster overview</h2><img src="data:image/png;base64,{png}" alt="Sizes and proposed labels of all 24 purpose clusters">
<p>Names/descriptions receive 85% weight and bodies 15%, followed by TF-IDF, 128-dimensional LSA and K-means.
The model uses local computation and no external API. The GitHub sample was used, not the full Zenodo corpus.</p>
<h2>Purpose and supporting examples</h2>{''.join(cards)}
<h2 id="browser">Browse individual skills</h2><div class="controls"><label>Cluster <select id="cluster"><option value="">All clusters</option></select></label>
<input id="search" type="search" placeholder="Search names, descriptions, purposes" aria-label="Search skills"><label><input type="checkbox" id="uncertain"> Low margin only</label><button id="download">Download filtered CSV</button></div>
<p id="count" aria-live="polite"></p><div class="controls"><button id="previous">Previous</button><button id="next">Next</button></div>
<div class="table-wrap"><table><thead><tr><th>Name</th><th>Proposed purpose</th><th>Declared description</th><th>Margin</th></tr></thead><tbody id="rows"></tbody></table></div>
<h2>What the diagnostics say</h2><p>Cosine silhouette at 24 clusters: 0.092. Alternate-seed adjusted Rand agreement: about 0.39.
Description-only agreement with the combined partition: 0.443; body-only: 0.132. These indicate substantial representation and initialization sensitivity.</p>
<p>275 of 649 lexical-similarity pairs cross these purpose clusters; 14 of 140 similarity families span multiple groups.
This suggests candidates for investigating template reuse. It does not establish genuine purpose drift or copying direction.</p>
<p class="note"><strong>Follow-up audit:</strong> 255 of those 275 crossing pairs (92.7%) belong to one 25-content family.
Excluding it leaves 20/349 crossing pairs. Selected pairs in seven of the 14 crossing families still describe the same core task in assistant static review.
<a href="gitskills-template-audit.html">Read the checked evidence and limitations</a>.</p>
<p>Next methods to compare: multilingual sentence embeddings; multi-label action/object/domain/output extraction; overlapping topic models;
declared-purpose versus body evidence; and task-to-skill retrieval evaluated by people.
See the included methodology and ideas documents for experimental designs and sources.</p>
<p class="muted">This HTML contains the chart and search data and works offline. Dataset descriptions are shown as plain text.</p></main>
<script type="application/json" id="data">{payload}</script>'''
    script = '''<script>
const data=JSON.parse(document.getElementById('data').textContent), select=document.getElementById('cluster');
for(const c of data.clusters)select.add(new Option(`${c.cluster}: ${c.purpose} (${c.contents})`, c.cluster));
let page=0, filtered=[]; const size=50;
function render(){const query=document.getElementById('search').value.toLocaleLowerCase(), only=document.getElementById('uncertain').checked;
filtered=data.skills.filter(s=>(select.value===''||s.cluster===Number(select.value))&&(!only||s.uncertain)&&(!query||[s.name,s.description,s.purpose].join(' ').toLocaleLowerCase().includes(query)));
const pages=Math.max(1,Math.ceil(filtered.length/size));page=Math.min(page,pages-1);
document.getElementById('count').textContent=`${filtered.length.toLocaleString()} matching skills · page ${page+1} of ${pages}`;
const body=document.getElementById('rows');body.replaceChildren();
for(const s of filtered.slice(page*size,(page+1)*size)){const row=document.createElement('tr');
for(const value of [s.name,`${s.cluster}: ${s.purpose}`,s.description,`${s.margin.toFixed(3)}${s.uncertain?' · low':''}`]){const cell=document.createElement('td');cell.textContent=value;row.appendChild(cell);}body.appendChild(row);}
document.getElementById('previous').disabled=page===0;document.getElementById('next').disabled=page>=pages-1;}
for(const id of ['cluster','search','uncertain'])document.getElementById(id).addEventListener('input',()=>{page=0;render();});
document.getElementById('previous').onclick=()=>{page--;render();};document.getElementById('next').onclick=()=>{page++;render();};
for(const button of document.querySelectorAll('[data-cluster]'))button.onclick=()=>{select.value=button.dataset.cluster;document.getElementById('search').value='';document.getElementById('uncertain').checked=false;page=0;render();document.getElementById('browser').scrollIntoView({behavior:'smooth'});};
document.getElementById('download').onclick=()=>{const fields=['sha','name','cluster','purpose','assessment','description','margin','uncertain'];
const escape=value=>{let text=String(value??'');if(/^[=+@-]/.test(text))text="'"+text;return '"'+text.replaceAll('"','""')+'"';};
const csv=[fields.join(','),...filtered.map(row=>fields.map(key=>escape(row[key])).join(','))].join('\\r\\n');
const url=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download='skill-purposes.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};render();
</script></html>'''
    ARTIFACTS.mkdir(exist_ok=True)
    (ARTIFACTS / "gitskills-purpose-explorer.html").write_text(header + script, encoding="utf-8")
    print(f"Rendered {len(clusters)} labeled clusters and {len(assignments):,} searchable assignments.")


if __name__ == "__main__":
    main()

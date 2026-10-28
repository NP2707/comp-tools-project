"""Build a portable source/results ZIP and a self-contained HTML report."""
from __future__ import annotations

import base64
import csv
import hashlib
import html
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results" / "sample-4000"
DEST = ROOT / "artifacts"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def table(rows, fields):
    head = "".join(f"<th>{html.escape(field.replace('_', ' '))}</th>" for field in fields)
    body = "".join("<tr>" + "".join(f"<td>{html.escape(str(row.get(field, '')))}</td>"
                                   for field in fields) + "</tr>" for row in rows)
    return f'<div class="table-wrap"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def main():
    DEST.mkdir(exist_ok=True)
    summary = json.loads((RESULTS / "summary.json").read_text())
    manifest = json.loads((ROOT / "data" / "manifest.json").read_text())
    for name, expected in summary["source_sha256"].items():
        if sha256((ROOT / name).read_bytes()) != expected:
            raise ValueError(f"Analysis source differs from recorded run: {name}")
    evaluation = list(csv.DictReader((RESULTS / "retrieval.csv").open()))
    graph = summary["graph"]
    chart = base64.b64encode((RESULTS / "overview.png").read_bytes()).decode()
    code_files = sorted((ROOT / "gitskills").glob("*.py"))
    source = "".join(f'<details><summary>{html.escape(str(path.relative_to(ROOT)))}</summary>'
                     f'<pre><code>{html.escape(path.read_text())}</code></pre></details>' for path in code_files)
    source_url = ("https://github.com/giuseppedestefanis/gitskills-sample/tree/"
                  + manifest["source_commit"])
    report = f'''<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>GitSkills — prototype artifact</title>
<style>
:root{{font-family:system-ui,sans-serif;color:#19313b;background:#f4f7f8;line-height:1.6}}
body{{max-width:1080px;margin:40px auto;padding:0 24px}}h1{{font-size:2.4rem;line-height:1.15}}
h2{{margin-top:2.5rem}}a{{color:#086b7e}}.tag{{font-size:.8rem;text-transform:uppercase;letter-spacing:.12em;color:#52717b}}
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:16px}}
.card,details{{background:white;border:1px solid #d9e4e8;border-radius:10px;padding:18px}}
.card strong{{font-size:1.8rem;display:block}}.muted{{color:#526b75}}img{{width:100%;background:white}}
.table-wrap{{overflow:auto}}table{{border-collapse:collapse;background:white;width:100%;font-size:.9rem}}
th,td{{padding:9px 12px;border-bottom:1px solid #d9e4e8;text-align:left}}th{{background:#e4eef0}}
pre{{white-space:pre-wrap;overflow-wrap:anywhere;background:#102c36;color:#edf7f8;padding:18px;border-radius:8px;font-size:.85rem}}
summary{{cursor:pointer;font-weight:650}}details{{margin:10px 0}}.note{{border-left:4px solid #c48b30;padding:8px 18px;background:#fff8e9}}
@media print{{body{{margin:0}}details{{break-inside:avoid}}a{{color:inherit}}}}
</style>
<main>
<p class="tag">DTU 02807 · MSR 2027 · initial prototype</p>
<h1>GitSkills similarity study</h1>
<p>Research question: what families of similar agent instructions appear beyond identical byte contents?</p>
<p><a href="gitskills-prototype.zip" download>Download code, notebook, results, and reproduction instructions</a></p>
<p class="note"><strong>Dataset used: the GitHub sample.</strong> The full Zenodo dataset was not downloaded or analyzed.
The sample contains 29,786 file occurrences and 13,000 distinct contents; the default filters retain 11,015 contents.</p>
<div class="cards">
<div class="card"><strong>{summary['corpus']['selected_contents']:,}</strong>eligible distinct contents</div>
<div class="card"><strong>{graph['edges']:,}</strong>verified pairs at Jaccard ≥ 0.8</div>
<div class="card"><strong>{graph['nontrivial_communities']:,}</strong>communities with at least two contents</div>
<div class="card"><strong>122 / 122</strong>qualifying pairs retrieved on the 4,000-document evaluation subset</div>
</div>
<h2>What code was used?</h2>
<p>The analysis code was written for this project. The external GitHub repository supplied the data sample.</p>
{table([
    {'part':'Data loading and preprocessing','implementation':'Project Python code; sqlite3, Unicode normalization, Git blob verification'},
    {'part':'Shingling, MinHash, banded LSH, exact Jaccard','implementation':'Custom project implementation, using NumPy for hash arithmetic'},
    {'part':'Graph communities','implementation':'NetworkX weighted Louvain implementation'},
    {'part':'Latent semantic analysis','implementation':'scikit-learn TF-IDF, TruncatedSVD, normalization; project cosine-neighbour selection'},
    {'part':'Evaluation, review sampling, orchestration','implementation':'Project Python code'},
    {'part':'Figures and notebook','implementation':'Matplotlib and Jupyter/nbformat/nbclient'}
], ['part','implementation'])}
<h2>Results and interpretation</h2>
<p>LSH proposed {summary['candidates']:,} of {summary['possible_pairs']:,} possible pairs.
The complete run took {summary['timings_seconds']['total']:.1f} seconds including exhaustive evaluation and comparisons;
peak process memory was {summary['peak_process_rss_mib']:,.0f} MiB. The baseline's nine correctness tests passed and its notebook was executed.</p>
<img src="data:image/png;base64,{chart}" alt="Recall by LSH layout and Jaccard threshold, ranked community sizes, and verified edge similarities">
<p>Some high-similarity pairs share generic templates despite different purposes. At resolution 1, Louvain reproduces
the connected components at each evaluated threshold. Human review and a stronger graph formulation are still needed.
Subset recall is not a guarantee of complete full-corpus recall. Verified precision follows the lexical threshold definition,
not human judgments of useful similarity.</p>
<p>The <a href="gitskills-template-audit.html">template audit</a> checks this interpretation: one generic family accounts
for 92.7% of pairs crossing the provisional purpose clusters. Shared text and cluster assignments alone do not establish shared functionality.</p>
<h2>Retrieval evaluation</h2>
{table(evaluation, ['bands','rows','threshold','true_pairs','retrieved_true_pairs','missed_true_pairs','candidate_pairs','recall'])}
<h2>Data provenance</h2>
<p><a href="{source_url}">Pinned GitSkills GitHub sample</a>, commit <code>{manifest['source_commit']}</code>.</p>
<p>Database SHA-256: <code>{manifest['database_sha256']}</code>.<br>
Archive SHA-256: <code>{manifest['archive_sha256']}</code>.</p>
<p>The ZIP includes the downloader and manifest. The raw database is downloaded separately by the included script.
The report itself is self-contained and works offline; the ZIP download link expects the ZIP beside this HTML file.</p>
<h2>Reproduce after extracting the ZIP</h2>
<pre>cd gitskills-prototype
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt
.venv/bin/python scripts/download_sample.py
.venv/bin/python -m pytest -q
.venv/bin/python -m gitskills --eval-size 4000 --output results/reproduction</pre>
<p>The saved results retain their original run metadata. New runs resolve the database relative to the extracted project.</p>
<h2>Browse the analysis source</h2>
{source}
</main></html>'''
    (DEST / "gitskills-report.html").write_text(report, encoding="utf-8")
    files = [ROOT / p for p in ("README.md", ".gitignore", "requirements.txt", "requirements-lock.txt", "data/manifest.json")]
    for directory, pattern in (("gitskills", "*.py"), ("scripts", "*.py"), ("tests", "*.py"),
                               ("docs", "*.md"), ("notebooks", "*.ipynb"),
                               ("results/sample", "*"), ("results/sample-4000", "*"), ("results/purpose", "*"),
                               ("results/template-audit", "*")):
        files.extend(p for p in (ROOT / directory).glob(pattern)
                     if p.is_file() and p.name != "evidence_packets.json")
    entries = {str(path.relative_to(ROOT)): path.read_bytes() for path in sorted(set(files))}
    entries["artifacts/gitskills-report.html"] = report.encode()
    purpose_report = DEST / "gitskills-purpose-explorer.html"
    if purpose_report.exists():
        entries["artifacts/gitskills-purpose-explorer.html"] = purpose_report.read_bytes()
    audit_report = DEST / "gitskills-template-audit.html"
    if audit_report.exists():
        entries["artifacts/gitskills-template-audit.html"] = audit_report.read_bytes()
    entries["ARTIFACT.md"] = (
        "GitSkills prototype artifact\n\n"
        "Data source: the pinned GitHub sample, not the full Zenodo corpus.\n"
        "Start with README.md, notebooks/01_gitskills.ipynb, or artifacts/gitskills-report.html.\n"
        "The current run is results/sample-4000; results/sample preserves the earlier pilot.\n"
        "Purpose clustering is in results/purpose, with an interactive artifacts/gitskills-purpose-explorer.html.\n"
        "Read artifacts/gitskills-template-audit.html for the checked template-versus-task findings.\n"
        "The audit includes separate assistant assessments and blank human-review fields.\n"
        "Full raw audit text packets are omitted; regenerate them with scripts/run_template_audit.py.\n"
        "The source, executed notebook, CSV outputs, figures, tests, dependency lock, and provenance are included.\n"
        "Download the raw sample using scripts/download_sample.py; environments and raw data are not bundled.\n"
        "SHA256SUMS.txt records every included file except itself.\n"
    ).encode()
    entries["SHA256SUMS.txt"] = "".join(f"{sha256(data)}  {name}\n" for name, data in sorted(entries.items())).encode()
    archive = DEST / "gitskills-prototype.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as target:
        for name, data in sorted(entries.items()):
            target.writestr("gitskills-prototype/" + name, data)
    with zipfile.ZipFile(archive) as check:
        assert check.testzip() is None
        for name, data in entries.items():
            assert check.read("gitskills-prototype/" + name) == data
        assert not any("/data/raw/" in name or "/.venv/" in name for name in check.namelist())
    artifact_files = [archive, DEST / "gitskills-report.html"]
    if purpose_report.exists():
        artifact_files.append(purpose_report)
    if audit_report.exists():
        artifact_files.append(audit_report)
    (DEST / "SHA256SUMS.txt").write_text("".join(
        f"{sha256(path.read_bytes())}  {path.name}\n" for path in artifact_files))
    print(f"Verified {len(entries)} files in {archive.name} ({archive.stat().st_size:,} bytes)")
    print(f"Standalone report: {DEST / 'gitskills-report.html'}")


if __name__ == "__main__":
    main()

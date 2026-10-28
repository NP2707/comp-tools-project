# Comp tools project

GitSkills near-duplicate and purpose analysis for [DTU 02807](https://courses.compute.dtu.dk/02807/2026/) and the [MSR 2027 Mining Challenge](https://2027.msrconf.org/track/msr-2027-mining-challenge).

**Start here:** [everything completed, findings, limitations and next steps](docs/project-handoff.md). The study asks whether similar agent-skill instructions represent specialized procedures or generic templates. Shared text sometimes spans very different declared tasks, but the provisional purpose clusters cannot be treated as ground truth.

The HTML reports below can be downloaded and opened locally; GitHub displays their source. The linked Markdown summaries are readable directly on GitHub.

Artifacts: [complete ZIP bundle](artifacts/gitskills-prototype.zip) and [standalone HTML report with source code](artifacts/gitskills-report.html). This analysis used the **GitHub sample**, not the full Zenodo dataset. Rebuild the bundle with `python scripts/build_artifact.py`.

Purpose analysis is now available in the [interactive purpose explorer](artifacts/gitskills-purpose-explorer.html), [24-group summary](results/purpose/PURPOSES.md), and [labeled assignments](results/purpose/assignments_labeled.csv). Labels are provisional assistant interpretations; mixed and unresolved groups are explicitly marked. See [purpose methodology](docs/purpose-methodology.md) and [further research ideas](docs/purpose-ideas.md).

The [template audit artifact](artifacts/gitskills-template-audit.html) and [detailed findings](results/template-audit/FINDINGS.md) check whether shared text implies shared purpose. One generic 25-content family produces 255 of 275 cross-cluster pairs (92.7%); excluding it leaves 20/349. Static review of 36 selected pairs finds both substantive same-task reuse and generic scaffolds under different declared tasks. Cluster disagreement is not ground truth, and runtime functionality was not evaluated. Reproduce diagnostics in a fresh folder with `.venv/bin/python scripts/run_template_audit.py --output results/audit-reproduction`. Rebuild reports with `scripts/build_template_report.py`, `scripts/build_purpose_report.py`, then `scripts/build_artifact.py`, using the project Python environment.

The first prototype includes a pinned sample downloader, custom MinHash/LSH, exact Jaccard verification, Louvain communities, exhaustive retrieval evaluation, and a latent semantic analysis (LSA) comparison. Start with [the notebook](notebooks/01_gitskills.ipynb), [run results](results/sample-4000/RESULTS.md), or [the figure](results/sample-4000/overview.png).

The working research question is: **What additional families of similar agent skills appear beyond byte-identical copies, and how sensitive are those families to the similarity representation and threshold?** Human review is needed before interpreting similarity families as meaningful reuse. Read [the pilot findings](docs/pilot-findings.md) for observations and the limitations exposed by this first run.

Run these commands from this folder with Python 3.12:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt
.venv/bin/python scripts/download_sample.py
.venv/bin/python -m pytest -q
.venv/bin/python -m gitskills --eval-size 4000 --output results/reproduction
```

An installed `.venv` and downloaded sample are already available in this workspace. The downloader pins the repository commit, checks the archive against its Git blob hash, verifies SQLite integrity, and records [checksums](data/manifest.json). Raw data and the environment are ignored by Git. `requirements.txt` describes direct dependencies; `requirements-lock.txt` records the tested environment. On systems without `ensurepip`, use an available Python/venv installer; this workspace used the official PyPA pip zipapp to install pip into the local environment.

Each run needs a new or empty output directory, preserving earlier experiments and reviewer labels. A smoke run uses `--limit 200 --eval-size 150`. Use `--help` for filters and parameters. The implementation is sized for the published sample; the full corpus needs a separate scaling plan.

| File or directory | Purpose |
| --- | --- |
| `gitskills/corpus.py` | Read-only SQLite access, content verification, filtering, copy counts |
| `gitskills/similarity.py` | Custom shingling, seeded MinHash, banded LSH, exact verification |
| `gitskills/experiments.py` | Exhaustive evaluation, Louvain, LSA, review sampling |
| `gitskills/__main__.py` | Command-line experiment and exports |
| `notebooks/01_gitskills.ipynb` | Guided inspection, results, reproduction commands |
| `results/sample-4000/summary.json` | Configuration, code/data hashes, versions, timing, peak memory |
| `results/sample-4000/retrieval.csv` | Recall, precision, candidate reduction, timings |
| `results/sample-4000/nodes.csv`, `edges.csv`, `communities.csv` | Content graph and occurrence summaries |
| `results/sample-4000/graph_sensitivity.csv` | Threshold and Louvain-resolution comparisons |
| `results/sample-4000/lsa_pairs.csv`, `review.csv` | Semantic candidates and unlabeled review sample |
| `tests/` | Algorithm and data-handling checks, including deliberately missed matches |

The two course topics are similarity/LSH and graph clustering. The additional method is LSA: TF-IDF is projected through truncated SVD, then normalized vectors are compared by cosine similarity. See [methodology](docs/methodology.md), [review instructions](docs/review.md), and [the original course/challenge orientation](docs/orientation.md).

The initial `results/sample` run used a 1,000-document evaluation subset with only one positive pair at Jaccard 0.8. Use `results/sample-4000` for the stronger evaluation. Neither is a final scientific result. Next steps are human review, preprocessing and seed sensitivity, refinement of the research question, and a decision about larger data. Group size, registration status, and the ambiguous course deadline still need confirmation for submission planning.

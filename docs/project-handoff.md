# Comp tools project — saved project handoff

Saved 28 October 2026. This document preserves the work completed, the conclusions reached, and how to continue. It summarizes the project discussion; it is not a verbatim chat transcript.

## Project and material

The project connects [DTU 02807 Computational Tools for Data Science](https://courses.compute.dtu.dk/02807/2026/) with the [MSR 2027 Mining Challenge](https://2027.msrconf.org/track/msr-2027-mining-challenge). Initial requirements, submission formats and scheduling questions are recorded in [orientation.md](orientation.md). Registration or submission has not been performed by this work.

The initial direction was to discover near-duplicate agent instruction files beyond byte-identical copies, then investigate whether their families represent generic templates or specialized skills. The implemented course topics are similarity/LSH and graph clustering, with latent semantic analysis (LSA) as the additional technique.

## Data actually used

All experiments use the **GitHub GitSkills sample**, not the full Zenodo dataset. The sample repository supplied data; the analysis code was written for this project.

- Repository: [giuseppedestefanis/gitskills-sample](https://github.com/giuseppedestefanis/gitskills-sample/tree/fff3df93beeee51a5444450891751f143e38da3e).
- Pinned commit: `fff3df93beeee51a5444450891751f143e38da3e`.
- Input: 29,786 file occurrences, representing 13,000 distinct contents.
- Default filters: 11,015 distinct contents, representing 26,713 occurrences.
- Full provenance and checksums: [data/manifest.json](../data/manifest.json).
- Raw database and its downloaded archive are retained locally under `data/raw/`. They are excluded from Git and the portable bundle; the downloader recreates them from the pinned source.

Dataset instructions and scripts were treated as research text, not executed.

## Completed work

### 1. Near-duplicate retrieval and graph analysis

Implemented custom five-word shingling, 128-component MinHash, and banded LSH with 32 bands of four rows. Candidates are verified with exact Jaccard similarity. NumPy supports hashing arithmetic; NetworkX supplies weighted Louvain clustering. The project code implements loading, orchestration, evaluation and exports. scikit-learn supplies TF-IDF and truncated SVD for the semantic comparison.

At Jaccard ≥ 0.8, LSH proposed 3,512 candidates out of 60,659,605 possible content pairs. Exact verification retained 649 edges. These form 140 nontrivial families involving 362 distinct contents; 10,653 contents remain isolated. At resolution 1, Louvain matches the connected components, so community detection adds no further subdivision in this run.

Exhaustive evaluation on a 4,000-content subset checked 7,998,000 possible pairs. The selected LSH configuration retrieved all 122 qualifying pairs at the 0.8 threshold. This is subset retrieval evidence, not a guarantee of full-corpus recall or human-judged semantic relevance.

The main run is [results/sample-4000](../results/sample-4000). The earlier 1,000-content evaluation pilot remains in `results/sample`; it had only one positive pair and is weaker evidence. The first [executed notebook](../notebooks/01_gitskills.ipynb) explains the pipeline.

### 2. Purpose clustering and interpretation

Implemented separately normalized name/description and body TF-IDF representations, weighted 85% and 15%, projected into 128-dimensional LSA, followed by K-means. The readable inspection view uses 24 clusters, with alternative cluster counts and seeds retained for comparison. The assistant interpreted enriched terms and sampled descriptions to label these groups.

The partition is provisional: cosine silhouette is about 0.092, alternate-seed adjusted Rand agreement is about 0.39, and 42.2% of assignments have a low geometric margin. Two explicitly unresolved groups contain 1,954 contents. Metadata-only agreement with the combined view is about 0.443; body-only agreement is about 0.132. These are representation diagnostics, not evidence that descriptions contradict behavior.

Saved outputs include all assignments, group summaries, example evidence, plots, stability comparisons, blank human-review fields, an [executed notebook](../notebooks/02_skill_purposes.ipynb), and an offline searchable [purpose explorer](../artifacts/gitskills-purpose-explorer.html). See [purpose methodology](purpose-methodology.md).

### 3. Checking whether shared templates imply shared purpose

The initial intersection found 275 of 649 lexical pairs crossing purpose clusters, with 14 of 140 families spanning clusters. The follow-up audit materially qualifies that interpretation:

| Finding | Interpretation |
| --- | --- |
| One 25-content family contributes 255 of the 275 crossing pairs (92.7%). | Pair counts are dominated by one dense family and are not independent observations. |
| Excluding that family leaves 20/349 crossing pairs (5.7%). | This is an influence diagnostic, not a corrected population estimate. |
| All 25 family members have identical normalized bodies after removing YAML metadata and the first H1. | Different declared tasks, including DNS architecture and dairy operations, share a generic requirements/draft/review scaffold. |
| Selected pairs from seven of the 14 crossing families describe the same core task in assistant static review. | Cluster mismatch is not reliable evidence of different purposes. |
| Some within-cluster controls target different services or declared tasks. | Cluster agreement is also insufficient evidence of task equivalence. |

The audit reviewed one selected pair in each of 36 families: all 14 crossing families, 20 randomly sampled within-cluster controls, and three large controls, with one overlap. Selection favors crossing pairs and then highest Jaccard similarity. This targeted qualitative review is not an unbiased population survey.

All 649 existing edge similarities were recomputed, and content hashes were checked. Static assessments are explicitly stored separately from blank human-review fields. Referenced scripts and external procedures were not evaluated. The findings establish text-level counterexamples, not runtime functionality, copying direction, historical evolution, or prevalence in the full corpus.

Read the [full audit findings](../results/template-audit/FINDINGS.md) or the [audit HTML artifact](../artifacts/gitskills-template-audit.html). The full raw text evidence packets are saved locally as `results/template-audit/evidence_packets.json`; they are excluded from Git and the portable archive and can be regenerated.

## Saved artifacts and verification

- [Complete source and results bundle](../artifacts/gitskills-prototype.zip).
- [Similarity report with analysis source](../artifacts/gitskills-report.html).
- [Interactive purpose explorer](../artifacts/gitskills-purpose-explorer.html).
- [Template audit report](../artifacts/gitskills-template-audit.html).
- [Artifact checksums](../artifacts/SHA256SUMS.txt).
- [Recorded audit verification](../results/template-audit/validation.json).

The latest analysis checks passed **15 tests**. An independent audit rerun reproduced all five generated output files byte for byte. The audit HTML has 36 evidence entries and resolving local links. The portable ZIP was checked for integrity and file contents. Browser visual testing was not performed. Human scientific validation remains outstanding.

## Reproduction

Run from the project root using Python 3.12. The existing workspace already contains the environment and sample data.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt
.venv/bin/python scripts/download_sample.py
.venv/bin/python -m pytest -q
.venv/bin/python -m gitskills --eval-size 4000 --output results/reproduction
.venv/bin/python -m gitskills.purpose --output results/purpose-reproduction
.venv/bin/python scripts/run_template_audit.py --output results/audit-reproduction
```

Each analysis needs a new or empty output folder. Purpose analysis and the template audit use the saved baseline inputs; running new output directories does not automatically redirect every downstream stage. Report renderers read the saved canonical result folders and their recorded assistant labels. They do not generate independent judgments.

To rebuild the saved reports and portable bundle:

```bash
.venv/bin/python scripts/build_template_report.py
.venv/bin/python scripts/build_purpose_report.py
.venv/bin/python scripts/build_artifact.py
```

## Direction to continue

The strongest supported next question is: **When do similar agent-skill instructions represent task-specific procedure reuse, and when do they merely reuse a generic scaffold under different declared purposes?**

1. Define action, object, domain, output and mechanism labels; allow multiple purposes per skill.
2. Obtain independent human annotations for both within-cluster and cross-cluster pairs, separating substantive instructions, generic scaffolds and delegated procedures. Include language and family-size strata.
3. Compare multilingual sentence embeddings and overlapping topic models against the existing LSA baseline using these labels, rather than relying on silhouette alone.
4. Evaluate task-to-skill retrieval on held-out task requests. Keep related families and repositories in the same evaluation split to reduce leakage.
5. Report family-level results alongside pair-level counts. Decide on full Zenodo data only after establishing a sampling and scaling plan.

Additional ideas and references are in [purpose-ideas.md](purpose-ideas.md). Runtime task success is a separate experiment requiring controlled execution and explicit success criteria. Team registration, group size, and the course deadline discrepancy recorded in the orientation still require confirmation for submission planning.

## Publication decision

The user requested a public explanation and then selected a GitHub repository under **NP2707** as the publication destination. The intended repository name is `comp-tools-project`. No Sites deployment was completed in this workflow. The repository should contain the code, notebooks, reports and portable artifact; raw data and local environments stay downloadable or reproducible through the documented steps.

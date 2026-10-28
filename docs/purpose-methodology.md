The purpose experiment analyzes the same 11,015 filtered distinct contents as the similarity study. Names and parsed descriptions are read from primary SQLite rows. Existing similarity code and results are preserved.

Names/descriptions and body tokens receive separate TF-IDF representations. The metadata view uses unigrams and bigrams; the body view uses unigrams. Common English words, a small German stopword list, generic skill-instruction terms, and opaque `u12345` identifiers are removed. We preserve Unicode words but do not translate or perform language-specific segmentation. This is a material limitation for multilingual text.

Each field is L2-normalized. Concatenating `sqrt(0.85) * metadata` with `sqrt(0.15) * body` gives the declared purpose more influence before reduction. Truncated SVD projects the result to 128 dimensions; rows are normalized again. K-means uses ten initializations and seed 42. This follows the general [TF-IDF/LSA document-clustering approach](https://scikit-learn.org/stable/auto_examples/text/plot_document_clustering.html), with a project-specific split into weighted fields.

The 24-group view was chosen as a readable initial granularity. We also evaluate 12, 36 and 48 clusters; the larger choices obtain better internal scores, so 24 is not claimed to be optimal or a true number of purposes. Cosine silhouette uses a fixed 1,500-document sample; Davies–Bouldin uses the embedded corpus. Two additional K-means seeds assess initialization sensitivity while keeping the representation fixed. Separate metadata-only and body-only fits assess representation sensitivity.

Cluster IDs are ordered by size. Enriched terms are ranked by the cluster's mean metadata TF-IDF minus the corpus mean. Each cluster includes five examples nearest its centroid, five randomly sampled members, and one low-margin boundary case. These examples support interpretation, not an independent quality test. The assistant inferred names and descriptions for the groups from the terms and examples; no external LLM/API was called. Human judgment columns in `purpose_review.csv` remain blank.

Assignment margin is `(distance_to_second - distance_to_first) / distance_to_second`. A value below 0.05 is flagged for review. This cutoff is a heuristic and the number is not a probability. Every document receives a K-means assignment; low-margin documents and explicitly unresolved clusters must not be treated as confidently classified. No human-labeled accuracy can be reported yet.

The results expose weak separation: silhouette about 0.092, alternate-seed adjusted Rand agreement about 0.39, and 42.2% low-margin assignments. Two groups totaling 1,954 contents are explicitly labeled unresolved. Several other groups are broad or language-influenced. In particular, AI or MCP can identify a mechanism rather than an end-user purpose. These failures motivate a multi-label taxonomy and multilingual representations.

We intersect purpose assignments with the existing near-duplicate families. Fourteen of 140 families span multiple purpose groups; 275 of 649 similarity edges cross groups. These are hypothesis-generating counts conditional on this unstable partition. They do not prove distinct purposes, template generation, historical changes, or copying direction. The 140 families are sparse content-sample families, not complete families in the full population.

The [follow-up template audit](../results/template-audit/FINDINGS.md) reveals strong concentration: one 25-content family contributes 255/275 crossing edges (92.7%). Excluding it leaves 20/349. Its normalized bodies are identical across different declared domains, confirming a generic-template counterexample, while selected pairs in seven of the 14 crossing families still describe the same core task in assistant static review. Pair counts are not independent, cluster disagreement is not task disagreement, and the audit does not evaluate runtime behavior.

Run from the project root:

```bash
.venv/bin/python -m gitskills.purpose --output results/purpose-reproduction
```

The report renderer reads the checked-in `results/purpose/cluster_labels.json`, generates labeled CSVs and plots, and builds the offline explorer:

```bash
.venv/bin/python scripts/build_purpose_report.py
.venv/bin/python scripts/build_artifact.py
```

Purpose interpretation needs validation: sample held-out members from each proposed group, ask two reviewers for independent activity/domain labels, measure agreement, and report purity and ambiguous coverage by group. Centroid examples used for naming should not double as the held-out validation sample. Avoid reporting a single overall accuracy before defining what counts as a correct multi-purpose assignment.

# Do shared templates imply shared functionality?

The sample confirms shared generic instructions across different **declared tasks**. It also contains shared substantive guidance for the same task. Lexical similarity alone does not distinguish these cases, and the purpose clusters are too unstable to serve as ground truth. No runtime functionality was evaluated.

## The earlier pair count is dominated by one family

| Diagnostic | Count | Fraction |
| --- | ---: | ---: |
| All verified lexical pairs | 275/649 | 42.4% |
| Largest family only | 255/300 | 85.0% |
| Pairs excluding largest family | 20/349 | 5.7% |
| Families spanning purpose clusters | 14/140 | 10.0% |

Family 0 contains 25 distinct contents and all 300 possible pairs. Its 255 crossing pairs account for **92.7% of the 275 crossing pairs**. Pairs sharing the same documents are not independent observations. Removing this family is an influence diagnostic, not a corrected population estimate. The family-level 14/140 count also describes cluster disagreement, not proven task differences.

All 25 family members have exactly the same normalized instruction body after removing leading YAML metadata and the first Markdown H1. Names and descriptions vary across 25 distinct values. Examples include **DNS architecture, dairy operations, virtual classroom design and startup board management**. Their common text asks for requirements, research, a draft, review, an action plan and metrics; it supplies no procedures specific to those domains. This is direct text-level evidence of generic template reuse, regardless of cluster assignments.

Across all 649 pairs, 355 have identical normalized title-free bodies. This number includes substantive same-task instructions and must not be interpreted as a count of generic boilerplate.

## Static review changes the interpretation

The assistant inspected one selected pair from each of 36 families: all 14 families spanning clusters, 20 randomly sampled within-cluster controls (seed 20261028), and the three largest within-cluster families. One large family overlaps the random controls, leaving 22 distinct controls. Pair selection prioritizes crossing pairs, then highest Jaccard similarity, so this is a targeted qualitative review, not a random pair survey.

Selected pairs in **7 of the 14 crossing families** describe the same core task: spreadsheet work, documentation lookup, social posting, extracting reusable lessons, Azure messaging, accounting entries and GitHub issue management. Differences include language, metadata, runtime configuration and optional integration steps. These are likely false splits at the core-task level; this assessment does not establish execution equivalence or label every pair in those families.

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
| 0 | vehicle-lifecycle-management / startup-board-management | generic boilerplate | different declared tasks |
| 1 | redis / unleash | parameterized wrapper | related tasks different targets |
| 2 | u3550-plan-quality-evaluation-for-civic-participation-platforms / u09955-decision-journal-maintenance-for-accessibility-services | generic boilerplate | different declared tasks |
| 3 | skill-creator / skill-creator | substantive instructions | same core task |
| 5 | turborepo / turborepo | substantive instructions | same core task |
| 6 | mm-improve-codebase-architecture / improve-codebase-architecture | substantive instructions | same core task |
| 7 | owasp-www-project-threat-dragon / owasp-www-chapter-cali | parameterized wrapper | related tasks different targets |
| 10 | dokument-xlsx / xlsx | substantive instructions | same core task |
| 13 | arabic-teamwork-skills / arabic-security-awareness | placeholder template | different declared tasks |
| 22 | critique / critique | substantive instructions | same core task |
| 31 | plan / plan | substantive instructions | same core task |
| 33 | architecture / architecture | substantive instructions | same core task |
| 34 | find-docs / find-docs | substantive instructions | same core task |
| 38 | gtm-create-html-slides / frontend-slides | substantive instructions | same core task |
| 46 | sns-patterns / sns-patterns | substantive instructions | same core task |
| 48 | extracting-learned-skills / learner | substantive instructions | same core task |
| 59 | expeditionary-additive-munitions-quality-assurance-cell / theater-maritime-fuel-blending-and-quality-assurance-cell | generic boilerplate | related tasks different targets |
| 66 | copywriting / copywriting | substantive instructions | same core task |
| 67 | File Encryption Manager / pdf-ci-helper-agent-configuration | generic boilerplate | different declared tasks |
| 72 | simplify-code / simplify-code | substantive instructions | same core task |
| 78 | algorithmic-art / algorithmic-art | substantive instructions | same core task |
| 80 | temporal-python-testing / temporal-python-testing | substantive instructions | same core task |
| 83 | openspec-explore / openspec-explore | substantive instructions | same core task |
| 85 | hypothesis-generation / hypothesis-generation | substantive instructions | same core task |
| 88 | slideshow / slideshow | substantive instructions | same core task |
| 96 | canvas-design / canvas-design | substantive instructions | same core task |
| 97 | typescript-advanced-types / typescript-advanced-types | delegating wrapper | same core task |
| 101 | design-image-prompt-engineer / agency-image-prompt-engineer | substantive instructions | same core task |
| 109 | azure-servicebus-dotnet / azure-servicebus-dotnet | substantive instructions | same core task |
| 111 | journal-entry / journal-entry | substantive instructions | same core task |
| 116 | programmatic-seo / programmatic-seo | substantive instructions | same core task |
| 130 | growth-engine / growth-engine | substantive instructions | same core task |
| 132 | frontend-preview / django-verification | delegating wrapper | related tasks different targets |
| 133 | ax-migration-marketplace-integration-lead / ax-migration-audit-binder | generic boilerplate | related tasks different targets |
| 137 | shadcn / shadcn | substantive instructions | same core task |
| 138 | github-issues / github-issues | substantive instructions | same core task |

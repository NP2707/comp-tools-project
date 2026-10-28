Initial orientation notes, checked 28 October 2026. Project: DTU 02807 Computational Tools for Data Science, with the MSR 2027 Mining Challenge as the research setting. This records the initial assessment; see the project README for implementation status.

The [course homepage](https://courses.compute.dtu.dk/02807/2026/) requires groups of 4–5, formed on DTU Learn by 23 October at 23:59. That date has passed; the team's registration status has not been checked.

The [project brief](https://courses.compute.dtu.dk/02807/2026/project/project.pdf) specifies:

- At least one substantial course topic, preferably two, plus an independently learned technique. TF-IDF alone does not count as a course topic.
- Eligible topics: MapReduce, similarity/LSH, frequent itemsets, general clustering, graph clustering.
- Report limit: 11,000 non-whitespace characters; 12,500 for five students.
- Submit through Learn: report, documented Jupyter notebook, reproducibility materials, and individual contributions. Explain decisions and evaluate results; technical substance matters.
- Deadline conflict: front page gives **4 December 2026, 23:59**; page 3 mentions **6 December**. Plan for December 4 pending course clarification.

The [MSR challenge call](https://2027.msrconf.org/track/msr-2027-mining-challenge) permits either dataset below or both. Participation involves submitting a research paper through [HotCRP](https://msr2027-challenge.hotcrp.com/).

| Milestone | Published date |
| --- | --- |
| Abstract | 18 December 2026, AoE |
| Paper | 23 December 2026, AoE |
| Notification | 19 January 2027 |
| Camera-ready | 26 January 2027 |
| Conference in Dublin | 26–27 April 2027 |

MSR requires IEEE format, four pages plus one reference page, anonymous submission, an ethics section, and an explicit dataset version. Reproducible code/data archives are encouraged and required for award eligibility. Accepted papers require an author to register and present. The course report and conference paper therefore need separate preparation.

| Dataset | Contents and practical entry point |
| --- | --- |
| [GitSkills sample](https://github.com/giuseppedestefanis/gitskills-sample) | AI agent instruction files. Full corpus: 3.80 million occurrences and 1.88 million distinct contents. SQLite sample: 29,786 occurrences, 13,000 distinct contents, approximately 277 MB. |
| [SpecMine sample](https://github.com/shyamagarwal13/specmine-official) | Development specifications, structure, histories, and links to code/PRs. Broad corpus: 470,795 specs across 73,030 repositories, plus a separate Kiro collection. A 500-repository sample includes Parquet tables, text, schema, and an example notebook. |

GitSkills retains every occurrence but stores text on one representative per content hash. Its sample preserves complete exact-copy groups. Histories are sampled and follow current paths; filename matches can include unrelated older files. Account for these limitations when defining the population. See the [sample documentation](https://github.com/giuseppedestefanis/gitskills-sample) and [dataset paper](https://arxiv.org/abs/2608.10906).

SpecMine's sample deliberately favors popular and PR-rich repositories, so it is suitable for prototyping but not population estimates. Its README labels the sample v1.1 while also referencing a full v1.0 release: verify versions before combining files. See the [sample documentation](https://github.com/shyamagarwal13/specmine-official) and [linked study](https://arxiv.org/abs/2608.25202).

My preliminary direction is GitSkills: investigate how much reuse appears only after detecting near-duplicates, and whether similarity communities distinguish broad templates from specialized skills. MinHash/LSH could generate candidate pairs, exact similarity could verify them, and graph clustering could identify families. A semantic-embedding comparison is a possible independently learned technique, subject to a focused literature check. Evaluate retrieval against exhaustive comparisons on a small subset, manually inspect sampled pairs, and measure runtime, memory, and sensitivity to thresholds. Similarity alone would not establish who copied whom.

Before implementation: settle the research question, confirm team registration and the course deadline, inspect a sample, and define evaluation criteria and a feasible data scale. These notes record an initial assessment, not experimental findings or a completed challenge registration.

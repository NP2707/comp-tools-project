Purpose clustering of the GitSkills sample

These are provisional interpretations of declared purposes, inferred by the assistant from enriched terms and sampled descriptions. They are not human-validated labels.

Analyzed 11,015 distinct contents in 24 clusters. 1,954 contents lie in explicitly unresolved groups; 42.2% have an assignment margin below 0.05.

| Cluster | Proposed purpose | Contents | Assessment |
| --- | --- | ---: | --- |
| 0 | Mixed purposes / multilingual residual | 1,800 | unresolved |
| 1 | Application development and framework patterns | 719 | broad |
| 2 | Operating apps, messaging and personal tools | 662 | broad |
| 3 | Deployment, cloud infrastructure and operations | 634 | broad |
| 4 | Business strategy, sales and finance | 617 | broad |
| 5 | Requirements, specifications and implementation planning | 586 | focused |
| 6 | Project documentation and repository setup | 576 | broad |
| 7 | Code understanding, quality and refactoring | 458 | broad |
| 8 | Machine learning and scientific analysis | 448 | broad |
| 9 | Git, commits, pull requests and releases | 424 | focused |
| 10 | UI/UX design and design systems | 407 | focused |
| 11 | Data management, databases and pipelines | 399 | broad |
| 12 | Agent orchestration and agent operations | 398 | broad |
| 13 | Code and pull-request review | 390 | focused |
| 14 | Testing, QA and test automation | 363 | focused |
| 15 | API design, integration and gateways | 354 | broad |
| 16 | AI-assisted workflows and generation | 327 | mixed |
| 17 | Debugging, troubleshooting and performance | 314 | focused |
| 18 | Security assessment and hardening | 228 | focused |
| 19 | MCP-based integrations and automation | 219 | broad |
| 20 | Research, discovery and evidence synthesis | 213 | broad |
| 21 | Video, audio and media processing | 165 | focused |
| 22 | German legal, regulatory and professional workflows | 160 | language-influenced |
| 23 | Romance-language mixed purposes | 154 | unresolved |

Representation: name + description TF-IDF contributes 85% and body TF-IDF 15% before 128-dimensional LSA and K-means. The 24-cluster view is an inspection choice. The 12/24/36/48 sweep, seed checks and single-view comparisons are saved alongside this report.

At 24 clusters, cosine silhouette is approximately 0.092 and alternate-seed adjusted Rand scores are approximately 0.39. These indicate weak separation and substantial sensitivity. Margins are geometric diagnostics, not confidence probabilities.

The description-only partition has adjusted Rand agreement 0.443 with the combined view, versus 0.132 for body-only. This is representation sensitivity, not proof that a description contradicts its body.

Of the 649 previously verified lexical-similarity pairs, 275 cross these purpose clusters. Fourteen of 140 lexical families span multiple clusters. Because the purpose assignments are provisional, these are candidates for studying template reuse, not confirmed purpose changes.

Follow-up audit: 255 of the 275 crossing pairs (92.7%) come from one 25-content family. Excluding that family leaves 20/349 crossing pairs. Selected pairs in seven of the 14 crossing families still describe the same core task in assistant static review. These counts cannot be treated as purpose-change prevalence. See [the audit findings](../template-audit/FINDINGS.md).

See docs/purpose-methodology.md and docs/purpose-ideas.md. Human-review fields in purpose_review.csv are empty.

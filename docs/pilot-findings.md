First measured pilot, 28 October 2026. Reproducible artifacts are in [results/sample-4000](../results/sample-4000/RESULTS.md).

- The default population has 11,015 distinct contents representing 26,713 occurrences. Metadata filters excluded 1,784 contents; the minimum body length excluded another 201.
- LSH generated 3,512 of 60,659,605 possible pairs, a 99.9942% candidate reduction. Exact verification retained 649 pairs at Jaccard >= 0.8. Fifty of these have identical shingle sets despite different original byte hashes.
- Exhaustive evaluation over 4,000 independently selected contents checked 7,998,000 possible pairs. At the default threshold/layout, all 122 qualifying pairs were retrieved. This is subset evidence, not a guarantee of complete recall on the full corpus.
- The graph contains 140 communities with at least two contents, involving 362 nodes; 10,653 nodes are isolated. The largest community has 25 contents.
- At resolution 1, Louvain's partition equals the connected components at every evaluated threshold. Consequently this pilot has not yet demonstrated added value from graph clustering. That matters when refining the project's second course topic.
- LSA generated 33,723 neighbour pairs, including 404 of the 649 lexical pairs. Its top-five cap and different similarity definition make this an exploratory comparison, not an accuracy score.
- Total runtime was 54.8 seconds, including exhaustive evaluation and all comparisons; peak process RSS was approximately 2,417 MiB.

One inspected pair, `salary-cap-analyzer` and `beauty-influencer-kit`, has Jaccard approximately 0.928 despite different stated purposes. Their bodies share a generic workflow and output template. This supports investigating template boilerplate, but one pair cannot establish its prevalence. The stratified review queue remains unlabeled for independent group review.

The next useful experiment is a controlled comparison with frontmatter retained, followed by human labeling of template-driven matches and substantive variants. Further graph work should test a representation that captures meaningful relationships beyond disconnected near-duplicate pairs, and compare against connected components explicitly. Larger-scale claims should wait for that validation.

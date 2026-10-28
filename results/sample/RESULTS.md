Prototype run: 11,015 eligible distinct contents, representing 26,713 file occurrences.

LSH proposed 3,512 pairs out of 60,659,605; 649 passed exact 5-word-shingle Jaccard >= 0.8. The graph contains 140 communities of at least two contents and 10,653 isolated contents.

Retrieval recall on 1000 independently sampled documents: 100.0%. See retrieval.csv for true-pair counts, other thresholds, precision, and timing. A zero-positive evaluation produces undefined recall, never a claimed perfect score.

Total runtime: 27.0 seconds; peak process RSS: 2417 MiB. These measurements include evaluation and comparisons.

The LSA comparison and blank, stratified review.csv support follow-up human inspection. Neither similarity nor modularity proves copying or semantic correctness. Community membership is not pairwise similarity: connected chains can join dissimilar endpoints.

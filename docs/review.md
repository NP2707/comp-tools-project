Use `results/sample-4000/review.csv` for a stratified qualitative pilot. Labels are intentionally empty. Preserve the original and have two group members inspect pairs independently before discussing disagreements.

Suggested labels:

- `variant`: substantial shared task-specific instructions, with meaningful edits.
- `format_only`: differences chiefly in formatting, case, or frontmatter.
- `template`: similarity mainly from generic structure or boilerplate.
- `related`: similar purpose without sufficient shared instructions to call it a variant.
- `unrelated`: no convincing relationship.
- `uncertain`: insufficient context or language familiarity.

The notebook provides a read-only pair inspector. Record evidence in `notes`. Labels describe textual relationships, not proven copying. Report reviewer agreement, failure modes, and counts within each stratum. Equally allocated review samples cannot be pooled into an overall precision estimate without weighting for stratum sizes. This pilot does not establish population rates.

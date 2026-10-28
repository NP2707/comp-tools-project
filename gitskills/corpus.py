"""Read distinct contents while retaining occurrence counts for reuse analysis."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
import random
import re
import sqlite3
import unicodedata


@dataclass(frozen=True)
class Skill:
    sha: str
    name: str
    repo: str
    path: str
    text: str
    tokens: tuple[str, ...]
    copies: int
    repos: tuple[str, ...]


def body_tokens(text: str, strip_frontmatter: bool = True) -> tuple[str, ...]:
    """Normalize Unicode/case; retain words, numbers, underscores and code tokens.

    Remove only a delimited YAML block at the beginning. Keep Markdown body and
    code examples; no stopword removal, stemming, or undocumented truncation.
    """
    text = text.lstrip("\ufeff")
    if strip_frontmatter:
        text = re.sub(r"\A---[^\S\r\n]*\r?\n.*?\r?\n(?:---|\.\.\.)[^\S\r\n]*(?:\r?\n|\Z)",
                      "", text, count=1, flags=re.DOTALL)
    return tuple(re.findall(r"\w+", unicodedata.normalize("NFKC", text).casefold()))


def load_corpus(database: Path, *, limit: int = 0, seed: int = 42,
                min_tokens: int = 30, strict: bool = True,
                strip_frontmatter: bool = True) -> tuple[list[Skill], dict]:
    if limit < 0 or min_tokens < 1:
        raise ValueError("limit must be nonnegative and min_tokens positive")
    if not database.is_file():
        raise FileNotFoundError(f"Missing {database}; run scripts/download_sample.py first")
    connection = sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    with connection:
        required = {"file_sha", "dedup_primary", "content", "name", "description",
                    "frontmatter_valid", "filename", "repo_full_name", "path"}
        columns = {r[1] for r in connection.execute("PRAGMA table_info(artifacts)")}
        if not required <= columns:
            raise ValueError(f"Missing artifact columns: {sorted(required - columns)}")
        occurrences: dict[str, list] = {}
        for row in connection.execute("SELECT file_sha, repo_full_name, filename FROM artifacts"):
            group = occurrences.setdefault(row[0], [0, set(), False])
            group[0] += 1
            group[1].add(row[1])
            group[2] |= row[2] == "SKILL.md"
        stats = {"occurrences": sum(g[0] for g in occurrences.values()),
                 "distinct_contents": len(occurrences), "representatives": 0,
                 "excluded_metadata": 0, "excluded_short": 0, "excluded_missing_text": 0}
        skills, seen = [], set()
        for row in connection.execute("SELECT * FROM artifacts WHERE dedup_primary=1 ORDER BY file_sha"):
            stats["representatives"] += 1
            sha, text = row["file_sha"], row["content"]
            if sha in seen:
                raise ValueError(f"Multiple primary rows for {sha}")
            seen.add(sha)
            if not isinstance(text, str) or not text.strip():
                stats["excluded_missing_text"] += 1
                continue
            raw = text.encode("utf-8")
            actual_sha = hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest()
            if actual_sha != sha:
                raise ValueError(f"Content hash mismatch for {sha}")
            copies, repos, has_skill_filename = occurrences[sha]
            if strict and (not has_skill_filename or row["frontmatter_valid"] != 1
                           or not (row["name"] or "").strip()
                           or not (row["description"] or "").strip()):
                stats["excluded_metadata"] += 1
                continue
            tokens = body_tokens(text, strip_frontmatter)
            if len(tokens) < min_tokens:
                stats["excluded_short"] += 1
                continue
            skills.append(Skill(sha, row["name"] or "", row["repo_full_name"],
                                row["path"], text, tokens, copies, tuple(sorted(repos))))
        if seen != set(occurrences):
            raise ValueError("Some content groups have no primary row")
    connection.close()
    stats["eligible_contents"] = len(skills)
    if limit and len(skills) > limit:
        skills = random.Random(seed).sample(skills, limit)
    skills.sort(key=lambda skill: skill.sha)
    stats["selected_contents"] = len(skills)
    stats["selected_occurrences"] = sum(s.copies for s in skills)
    return skills, stats


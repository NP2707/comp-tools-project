import hashlib
from itertools import combinations
import sqlite3

import numpy as np
import pytest

from gitskills.corpus import body_tokens, load_corpus
from gitskills.experiments import cluster_graph, evaluate_retrieval
from gitskills.similarity import jaccard, lsh_candidates, retrieval_metrics, shingles, signatures, verified_edges


def test_preprocessing():
    assert body_tokens("---\r\nname: ignore\r\n---\r\n# ＴＥＳＴ Foo_bar 123") == ("test", "foo_bar", "123")
    assert body_tokens("---\nnot a delimited header") == ("not", "a", "delimited", "header")
    assert body_tokens("---\nname: retain\n---\nbody", False) == ("name", "retain", "body")
    assert shingles(("a", "b", "a", "b"), 2) == {"a\x1fb", "b\x1fa"}


def test_exact_verification_matches_exhaustive_reference():
    documents = [frozenset(), frozenset("abc"), frozenset("abcd"), frozenset("cde"), frozenset("abc")]
    expected = {(i, j): len(documents[i] & documents[j]) / len(documents[i] | documents[j])
                for i, j in combinations(range(len(documents)), 2)
                if documents[i] and documents[j]
                and len(documents[i] & documents[j]) / len(documents[i] | documents[j]) >= 0.5}
    assert verified_edges(documents, combinations(range(len(documents)), 2), 0.5) == expected
    assert jaccard(frozenset(), frozenset()) == 0


def test_minhash_accuracy_and_reproducibility():
    left = frozenset(f"word{i}" for i in range(200))
    right = frozenset(f"word{i}" for i in range(50, 250))
    matrix = signatures([left, right, left], permutations=1024, seed=19)
    assert np.array_equal(matrix[0], matrix[2])
    assert np.array_equal(matrix, signatures([left, right, left], 1024, 19))
    assert abs(np.mean(matrix[0] == matrix[1]) - 0.6) < 0.07


def test_empty_documents_and_candidate_limits():
    docs = [frozenset(), frozenset(), frozenset({"abc"}), frozenset({"abc"})]
    assert lsh_candidates(signatures(docs)) == {(2, 3)}
    with pytest.raises(ValueError):
        lsh_candidates(signatures(docs), bands=7, rows=4)
    with pytest.raises(RuntimeError, match="cap exceeded"):
        lsh_candidates(signatures([frozenset({"a"})] * 5), max_candidates=2)


def test_metrics_expose_false_negatives_and_undefined_recall():
    metrics = retrieval_metrics({(0, 1), (1, 2)}, {(0, 1), (0, 2)}, {(0, 1)}, 3)
    assert metrics["recall"] == 0.5
    assert metrics["candidate_precision"] == 0.5
    assert metrics["verified_precision"] == 1
    assert metrics["missed_true_pairs"] == 1
    assert retrieval_metrics(set(), set(), set(), 0)["recall"] is None


def test_evaluation_truth_is_independent_of_candidates(monkeypatch):
    import gitskills.experiments as experiments
    monkeypatch.setattr(experiments, "lsh_candidates", lambda *args: set())
    rows, ids = evaluate_retrieval([frozenset("abc"), frozenset("abc"), frozenset("xyz")], size=3)
    assert len(ids) == 3
    assert all(r["true_pairs"] == 1 and r["recall"] == 0 and r["missed_true_pairs"] == 1 for r in rows)


def test_graph_retains_isolates_and_separate_families():
    edges = {(0, 1): 0.9, (1, 2): 0.9, (0, 2): 0.9, (3, 4): 0.95}
    graph, groups, stats = cluster_graph(6, edges)
    assert {frozenset(g) for g in groups} == {frozenset({0, 1, 2}), frozenset({3, 4}), frozenset({5})}
    assert stats["isolates"] == 1
    assert graph.number_of_nodes() == 6
    assert cluster_graph(3, {})[2]["modularity"] is None


@pytest.fixture
def database(tmp_path):
    path = tmp_path / "sample.db"
    text = "---\nname: test\ndescription: testing\n---\n" + " ".join(f"token{i}" for i in range(50))
    raw = text.encode()
    sha = hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest()
    with sqlite3.connect(path) as c:
        c.execute("CREATE TABLE artifacts (file_sha TEXT, dedup_primary INTEGER, content TEXT, "
                  "name TEXT, description TEXT, frontmatter_valid INTEGER, filename TEXT, repo_full_name TEXT, path TEXT)")
        c.executemany("INSERT INTO artifacts VALUES (?,?,?,?,?,?,?,?,?)", [
            (sha, 1, text, "test", "testing", 1, "skill.md", "a/repo", "skill.md"),
            (sha, 0, None, None, None, None, "SKILL.md", "b/repo", "SKILL.md"),
        ])
    return path


def test_loader_retains_copies_and_checks_integrity(database):
    skills, stats = load_corpus(database)
    assert len(skills) == 1
    assert skills[0].copies == 2
    assert skills[0].repos == ("a/repo", "b/repo")
    assert stats["selected_occurrences"] == 2
    with sqlite3.connect(database) as c:
        c.execute("UPDATE artifacts SET content='modified' WHERE dedup_primary=1")
    with pytest.raises(ValueError, match="hash mismatch"):
        load_corpus(database)


def test_missing_database_is_not_created(tmp_path):
    missing = tmp_path / "missing.db"
    with pytest.raises(FileNotFoundError):
        load_corpus(missing)
    assert not missing.exists()

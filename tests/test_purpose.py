import numpy as np
import pytest
from scipy import sparse

from gitskills.purpose import aligned_labels, assignment_margins, combine_views, purpose_tokens


def test_weighted_views_have_expected_cosine_contributions():
    # Metadata is identical; body vectors are orthogonal. Combined cosine = w.
    metadata = sparse.csr_matrix([[1., 0.], [1., 0.]])
    body = sparse.csr_matrix([[1., 0.], [0., 1.]])
    matrix = combine_views(metadata, body, 0.85)
    gram = (matrix @ matrix.T).toarray()
    np.testing.assert_allclose(np.diag(gram), [1, 1])
    assert gram[0, 1] == pytest.approx(0.85)
    with pytest.raises(ValueError):
        combine_views(metadata, body, 1.1)


def test_partition_alignment_removes_arbitrary_label_permutations():
    truth = np.array([0, 0, 1, 1, 2, 2])
    alternate = np.array([2, 2, 0, 0, 1, 1])
    np.testing.assert_array_equal(aligned_labels(truth, alternate), truth)


def test_ambiguity_margin_handles_ties_and_coincident_centers():
    np.testing.assert_allclose(assignment_margins(np.array([[2., 1., 3.], [1., 1., 2.], [0., 0., 1.]])), [0.5, 0, 0])


def test_names_split_without_opaque_ids_and_preserve_unicode():
    assert purpose_tokens("u09613-writing_and-test API2 Rechtsschutz") == ["writing", "and", "test", "api2", "rechtsschutz"]

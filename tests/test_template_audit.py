from gitskills.template_audit import instruction_body, normalize


def test_remove_only_metadata_and_first_h1_preserving_operations():
    text = "---\nname: first\n---\n# First\n## Steps\nRead records.\n# Later heading\nDelete records."
    assert instruction_body(text, True) == "## Steps\nRead records.\n# Later heading\nDelete records."


def test_title_normalization_does_not_hide_operational_changes():
    left = "---\nname: first\n---\n# First\nRead customer records."
    renamed = "---\nname: second\n---\n# Second\nRead customer records."
    changed = "---\nname: second\n---\n# Second\nDelete customer records."
    assert normalize(instruction_body(left, True)) == normalize(instruction_body(renamed, True))
    assert normalize(instruction_body(left, True)) != normalize(instruction_body(changed, True))

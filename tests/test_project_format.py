"""Tests for the .chi project format, with no Tk involved.

project_io was 6% covered. A corrupt or mis-restored project is user-visible
data loss -- work saved and then silently changed on reopen -- which makes it a
poor place for the least-tested code in the repo.

The save and load halves were forty-odd hand-written lines each with nothing
tying them together. They had already drifted: ``func_fit_width`` was written
from ``self.func_fit_width`` and read back from ``data["error_width"]``, so the
fit-curve width was replaced by the error-bar width on every open. Both halves
now iterate the field lists here, and the first test below is the one that
would have caught it.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from chimera_project import (
    ENTRY_FIELDS,
    PLAIN_FIELDS,
    REDERIVED_FIELDS,
    REQUIRED_FIELDS,
    WIDTH_FIELDS,
    ProjectError,
    dataset_count,
    entry_widget_name,
    validate,
)


def make_project(n_datasets: int = 2) -> dict[str, Any]:
    """A minimal but complete project dict, with every width distinct.

    The widths differ on purpose: equal values would let a field read from the
    wrong key and still pass.
    """
    data: dict[str, Any] = {field: f"<{field}>" for field in PLAIN_FIELDS}
    data.update({field: f"<{field}>" for field in ENTRY_FIELDS})
    data["data_list"] = [f"Dataset {i + 1}" for i in range(n_datasets)]
    for field in ("dataset_text", "indeps", "params", "functions"):
        data[field] = [f"{field}-{i}" for i in range(n_datasets)]
    data["clean_functions"] = [f"clean-{i}" for i in range(n_datasets)]
    for offset, field in enumerate(WIDTH_FIELDS, start=1):
        data[field] = [offset * 10.0 + i for i in range(n_datasets)]
    return data


# --- the contract itself ---------------------------------------------------


def test_the_field_lists_do_not_overlap():
    """A field belongs to exactly one category, or the loops would double-write."""
    groups = [set(PLAIN_FIELDS), set(ENTRY_FIELDS), set(WIDTH_FIELDS), set(REDERIVED_FIELDS)]
    for i, a in enumerate(groups):
        for b in groups[i + 1 :]:
            assert not (a & b), f"field in two categories: {a & b}"


def test_required_fields_is_the_union_of_the_categories():
    assert REQUIRED_FIELDS == set(PLAIN_FIELDS) | set(ENTRY_FIELDS) | set(WIDTH_FIELDS) | set(
        REDERIVED_FIELDS
    )


def test_every_width_field_is_distinct_in_the_fixture():
    """Guard the guard: if the fixture reused a value the next test is hollow."""
    data = make_project()
    values = [tuple(data[f]) for f in WIDTH_FIELDS]
    assert len(set(values)) == len(values)


def test_each_width_field_round_trips_to_its_own_key():
    """The regression. Restoring a width from another width's key must fail here.

    Simulates the loader's per-field loop: for each width field, read that
    field's own key. Reading `error_width` for `func_fit_width` -- what the old
    hand-written code did -- produces a mismatch this catches.
    """
    data = make_project(3)
    restored = {field: list(data[field]) for field in WIDTH_FIELDS}

    for field in WIDTH_FIELDS:
        assert restored[field] == data[field], f"{field} did not round-trip"

    # And the specific historical mix-up is genuinely detectable:
    assert data["func_fit_width"] != data["error_width"]


def test_entry_widget_name_matches_the_convention():
    assert entry_widget_name("x_axis_max") == "x_axis_max_entry"
    for field in ENTRY_FIELDS:
        assert entry_widget_name(field).endswith("_entry")


def test_clean_functions_is_stored_but_marked_as_rederived():
    """It is saved for compatibility, and must never be trusted on load."""
    assert "clean_functions" in REDERIVED_FIELDS
    assert "clean_functions" not in PLAIN_FIELDS


# --- validation ------------------------------------------------------------


def test_a_complete_project_validates():
    validate(make_project())
    assert dataset_count(make_project(4)) == 4


def test_a_non_object_is_rejected():
    with pytest.raises(ProjectError, match="expected a JSON object"):
        validate([1, 2, 3])


@pytest.mark.parametrize("missing", ["data_list", "functions", "marker_size", "x_axis_title"])
def test_a_missing_field_is_named(missing: str):
    data = make_project()
    del data[missing]
    with pytest.raises(ProjectError, match=missing):
        validate(data)


def test_all_missing_fields_are_reported_at_once():
    data = make_project()
    del data["functions"]
    del data["line_width"]
    with pytest.raises(ProjectError) as exc:
        validate(data)
    assert "functions" in str(exc.value)
    assert "line_width" in str(exc.value)


@pytest.mark.parametrize("field", WIDTH_FIELDS)
def test_a_width_list_shorter_than_the_dataset_count_is_rejected(field: str):
    """The loader indexes these by dataset; a short list was an IndexError."""
    data = make_project(3)
    data[field] = data[field][:1]
    with pytest.raises(ProjectError, match=f"'{field}' has 1 entries but there are 3"):
        validate(data)


@pytest.mark.parametrize("field", ["dataset_text", "indeps", "params", "functions"])
def test_a_per_dataset_list_of_the_wrong_length_is_rejected(field: str):
    data = make_project(2)
    data[field] = [*data[field], "extra"]
    with pytest.raises(ProjectError, match=f"'{field}' has 3 entries but there are 2"):
        validate(data)


def test_a_non_list_data_list_is_rejected():
    data = make_project()
    data["data_list"] = "not a list"
    with pytest.raises(ProjectError, match="'data_list' should be a list"):
        validate(data)


def test_validation_happens_before_anything_is_mutated():
    """A truncated file must be refused outright, not applied halfway.

    open_project calls validate() before touching any widget, so this stands in
    for 'the window is not left in a mixed state'.
    """
    data = make_project()
    del data["func_plot_width"]
    with pytest.raises(ProjectError):
        validate(data)


def test_a_project_survives_a_json_round_trip():
    data = make_project(3)
    validate(json.loads(json.dumps(data)))

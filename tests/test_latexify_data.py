"""Tests for LaTeX table generation from datasets.

This had no coverage, and both of its modes were broken in ways that only show
up in the exported table:

* mode 0 assigned a dataset's y value to whichever Y column happened to come
  first, rather than to that dataset's own column, so any x contributed by a
  later dataset landed under the wrong heading;
* mode 1 was unreachable, because ``export_data_diff_x`` passed mode 0.
"""

import pytest

from chimera_core import latexify_data

# "x y yerr" points.
SET_A = "1 10 0.1\n2 20 0.2\n3 30 0.3"
SET_B = "1 11 0.1\n2 22 0.2\n4 44 0.4"
# "x xerr y yerr" points, the shape the data-entry box produces by default.
SET_XERR = "1 0.5 10 0.1\n2 0.5 20 0.2"


def body(table: str) -> list[str]:
    """The data rows, without the preamble/header/footer boilerplate.

    The closing ``\\hline`` is glued onto the final row, so strip it to compare
    rows uniformly.
    """
    rows = table.split("\\\\ \\hline \n", 1)[1]
    return [line.removesuffix(" \\hline").rstrip() for line in rows.split("\n") if "&" in line]


# --- mode 0: one shared X column -----------------------------------------


def test_shared_x_puts_each_dataset_in_its_own_column():
    """The regression: x=4 exists only in SET_B, so Y1 must be empty, not 44."""
    rows = body(latexify_data([SET_A, SET_B], 0))
    assert rows == [
        "1 & 10$\\pm$0.1 & 11$\\pm$0.1 \\\\",
        "2 & 20$\\pm$0.2 & 22$\\pm$0.2 \\\\",
        "3 & 30$\\pm$0.3 & $-$ \\\\",
        "4 & $-$ & 44$\\pm$0.4 \\\\",
    ]


def test_shared_x_rows_are_sorted_by_x():
    rows = body(latexify_data(["3 30 0.3\n1 10 0.1\n2 20 0.2"], 0))
    assert [row.split(" &")[0] for row in rows] == ["1", "2", "3"]


def test_shared_x_header_has_one_y_column_per_dataset():
    table = latexify_data([SET_A, SET_B], 0)
    assert "X & Y1 & Y2" in table
    assert "\\begin{tabular}{c|cc}" in table


def test_shared_x_single_dataset():
    rows = body(latexify_data([SET_A], 0))
    assert rows == [
        "1 & 10$\\pm$0.1 \\\\",
        "2 & 20$\\pm$0.2 \\\\",
        "3 & 30$\\pm$0.3 \\\\",
    ]


def test_shared_x_carries_the_x_uncertainty():
    rows = body(latexify_data([SET_XERR], 0))
    assert rows[0] == "1$\\pm$0.5 & 10$\\pm$0.1 \\\\"


def test_shared_x_handles_two_identical_datasets():
    """Datasets were compared by value, so identical ones skipped each other."""
    rows = body(latexify_data([SET_A, SET_A], 0))
    assert rows[0] == "1 & 10$\\pm$0.1 & 10$\\pm$0.1 \\\\"
    assert len(rows) == 3


# --- mode 1: an X column per dataset --------------------------------------


def test_per_dataset_x_pairs_columns_by_row_index():
    rows = body(latexify_data([SET_A, SET_B], 1))
    assert rows == [
        "1 & 10$\\pm$0.1 & 1 & 11$\\pm$0.1 \\\\",
        "2 & 20$\\pm$0.2 & 2 & 22$\\pm$0.2 \\\\",
        "3 & 30$\\pm$0.3 & 4 & 44$\\pm$0.4 \\\\",
    ]


def test_per_dataset_x_pads_the_shorter_dataset():
    rows = body(latexify_data([SET_A, "5 55 0.5"], 1))
    assert rows[1].endswith("$-$ & $-$ \\\\")
    assert len(rows) == 3


def test_per_dataset_x_header_pairs_each_x_with_its_y():
    table = latexify_data([SET_A, SET_B], 1)
    assert "X1 & Y1 & X2 & Y2" in table
    assert "\\begin{tabular}{cc|cc}" in table


# --- shared structure -----------------------------------------------------


@pytest.mark.parametrize("mode", [0, 1])
def test_table_is_wrapped_in_the_expected_environment(mode):
    table = latexify_data([SET_A, SET_B], mode)
    assert table.startswith("% Add the following required packages")
    assert "\\begin{table}[H]" in table
    assert table.endswith("\\end{table}")
    assert table.count("\\begin{tabular}") == 1
    assert table.count("\\end{tabular}") == 1


@pytest.mark.parametrize("mode", [-1, 2, 99])
def test_unknown_mode_is_rejected(mode):
    """It used to fall through and raise UnboundLocalError on data_text."""
    with pytest.raises(ValueError, match="unknown table mode"):
        latexify_data([SET_A], mode)


def test_malformed_point_is_reported():
    with pytest.raises(ValueError, match="malformed data point"):
        latexify_data(["1"], 0)

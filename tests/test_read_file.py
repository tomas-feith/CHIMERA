"""Tests for ``main.read_file``, which parses whitespace/character-separated data
into per-dataset point lists. StringIO input is treated as text-format data.
"""

from io import StringIO

from main import read_file


def _sio(text):
    return StringIO(text)


def test_three_columns_no_x_uncertainty():
    # x, y, ey  ->  one dataset of [x, y, ey] points
    result = read_file(_sio("1 2 0.1\n2 4 0.2"), str, False, 0)
    assert result == [[["1", "2", "0.1"], ["2", "4", "0.2"]]]


def test_four_columns_with_x_uncertainty():
    # x, ex, y, ey  ->  one dataset of [x, ex, y, ey] points
    result = read_file(_sio("1 0.1 2 0.2\n2 0.1 4 0.2"), str, False, 0)
    assert result == [[["1", "0.1", "2", "0.2"], ["2", "0.1", "4", "0.2"]]]


def test_mode_true_joins_points_into_text():
    # mode=True collapses each dataset into a single newline-joined string.
    result = read_file(_sio("1 2 0.1\n2 4 0.2"), str, True, 0)
    assert result == ["1 2 0.1\n2 4 0.2"]


def test_semicolon_and_comma_separators_are_accepted():
    result = read_file(_sio("1;2;0.1\n2,4,0.2"), str, False, 0)
    assert result == [[["1", "2", "0.1"], ["2", "4", "0.2"]]]


def test_unknown_extension_returns_error_sentinel():
    assert read_file("data.unknownext", str, False, 0) == -1

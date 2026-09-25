from datetime import date
from decimal import Decimal

from app.grader import compare


def test_order_ignored_when_flag_is_off():
    grade = compare(
        [("b",), ("a",)],
        [("a",), ("b",)],
        ["name"],
        ["name"],
        order_matters=False,
    )
    assert grade.correct


def test_order_required():
    grade = compare(
        [("b",), ("a",)],
        [("a",), ("b",)],
        ["name"],
        ["name"],
        order_matters=True,
    )
    assert not grade.correct
    assert grade.detail == "Row order differs."


def test_nulls_match():
    grade = compare([(None,)], [(None,)], ["arrived_on"], ["arrived_on"], False)
    assert grade.correct


def test_duplicate_rows_are_a_multiset():
    user = [("a",), ("a",), ("b",)]
    expected = [("b",), ("a",), ("a",)]
    assert compare(user, expected, ["name"], ["name"], False).correct
    assert not compare(user, [("a",), ("b",)], ["name"], ["name"], False).correct


def test_column_rename_fails():
    grade = compare([("a",)], [("a",)], ["name"], ["vessel"], False)
    assert not grade.correct
    assert grade.column_match is False
    assert grade.detail == "Column list differs."


def test_column_names_are_case_insensitive():
    grade = compare([("Ada",)], [("Ada",)], ["Name"], ["name"], False)
    assert grade.correct


def test_decimal_scale_does_not_matter():
    grade = compare(
        [(Decimal("2.10"),)],
        [(Decimal("2.1"),)],
        ["avg_days"],
        ["avg_days"],
        False,
    )
    assert grade.correct


def test_dates_match_by_calendar_day():
    grade = compare(
        [(date(2024, 4, 2),)],
        [(date(2024, 4, 2),)],
        ["departed_on"],
        ["departed_on"],
        False,
    )
    assert grade.correct

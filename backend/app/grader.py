from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal


@dataclass(frozen=True)
class Grade:
    correct: bool
    row_count: int
    expected_row_count: int
    column_match: bool
    detail: str


def compare(
    user_rows: list[tuple],
    expected_rows: list[tuple],
    user_columns: list[str],
    expected_columns: list[str],
    order_matters: bool,
) -> Grade:
    row_count = len(user_rows)
    expected_row_count = len(expected_rows)
    if [column.casefold() for column in user_columns] != [
        column.casefold() for column in expected_columns
    ]:
        return Grade(
            False,
            row_count,
            expected_row_count,
            False,
            "Column list differs.",
        )

    user_norm = [_row(row) for row in user_rows]
    expected_norm = [_row(row) for row in expected_rows]
    if order_matters:
        if user_norm == expected_norm:
            return Grade(True, row_count, expected_row_count, True, "That result matches.")
        if sorted(user_norm) == sorted(expected_norm):
            return Grade(False, row_count, expected_row_count, True, "Row order differs.")
        return Grade(False, row_count, expected_row_count, True, "Values differ.")

    if sorted(user_norm) == sorted(expected_norm):
        return Grade(True, row_count, expected_row_count, True, "That result matches.")
    return Grade(False, row_count, expected_row_count, True, "Values differ.")


def _row(row: tuple) -> tuple:
    return tuple(_norm(value) for value in row)


def _norm(value: object) -> tuple:
    if value is None:
        return ("null",)
    if isinstance(value, bool):
        return ("bool", value)
    if isinstance(value, Decimal):
        return ("num", value.normalize())
    if isinstance(value, int):
        return ("num", Decimal(value))
    if isinstance(value, float):
        return ("num", Decimal(str(value)).normalize())
    if isinstance(value, datetime):
        return ("ts", value.isoformat())
    if isinstance(value, date):
        return ("date", value.isoformat())
    return ("str", str(value))

import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

try:
    from app.main import HintBody, SqlBody, check_exercise, hint_exercise, run_exercise
except ModuleNotFoundError as exc:
    if exc.name != "app.query_plan":
        raise
    # The plan module is created separately. Keep this file importable until it lands.
    sys.modules.setdefault("app.query_plan", MagicMock())
    sys.modules.pop("app.main", None)
    from app.main import HintBody, SqlBody, check_exercise, hint_exercise, run_exercise

PLAN = {"steps": ["Seq Scan"], "mermaid": "flowchart TD"}


def _graded(*, correct: bool) -> dict:
    return {
        "columns": ["name"],
        "rows": [["North"]],
        "error": None,
        "correct": correct,
        "row_count": 1,
        "expected_row_count": 1,
        "column_match": True,
        "detail": None,
    }


def test_correct_check_includes_the_patched_plan():
    graded = _graded(correct=True)
    with (
        patch("app.main._exercise_or_404", return_value=object()) as found,
        patch("app.main._grade", return_value=graded) as grade,
        patch("app.main.plan_for_correct_answer", return_value=PLAN) as plan,
    ):
        result = check_exercise("01-newer-vessels", SqlBody(sql="SELECT name FROM vessels"))
    found.assert_called_once_with("01-newer-vessels")
    assert grade.call_args.args[1] == "SELECT name FROM vessels"
    plan.assert_called_once_with(True, "SELECT name FROM vessels")
    assert result["plan"] is PLAN
    assert result["correct"] is True
    assert result["error"] is None


def test_incorrect_check_has_no_plan():
    graded = _graded(correct=False)
    with (
        patch("app.main._exercise_or_404", return_value=object()),
        patch("app.main._grade", return_value=graded),
        patch("app.main.plan_for_correct_answer") as plan,
    ):
        result = check_exercise("01-newer-vessels", SqlBody(sql="SELECT 1"))
    plan.assert_not_called()
    assert "plan" not in result
    assert result["correct"] is False


def test_error_check_has_no_plan():
    graded = {"columns": None, "rows": None, "error": "Only a SELECT is allowed."}
    with (
        patch("app.main._exercise_or_404", return_value=object()),
        patch("app.main._grade", return_value=graded),
        patch("app.main.plan_for_correct_answer") as plan,
    ):
        result = check_exercise("01-newer-vessels", SqlBody(sql="DELETE FROM vessels"))
    plan.assert_not_called()
    assert "plan" not in result
    assert result == graded


def test_correct_hint_has_no_plan():
    graded = _graded(correct=True)
    with (
        patch("app.main._exercise_or_404", return_value=object()),
        patch("app.main._grade", return_value=graded),
        patch("app.main.plan_for_correct_answer") as plan,
    ):
        result = hint_exercise(
            "01-newer-vessels",
            HintBody(sql="SELECT name FROM vessels", level=1),
        )
    plan.assert_not_called()
    assert "plan" not in result
    assert result["note"] == "That result matches."
    assert result["correct"] is True


def test_run_has_no_plan():
    exercise = SimpleNamespace(schema_name="practice")
    with (
        patch("app.main._exercise_or_404", return_value=exercise),
        patch("app.main._prepare"),
        patch("app.main.run_query", return_value=(["name"], [("North",)])),
        patch("app.main.plan_for_correct_answer") as plan,
    ):
        result = run_exercise("01-newer-vessels", SqlBody(sql="SELECT name FROM vessels"))
    plan.assert_not_called()
    assert "plan" not in result
    assert result["error"] is None
    assert result["columns"] == ["name"]
    assert result["rows"] == [["North"]]

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
FRAMES = [{"op": "from", "columns": ["name"], "rows": [["North"]]}]


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
    exercise = SimpleNamespace(schema_name="practice")
    with (
        patch("app.main._exercise_or_404", return_value=exercise) as found,
        patch("app.main._grade", return_value=graded) as grade,
        patch("app.main.plan_for_correct_answer", return_value=PLAN) as plan,
        patch("app.main.illustrate_query", return_value=FRAMES) as illustrate,
    ):
        result = check_exercise("01-newer-vessels", SqlBody(sql="SELECT name FROM vessels"))
    found.assert_called_once_with("01-newer-vessels")
    assert grade.call_args.args[1] == "SELECT name FROM vessels"
    plan.assert_called_once_with(True, "SELECT name FROM vessels")
    illustrate.assert_called_once()
    sql, execute = illustrate.call_args.args
    assert sql == "SELECT name FROM vessels"
    with patch("app.main.run_query", return_value=(["name"], [("North",)])) as queried:
        assert execute("SELECT name FROM vessels") == (["name"], [("North",)])
    queried.assert_called_once_with("SELECT name FROM vessels", "practice")
    assert result["plan"] is PLAN
    assert result["plan"]["frames"] == FRAMES
    assert result["correct"] is True
    assert result["error"] is None


def test_illustrate_failure_keeps_plan_with_empty_frames():
    graded = _graded(correct=True)
    plan_body = dict(PLAN)
    with (
        patch("app.main._exercise_or_404", return_value=SimpleNamespace(schema_name="practice")),
        patch("app.main._grade", return_value=graded),
        patch("app.main.plan_for_correct_answer", return_value=plan_body),
        patch("app.main.illustrate_query", side_effect=RuntimeError("illustrate failed")),
    ):
        result = check_exercise("01-newer-vessels", SqlBody(sql="SELECT name FROM vessels"))
    assert result["plan"] is plan_body
    assert result["plan"]["frames"] == []
    assert result["correct"] is True


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

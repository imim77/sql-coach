import pytest

from app.coach import ask_coach
from app.exercises import Exercise

FALLBACK = (
    "Say what you want the result to include, and which table it comes from. "
    "I will not write the query."
)


def _exercise() -> Exercise:
    return Exercise(
        id="newer-vessels",
        title="Newer vessels",
        prompt="List vessel names built after 2010.",
        concepts=["filter"],
        order_matters=False,
        reference_sql="SELECT name FROM vessels WHERE year_built > 2010",
        hints=["Think about the year.", "Filter the vessels table.", "Compare year_built."],
        schema_text="vessels(id, name, year_built)",
    )


def test_blank_question_raises():
    exercise = _exercise()
    with pytest.raises(ValueError, match="Ask a question first."):
        ask_coach(exercise, "SELECT id FROM ports", "   ")
    with pytest.raises(ValueError, match="Ask a question first."):
        ask_coach(exercise, "", "")


def test_missing_key_uses_notes(monkeypatch):
    def explode(instructions, payload):
        raise AssertionError("model should not be called")

    monkeypatch.setattr("app.coach.OPENAI_API_KEY", "")
    monkeypatch.setattr("app.coach._model_answer", explode)
    result = ask_coach(_exercise(), "SELECT id FROM ports", "Which table has the names?")
    assert result["source"] == "notes"
    assert result["answer"] == FALLBACK
    assert "SELECT" not in result["answer"]


def test_leaked_select_is_replaced(monkeypatch):
    seen = {}

    def leak(instructions, payload):
        seen["instructions"] = instructions
        seen["payload"] = payload
        return "SELECT name FROM vessels"

    monkeypatch.setattr("app.coach.OPENAI_API_KEY", "test-key")
    monkeypatch.setattr("app.coach._model_answer", leak)
    exercise = _exercise()
    result = ask_coach(exercise, "SELECT id FROM ports", "Which rows should stay?")
    assert result["source"] == "notes"
    assert result["answer"] == FALLBACK
    assert "SELECT" not in result["answer"]
    assert exercise.reference_sql not in seen["payload"]
    assert exercise.title in seen["payload"]
    assert exercise.prompt in seen["payload"]
    assert exercise.schema_text in seen["payload"]
    assert "SELECT id FROM ports" in seen["payload"]
    assert "Which rows should stay?" in seen["payload"]


def test_clean_model_answer_is_coach(monkeypatch):
    monkeypatch.setattr("app.coach.OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(
        "app.coach._model_answer",
        lambda instructions, payload: "Start from the vessels table and keep the later years.",
    )
    result = ask_coach(_exercise(), "SELECT id FROM ports", "Where do I start?")
    assert result == {
        "answer": "Start from the vessels table and keep the later years.",
        "source": "coach",
    }

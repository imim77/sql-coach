import pytest

from app.lesson_gen import FALLBACKS, LessonError, next_identity, spec_from_payload
from app.exercises import Exercise


def test_fallback_lesson_is_valid():
    exercise = spec_from_payload(FALLBACKS[0], "lesson-01", "lesson_01")
    assert exercise.dataset == "Corner bakery"
    assert exercise.table_names == ("products", "orders")
    assert "Column names and column order" in exercise.prompt


def test_bad_table_name_is_rejected():
    payload = {
        **FALLBACKS[0],
        "tables": [
            {**FALLBACKS[0]["tables"][0], "name": "Products"},
            FALLBACKS[0]["tables"][1],
        ],
    }
    with pytest.raises(LessonError, match="table name"):
        spec_from_payload(payload, "lesson-01", "lesson_01")


def test_next_identity_counts_generated_lessons():
    existing = [
        Exercise(
            id="newer-vessels",
            title="Newer vessels",
            prompt="List names.",
            concepts=["filter"],
            order_matters=False,
            reference_sql="SELECT name FROM vessels",
            hints=["a", "b", "c"],
        ),
        Exercise(
            id="lesson-02",
            title="Bread",
            prompt="Count.",
            concepts=["join"],
            order_matters=False,
            reference_sql="SELECT 1",
            hints=["a", "b", "c"],
        ),
    ]
    assert next_identity(existing) == ("lesson-03", "lesson_03")


def test_installed_fallback_matches_its_reference():
    from app.db import ping, run_query, schema_preview
    from app.grader import compare
    from app.lesson_gen import _drop_schema, install_exercise

    if not ping():
        pytest.skip("database is down")
    exercise = spec_from_payload(FALLBACKS[0], "lesson-99", "lesson_99")
    try:
        install_exercise(exercise)
        columns, rows = run_query(exercise.reference_sql, "lesson_99")
        assert compare(rows, rows, columns, columns, False).correct
        assert {row[0] for row in rows} == {"rye", "bun", "cake"}
        preview = schema_preview("lesson_99", ["products", "orders"])
        assert preview[0]["name"] == "products"
        assert len(preview[0]["sample_rows"]) == 3
    finally:
        _drop_schema("lesson_99")

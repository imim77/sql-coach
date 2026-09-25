import pytest

from app.exercises import load_exercises
from app.sql_guard import QueryRejected, prepare_statement


def test_trailing_semicolon_is_one_statement():
    assert prepare_statement("SELECT name FROM ports;") == "SELECT name FROM ports"


def test_second_statement_is_rejected():
    with pytest.raises(QueryRejected, match="one SELECT"):
        prepare_statement("SELECT 1; SELECT 2")


def test_semicolon_inside_a_string_is_kept():
    sql = "SELECT name FROM ports WHERE name = 'a;b'"
    assert prepare_statement(sql) == sql


def test_only_select_or_with():
    with pytest.raises(QueryRejected, match="Only a SELECT"):
        prepare_statement("DELETE FROM ports")


def test_comment_before_select_is_allowed():
    prepare_statement("-- draft\nSELECT 1")


def test_reference_queries_pass_the_guard():
    exercises = load_exercises()
    assert len(exercises) == 10
    for exercise in exercises:
        prepare_statement(exercise.reference_sql)
        assert len(exercise.hints) == 3


def test_coach_leak_pattern_flags_a_query():
    from app.coach import LEAK

    assert LEAK.search("```sql")
    assert LEAK.search("SELECT name FROM vessels")
    assert not LEAK.search("Keep only the later builds.")


def test_public_summary_hides_the_solution():
    from app.exercises import summary

    public = summary(load_exercises()[0])
    assert "reference_sql" not in public
    assert "hints" not in public

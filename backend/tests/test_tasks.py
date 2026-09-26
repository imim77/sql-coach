import json
import sqlite3

import pytest
from fastapi import HTTPException

from app import catalog
from app.db import DatabaseUnavailable
from app.main import TaskBody, create_task
from app.sql_guard import QueryRejected
from app.tasks import TaskError, accept_task, load_tasks, save_task, task_from_payload

VALID = {
    "id": "flagged-vessels",
    "title": "Flagged vessels",
    "prompt": "List the name of every vessel. Return one column named name.",
    "concepts": ["filter"],
    "order_matters": False,
    "reference_sql": "SELECT name FROM vessels",
    "hints": [
        "The vessels table has a name column.",
        "Return that column for every row.",
        "Do not filter the rows.",
    ],
}


def _drop(exercise_id: str) -> None:
    with catalog._lock:
        catalog._exercises[:] = [item for item in catalog._exercises if item.id != exercise_id]


def _rows(db_path) -> list[dict]:
    if not db_path.exists():
        return []
    connection = sqlite3.connect(db_path)
    try:
        connection.row_factory = sqlite3.Row
        fetched = connection.execute(
            """
            SELECT id, title, prompt, concepts, order_matters, reference_sql, hints, position
            FROM tasks
            ORDER BY position
            """
        ).fetchall()
        return [dict(row) for row in fetched]
    finally:
        connection.close()


def test_task_from_payload_uses_the_practice_schema():
    exercise = task_from_payload(VALID)
    assert exercise.dataset == "Northline"
    assert exercise.schema_name == "practice"
    assert exercise.concepts == ["filter"]
    assert exercise.order_matters is False
    assert exercise.reference_sql == "SELECT name FROM vessels"
    assert exercise.table_names == ()


def test_trailing_semicolon_is_stripped_from_the_reference():
    exercise = task_from_payload({**VALID, "reference_sql": "SELECT name FROM vessels;"})
    assert exercise.reference_sql == "SELECT name FROM vessels"


def test_prompt_may_say_selection_but_not_select():
    exercise = task_from_payload(
        {**VALID, "prompt": "Return a selection of vessel names in a column named name."}
    )
    assert "selection" in exercise.prompt
    with pytest.raises(TaskError, match="contains a query"):
        task_from_payload({**VALID, "prompt": "SELECT name FROM vessels"})


def test_id_must_be_a_slug_and_lesson_ids_are_reserved():
    for exercise_id in ("Flagged", "a-", "a--b", "a" * 41):
        with pytest.raises(TaskError, match="lowercase slug"):
            task_from_payload({**VALID, "id": exercise_id})
    with pytest.raises(TaskError, match="reserved"):
        task_from_payload({**VALID, "id": "lesson-01"})


def test_hints_need_three_notes_without_a_query():
    with pytest.raises(TaskError, match="exactly 3 hints"):
        task_from_payload({**VALID, "hints": VALID["hints"][:2]})
    with pytest.raises(TaskError, match="contains a query"):
        task_from_payload({**VALID, "hints": [*VALID["hints"][:2], "SELECT name FROM vessels"]})


def test_order_matters_defaults_to_false_and_rejects_strings():
    payload = dict(VALID)
    del payload["order_matters"]
    assert task_from_payload(payload).order_matters is False
    with pytest.raises(TaskError, match="true or false"):
        task_from_payload({**VALID, "order_matters": "yes"})


def test_reference_must_be_one_select():
    with pytest.raises(TaskError, match="Only a SELECT"):
        task_from_payload({**VALID, "reference_sql": "DELETE FROM vessels"})


def test_concepts_accept_a_join_name_and_reject_an_empty_list():
    exercise = task_from_payload({**VALID, "concepts": ["semi-join"]})
    assert exercise.concepts == ["semi-join"]
    with pytest.raises(TaskError, match="one to three"):
        task_from_payload({**VALID, "concepts": []})


def test_save_and_load_roundtrip_keeps_creation_order(tmp_path):
    db_path = tmp_path / "tasks.sqlite"
    save_task(task_from_payload(VALID), db_path)
    save_task(task_from_payload({**VALID, "id": "idle-flags"}), db_path)
    rows = _rows(db_path)
    assert [row["id"] for row in rows] == ["flagged-vessels", "idle-flags"]
    assert [row["position"] for row in rows] == [1, 2]
    assert json.loads(rows[0]["concepts"]) == ["filter"]
    assert json.loads(rows[0]["hints"]) == VALID["hints"]
    assert rows[0]["reference_sql"] == VALID["reference_sql"]
    assert rows[0]["order_matters"] == 0
    loaded = load_tasks(db_path)
    assert [item.id for item in loaded] == ["flagged-vessels", "idle-flags"]
    assert loaded[0].prompt == VALID["prompt"]
    assert loaded[0].hints == VALID["hints"]
    assert loaded[0].schema_name == "practice"
    assert loaded[0].dataset == "Northline"
    assert list(tmp_path.glob("*.yaml")) == []
    assert list(tmp_path.glob("*.json")) == []
    with pytest.raises(TaskError, match="already exists"):
        save_task(task_from_payload(VALID), db_path)
    assert [row["id"] for row in _rows(db_path)] == ["flagged-vessels", "idle-flags"]


def test_accept_task_saves_after_the_reference_runs(tmp_path):
    seen = {}

    def execute(sql, schema):
        seen["sql"] = sql
        seen["schema"] = schema
        return (["name"], [("North",)])

    db_path = tmp_path / "tasks.sqlite"
    exercise = accept_task(VALID, set(), execute, db_path)
    assert seen == {"sql": "SELECT name FROM vessels", "schema": "practice"}
    assert load_tasks(db_path)[0].id == exercise.id
    assert _rows(db_path)[0]["reference_sql"] == "SELECT name FROM vessels"


def test_accept_task_does_not_save_a_rejected_reference(tmp_path):
    def execute(sql, schema):
        raise QueryRejected('column "nope" does not exist')

    db_path = tmp_path / "tasks.sqlite"
    with pytest.raises(TaskError, match="does not exist"):
        accept_task(VALID, set(), execute, db_path)
    assert _rows(db_path) == []


def test_accept_task_leaves_database_errors_alone(tmp_path):
    def execute(sql, schema):
        raise DatabaseUnavailable("Database is not reachable.")

    db_path = tmp_path / "tasks.sqlite"
    with pytest.raises(DatabaseUnavailable):
        accept_task(VALID, set(), execute, db_path)
    assert _rows(db_path) == []


def test_accept_task_runs_against_practice_when_the_database_is_up(tmp_path):
    from app.db import ping, run_query

    if not ping():
        pytest.skip("database is down")
    db_path = tmp_path / "tasks.sqlite"
    exercise = accept_task(VALID, set(), run_query, db_path)
    assert exercise.schema_name == "practice"
    assert load_tasks(db_path)[0].reference_sql == "SELECT name FROM vessels"


def test_duplicate_known_id_skips_execution(tmp_path):
    def execute(sql, schema):
        raise AssertionError("should not run")

    db_path = tmp_path / "tasks.sqlite"
    with pytest.raises(TaskError, match="already exists"):
        accept_task(VALID, {"flagged-vessels"}, execute, db_path)
    assert _rows(db_path) == []


def test_duplicate_stored_id_skips_execution(tmp_path):
    db_path = tmp_path / "tasks.sqlite"
    save_task(task_from_payload(VALID), db_path)

    def execute(sql, schema):
        raise AssertionError("should not run")

    with pytest.raises(TaskError, match="already exists"):
        accept_task(VALID, set(), execute, db_path)
    assert [row["id"] for row in _rows(db_path)] == ["flagged-vessels"]


def test_legacy_yaml_imports_once_in_filename_order(tmp_path, monkeypatch):
    db_path = tmp_path / "tasks.sqlite"
    empty = tmp_path / "empty"
    legacy = tmp_path / "legacy"
    empty.mkdir()
    legacy.mkdir()
    monkeypatch.setattr("app.tasks.TASKS_DIR", empty)
    save_task(task_from_payload({**VALID, "title": "Already stored"}), db_path)

    def write(name: str, exercise_id: str, title: str) -> None:
        (legacy / name).write_text(
            f"""\
id: {exercise_id}
title: {title}
prompt: List the name of every vessel. Return one column named name.
concepts:
- filter
order_matters: false
reference_sql: SELECT name FROM vessels
hints:
- The vessels table has a name column.
- Return that column for every row.
- Do not filter the rows.
"""
        )

    write("10-later-flags.yaml", "later-flags", "Later flags")
    write("2-idle-flags.yaml", "idle-flags", "Idle flags")
    write("1-flagged-vessels.yaml", "flagged-vessels", "Flagged vessels")
    (legacy / "notes.yaml").write_text("not a task\n")
    before = {path.name: path.read_bytes() for path in legacy.iterdir()}
    monkeypatch.setattr("app.tasks.TASKS_DIR", legacy)

    loaded = load_tasks(db_path)
    assert [(item.id, item.title) for item in loaded] == [
        ("flagged-vessels", "Already stored"),
        ("idle-flags", "Idle flags"),
        ("later-flags", "Later flags"),
    ]
    save_task(task_from_payload({**VALID, "id": "extra-flags", "title": "Extra flags"}), db_path)
    assert [item.id for item in load_tasks(db_path)] == [
        "flagged-vessels",
        "idle-flags",
        "later-flags",
        "extra-flags",
    ]
    assert {path.name: path.read_bytes() for path in legacy.iterdir()} == before
    assert list(tmp_path.glob("*.yaml")) == []
    assert list(tmp_path.glob("*.json")) == []


def test_endpoint_creates_a_task_without_returning_the_reference(monkeypatch, tmp_path):
    db_path = tmp_path / "tasks.sqlite"
    monkeypatch.setattr("app.tasks.TASKS_DB", db_path)
    monkeypatch.setattr(
        "app.main.run_query",
        lambda sql, schema: (["name"], [("North",)]),
    )
    try:
        result = create_task(TaskBody(**VALID))
        assert result["id"] == "flagged-vessels"
        assert result["dataset"] == "Northline"
        assert "reference_sql" not in result
        rows = _rows(db_path)
        assert [row["id"] for row in rows] == ["flagged-vessels"]
        assert rows[0]["reference_sql"] == "SELECT name FROM vessels"
        assert json.loads(rows[0]["concepts"]) == ["filter"]
        assert json.loads(rows[0]["hints"]) == VALID["hints"]
    finally:
        _drop("flagged-vessels")


def test_endpoint_rejects_a_bundled_id_without_running_sql(monkeypatch):
    def fail(sql, schema):
        raise AssertionError("should not run")

    monkeypatch.setattr("app.main.run_query", fail)
    body = TaskBody(**{**VALID, "id": "newer-vessels"})
    with pytest.raises(HTTPException) as caught:
        create_task(body)
    assert caught.value.status_code == 409


def test_endpoint_rejects_a_hint_that_contains_a_query():
    body = TaskBody(**{**VALID, "hints": [*VALID["hints"][:2], "SELECT name FROM vessels"]})
    with pytest.raises(HTTPException) as caught:
        create_task(body)
    assert caught.value.status_code == 422
    assert caught.value.detail == "A hint contains a query."


def test_endpoint_reports_a_database_outage(monkeypatch):
    def down(sql, schema):
        raise DatabaseUnavailable("Database is not reachable.")

    monkeypatch.setattr("app.main.run_query", down)
    body = TaskBody(**{**VALID, "id": "offline-vessels"})
    with pytest.raises(HTTPException) as caught:
        create_task(body)
    assert caught.value.status_code == 503
    assert all(item.id != "offline-vessels" for item in catalog.list_exercises())


def test_add_exercise_slots_before_generated_lessons():
    exercise = task_from_payload({**VALID, "id": "catalog-slot"})
    try:
        catalog.add_exercise(exercise)
        rows = catalog.list_exercises()
        practice = [item.id for item in rows if item.schema_name == "practice"]
        assert practice[-1] == "catalog-slot"
        later = [item for item in rows if item.schema_name != "practice"]
        if later:
            assert rows.index(exercise) < rows.index(later[0])
        with pytest.raises(ValueError, match="already exists"):
            catalog.add_exercise(exercise)
    finally:
        _drop("catalog-slot")

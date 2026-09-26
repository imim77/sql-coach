import json
import re
import sqlite3
from contextlib import contextmanager
from pathlib import Path

import yaml

from app.config import TASKS_DB, TASKS_DIR
from app.exercises import Exercise
from app.sql_guard import QueryRejected, prepare_statement

ID_RE = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
CONCEPT_RE = re.compile(r"^[a-z][a-z0-9-]{0,23}$")
QUERY_LEAK = re.compile(r"```|\bselect\b", re.IGNORECASE)
_YAML_NUMBER = re.compile(r"^(\d+)-.+\.yaml$")
_SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    prompt TEXT NOT NULL,
    concepts TEXT NOT NULL,
    order_matters INTEGER NOT NULL,
    reference_sql TEXT NOT NULL,
    hints TEXT NOT NULL,
    position INTEGER NOT NULL UNIQUE
)
"""


class TaskError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def task_from_payload(data: dict) -> Exercise:
    if not isinstance(data, dict):
        raise TaskError("Task was not an object.")
    exercise_id = _id(data.get("id"))
    title = _bounded(data.get("title"), "Title is required.", "Title is too long.", 80)
    prompt = _bounded(data.get("prompt"), "Prompt is required.", "Prompt is too long.", 800)
    if QUERY_LEAK.search(prompt):
        raise TaskError("The prompt contains a query.")
    return Exercise(
        id=exercise_id,
        title=title,
        prompt=prompt,
        concepts=_concepts(data.get("concepts")),
        order_matters=_order_matters(data),
        reference_sql=_reference(data.get("reference_sql")),
        hints=_hints(data.get("hints")),
        schema_name="practice",
        dataset="Northline",
        schema_text="",
        table_names=(),
        tables=(),
    )


def save_task(exercise: Exercise, db_path: Path | None = None) -> None:
    with _session(db_path) as connection:
        if _has_id(connection, exercise.id):
            raise TaskError("A task with this id already exists.")
        _insert(connection, exercise)


def load_tasks(db_path: Path | None = None) -> list[Exercise]:
    with _session(db_path) as connection:
        rows = connection.execute(
            """
            SELECT id, title, prompt, concepts, order_matters, reference_sql, hints
            FROM tasks
            ORDER BY position
            """
        ).fetchall()
        return [_exercise_from_row(row) for row in rows]


def accept_task(
    data: dict,
    known_ids: set[str],
    execute,
    db_path: Path | None = None,
) -> Exercise:
    exercise = task_from_payload(data)
    if exercise.id in known_ids or _stored(exercise.id, db_path):
        raise TaskError("A task with this id already exists.")
    try:
        execute(exercise.reference_sql, "practice")
    except QueryRejected as exc:
        raise TaskError(exc.message) from exc
    save_task(exercise, db_path)
    return exercise


def _id(value: object) -> str:
    if not isinstance(value, str) or not ID_RE.fullmatch(value) or len(value) > 40:
        raise TaskError("Id must be a lowercase slug.")
    if value.startswith("lesson-"):
        raise TaskError("Id is reserved.")
    return value


def _bounded(value: object, missing: str, too_long: str, limit: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TaskError(missing)
    text = value.strip()
    if len(text) > limit:
        raise TaskError(too_long)
    return text


def _concepts(value: object) -> list[str]:
    if not isinstance(value, list) or not 1 <= len(value) <= 3:
        raise TaskError("Concepts must be one to three short names.")
    names: list[str] = []
    for item in value:
        if not isinstance(item, str) or not CONCEPT_RE.fullmatch(item.strip()):
            raise TaskError("Concepts must be one to three short names.")
        names.append(item.strip())
    return names


def _order_matters(data: dict) -> bool:
    if "order_matters" not in data:
        return False
    value = data["order_matters"]
    if not isinstance(value, bool):
        raise TaskError("order_matters must be true or false.")
    return value


def _reference(value: object) -> str:
    text = _bounded(value, "Reference SQL is required.", "Reference SQL is too long.", 2000)
    try:
        return prepare_statement(text)
    except QueryRejected as exc:
        raise TaskError(exc.message) from exc


def _hints(value: object) -> list[str]:
    if not isinstance(value, list) or len(value) != 3:
        raise TaskError("A task needs exactly 3 hints.")
    hints: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise TaskError("A task needs exactly 3 hints.")
        text = item.strip()
        if len(text) > 400:
            raise TaskError("Hint is too long.")
        if QUERY_LEAK.search(text):
            raise TaskError("A hint contains a query.")
        hints.append(text)
    return hints


def _stored(exercise_id: str, db_path: Path | None) -> bool:
    with _session(db_path) as connection:
        return _has_id(connection, exercise_id)


def _has_id(connection: sqlite3.Connection, exercise_id: str) -> bool:
    row = connection.execute(
        "SELECT 1 FROM tasks WHERE id = ?",
        (exercise_id,),
    ).fetchone()
    return row is not None


def _insert(connection: sqlite3.Connection, exercise: Exercise) -> None:
    position = connection.execute(
        "SELECT COALESCE(MAX(position), 0) + 1 FROM tasks"
    ).fetchone()[0]
    connection.execute(
        """
        INSERT INTO tasks (
            id, title, prompt, concepts, order_matters, reference_sql, hints, position
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            exercise.id,
            exercise.title,
            exercise.prompt,
            json.dumps(exercise.concepts, ensure_ascii=False),
            1 if exercise.order_matters else 0,
            exercise.reference_sql,
            json.dumps(exercise.hints, ensure_ascii=False),
            position,
        ),
    )


def _exercise_from_row(row: sqlite3.Row) -> Exercise:
    return Exercise(
        id=row["id"],
        title=row["title"],
        prompt=row["prompt"],
        concepts=list(json.loads(row["concepts"])),
        order_matters=bool(row["order_matters"]),
        reference_sql=row["reference_sql"],
        hints=list(json.loads(row["hints"])),
        schema_name="practice",
        dataset="Northline",
        schema_text="",
        table_names=(),
        tables=(),
    )


def _resolve(db_path: Path | None) -> Path:
    if db_path is None:
        return Path(TASKS_DB)
    return Path(db_path)


@contextmanager
def _session(db_path: Path | None):
    connection = _connect(_resolve(db_path))
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def _connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    try:
        connection.row_factory = sqlite3.Row
        connection.execute(_SCHEMA)
        _import_yaml(connection)
        connection.commit()
    except Exception:
        connection.close()
        raise
    return connection


def _import_yaml(connection: sqlite3.Connection) -> None:
    # Legacy YAML stays on disk; each missing id is copied once, in filename order.
    directory = Path(TASKS_DIR)
    if not directory.exists():
        return
    existing = {row["id"] for row in connection.execute("SELECT id FROM tasks")}
    for path in _numbered_yaml(directory):
        payload = yaml.safe_load(path.read_text())
        if isinstance(payload, dict) and payload.get("id") in existing:
            continue
        exercise = task_from_payload(payload)
        if exercise.id in existing:
            continue
        _insert(connection, exercise)
        existing.add(exercise.id)


def _numbered_yaml(directory: Path) -> list[Path]:
    numbered: list[tuple[int, str, Path]] = []
    for path in directory.glob("*.yaml"):
        match = _YAML_NUMBER.fullmatch(path.name)
        if match:
            numbered.append((int(match.group(1)), path.name, path))
    numbered.sort()
    return [path for _number, _name, path in numbered]

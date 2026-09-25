import re
from pathlib import Path

import yaml

from app.config import TASKS_DIR
from app.exercises import Exercise
from app.sql_guard import QueryRejected, prepare_statement

ID_RE = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
CONCEPT_RE = re.compile(r"^[a-z][a-z0-9-]{0,23}$")
QUERY_LEAK = re.compile(r"```|\bselect\b", re.IGNORECASE)
FILE_ID = re.compile(r"\d+-(.+)\.yaml")
FILE_NUMBER = re.compile(r"^(\d+)-")


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


def save_task(exercise: Exercise, directory: Path | None = None) -> Path:
    directory = TASKS_DIR if directory is None else directory
    directory.mkdir(parents=True, exist_ok=True)
    if exercise.id in _ids_on_disk(directory):
        raise TaskError("A task with this id already exists.")
    path = directory / f"{_next_number(directory):04d}-{exercise.id}.yaml"
    payload = {
        "id": exercise.id,
        "title": exercise.title,
        "concepts": exercise.concepts,
        "order_matters": exercise.order_matters,
        "prompt": exercise.prompt,
        "reference_sql": exercise.reference_sql,
        "hints": exercise.hints,
    }
    path.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=True))
    return path


def load_tasks(directory: Path | None = None) -> list[Exercise]:
    directory = TASKS_DIR if directory is None else directory
    if not directory.exists():
        return []
    exercises: list[Exercise] = []
    seen: set[str] = set()
    for path in sorted(directory.glob("*.yaml")):
        exercise = task_from_payload(yaml.safe_load(path.read_text()))
        if exercise.id in seen:
            raise TaskError(f"Duplicate task id {exercise.id}")
        seen.add(exercise.id)
        exercises.append(exercise)
    return exercises


def accept_task(
    data: dict,
    known_ids: set[str],
    execute,
    directory: Path | None = None,
) -> Exercise:
    exercise = task_from_payload(data)
    folder = TASKS_DIR if directory is None else directory
    if exercise.id in known_ids or exercise.id in _ids_on_disk(folder):
        raise TaskError("A task with this id already exists.")
    try:
        execute(exercise.reference_sql, "practice")
    except QueryRejected as exc:
        raise TaskError(exc.message) from exc
    save_task(exercise, folder)
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


def _ids_on_disk(directory: Path) -> set[str]:
    if not directory.exists():
        return set()
    found: set[str] = set()
    for path in directory.glob("*.yaml"):
        match = FILE_ID.fullmatch(path.name)
        if match:
            found.add(match.group(1))
    return found


def _next_number(directory: Path) -> int:
    numbers: list[int] = []
    for path in directory.glob("*.yaml"):
        match = FILE_NUMBER.match(path.name)
        if match:
            numbers.append(int(match.group(1)))
    return max(numbers, default=0) + 1

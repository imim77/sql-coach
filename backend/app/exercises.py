from dataclasses import dataclass
from pathlib import Path

import yaml

from app.config import EXERCISES_DIR


@dataclass(frozen=True)
class Exercise:
    id: str
    title: str
    prompt: str
    concepts: list[str]
    order_matters: bool
    reference_sql: str
    hints: list[str]
    schema_name: str = "practice"
    dataset: str = "Northline"
    schema_text: str = ""
    table_names: tuple[str, ...] = ()
    tables: tuple[dict, ...] = ()


def load_exercises(directory: Path = EXERCISES_DIR) -> list[Exercise]:
    files = sorted(directory.glob("*.yaml"))
    if not files:
        raise FileNotFoundError(f"No exercises in {directory}")

    exercises: list[Exercise] = []
    seen: set[str] = set()
    for file in files:
        data = yaml.safe_load(file.read_text())
        exercise_id = str(data["id"])
        if exercise_id in seen:
            raise ValueError(f"Duplicate exercise id {exercise_id}")
        seen.add(exercise_id)
        hints = list(data["hints"])
        if len(hints) != 3:
            raise ValueError(f"{file.name} needs exactly 3 hints")
        exercises.append(
            Exercise(
                id=exercise_id,
                title=str(data["title"]),
                prompt=str(data["prompt"]).strip(),
                concepts=[str(concept) for concept in data["concepts"]],
                order_matters=bool(data["order_matters"]),
                reference_sql=str(data["reference_sql"]).strip(),
                hints=[str(hint).strip() for hint in hints],
            )
        )
    return exercises


def summary(exercise: Exercise) -> dict:
    return {
        "id": exercise.id,
        "title": exercise.title,
        "concepts": exercise.concepts,
        "dataset": exercise.dataset,
    }


def detail(exercise: Exercise, schema: list[dict]) -> dict:
    return {
        **summary(exercise),
        "prompt": exercise.prompt,
        "schema": schema,
    }

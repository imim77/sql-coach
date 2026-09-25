import threading

from app.exercises import Exercise, load_exercises, summary
from app.lesson_gen import LessonError, build_next, ensure_installed, load_generated, save_exercise

_lock = threading.Lock()
_gen_lock = threading.Lock()
_exercises: list[Exercise] = []


def init() -> None:
    loaded = load_exercises() + load_generated()
    with _lock:
        _exercises[:] = loaded
    for exercise in loaded:
        if exercise.schema_name == "practice":
            continue
        try:
            ensure_installed(exercise)
        except LessonError:
            continue


def list_exercises() -> list[Exercise]:
    with _lock:
        return list(_exercises)


def get(exercise_id: str) -> Exercise | None:
    with _lock:
        for exercise in _exercises:
            if exercise.id == exercise_id:
                return exercise
    return None


def summaries() -> list[dict]:
    return [summary(exercise) for exercise in list_exercises()]


def continue_after(exercise_id: str) -> list[dict]:
    with _gen_lock:
        with _lock:
            if not _exercises or _exercises[-1].id != exercise_id:
                return [summary(exercise) for exercise in _exercises]
            existing = list(_exercises)
        exercise = build_next(existing)
        save_exercise(exercise)
        with _lock:
            if _exercises and _exercises[-1].id == exercise_id:
                _exercises.append(exercise)
            return [summary(item) for item in _exercises]


init()

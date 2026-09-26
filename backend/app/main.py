import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.catalog import (
    add_exercise,
    continue_after,
    get,
    list_exercises as catalog_exercises,
    summaries,
)
from app.coach import ask_coach, coach_note
from app.config import OPENAI_API_KEY, STUDENT_DATABASE_URL
from app.db import DatabaseUnavailable, json_row, ping, run_query, schema_preview
from app.exercises import detail, summary
from app.grader import compare
from app.lesson_gen import LessonError, ensure_installed
from app.query_plan import illustrate_query, plan_for_correct_answer
from app.referenced_tables import referenced_tables
from app.sql_guard import QueryRejected
from app.tasks import TaskError, accept_task

app = FastAPI(title="SQL Coach")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_schema_cache: dict[tuple[str, tuple[str, ...]], list[dict]] = {}


class SqlBody(BaseModel):
    sql: str


class HintBody(BaseModel):
    sql: str
    level: int = Field(ge=1, le=3)


class ContinueBody(BaseModel):
    after_id: str


class TaskBody(BaseModel):
    id: str
    title: str
    prompt: str
    concepts: list[str]
    order_matters: bool = False
    reference_sql: str
    hints: list[str]


def _exercise_or_404(exercise_id: str):
    exercise = get(exercise_id)
    if exercise is None:
        raise HTTPException(status_code=404, detail="Exercise not found.")
    return exercise


def _prepare(exercise):
    try:
        ensure_installed(exercise)
    except LessonError as exc:
        raise HTTPException(status_code=500, detail=exc.message) from exc


def _schema(exercise) -> list[dict]:
    names = exercise.table_names or referenced_tables(exercise.reference_sql)
    if not names:
        # Not cached. A schema-wide entry would be served for a later narrower list.
        try:
            return schema_preview(exercise.schema_name, None)
        except DatabaseUnavailable as exc:
            raise HTTPException(status_code=503, detail=exc.message) from exc

    key = (exercise.schema_name, tuple(names))
    cached = _schema_cache.get(key)
    if cached is not None:
        return cached
    try:
        preview = schema_preview(exercise.schema_name, list(names))
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail=exc.message) from exc
    _schema_cache[key] = preview
    return preview


def _grade(exercise, sql: str) -> dict:
    _prepare(exercise)
    try:
        columns, rows = run_query(sql, exercise.schema_name)
    except QueryRejected as exc:
        return {"columns": None, "rows": None, "error": exc.message}
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail=exc.message) from exc

    try:
        expected_columns, expected_rows = run_query(
            exercise.reference_sql,
            exercise.schema_name,
        )
    except QueryRejected as exc:
        raise HTTPException(status_code=500, detail="This exercise is misconfigured.") from exc
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail=exc.message) from exc

    grade = compare(
        rows,
        expected_rows,
        columns,
        expected_columns,
        exercise.order_matters,
    )
    return {
        "columns": columns,
        "rows": [json_row(row) for row in rows],
        "error": None,
        "correct": grade.correct,
        "row_count": grade.row_count,
        "expected_row_count": grade.expected_row_count,
        "column_match": grade.column_match,
        "detail": grade.detail,
    }


@app.get("/api/health")
def health():
    return {
        "database": ping() and ping(STUDENT_DATABASE_URL),
        "coach": bool(OPENAI_API_KEY),
    }


@app.get("/api/exercises")
def list_exercises():
    return summaries()


@app.post("/api/tasks", status_code=201)
def create_task(body: TaskBody):
    try:
        exercise = accept_task(
            body.model_dump(),
            {item.id for item in catalog_exercises()},
            run_query,
        )
    except TaskError as exc:
        status = 409 if exc.message == "A task with this id already exists." else 422
        raise HTTPException(status_code=status, detail=exc.message) from exc
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail=exc.message) from exc
    add_exercise(exercise)
    return summary(exercise)


@app.post("/api/exercises/continue")
def continue_exercises(body: ContinueBody):
    try:
        return continue_after(body.after_id)
    except LessonError as exc:
        raise HTTPException(status_code=502, detail=exc.message) from exc


@app.get("/api/exercises/{exercise_id}")
def get_exercise(exercise_id: str):
    exercise = _exercise_or_404(exercise_id)
    _prepare(exercise)
    return detail(exercise, _schema(exercise))


@app.post("/api/exercises/{exercise_id}/run")
def run_exercise(exercise_id: str, body: SqlBody):
    exercise = _exercise_or_404(exercise_id)
    _prepare(exercise)
    try:
        columns, rows = run_query(body.sql, exercise.schema_name)
    except QueryRejected as exc:
        return {"columns": None, "rows": None, "error": exc.message}
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail=exc.message) from exc
    return {
        "columns": columns,
        "rows": [json_row(row) for row in rows],
        "error": None,
    }


@app.post("/api/exercises/{exercise_id}/check")
def check_exercise(exercise_id: str, body: SqlBody):
    exercise = _exercise_or_404(exercise_id)
    outcome = _grade(exercise, body.sql)
    if outcome.get("error"):
        return outcome
    if outcome.get("correct") is not True:
        return outcome
    outcome["plan"] = plan_for_correct_answer(True, body.sql)
    plan = outcome["plan"]
    try:
        plan["frames"] = illustrate_query(
            body.sql,
            lambda statement: run_query(statement, exercise.schema_name),
        )
    except Exception:
        plan["frames"] = []
    return outcome


@app.post("/api/exercises/{exercise_id}/hint")
def hint_exercise(exercise_id: str, body: HintBody):
    exercise = _exercise_or_404(exercise_id)
    outcome = _grade(exercise, body.sql)
    if outcome.get("error"):
        diff = f"Postgres error: {outcome['error']}"
    elif outcome["correct"]:
        return {
            **outcome,
            "note": "That result matches.",
            "level": body.level,
            "source": "notes",
        }
    else:
        diff = (
            f"columns_match={outcome['column_match']}; "
            f"user_rows={outcome['row_count']}; "
            f"expected_rows={outcome['expected_row_count']}; "
            f"detail={outcome['detail']}"
        )
    note = coach_note(exercise, body.sql, body.level, diff)
    return {**outcome, **note}


@app.post("/api/exercises/{exercise_id}/solution")
def show_solution(exercise_id: str):
    exercise = _exercise_or_404(exercise_id)
    return {"reference_sql": exercise.reference_sql}


class AskBody(BaseModel):
    sql: str = ""
    question: str


@app.post("/api/exercises/{exercise_id}/ask")
def ask_exercise(exercise_id: str, body: AskBody):
    exercise = _exercise_or_404(exercise_id)
    try:
        return ask_coach(exercise, body.sql, body.question)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Ask a question first.") from exc


def mount_frontend(application: FastAPI, directory: Path) -> None:
    # Registered last so /api routes keep priority over the page files.
    application.mount("/", StaticFiles(directory=directory, html=True), name="frontend")


_static_dir = os.getenv("STATIC_DIR", "").strip()
if _static_dir:
    _static_path = Path(_static_dir)
    if not _static_path.is_dir():
        raise RuntimeError(f"STATIC_DIR does not exist: {_static_path}")
    mount_frontend(app, _static_path)

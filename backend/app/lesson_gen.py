import json
import re
from datetime import date
from decimal import Decimal, InvalidOperation

import psycopg
import yaml
from psycopg import sql

from app.config import DATABASE_URL, GENERATED_DIR, OPENAI_API_KEY, OPENAI_MODEL
from app.db import SCHEMA_TEXT, run_query
from app.exercises import Exercise
from app.sql_guard import QueryRejected, prepare_statement

IDENT = re.compile(r"^[a-z][a-z0-9_]{0,30}$")
TYPES = {
    "integer": "integer",
    "text": "text",
    "boolean": "boolean",
    "numeric": "numeric",
    "date": "date",
}
RESERVED = {
    "select",
    "from",
    "where",
    "table",
    "user",
    "order",
    "group",
    "join",
    "on",
    "and",
    "or",
}

LESSON_INSTRUCTIONS = """You write one PostgreSQL practice exercise as a single JSON object.
Invent a new everyday domain. Do not use shipping, ports, vessels, voyages, cargo, or crew.
Do not repeat a domain you are given.
The exercise must need at least one join.
Keys: title, domain, prompt, concepts, order_matters, tables, reference_sql, hints.
tables is 2 or 3 items. Each item has name, columns, and rows.
columns is a list of {name, type}. type is one of integer, text, boolean, numeric, date.
The first column of every table is id integer. 4 to 8 rows per table. Ids used in joins must exist.
prompt names every output column in lowercase and says whether row order matters. It does not contain a query.
reference_sql is one SELECT using unqualified table names. Aliases match the prompt. It returns 1 to 15 rows.
hints is exactly 3 short strings with no SELECT keyword and no code fence.
order_matters is true only when the prompt requires a sort.
concepts is 1 to 3 of: filter, order, join, group, aggregate, anti-join, subquery, window, case, dates.
"""


class LessonError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def spec_from_payload(data: dict, exercise_id: str, schema_name: str) -> Exercise:
    if not isinstance(data, dict):
        raise LessonError("Lesson was not an object.")
    title = _text(data.get("title"), "title", 80)
    domain = _text(data.get("domain") or data.get("dataset"), "domain", 40)
    prompt = _text(data.get("prompt"), "prompt", 800)
    if "select" in prompt.lower() or "```" in prompt:
        raise LessonError("The prompt contains a query.")
    concepts = data.get("concepts")
    if not isinstance(concepts, list) or not 1 <= len(concepts) <= 3:
        raise LessonError("Concepts must be a short list.")
    concept_names = [_text(concept, "concept", 24) for concept in concepts]
    order_matters = data.get("order_matters")
    if not isinstance(order_matters, bool):
        raise LessonError("order_matters must be true or false.")
    tables = _tables(data.get("tables"))
    reference_sql = _text(data.get("reference_sql"), "reference_sql", 2000)
    try:
        prepare_statement(reference_sql)
    except QueryRejected as exc:
        raise LessonError(exc.message) from exc
    hints_raw = data.get("hints")
    if not isinstance(hints_raw, list) or len(hints_raw) != 3:
        raise LessonError("A lesson needs exactly 3 hints.")
    hints = []
    for hint in hints_raw:
        text = _text(hint, "hint", 400)
        if re.search(r"```|\bselect\b", text, re.IGNORECASE):
            raise LessonError("A hint contains a query.")
        hints.append(text)
    names = tuple(table["name"] for table in tables)
    schema_text = _schema_text(tables)
    suffix = "Column names and column order are part of the answer."
    if suffix not in prompt:
        prompt = prompt.rstrip() + "\n" + suffix
    return Exercise(
        id=exercise_id,
        title=title,
        prompt=prompt,
        concepts=concept_names,
        order_matters=order_matters,
        reference_sql=reference_sql,
        hints=hints,
        schema_name=schema_name,
        dataset=domain,
        schema_text=schema_text,
        table_names=names,
        tables=tuple(tables),
    )


def install_exercise(exercise: Exercise) -> None:
    if not exercise.tables or not exercise.schema_name.startswith("lesson_"):
        raise LessonError("This lesson has no tables to install.")
    schema_name = exercise.schema_name
    try:
        with psycopg.connect(DATABASE_URL, connect_timeout=5, application_name="sqlcoach") as conn:
            with conn.cursor() as cur:
                cur.execute(
                    sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(schema_name))
                )
                cur.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema_name)))
                for table in exercise.tables:
                    _create_table(cur, schema_name, table)
                    _insert_rows(cur, schema_name, table)
                cur.execute(
                    sql.SQL("GRANT USAGE ON SCHEMA {} TO student").format(sql.Identifier(schema_name))
                )
                cur.execute(
                    sql.SQL("GRANT SELECT ON ALL TABLES IN SCHEMA {} TO student").format(
                        sql.Identifier(schema_name)
                    )
                )
    except psycopg.OperationalError as exc:
        raise LessonError("Database is not reachable.") from exc
    except psycopg.Error as exc:
        _drop_schema(schema_name)
        message = exc.diag.message_primary if exc.diag and exc.diag.message_primary else str(exc)
        raise LessonError(message) from exc

    try:
        _columns, rows = run_query(exercise.reference_sql, schema_name)
    except QueryRejected as exc:
        _drop_schema(schema_name)
        raise LessonError(exc.message) from exc
    if not 1 <= len(rows) <= 15:
        _drop_schema(schema_name)
        raise LessonError("The reference query must return between 1 and 15 rows.")


def schema_exists(schema_name: str) -> bool:
    try:
        with psycopg.connect(DATABASE_URL, connect_timeout=5, application_name="sqlcoach") as conn:
            row = conn.execute(
                "SELECT 1 FROM information_schema.schemata WHERE schema_name = %s",
                (schema_name,),
            ).fetchone()
        return row is not None
    except psycopg.OperationalError as exc:
        raise LessonError("Database is not reachable.") from exc


def ensure_installed(exercise: Exercise) -> None:
    if exercise.schema_name == "practice":
        return
    if schema_exists(exercise.schema_name):
        return
    install_exercise(exercise)


def save_exercise(exercise: Exercise) -> None:
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    path = GENERATED_DIR / f"{exercise.id}.yaml"
    payload = {
        "id": exercise.id,
        "title": exercise.title,
        "dataset": exercise.dataset,
        "schema_name": exercise.schema_name,
        "schema_text": exercise.schema_text,
        "concepts": exercise.concepts,
        "order_matters": exercise.order_matters,
        "prompt": exercise.prompt,
        "reference_sql": exercise.reference_sql,
        "hints": exercise.hints,
        "tables": list(exercise.tables),
    }
    path.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=True))


def load_generated() -> list[Exercise]:
    if not GENERATED_DIR.exists():
        return []
    exercises: list[Exercise] = []
    for path in sorted(GENERATED_DIR.glob("*.yaml")):
        data = yaml.safe_load(path.read_text())
        exercises.append(
            spec_from_payload(data, str(data["id"]), str(data["schema_name"]))
        )
    return exercises


def next_identity(existing: list[Exercise]) -> tuple[str, str]:
    numbers = []
    for exercise in existing:
        match = re.fullmatch(r"lesson-(\d+)", exercise.id)
        if match:
            numbers.append(int(match.group(1)))
    number = max(numbers, default=0) + 1
    return f"lesson-{number:02d}", f"lesson_{number:02d}"


def build_next(existing: list[Exercise]) -> Exercise:
    exercise_id, schema_name = next_identity(existing)
    errors: list[str] = []
    if OPENAI_API_KEY:
        for _attempt in range(2):
            try:
                payload = _ask_model(existing, errors)
                exercise = spec_from_payload(payload, exercise_id, schema_name)
                install_exercise(exercise)
                return exercise
            except (LessonError, json.JSONDecodeError, QueryRejected) as exc:
                errors.append(str(exc))
                _drop_schema(schema_name)
    for payload in FALLBACKS:
        if any(exercise.dataset == payload["domain"] for exercise in existing):
            continue
        exercise = spec_from_payload(payload, exercise_id, schema_name)
        install_exercise(exercise)
        return exercise
    if errors:
        raise LessonError(errors[-1])
    raise LessonError("No further saved lesson is available. Set OPENAI_API_KEY to write more.")


def practice_schema_text() -> str:
    return SCHEMA_TEXT


def _ask_model(existing: list[Exercise], errors: list[str]) -> dict:
    from openai import OpenAI

    finished = "\n".join(
        f"- {exercise.dataset}: {exercise.title}" for exercise in existing
    )
    correction = ""
    if errors:
        correction = "\nThe previous attempt failed: " + errors[-1] + "\nReturn corrected JSON only."
    client = OpenAI(api_key=OPENAI_API_KEY, timeout=90)
    response = client.responses.create(
        model=OPENAI_MODEL,
        instructions=LESSON_INSTRUCTIONS,
        reasoning={"effort": "low"},
        max_output_tokens=4000,
        input=f"Lessons already written:\n{finished}{correction}",
    )
    return _parse_json(response.output_text or "")


def _parse_json(text: str) -> dict:
    body = text.strip()
    if body.startswith("```"):
        body = re.sub(r"^```(?:json)?", "", body).strip()
        body = re.sub(r"```$", "", body).strip()
    start = body.find("{")
    end = body.rfind("}")
    if start < 0 or end < start:
        raise LessonError("The model did not return JSON.")
    parsed = json.loads(body[start : end + 1])
    if not isinstance(parsed, dict):
        raise LessonError("The model did not return an object.")
    return parsed


def _tables(value: object) -> list[dict]:
    if not isinstance(value, list) or not 2 <= len(value) <= 3:
        raise LessonError("A lesson needs 2 or 3 tables.")
    tables = []
    seen: set[str] = set()
    for table in value:
        if not isinstance(table, dict):
            raise LessonError("A table was not an object.")
        name = _ident(table.get("name"), "table")
        if name in seen:
            raise LessonError(f"Duplicate table {name}.")
        seen.add(name)
        columns = _columns(table.get("columns"))
        rows = _rows(table.get("rows"), columns)
        tables.append({"name": name, "columns": columns, "rows": rows})
    return tables


def _columns(value: object) -> list[dict]:
    if not isinstance(value, list) or not 2 <= len(value) <= 6:
        raise LessonError("Each table needs 2 to 6 columns.")
    columns = []
    seen: set[str] = set()
    for column in value:
        if not isinstance(column, dict):
            raise LessonError("A column was not an object.")
        name = _ident(column.get("name"), "column")
        if name in seen:
            raise LessonError(f"Duplicate column {name}.")
        seen.add(name)
        column_type = str(column.get("type", "")).lower()
        if column_type not in TYPES:
            raise LessonError(f"Unsupported type for {name}.")
        columns.append({"name": name, "type": column_type})
    if columns[0]["name"] != "id" or columns[0]["type"] != "integer":
        raise LessonError("The first column must be id integer.")
    return columns


def _rows(value: object, columns: list[dict]) -> list[list]:
    if not isinstance(value, list) or not 4 <= len(value) <= 8:
        raise LessonError("Each table needs 4 to 8 rows.")
    rows = []
    seen_ids: set[int] = set()
    for raw in value:
        if not isinstance(raw, list) or len(raw) != len(columns):
            raise LessonError("A row does not match its columns.")
        row = [_coerce(cell, column) for cell, column in zip(raw, columns, strict=True)]
        row_id = row[0]
        if not isinstance(row_id, int) or row_id in seen_ids:
            raise LessonError("Each id must be a unique integer.")
        seen_ids.add(row_id)
        rows.append(row)
    return rows


def _coerce(value: object, column: dict):
    if value is None:
        if column["name"] == "id":
            raise LessonError("id cannot be null.")
        return None
    column_type = column["type"]
    if column_type == "integer":
        if isinstance(value, bool):
            raise LessonError(f"{column['name']} must be an integer.")
        if isinstance(value, float) and value.is_integer():
            return int(value)
        if not isinstance(value, int):
            raise LessonError(f"{column['name']} must be an integer.")
        return value
    if column_type == "text":
        if not isinstance(value, str) or not value.strip() or len(value) > 80:
            raise LessonError(f"{column['name']} must be short text.")
        return value
    if column_type == "boolean":
        if not isinstance(value, bool):
            raise LessonError(f"{column['name']} must be true or false.")
        return value
    if column_type == "numeric":
        try:
            return format(Decimal(str(value)), "f")
        except (InvalidOperation, ValueError) as exc:
            raise LessonError(f"{column['name']} must be a number.") from exc
    if not isinstance(value, str):
        raise LessonError(f"{column['name']} must be a date.")
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise LessonError(f"{column['name']} must be a YYYY-MM-DD date.") from exc
    return value


def _create_table(cur, schema_name: str, table: dict) -> None:
    pieces = []
    for column in table["columns"]:
        piece = sql.SQL("{} {}").format(
            sql.Identifier(column["name"]),
            sql.SQL(TYPES[column["type"]]),
        )
        if column["name"] == "id":
            piece = piece + sql.SQL(" PRIMARY KEY")
        pieces.append(piece)
    cur.execute(
        sql.SQL("CREATE TABLE {} ({})").format(
            sql.Identifier(schema_name, table["name"]),
            sql.SQL(", ").join(pieces),
        )
    )


def _insert_rows(cur, schema_name: str, table: dict) -> None:
    columns = table["columns"]
    statement = sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
        sql.Identifier(schema_name, table["name"]),
        sql.SQL(", ").join(sql.Identifier(column["name"]) for column in columns),
        sql.SQL(", ").join(sql.Placeholder() for _ in columns),
    )
    cur.executemany(statement, table["rows"])


def _drop_schema(schema_name: str) -> None:
    if not schema_name.startswith("lesson_"):
        return
    try:
        with psycopg.connect(DATABASE_URL, connect_timeout=5, application_name="sqlcoach") as conn:
            conn.execute(
                sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(schema_name))
            )
    except psycopg.Error:
        return


def _schema_text(tables: list[dict]) -> str:
    lines = []
    for table in tables:
        columns = ", ".join(f"{column['name']} {column['type']}" for column in table["columns"])
        lines.append(f"{table['name']}({columns})")
    return "\n".join(lines)


def _ident(value: object, kind: str) -> str:
    if not isinstance(value, str) or not IDENT.fullmatch(value) or value in RESERVED:
        raise LessonError(f"Invalid {kind} name.")
    return value


def _text(value: object, label: str, limit: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise LessonError(f"{label} is missing.")
    text = value.strip()
    if len(text) > limit:
        raise LessonError(f"{label} is too long.")
    return text


FALLBACKS = [
    {
        "title": "Bread sold",
        "domain": "Corner bakery",
        "concepts": ["join", "aggregate"],
        "order_matters": False,
        "prompt": (
            "For each product that has been ordered, return its name and the total quantity sold. "
            "Return name and units."
        ),
        "reference_sql": (
            "SELECT p.name, SUM(o.quantity) AS units\n"
            "FROM orders AS o\n"
            "JOIN products AS p ON p.id = o.product_id\n"
            "GROUP BY p.id, p.name"
        ),
        "hints": [
            "Quantity lives on orders. The product name lives on products.",
            "Join orders to products, then sum quantity per product.",
            "Name the sum units. Group by the product.",
        ],
        "tables": [
            {
                "name": "products",
                "columns": [
                    {"name": "id", "type": "integer"},
                    {"name": "name", "type": "text"},
                    {"name": "price", "type": "numeric"},
                ],
                "rows": [[1, "rye", "4.50"], [2, "bun", "2.00"], [3, "cake", "18.00"], [4, "loaf", "3.50"]],
            },
            {
                "name": "orders",
                "columns": [
                    {"name": "id", "type": "integer"},
                    {"name": "product_id", "type": "integer"},
                    {"name": "quantity", "type": "integer"},
                    {"name": "ordered_on", "type": "date"},
                ],
                "rows": [
                    [1, 1, 3, "2024-05-01"],
                    [2, 1, 2, "2024-05-02"],
                    [3, 2, 4, "2024-05-02"],
                    [4, 3, 1, "2024-05-03"],
                ],
            },
        ],
    },
    {
        "title": "Unreturned books",
        "domain": "Town library",
        "concepts": ["join", "filter"],
        "order_matters": False,
        "prompt": (
            "Return the title of every book that is currently on loan. "
            "A loan with no return date is still out. Return title."
        ),
        "reference_sql": (
            "SELECT books.title\n"
            "FROM loans\n"
            "JOIN books ON books.id = loans.book_id\n"
            "WHERE loans.returned_on IS NULL"
        ),
        "hints": [
            "A missing return date means the book is still out.",
            "Join loans to books and keep rows where returned_on is null.",
            "Return only the book title.",
        ],
        "tables": [
            {
                "name": "books",
                "columns": [
                    {"name": "id", "type": "integer"},
                    {"name": "title", "type": "text"},
                    {"name": "author", "type": "text"},
                ],
                "rows": [
                    [1, "Harbour Light", "Ness"],
                    [2, "Kiln", "Adeyemi"],
                    [3, "Paper Birds", "Cho"],
                    [4, "Salt Maps", "Ibarra"],
                ],
            },
            {
                "name": "loans",
                "columns": [
                    {"name": "id", "type": "integer"},
                    {"name": "book_id", "type": "integer"},
                    {"name": "member", "type": "text"},
                    {"name": "returned_on", "type": "date"},
                ],
                "rows": [
                    [1, 1, "Ada", None],
                    [2, 2, "Bo", "2024-06-02"],
                    [3, 3, "Cleo", None],
                    [4, 1, "Dan", "2024-06-11"],
                ],
            },
        ],
    },
    {
        "title": "Repeat visits",
        "domain": "Hill clinic",
        "concepts": ["group"],
        "order_matters": True,
        "prompt": (
            "Return each patient name and how many visits they have, sorted by name. "
            "Return name and visits. Row order is part of the answer."
        ),
        "reference_sql": (
            "SELECT patients.name, COUNT(visits.id) AS visits\n"
            "FROM patients\n"
            "LEFT JOIN visits ON visits.patient_id = patients.id\n"
            "GROUP BY patients.id, patients.name\n"
            "ORDER BY patients.name"
        ),
        "hints": [
            "Every patient should appear, even one with no visit.",
            "Left join visits, count visit ids, and sort by patient name.",
            "Name the count visits. Row order is graded.",
        ],
        "tables": [
            {
                "name": "patients",
                "columns": [
                    {"name": "id", "type": "integer"},
                    {"name": "name", "type": "text"},
                ],
                "rows": [[1, "Amir"], [2, "Bea"], [3, "Chen"], [4, "Dalia"]],
            },
            {
                "name": "visits",
                "columns": [
                    {"name": "id", "type": "integer"},
                    {"name": "patient_id", "type": "integer"},
                    {"name": "reason", "type": "text"},
                    {"name": "visited_on", "type": "date"},
                ],
                "rows": [
                    [1, 1, "check", "2024-04-01"],
                    [2, 1, "followup", "2024-04-20"],
                    [3, 3, "check", "2024-05-02"],
                    [4, 2, "labs", "2024-05-09"],
                ],
            },
        ],
    },
]

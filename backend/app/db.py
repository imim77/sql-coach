import re
from datetime import date, datetime
from decimal import Decimal

import psycopg
from psycopg import sql

from app.config import DATABASE_URL, ROW_LIMIT, STUDENT_DATABASE_URL
from app.sql_guard import QueryRejected, prepare_statement

SCHEMA_NAME = re.compile(r"^(practice|lesson_[0-9]+)$")

TABLES = ("ports", "vessels", "voyages", "cargo", "crew")

SCHEMA_TEXT = """
ports(id, name, country, latitude)
vessels(id, name, vessel_type, year_built, home_port_id)
voyages(id, vessel_id, departed_on, arrived_on, origin_port_id, destination_port_id)
cargo(id, voyage_id, description, weight_tons, hazardous)
crew(id, name, role, vessel_id)
voyages.arrived_on is null while a voyage is still at sea.
""".strip()


class DatabaseUnavailable(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def ping(dsn: str = DATABASE_URL) -> bool:
    try:
        with psycopg.connect(dsn, connect_timeout=3, application_name="sqlcoach") as conn:
            conn.execute("SELECT 1")
        return True
    except psycopg.Error:
        return False


def run_query(statement_sql: str, schema: str = "practice") -> tuple[list[str], list[tuple]]:
    if not SCHEMA_NAME.fullmatch(schema):
        raise QueryRejected("Unknown schema.")
    statement = prepare_statement(statement_sql)
    try:
        with psycopg.connect(
            STUDENT_DATABASE_URL,
            connect_timeout=5,
            application_name="sqlcoach",
        ) as conn:
            with conn.cursor() as cur:
                cur.execute("SET LOCAL statement_timeout = '3s'")
                cur.execute("SET LOCAL default_transaction_read_only = on")
                cur.execute(sql.SQL("SET LOCAL search_path TO {}").format(sql.Identifier(schema)))
                cur.execute(statement)
                if cur.description is None:
                    raise QueryRejected("That query did not return a table.")
                columns = [column.name for column in cur.description]
                rows = cur.fetchmany(ROW_LIMIT + 1)
                if len(rows) > ROW_LIMIT:
                    raise QueryRejected(
                        f"Result is larger than {ROW_LIMIT} rows. Narrow the query."
                    )
                return columns, rows
    except QueryRejected:
        raise
    except psycopg.errors.QueryCanceled as exc:
        raise QueryRejected(
            "Query timed out after 3 seconds. Narrow the result or simplify the statement."
        ) from exc
    except psycopg.errors.ReadOnlySqlTransaction as exc:
        raise QueryRejected(
            "That statement would change the database. Only a SELECT is allowed."
        ) from exc
    except psycopg.OperationalError as exc:
        raise DatabaseUnavailable("Database is not reachable.") from exc
    except psycopg.Error as exc:
        message = exc.diag.message_primary if exc.diag and exc.diag.message_primary else str(exc)
        raise QueryRejected(message) from exc


def schema_preview(schema: str = "practice", table_names: list[str] | None = None) -> list[dict]:
    if not SCHEMA_NAME.fullmatch(schema):
        raise QueryRejected("Unknown schema.")
    names = table_names or list(TABLES)
    try:
        with psycopg.connect(
            STUDENT_DATABASE_URL,
            connect_timeout=5,
            application_name="sqlcoach",
        ) as conn:
            with conn.cursor() as cur:
                tables: list[dict] = []
                for table in names:
                    cur.execute(
                        """
                        SELECT column_name, data_type, is_nullable
                        FROM information_schema.columns
                        WHERE table_schema = %s AND table_name = %s
                        ORDER BY ordinal_position
                        """,
                        (schema, table),
                    )
                    columns = [
                        {
                            "name": name,
                            "data_type": data_type,
                            "nullable": nullable == "YES",
                        }
                        for name, data_type, nullable in cur.fetchall()
                    ]
                    cur.execute(
                        sql.SQL("SELECT * FROM {} ORDER BY id LIMIT 3").format(
                            sql.Identifier(schema, table)
                        )
                    )
                    sample_columns = [column.name for column in cur.description]
                    sample_rows = [json_row(row) for row in cur.fetchall()]
                    tables.append(
                        {
                            "name": table,
                            "columns": columns,
                            "sample_columns": sample_columns,
                            "sample_rows": sample_rows,
                        }
                    )
                return tables
    except psycopg.OperationalError as exc:
        raise DatabaseUnavailable("Database is not reachable.") from exc


def json_row(row: tuple) -> list:
    return [json_value(value) for value in row]


def json_value(value: object):
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return value
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return str(value)

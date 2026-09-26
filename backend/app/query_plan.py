import re
from datetime import date, datetime
from decimal import Decimal

_KEYWORD = re.compile(
    r"\b(SELECT|FROM|WHERE|GROUP\s+BY|HAVING|ORDER\s+BY|LIMIT|"
    r"(?:LEFT|RIGHT|FULL|CROSS|INNER)?\s*JOIN)\b",
    re.IGNORECASE,
)
_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def plan_for_correct_answer(correct: bool, sql: str) -> dict | None:
    if not correct:
        return None
    return explain_query(sql)


def explain_query(sql: str) -> dict:
    clauses = _clauses(sql)
    steps = _steps(clauses)
    return {"steps": steps, "mermaid": _mermaid(steps)}


def illustrate_query(sql: str, execute) -> list[dict]:
    """execute(statement: str) -> tuple[list[str], list[tuple]]
    One frame per explain_query step, same order.
    """
    clauses = _clauses(sql)
    steps = explain_query(sql)["steps"]
    from_text = next((text for label, text in clauses if label == "FROM"), "")
    join_texts = [text for label, text in clauses if label.endswith("JOIN")]
    where_text = next((text for label, text in clauses if label == "WHERE"), "")
    limit_text = next((text for label, text in clauses if label == "LIMIT"), "")
    frames: list[dict] = []
    seen_joins = 0
    carried_count: int | None = None
    carried_columns: list[str] = []
    carried_rows: list[list] = []
    for step in steps:
        op = step["op"]
        failed = False
        if op in {"from", "join", "where"}:
            included = join_texts[:seen_joins]
            if op == "join":
                included = join_texts[: seen_joins + 1]
                seen_joins += 1
            partial = _partial_read(from_text, included, where_text, op == "where")
            snapshot = _snapshot(execute, partial)
            if snapshot is None:
                failed = True
                row_count, columns, rows = None, [], []
            else:
                row_count, columns, rows = snapshot
            dropped = _dropped(op, carried_count, row_count)
        elif op == "limit":
            parsed = _limit_number(limit_text)
            columns = list(carried_columns)
            if parsed is None:
                row_count = carried_count
                rows = [list(row) for row in carried_rows]
                dropped = None
            else:
                row_count = parsed if carried_count is None else min(carried_count, parsed)
                rows = [list(row) for row in carried_rows[:parsed]]
                dropped = _dropped("limit", carried_count, row_count)
        else:
            row_count = carried_count
            columns = list(carried_columns)
            rows = [list(row) for row in carried_rows]
            dropped = None
        frames.append(
            {
                "op": op,
                "label": step["label"],
                "detail": step["detail"],
                "row_count": row_count,
                "dropped": dropped,
                "columns": columns,
                "rows": rows,
            }
        )
        if failed:
            carried_count = None
            carried_columns = []
            carried_rows = []
        else:
            carried_count = row_count
            carried_columns = list(columns)
            carried_rows = [list(row) for row in rows]
    return frames


def _clauses(sql: str) -> list[tuple[str, str]]:
    original = sql.strip()
    if original.endswith(";"):
        original = original[:-1].rstrip()
    masked = _mask(original)
    marks: list[tuple[int, str]] = []
    depth = 0
    covered_until = 0
    for index, char in enumerate(masked):
        if char == "(":
            depth += 1
        elif char == ")" and depth:
            depth -= 1
        elif depth == 0 and index >= covered_until:
            match = _KEYWORD.match(masked, index)
            if match and (index == 0 or not masked[index - 1].isalnum()):
                marks.append((index, _label(match.group(1))))
                covered_until = match.end()
    if not marks:
        return []
    found: list[tuple[str, str]] = []
    for position, (start, label) in enumerate(marks):
        end = marks[position + 1][0] if position + 1 < len(marks) else len(original)
        found.append((label, original[start:end].strip()))
    return found


def _label(word: str) -> str:
    compact = re.sub(r"\s+", " ", word).upper()
    if compact.endswith("JOIN") and compact != "JOIN":
        kind = compact.split()[0]
        if kind == "INNER":
            return "JOIN"
        return f"{kind} JOIN"
    return compact


def _steps(clauses: list[tuple[str, str]]) -> list[dict]:
    by_label = {label: text for label, text in clauses}
    steps: list[dict] = []
    from_text = by_label.get("FROM", "")
    from_table = _table_name(from_text[4:]) if from_text else ""
    if from_table:
        steps.append(
            {
                "op": "from",
                "label": "FROM",
                "detail": f"Start by reading every row of {from_table}.",
            }
        )
    joins = [(label, text) for label, text in clauses if label.endswith("JOIN")]
    left = from_table or "the rows so far"
    for index, (label, text) in enumerate(joins):
        right = _table_name(re.sub(r"^(?:LEFT|RIGHT|FULL|CROSS|INNER)?\s*JOIN\b", "", text, count=1, flags=re.I))
        condition = _after_on(text)
        side = left if index == 0 else "the rows so far"
        steps.append(
            {
                "op": "join",
                "label": label,
                "detail": _join_detail(label, side, right or "the other table", condition),
            }
        )
        left = "the rows so far"
    if "WHERE" in by_label:
        condition = by_label["WHERE"][5:].strip()
        steps.append(
            {
                "op": "where",
                "label": "WHERE",
                "detail": f"Drop rows that fail this test: {condition}.",
            }
        )
    if "GROUP BY" in by_label:
        expr = by_label["GROUP BY"][8:].strip()
        steps.append(
            {
                "op": "group",
                "label": "GROUP BY",
                "detail": f"Collapse rows that share {expr} into one group.",
            }
        )
    if "HAVING" in by_label:
        condition = by_label["HAVING"][6:].strip()
        steps.append(
            {
                "op": "having",
                "label": "HAVING",
                "detail": f"Drop groups that fail this test: {condition}.",
            }
        )
    select = next((text for label, text in clauses if label == "SELECT"), "")
    if select:
        distinct = bool(re.match(r"(?i)SELECT\s+DISTINCT\b", select))
        body = re.sub(r"(?i)^SELECT\s+(?:DISTINCT\s+)?", "", select).strip()
        detail = f"Return only these values: {body}."
        if distinct:
            detail += " Then drop duplicate result rows."
        steps.append(
            {
                "op": "select",
                "label": "SELECT DISTINCT" if distinct else "SELECT",
                "detail": detail,
            }
        )
    if "ORDER BY" in by_label:
        expr = by_label["ORDER BY"][8:].strip()
        steps.append(
            {
                "op": "order",
                "label": "ORDER BY",
                "detail": f"Sort the remaining rows by {expr}.",
            }
        )
    if "LIMIT" in by_label:
        count = by_label["LIMIT"][5:].strip()
        steps.append(
            {
                "op": "limit",
                "label": "LIMIT",
                "detail": f"Keep only {count} rows.",
            }
        )
    return steps


def _join_detail(label: str, left: str, right: str, condition: str) -> str:
    if label == "CROSS JOIN":
        return f"Pair every row of {left} with every row of {right}."
    if label == "LEFT JOIN":
        test = f" when this condition matches: {condition}" if condition else ""
        return (
            f"Keep every row from {left}, and attach {right}{test}. "
            f"Unmatched rows stay, with empty {right} columns."
        )
    test = f" this condition: {condition}" if condition else " the join condition"
    return f"Keep only rows from {left} and {right} that match{test}."


def _table_name(fragment: str) -> str:
    text = fragment.strip()
    if not text or text.startswith("("):
        return ""
    match = _IDENT.match(text)
    return match.group(0) if match else ""


def _after_on(text: str) -> str:
    match = re.search(r"(?i)\bON\b", text)
    return text[match.end() :].strip() if match else ""


def _mermaid(steps: list[dict]) -> str:
    lines = ["flowchart TD"]
    ids: list[str] = []
    for index, step in enumerate(steps):
        node = f"s{index}"
        ids.append(node)
        text = _mermaid_text(f"{step['label']}<br/>{step['detail']}")
        lines.append(f'  {node}["{text}"]')
    for earlier, later in zip(ids, ids[1:]):
        lines.append(f"  {earlier} --> {later}")
    return "\n".join(lines)


def _mermaid_text(value: str) -> str:
    chunks = []
    for part in value.split("<br/>"):
        chunks.append(
            part.replace("&", "&amp;").replace('"', "'").replace("<", "&lt;").replace(">", "&gt;")
        )
    return "<br/>".join(chunks)


def _partial_read(
    from_text: str, join_texts: list[str], where_text: str, include_where: bool
) -> str:
    parts = ["SELECT *"]
    if from_text:
        parts.append(from_text)
    parts.extend(text for text in join_texts if text)
    if include_where and where_text:
        parts.append(where_text)
    return " ".join(parts)


def _snapshot(execute, partial: str) -> tuple[int | None, list[str], list[list]] | None:
    try:
        _, count_rows = execute(f"SELECT count(*) FROM ({partial}) AS step_rows")
        columns, sample_rows = execute(f"SELECT * FROM ({partial}) AS step_rows LIMIT 3")
    except Exception:
        return None
    row_count = None
    try:
        if count_rows and count_rows[0]:
            row_count = _count_value(count_rows[0][0])
    except Exception:
        row_count = None
    try:
        plain_columns = [str(column) for column in columns]
        plain_rows = [[_plain(value) for value in row] for row in list(sample_rows)[:3]]
    except Exception:
        return None
    return row_count, plain_columns, plain_rows


def _dropped(op: str, previous: int | None, current: int | None) -> int | None:
    if op not in {"join", "where", "having", "limit"}:
        return None
    if previous is None or current is None or current >= previous:
        return None
    return previous - current


def _limit_number(limit_text: str) -> int | None:
    match = re.match(r"(?i)LIMIT\s+(\d+)\b", limit_text.strip())
    if not match:
        return None
    return int(match.group(1))


def _count_value(value: object) -> int | None:
    plain = _plain(value)
    if isinstance(plain, int) and not isinstance(plain, bool):
        return plain
    if isinstance(plain, str):
        try:
            return int(plain.strip())
        except ValueError:
            return None
    return None


def _plain(value: object):
    if value is None or isinstance(value, str):
        return value
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value) if value.is_integer() else str(value)
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else format(value, "f")
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return str(value)


def _mask(sql: str) -> str:
    chars = list(sql)
    index = 0
    length = len(sql)
    while index < length:
        if sql.startswith("--", index):
            end = sql.find("\n", index)
            end = length if end == -1 else end
            for cursor in range(index, end):
                chars[cursor] = " "
            index = end
            continue
        if sql.startswith("/*", index):
            end = sql.find("*/", index + 2)
            end = length if end == -1 else end + 2
            for cursor in range(index, min(end, length)):
                chars[cursor] = " "
            index = end
            continue
        if sql[index] == "'":
            chars[index] = " "
            index += 1
            while index < length:
                if sql[index] == "'" and index + 1 < length and sql[index + 1] == "'":
                    chars[index] = " "
                    chars[index + 1] = " "
                    index += 2
                    continue
                quote = sql[index] == "'"
                chars[index] = " "
                index += 1
                if quote:
                    break
            continue
        index += 1
    return "".join(chars)

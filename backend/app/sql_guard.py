import re


class QueryRejected(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def prepare_statement(sql: str) -> str:
    if not sql or not sql.strip():
        raise QueryRejected("Write a query first.")

    text = sql.strip()
    if text.endswith(";"):
        text = text[:-1].rstrip()
    if not text:
        raise QueryRejected("Write a query first.")
    if _contains_semicolon(text):
        raise QueryRejected("Submit one SELECT statement.")

    body = _strip_comments(text).strip()
    if not re.match(r"(?is)^(select|with)\b", body):
        raise QueryRejected("Only a SELECT query is allowed.")
    return text


def _contains_semicolon(sql: str) -> bool:
    for kind, _text in _scan(sql):
        if kind == "semicolon":
            return True
    return False


def _strip_comments(sql: str) -> str:
    parts: list[str] = []
    for kind, text in _scan(sql):
        if kind in {"code", "string"}:
            parts.append(text)
        elif kind == "semicolon":
            parts.append(";")
    return "".join(parts)


def _scan(sql: str):
    i = 0
    length = len(sql)
    while i < length:
        ch = sql[i]
        nxt = sql[i + 1] if i + 1 < length else ""
        if ch == "-" and nxt == "-":
            end = sql.find("\n", i)
            if end == -1:
                return
            i = end
            continue
        if ch == "/" and nxt == "*":
            end = sql.find("*/", i + 2)
            if end == -1:
                return
            i = end + 2
            continue
        if ch in {"'", '"'} or (ch == "$" and _dollar_tag(sql, i) is not None):
            if ch == "$":
                tag = _dollar_tag(sql, i)
                end = sql.find(tag, i + len(tag))
                if end == -1:
                    yield "string", sql[i:]
                    return
                yield "string", sql[i : end + len(tag)]
                i = end + len(tag)
                continue
            end = _quoted_end(sql, i, ch)
            yield "string", sql[i:end]
            i = end
            continue
        if ch == ";":
            yield "semicolon", ";"
            i += 1
            continue
        start = i
        while i < length and not _boundary(sql, i):
            i += 1
        yield "code", sql[start:i]


def _boundary(sql: str, i: int) -> bool:
    ch = sql[i]
    nxt = sql[i + 1] if i + 1 < len(sql) else ""
    if ch in {"'", '"', ";"}:
        return True
    if ch == "-" and nxt == "-":
        return True
    if ch == "/" and nxt == "*":
        return True
    return ch == "$" and _dollar_tag(sql, i) is not None


def _quoted_end(sql: str, start: int, quote: str) -> int:
    i = start + 1
    while i < len(sql):
        if sql[i] == quote:
            if quote == "'" and i + 1 < len(sql) and sql[i + 1] == "'":
                i += 2
                continue
            return i + 1
        i += 1
    return len(sql)


def _dollar_tag(sql: str, start: int) -> str | None:
    if sql[start] != "$":
        return None
    end = sql.find("$", start + 1)
    if end == -1:
        return None
    tag = sql[start : end + 1]
    body = tag[1:-1]
    if body == "" or re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", body):
        return tag
    return None

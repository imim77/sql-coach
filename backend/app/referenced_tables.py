import re

_FROM_OR_JOIN = re.compile(r"\b(?:FROM|JOIN)\b", re.IGNORECASE)
_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def referenced_tables(sql: str) -> tuple[str, ...]:
    text = _strip_noise(sql)
    names: list[str] = []
    seen: set[str] = set()
    for match in _FROM_OR_JOIN.finditer(text):
        index = match.end()
        while index < len(text) and text[index].isspace():
            index += 1
        if index >= len(text) or text[index] == "(":
            continue
        ident = _IDENT.match(text, index)
        if ident is None:
            continue
        name = ident.group(0)
        if name in seen:
            continue
        seen.add(name)
        names.append(name)
    return tuple(names)


def _strip_noise(sql: str) -> str:
    pieces: list[str] = []
    i = 0
    length = len(sql)
    while i < length:
        if sql.startswith("--", i):
            end = sql.find("\n", i)
            pieces.append(" ")
            if end == -1:
                break
            i = end
            continue
        if sql.startswith("/*", i):
            end = sql.find("*/", i + 2)
            pieces.append(" ")
            if end == -1:
                break
            i = end + 2
            continue
        if sql[i] == "'":
            i += 1
            while i < length:
                if sql[i] == "'":
                    if i + 1 < length and sql[i + 1] == "'":
                        i += 2
                        continue
                    i += 1
                    break
                i += 1
            pieces.append(" ")
            continue
        pieces.append(sql[i])
        i += 1
    return "".join(pieces)

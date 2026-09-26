from app.query_plan import explain_query, illustrate_query, plan_for_correct_answer

SIMPLE = "SELECT name FROM vessels WHERE year_built > 2010"
LEFT = "SELECT v.name FROM vessels AS v LEFT JOIN voyages AS voy ON voy.vessel_id = v.id"
AGGREGATE = (
    "SELECT origin, COUNT(*) FROM voyages GROUP BY origin "
    "HAVING COUNT(*) > 2 ORDER BY origin LIMIT 5"
)


def _labels(sql: str) -> list[str]:
    return [step["label"] for step in explain_query(sql)["steps"]]


def test_where_query_runs_from_then_where_then_select():
    explained = explain_query(SIMPLE)
    assert _labels(SIMPLE) == ["FROM", "WHERE", "SELECT"]
    assert explained["steps"][0]["detail"] == "Start by reading every row of vessels."
    assert "year_built > 2010" in explained["steps"][1]["detail"]
    mermaid = explained["mermaid"]
    assert mermaid.index("FROM") < mermaid.index("WHERE") < mermaid.index("SELECT")
    assert plan_for_correct_answer(False, SIMPLE) is None
    assert plan_for_correct_answer(True, SIMPLE) == explained


def test_left_join_keeps_every_left_row():
    steps = explain_query(LEFT)["steps"]
    assert [step["label"] for step in steps[:2]] == ["FROM", "LEFT JOIN"]
    assert "vessels" in steps[0]["detail"]
    assert "every row from vessels" in steps[1]["detail"]
    assert "voyages" in steps[1]["detail"]


def test_aggregate_query_uses_logical_order():
    labels = _labels(AGGREGATE)
    assert labels == ["FROM", "GROUP BY", "HAVING", "SELECT", "ORDER BY", "LIMIT"]
    assert labels.index("SELECT") < labels.index("ORDER BY")


def test_string_literal_is_not_a_from_clause():
    sql = "SELECT name FROM vessels WHERE note = 'FROM ports'"
    details = " ".join(step["detail"] for step in explain_query(sql)["steps"])
    assert "reading every row of vessels" in details
    assert "reading every row of ports" not in details


def test_distinct_is_called_out_on_the_select_step():
    steps = explain_query("SELECT DISTINCT country FROM ports")["steps"]
    select = next(step for step in steps if step["op"] == "select")
    assert select["label"] == "SELECT DISTINCT"
    assert "duplicate" in select["detail"]


def test_where_frame_counts_dropped_rows():
    calls = []

    def execute(statement: str):
        calls.append(statement)
        filtered = "year_built > 2010" in statement
        if statement.startswith("SELECT count(*)"):
            return ["count"], [(2 if filtered else 5,)]
        rows = [("Ada", 2012), ("Bea", 2014), ("Cal", 1998), ("Dee", 2001)]
        return ["name", "year_built"], rows[:2] if filtered else rows

    frames = illustrate_query(SIMPLE, execute)
    assert [frame["op"] for frame in frames] == ["from", "where", "select"]
    assert calls == [
        "SELECT count(*) FROM (SELECT * FROM vessels) AS step_rows",
        "SELECT * FROM (SELECT * FROM vessels) AS step_rows LIMIT 3",
        "SELECT count(*) FROM (SELECT * FROM vessels WHERE year_built > 2010) AS step_rows",
        "SELECT * FROM (SELECT * FROM vessels WHERE year_built > 2010) AS step_rows LIMIT 3",
    ]
    where = frames[1]
    assert frames[0]["row_count"] == 5
    assert frames[0]["dropped"] is None
    assert frames[0]["rows"] == [["Ada", 2012], ["Bea", 2014], ["Cal", 1998]]
    assert where["row_count"] == 2
    assert where["dropped"] == frames[0]["row_count"] - where["row_count"]
    assert where["dropped"] > 0
    assert where["columns"] == ["name", "year_built"]
    assert where["rows"] == [["Ada", 2012], ["Bea", 2014]]
    assert frames[2]["row_count"] == where["row_count"]
    assert frames[2]["rows"] == where["rows"]
    assert frames[2]["dropped"] is None


def test_left_join_frame_keeps_every_left_row_and_lists_rows():
    def execute(statement: str):
        joined = "JOIN" in statement.upper()
        if statement.startswith("SELECT count(*)"):
            return ["count"], [(4,)]
        if joined:
            return ["name", "voyage_id"], [("Nord", 1), ("Syd", None)]
        return ["name", "voyage_id"], [("Nord", None), ("Syd", None), ("Ost", None)]

    frames = illustrate_query(LEFT, execute)
    explained = explain_query(LEFT)["steps"]
    assert [(frame["op"], frame["label"], frame["detail"]) for frame in frames] == [
        (step["op"], step["label"], step["detail"]) for step in explained
    ]
    join = next(frame for frame in frames if frame["op"] == "join")
    assert "every row from vessels" in join["detail"]
    assert join["rows"] == [["Nord", 1], ["Syd", None]]
    assert join["dropped"] is None


def test_distinct_copies_rows_without_recounting_dropped():
    def execute(statement: str):
        if statement.startswith("SELECT count(*)"):
            return ["count"], [(4,)]
        return ["country"], [("NO",), ("SE",), ("NO",)]

    frames = illustrate_query("SELECT DISTINCT country FROM ports", execute)
    select = frames[-1]
    assert select["label"] == "SELECT DISTINCT"
    assert select["dropped"] is None
    assert select["row_count"] == frames[0]["row_count"]
    assert select["rows"] == frames[0]["rows"]


def test_limit_frame_uses_the_parsed_limit():
    def execute(statement: str):
        if statement.startswith("SELECT count(*)"):
            return ["count"], [(9,)]
        return ["origin"], [("Oslo",), ("Bergen",), ("Tromso",)]

    frames = illustrate_query(AGGREGATE, execute)
    limit = frames[-1]
    assert limit["op"] == "limit"
    assert limit["row_count"] == 5
    assert limit["dropped"] == 4
    assert limit["rows"] == [["Oslo"], ["Bergen"], ["Tromso"]]
    having = next(frame for frame in frames if frame["op"] == "having")
    assert having["rows"] == limit["rows"]
    assert having["dropped"] is None


def test_illustrate_query_does_not_raise_when_execute_fails():
    class DatabaseError(Exception):
        pass

    def execute(statement: str):
        raise DatabaseError("database is unavailable")

    frames = illustrate_query(SIMPLE, execute)
    assert [frame["label"] for frame in frames] == ["FROM", "WHERE", "SELECT"]
    for frame in frames:
        assert frame["row_count"] is None
        assert frame["dropped"] is None
        assert frame["columns"] == []
        assert frame["rows"] == []

    aggregate = illustrate_query(AGGREGATE, execute)
    assert [frame["label"] for frame in aggregate] == [
        "FROM",
        "GROUP BY",
        "HAVING",
        "SELECT",
        "ORDER BY",
        "LIMIT",
    ]

from app.query_plan import explain_query, plan_for_correct_answer

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

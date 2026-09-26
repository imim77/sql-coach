from app.referenced_tables import referenced_tables


def test_single_table_after_from():
    assert referenced_tables(
        "SELECT name FROM vessels WHERE year_built > 2010"
    ) == ("vessels",)


def test_join_lists_tables_without_aliases():
    sql = "SELECT v.name FROM voyages v JOIN ports p ON p.id = v.origin_port_id"
    assert referenced_tables(sql) == ("voyages", "ports")


def test_from_inside_a_quoted_string_is_not_a_table():
    assert referenced_tables(
        "SELECT name FROM ports WHERE label = 'FROM vessels'"
    ) == ("ports",)
    assert referenced_tables(
        "SELECT name FROM ports WHERE label = 'it''s FROM crew'"
    ) == ("ports",)


def test_comments_do_not_add_tables():
    sql = "SELECT name FROM ports -- FROM vessels\n/* JOIN crew */"
    assert referenced_tables(sql) == ("ports",)


def test_duplicates_are_removed_in_first_seen_order():
    sql = (
        "SELECT v.name FROM voyages v "
        "JOIN ports p ON p.id = v.origin_port_id "
        "JOIN voyages w ON w.origin_port_id = p.id"
    )
    assert referenced_tables(sql) == ("voyages", "ports")


def test_subquery_parenthesis_is_not_a_table():
    sql = "SELECT * FROM (SELECT id FROM vessels) s"
    assert referenced_tables(sql) == ("vessels",)

from digital_futures.app import from_table, to_table

AXIS_SETS = [{"name": "A × B", "x": {"driver_id": "d1", "pole_a": "one", "pole_b": "two"}, "rationale": "r"}]
DRIVERS = [{"id": "d1", "impact": 4, "sources": [{"title": "t", "url": "u"}]}]


def test_tables_flatten_nested_records_and_restore_them():
    table = to_table(AXIS_SETS)
    assert "x.pole_a" in table.columns
    assert from_table(table, AXIS_SETS) == AXIS_SETS


def test_tables_keep_lists_as_json_text():
    table = to_table(DRIVERS)
    assert table["sources"][0] == '[{"title": "t", "url": "u"}]'
    assert from_table(table, DRIVERS) == DRIVERS


def test_an_edited_cell_comes_back_in_the_nested_record():
    table = to_table(AXIS_SETS)
    table.loc[0, "x.pole_a"] = "changed"
    assert from_table(table, AXIS_SETS)[0]["x"]["pole_a"] == "changed"

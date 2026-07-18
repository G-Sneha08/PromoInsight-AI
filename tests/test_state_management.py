import pytest

from src.state_management import (
    reset_current_display_state,
    deductuplicate_filters,
    deduplicate_dimensions,
    deduplicate_group_by,
    deduplicate_sort_conditions,
    deduplicate_result_entities,
    classify_reference,
    is_meaningful_follow_up,
)


def test_reset_current_display_state_preserves_context():
    state = {
        "current_request": "old question",
        "current_status": "success",
        "current_plan": {"op": "value"},
        "current_response": {"direct_answer": "old"},
        "current_data": [{"x": 1}],
        "current_chart": {"chart": True},
        "current_metrics": {"k": "v"},
        "current_sql": "SELECT 1",
        "conversation_context": {"metric": "total_sales"},
        "query_history": [{"question": "old"}],
        "last_successful_plan": {"metric": "total_sales"},
        "last_resolved_entity": {"field": "category", "value": "Fruit Juice"},
    }

    reset_current_display_state(state)

    assert state["current_request"] == ""
    assert state["current_status"] == "idle"
    assert state["current_plan"] is None
    assert state["current_response"] is None
    assert state["current_data"] == []
    assert state["current_chart"] is None
    assert state["current_metrics"] == {}
    assert state["current_sql"] == ""
    assert state["conversation_context"] == {"metric": "total_sales"}
    assert state["query_history"][0]["question"] == "old"
    assert state["last_successful_plan"] == {"metric": "total_sales"}


def test_deduplicates_filters_and_grouping_fields():
    filters = [
        {"field": "region_name", "operator": "equals", "value": "North"},
        {"field": "region_name", "operator": "equals", "value": "North"},
        {"field": "category", "operator": "equals", "value": "Fruit Juice"},
    ]
    dimensions = ["category", "category", "region_name"]
    group_by = ["region_name", "region_name", "category"]
    sort_conditions = [{"field": "total_sales", "direction": "descending"}, {"field": "total_sales", "direction": "descending"}]

    assert deductuplicate_filters(filters) == [
        {"field": "region_name", "operator": "equals", "value": "North"},
        {"field": "category", "operator": "equals", "value": "Fruit Juice"},
    ]
    assert deduplicate_dimensions(dimensions) == ["category", "region_name"]
    assert deduplicate_group_by(group_by) == ["region_name", "category"]
    assert deduplicate_sort_conditions(sort_conditions) == [{"field": "total_sales", "direction": "descending"}]


def test_deduplicates_result_entities():
    entities = [
        {"entity": "Fruit Juice", "value": 100},
        {"entity": "Fruit Juice", "value": 100},
        {"entity": "Coca-Cola", "value": 50},
    ]
    assert deduplicate_result_entities(entities) == [
        {"entity": "Fruit Juice", "value": 100},
        {"entity": "Coca-Cola", "value": 50},
    ]


def test_reference_resolution_requires_single_clear_match():
    context = {
        "resolved_entity": {"field": "category", "value": "Fruit Juice"},
        "last_operation": {"operation_type": "aggregate", "metric": "total_sales"},
    }

    assert classify_reference("that one", context, None) == "resolved"
    assert classify_reference("that thing", {"resolved_entity": None}, None) == "missing"


def test_meaningful_follow_up_requires_real_transformation():
    assert is_meaningful_follow_up("show sales", {}) is False
    assert is_meaningful_follow_up("show sales for South", {}) is True
    assert is_meaningful_follow_up("show sales last month", {}) is True

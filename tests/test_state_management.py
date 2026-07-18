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
    segment_questions,
    classify_segment,
    prepare_ordinal_follow_up,
    classify_input,
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


def test_segment_questions_split_independent_requests():
    text = "Which products had the highest sales? Show the top three regions."
    segments = segment_questions(text)
    assert len(segments) == 2
    assert segments[0]["text"].startswith("Which products")
    assert segments[1]["text"].startswith("Show the top three regions")


def test_classify_segment_uses_context_for_follow_up():
    context = {"last_successful_plan": {"operation_type": "rank", "metric": "total_sales"}}
    assert classify_segment("Show the second one.", context) == "follow_up"
    assert classify_segment("Show total sales for Fruit Juice.", {}) == "independent_question"


def test_prepare_ordinal_follow_up_removes_limit_one():
    plan = {"operation_type": "rank", "metric": "total_sales", "limit": 1}
    prepared = prepare_ordinal_follow_up("Which one was second?", plan)
    assert prepared["limit"] == 2


def test_classify_input_rejects_low_information_queries():
    assert classify_input("") == "malformed_input"
    assert classify_input("   ") == "malformed_input"
    assert classify_input("the") == "incomplete_query"
    assert classify_input("sales") == "incomplete_query"
    assert classify_input("show") == "incomplete_query"
    assert classify_input("what") == "incomplete_query"
    assert classify_input("tell me") == "incomplete_query"
    assert classify_input("hello") == "casual_input"
    assert classify_input("!!!") == "malformed_input"
    assert classify_input("something") == "incomplete_query"
    assert classify_input("test") == "incomplete_query"


def test_classify_input_accepts_valid_follow_up_with_context():
    context = {"last_successful_plan": {"operation_type": "aggregate", "metric": "total_sales"}}
    assert classify_input("South only", context) == "valid_query"
    assert classify_input("Monthly", context) == "valid_query"


def test_classify_input_accepts_valid_analytical_queries():
    assert classify_input("Show sales in South") == "valid_query"
    assert classify_input("Show closing inventory") == "valid_query"
    assert classify_input("How complete is the inventory dataset?") == "valid_query"


def test_classify_input_does_not_use_total_sales_as_universal_fallback():
    assert classify_input("the") != "valid_query"
    assert classify_input("show") != "valid_query"
    assert classify_input("sales") != "valid_query"

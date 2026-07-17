import pytest
from src.rule_based_parser import RuleBasedParser
from src.models import QueryPlan

def test_rule_based_parser_entities():
    parser = RuleBasedParser()
    
    # 1. Test region and category extraction
    plan = parser.parse("What were total sales in the South region last month?")
    assert not plan.needs_clarification
    assert len(plan.operations) == 1
    op = plan.operations[0]
    assert op.metric == "total_sales"
    assert op.operation_type == "aggregate"
    
    # Check filters
    filters = {f.field: f.value for f in op.filters}
    assert "region_name" in filters
    assert filters["region_name"] == "South"
    
    # Check time range
    assert op.time_range is not None
    assert op.time_range.type == "relative"
    assert op.time_range.value == "last_month"

def test_rule_based_parser_ambiguity():
    parser = RuleBasedParser()
    
    # 2. Test ambiguity clarification trigger
    plan = parser.parse("Which is the best product?")
    assert plan.needs_clarification
    assert plan.clarification_question is not None
    assert "best" in plan.clarification_question.lower()

def test_rule_based_parser_follow_up():
    parser = RuleBasedParser()
    
    # Question 1
    plan1 = parser.parse("Show total sales in the South last month")
    assert not plan1.needs_clarification
    
    # Question 2 (Follow up fragment)
    plan2 = parser.parse("What about Fruit Juice only?", history=[plan1])
    assert not plan2.needs_clarification
    assert len(plan2.operations) == 1
    op = plan2.operations[0]
    
    # Verify filters merged
    filters = {f.field: f.value for f in op.filters}
    assert "region_name" in filters
    assert filters["region_name"] == "South"  # Carried over
    assert "category" in filters
    assert filters["category"] == "Fruit Juice" # Added new
    
    # Verify time range carried over
    assert op.time_range is not None
    assert op.time_range.value == "last_month"

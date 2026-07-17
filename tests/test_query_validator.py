import pytest
from src.query_validator import QueryValidator
from src.models import QueryPlan, OperationPlan, FilterCondition, SortCondition

def test_query_validator_valid():
    op = OperationPlan(
        operation_type="aggregate",
        metric="total_sales",
        dimensions=["region_name"],
        filters=[FilterCondition(field="region_name", operator="equals", value="South")],
        group_by=["region_name"]
    )
    plan = QueryPlan(operations=[op])
    is_valid, msg = QueryValidator.validate(plan)
    assert is_valid
    
def test_query_validator_invalid_metric():
    op = OperationPlan(
        operation_type="aggregate",
        metric="unsupported_business_metric",
        dimensions=[]
    )
    plan = QueryPlan(operations=[op])
    is_valid, msg = QueryValidator.validate(plan)
    assert not is_valid
    assert "Unsupported metric" in msg

def test_query_validator_invalid_column():
    op = OperationPlan(
        operation_type="aggregate",
        metric="total_sales",
        dimensions=["employee_salary_column"]
    )
    plan = QueryPlan(operations=[op])
    is_valid, msg = QueryValidator.validate(plan)
    assert not is_valid
    assert "cannot be answered reliably" in msg

def test_query_validator_invalid_operator():
    op = OperationPlan(
        operation_type="aggregate",
        metric="total_sales",
        filters=[FilterCondition(field="region_name", operator="greater_than", value="South")] # greater_than not allowed for region text
    )
    plan = QueryPlan(operations=[op])
    is_valid, msg = QueryValidator.validate(plan)
    assert not is_valid
    assert "Operator" in msg

def test_query_validator_limits():
    op = OperationPlan(
        operation_type="rank",
        metric="total_sales",
        limit=105 # Exceeds 100 limit
    )
    plan = QueryPlan(operations=[op])
    is_valid, msg = QueryValidator.validate(plan)
    assert not is_valid
    assert "limit" in msg.lower()

import pytest
from src.models import OperationPlan, FilterCondition, SortCondition
from src.sql_compiler import SQLCompiler

def test_sql_compiler_simple():
    compiler = SQLCompiler()
    
    op = OperationPlan(
        operation_type="aggregate",
        metric="total_sales",
        dimensions=["region_name"],
        filters=[FilterCondition(field="region_name", operator="equals", value="South")],
        group_by=["region_name"]
    )
    
    sql, params = compiler.compile(op)
    
    # Verify SQL query components
    assert "SELECT" in sql
    assert "SUM(sales.sales_amount) AS total_sales" in sql
    assert "FROM sales" in sql
    assert "JOIN regions" in sql
    assert "WHERE regions.region_name = ?" in sql
    assert "GROUP BY regions.region_name" in sql
    assert params == ["South"]

def test_sql_compiler_ranking():
    compiler = SQLCompiler()
    
    op = OperationPlan(
        operation_type="rank",
        metric="total_units",
        dimensions=["product_name"],
        order_by=[SortCondition(field="total_units", direction="descending")],
        limit=5,
        group_by=["product_name"]
    )
    
    sql, params = compiler.compile(op)
    assert "SUM(sales.units_sold) AS total_units" in sql
    assert "ORDER BY total_units DESC" in sql
    assert "LIMIT 5" in sql

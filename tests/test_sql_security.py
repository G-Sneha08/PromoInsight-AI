import pytest
from src.models import OperationPlan, FilterCondition
from src.sql_compiler import SQLCompiler
from src.sql_executor import SQLExecutor

def test_sql_compiler_injection_safety():
    compiler = SQLCompiler()
    
    # Injected value
    malicious_value = "South' UNION SELECT * FROM users; --"
    op = OperationPlan(
        operation_type="aggregate",
        metric="total_sales",
        filters=[FilterCondition(field="region_name", operator="equals", value=malicious_value)]
    )
    
    sql, params = compiler.compile(op)
    
    # SQL must use parameter placeholder '?'
    assert "regions.region_name = ?" in sql
    assert malicious_value in params
    assert len(params) == 1
    
def test_sql_executor_write_protection():
    # If a query attempts schema modification or write, it must raise a PermissionError
    drop_sql = "DROP TABLE sales;"
    with pytest.raises(PermissionError):
        SQLExecutor.execute(drop_sql)
        
    update_sql = "UPDATE sales SET units_sold = 1000;"
    with pytest.raises(PermissionError):
        SQLExecutor.execute(update_sql)

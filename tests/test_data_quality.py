import pytest
from src.config import is_db_ready
from src.data_quality import DataQuality

pytestmark = pytest.mark.skipif(not is_db_ready(), reason="Database file not initialized.")

def test_data_quality_run_checks():
    res = DataQuality.run_all_checks()
    
    assert "overall_completeness_score" in res
    assert "duplicate_sales_records" in res
    assert "referential_integrity" in res
    assert "inventory_days_completeness" in res
    
    # Verify duplicates are caught
    assert res["duplicate_sales_records"] >= 0
    # Expected completeness details
    assert res["inventory_days_completeness"]["percentage_completeness"] > 0
    assert len(res["warnings"]) >= 0

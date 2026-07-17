import pytest
import pandas as pd
import numpy as np
from src.result_validator import ResultValidator

def test_result_validator_nan_inf():
    # Input with NaN and Inf
    raw_data = {
        "success": True,
        "operation_type": "aggregate",
        "metric": "total_sales",
        "data": pd.DataFrame({
            "region_name": ["North", "South"],
            "total_sales": [1000.0, np.inf],
            "units": [np.nan, 200.0]
        }),
        "warnings": [],
        "assumptions": []
    }
    
    is_ok, msg, res = ResultValidator.validate_results(raw_data)
    assert is_ok
    df_clean = res["data"]
    
    # Assert NaN and Inf are cleaned
    assert df_clean["total_sales"].iloc[1] == 0.0
    assert df_clean["units"].iloc[0] == 0.0
    
    # Assert warning added
    assert len(res["warnings"]) > 0
    assert "Sanitized" in res["warnings"][0] or "sanitized" in res["warnings"][0]

def test_result_validator_causal_language():
    raw_data = {
        "success": True,
        "operation_type": "promotion_uplift",
        "metric": "promotion_uplift_percentage",
        "data": pd.DataFrame({"product_name": ["Cola Classic"], "uplift_percent": [25.0]}),
        "warnings": ["The sales growth was caused by the Thanksgiving campaign."],
        "assumptions": []
    }
    
    is_ok, msg, res = ResultValidator.validate_results(raw_data)
    assert is_ok
    
    # Assert causal language is sanitized
    sanitized_warning = res["warnings"][0]
    assert "caused by" not in sanitized_warning
    assert "associated with" in sanitized_warning

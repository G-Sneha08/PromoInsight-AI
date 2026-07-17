import pytest
from src.metric_catalog import METRIC_CATALOG

def test_metric_catalog_completeness():
    required_metrics = [
        "total_sales",
        "total_units",
        "average_selling_price",
        "average_daily_sales",
        "sales_growth_percentage",
        "month_over_month_growth",
        "revenue_contribution_percentage",
        "promotion_sales",
        "baseline_sales",
        "promotion_uplift_percentage",
        "opening_inventory",
        "closing_inventory",
        "inventory_reduction_percentage",
        "sell_through_percentage",
        "stockout_risk",
        "excess_inventory",
        "data_completeness_percentage"
    ]
    
    for metric in required_metrics:
        assert metric in METRIC_CATALOG, f"Missing metric: {metric}"
        assert "description" in METRIC_CATALOG[metric]
        assert "formula" in METRIC_CATALOG[metric]
        assert "required_columns" in METRIC_CATALOG[metric]

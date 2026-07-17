import pytest
import os
from src.config import is_db_ready
from src.promotion_analysis import PromotionAnalysis

# Only run if database is initialized
pytestmark = pytest.mark.skipif(not is_db_ready(), reason="Database file not initialized. Run generate_data.py and setup_database.py first.")

def test_promotion_analysis_success():
    # PROM03 is orange splash promo, starts later so has history to construct baseline
    res = PromotionAnalysis.analyze_promotion("PROM03")
    assert "error" not in res
    assert res["promotion_id"] == "PROM03"
    assert res["uplift_percent"] > 0.0
    assert "baseline_units" in res
    assert "promo_units" in res
    assert res["promo_units"] > res["baseline_units"]

def test_promotion_underperformance():
    # PROM05 is the underperforming Bolt Energy Flash Sale (actual sales dip)
    res = PromotionAnalysis.analyze_promotion("PROM05")
    assert "error" not in res
    # Sells fewer units than baseline
    assert res["uplift_percent"] < 0.0
    assert res["uplift_units"] < 0

def test_promotion_overlap_detection():
    # PROM06 and PROM07 overlap in region R02 for product P015
    res = PromotionAnalysis.analyze_promotion("PROM06")
    assert res["has_overlap"]
    
    # Check that warning contains overlap message
    overlap_warns = [w for w in res["warnings"] if "overlapping promotion detected" in w.lower()]
    assert len(overlap_warns) > 0
    assert "associative and cannot be solely attributed" in overlap_warns[0]

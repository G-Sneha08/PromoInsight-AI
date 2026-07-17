import pytest
import pandas as pd
from src.response_generator import ResponseGenerator

def test_response_formatting_helpers():
    # 1. Test metric label formatter
    assert ResponseGenerator.format_metric_name("total_sales") == "revenue"
    assert ResponseGenerator.format_metric_name("total_units") == "units sold"
    assert ResponseGenerator.format_metric_name("unknown_metric") == "unknown metric"
    
    # 2. Test dimension label formatter
    assert ResponseGenerator.format_dimension_name("region_name") == "region"
    assert ResponseGenerator.format_dimension_name("product_name") == "product"
    
    # 3. Test currency formatter
    assert ResponseGenerator.format_currency(123456.78) == "$123,456.78"
    assert ResponseGenerator.format_currency("ABC") == "ABC"
    
    # 4. Test percentage formatter
    assert ResponseGenerator.format_percentage(12.3456) == "12.35%"
    assert ResponseGenerator.format_percentage("ABC") == "ABC"
    
    # 5. Test number formatter
    assert ResponseGenerator.format_number(12345.67) == "12,345.67"
    assert ResponseGenerator.format_number(12345.0) == "12,345"

def test_causal_language_sanitization():
    # Enforces neutral business-friendly wording
    raw_text = "The promotion caused a 15.50% sales uplift."
    sanitized = ResponseGenerator._validate_and_sanitize_answer(
        raw_text, 
        pd.DataFrame({"uplift_percent": [15.50]}), 
        "uplift_percent", 
        [], 
        [], 
        None
    )
    assert "caused" not in sanitized
    assert "was associated with" in sanitized

def test_forbidden_phrases_fallback():
    # Enforces forbidden phrases blocking
    raw_text = "The query returned 1 record: South with value of $10,000.00."
    df = pd.DataFrame({"region_name": ["South"], "total_sales": [10000.00]})
    sanitized = ResponseGenerator._validate_and_sanitize_answer(
        raw_text, 
        df, 
        "total_sales", 
        ["region_name"], 
        [], 
        None
    )
    # The output should fallback to a clean message
    assert "query returned" not in sanitized
    assert "record" not in sanitized
    assert "with value of" not in sanitized
    assert sanitized == "South registered revenue of $10,000.00."

def test_hallucinated_number_validation():
    # Enforces that all numbers present in text exist in results
    raw_text = "Sales in South region reached $500,000.00." # 500,000 is not in dataframe!
    df = pd.DataFrame({"region_name": ["South"], "total_sales": [12345.67]})
    sanitized = ResponseGenerator._validate_and_sanitize_answer(
        raw_text, 
        df, 
        "total_sales", 
        ["region_name"], 
        [], 
        None
    )
    # Falling back because 500,000 is hallucinated
    assert sanitized == "South registered revenue of $12,345.67."

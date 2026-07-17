import logging
from typing import Any

# Configure global logger
def setup_logger():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger("PromoInsightAI")

logger = setup_logger()

def format_currency(value: Any) -> str:
    try:
        val = float(value)
        return f"${val:,.2f}"
    except (ValueError, TypeError):
        return str(value)

def format_percentage(value: Any) -> str:
    try:
        val = float(value)
        return f"{val:.2f}%"
    except (ValueError, TypeError):
        return str(value)

from __future__ import annotations

import re
from copy import deepcopy
from typing import Any, Dict, List, Optional, Tuple

STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "can", "do", "does", "for", "from",
    "had", "have", "help", "how", "i", "in", "into", "is", "it", "me", "my", "of", "on", "or",
    "our", "please", "show", "tell", "that", "the", "their", "this", "to", "was", "what", "when",
    "which", "who", "why", "with", "would", "you", "your"
}

GREETING_WORDS = {"hello", "hi", "hey", "greetings", "good morning", "good afternoon", "good evening"}

ANALYTICAL_HINTS = {
    "sales", "revenue", "units", "inventory", "promotion", "promotions", "campaign", "campaigns",
    "uplift", "growth", "compare", "rank", "trend", "share", "contribution", "anomaly", "spike",
    "completeness", "complete", "quality", "dataset", "stockout", "closing", "opening", "price",
    "region", "category", "brand", "product", "products", "regions", "categories", "brands", "south",
    "north", "east", "west", "central", "fruit", "juice", "water", "tea", "drinks", "coca", "cola"
}

TIME_HINTS = {"day", "days", "week", "weeks", "month", "months", "quarter", "quarters", "year", "years", "monthly", "weekly", "daily", "yearly", "latest", "last", "previous", "before", "after", "during", "from", "to"}

UNSUPPORTED_TERMS = {"salary", "salaries", "employee", "employees", "staff", "weather", "cost", "profit", "margin", "expense", "expenses", "customer", "customers", "feedback", "review", "reviews", "rating", "ratings"}


def classify_input(question: str, context: Optional[Dict[str, Any]] = None) -> str:
    if context is None:
        context = {}

    if not isinstance(question, str):
        return "malformed_input"

    normalized = re.sub(r"\s+", " ", question.strip()).lower()
    if not normalized:
        return "malformed_input"

    if re.fullmatch(r"[\W_]+", normalized):
        return "malformed_input"

    tokens = re.findall(r"[a-z0-9]+", normalized)
    if not tokens:
        return "malformed_input"

    if any(token in GREETING_WORDS for token in [normalized] if normalized in GREETING_WORDS):
        return "casual_input"

    if normalized in GREETING_WORDS:
        return "casual_input"

    if any(term in normalized for term in UNSUPPORTED_TERMS):
        return "unsupported_query"

    if len(tokens) == 1 and tokens[0] in STOP_WORDS:
        return "incomplete_query"

    if len(tokens) == 1 and tokens[0] in {"sales", "revenue", "inventory", "promotion", "promotions", "product", "products", "region", "regions", "category", "categories", "brand", "brands", "data", "dataset"}:
        return "incomplete_query"

    if re.search(r"\bwhich one\b", normalized) and re.search(r"\b(best|performed|highest|lowest|top|worst)\b", normalized):
        return "ambiguous_query"

    if len(tokens) <= 2 and any(token in {"show", "tell", "what", "which", "how", "can", "please", "me"} for token in tokens):
        return "incomplete_query"

    if len(tokens) <= 2 and any(token in {"the", "a", "an", "that", "this", "those", "these", "something", "test"} for token in tokens):
        return "incomplete_query"

    if len(tokens) <= 2 and all(token in STOP_WORDS for token in tokens):
        return "incomplete_query"

    has_context = bool(context.get("last_successful_plan") or context.get("resolved_entity") or context.get("last_question"))
    if has_context and len(tokens) <= 2 and any(token in TIME_HINTS or token in ANALYTICAL_HINTS for token in tokens):
        return "valid_query"

    has_analytical_hint = any(token in ANALYTICAL_HINTS for token in tokens) or any(term in normalized for term in ["sales", "revenue", "units", "inventory", "promotion", "uplift", "growth", "compare", "rank", "trend", "share", "contribution", "anomaly", "spike", "complete", "completeness", "quality", "dataset", "stockout", "closing", "opening", "price"])
    has_time_hint = any(token in TIME_HINTS for token in tokens)
    has_filter_hint = any(token in {"south", "north", "east", "west", "central", "fruit", "juice", "water", "tea", "drinks", "coca", "cola"} for token in tokens)

    if not has_analytical_hint and not has_time_hint and not has_filter_hint:
        if any(token in {"what", "which", "show", "tell", "hello", "hi", "hey", "test", "something"} for token in tokens):
            return "incomplete_query"
        if len(tokens) <= 3 and any(token in {"that", "this", "those", "them", "it", "one"} for token in tokens):
            return "ambiguous_query"
        return "malformed_input"

    if len(tokens) <= 3 and any(token in {"that", "this", "those", "them", "it", "one"} for token in tokens):
        if has_context:
            return "valid_query"
        return "ambiguous_query"

    return "valid_query"


def reset_current_display_state(state: Dict[str, Any]) -> None:
    state["current_request"] = ""
    state["current_status"] = "idle"
    state["current_plan"] = None
    state["current_response"] = None
    state["current_data"] = []
    state["current_chart"] = None
    state["current_metrics"] = {}
    state["current_sql"] = ""


def deductuplicate_filters(filters: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    deduped: List[Dict[str, Any]] = []
    for item in filters:
        key = (item.get("field"), item.get("operator"), repr(item.get("value")))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(deepcopy(item))
    return deduped


def deduplicate_dimensions(dimensions: List[str]) -> List[str]:
    seen = set()
    result: List[str] = []
    for item in dimensions:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def deduplicate_group_by(group_by: List[str]) -> List[str]:
    return deduplicate_dimensions(group_by)


def deduplicate_sort_conditions(sort_conditions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    result: List[Dict[str, Any]] = []
    for item in sort_conditions:
        key = (item.get("field"), item.get("direction"))
        if key in seen:
            continue
        seen.add(key)
        result.append(deepcopy(item))
    return result


def deduplicate_result_entities(entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    result: List[Dict[str, Any]] = []
    for item in entities:
        key = item.get("entity") or item.get("value")
        if key in seen:
            continue
        seen.add(key)
        result.append(deepcopy(item))
    return result


def deduplicate_history_entries(history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    result: List[Dict[str, Any]] = []
    for item in history:
        request_id = item.get("request_id")
        if request_id in seen:
            continue
        seen.add(request_id)
        result.append(deepcopy(item))
    return result


def classify_reference(reference: str, context: Dict[str, Any], current_plan: Optional[Dict[str, Any]] = None) -> str:
    if not reference:
        return "missing"
    entity = context.get("resolved_entity")
    if entity:
        return "resolved"
    return "missing"


def is_meaningful_follow_up(question: str, context: Dict[str, Any]) -> bool:
    q = question.lower().strip()
    if not q:
        return False
    if any(token in q for token in ["for ", "in the ", "last month", "last quarter", "from ", "to ", "compare", "rank", "top", "bottom", "highest", "lowest", "instead", "only", "second", "third", "first", "last"]):
        return True
    return False


def segment_questions(text: str) -> List[Dict[str, Any]]:
    if not text or not text.strip():
        return []

    cleaned = text.strip()
    parts = []
    for raw in re.split(r"(?<=[?])\s+|\n+|\s*;\s*", cleaned):
        candidate = raw.strip()
        if not candidate:
            continue
        if re.search(r"[?]$", candidate) or re.search(r"\b(?:show|which|what|compare|rank|were|did|how|can|list)\b", candidate.lower()):
            parts.append(candidate)
    if not parts:
        parts = [cleaned]
    return [{"request_id": f"req-{idx + 1}", "text": part, "position": idx + 1} for idx, part in enumerate(parts)]


def classify_segment(question: str, context: Dict[str, Any]) -> str:
    q = question.lower().strip()
    if not q:
        return "unsupported_request"

    has_context = bool(context.get("last_successful_plan"))
    if any(token in q for token in ["what about", "that", "this", "those", "it", "them", "the second", "the third", "second", "third", "first", "last"]):
        if has_context and is_meaningful_follow_up(question, context):
            return "follow_up"

    if re.search(r"\b(?:show|which|what|compare|rank|were|did|how|can|list)\b", q):
        if has_context and any(token in q for token in ["for ", "in the ", "last month", "last quarter", "from ", "to ", "compare", "rank", "top", "bottom", "highest", "lowest", "instead", "only", "second", "third", "first", "last"]):
            return "follow_up"
        return "independent_question"
    return "unsupported_request"


def prepare_ordinal_follow_up(question: str, plan: Dict[str, Any]) -> Dict[str, Any]:
    prepared = deepcopy(plan)
    prepared["ordinal_position"] = None
    lowered = question.lower()
    if "second" in lowered:
        prepared["ordinal_position"] = 2
    elif "third" in lowered:
        prepared["ordinal_position"] = 3
    elif "first" in lowered or "next" in lowered:
        prepared["ordinal_position"] = 1
    elif "last" in lowered:
        prepared["ordinal_position"] = "last"
    if prepared.get("limit") in {1, None}:
        prepared["limit"] = max(2, prepared.get("limit") or 2)
    if prepared.get("operation_type") == "rank":
        prepared["limit"] = max(prepared.get("limit", 2), 2)
    return prepared

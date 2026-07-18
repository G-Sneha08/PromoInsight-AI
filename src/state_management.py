from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Optional, Tuple


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
    if any(token in q for token in ["for ", "in the ", "last month", "last quarter", "from ", "to ", "compare", "rank", "top", "bottom", "highest", "lowest", "instead", "only"]):
        return True
    return False

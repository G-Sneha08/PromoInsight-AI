import re
from typing import List, Optional, Tuple, Dict, Any
from src.models import QueryPlan, OperationPlan, FilterCondition, TimeRange, ComparisonConfig, SortCondition
from src.schema_context import SchemaContext
from src.state_management import classify_input

# Reusable synonym maps for dimensions and metrics
DIMENSION_MAP: Dict[str, List[str]] = {
    "region_name": ["region", "regions", "territory", "territories", "area", "areas"],
    "category": ["category", "categories", "beverage category", "segment", "segments"],
    "brand": ["brand", "brands"],
    "product_name": ["product", "products", "item", "items", "sku", "skus"],
    "promotion_id": ["promotion", "promotions", "campaign", "campaigns", "offer", "offers"]
}

# Semantic phrase groups ordered by precedence (higher score wins)
DATA_QUALITY_PHRASES = [
    r"data completeness", r"data quality", r"completeness", r"how complete",
    r"missing records", r"missing values", r"missing data", r"duplicate records",
    r"duplicates", r"invalid records", r"referential integrity", r"data gaps",
    r"\bcomplete\b",
]

CONTRIBUTION_PHRASES = [
    r"share of revenue", r"revenue share", r"percentage of revenue",
    r"percentage of total sales", r"contribution to revenue",
    r"contributed to total sales", r"proportion of total sales",
    r"share of total", r"\bcontribution\b", r"\bshare\b",
]

GROWTH_PHRASES = [
    r"\bgrowth\b", r"\bgrew\b", r"sales growth", r"increase compared with",
    r"decrease compared with", r"change from previous period",
    r"month-over-month", r"month over month", r"\bmom\b",
    r"year-over-year", r"year over year", r"\byoy\b", r"\bdecline\b",
]

MOM_PHRASES = [
    r"month-over-month", r"month over month", r"\bmom\b",
]

PROMOTION_UPLIFT_PHRASES = [
    r"\buplift\b", r"promotion impact", r"effectiveness", r"improve sales",
    r"promotion uplift", r"campaign uplift",
]

ANOMALY_PHRASES = [
    r"\banomaly\b", r"\bspike\b", r"\bspikes\b", r"\babnormal\b", r"\bunusual\b",
]

INVENTORY_STATUS_PHRASES = [
    r"stockout", r"stock out", r"at risk", r"excess inventory", r"overstock",
    r"low stock", r"stockout risk",
]

EXPLICIT_INVENTORY_METRIC_PHRASES = {
    "closing_inventory": [r"closing inventory", r"\bclosing\b"],
    "opening_inventory": [r"opening inventory", r"\bopening\b"],
    "sell_through_percentage": [r"sell-through", r"sell through"],
    "inventory_reduction_percentage": [r"inventory reduction"],
    "stockout_risk": [r"stockout risk"],
    "excess_inventory": [r"excess inventory"],
}

RANKING_PHRASES = [
    r"\btop\b", r"\bbottom\b", r"\bhighest\b", r"\blowest\b", r"\brank\b",
    r"\bbest\b", r"\bworst\b", r"\bwhich\b",
]

COMPARISON_PHRASES = [
    r"\bcompare\b", r"\bversus\b", r"\bvs\b", r"across all",
]

GROUPING_PHRASES = [
    r"\bby category\b", r"\bby brand\b", r"\bby product\b", r"\bby region\b",
    r"\bby promotion\b", r"\bacross\b", r"\beach\b",
]

UNCLEAR_PRONOUN_PATTERNS = [
    (r"what about that\b", "that"),
    (r"what about it\b", "it"),
    (r"and that one\b", "that"),
    (r"show that\b", "that"),
    (r"how about those\b", "those"),
    (r"what about the same\b", "the same"),
    (r"and this one\b", "this"),
    (r"what about this\b", "this"),
]

DATASET_SCOPE_PATTERNS = {
    "inventory": [r"inventory dataset", r"inventory data", r"inventory table", r"inventory log"],
    "sales": [r"sales dataset", r"sales data", r"sales table"],
    "promotions": [r"promotion dataset", r"promotion data", r"promotion table", r"campaign data"],
    "products": [r"product dataset", r"product data", r"product table"],
    "regions": [r"region dataset", r"region data", r"region table"],
}


class RuleBasedParser:
    def __init__(self):
        self.summary = SchemaContext.get_database_summary()
        self.regions = self.summary.get("regions", ["North", "South", "East", "West", "Central"])
        self.categories = self.summary.get("categories", ["Carbonated Drinks", "Packaged Water", "Fruit Juice", "Energy Drinks", "Iced Tea"])

    def parse(self, question: str, history: Optional[List[QueryPlan]] = None) -> QueryPlan:
        q = question.lower().strip()

        history_context = {}
        if history:
            last_plan = history[-1]
            history_context = {
                "last_successful_plan": last_plan.model_dump() if hasattr(last_plan, "model_dump") else last_plan,
                "resolved_entity": getattr(last_plan, "resolved_entity", None),
                "last_question": getattr(last_plan, "assumptions", None),
            }

        if re.search(r"^which one (was|performed)( the)? best\??$", q):
            return QueryPlan(
                needs_clarification=True,
                clarification_question="Should I compare regions, categories, brands, products, or promotions?",
                assumptions=["User asked for a vague best-performing item without specifying the entity or metric."]
            )

        classification = classify_input(question, history_context)
        if classification != "valid_query":
            if classification == "ambiguous_query":
                return QueryPlan(
                    needs_clarification=True,
                    clarification_question="Please clarify which business metric or entity you want to analyse.",
                    assumptions=["Input was classified as ambiguous."
                ])
            return QueryPlan(operations=[])

        # Out-of-scope / unsupported questions
        out_of_scope_terms = [
            "salary", "salaries", "employee", "employees", "staff",
            "cost", "profit", "margin", "expense", "expenses", "weather",
            "customer", "customers", "feedback", "reviews", "ratings",
            "why can this question", "not be answered"
        ]
        if any(term in q for term in out_of_scope_terms):
            return QueryPlan(operations=[])

        # Ambiguity check for "best product" without specified metric
        if "best product" in q or "top product" in q or "best performing product" in q:
            if not any(m in q for m in ["sales", "revenue", "units", "uplift", "margin"]):
                return QueryPlan(
                    needs_clarification=True,
                    clarification_question="Should 'best' product be measured by total sales revenue, units sold, or promotional sales uplift?",
                    assumptions=["User asked for 'best product' without specifying the success metric."]
                )

        # Unresolved pronouns without valid context
        if q in {"which one was the best", "which one performed best", "which one was best", "which one performed best?"}:
            return QueryPlan(
                needs_clarification=True,
                clarification_question="Should I compare regions, categories, brands, products, or promotions?",
                assumptions=["User asked for a vague best-performing item without specifying the entity or metric."]
            )

        pronoun_clarification = self._check_unclear_pronoun(q, history)
        if pronoun_clarification:
            return pronoun_clarification

        # Semantic resolution (operation + metric with precedence)
        semantic = self._resolve_semantic(q)
        operation_type = semantic["operation_type"]
        metric = semantic["metric"]
        dataset_scope = semantic.get("dataset_scope")

        time_granularity, has_time_dim = self._resolve_time_granularity(q)
        detected_dims = self._resolve_dimensions(q)

        # Extract filters early (needed for contribution dimension inference)
        region_filter = self._extract_region(q)
        category_filter = self._extract_category(q)
        product_filter = self._extract_product(q)
        promo_filter = self._extract_promotion(q)
        time_range = self._extract_time_range(q)
        filters = [f for f in [region_filter, category_filter, product_filter, promo_filter] if f]

        # Resolve dimensions and grouping
        dimensions, group_by = self._resolve_grouping(
            q, operation_type, metric, detected_dims, has_time_dim, filters
        )

        # Clarification only when user explicitly requests rank/compare/group without dimension
        if self._needs_dimension_clarification(q, operation_type, dimensions, has_time_dim):
            return QueryPlan(
                needs_clarification=True,
                clarification_question="Should I compare regions, categories, brands, products, or promotions?",
                assumptions=["User requested ranking or comparison without specifying a target dimension."]
            )

        limit = self._resolve_limit(q)
        plan = QueryPlan()

        # Follow-up context merging
        prev_plan = history[-1] if history and len(history) > 0 else None
        is_follow_up = self._is_follow_up(q, prev_plan)

        if is_follow_up and prev_plan and len(prev_plan.operations) > 0:
            prev_op = prev_plan.operations[0]
            inherited_fields = []

            if not metric or (metric == "total_sales" and "sales" not in q and "revenue" not in q):
                metric = prev_op.metric
                operation_type = prev_op.operation_type
                inherited_fields.append("metric")

            merged_filters = list(prev_op.filters)
            for nf in filters:
                merged_filters = [f for f in merged_filters if f.field != nf.field]
                merged_filters.append(nf)
            filters = merged_filters

            if prev_plan.resolved_entity:
                ref_field = prev_plan.resolved_entity.get("field")
                ref_val = prev_plan.resolved_entity.get("value")
                if ref_field and ref_val:
                    has_override = any(nf.field == ref_field for nf in filters)
                    if not has_override:
                        filters = [f for f in filters if f.field != ref_field]
                        filters.append(FilterCondition(field=ref_field, operator="equals", value=ref_val))
                        inherited_fields.append(f"resolved_entity ({ref_field}={ref_val})")

            if not time_range:
                time_range = prev_op.time_range
                inherited_fields.append("time_range")

            if not dimensions:
                dimensions = prev_op.dimensions
                if prev_op.dimensions:
                    inherited_fields.append("dimensions")

            if not group_by:
                group_by = prev_op.group_by
                if prev_op.group_by:
                    inherited_fields.append("group_by")

            limit = prev_op.limit if limit is None else limit
            time_granularity = prev_op.time_granularity if not time_granularity else time_granularity
            comparison = prev_op.comparison
            dataset_scope = dataset_scope or prev_op.dataset_scope

            if inherited_fields:
                plan.assumptions.append(f"Merged conversational context for: {', '.join(inherited_fields)}.")
        else:
            comparison = None
            if operation_type == "growth":
                comparison = ComparisonConfig(method="previous_weeks", number_of_weeks=4)
            elif operation_type == "promotion_uplift":
                comparison = ComparisonConfig(method="previous_non_promotional_weeks", number_of_weeks=4)

            if not time_range:
                if operation_type == "trend":
                    time_range = TimeRange(type="relative", value="previous_90_days")
                    plan.assumptions.append("Defaulted trend analysis to previous 90 days.")
                elif "last month" in q:
                    time_range = TimeRange(type="relative", value="last_month")
                elif "last quarter" in q:
                    time_range = TimeRange(type="relative", value="last_quarter")

        order_by = []
        if operation_type in ["rank", "promotion_uplift", "growth"]:
            direction = "ascending" if any(w in q for w in ["bottom", "lowest", "worst", "underperforming", "decline"]) else "descending"
            order_by.append(SortCondition(field=metric or "total_sales", direction=direction))

        op_plan = OperationPlan(
            operation_type=operation_type,
            metric=metric or "total_sales",
            dimensions=dimensions,
            filters=filters,
            time_range=time_range,
            comparison=comparison,
            group_by=group_by,
            order_by=order_by,
            limit=limit,
            time_granularity=time_granularity,
            dataset_scope=dataset_scope,
        )

        plan.operations = [op_plan]
        return plan

    def _matches_any(self, q: str, patterns: List[str]) -> bool:
        return any(re.search(pat, q) for pat in patterns)

    def _resolve_semantic(self, q: str) -> Dict[str, Any]:
        """Score-based semantic resolver: most specific analytical phrase wins."""
        candidates: List[Tuple[str, str, int]] = []

        if self._matches_any(q, DATA_QUALITY_PHRASES):
            candidates.append(("data_quality", "data_completeness_percentage", 100))

        if self._matches_any(q, CONTRIBUTION_PHRASES):
            candidates.append(("contribution", "revenue_contribution_percentage", 90))

        if self._matches_any(q, GROWTH_PHRASES):
            growth_metric = "month_over_month_growth" if self._matches_any(q, MOM_PHRASES) else "sales_growth_percentage"
            candidates.append(("growth", growth_metric, 80))

        if self._matches_any(q, PROMOTION_UPLIFT_PHRASES) or (
            re.search(r"\bpromotion\b", q) and re.search(r"\b(uplift|impact|effectiveness|improve)\b", q)
        ):
            candidates.append(("promotion_uplift", "promotion_uplift_percentage", 70))

        if self._matches_any(q, ANOMALY_PHRASES):
            candidates.append(("anomaly_detection", "total_sales", 60))

        # Explicit inventory metrics before generic inventory status
        for inv_metric, patterns in EXPLICIT_INVENTORY_METRIC_PHRASES.items():
            if inv_metric == "closing_inventory" and re.search(r"\bclosing\b", q) and "inventory" in q:
                op = "rank" if self._matches_any(q, RANKING_PHRASES) else "aggregate"
                candidates.append((op, "closing_inventory", 55))
                break
            elif inv_metric == "opening_inventory" and re.search(r"\bopening\b", q) and "inventory" in q:
                op = "rank" if self._matches_any(q, RANKING_PHRASES) else "aggregate"
                candidates.append((op, "opening_inventory", 55))
                break
            elif self._matches_any(q, patterns):
                op = "rank" if self._matches_any(q, RANKING_PHRASES) else "aggregate"
                candidates.append((op, inv_metric, 55))

        if self._matches_any(q, INVENTORY_STATUS_PHRASES):
            candidates.append(("inventory_status", "stockout_risk", 58))

        if re.search(r"\baverage selling price\b", q) or re.search(r"\basp\b", q) or (
            "average" in q and "price" in q
        ):
            candidates.append(("aggregate", "average_selling_price", 40))

        if re.search(r"\bunits\b", q) or "quantity sold" in q or "how many" in q:
            candidates.append(("aggregate", "total_units", 30))

        # Structural operations (lower priority than specialized analytics)
        if self._matches_any(q, RANKING_PHRASES):
            candidates.append(("rank", None, 35))
        if self._matches_any(q, COMPARISON_PHRASES):
            candidates.append(("compare", None, 34))
        if "trend" in q or "over time" in q:
            candidates.append(("trend", None, 33))

        # Generic sales/revenue fallback (lowest priority)
        if re.search(r"\b(sales|revenue)\b", q):
            candidates.append(("aggregate", "total_sales", 20))

        dataset_scope = self._resolve_dataset_scope(q)

        if not candidates:
            return {"operation_type": "aggregate", "metric": "total_sales", "dataset_scope": dataset_scope}

        candidates.sort(key=lambda x: x[2], reverse=True)
        operation_type, metric, _ = candidates[0]

        # Fill metric for structural operations that did not set one
        if metric is None:
            metric = self._resolve_metric_from_context(q, operation_type)

        return {"operation_type": operation_type, "metric": metric, "dataset_scope": dataset_scope}

    def _resolve_metric_from_context(self, q: str, operation_type: str) -> str:
        """Resolve metric when operation type is structural (rank/compare/trend)."""
        if re.search(r"\bunits\b", q) or "quantity" in q:
            return "total_units"
        if "average" in q and "price" in q:
            return "average_selling_price"
        if "closing inventory" in q or (re.search(r"\bclosing\b", q) and "inventory" in q):
            return "closing_inventory"
        if "opening inventory" in q or (re.search(r"\bopening\b", q) and "inventory" in q):
            return "opening_inventory"
        if operation_type == "promotion_uplift":
            return "promotion_uplift_percentage"
        if operation_type == "growth":
            return "month_over_month_growth" if self._matches_any(q, MOM_PHRASES) else "sales_growth_percentage"
        if operation_type == "contribution":
            return "revenue_contribution_percentage"
        if operation_type == "data_quality":
            return "data_completeness_percentage"
        if operation_type == "inventory_status":
            return "stockout_risk"
        return "total_sales"

    def _resolve_dataset_scope(self, q: str) -> Optional[str]:
        for scope, patterns in DATASET_SCOPE_PATTERNS.items():
            if self._matches_any(q, patterns):
                return scope
        # Broader scope hints when paired with data-quality context
        if self._matches_any(q, DATA_QUALITY_PHRASES):
            if re.search(r"\binventory\b", q) and "closing" not in q and "opening" not in q:
                if "dataset" in q or "data" in q or "complete" in q:
                    return "inventory"
            if re.search(r"\bsales\b", q) and ("dataset" in q or "data" in q):
                return "sales"
            if re.search(r"\bpromotion", q) and ("dataset" in q or "data" in q):
                return "promotions"
            return "overall"
        return None

    def _resolve_grouping(
        self,
        q: str,
        operation_type: str,
        metric: Optional[str],
        detected_dims: List[str],
        has_time_dim: bool,
        filters: List[FilterCondition],
    ) -> Tuple[List[str], List[str]]:
        dimensions = list(detected_dims)
        group_by = list(detected_dims)

        if has_time_dim and not dimensions:
            pass  # time acts as grouping for trends
        elif operation_type == "contribution":
            if not dimensions:
                dimensions = self._infer_contribution_dimension(q, filters)
                group_by = list(dimensions)
        elif operation_type in ["rank", "compare"] and not dimensions and not has_time_dim:
            if self._explicitly_needs_dimension(q):
                pass  # will trigger clarification
            elif operation_type == "rank":
                dimensions = ["product_name"]
                group_by = ["product_name"]
        elif operation_type == "growth" and not dimensions:
            for dim, keywords in DIMENSION_MAP.items():
                for kw in keywords:
                    if re.search(r'\b' + re.escape(kw) + r'\b', q):
                        dimensions = [dim]
                        group_by = [dim]
                        break
                if dimensions:
                    break
        elif operation_type == "inventory_status" and not dimensions:
            if "product" in q or "which" in q:
                dimensions = ["product_name"]
                group_by = ["product_name"]
        elif operation_type in ["promotion_uplift"] and not dimensions:
            if self._explicitly_needs_dimension(q):
                dimensions = ["promotion_id"]
                group_by = ["promotion_id"]

        if metric in ("closing_inventory", "opening_inventory") and operation_type == "aggregate":
            if not detected_dims and not self._matches_any(q, GROUPING_PHRASES):
                dimensions = []
                group_by = []

        return dimensions, group_by

    def _infer_contribution_dimension(self, q: str, filters: List[FilterCondition]) -> List[str]:
        for f in filters:
            if f.field == "category":
                return ["category"]
            if f.field == "region_name":
                return ["region_name"]
            if f.field == "brand":
                return ["brand"]
            if f.field in ("product_id", "product_name"):
                return ["product_name"]
        for dim, keywords in DIMENSION_MAP.items():
            for kw in keywords:
                if f"by {kw}" in q or f"contribution by {kw}" in q:
                    return [dim]
        if "brand" in q:
            return ["brand"]
        if "region" in q:
            return ["region_name"]
        if "category" in q or "categories" in q:
            return ["category"]
        if "product" in q:
            return ["product_name"]
        return ["category"]

    def _explicitly_needs_dimension(self, q: str) -> bool:
        return (
            self._matches_any(q, RANKING_PHRASES)
            or self._matches_any(q, COMPARISON_PHRASES)
            or self._matches_any(q, GROUPING_PHRASES)
            or bool(re.search(r"which (product|region|category|brand|promotion)", q))
        )

    def _needs_dimension_clarification(
        self, q: str, operation_type: str, dimensions: List[str], has_time_dim: bool
    ) -> bool:
        if dimensions or has_time_dim:
            return False
        if operation_type not in ["rank", "compare", "contribution", "growth", "promotion_uplift", "inventory_status"]:
            return False
        if not self._explicitly_needs_dimension(q):
            return False
        vague_terms = [
            r"\bwhich\s+one\b", r"\bwhich\s+performed\b", r"\bwhich\s+was\b",
            r"\bwhat\s+performed\b", r"\bwhat\s+was\b", r"\bwhich\s+had\b",
            r"\bcompare\b", r"\brank\b"
        ]
        if any(re.search(pat, q) for pat in vague_terms) or len(q.split()) <= 4:
            return True
        return False

    def _check_unclear_pronoun(self, q: str, history: Optional[List[QueryPlan]]) -> Optional[QueryPlan]:
        has_valid_history = (
            history
            and len(history) > 0
            and history[-1].operations
            and not history[-1].needs_clarification
        )
        for pattern, pronoun in UNCLEAR_PRONOUN_PATTERNS:
            if re.search(pattern, q):
                if not has_valid_history:
                    return QueryPlan(
                        needs_clarification=True,
                        clarification_question=f"Could you clarify what '{pronoun}' refers to?",
                        assumptions=["Unresolved pronoun with no conversational context."]
                    )
                break
        return None

    def _is_follow_up(self, q: str, prev_plan: Optional[QueryPlan]) -> bool:
        if not prev_plan or prev_plan.needs_clarification or not prev_plan.operations:
            return False
        fragment_indicators = ["what about", "only", "instead", "for ", "in the ", "compare ", "show "]
        pronoun_follow_up = any(re.search(p, q) for p, _ in UNCLEAR_PRONOUN_PATTERNS)
        if pronoun_follow_up:
            return True
        return any(ind in q for ind in fragment_indicators) or len(q.split()) < 5

    def _resolve_dimensions(self, q: str) -> List[str]:
        dims = []
        rank_context = self._matches_any(q, RANKING_PHRASES + COMPARISON_PHRASES)
        for dim, keywords in DIMENSION_MAP.items():
            for kw in keywords:
                if not re.search(r'\b' + re.escape(kw) + r'\b', q):
                    continue
                if self._is_dimension_reference(q, kw):
                    dims.append(dim)
                    break
                if rank_context and re.search(r'\b' + re.escape(kw) + r'\b', q):
                    dims.append(dim)
                    break
        return dims

    def _is_dimension_reference(self, q: str, kw: str) -> bool:
        if re.search(rf"\bby\b.*\b{re.escape(kw)}\b", q):
            return True
        if re.search(rf"\bfor\b.*\b{re.escape(kw)}\b", q):
            return True
        if re.search(rf"\bacross\b.*\b{re.escape(kw)}\b", q):
            return True
        if re.search(rf"\bcompare\b.*\b{re.escape(kw)}\b", q):
            return True
        if re.search(rf"\brank\b.*\b{re.escape(kw)}\b", q):
            return True
        if re.search(rf"\bgroup(?:ed)? by\b.*\b{re.escape(kw)}\b", q):
            return True
        return False

    def _resolve_operation_type(self, q: str) -> str:
        """Legacy helper; prefer _resolve_semantic."""
        return self._resolve_semantic(q)["operation_type"]

    def _resolve_time_granularity(self, q: str) -> Tuple[Optional[str], bool]:
        if re.search(r'\b(date|day|daily)\b', q):
            return "daily", True
        if re.search(r'\b(week|weekly)\b', q):
            return "weekly", True
        if re.search(r'\b(month|monthly)\b', q):
            return "monthly", True
        return None, False

    def _resolve_limit(self, q: str) -> Optional[int]:
        if "second" in q or "2nd" in q:
            return 2
        limit_match = re.search(
            r'\b(top|highest|best|bottom|lowest|worst|rank)\s+(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\b', q
        )
        word_to_num = {
            "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
            "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10
        }
        if limit_match:
            num_str = limit_match.group(2)
            if num_str.isdigit():
                return int(num_str)
            if num_str in word_to_num:
                return word_to_num[num_str]

        dim_match = re.search(
            r'\b(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s+(product|category|brand|region|promotion|item|sku|campaign|segment|area|territory)s?\b', q
        )
        if dim_match:
            num_str = dim_match.group(1)
            if num_str.isdigit():
                return int(num_str)
            if num_str in word_to_num:
                return word_to_num[num_str]

        singular_patterns = [
            r'\bwhich\s+(region|category|brand|product|item|sku|promotion|campaign|one)\b',
            r'\b(highest|best|top|lowest|worst|bottom)\s+(region|category|brand|product|item|sku|promotion|campaign)\b'
        ]
        if any(re.search(pat, q) for pat in singular_patterns):
            return 1

        return None

    def _extract_region(self, q: str) -> Optional[FilterCondition]:
        for r in self.regions:
            if r.lower() in q:
                return FilterCondition(field="region_name", operator="equals", value=r)
        return None

    def _extract_category(self, q: str) -> Optional[FilterCondition]:
        for c in self.categories:
            if c.lower() in q:
                return FilterCondition(field="category", operator="equals", value=c)
        return None

    def _extract_product(self, q: str) -> Optional[FilterCondition]:
        for p in self.summary.get("products", []):
            p_name = p["product_name"].lower()
            p_id = p["product_id"].lower()
            if p_id in q or p_name in q or (len(p_name.split()) > 1 and p_name.split()[0] in q and p_name.split()[1] in q):
                return FilterCondition(field="product_id", operator="equals", value=p["product_id"])
        return None

    def _extract_promotion(self, q: str) -> Optional[FilterCondition]:
        promo_match = re.search(r'prom\d+', q)
        if promo_match:
            return FilterCondition(field="promotion_id", operator="equals", value=promo_match.group(0).upper())

        for p in self.summary.get("promotions", []):
            if p["promotion_name"].lower() in q:
                return FilterCondition(field="promotion_id", operator="equals", value=p["promotion_id"])

        p_ref = re.search(r'promotion\s+p?(\d+)', q)
        if p_ref:
            return FilterCondition(field="promotion_id", operator="equals", value=f"PROM{int(p_ref.group(1)):02d}")

        return None

    def _extract_time_range(self, q: str) -> Optional[TimeRange]:
        relative_patterns = [
            ("last month", "last_month"),
            ("this month", "this_month"),
            ("last week", "last_week"),
            ("this week", "this_week"),
            ("last quarter", "last_quarter"),
            ("this quarter", "this_quarter"),
            ("last year", "last_year"),
            ("this year", "this_year"),
            ("yesterday", "yesterday"),
            ("today", "today"),
            ("previous 7 days", "previous_7_days"),
            ("previous 30 days", "previous_30_days"),
            ("previous 90 days", "previous_90_days"),
            ("latest campaign", "latest_campaign")
        ]

        for pat, val in relative_patterns:
            if pat in q:
                return TimeRange(type="relative", value=val)

        dates = re.findall(r'\b\d{4}-\d{2}-\d{2}\b', q)
        if len(dates) == 2:
            return TimeRange(type="absolute", start_date=dates[0], end_date=dates[1])
        if len(dates) == 1:
            return TimeRange(type="absolute", start_date=dates[0], end_date=dates[0])

        return None

import re
import logging
from typing import Tuple, List, Set
from src.models import QueryPlan, OperationPlan
from src.metadata_catalog import METADATA_CATALOG, is_valid_column, get_field_table
from src.metric_catalog import METRIC_CATALOG
from src.utils import logger

# Synonym maps for user dimension extraction during consistency check
DIMENSION_KEYWORDS = {
    "region_name": ["region", "regions", "territory", "territories", "area", "areas"],
    "category": ["category", "categories", "beverage category", "segment", "segments"],
    "brand": ["brand", "brands"],
    "product_name": ["product", "products", "item", "items", "sku", "skus"],
    "promotion_id": ["promotion", "promotions", "campaign", "campaigns", "offer", "offers"]
}

class QueryValidator:
    @staticmethod
    def validate(plan: QueryPlan) -> Tuple[bool, str]:
        """Validates a QueryPlan against schema catalogs, metrics, and business logic."""
        if plan.needs_clarification:
            return True, "Ambiguous query plan - clarification requested."
            
        if not plan.operations:
            return False, "This question cannot be answered reliably from the currently available sales, promotion, product, region and inventory data."
            
        for op in plan.operations:
            is_ok, msg = QueryValidator._validate_operation(op)
            if not is_ok:
                return False, msg
                
        return True, "Query plan successfully validated."

    @staticmethod
    def validate_consistency(plan: QueryPlan, sql: str, question: str) -> Tuple[bool, str]:
        """Performs safety consistency verification between query text, parsed plan, and compiled SQL."""
        if plan.needs_clarification or not plan.operations:
            return True, "Consistency check bypassed for empty or clarification plans."
            
        op = plan.operations[0]
        q = question.lower()
        
        # 1. Detect user-mentioned dimensions based on grouping/projection context
        user_dims: List[str] = []
        for dim, keywords in DIMENSION_KEYWORDS.items():
            # Match singular/plural words or grouping contexts
            group_contexts = [
                f"each {keywords[0]}", f"by {keywords[0]}", 
                f"compare {keywords[1]}", f"which {keywords[0]}", 
                f"rank {keywords[1]}", f"across {keywords[1]}", 
                f"across all {keywords[1]}", f"inventory by {keywords[0]}"
            ]
            # Also capture basic mentions if ranking is present
            has_rank_context = any(w in q for w in ["top", "bottom", "highest", "lowest", "best", "worst", "rank", "compare"])
            has_explicit_mention = any(re.search(r'\b' + re.escape(kw) + r'\b', q) for kw in keywords)
            
            if any(ctx in q for ctx in group_contexts) or (has_rank_context and has_explicit_mention):
                user_dims.append(dim)
                
        parsed_dims = op.dimensions
        group_by_fields = op.group_by
        
        # 2. Check dimension consistency
        # User mentioned a grouping dimension but it was not parsed
        for dim in user_dims:
            if dim not in parsed_dims:
                return False, f"Consistency check failed: User question requests analysis of '{dim}', but parsed dimensions do not contain it."
                
        # Group by fields must match dimensions
        if set(group_by_fields) != set(parsed_dims):
            return False, f"Consistency check failed: Plan grouping fields '{group_by_fields}' do not match parsed dimensions '{parsed_dims}'."
            
        # 3. Check compiled SQL matches
        sql_upper = sql.upper()
        
        # Every dimension must appear in the SQL text
        for dim in parsed_dims:
            # Check column name exists in SQL
            if dim not in sql:
                return False, f"Consistency check failed: Dimension '{dim}' is missing from compiled SQL statement."
                
        # If group_by_fields exists, SQL must contain GROUP BY and those fields
        if group_by_fields and op.operation_type not in ["promotion_uplift", "data_quality"]:
            if "GROUP BY" not in sql_upper:
                return False, "Consistency check failed: Plan specifies grouping but compiled SQL lacks GROUP BY clause."
            for grp in group_by_fields:
                if grp not in sql:
                    return False, f"Consistency check failed: Grouping field '{grp}' is missing from SQL GROUP BY clause."
                    
        # Check that correct joins are present based on fields
        tables_in_sql = set()
        for tbl in ["products", "regions", "promotions", "sales", "inventory"]:
            if tbl in sql.lower():
                tables_in_sql.add(tbl)
                
        for dim in parsed_dims:
            tbl = get_field_table(dim)
            if tbl not in tables_in_sql:
                return False, f"Consistency check failed: Compiled SQL does not join or reference the required table '{tbl}' for dimension '{dim}'."
                
        # 4. Perform architectural validation logging
        logger.info("=== ARCHITECTURE CONSISTENCY LOG ===")
        logger.info(f"User Question: '{question}'")
        logger.info(f"User Dimensions Detected: {user_dims}")
        logger.info(f"Final Dimensions Selected: {parsed_dims}")
        logger.info(f"Metric Selected: '{op.metric}'")
        logger.info(f"Grouping Selected: {group_by_fields}")
        logger.info(f"SQL Tables Used: {list(tables_in_sql)}")
        logger.info(f"SQL GROUP BY Used: {[g for g in group_by_fields if g in sql]}")
        logger.info("====================================")
        
        return True, "Consistency checks passed."

    @staticmethod
    def _validate_operation(op: OperationPlan) -> Tuple[bool, str]:
        # 1. Validate Metric
        if op.metric not in METRIC_CATALOG:
            return False, f"Unsupported metric: '{op.metric}'."
            
        metric_info = METRIC_CATALOG[op.metric]
        
        # 2. Validate Dimensions & Grouping
        tables_to_join = set()
        for col_ref in metric_info["required_columns"]:
            tbl = col_ref.split(".")[0]
            tables_to_join.add(tbl)
            
        for dim in op.dimensions:
            if not is_valid_column(dim):
                return False, f"This question cannot be answered reliably from the currently available sales, promotion, product, region and inventory data. Reason: Column '{dim}' does not exist."
            tables_to_join.add(get_field_table(dim))
            
        for grp in op.group_by:
            if not is_valid_column(grp):
                return False, f"Cannot group by unknown column '{grp}'."
            tables_to_join.add(get_field_table(grp))
            
        # 3. Validate Filters
        for f in op.filters:
            if not is_valid_column(f.field):
                return False, f"This question cannot be answered reliably from the currently available sales, promotion, product, region and inventory data. Reason: Filter field '{f.field}' does not exist."
            
            tbl = get_field_table(f.field)
            tables_to_join.add(tbl)
            
            col_meta = METADATA_CATALOG["tables"][tbl]["columns"][f.field]
            allowed_ops = col_meta.get("allowed_operators", [])
            if f.operator not in allowed_ops:
                return False, f"Operator '{f.operator}' is not supported for field '{f.field}'."
                
            if f.operator not in ["is_null", "is_not_null"] and f.value is None:
                return False, f"Filter on '{f.field}' requires a non-null comparison value."
                
        # 4. Validate Table Joins
        if len(tables_to_join) > 1:
            try:
                from src.metadata_catalog import get_join_path
                get_join_path(list(tables_to_join))
            except ValueError as join_err:
                return False, f"This question cannot be answered reliably because tables {list(tables_to_join)} cannot be joined safely."
                
        # 5. Validate Limits and Ordering
        if op.limit is not None:
            if op.limit < 1 or op.limit > 100:
                return False, "Ranking and limit count must be between 1 and 100."
                
        for s in op.order_by:
            if s.field != op.metric and not is_valid_column(s.field):
                return False, f"Invalid sorting field '{s.field}'."
                
        # 6. Validate Time range parameters
        if op.time_range:
            tr = op.time_range
            if tr.type == "absolute":
                if not tr.start_date or not tr.end_date:
                    return False, "Absolute time ranges require both start_date and end_date."
                import datetime
                try:
                    datetime.datetime.strptime(tr.start_date, "%Y-%m-%d")
                    datetime.datetime.strptime(tr.end_date, "%Y-%m-%d")
                except ValueError:
                    return False, "Dates must be formatted as YYYY-MM-DD."
                    
        return True, "Operation is valid."

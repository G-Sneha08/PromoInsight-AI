import sqlite3
import datetime
from typing import Tuple, List, Dict, Any, Optional
from src.models import OperationPlan, FilterCondition
from src.metadata_catalog import METADATA_CATALOG, get_field_table, get_join_path, is_valid_column
from src.metric_catalog import METRIC_CATALOG
from src.schema_context import SchemaContext

class SQLCompiler:
    def __init__(self):
        # We can dynamically retrieve the dataset's max date
        summary = SchemaContext.get_database_summary()
        max_date_str = summary.get("date_range", {}).get("max_date")
        if max_date_str:
            self.ref_date = datetime.datetime.strptime(max_date_str, "%Y-%m-%d").date()
        else:
            # Fallback default reference date matching the generation logic end_date
            self.ref_date = datetime.date(2026, 6, 30)
            
    def compile(self, op: OperationPlan) -> Tuple[str, List[Any]]:
        """Compiles an OperationPlan to (parameterized_sql_string, parameters_list)."""
        tables = set()
        
        # 1. Resolve tables needed from metric and dimensions
        metric_info = METRIC_CATALOG[op.metric]
        for col_ref in metric_info["required_columns"]:
            tables.add(col_ref.split(".")[0])
            
        for dim in op.dimensions:
            tables.add(get_field_table(dim))
            
        for grp in op.group_by:
            tables.add(get_field_table(grp))
            
        for f in op.filters:
            tables.add(get_field_table(f.field))
            
        # Determine main table. If sales is one of them, use sales. If inventory is one of them, use inventory.
        # Otherwise, choose products or promotions.
        main_table = "sales"
        if "sales" in tables:
            main_table = "sales"
        elif "inventory" in tables:
            main_table = "inventory"
        elif "promotions" in tables:
            main_table = "promotions"
        elif tables:
            main_table = list(tables)[0]
            
        # 2. Build SELECT projections
        projections = []
        
        # Add dimensions with table prefix
        for dim in op.dimensions:
            tbl = get_field_table(dim)
            # Safe column validation
            if not is_valid_column(dim):
                raise ValueError(f"Invalid column name: {dim}")
            projections.append(f"{tbl}.{dim} AS {dim}")
            
        # Add time bucketing if trend time_granularity specified
        date_column = self._get_date_column(main_table)
        if op.time_granularity and date_column:
            if op.time_granularity == "daily":
                projections.append(f"{main_table}.{date_column} AS trend_period")
            elif op.time_granularity == "weekly":
                # Group by week start (represented by Monday date)
                projections.append(f"date({main_table}.{date_column}, 'weekday 0', '-6 days') AS trend_period")
            elif op.time_granularity == "monthly":
                # Group by month string (YYYY-MM)
                projections.append(f"strftime('%Y-%m', {main_table}.{date_column}) AS trend_period")
                
        # Add Metric Formula
        metric_formula = metric_info["formula"]
        
        # Special calculated formulas
        if op.metric == "average_selling_price":
            metric_formula = "SUM(sales.sales_amount) / SUM(sales.units_sold)"
        elif op.metric == "average_daily_sales":
            metric_formula = "AVG(sales.units_sold)"
        elif op.metric in ["revenue_contribution_percentage", "sales_growth_percentage", "month_over_month_growth", "promotion_sales"]:
            metric_formula = "SUM(sales.sales_amount)"
        elif op.metric == "opening_inventory":
            metric_formula = "SUM(inventory.opening_inventory)"
        elif op.metric == "closing_inventory":
            metric_formula = "SUM(inventory.closing_inventory)"
        elif op.metric == "baseline_sales":
            metric_formula = "SUM(sales.sales_amount)"
        elif op.metric == "data_completeness_percentage":
            metric_formula = "100.0"
        elif op.metric == "inventory_reduction_percentage":
            metric_formula = "SUM(inventory.opening_inventory) - SUM(inventory.closing_inventory)"
        elif op.metric == "sell_through_percentage":
            metric_formula = "CAST(SUM(sales.units_sold) AS REAL) / (SUM(inventory.opening_inventory) + SUM(inventory.received_units)) * 100"
        elif op.metric == "stockout_risk":
            # Risk is days with closing inventory = 0 / total days
            # Compile as COUNT of days with closing_inventory = 0
            metric_formula = "COUNT(CASE WHEN inventory.closing_inventory = 0 THEN 1 END) * 100.0 / COUNT(*)"
        elif op.metric == "excess_inventory":
            # Needs closing inventory sum
            metric_formula = "SUM(inventory.closing_inventory)"
        
        # Inject SUM/AVG/COUNT according to valid aggregations if formula is not aggregated
        projections.append(f"{metric_formula} AS {op.metric}")
        
        # 3. Build FROM and JOINs
        join_paths = get_join_path(list(tables))
        from_clause = main_table
        joined_tables = {main_table}
        
        queue = list(join_paths)
        progress = True
        while queue and progress:
            progress = False
            deferred = []
            for j in queue:
                parts = j.split(" = ")
                t1 = parts[0].split(".")[0]
                t2 = parts[1].split(".")[0]
                
                # Case 1: Both already joined. Redundant path, skip.
                if t1 in joined_tables and t2 in joined_tables:
                    progress = True
                    continue
                # Case 2: t1 is joined, t2 is new. Join t2.
                elif t1 in joined_tables and t2 not in joined_tables:
                    from_clause += f" JOIN {t2} ON {j}"
                    joined_tables.add(t2)
                    progress = True
                # Case 3: t2 is joined, t1 is new. Join t1.
                elif t2 in joined_tables and t1 not in joined_tables:
                    from_clause += f" JOIN {t1} ON {j}"
                    joined_tables.add(t1)
                    progress = True
                # Case 4: Neither is joined yet. Defer.
                else:
                    deferred.append(j)
            queue = deferred
            
        # 4. Build WHERE and filter parameters
        where_clauses = []
        params = []
        
        # Date boundaries
        if op.time_range:
            start_date, end_date = self._resolve_time_range(op.time_range)
            if start_date and end_date and date_column:
                where_clauses.append(f"{main_table}.{date_column} BETWEEN ? AND ?")
                params.extend([start_date, end_date])
                
        # Normal filters
        for f in op.filters:
            tbl = get_field_table(f.field)
            if not is_valid_column(f.field):
                raise ValueError(f"Invalid column name: {f.field}")
                
            op_sql, val_params = self._compile_filter_condition(f"{tbl}.{f.field}", f.operator, f.value)
            where_clauses.append(op_sql)
            params.extend(val_params)
            
        where_clause_str = ""
        if where_clauses:
            where_clause_str = " WHERE " + " AND ".join(where_clauses)
            
        # 5. Build GROUP BY
        group_by_clauses = []
        for grp in op.group_by:
            tbl = get_field_table(grp)
            group_by_clauses.append(f"{tbl}.{grp}")
            
        if op.time_granularity and date_column:
            group_by_clauses.append("trend_period")
            
        group_by_str = ""
        if group_by_clauses:
            group_by_str = " GROUP BY " + ", ".join(group_by_clauses)
            
        # 6. Build ORDER BY
        order_by_clauses = []
        for s in op.order_by:
            # Safety check on sorting column
            if s.field != op.metric and not is_valid_column(s.field):
                raise ValueError(f"Invalid sorting field: {s.field}")
            direction = "DESC" if s.direction == "descending" else "ASC"
            order_by_clauses.append(f"{s.field} {direction}")
            
        order_by_str = ""
        if order_by_clauses:
            order_by_str = " ORDER BY " + ", ".join(order_by_clauses)
            
        # 7. Build LIMIT
        limit_str = ""
        if op.limit:
            limit_str = f" LIMIT {int(op.limit)}"
            
        # Combine
        sql = f"SELECT {', '.join(projections)} FROM {from_clause}{where_clause_str}{group_by_str}{order_by_str}{limit_str};"
        return sql, params

    def _get_date_column(self, table: str) -> Optional[str]:
        if table == "sales":
            return "sale_date"
        elif table == "inventory":
            return "snapshot_date"
        elif table == "promotions":
            return "start_date"
        return None

    def _compile_filter_condition(self, col: str, operator: str, value: Any) -> Tuple[str, List[Any]]:
        if operator == "equals":
            return f"{col} = ?", [value]
        elif operator == "not_equals":
            return f"{col} != ?", [value]
        elif operator == "in":
            if not isinstance(value, list):
                value = [value]
            placeholders = ", ".join(["?"] * len(value))
            return f"{col} IN ({placeholders})", list(value)
        elif operator == "not_in":
            if not isinstance(value, list):
                value = [value]
            placeholders = ", ".join(["?"] * len(value))
            return f"{col} NOT IN ({placeholders})", list(value)
        elif operator == "greater_than":
            return f"{col} > ?", [value]
        elif operator == "greater_than_or_equal":
            return f"{col} >= ?", [value]
        elif operator == "less_than":
            return f"{col} < ?", [value]
        elif operator == "less_than_or_equal":
            return f"{col} <= ?", [value]
        elif operator == "between":
            # value should be a list/tuple of two items
            if not isinstance(value, list) or len(value) != 2:
                raise ValueError("Between operator requires a list of 2 values.")
            return f"{col} BETWEEN ? AND ?", list(value)
        elif operator == "contains":
            return f"{col} LIKE ?", [f"%{value}%"]
        elif operator == "is_null":
            return f"{col} IS NULL", []
        elif operator == "is_not_null":
            return f"{col} IS NOT NULL", []
        else:
            raise ValueError(f"Unsupported filter operator: {operator}")

    def _resolve_time_range(self, tr: Any) -> Tuple[Optional[str], Optional[str]]:
        if tr.type == "absolute":
            return tr.start_date, tr.end_date
            
        ref = self.ref_date
        val = tr.value
        
        if val == "today":
            return ref.strftime("%Y-%m-%d"), ref.strftime("%Y-%m-%d")
        elif val == "yesterday":
            yesterday = ref - datetime.timedelta(days=1)
            return yesterday.strftime("%Y-%m-%d"), yesterday.strftime("%Y-%m-%d")
        elif val == "this week":
            # Monday of current week
            monday = ref - datetime.timedelta(days=ref.weekday())
            sunday = monday + datetime.timedelta(days=6)
            return monday.strftime("%Y-%m-%d"), sunday.strftime("%Y-%m-%d")
        elif val == "last week":
            # Monday of previous week
            monday = ref - datetime.timedelta(days=ref.weekday() + 7)
            sunday = monday + datetime.timedelta(days=6)
            return monday.strftime("%Y-%m-%d"), sunday.strftime("%Y-%m-%d")
        elif val == "this month":
            first_day = ref.replace(day=1)
            # Find last day of current month
            next_month = ref.replace(day=28) + datetime.timedelta(days=4)
            last_day = next_month - datetime.timedelta(days=next_month.day)
            return first_day.strftime("%Y-%m-%d"), last_day.strftime("%Y-%m-%d")
        elif val == "last_month" or val == "last month":
            # Find first day of previous month
            first_of_this = ref.replace(day=1)
            last_of_prev = first_of_this - datetime.timedelta(days=1)
            first_of_prev = last_of_prev.replace(day=1)
            return first_of_prev.strftime("%Y-%m-%d"), last_of_prev.strftime("%Y-%m-%d")
        elif val == "this quarter":
            quarter = (ref.month - 1) // 3 + 1
            first_day = datetime.date(ref.year, 3 * quarter - 2, 1)
            # Last day of quarter
            last_month = 3 * quarter
            if last_month in (3, 12):
                last_day = datetime.date(ref.year, last_month, 31)
            else:
                last_day = datetime.date(ref.year, last_month, 30)
            return first_day.strftime("%Y-%m-%d"), last_day.strftime("%Y-%m-%d")
        elif val == "last_quarter" or val == "last quarter":
            current_quarter = (ref.month - 1) // 3 + 1
            if current_quarter == 1:
                prev_quarter = 4
                year = ref.year - 1
            else:
                prev_quarter = current_quarter - 1
                year = ref.year
                
            first_day = datetime.date(year, 3 * prev_quarter - 2, 1)
            last_month = 3 * prev_quarter
            if last_month in (3, 12):
                last_day = datetime.date(year, last_month, 31)
            else:
                last_day = datetime.date(year, last_month, 30)
            return first_day.strftime("%Y-%m-%d"), last_day.strftime("%Y-%m-%d")
        elif val == "this year":
            return datetime.date(ref.year, 1, 1).strftime("%Y-%m-%d"), ref.strftime("%Y-%m-%d")
        elif val == "last_year" or val == "last year":
            return datetime.date(ref.year - 1, 1, 1).strftime("%Y-%m-%d"), datetime.date(ref.year - 1, 12, 31).strftime("%Y-%m-%d")
        elif val == "previous_7_days" or val == "previous 7 days":
            start = ref - datetime.timedelta(days=7)
            return start.strftime("%Y-%m-%d"), ref.strftime("%Y-%m-%d")
        elif val == "previous_30_days" or val == "previous 30 days":
            start = ref - datetime.timedelta(days=30)
            return start.strftime("%Y-%m-%d"), ref.strftime("%Y-%m-%d")
        elif val == "previous_90_days" or val == "previous 90 days":
            start = ref - datetime.timedelta(days=90)
            return start.strftime("%Y-%m-%d"), ref.strftime("%Y-%m-%d")
        elif val == "latest_campaign" or val == "latest campaign":
            # Retrieve date range of the latest promotion campaign in the database
            summary = SchemaContext.get_database_summary()
            promos = summary.get("promotions", [])
            if promos:
                # Sort by start_date descending
                sorted_promos = sorted(promos, key=lambda x: x["start_date"], reverse=True)
                return sorted_promos[0]["start_date"], sorted_promos[0]["end_date"]
            return None, None
            
        return None, None

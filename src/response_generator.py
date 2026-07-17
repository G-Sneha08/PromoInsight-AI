import re
import pandas as pd
from typing import Dict, Any, List, Optional
from src.metric_catalog import METRIC_CATALOG

# Reusable synonym maps for business-friendly labels
METRIC_LABELS = {
    "total_sales": "revenue",
    "total_units": "units sold",
    "average_selling_price": "average selling price",
    "sales_growth_percentage": "sales growth",
    "month_over_month_growth": "sales growth",
    "promotion_sales": "promotional sales",
    "baseline_sales": "baseline sales",
    "promotion_uplift_percentage": "promotional uplift",
    "opening_inventory": "opening inventory",
    "closing_inventory": "closing inventory",
    "inventory_reduction_percentage": "inventory reduction",
    "sell_through_percentage": "sell-through percentage",
    "stockout_risk": "stockout risk",
    "excess_inventory": "excess inventory",
    "data_completeness_percentage": "data completeness"
}

DIMENSION_LABELS = {
    "region_name": "region",
    "category": "category",
    "product_name": "product",
    "brand": "brand",
    "promotion_name": "promotion",
    "promotion_id": "promotion",
    "sale_date": "date"
}

FORBIDDEN_PHRASES = [
    "query returned",
    "analysis returned",
    "record",
    "with value of",
    "requested total sales is",
    "the requested",
    "result set contains",
    "according to the sql"
]

CAUSAL_WORDS = ["caused", "proved", "guaranteed", "definitely resulted in"]

class ResponseGenerator:
    # 1. Formatting Helpers
    @staticmethod
    def format_metric_name(metric_name: str) -> str:
        return METRIC_LABELS.get(metric_name, metric_name.replace("_", " "))

    @staticmethod
    def format_dimension_name(dimension_name: str) -> str:
        return DIMENSION_LABELS.get(dimension_name, dimension_name.replace("_", " "))

    @staticmethod
    def format_currency(value: Any) -> str:
        try:
            return f"${float(value):,.2f}"
        except (ValueError, TypeError):
            return str(value)

    @staticmethod
    def format_percentage(value: Any) -> str:
        try:
            return f"{float(value):.2f}%"
        except (ValueError, TypeError):
            return str(value)

    @staticmethod
    def format_number(value: Any) -> str:
        try:
            f_val = float(value)
            if f_val.is_integer():
                return f"{int(f_val):,}"
            return f"{f_val:,.2f}"
        except (ValueError, TypeError):
            return str(value)

    @staticmethod
    def format_val_by_metric(val: Any, metric_name: str) -> str:
        if val is None or pd.isna(val):
            return "N/A"
        metric_lower = metric_name.lower()
        if "percentage" in metric_lower or "pct" in metric_lower or "growth" in metric_lower or "risk" in metric_lower:
            return ResponseGenerator.format_percentage(val)
        if "amount" in metric_lower or "sales" in metric_lower or "revenue" in metric_lower or "price" in metric_lower:
            return ResponseGenerator.format_currency(val)
        return ResponseGenerator.format_number(val)

    @staticmethod
    def describe_time_range(tr: Optional[Any]) -> str:
        if not tr:
            return "overall"
        if tr.type == "relative":
            return f"for the {tr.value.replace('_', ' ')}"
        else:
            return f"from {tr.start_date} to {tr.end_date}"

    @staticmethod
    def describe_filters(filters: List[Any]) -> str:
        if not filters:
            return ""
        descriptions = []
        for f in filters:
            label = ResponseGenerator.format_dimension_name(f.field)
            val = f.value
            if f.operator == "equals":
                descriptions.append(f"in the {val} {label}" if label == "region" else f"for {label} {val}")
            elif f.operator == "in":
                descriptions.append(f"for {label} in {val}")
            elif f.operator == "greater_than":
                descriptions.append(f"where {label} is greater than {val}")
        return " " + " and ".join(descriptions)

    # 2. Dynamic Answer Templates
    @staticmethod
    def generate_aggregate_answer(row: Dict[str, Any], metric: str, filters: List[Any], time_range: Optional[Any]) -> str:
        val = row.get(metric, list(row.values())[0])
        fmt = ResponseGenerator.format_val_by_metric(val, metric)
        metric_label = ResponseGenerator.format_metric_name(metric)
        time_desc = ResponseGenerator.describe_time_range(time_range)
        filter_desc = ResponseGenerator.describe_filters(filters)
        
        if metric == "total_sales":
            period = time_desc.replace("for the ", "")
            return f"Total sales {period} {filter_desc} were {fmt}.".replace("  ", " ").strip()
        elif metric == "closing_inventory":
            return f"Total closing inventory was {fmt} units.".replace("  ", " ").strip()
        elif metric == "opening_inventory":
            return f"Total opening inventory was {fmt} units.".replace("  ", " ").strip()
        elif metric == "average_selling_price":
            prod_or_cat = ""
            for f in filters:
                if f.field in ["product_id", "category"]:
                    prod_or_cat = f"of {f.value} "
                    break
            period = time_desc.replace("for the ", "")
            return f"The average selling price {prod_or_cat}was {fmt} {period}.".replace("  ", " ").strip()
            
        return f"{metric_label.title()}{filter_desc} {time_desc} was {fmt}.".replace("  ", " ").strip()

    @staticmethod
    def generate_ranking_answer(df: pd.DataFrame, metric: str, dimensions: List[str], filters: List[Any], time_range: Optional[Any], order_by: List[Any], limit: Optional[int], question: str) -> str:
        if df.empty:
            return "No matching data was found for the selected filters and time period."
            
        dim = dimensions[0]
        dim_label = ResponseGenerator.format_dimension_name(dim)
        metric_label = ResponseGenerator.format_metric_name(metric)
        time_desc = ResponseGenerator.describe_time_range(time_range)
        filter_desc = ResponseGenerator.describe_filters(filters)
        
        direction = order_by[0].direction if order_by else "descending"
        
        if "second" in question.lower() or "2nd" in question.lower():
            if len(df) >= 2:
                second_row = df.iloc[1]
                val = second_row[metric]
                fmt = ResponseGenerator.format_val_by_metric(val, metric)
                entity = second_row[dim]
                rank_adj = "second highest" if direction == "descending" else "second lowest"
                return f"{entity} was the {rank_adj} {dim_label}{filter_desc} {time_desc}, with {metric_label} of {fmt}."
            else:
                return "No second-ranked entity was found in the results."

        if len(df) == 1 or limit == 1:
            row = df.iloc[0]
            val = row[metric]
            fmt = ResponseGenerator.format_val_by_metric(val, metric)
            entity = row[dim]
            
            if direction == "descending":
                if metric == "total_units":
                    return f"{entity} sold the most units{filter_desc} {time_desc}, with {fmt} units sold."
                return f"{entity} generated the highest {metric_label}{filter_desc} {time_desc}, with {metric_label} of {fmt}."
            else:
                return f"{entity} recorded the lowest {metric_label}{filter_desc} {time_desc}, with {metric_label} of {fmt}."
        else:
            items = df[dim].tolist()
            if len(items) > 1:
                items_str = ", ".join(str(i) for i in items[:-1]) + f" and {items[-1]}"
            else:
                items_str = str(items[0])
                
            first_entity = df.iloc[0][dim]
            first_val = df.iloc[0][metric]
            first_fmt = ResponseGenerator.format_val_by_metric(first_val, metric)
            
            noun_plural = dim_label + "s" if not dim_label.endswith("y") else dim_label[:-1] + "ies"
            rank_adj = "highest-revenue" if direction == "descending" and metric == "total_sales" else ("highest" if direction == "descending" else "lowest")
            
            return f"The {len(df)} {rank_adj} {noun_plural}{filter_desc} {time_desc} were {items_str}. {first_entity} ranked first with {metric_label} of {first_fmt}."

    @staticmethod
    def generate_comparison_answer(df: pd.DataFrame, metric: str, dimensions: List[str], filters: List[Any], time_range: Optional[Any]) -> str:
        if len(df) < 2:
            return ResponseGenerator.generate_aggregate_answer(df.iloc[0].to_dict(), metric, filters, time_range)
            
        dim = dimensions[0]
        dim_label = ResponseGenerator.format_dimension_name(dim)
        metric_label = ResponseGenerator.format_metric_name(metric)
        time_desc = ResponseGenerator.describe_time_range(time_range)
        
        df_sorted = df.sort_values(by=metric, ascending=False)
        top = df_sorted.iloc[0]
        bot = df_sorted.iloc[-1]
        
        top_fmt = ResponseGenerator.format_val_by_metric(top[metric], metric)
        bot_fmt = ResponseGenerator.format_val_by_metric(bot[metric], metric)
        
        return f"{top[dim]} recorded the highest total sales{time_desc} at {top_fmt}, while {bot[dim]} recorded the lowest at {bot_fmt}."

    @staticmethod
    def generate_trend_answer(df: pd.DataFrame, metric: str, filters: List[Any], time_range: Optional[Any]) -> str:
        if df.empty:
            return "No matching data was found for the selected filters and time period."
            
        metric_label = ResponseGenerator.format_metric_name(metric)
        time_col = [c for c in df.columns if "date" in c or "period" in c][0]
        
        df_sorted = df.sort_values(by=metric, ascending=False)
        top_row = df_sorted.iloc[0]
        top_val = top_row[metric]
        top_fmt = ResponseGenerator.format_val_by_metric(top_val, metric)
        top_date = top_row[time_col]
        
        category_str = "sales"
        for f in filters:
            if f.field == "category":
                category_str = f"{f.value} sales"
                break
                
        return f"{category_str.title()} reached their highest monthly value in {top_date} at {top_fmt}."

    @staticmethod
    def generate_contribution_answer(df: pd.DataFrame, metric: str, dimensions: List[str], filters: List[Any], time_range: Optional[Any]) -> str:
        if df.empty:
            return "No contribution share could be calculated."
            
        dim = dimensions[0]
        contrib_col = "contribution_percentage"
        row = df.iloc[0]
        
        return f"{row[dim]} contributed {ResponseGenerator.format_percentage(row[contrib_col])} of total revenue."

    @staticmethod
    def generate_growth_answer(df: pd.DataFrame, metric: str, time_range: Optional[Any]) -> str:
        if df.empty:
            return "No growth calculation results were returned."
            
        row = df.iloc[0]
        g_val = row["growth_percentage"]
        fmt = ResponseGenerator.format_percentage(abs(g_val))
        
        direction = "increased" if g_val >= 0 else "decreased"
        return f"Sales {direction} by {fmt} compared with the previous period."

    @staticmethod
    def generate_promotion_answer(validated_res: Dict[str, Any]) -> str:
        if "full_results" in validated_res:
            res = validated_res["full_results"]
            uplift_pct = res["uplift_percent"]
            fmt = ResponseGenerator.format_percentage(abs(uplift_pct))
            
            direction = "uplift" if uplift_pct >= 0 else "decline"
            return f"The promotion was associated with a {fmt} sales {direction} compared with the selected baseline."
        else:
            df = validated_res.get("data", pd.DataFrame())
            if df.empty:
                return "No active promotion records were found in the selected period."
            top_row = df.iloc[0]
            fmt = ResponseGenerator.format_percentage(top_row["uplift_percent"])
            return f"Across all campaigns, the highest promotional sales uplift was observed in {top_row['promotion_name']} with an uplift of {fmt}."

    @staticmethod
    def generate_inventory_answer(df: pd.DataFrame) -> str:
        if df.empty:
            return "No stockout risks or inventory anomalies were identified."
            
        risk_count = len(df[df["stockout_risk"] > 50]) if "stockout_risk" in df.columns else len(df)
        lowest_row = df.sort_values(by="closing_inventory").iloc[0] if "closing_inventory" in df.columns else df.iloc[0]
        
        dim_col = df.columns[0]
        entity = lowest_row[dim_col]
        units = lowest_row.get("closing_inventory", lowest_row.iloc[1] if len(lowest_row) > 1 else 0)
        
        return f"{risk_count} products were identified as potential stockout risks. {entity} had the lowest closing inventory at {ResponseGenerator.format_number(units)} units."

    @staticmethod
    def generate_anomaly_answer(df: pd.DataFrame, metric: str) -> str:
        count = len(df)
        if count == 0:
            return "No unusual sales spikes were detected."
            
        max_anom = df.sort_values(by="deviation_score", ascending=False).iloc[0]
        date_str = max_anom.get("sale_date", "selected period")
        prod = max_anom.get("product_name", "the product")
        reg = max_anom.get("region_name", "the region")
        val = max_anom[metric]
        fmt = ResponseGenerator.format_val_by_metric(val, metric)
        
        return f"{count} unusual sales spikes were detected. The largest occurred on {date_str} for {prod} in {reg}, with sales of {fmt}."

    @staticmethod
    def generate_data_quality_answer(validated_res: Dict[str, Any]) -> str:
        details = validated_res["quality_details"]
        score = details["overall_completeness_score"]
        missing = sum(details["missing_values"].values())
        scope = validated_res.get("dataset_scope") or "overall"
        scope_labels = {
            "overall": "The available dataset",
            "inventory": "The inventory dataset",
            "sales": "The sales dataset",
            "promotions": "The promotions dataset",
            "products": "The product dataset",
            "regions": "The region dataset",
        }
        label = scope_labels.get(scope, "The available dataset")
        return f"{label} is {ResponseGenerator.format_percentage(score)} complete, with {ResponseGenerator.format_number(missing)} missing values identified."

    # 3. Execution Coordinator & Response Validator
    @staticmethod
    def generate_response(validated_res: Dict[str, Any], question: str) -> Dict[str, Any]:
        """Generates a structured business explanation from validated analytics results."""
        if not validated_res.get("verified", False):
            err = validated_res.get("error", "")
            if "cannot be answered" in err:
                direct_answer = "This question cannot be answered reliably from the available sales, promotion, product, region and inventory data."
            else:
                direct_answer = "No matching data was found for the selected filters and time period."
                
            return {
                "direct_answer": direct_answer,
                "key_metrics": {},
                "breakdown": "",
                "applied_filters": [],
                "time_period": "N/A",
                "assumptions": validated_res.get("assumptions", []),
                "data_quality": "Failed Validation",
                "warnings": validated_res.get("warnings", []),
                "recommended_action": "Check database status or clarify the question."
            }
            
        df = validated_res.get("data", pd.DataFrame())
        op_type = validated_res.get("operation_type", "aggregate")
        metric_col = validated_res.get("metric", "total_sales")
        filters = validated_res.get("filters", [])
        time_range = validated_res.get("time_range", None)
        dimensions = validated_res.get("dimensions", [])
        order_by = validated_res.get("order_by", [])
        limit = validated_res.get("limit", None)
        dataset_scope = validated_res.get("dataset_scope")
        
        key_metrics = {}
        direct_answer = ""
        breakdown_md = ""
        recommended_action = "Monitor sales performance and adjust inventory buffers accordingly."
        
        if op_type == "promotion_uplift":
            direct_answer = ResponseGenerator.generate_promotion_answer(validated_res)
            if "full_results" in validated_res:
                res = validated_res["full_results"]
                key_metrics = {
                    "Promo Sales": ResponseGenerator.format_currency(res["promo_revenue"]),
                    "Baseline Sales": ResponseGenerator.format_currency(res["baseline_revenue"]),
                    "Uplift Units": ResponseGenerator.format_number(res["uplift_units"]),
                    "Uplift Percentage": ResponseGenerator.format_percentage(res["uplift_percent"])
                }
            elif not df.empty:
                top_row = df.iloc[0]
                key_metrics = {
                    "Total Campaigns": str(len(df)),
                    "Top Campaign": str(top_row["promotion_name"]),
                    "Highest Uplift": ResponseGenerator.format_percentage(top_row["uplift_percent"])
                }
                breakdown_md = df.to_markdown(index=False)
                
        elif op_type == "data_quality":
            direct_answer = ResponseGenerator.generate_data_quality_answer(validated_res)
            details = validated_res["quality_details"]
            key_metrics = {
                "Quality Score": f"{details['overall_completeness_score']}%",
                "Duplicate Rows": str(details["duplicate_sales_records"]),
                "Missing Values": str(sum(details["missing_values"].values())),
                "Invalid FKs": str(details["referential_integrity"]["sales_invalid_promo_count"])
            }
            
        elif op_type == "growth":
            direct_answer = ResponseGenerator.generate_growth_answer(df, metric_col, time_range)
            if not df.empty:
                if len(df) == 1:
                    row = df.iloc[0]
                    key_metrics = {
                        "Current Sales": ResponseGenerator.format_currency(row["current_value"]),
                        "Prior Sales": ResponseGenerator.format_currency(row["prior_value"]),
                        "Growth Rate": ResponseGenerator.format_percentage(row["growth_percentage"])
                    }
                else:
                    breakdown_md = df.to_markdown(index=False)
                    
        elif op_type == "contribution":
            direct_answer = ResponseGenerator.generate_contribution_answer(df, metric_col, dimensions, filters, time_range)
            if not df.empty:
                row = df.iloc[0]
                dim = dimensions[0]
                key_metrics = {
                    "Top Contributor": str(row[dim]),
                    "Share": ResponseGenerator.format_percentage(row["contribution_percentage"]),
                    "Revenue": ResponseGenerator.format_currency(row[metric_col])
                }
                breakdown_md = df.to_markdown(index=False)
                
        elif op_type == "anomaly_detection":
            direct_answer = ResponseGenerator.generate_anomaly_answer(df, metric_col)
            if not df.empty:
                key_metrics = {
                    "Anomalies Detected": str(len(df)),
                    "Max Spike": ResponseGenerator.format_currency(df[metric_col].max())
                }
                breakdown_md = df.to_markdown(index=False)
                
        elif op_type == "inventory_status":
            direct_answer = ResponseGenerator.generate_inventory_answer(df)
            if not df.empty:
                lowest_row = df.sort_values(by="closing_inventory").iloc[0] if "closing_inventory" in df.columns else df.iloc[0]
                dim_col = df.columns[0]
                key_metrics = {
                    "Lowest Stock Item": str(lowest_row[dim_col]),
                    "Closing Units": ResponseGenerator.format_number(lowest_row.get("closing_inventory", lowest_row.iloc[1] if len(lowest_row) > 1 else 0))
                }
                breakdown_md = df.to_markdown(index=False)
                
        elif op_type == "aggregate":
            if not df.empty:
                row = df.iloc[0]
                direct_answer = ResponseGenerator.generate_aggregate_answer(row.to_dict(), metric_col, filters, time_range)
                key_metrics = {"Value": ResponseGenerator.format_val_by_metric(row[metric_col], metric_col)}
                
        elif op_type == "rank":
            direct_answer = ResponseGenerator.generate_ranking_answer(df, metric_col, dimensions, filters, time_range, order_by, limit, question)
            if not df.empty:
                dim = dimensions[0]
                top_row = df.iloc[0]
                key_metrics = {
                    "Top Item": str(top_row[dim]),
                    "Top Value": ResponseGenerator.format_val_by_metric(top_row[metric_col], metric_col)
                }
                breakdown_md = df.to_markdown(index=False)
                
        elif op_type == "compare":
            direct_answer = ResponseGenerator.generate_comparison_answer(df, metric_col, dimensions, filters, time_range)
            if not df.empty:
                breakdown_md = df.to_markdown(index=False)
                
        elif op_type == "trend":
            direct_answer = ResponseGenerator.generate_trend_answer(df, metric_col, filters, time_range)
            if not df.empty:
                breakdown_md = df.to_markdown(index=False)
                
        if not direct_answer:
            direct_answer = "No matching data was found for the selected filters and time period."
            
        # 4. Strict Response Validation Post-Generation
        direct_answer = ResponseGenerator._validate_and_sanitize_answer(direct_answer, df, metric_col, dimensions, order_by, limit)
        
        applied_filters = [f"{ResponseGenerator.format_dimension_name(f.field)}: {f.value}" for f in filters]
        time_period = ResponseGenerator.describe_time_range(time_range)
        
        return {
            "direct_answer": direct_answer,
            "key_metrics": key_metrics,
            "breakdown": breakdown_md,
            "applied_filters": applied_filters,
            "time_period": time_period,
            "assumptions": validated_res.get("assumptions", []),
            "data_quality": f"Verified ({validated_res.get('data_completeness', 100.0)}% completeness)",
            "warnings": validated_res.get("warnings", []),
            "recommended_action": recommended_action
        }

    @staticmethod
    def _validate_and_sanitize_answer(text: str, df: pd.DataFrame, metric: str, dimensions: List[str], order_by: List[Any], limit: Optional[int]) -> str:
        """Sanitizes text, checks numbers against result df, and enforces forbidden phrase checks."""
        # 1. Block unsupported causal words
        for cw in CAUSAL_WORDS:
            if cw in text.lower():
                text = re.sub(r'\b' + re.escape(cw) + r'\b', "was associated with", text, flags=re.IGNORECASE)
                
        # 2. Extract every number from text
        cleaned = re.sub(r'[\$,%]', '', text)
        extracted_numbers: List[float] = []
        for word in cleaned.split():
            if "-" in word or "/" in word:
                continue # Skip dates/years
            match = re.search(r'-?\d+\.?\d*', word)
            if match:
                try:
                    extracted_numbers.append(float(match.group(0)))
                except ValueError:
                    pass
                    
        allowed_values = set()
        if not df.empty:
            for col in df.columns:
                if pd.api.types.is_numeric_dtype(df[col]):
                    for val in df[col].dropna():
                        allowed_values.add(round(float(val), 2))
                        allowed_values.add(float(val))
            allowed_values.add(float(len(df)))
            
        if limit:
            allowed_values.add(float(limit))
            
        allowed_values.add(1.0)
        allowed_values.add(2.0)
        allowed_values.add(100.0)
        
        for num in extracted_numbers:
            has_match = False
            for allowed in allowed_values:
                if abs(num - allowed) < 0.05:
                    has_match = True
                    break
            if not has_match:
                return ResponseGenerator._generate_safe_fallback(df, metric, dimensions, order_by)
                
        # 3. Strict forbidden phrases block with word boundaries
        for fp in FORBIDDEN_PHRASES:
            pattern = r'\b' + re.escape(fp) + r'\b'
            if re.search(pattern, text.lower()):
                return ResponseGenerator._generate_safe_fallback(df, metric, dimensions, order_by)
                
        return text

    @staticmethod
    def _generate_safe_fallback(df: pd.DataFrame, metric: str, dimensions: List[str], order_by: List[Any]) -> str:
        """Returns a generic fallback description that is guaranteed to contain no technical/forbidden phrases."""
        if df.empty:
            return "No matching data was found for the selected filters and time period."
            
        metric_label = ResponseGenerator.format_metric_name(metric)
        
        if len(df) == 1:
            row = df.iloc[0].to_dict()
            val = row.get(metric, list(row.values())[-1])
            fmt = ResponseGenerator.format_val_by_metric(val, metric)
            if dimensions:
                dim_col = dimensions[0]
                entity = row[dim_col]
                return f"{entity} registered {metric_label} of {fmt}."
            return f"The metric {metric_label} was {fmt}."
        else:
            dim_col = dimensions[0] if dimensions else (df.columns[0] if not df.empty else None)
            if dim_col:
                top_row = df.iloc[0]
                val = top_row.get(metric, top_row.iloc[1] if len(top_row) > 1 else 0)
                fmt = ResponseGenerator.format_val_by_metric(val, metric)
                entity = top_row[dim_col]
                
                direction = order_by[0].direction if order_by else "descending"
                rank_adj = "highest" if direction == "descending" else "lowest"
                return f"{entity} registered the {rank_adj} {metric_label} at {fmt}."
            return "Multiple results were resolved."

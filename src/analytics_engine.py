import pandas as pd
import numpy as np
import datetime
from typing import Dict, Any, Tuple, List
from src.models import OperationPlan, QueryPlan, SortCondition, TimeRange
from src.sql_compiler import SQLCompiler
from src.sql_executor import SQLExecutor
from src.promotion_analysis import PromotionAnalysis
from src.anomaly_detection import AnomalyDetector
from src.data_quality import DataQuality
from src.query_validator import QueryValidator

class AnalyticsEngine:
    @staticmethod
    def execute_plan(plan: QueryPlan, question: str) -> Dict[str, Any]:
        """Executes a multi-operation or single-operation QueryPlan."""
        if not plan.operations:
            return {
                "success": False,
                "error": "This question cannot be answered reliably from the currently available sales, promotion, product, region and inventory data.",
                "data": pd.DataFrame(),
                "sql": ""
            }
            
        op = plan.operations[0]
        
        try:
            res = AnalyticsEngine._execute_operation(op, plan, question)
            return res
        except Exception as e:
            return {
                "success": False,
                "error": f"Analytics execution failed: {str(e)}",
                "data": pd.DataFrame(),
                "sql": ""
            }

    @staticmethod
    def _execute_operation(op: OperationPlan, plan: QueryPlan, question: str) -> Dict[str, Any]:
        compiler = SQLCompiler()
        
        # Base metadata to copy to the return dict
        meta = {
            "dimensions": op.dimensions,
            "filters": op.filters,
            "time_range": op.time_range,
            "order_by": op.order_by,
            "limit": op.limit,
            "dataset_scope": op.dataset_scope,
        }
        
        # 1. Specialized: promotion_uplift
        if op.operation_type == "promotion_uplift" or op.metric == "promotion_uplift_percentage":
            # Check if promotion_id is filtered
            promo_id = None
            for f in op.filters:
                if f.field == "promotion_id" and f.operator == "equals":
                    promo_id = f.value
                    break
                    
            if promo_id:
                # Analyze single promotion
                res = PromotionAnalysis.analyze_promotion(promo_id)
                if "error" in res:
                    raise ValueError(res["error"])
                    
                df = pd.DataFrame([res])
                display_cols = ["promotion_id", "promotion_name", "product_name", "region_name", "promo_units", "baseline_units", "uplift_units", "uplift_percent"]
                df_display = df[[c for c in display_cols if c in df.columns]]
                
                # Check consistency
                sql_dummy = f"SELECT * FROM promotions WHERE promotion_id = '{promo_id}'"
                is_consistent, msg = QueryValidator.validate_consistency(plan, sql_dummy, question)
                if not is_consistent:
                    raise ValueError(msg)
                
                return {
                    "success": True,
                    "operation_type": op.operation_type,
                    "metric": op.metric,
                    **meta,
                    "data": df_display,
                    "full_results": res,
                    "sql": f"-- Running custom promotion effectiveness calculation for '{promo_id}'",
                    "warnings": res.get("warnings", []),
                    "assumptions": plan.assumptions + res.get("assumptions", [])
                }
            else:
                # Calculate uplift across all promotions
                df_promos = SQLExecutor.execute("SELECT promotion_id FROM promotions;")
                promo_ids = df_promos["promotion_id"].tolist()
                
                all_results = []
                warnings = []
                for p_id in promo_ids:
                    res = PromotionAnalysis.analyze_promotion(p_id)
                    if "error" not in res:
                        all_results.append(res)
                        warnings.extend(res.get("warnings", []))
                        
                df_all = pd.DataFrame(all_results)
                
                for f in op.filters:
                    if f.field in df_all.columns:
                        df_all = df_all[df_all[f.field].astype(str) == str(f.value)]
                        
                if op.order_by:
                    sort_col = op.order_by[0].field
                    ascending = op.order_by[0].direction == "ascending"
                    if sort_col == "promotion_uplift_percentage":
                        sort_col = "uplift_percent"
                    if sort_col in df_all.columns:
                        df_all = df_all.sort_values(by=sort_col, ascending=ascending)
                else:
                    df_all = df_all.sort_values(by="uplift_percent", ascending=False)
                    
                if op.limit:
                    df_all = df_all.head(op.limit)
                    
                display_cols = ["promotion_id", "promotion_name", "product_name", "region_name", "promo_units", "baseline_units", "uplift_percent"]
                df_display = df_all[[c for c in display_cols if c in df_all.columns]]
                
                sql_dummy = "SELECT promotion_id, promotion_name FROM promotions JOIN sales JOIN products"
                is_consistent, msg = QueryValidator.validate_consistency(plan, sql_dummy, question)
                if not is_consistent:
                    raise ValueError(msg)
                
                unique_warnings = list(set(warnings))
                return {
                    "success": True,
                    "operation_type": op.operation_type,
                    "metric": op.metric,
                    **meta,
                    "data": df_display,
                    "sql": "-- Aggregated promotion effectiveness across multiple campaigns",
                    "warnings": unique_warnings,
                    "assumptions": plan.assumptions + ["Aggregated all promotion uplifts present in database."]
                }
                
        # 2. Specialized: data_quality
        elif op.operation_type == "data_quality" or op.metric == "data_completeness_percentage":
            res = DataQuality.run_all_checks()
            rows = [
                {"Metric": "Overall Data Completeness Score", "Value": f"{res['overall_completeness_score']}%"},
                {"Metric": "Duplicate Sales Transactions", "Value": str(res["duplicate_sales_records"])},
                {"Metric": "Invalid Promotion References", "Value": str(res["referential_integrity"]["sales_invalid_promo_count"])},
                {"Metric": "Invalid Product References", "Value": str(res["referential_integrity"]["invalid_promos_count"])},
                {"Metric": "Inventory Log Coverage", "Value": f"{res['inventory_days_completeness']['percentage_completeness']}%"}
            ]
            df = pd.DataFrame(rows)
            
            return {
                "success": True,
                "operation_type": op.operation_type,
                "metric": op.metric,
                **meta,
                "data": df,
                "quality_details": res,
                "sql": "-- Executed data quality diagnostics across multiple database integrity tables",
                "warnings": res.get("warnings", []),
                "assumptions": plan.assumptions + ["Parsed all tables to check referential integrity, duplicates, and coverage."]
            }
            
        # 3. Specialized: anomaly_detection
        elif op.operation_type == "anomaly_detection":
            anomaly_op = OperationPlan(
                operation_type="trend",
                metric=op.metric,
                dimensions=op.dimensions + (["sale_date"] if "sale_date" not in op.dimensions else []),
                filters=op.filters,
                time_range=op.time_range,
                group_by=op.group_by + (["sale_date"] if "sale_date" not in op.group_by else []),
                order_by=[SortCondition(field="sale_date", direction="ascending")],
                time_granularity="daily"
            )
            
            sql, params = compiler.compile(anomaly_op)
            
            # Check consistency
            is_consistent, msg = QueryValidator.validate_consistency(plan, sql, question)
            if not is_consistent:
                raise ValueError(msg)
                
            df = SQLExecutor.execute(sql, params)
            
            direction = "both"
            if "spike" in op.metric or "spike" in str(plan.assumptions):
                direction = "spikes"
            elif "drop" in op.metric or "drop" in str(plan.assumptions):
                direction = "drops"
                
            anomalies_df = AnomalyDetector.detect_anomalies(df, op.metric, method="zscore", threshold=2.0, direction=direction)
            
            return {
                "success": True,
                "operation_type": op.operation_type,
                "metric": op.metric,
                **meta,
                "data": anomalies_df,
                "sql": sql,
                "warnings": ["Anomalies computed using daily rolling Z-score method (threshold=2.0 std dev)."] if not anomalies_df.empty else ["No anomalies detected in the selected period."],
                "assumptions": plan.assumptions + ["Assumed normal sales distribution to execute Z-score filter."]
            }
            
        # 4. Specialized: growth
        elif op.operation_type == "growth" or op.metric == "sales_growth_percentage" or op.metric == "month_over_month_growth":
            if not op.time_range:
                op.time_range = TimeRange(type="relative", value="previous_30_days")
                # Update meta time range since it changed
                meta["time_range"] = op.time_range
                
            sql_curr, params_curr = compiler.compile(op)
            
            is_consistent, msg = QueryValidator.validate_consistency(plan, sql_curr, question)
            if not is_consistent:
                raise ValueError(msg)
                
            df_curr = SQLExecutor.execute(sql_curr, params_curr)
            
            start_date_str, end_date_str = compiler._resolve_time_range(op.time_range)
            start_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_date = datetime.datetime.strptime(end_date_str, "%Y-%m-%d").date()
            duration = (end_date - start_date).days + 1
            
            prior_start = start_date - datetime.timedelta(days=duration)
            prior_end = start_date - datetime.timedelta(days=1)
            
            prior_op = op.model_copy(deep=True)
            prior_op.time_range = TimeRange(
                type="absolute",
                start_date=prior_start.strftime("%Y-%m-%d"),
                end_date=prior_end.strftime("%Y-%m-%d")
            )
            
            sql_prior, params_prior = compiler.compile(prior_op)
            df_prior = SQLExecutor.execute(sql_prior, params_prior)
            
            merge_cols = op.group_by if op.group_by else []
            metric_col = op.metric
            
            if df_curr.empty:
                return {
                    "success": True,
                    "operation_type": op.operation_type,
                    "metric": op.metric,
                    **meta,
                    "data": pd.DataFrame(),
                    "sql": f"-- Current period SQL:\n{sql_curr}",
                    "warnings": ["No data available in the current selection period to calculate growth."],
                    "assumptions": plan.assumptions
                }
                
            if df_prior.empty:
                df_curr["prior_value"] = 0.0
                df_curr["growth_percentage"] = 100.0
                df_curr = df_curr.rename(columns={metric_col: "current_value"})
                return {
                    "success": True,
                    "operation_type": op.operation_type,
                    "metric": op.metric,
                    **meta,
                    "data": df_curr,
                    "sql": f"-- Current SQL:\n{sql_curr}\n-- Prior SQL:\n{sql_prior}",
                    "warnings": ["Prior period had zero sales records; growth calculated at 100%."],
                    "assumptions": plan.assumptions
                }
                
            if not merge_cols:
                curr_val = float(df_curr.iloc[0][metric_col] or 0.0)
                prior_val = float(df_prior.iloc[0][metric_col] or 0.0)
                growth = ((curr_val - prior_val) / prior_val) * 100.0 if prior_val > 0 else 100.0
                df_growth = pd.DataFrame([{
                    "current_value": round(curr_val, 2),
                    "prior_value": round(prior_val, 2),
                    "growth_percentage": round(growth, 2)
                }])
            else:
                df_merged = pd.merge(df_curr, df_prior, on=merge_cols, suffixes=("_curr", "_prior"))
                curr_col = f"{metric_col}_curr"
                prior_col = f"{metric_col}_prior"
                
                df_merged["growth_percentage"] = ((df_merged[curr_col] - df_merged[prior_col]) / df_merged[prior_col]) * 100.0
                df_merged["growth_percentage"] = df_merged["growth_percentage"].replace([np.inf, -np.inf], 100.0).fillna(0.0)
                
                df_growth = df_merged.rename(columns={curr_col: "current_value", prior_col: "prior_value"})
                df_growth["current_value"] = df_growth["current_value"].round(2)
                df_growth["prior_value"] = df_growth["prior_value"].round(2)
                df_growth["growth_percentage"] = df_growth["growth_percentage"].round(2)
                
                reorder_cols = merge_cols + ["current_value", "prior_value", "growth_percentage"]
                df_growth = df_growth[reorder_cols]
                
            return {
                "success": True,
                "operation_type": op.operation_type,
                "metric": op.metric,
                **meta,
                "data": df_growth,
                "sql": f"-- Current SQL:\n{sql_curr}\n\n-- Prior SQL:\n{sql_prior}",
                "warnings": [],
                "assumptions": plan.assumptions + [f"Compared period {start_date_str} to {end_date_str} with prior period {prior_start.strftime('%Y-%m-%d')} to {prior_end.strftime('%Y-%m-%d')}."]
            }
            
        # 5. Specialized: contribution
        elif op.operation_type == "contribution" or op.metric == "revenue_contribution_percentage":
            if not op.group_by:
                raise ValueError("Contribution calculations require grouping (by product, category, region, etc.).")
                
            sql_group, params_group = compiler.compile(op)
            
            is_consistent, msg = QueryValidator.validate_consistency(plan, sql_group, question)
            if not is_consistent:
                raise ValueError(msg)
                
            df_group = SQLExecutor.execute(sql_group, params_group)
            
            total_op = op.model_copy(deep=True)
            total_op.group_by = []
            total_op.dimensions = []
            total_op.order_by = []
            
            sql_total, params_total = compiler.compile(total_op)
            df_total = SQLExecutor.execute(sql_total, params_total)
            
            if df_group.empty or df_total.empty:
                return {
                    "success": True,
                    "operation_type": op.operation_type,
                    "metric": op.metric,
                    **meta,
                    "data": pd.DataFrame(),
                    "sql": sql_group,
                    "warnings": ["No data available to calculate contribution share."],
                    "assumptions": plan.assumptions
                }
                
            total_sum = float(df_total.iloc[0][op.metric] or 0.0)
            metric_col = op.metric
            
            if total_sum > 0:
                df_group["contribution_percentage"] = (df_group[metric_col] / total_sum) * 100.0
                df_group["contribution_percentage"] = df_group["contribution_percentage"].round(2)
            else:
                df_group["contribution_percentage"] = 0.0
                
            return {
                "success": True,
                "operation_type": op.operation_type,
                "metric": op.metric,
                **meta,
                "data": df_group,
                "sql": f"-- Grouped Query:\n{sql_group}\n\n-- Total Query:\n{sql_total}",
                "warnings": [],
                "assumptions": plan.assumptions + ["Computed share relative to total aggregate sum of the period."]
            }
            
        # 6. Standard compiler execution
        else:
            sql, params = compiler.compile(op)
            
            is_consistent, msg = QueryValidator.validate_consistency(plan, sql, question)
            if not is_consistent:
                raise ValueError(msg)
                
            df = SQLExecutor.execute(sql, params)
            return {
                "success": True,
                "operation_type": op.operation_type,
                "metric": op.metric,
                **meta,
                "data": df,
                "sql": sql,
                "warnings": [],
                "assumptions": plan.assumptions
            }

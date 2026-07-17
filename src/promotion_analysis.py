import sqlite3
import datetime
import pandas as pd
from typing import Dict, Any, Tuple, Optional, List
from src.config import DATABASE_PATH
from src.sql_executor import SQLExecutor

class PromotionAnalysis:
    @staticmethod
    def analyze_promotion(promotion_id: str) -> Dict[str, Any]:
        """Runs full promotion effectiveness and uplift analysis for a specific campaign."""
        # 1. Fetch promotion details
        promo_query = """
        SELECT promotion_id, promotion_name, promotion_type, discount_percentage, start_date, end_date, product_id, region_id
        FROM promotions WHERE promotion_id = ?;
        """
        df_promo = SQLExecutor.execute(promo_query, [promotion_id])
        if df_promo.empty:
            return {"error": f"Promotion '{promotion_id}' not found."}
            
        promo = df_promo.iloc[0]
        p_id = promo["product_id"]
        r_id = promo["region_id"]
        start_date_str = promo["start_date"]
        end_date_str = promo["end_date"]
        
        start_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d").date()
        end_date = datetime.datetime.strptime(end_date_str, "%Y-%m-%d").date()
        promo_days = (end_date - start_date).days + 1
        
        # 2. Check for overlapping campaigns
        overlap_query = """
        SELECT promotion_id, promotion_name, start_date, end_date
        FROM promotions
        WHERE product_id = ? AND region_id = ? AND promotion_id != ?
          AND start_date <= ? AND end_date >= ?;
        """
        df_overlaps = SQLExecutor.execute(overlap_query, [p_id, r_id, promotion_id, end_date_str, start_date_str])
        has_overlap = not df_overlaps.empty
        overlap_details = []
        if has_overlap:
            for _, row in df_overlaps.iterrows():
                overlap_details.append(f"{row['promotion_name']} ({row['promotion_id']}: {row['start_date']} to {row['end_date']})")
                
        # 3. Query sales during promotion period
        sales_query = """
        SELECT SUM(units_sold) AS promo_units, SUM(sales_amount) AS promo_revenue
        FROM sales
        WHERE product_id = ? AND region_id = ? AND sale_date BETWEEN ? AND ?;
        """
        df_sales = SQLExecutor.execute(sales_query, [p_id, r_id, start_date_str, end_date_str])
        promo_units = int(df_sales.iloc[0]["promo_units"] or 0)
        promo_revenue = float(df_sales.iloc[0]["promo_revenue"] or 0.0)
        
        # 4. Calculate baseline
        baseline_units, baseline_method, baseline_warnings = PromotionAnalysis._calculate_baseline(p_id, r_id, start_date, end_date)
        
        # Calculate uplift
        uplift_units = 0
        uplift_percent = 0.0
        warnings = list(baseline_warnings)
        
        # Overlap warnings
        if has_overlap:
            warnings.append(
                f"Overlapping promotion detected: {', '.join(overlap_details)}. "
                "The calculated sales uplift is associative and cannot be solely attributed to a single campaign. "
                "Matched-control or regression analysis is recommended for causal attribution."
            )
            
        if baseline_units > 0:
            uplift_units = promo_units - baseline_units
            uplift_percent = (uplift_units / baseline_units) * 100.0
        else:
            warnings.append("Baseline sales could not be calculated (baseline=0). Uplift set to 0.")
            
        # Get product name and region name for response
        prod_info = SQLExecutor.execute("SELECT product_name FROM products WHERE product_id = ?;", [p_id])
        reg_info = SQLExecutor.execute("SELECT region_name FROM regions WHERE region_id = ?;", [r_id])
        product_name = prod_info.iloc[0]["product_name"] if not prod_info.empty else p_id
        region_name = reg_info.iloc[0]["region_name"] if not reg_info.empty else r_id
        
        # Baseline revenue estimation (based on standard unit price)
        price_query = "SELECT unit_price FROM products WHERE product_id = ?;"
        df_price = SQLExecutor.execute(price_query, [p_id])
        unit_price = float(df_price.iloc[0]["unit_price"] if not df_price.empty else 0.0)
        baseline_revenue = baseline_units * unit_price
        
        # Closing stock during campaign
        inv_query = """
        SELECT AVG(closing_inventory) AS avg_stock, MIN(closing_inventory) AS min_stock
        FROM inventory
        WHERE product_id = ? AND region_id = ? AND snapshot_date BETWEEN ? AND ?;
        """
        df_inv = SQLExecutor.execute(inv_query, [p_id, r_id, start_date_str, end_date_str])
        avg_inventory = float(df_inv.iloc[0]["avg_stock"] or 0.0)
        min_inventory = int(df_inv.iloc[0]["min_stock"] or 0)
        
        # Assumptions
        assumptions = [
            f"Baseline sales calculated using: {baseline_method}.",
            f"Assumed standard pricing of ${unit_price:.2f} per unit for baseline revenue estimation."
        ]
        
        return {
            "promotion_id": promotion_id,
            "promotion_name": promo["promotion_name"],
            "product_name": product_name,
            "region_name": region_name,
            "start_date": start_date_str,
            "end_date": end_date_str,
            "campaign_days": promo_days,
            "promo_units": promo_units,
            "promo_revenue": promo_revenue,
            "baseline_units": baseline_units,
            "baseline_revenue": baseline_revenue,
            "uplift_units": uplift_units,
            "uplift_percent": round(uplift_percent, 2),
            "avg_inventory_during_campaign": round(avg_inventory, 1),
            "min_inventory_during_campaign": min_inventory,
            "has_overlap": has_overlap,
            "warnings": warnings,
            "assumptions": assumptions,
            "data_completeness": 100.0 # Will be verified by result validator
        }
        
    @staticmethod
    def _calculate_baseline(product_id: str, region_id: str, start_date: datetime.date, end_date: datetime.date) -> Tuple[int, str, List[str]]:
        """Calculates baseline units sold using the prioritized business logic rules."""
        promo_days = (end_date - start_date).days + 1
        warnings = []
        
        # Priority 1: Previous 4 comparable non-promotional weeks
        p1_start = start_date - datetime.timedelta(days=28)
        p1_end = start_date - datetime.timedelta(days=1)
        
        # Query active promotions for this product & region in the baseline window
        promo_dates_query = """
        SELECT start_date, end_date FROM promotions
        WHERE product_id = ? AND region_id = ?
          AND start_date <= ? AND end_date >= ?;
        """
        df_promo_dates = SQLExecutor.execute(promo_dates_query, [product_id, region_id, p1_end.strftime("%Y-%m-%d"), p1_start.strftime("%Y-%m-%d")])
        
        promo_dates = set()
        for _, row in df_promo_dates.iterrows():
            s = datetime.datetime.strptime(row["start_date"], "%Y-%m-%d").date()
            e = datetime.datetime.strptime(row["end_date"], "%Y-%m-%d").date()
            # Generate all dates in this promo
            curr = max(p1_start, s)
            limit = min(p1_end, e)
            while curr <= limit:
                promo_dates.add(curr.strftime("%Y-%m-%d"))
                curr += datetime.timedelta(days=1)
                
        # Query daily sales in the baseline window
        sales_query = """
        SELECT sale_date, units_sold
        FROM sales
        WHERE product_id = ? AND region_id = ? AND sale_date BETWEEN ? AND ?;
        """
        df_sales = SQLExecutor.execute(sales_query, [product_id, region_id, p1_start.strftime("%Y-%m-%d"), p1_end.strftime("%Y-%m-%d")])
        
        # Filter out promotional dates
        non_promo_sales = df_sales[~df_sales["sale_date"].isin(promo_dates)]
        
        if len(non_promo_sales) >= 14: # At least 2 weeks of clean baseline data
            avg_daily = non_promo_sales["units_sold"].mean()
            baseline_units = int(avg_daily * promo_days)
            return baseline_units, f"average of previous 4 comparable non-promotional weeks ({len(non_promo_sales)} clean days)", warnings
            
        # Priority 2: Same comparable period from the previous year
        p2_start = start_date - datetime.timedelta(days=365)
        p2_end = end_date - datetime.timedelta(days=365)
        
        df_sales_prev_year = SQLExecutor.execute(
            "SELECT SUM(units_sold) AS units FROM sales WHERE product_id = ? AND region_id = ? AND sale_date BETWEEN ? AND ?;",
            [product_id, region_id, p2_start.strftime("%Y-%m-%d"), p2_end.strftime("%Y-%m-%d")]
        )
        
        prev_year_units = df_sales_prev_year.iloc[0]["units"]
        if prev_year_units and prev_year_units > 0:
            return int(prev_year_units), "same comparable period from the previous year", warnings
            
        # Priority 3: Previous 4 available weeks (including promotion dates if any)
        if not df_sales.empty:
            avg_daily = df_sales["units_sold"].mean()
            baseline_units = int(avg_daily * promo_days)
            warnings.append("Baseline includes promotional days due to insufficient non-promotional history in the prior 4 weeks.")
            return baseline_units, "previous 4 available weeks (with promotions included)", warnings
            
        # Priority 4: Return insufficient-data warning
        warnings.append("Insufficient sales data prior to promotion period to construct a baseline.")
        return 0, "no baseline available (insufficient data)", warnings

import pandas as pd
from typing import Dict, Any, List
from src.sql_executor import SQLExecutor

class DataQuality:
    @staticmethod
    def run_all_checks() -> Dict[str, Any]:
        """Runs a comprehensive suite of data quality checks on the database."""
        missing_counts = DataQuality._check_missing_values()
        duplicate_sales = DataQuality._check_duplicate_sales()
        referential_integrity = DataQuality._check_referential_integrity()
        inventory_completeness = DataQuality._check_inventory_completeness()
        
        # Calculate an overall score
        total_checks = 4
        failures = 0
        
        if duplicate_sales > 0: failures += 0.5
        if referential_integrity["invalid_promos_count"] > 0: failures += 0.5
        if referential_integrity["sales_invalid_promo_count"] > 0: failures += 0.5
        for col, val in missing_counts.items():
            if val > 0 and not col.endswith("promotion_id"): # promotion_id is naturally null/blank
                failures += 0.1
                
        overall_score = max(0.0, min(100.0, 100.0 - (failures * 10.0)))
        
        return {
            "overall_completeness_score": round(overall_score, 1),
            "missing_values": missing_counts,
            "duplicate_sales_records": duplicate_sales,
            "referential_integrity": referential_integrity,
            "inventory_days_completeness": inventory_completeness,
            "warnings": DataQuality._generate_warnings(missing_counts, duplicate_sales, referential_integrity)
        }
        
    @staticmethod
    def _check_missing_values() -> Dict[str, int]:
        results = {}
        tables = ["products", "regions", "promotions", "sales", "inventory"]
        for t in tables:
            # Query table columns
            info_df = SQLExecutor.execute(f"PRAGMA table_info({t});")
            cols = info_df["name"].tolist()
            
            for c in cols:
                # Count NULLs
                null_df = SQLExecutor.execute(f"SELECT COUNT(*) AS nulls FROM {t} WHERE {c} IS NULL OR {c} = '';")
                results[f"{t}.{c}"] = int(null_df.iloc[0]["nulls"])
        return results

    @staticmethod
    def _check_duplicate_sales() -> int:
        # Check duplicate sales transactions (identical date, product, region, units, amount)
        query = """
        SELECT COUNT(*) - COUNT(DISTINCT sale_id) AS duplicates
        FROM (
            SELECT MIN(sale_id) as sale_id, sale_date, product_id, region_id, units_sold, sales_amount, promotion_id
            FROM sales
            GROUP BY sale_date, product_id, region_id, units_sold, sales_amount, promotion_id
        );
        """
        # Alternatively, find duplicates directly:
        query = """
        SELECT SUM(cnt - 1) AS duplicates
        FROM (
            SELECT COUNT(*) AS cnt
            FROM sales
            GROUP BY sale_date, product_id, region_id, units_sold, sales_amount, promotion_id
            HAVING cnt > 1
        );
        """
        df = SQLExecutor.execute(query)
        val = df.iloc[0]["duplicates"]
        return int(val) if pd.notnull(val) else 0

    @staticmethod
    def _check_referential_integrity() -> Dict[str, int]:
        # 1. Promotions pointing to non-existent products
        q1 = "SELECT COUNT(*) AS cnt FROM promotions WHERE product_id NOT IN (SELECT product_id FROM products);"
        # 2. Sales pointing to non-existent promotions (excluding NULLs)
        q2 = "SELECT COUNT(*) AS cnt FROM sales WHERE promotion_id IS NOT NULL AND promotion_id != '' AND promotion_id NOT IN (SELECT promotion_id FROM promotions);"
        
        df1 = SQLExecutor.execute(q1)
        df2 = SQLExecutor.execute(q2)
        
        return {
            "invalid_promos_count": int(df1.iloc[0]["cnt"]),
            "sales_invalid_promo_count": int(df2.iloc[0]["cnt"])
        }

    @staticmethod
    def _check_inventory_completeness() -> Dict[str, Any]:
        # Count expected snapshots (total products * total regions * total days) vs actual records
        q_counts = """
        SELECT 
            (SELECT COUNT(*) FROM products) * 
            (SELECT COUNT(*) FROM regions) * 
            (SELECT COUNT(DISTINCT sale_date) FROM sales) AS expected_rows,
            (SELECT COUNT(*) FROM inventory) AS actual_rows;
        """
        df = SQLExecutor.execute(q_counts)
        expected = int(df.iloc[0]["expected_rows"] or 0)
        actual = int(df.iloc[0]["actual_rows"] or 0)
        
        completeness = (actual / expected) * 100.0 if expected > 0 else 0.0
        return {
            "expected_records": expected,
            "actual_records": actual,
            "percentage_completeness": round(completeness, 2)
        }

    @staticmethod
    def _generate_warnings(missing: Dict[str, int], dups: int, ref: Dict[str, int]) -> List[str]:
        warns = []
        if dups > 0:
            warns.append(f"Data contains {dups} duplicate sales records.")
        if ref["invalid_promos_count"] > 0:
            warns.append(f"Referential integrity failure: {ref['invalid_promos_count']} promotions reference non-existent products.")
        if ref["sales_invalid_promo_count"] > 0:
            warns.append(f"Referential integrity failure: {ref['sales_invalid_promo_count']} sales records reference invalid promotions.")
            
        # Check key columns with missing values
        for key, val in missing.items():
            if val > 0:
                tbl, col = key.split(".")
                # Exclude columns that naturally allow NULLs
                if col in ["promotion_id", "state_group"]:
                    continue
                warns.append(f"Column {key} contains {val} missing values.")
                
        return warns

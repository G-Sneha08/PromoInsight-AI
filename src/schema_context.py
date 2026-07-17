import sqlite3
from typing import Dict, List, Any
from src.config import DATABASE_PATH, is_db_ready
from src.metadata_catalog import METADATA_CATALOG
from src.metric_catalog import METRIC_CATALOG

class SchemaContext:
    @staticmethod
    def get_database_summary() -> Dict[str, Any]:
        """Queries the actual database to retrieve row counts, distinct values, and date ranges."""
        summary = {
            "is_ready": False,
            "row_counts": {},
            "categories": [],
            "regions": [],
            "products": [],
            "promotions": [],
            "date_range": {"min_date": None, "max_date": None}
        }
        
        if not is_db_ready():
            return summary
            
        try:
            conn = sqlite3.connect(DATABASE_PATH)
            cursor = conn.cursor()
            summary["is_ready"] = True
            
            # Row counts
            for table in METADATA_CATALOG["tables"].keys():
                cursor.execute(f"SELECT COUNT(*) FROM {table};")
                summary["row_counts"][table] = cursor.fetchone()[0]
                
            # Categories
            cursor.execute("SELECT DISTINCT category FROM products;")
            summary["categories"] = [r[0] for r in cursor.fetchall() if r[0]]
            
            # Regions
            cursor.execute("SELECT DISTINCT region_name FROM regions;")
            summary["regions"] = [r[0] for r in cursor.fetchall() if r[0]]
            
            # Products
            cursor.execute("SELECT product_id, product_name, category, brand FROM products;")
            summary["products"] = [
                {"product_id": r[0], "product_name": r[1], "category": r[2], "brand": r[3]}
                for r in cursor.fetchall()
            ]
            
            # Promotions
            cursor.execute("SELECT promotion_id, promotion_name, start_date, end_date FROM promotions;")
            summary["promotions"] = [
                {"promotion_id": r[0], "promotion_name": r[1], "start_date": r[2], "end_date": r[3]}
                for r in cursor.fetchall()
            ]
            
            # Date range from sales
            cursor.execute("SELECT MIN(sale_date), MAX(sale_date) FROM sales;")
            dates = cursor.fetchone()
            if dates:
                summary["date_range"]["min_date"] = dates[0]
                summary["date_range"]["max_date"] = dates[1]
                
            conn.close()
        except Exception as e:
            # Fallback if query fails
            print(f"Error loading schema context from database: {e}")
            
        return summary

    @staticmethod
    def get_prompt_context_string() -> str:
        """Returns a string describing the database schema and metrics for the LLM planner context."""
        summary = SchemaContext.get_database_summary()
        
        context = []
        context.append("=== DATABASE SCHEMA ===")
        for table, details in METADATA_CATALOG["tables"].items():
            context.append(f"Table: {table}")
            context.append(f"  Description: {details['description']}")
            context.append("  Columns:")
            for col, col_det in details["columns"].items():
                context.append(f"    - {col} ({col_det['type']}): {col_det['meaning']} (e.g. {col_det['example']})")
                
        context.append("\n=== BUSINESS METRIC CATALOG ===")
        for metric, details in METRIC_CATALOG.items():
            context.append(f"Metric: {metric}")
            context.append(f"  Description: {details['description']}")
            context.append(f"  Formula: {details['formula']}")
            context.append(f"  Compatible Dimensions: {', '.join(details['compatible_dimensions'])}")
            
        context.append("\n=== INSTANCE VALUES IN DATABASE ===")
        context.append(f"Available Regions: {', '.join(summary['regions'])}")
        context.append(f"Available Categories: {', '.join(summary['categories'])}")
        context.append(f"Dataset Date Range: {summary['date_range']['min_date']} to {summary['date_range']['max_date']}")
        
        promo_list = [f"{p['promotion_id']} ({p['promotion_name']})" for p in summary['promotions'][:5]]
        context.append(f"Example Promotions: {', '.join(promo_list)}")
        
        prod_list = [p['product_name'] for p in summary['products'][:5]]
        context.append(f"Example Products: {', '.join(prod_list)}")
        
        return "\n".join(context)

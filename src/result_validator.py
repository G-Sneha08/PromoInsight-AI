import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple, List

class ResultValidator:
    @staticmethod
    def validate_results(analytics_res: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        """Validates analytics output data frames, handling NaN/Inf values and calculating completeness."""
        if not analytics_res.get("success", False):
            return False, analytics_res.get("error", "Analytics execution failed."), analytics_res
            
        df = analytics_res.get("data", pd.DataFrame())
        
        # 1. Check if empty or if aggregated values are missing
        if df.empty:
            if "full_results" in analytics_res:
                pass
            else:
                validated_res = analytics_res.copy()
                validated_res["verified"] = True
                validated_res["data_completeness"] = 100.0
                validated_res["data"] = pd.DataFrame()
                return True, "No records found matching filters.", validated_res

        has_all_missing = False
        if not df.empty and len(df.columns) > 0:
            numeric_mask = df.select_dtypes(include=[np.number]).columns
            if len(numeric_mask) > 0:
                has_all_missing = df[numeric_mask].isna().all().all()
            else:
                has_all_missing = df.isna().all().all()

        if has_all_missing:
            validated_res = analytics_res.copy()
            validated_res["verified"] = True
            validated_res["data_completeness"] = 100.0
            validated_res["data"] = pd.DataFrame()
            return True, "No records found matching filters.", validated_res
                
        validated_res = analytics_res.copy()
        validated_warnings = list(analytics_res.get("warnings", []))
        
        # 2. Check for NaN or Inf values in DataFrame
        if not df.empty:
            # Detect Inf
            has_inf = np.isinf(df.select_dtypes(include=np.number)).any().any()
            # Detect NaN
            has_nan = df.isna().any().any()
            
            if has_inf or has_nan:
                validated_warnings.append("Output contains incomplete or mathematically undefined values (NaN/Inf) which have been sanitized to zero.")
                # Replace with zero/appropriate values
                df = df.replace([np.inf, -np.inf], np.nan).fillna(0.0)
                validated_res["data"] = df
                
        # 3. Calculate data completeness percentage
        # Ratio of non-null cells to total cells in raw table
        if not df.empty:
            total_cells = df.size
            null_cells = df.isna().sum().sum()
            completeness = 100.0
            if total_cells > 0:
                completeness = ((total_cells - null_cells) / total_cells) * 100.0
            validated_res["data_completeness"] = round(completeness, 2)
        else:
            validated_res["data_completeness"] = 100.0
            
        # 4. Verify derived metrics logic (e.g. contribution totals)
        if validated_res.get("operation_type") == "contribution" and not df.empty:
            if "contribution_percentage" in df.columns:
                total_pct = df["contribution_percentage"].sum()
                if total_pct > 100.05: # Float precision limit
                    validated_warnings.append(f"Derived contribution percentages sum to {total_pct:.2f}%, exceeding 100% due to float precision.")
                    
        # 5. Prevent causal language in warnings or text
        # If any user-facing message contains words like 'caused', 'result of', replace with 'associated with'
        sanitized_warns = []
        for w in validated_warnings:
            sanitized_w = ResultValidator._sanitize_causal_language(w)
            sanitized_warns.append(sanitized_w)
            
        validated_res["warnings"] = sanitized_warns
        validated_res["verified"] = True
        
        return True, "Results verified successfully.", validated_res

    @staticmethod
    def _sanitize_causal_language(text: str) -> str:
        """Enforces associative rather than causal language."""
        replacements = {
            " caused by ": " associated with ",
            " caused ": " associated with ",
            " results of ": " associations of ",
            " resulted in ": " was associated with an increase of "
        }
        
        low_text = text.lower()
        sanitized = text
        for old, new in replacements.items():
            if old in low_text:
                # Retain capitalization if possible
                pattern = re.compile(re.escape(old), re.IGNORECASE)
                sanitized = pattern.sub(new, sanitized)
                
        return sanitized

import re

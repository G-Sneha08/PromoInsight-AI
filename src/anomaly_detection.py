import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple

class AnomalyDetector:
    @staticmethod
    def detect_anomalies(df: pd.DataFrame, metric_col: str, method: str = "zscore", threshold: float = 2.0, direction: str = "both") -> pd.DataFrame:
        """Detects anomalies in a DataFrame column using Z-Score or IQR methods.
        
        Args:
            df: Pandas DataFrame containing the data.
            metric_col: Column name to evaluate.
            method: 'zscore' or 'iqr'.
            threshold: Z-score threshold (e.g. 2.0) or IQR multiplier (e.g. 1.5).
            direction: 'spikes' (positive only), 'drops' (negative only), or 'both'.
        """
        if df.empty or metric_col not in df.columns:
            return pd.DataFrame()
            
        # Clean infinite or NaN values
        clean_df = df.copy()
        clean_df[metric_col] = pd.to_numeric(clean_df[metric_col], errors='coerce')
        clean_df = clean_df.dropna(subset=[metric_col])
        
        if len(clean_df) < 3:
            # Insufficient data to compute variance/quantiles
            return pd.DataFrame()
            
        anomalies_mask = pd.Series(False, index=clean_df.index)
        expected_values = pd.Series(0.0, index=clean_df.index)
        deviation_scores = pd.Series(0.0, index=clean_df.index)
        
        values = clean_df[metric_col].values
        
        if method == "zscore":
            mean = np.mean(values)
            std = np.std(values)
            if std == 0:
                std = 1e-9 # avoid zero division
                
            z_scores = (values - mean) / std
            expected_values = pd.Series(mean, index=clean_df.index)
            deviation_scores = pd.Series(z_scores, index=clean_df.index)
            
            if direction == "spikes":
                anomalies_mask = z_scores > threshold
            elif direction == "drops":
                anomalies_mask = z_scores < -threshold
            else:
                anomalies_mask = np.abs(z_scores) > threshold
                
        elif method == "iqr":
            q25 = np.percentile(values, 25)
            q50 = np.percentile(values, 50)
            q75 = np.percentile(values, 75)
            iqr = q75 - q25
            
            expected_values = pd.Series(q50, index=clean_df.index)
            
            low_cutoff = q25 - (threshold * iqr)
            high_cutoff = q75 + (threshold * iqr)
            
            # Simple deviation score relative to IQR
            if iqr > 0:
                deviation_scores = pd.Series((values - q50) / iqr, index=clean_df.index)
            else:
                deviation_scores = pd.Series(0.0, index=clean_df.index)
                
            if direction == "spikes":
                anomalies_mask = values > high_cutoff
            elif direction == "drops":
                anomalies_mask = values < low_cutoff
            else:
                anomalies_mask = (values < low_cutoff) | (values > high_cutoff)
                
        anomalies_df = clean_df[anomalies_mask].copy()
        
        if not anomalies_df.empty:
            anomalies_df["expected_value"] = expected_values[anomalies_mask].round(2)
            anomalies_df["deviation_score"] = deviation_scores[anomalies_mask].round(2)
            
        return anomalies_df

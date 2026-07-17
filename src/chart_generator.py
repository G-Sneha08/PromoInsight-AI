import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Optional, Any

class ChartGenerator:
    @staticmethod
    def generate_chart(df: pd.DataFrame, op_type: str, metric: str) -> Optional[Any]:
        """Inspects data shape and returns a Plotly figure object, or None if not applicable."""
        if df.empty:
            return None
            
        columns = df.columns.tolist()
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        
        # Style layout configs
        layout_theme = {
            "template": "plotly_white",
            "margin": dict(l=40, r=40, t=40, b=40),
            "font": dict(family="Outfit, Inter, sans-serif", size=12),
            "hovermode": "closest"
        }
        
        # 1. Anomaly chart
        if op_type == "anomaly_detection" and "deviation_score" in columns:
            date_col = "sale_date" if "sale_date" in columns else ("trend_period" if "trend_period" in columns else columns[0])
            fig = px.scatter(
                df, 
                x=date_col, 
                y=metric,
                color="deviation_score",
                size=np.abs(df["deviation_score"]),
                hover_data=columns,
                title=f"Statistical Anomalies for {metric.replace('_', ' ').title()}",
                color_continuous_scale=px.colors.sequential.Reds
            )
            fig.update_layout(**layout_theme)
            return fig
            
        # 2. Time-series trend (Line Chart)
        date_cols = [c for c in columns if "date" in c.lower() or c == "trend_period"]
        if date_cols and len(numeric_cols) > 0:
            date_col = date_cols[0]
            y_col = numeric_cols[0]
            
            # If multiple numeric columns exist (e.g., current and prior for growth)
            if "current_value" in columns and "prior_value" in columns:
                # Grouped line or bar is better
                pass
            else:
                # Normal line chart
                # Check if there is a categorical grouping column to color by
                cat_cols = [c for c in columns if c not in date_cols and c not in numeric_cols]
                color_by = cat_cols[0] if cat_cols else None
                
                # Sort by date
                df_sorted = df.copy()
                df_sorted[date_col] = df_sorted[date_col].astype(str)
                df_sorted = df_sorted.sort_values(by=date_col)
                
                fig = px.line(
                    df_sorted, 
                    x=date_col, 
                    y=y_col, 
                    color=color_by,
                    markers=True,
                    title=f"Trend over time: {y_col.replace('_', ' ').title()}",
                    line_shape="linear"
                )
                fig.update_traces(line=dict(width=2.5))
                fig.update_layout(**layout_theme)
                return fig
                
        # 3. Growth Comparison (Grouped Bar Chart)
        if "current_value" in columns and "prior_value" in columns:
            dim_col = columns[0] if columns[0] not in ["current_value", "prior_value", "growth_percentage"] else "Metric"
            
            # Check if it's a single value contribution
            if len(df) == 1:
                # Format to vertical bars
                df_melted = pd.melt(df, id_vars=[], value_vars=["current_value", "prior_value"], var_name="Period", value_name="Sales")
                fig = px.bar(
                    df_melted,
                    x="Period",
                    y="Sales",
                    color="Period",
                    title="Period comparison",
                    color_discrete_sequence=["#1E88E5", "#FFC107"]
                )
            else:
                # Grouped bars across dimensions
                fig = go.Figure()
                fig.add_trace(go.Bar(
                    name='Current Period',
                    x=df[dim_col], y=df['current_value'],
                    marker_color='#1E88E5'
                ))
                fig.add_trace(go.Bar(
                    name='Prior Period',
                    x=df[dim_col], y=df['prior_value'],
                    marker_color='#FFC107'
                ))
                fig.update_layout(
                    title=f"Growth Comparison by {dim_col.replace('_', ' ').title()}",
                    barmode='group',
                    **layout_theme
                )
            return fig
            
        # 4. Contribution Share (Pie Chart)
        if "contribution_percentage" in columns:
            dim_col = columns[0]
            fig = px.pie(
                df, 
                names=dim_col, 
                values="contribution_percentage",
                title=f"Revenue Contribution Share by {dim_col.replace('_', ' ').title()}",
                hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            fig.update_traces(textposition='inside', textinfo='percent+label')
            fig.update_layout(**layout_theme)
            return fig
            
        # 5. Inventory Status Flow (Grouped Bar Chart)
        if op_type == "inventory_status" and "opening_inventory" in columns and "closing_inventory" in columns:
            dim_col = columns[0] if len(columns) > 1 else "snapshot_date"
            fig = go.Figure()
            fig.add_trace(go.Bar(
                name='Opening Stock',
                x=df[dim_col], y=df['opening_inventory'],
                marker_color='#4CAF50'
            ))
            fig.add_trace(go.Bar(
                name='Closing Stock',
                x=df[dim_col], y=df['closing_inventory'],
                marker_color='#F44336'
            ))
            if "received_units" in columns:
                fig.add_trace(go.Bar(
                    name='Received Stock',
                    x=df[dim_col], y=df['received_units'],
                    marker_color='#2196F3'
                ))
                
            fig.update_layout(
                title="Inventory Stock flow",
                barmode='group',
                **layout_theme
            )
            return fig
            
        # 6. Default: Categorical vs Numeric (Bar Chart)
        if len(numeric_cols) > 0:
            y_col = numeric_cols[0]
            cat_cols = [c for c in columns if c != y_col and c != "trend_period"]
            if cat_cols:
                x_col = cat_cols[0]
                
                # Sort for clean visualization
                df_sorted = df.sort_values(by=y_col, ascending=False)
                
                fig = px.bar(
                    df_sorted, 
                    x=x_col, 
                    y=y_col,
                    color=x_col,
                    title=f"{y_col.replace('_', ' ').title()} by {x_col.replace('_', ' ').title()}",
                    color_discrete_sequence=px.colors.qualitative.Vivid
                )
                fig.update_layout(showlegend=False, **layout_theme)
                return fig
                
        return None

import numpy as np

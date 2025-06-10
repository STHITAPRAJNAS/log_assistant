"""Visualization tools for LogDetective."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Any, Optional, Tuple
from langchain_core.tools import tool
import json
import io
import base64
from config import settings


class ChartGenerator:
    """Generate charts from Splunk data."""
    
    @staticmethod
    def create_time_series_chart(df: pd.DataFrame, time_col: str = "_time", 
                               value_cols: List[str] = None, 
                               group_by: str = None) -> go.Figure:
        """Create a time series chart."""
        if df.empty:
            return go.Figure()
        
        # Convert time column to datetime
        if time_col in df.columns:
            df[time_col] = pd.to_datetime(df[time_col])
        
        fig = go.Figure()
        
        if group_by and group_by in df.columns:
            # Group by specified column
            for group in df[group_by].unique():
                group_data = df[df[group_by] == group]
                if value_cols:
                    for col in value_cols:
                        if col in group_data.columns:
                            fig.add_trace(go.Scatter(
                                x=group_data[time_col],
                                y=group_data[col],
                                name=f"{group}_{col}",
                                mode='lines+markers'
                            ))
                else:
                    # Use count if no value columns specified
                    fig.add_trace(go.Scatter(
                        x=group_data[time_col],
                        y=[1] * len(group_data),
                        name=str(group),
                        mode='lines+markers'
                    ))
        else:
            if value_cols:
                for col in value_cols:
                    if col in df.columns:
                        fig.add_trace(go.Scatter(
                            x=df[time_col],
                            y=df[col],
                            name=col,
                            mode='lines+markers'
                        ))
            else:
                # Default time series of event count
                time_counts = df.groupby(df[time_col].dt.floor('H')).size()
                fig.add_trace(go.Scatter(
                    x=time_counts.index,
                    y=time_counts.values,
                    name='Event Count',
                    mode='lines+markers'
                ))
        
        fig.update_layout(
            title="Time Series Analysis",
            xaxis_title="Time",
            yaxis_title="Value",
            template=settings.chart_theme
        )
        
        return fig
    
    @staticmethod
    def create_bar_chart(df: pd.DataFrame, category_col: str, 
                        value_col: str = None, title: str = "Bar Chart") -> go.Figure:
        """Create a bar chart.""" 
        if df.empty or category_col not in df.columns:
            return go.Figure()
        
        if value_col and value_col in df.columns:
            # Use specified value column
            data = df.groupby(category_col)[value_col].sum().sort_values(ascending=False)
        else:
            # Count occurrences
            data = df[category_col].value_counts()
        
        fig = go.Figure(data=[
            go.Bar(x=data.index, y=data.values)
        ])
        
        fig.update_layout(
            title=title,
            xaxis_title=category_col,
            yaxis_title=value_col or "Count",
            template=settings.chart_theme
        )
        
        return fig
    
    @staticmethod
    def create_pie_chart(df: pd.DataFrame, category_col: str,
                        value_col: str = None, title: str = "Pie Chart") -> go.Figure:
        """Create a pie chart."""
        if df.empty or category_col not in df.columns:
            return go.Figure()
        
        if value_col and value_col in df.columns:
            data = df.groupby(category_col)[value_col].sum()
        else:
            data = df[category_col].value_counts()
        
        fig = go.Figure(data=[
            go.Pie(labels=data.index, values=data.values)
        ])
        
        fig.update_layout(
            title=title,
            template=settings.chart_theme
        )
        
        return fig
    
    @staticmethod
    def create_heatmap(df: pd.DataFrame, x_col: str, y_col: str,
                      value_col: str = None, title: str = "Heatmap") -> go.Figure:
        """Create a heatmap."""
        if df.empty or x_col not in df.columns or y_col not in df.columns:
            return go.Figure()
        
        if value_col and value_col in df.columns:
            pivot_data = df.pivot_table(values=value_col, index=y_col, columns=x_col, fill_value=0)
        else:
            # Count occurrences
            pivot_data = df.groupby([y_col, x_col]).size().unstack(fill_value=0)
        
        fig = go.Figure(data=go.Heatmap(
            z=pivot_data.values,
            x=pivot_data.columns,
            y=pivot_data.index,
            colorscale='Blues'
        ))
        
        fig.update_layout(
            title=title,
            xaxis_title=x_col,
            yaxis_title=y_col,
            template=settings.chart_theme
        )
        
        return fig
    
    @staticmethod
    def create_histogram(df: pd.DataFrame, column: str, 
                        bins: int = 20, title: str = "Histogram") -> go.Figure:
        """Create a histogram."""
        if df.empty or column not in df.columns:
            return go.Figure()
        
        fig = go.Figure(data=[
            go.Histogram(x=df[column], nbinsx=bins)
        ])
        
        fig.update_layout(
            title=title,
            xaxis_title=column,
            yaxis_title="Count",
            template=settings.chart_theme
        )
        
        return fig


# Global chart generator instance
chart_generator = ChartGenerator()


@tool
def create_visualization(data_json: str, chart_type: str, 
                        x_column: str = None, y_column: str = None,
                        group_by: str = None, title: str = None) -> str:
    """
    Create a visualization from Splunk data.
    
    Args:
        data_json: JSON string containing the data
        chart_type: Type of chart (bar, pie, line, histogram, heatmap, timeseries)
        x_column: Column for x-axis
        y_column: Column for y-axis
        group_by: Column to group data by
        title: Chart title
    
    Returns:
        JSON string with chart configuration and data
    """
    try:
        # Parse data
        data = json.loads(data_json)
        
        if isinstance(data, dict) and "results" in data:
            df = pd.DataFrame(data["results"])
        else:
            df = pd.DataFrame(data)
        
        if df.empty:
            return json.dumps({
                "error": "No data available for visualization",
                "chart_type": chart_type
            })
        
        # Generate appropriate chart
        fig = go.Figure()
        
        if chart_type.lower() == "bar":
            if x_column and x_column in df.columns:
                fig = chart_generator.create_bar_chart(df, x_column, y_column, title or "Bar Chart")
            else:
                # Use first non-time column
                non_time_cols = [col for col in df.columns if col != "_time"]
                if non_time_cols:
                    fig = chart_generator.create_bar_chart(df, non_time_cols[0], y_column, title or "Bar Chart")
        
        elif chart_type.lower() == "pie":
            if x_column and x_column in df.columns:
                fig = chart_generator.create_pie_chart(df, x_column, y_column, title or "Pie Chart")
            else:
                non_time_cols = [col for col in df.columns if col != "_time"]
                if non_time_cols:
                    fig = chart_generator.create_pie_chart(df, non_time_cols[0], y_column, title or "Pie Chart")
        
        elif chart_type.lower() in ["line", "timeseries"]:
            time_col = "_time" if "_time" in df.columns else x_column
            value_cols = [y_column] if y_column else None
            fig = chart_generator.create_time_series_chart(df, time_col, value_cols, group_by)
        
        elif chart_type.lower() == "histogram":
            if x_column and x_column in df.columns:
                fig = chart_generator.create_histogram(df, x_column, title=title or "Histogram")
        
        elif chart_type.lower() == "heatmap":
            if x_column and y_column and x_column in df.columns and y_column in df.columns:
                fig = chart_generator.create_heatmap(df, x_column, y_column, title=title or "Heatmap")
        
        # Convert figure to JSON
        chart_json = fig.to_json()
        
        return json.dumps({
            "chart_type": chart_type,
            "chart_config": json.loads(chart_json),
            "data_summary": {
                "rows": len(df),
                "columns": list(df.columns),
                "column_count": len(df.columns)
            },
            "title": title or f"{chart_type.title()} Chart"
        }, indent=2)
        
    except Exception as e:
        return json.dumps({
            "error": f"Error creating visualization: {str(e)}",
            "chart_type": chart_type
        })


@tool
def suggest_visualization(data_json: str) -> str:
    """
    Suggest appropriate visualization types based on the data structure.
    
    Args:
        data_json: JSON string containing the data
    
    Returns:
        JSON string with visualization suggestions
    """
    try:
        # Parse data
        data = json.loads(data_json)
        
        if isinstance(data, dict) and "results" in data:
            df = pd.DataFrame(data["results"])
        else:
            df = pd.DataFrame(data)
        
        if df.empty:
            return json.dumps({
                "suggestions": [],
                "message": "No data available for analysis"
            })
        
        suggestions = []
        
        # Analyze data structure
        numeric_columns = df.select_dtypes(include=['number']).columns.tolist()
        categorical_columns = df.select_dtypes(include=['object', 'category']).columns.tolist()
        time_columns = [col for col in df.columns if 'time' in col.lower() or col == '_time']
        
        # Time series suggestions
        if time_columns:
            suggestions.append({
                "chart_type": "timeseries",
                "description": "Time series line chart showing trends over time",
                "recommended_params": {
                    "x_column": time_columns[0],
                    "y_column": numeric_columns[0] if numeric_columns else None,
                    "group_by": categorical_columns[0] if categorical_columns else None
                }
            })
        
        # Categorical analysis suggestions
        if categorical_columns:
            suggestions.append({
                "chart_type": "bar",
                "description": f"Bar chart showing distribution of {categorical_columns[0]}",
                "recommended_params": {
                    "x_column": categorical_columns[0],
                    "y_column": numeric_columns[0] if numeric_columns else None
                }
            })
            
            suggestions.append({
                "chart_type": "pie",
                "description": f"Pie chart showing proportions of {categorical_columns[0]}",
                "recommended_params": {
                    "x_column": categorical_columns[0],
                    "y_column": numeric_columns[0] if numeric_columns else None
                }
            })
        
        # Numeric data suggestions
        if numeric_columns:
            suggestions.append({
                "chart_type": "histogram",
                "description": f"Histogram showing distribution of {numeric_columns[0]}",
                "recommended_params": {
                    "x_column": numeric_columns[0]
                }
            })
        
        # Correlation/relationship suggestions
        if len(categorical_columns) >= 2:
            suggestions.append({
                "chart_type": "heatmap",
                "description": f"Heatmap showing relationship between {categorical_columns[0]} and {categorical_columns[1]}",
                "recommended_params": {
                    "x_column": categorical_columns[0],
                    "y_column": categorical_columns[1]
                }
            })
        
        return json.dumps({
            "suggestions": suggestions,
            "data_analysis": {
                "total_rows": len(df),
                "total_columns": len(df.columns),
                "numeric_columns": numeric_columns,
                "categorical_columns": categorical_columns,
                "time_columns": time_columns
            }
        }, indent=2)
        
    except Exception as e:
        return json.dumps({
            "error": f"Error analyzing data for visualization: {str(e)}",
            "suggestions": []
        }) 
"""Main Streamlit application for LogDetective."""

import streamlit as st
import plotly.graph_objects as go
import json
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import time

# Import LogDetective components
from agents import log_detective
from config import settings
from splunk_tools import splunk_connector

# Configure Streamlit page
st.set_page_config(
    page_title="LogDetective - Splunk Assistant",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for production-grade styling
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #1f4e79, #2d5aa0);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .status-connected {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        padding: 0.5rem;
        border-radius: 5px;
        display: inline-block;
    }
    
    .status-disconnected {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
        padding: 0.5rem;
        border-radius: 5px;
        display: inline-block;
    }
    
    .metric-card {
        background-color: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    
    .query-box {
        background-color: #f1f3f4;
        border-left: 4px solid #1f4e79;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 5px;
    }
    
    .response-box {
        background-color: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
    }
    
    .sidebar-section {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)


def initialize_session_state():
    """Initialize Streamlit session state."""
    if 'conversation_history' not in st.session_state:
        st.session_state.conversation_history = []
    
    if 'index_info' not in st.session_state:
        st.session_state.index_info = None
        
    if 'connection_status' not in st.session_state:
        st.session_state.connection_status = None


def display_header():
    """Display the main header."""
    st.markdown("""
    <div class="main-header">
        <h1>🔍 LogDetective</h1>
        <p>AI-Powered Splunk Log Analysis Assistant</p>
    </div>
    """, unsafe_allow_html=True)


def display_sidebar():
    """Display the sidebar with connection info and controls."""
    st.sidebar.markdown("### 🔧 System Status")
    
    # Connection Status Section
    with st.sidebar.expander("📡 Splunk Connection", expanded=True):
        if st.button("Test Connection", key="test_connection"):
            with st.spinner("Testing connection..."):
                st.session_state.index_info = log_detective.get_index_info()
                st.session_state.connection_status = st.session_state.index_info.get("connection", {})
        
        # Display connection status
        if st.session_state.connection_status:
            is_connected = st.session_state.connection_status.get("connected", False)
            
            if is_connected:
                st.markdown("""
                <div class="status-connected">
                    ✅ Connected to Splunk
                </div>
                """, unsafe_allow_html=True)
                
                st.write(f"**Host:** {st.session_state.connection_status.get('host', 'N/A')}")
                st.write(f"**Port:** {st.session_state.connection_status.get('port', 'N/A')}")
                st.write(f"**Index:** {st.session_state.connection_status.get('index', 'N/A')}")
                
            else:
                st.markdown("""
                <div class="status-disconnected">
                    ❌ Not Connected to Splunk
                </div>
                """, unsafe_allow_html=True)
                st.warning("Please check your Splunk configuration.")
    
    # Index Information Section
    with st.sidebar.expander("📊 Index 104118 Info", expanded=False):
        if st.session_state.index_info and st.session_state.index_info.get("fields"):
            fields_data = st.session_state.index_info["fields"]
            available_fields = fields_data.get("available_fields", [])
            
            st.write(f"**Available Fields:** {len(available_fields)}")
            
            # Display fields in a selectbox for easy reference
            if available_fields:
                selected_field = st.selectbox(
                    "Browse Available Fields:",
                    ["Select a field..."] + available_fields,
                    key="field_browser"
                )
                
                if selected_field != "Select a field...":
                    st.code(f"field: {selected_field}", language="sql")
        else:
            st.info("Test connection to view available fields")
    
    # Quick Actions
    st.sidebar.markdown("### ⚡ Quick Actions")
    
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("🔍 Recent Logs", key="recent_logs"):
            st.session_state.quick_query = "Show me the latest 10 log entries"
    
    with col2:
        if st.button("📈 Log Stats", key="log_stats"):
            st.session_state.quick_query = "Show me log statistics by host"
    
    # Sample Queries
    with st.sidebar.expander("💡 Sample Queries", expanded=False):
        sample_queries = [
            "Show me the latest 20 log entries",
            "Count events by host and show top 10",
            "Find error or failed events in the last hour",
            "Create a time chart showing log volume over the last 24 hours",
            "Show unique sourcetype values with counts",
            "Analyze logs by source and show statistics",
            "Find the most active hosts in the last 6 hours",
            "Show logs containing 'exception' with details",
            "Create a chart of events by hour of day",
            "Show logs with response times greater than 1000ms"
        ]
        
        for query in sample_queries:
            if st.button(f"▶️ {query}", key=f"sample_{hash(query)}"):
                st.session_state.quick_query = query


def display_main_interface():
    """Display the main chat interface."""
    st.markdown("### 💬 Chat with LogDetective")
    
    # Handle quick queries from sidebar
    initial_query = ""
    if hasattr(st.session_state, 'quick_query'):
        initial_query = st.session_state.quick_query
        delattr(st.session_state, 'quick_query')
    
    # Query input
    user_query = st.text_area(
        "Ask me anything about your Splunk logs:",
        value=initial_query,
        height=100,
        placeholder="Examples:\n• Show me the latest 50 log entries\n• Count events by host and create a chart\n• Find error or failed events in the last 2 hours\n• Analyze log patterns and identify anomalies"
    )
    
    col1, col2, col3 = st.columns([1, 1, 4])
    
    with col1:
        submit_button = st.button("🚀 Analyze", type="primary")
    
    with col2:
        clear_button = st.button("🗑️ Clear History")
    
    if clear_button:
        st.session_state.conversation_history = []
        st.rerun()
    
    # Process query
    if submit_button and user_query.strip():
        process_user_query(user_query.strip())
    
    # Display conversation history
    display_conversation_history()


def process_user_query(query: str):
    """Process user query through LogDetective agents."""
    # Add user query to history
    st.session_state.conversation_history.append({
        "role": "user",
        "content": query,
        "timestamp": datetime.now()
    })
    
    # Show processing indicator
    with st.spinner("🤖 LogDetective is analyzing your request..."):
        try:
            # Process through multi-agent system
            response = log_detective.process_request(query)
            
            if response.get("success"):
                # Add successful response to history
                st.session_state.conversation_history.append({
                    "role": "assistant",
                    "content": response.get("response", {}),
                    "timestamp": datetime.now(),
                    "query": query
                })
                
                st.success("Analysis complete!")
            else:
                # Add error response to history
                error_message = response.get("error", "Unknown error occurred")
                st.session_state.conversation_history.append({
                    "role": "error",
                    "content": f"Error: {error_message}",
                    "timestamp": datetime.now(),
                    "query": query
                })
                
                st.error(f"Error processing request: {error_message}")
                
        except Exception as e:
            st.error(f"Unexpected error: {str(e)}")
            st.session_state.conversation_history.append({
                "role": "error",
                "content": f"Unexpected error: {str(e)}",
                "timestamp": datetime.now(),
                "query": query
            })


def display_conversation_history():
    """Display the conversation history."""
    if not st.session_state.conversation_history:
        st.info("👋 Welcome! Ask me about your Splunk logs to get started.")
        return
    
    st.markdown("### 📜 Conversation History")
    
    # Display in reverse order (newest first)
    for i, entry in enumerate(reversed(st.session_state.conversation_history)):
        with st.container():
            if entry["role"] == "user":
                display_user_message(entry)
            elif entry["role"] == "assistant":
                display_assistant_message(entry)
            elif entry["role"] == "error":
                display_error_message(entry)
            
            if i < len(st.session_state.conversation_history) - 1:
                st.markdown("---")


def display_user_message(entry: Dict[str, Any]):
    """Display a user message."""
    timestamp = entry["timestamp"].strftime("%H:%M:%S")
    
    st.markdown(f"""
    <div class="query-box">
        <strong>🧑‍💻 You ({timestamp}):</strong><br>
        {entry["content"]}
    </div>
    """, unsafe_allow_html=True)


def display_assistant_message(entry: Dict[str, Any]):
    """Display an assistant message."""
    timestamp = entry["timestamp"].strftime("%H:%M:%S")
    content = entry["content"]
    
    st.markdown(f"**🤖 LogDetective ({timestamp}):**")
    
    # Handle different types of responses
    if isinstance(content, dict):
        # Try to extract and display relevant information
        display_structured_response(content)
    else:
        st.markdown(f"""
        <div class="response-box">
            {str(content)}
        </div>
        """, unsafe_allow_html=True)


def display_error_message(entry: Dict[str, Any]):
    """Display an error message."""
    timestamp = entry["timestamp"].strftime("%H:%M:%S")
    
    st.error(f"⚠️ Error ({timestamp}): {entry['content']}")


def display_structured_response(response_data: Dict[str, Any]):
    """Display structured response data."""
    try:
        # Look for messages in the response
        if "messages" in response_data:
            messages = response_data["messages"]
            
            # Extract and display assistant messages and results
            assistant_content = []
            query_results = []
            chart_data = None
            
            for message in messages:
                if isinstance(message, dict):
                    role = message.get("role", "unknown")
                    content = message.get("content", "")
                    
                    if role == "assistant":
                        assistant_content.append(content)
                    elif role == "tool" and content:
                        # Try to parse tool results
                        try:
                            tool_result = json.loads(content) if isinstance(content, str) else content
                            
                            # Check if it's query results
                            if isinstance(tool_result, dict) and "results" in tool_result:
                                query_results.append(tool_result)
                            elif isinstance(tool_result, dict) and "chart_config" in tool_result:
                                chart_data = tool_result
                        except:
                            # If not JSON, just include as text
                            assistant_content.append(content)
            
            # Display assistant content (textual summary)
            if assistant_content:
                st.markdown("### 📝 Analysis Summary")
                for content in assistant_content:
                    if content.strip():
                        st.markdown(content)
                        st.markdown("---")
            
            # Display query results as tables
            if query_results:
                for i, result in enumerate(query_results):
                    if result.get("success") and result.get("results"):
                        st.markdown(f"### 📊 Query Results {i+1 if len(query_results) > 1 else ''}")
                        
                        # Show query executed
                        if "query_executed" in result:
                            st.code(result["query_executed"], language="sql")
                        
                        # Display results table
                        display_data_table(result["results"])
                        
                        # Show query stats
                        if "stats" in result:
                            stats = result["stats"]
                            col1, col2, col3, col4 = st.columns(4)
                            with col1:
                                st.metric("Results", stats.get("result_count", 0))
                            with col2:
                                st.metric("Events Scanned", stats.get("scan_count", 0))
                            with col3:
                                st.metric("Runtime (s)", f"{float(stats.get('run_duration', 0)):.2f}")
                            with col4:
                                st.metric("Fields", result.get("field_count", 0))
                    
                    elif not result.get("success"):
                        st.error(f"Query Error: {result.get('message', 'Unknown error')}")
            
            # Display charts
            if chart_data:
                display_chart(chart_data)
        
        else:
            # Fallback for other response formats
            st.json(response_data)
            
    except Exception as e:
        st.error(f"Error displaying response: {str(e)}")
        st.json(response_data)  # Fallback to JSON display


def display_chart(chart_data: Dict[str, Any]):
    """Display a chart from chart configuration."""
    try:
        chart_config = chart_data.get("chart_config", {})
        
        if chart_config:
            fig = go.Figure(chart_config)
            st.plotly_chart(fig, use_container_width=True)
            
            # Display chart metadata
            if "data_summary" in chart_data:
                summary = chart_data["data_summary"]
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Rows", summary.get("rows", 0))
                with col2:
                    st.metric("Columns", summary.get("column_count", 0))
                with col3:
                    st.metric("Chart Type", chart_data.get("chart_type", "Unknown"))
                    
    except Exception as e:
        st.error(f"Error displaying chart: {str(e)}")


def display_data_table(data: list):
    """Display data in a table format."""
    if data and len(data) > 0:
        df = pd.DataFrame(data)
        
        st.subheader("📊 Data Results")
        st.dataframe(df, use_container_width=True)
        
        # Display summary metrics
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Records", len(df))
        with col2:
            st.metric("Fields", len(df.columns))


def main():
    """Main application function."""
    initialize_session_state()
    display_header()
    display_sidebar()
    display_main_interface()
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; padding: 1rem;">
        LogDetective v1.0 | Powered by LangGraph & AWS Bedrock | 
        <a href="https://github.com/your-repo/logdetective" target="_blank">GitHub</a>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main() 
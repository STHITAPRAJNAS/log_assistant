"""Simplified Streamlit interface for LogDetective workflow."""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import json
import time

from logdetective_workflow import log_detective_workflow
from config import settings

# Page configuration
st.set_page_config(
    page_title="LogDetective Workflow",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        text-align: center;
    }
    
    .success { color: #28a745; }
    .error { color: #dc3545; }
    .warning { color: #ffc107; }
</style>
""", unsafe_allow_html=True)


def initialize_session_state():
    """Initialize session state variables."""
    if 'query_history' not in st.session_state:
        st.session_state.query_history = []
    if 'current_result' not in st.session_state:
        st.session_state.current_result = None


def render_header():
    """Render the main header."""
    st.markdown("""
    <div class="main-header">
        <h1>🔍 LogDetective</h1>
        <p>AI-Powered Splunk Log Analysis with LangGraph Workflow</p>
    </div>
    """, unsafe_allow_html=True)


def render_sidebar():
    """Render sidebar with system information."""
    st.sidebar.title("🎛️ System Info")
    
    # Workflow info
    with st.sidebar.expander("📊 Workflow Details", expanded=True):
        info = log_detective_workflow.get_workflow_info()
        st.write(f"**Nodes:** {len(info['nodes'])}")
        st.write("**Features:**")
        for feature in info['features']:
            st.write(f"• {feature}")
    
    # System health
    with st.sidebar.expander("🔧 Health Check"):
        if st.button("🔄 Test Connections"):
            with st.spinner("Testing..."):
                try:
                    from splunk_tools import splunk_connector
                    splunk_ok = splunk_connector.test_connection()
                    st.success("✅ Splunk Connected" if splunk_ok else "❌ Splunk Failed")
                    
                    from knowledge_store import knowledge_store
                    docs = knowledge_store.search("test", k=1)
                    st.success(f"✅ Knowledge Base ({len(docs)} docs)")
                    
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
    
    # Recent queries
    with st.sidebar.expander("📚 Recent Queries"):
        if st.session_state.query_history:
            for i, query in enumerate(st.session_state.query_history[-5:]):
                st.write(f"**{i+1}.** {query['user_query'][:30]}...")
                if query.get('success'):
                    st.write(f"<span class='success'>✅ {query.get('execution_time', 0):.1f}s</span>", 
                           unsafe_allow_html=True)
                else:
                    st.write("<span class='error'>❌ Failed</span>", unsafe_allow_html=True)
                st.divider()
        else:
            st.info("No recent queries")


def render_query_interface():
    """Render the main query interface."""
    st.subheader("💭 Ask LogDetective")
    
    # Sample queries
    sample_queries = [
        "Show me the top 10 hosts by event count",
        "Find all error events in the last hour", 
        "What are the most common log levels?",
        "Show network traffic by destination port",
        "Find authentication failures",
        "Display disk usage alerts over time"
    ]
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        user_query = st.text_area(
            "Enter your question:",
            placeholder="e.g., Show me all error events in the last 24 hours",
            height=100,
            key="query_input"
        )
    
    with col2:
        st.write("**Quick Start:**")
        for query in sample_queries:
            if st.button(query, key=f"sample_{hash(query)}", use_container_width=True):
                st.session_state.query_input = query
                st.experimental_rerun()
    
    return user_query


def execute_query(user_query: str):
    """Execute query and show results."""
    if not user_query.strip():
        st.warning("Please enter a query")
        return
    
    # Progress tracking
    progress_container = st.container()
    results_container = st.container()
    
    with progress_container:
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        status_text.text("🚀 Starting workflow...")
        progress_bar.progress(20)
    
    try:
        with st.spinner("Processing your query..."):
            # Execute the workflow
            result = log_detective_workflow.process_query(user_query)
        
        progress_bar.progress(100)
        status_text.text("✅ Query completed!")
        
        # Store result
        st.session_state.current_result = result
        st.session_state.query_history.append(result)
        
        # Display results
        with results_container:
            display_results(result)
            
    except Exception as e:
        progress_bar.progress(100)
        status_text.text("❌ Query failed")
        st.error(f"Error: {str(e)}")


def display_results(result):
    """Display query results."""
    if not result.get('success'):
        st.error(f"❌ Query failed: {result.get('error', 'Unknown error')}")
        return
    
    # Header with key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Execution Time", f"{result.get('execution_time', 0):.2f}s")
    
    with col2:
        status = "✅ Connected" if result.get('splunk_connected') else "❌ Disconnected"
        st.metric("Splunk Status", status)
    
    with col3:
        retries = result.get('retry_count', 0)
        st.metric("Retries", retries)
    
    with col4:
        turn_id = result.get('turn_id', 'N/A')
        st.metric("Turn ID", turn_id)
    
    # Analysis response
    if result.get('analysis_response'):
        st.subheader("📝 Analysis")
        st.write(result['analysis_response'])
    
    # SPL query
    if result.get('spl_query'):
        st.subheader("🔍 Generated SPL Query")
        st.code(result['spl_query'], language='sql')
        
        if result.get('spl_explanation'):
            st.info(f"**Explanation:** {result['spl_explanation']}")
    
    # Query results
    query_results = result.get('query_results')
    if query_results and query_results.get('success'):
        display_data_results(query_results)
    
    # Visualization
    viz_config = result.get('visualization_config')
    if viz_config:
        display_visualization(viz_config)
    
    # Error details
    if result.get('error_message'):
        st.error(f"⚠️ Warning: {result['error_message']}")


def display_data_results(query_results):
    """Display query data results."""
    st.subheader("📊 Data Results")
    
    data = query_results.get('data', [])
    if not data:
        st.info("No data returned from query")
        return
    
    # Summary
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Results:** {len(data)} rows")
        st.write(f"**Fields:** {len(query_results.get('fields', []))}")
    
    with col2:
        stats = query_results.get('stats', {})
        st.write(f"**Events Scanned:** {stats.get('scan_count', 0):,}")
        st.write(f"**Query Time:** {stats.get('run_duration', 0):.2f}s")
    
    # Data table
    df = pd.DataFrame(data)
    st.dataframe(df, use_container_width=True)
    
    # Download option
    if len(data) > 0:
        csv = df.to_csv(index=False)
        st.download_button(
            label="📥 Download CSV",
            data=csv,
            file_name=f"logdetective_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )


def display_visualization(viz_config):
    """Display visualization."""
    st.subheader("📈 Visualization")
    
    try:
        chart_config = viz_config.get('chart_config', {})
        chart_data = chart_config.get('data', [])
        chart_type = chart_config.get('chart_type', 'bar')
        
        if chart_data:
            df = pd.DataFrame(chart_data)
            
            if chart_type == 'bar':
                fig = px.bar(df, x=df.columns[0], y=df.columns[1])
            elif chart_type == 'line':
                fig = px.line(df, x=df.columns[0], y=df.columns[1])
            elif chart_type == 'pie':
                fig = px.pie(df, names=df.columns[0], values=df.columns[1])
            else:
                fig = px.scatter(df, x=df.columns[0], y=df.columns[1])
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No visualization data available")
            
    except Exception as e:
        st.error(f"Visualization error: {str(e)}")


def main():
    """Main application."""
    initialize_session_state()
    render_header()
    render_sidebar()
    
    # Main query interface
    user_query = render_query_interface()
    
    # Execution modes
    col1, col2 = st.columns([2, 1])
    
    with col1:
        if st.button("🚀 Execute Query", type="primary", use_container_width=True):
            execute_query(user_query)
    
    with col2:
        if st.button("🔄 Stream Execution", use_container_width=True):
            stream_execution(user_query)
    
    # Display current result if available
    if st.session_state.current_result:
        st.divider()
        st.subheader("📋 Current Results")
        display_results(st.session_state.current_result)


def stream_execution(user_query: str):
    """Stream workflow execution."""
    if not user_query.strip():
        st.warning("Please enter a query")
        return
    
    st.subheader("🔄 Live Execution Stream")
    
    # Create containers for streaming
    status_container = st.container()
    steps_container = st.container()
    
    with status_container:
        status_placeholder = st.empty()
    
    try:
        step_count = 0
        for update in log_detective_workflow.stream_query(user_query):
            step_count += 1
            
            with status_placeholder.container():
                st.write(f"**Step {step_count}:** {update.get('step', 'unknown')}")
                st.write(f"**Time:** {update.get('timestamp', '')}")
            
            with steps_container:
                if update.get('error'):
                    st.error(f"❌ Error in {update.get('step')}: {update.get('error')}")
                else:
                    st.success(f"✅ Completed: {update.get('step')}")
            
            time.sleep(0.5)  # Brief pause for visibility
        
        # Get final result
        result = log_detective_workflow.process_query(user_query)
        st.session_state.current_result = result
        st.session_state.query_history.append(result)
        
        st.success("🎉 Streaming complete!")
        
    except Exception as e:
        st.error(f"Streaming failed: {str(e)}")


if __name__ == "__main__":
    main() 
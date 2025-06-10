"""Modern Streamlit interface for LogDetective workflow system."""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import json
import time
from typing import Dict, Any

from logdetective_workflow import log_detective_workflow
from config import settings

# Page configuration
st.set_page_config(
    page_title="LogDetective - Workflow Edition",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for modern UI
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        color: white;
        text-align: center;
    }
    
    .workflow-status {
        background: #f8f9fa;
        border: 1px solid #e9ecef;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
    }
    
    .node-success {
        background: #d4edda;
        border-color: #c3e6cb;
        color: #155724;
    }
    
    .node-error {
        background: #f8d7da;
        border-color: #f5c6cb;
        color: #721c24;
    }
    
    .node-running {
        background: #d1ecf1;
        border-color: #bee5eb;
        color: #0c5460;
    }
    
    .metrics-container {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin: 1rem 0;
    }
    
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: 500;
    }
    
    .conversation-history {
        background: #f8f9fa;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
        max-height: 400px;
        overflow-y: auto;
    }
</style>
""", unsafe_allow_html=True)


def initialize_session_state():
    """Initialize Streamlit session state."""
    if 'conversation_history' not in st.session_state:
        st.session_state.conversation_history = []
    if 'current_execution' not in st.session_state:
        st.session_state.current_execution = None
    if 'workflow_info' not in st.session_state:
        st.session_state.workflow_info = log_detective_workflow.get_workflow_info()
    if 'system_status' not in st.session_state:
        st.session_state.system_status = {}


def render_header():
    """Render the main header."""
    st.title("🔍 LogDetective - Workflow Edition")
    st.markdown("*Sophisticated LangGraph-powered Splunk log analysis with fault tolerance*")


def render_sidebar():
    """Render the sidebar with system information."""
    st.sidebar.title("🎛️ System Status")
    
    # Workflow information
    with st.sidebar.expander("📊 Workflow Info", expanded=True):
        workflow_info = st.session_state.workflow_info
        st.write(f"**Nodes:** {len(workflow_info['nodes'])}")
        st.write(f"**Max Retries:** {workflow_info['fault_tolerance']['max_retries_per_node']}")
        st.write(f"**Recovery Attempts:** {workflow_info['fault_tolerance']['max_recovery_attempts']}")
        
        st.write("**Capabilities:**")
        for capability in workflow_info['capabilities']:
            st.write(f"• {capability}")
    
    # System health check
    with st.sidebar.expander("🔧 System Health", expanded=True):
        if st.button("🔄 Check Connection"):
            with st.spinner("Testing connections..."):
                try:
                    from splunk_tools import splunk_connector
                    splunk_status = splunk_connector.test_connection()
                    st.success("✅ Splunk Connected" if splunk_status else "❌ Splunk Disconnected")
                    
                    # Test knowledge store
                    from knowledge_store import knowledge_store
                    docs = knowledge_store.search("test", k=1)
                    st.success(f"✅ Knowledge Store ({len(docs)} docs available)")
                    
                except Exception as e:
                    st.error(f"❌ System Error: {str(e)}")
    
    # Configuration
    with st.sidebar.expander("⚙️ Configuration"):
        st.write(f"**AWS Region:** {settings.aws_default_region}")
        st.write(f"**Bedrock Model:** {settings.bedrock_model_id}")
        st.write(f"**Splunk Index:** 104118")
        st.write(f"**Max Results:** 100")
    
    # Conversation history
    with st.sidebar.expander("💬 Conversation History"):
        if st.session_state.conversation_history:
            for i, turn in enumerate(st.session_state.conversation_history[-5:]):  # Last 5
                with st.container():
                    st.write(f"**Q{i+1}:** {turn['user_query'][:50]}...")
                    if turn.get('success'):
                        st.success(f"✅ {turn.get('execution_time', 0):.1f}s")
                    else:
                        st.error("❌ Failed")
        else:
            st.info("No conversation history yet")


def render_query_interface():
    """Render the main query interface."""
    st.subheader("💭 Query Interface")
    
    # Sample queries
    sample_queries = [
        "Show me the top 10 hosts by event count",
        "Find all error events in the last hour",
        "What are the most common log levels?",
        "Show network traffic patterns by destination port",
        "Find authentication failures by user",
        "Show disk usage alerts over time"
    ]
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        user_query = st.text_area(
            "Enter your log analysis query:",
            placeholder="e.g., Show me all error events in the last 24 hours",
            height=100
        )
    
    with col2:
        st.write("**Sample Queries:**")
        for query in sample_queries:
            if st.button(query, key=f"sample_{hash(query)}"):
                user_query = query
                st.experimental_rerun()
    
    # Execution options
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        execution_mode = st.selectbox(
            "Execution Mode:",
            ["Standard", "Streaming", "Debug"],
            help="Standard: Normal execution, Streaming: Real-time updates, Debug: Detailed logging"
        )
    
    with col2:
        include_visualization = st.checkbox("Include Charts", value=True)
    
    with col3:
        max_results = st.number_input("Max Results", min_value=10, max_value=1000, value=100)
    
    return user_query, execution_mode, include_visualization, max_results


def execute_workflow(user_query: str, execution_mode: str):
    """Execute the workflow and display results."""
    if not user_query.strip():
        st.warning("Please enter a query")
        return
    
    # Prepare conversation history
    history = [
        {
            "role": "user",
            "content": turn["user_query"]
        }
        for turn in st.session_state.conversation_history[-5:]  # Last 5 turns
    ]
    
    if execution_mode == "Streaming":
        execute_streaming_workflow(user_query, history)
    else:
        execute_standard_workflow(user_query, history, execution_mode == "Debug")


def execute_standard_workflow(user_query: str, history: list, debug: bool = False):
    """Execute standard workflow."""
    start_time = time.time()
    
    # Create progress containers
    progress_container = st.container()
    results_container = st.container()
    
    with progress_container:
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        status_text.text("🚀 Initializing workflow...")
        progress_bar.progress(10)
    
    try:
        # Execute workflow
        with st.spinner("Processing your query..."):
            result = log_detective_workflow.process_query(user_query, history)
        
        execution_time = time.time() - start_time
        progress_bar.progress(100)
        status_text.text(f"✅ Completed in {execution_time:.2f}s")
        
        # Display results
        with results_container:
            display_workflow_results(result, debug)
        
        # Add to conversation history
        result['execution_time'] = execution_time
        result['timestamp'] = datetime.now().isoformat()
        st.session_state.conversation_history.append(result)
        
    except Exception as e:
        progress_bar.progress(100)
        status_text.text("❌ Workflow failed")
        st.error(f"Workflow execution failed: {str(e)}")


def execute_streaming_workflow(user_query: str, history: list):
    """Execute streaming workflow with real-time updates."""
    st.subheader("🔄 Live Workflow Execution")
    
    # Create containers for streaming updates
    progress_container = st.container()
    nodes_container = st.container()
    results_container = st.container()
    
    with progress_container:
        progress_bar = st.progress(0)
        status_text = st.empty()
    
    node_statuses = {}
    total_nodes = len(st.session_state.workflow_info['nodes'])
    
    try:
        # Stream workflow execution
        for i, chunk in enumerate(log_detective_workflow.stream_query(user_query, history)):
            node_name = chunk.get("node", "unknown")
            
            # Update progress
            progress = min(100, (i + 1) * 100 // total_nodes)
            progress_bar.progress(progress)
            status_text.text(f"🔄 Executing: {node_name}")
            
            # Update node status
            node_statuses[node_name] = {
                "status": "running" if "error" not in chunk else "error",
                "timestamp": chunk.get("timestamp", ""),
                "error": chunk.get("error")
            }
            
            # Display node statuses
            with nodes_container:
                display_node_statuses(node_statuses)
            
            time.sleep(0.1)  # Brief pause for visual effect
        
        status_text.text("✅ Workflow completed")
        
        # Execute final workflow to get complete results
        result = log_detective_workflow.process_query(user_query, history)
        
        with results_container:
            display_workflow_results(result, False)
        
        # Add to conversation history
        result['timestamp'] = datetime.now().isoformat()
        st.session_state.conversation_history.append(result)
        
    except Exception as e:
        status_text.text("❌ Streaming failed")
        st.error(f"Streaming execution failed: {str(e)}")


def display_node_statuses(node_statuses: Dict[str, Any]):
    """Display current node execution statuses."""
    st.write("**Node Execution Status:**")
    
    cols = st.columns(3)
    for i, (node_name, status) in enumerate(node_statuses.items()):
        col_idx = i % 3
        
        with cols[col_idx]:
            status_class = f"node-{status['status']}"
            
            if status['status'] == 'running':
                icon = "🔄"
            elif status['status'] == 'error':
                icon = "❌"
            else:
                icon = "✅"
            
            st.markdown(f"""
            <div class="workflow-status {status_class}">
                <strong>{icon} {node_name}</strong><br>
                <small>{status['timestamp']}</small>
            </div>
            """, unsafe_allow_html=True)


def display_workflow_results(result: Dict[str, Any], debug: bool = False):
    """Display comprehensive workflow results."""
    if not result.get('success'):
        st.error(f"❌ Query failed: {result.get('error', 'Unknown error')}")
        return
    
    # Main response
    st.subheader("📝 Analysis Results")
    st.write(result['final_response'])
    
    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Execution Time",
            f"{result.get('total_execution_time', 0):.2f}s",
            help="Total workflow execution time"
        )
    
    with col2:
        st.metric(
            "Error Count",
            result.get('error_count', 0),
            help="Number of errors encountered"
        )
    
    with col3:
        st.metric(
            "Splunk Status",
            "Connected" if result.get('splunk_connection_status') else "Disconnected",
            help="Splunk connection status"
        )
    
    with col4:
        st.metric(
            "Nodes Executed",
            len(result.get('execution_trace', [])),
            help="Number of workflow nodes executed"
        )
    
    # SPL Query
    if result.get('spl_query'):
        st.subheader("🔍 Generated SPL Query")
        st.code(result['spl_query'], language='sql')
    
    # Data Results
    data_results = result.get('data_results')
    if data_results and data_results.get('success'):
        display_data_results(data_results)
    
    # Visualization
    viz_config = result.get('visualization_config')
    if viz_config:
        display_visualization(viz_config)
    
    # Debug information
    if debug:
        display_debug_info(result)


def display_data_results(data_results: Dict[str, Any]):
    """Display query data results."""
    st.subheader("📊 Query Results")
    
    results = data_results.get('results', [])
    if not results:
        st.info("No data returned from the query")
        return
    
    # Convert to DataFrame
    df = pd.DataFrame(results)
    
    # Display summary
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Total Results:** {len(results)}")
        st.write(f"**Fields:** {', '.join(df.columns.tolist())}")
    
    with col2:
        stats = data_results.get('stats', {})
        st.write(f"**Events Scanned:** {stats.get('scan_count', 0):,}")
        st.write(f"**Query Runtime:** {stats.get('run_duration', 0):.2f}s")
    
    # Display data table
    st.dataframe(df, use_container_width=True)
    
    # Download option
    csv = df.to_csv(index=False)
    st.download_button(
        label="📥 Download CSV",
        data=csv,
        file_name=f"logdetective_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv"
    )


def display_visualization(viz_config: Dict[str, Any]):
    """Display generated visualization."""
    st.subheader("📈 Data Visualization")
    
    try:
        chart_config = viz_config.get('chart_config', {})
        chart_type = chart_config.get('chart_type', 'bar')
        
        if chart_type and chart_config.get('data'):
            # Create plotly figure from config
            fig = create_plotly_from_config(chart_config)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No visualization data available")
            
    except Exception as e:
        st.error(f"Visualization error: {str(e)}")


def create_plotly_from_config(chart_config: Dict[str, Any]) -> go.Figure:
    """Create Plotly figure from chart configuration."""
    chart_type = chart_config.get('chart_type', 'bar')
    data = chart_config.get('data', [])
    title = chart_config.get('title', 'Chart')
    
    df = pd.DataFrame(data)
    
    if chart_type == 'bar':
        fig = px.bar(df, x=df.columns[0], y=df.columns[1], title=title)
    elif chart_type == 'line':
        fig = px.line(df, x=df.columns[0], y=df.columns[1], title=title)
    elif chart_type == 'pie':
        fig = px.pie(df, names=df.columns[0], values=df.columns[1], title=title)
    else:
        # Default to scatter
        fig = px.scatter(df, x=df.columns[0], y=df.columns[1], title=title)
    
    return fig


def display_debug_info(result: Dict[str, Any]):
    """Display debug information."""
    st.subheader("🐛 Debug Information")
    
    with st.expander("Execution Trace"):
        trace = result.get('execution_trace', [])
        st.write(f"Nodes executed: {trace}")
    
    with st.expander("Full Result Object"):
        st.json(result)


def main():
    """Main application function."""
    initialize_session_state()
    render_header()
    render_sidebar()
    
    # Main interface
    user_query, execution_mode, include_viz, max_results = render_query_interface()
    
    # Execute button
    if st.button("🚀 Execute Query", type="primary"):
        execute_workflow(user_query, execution_mode)
    
    # Display recent results
    if st.session_state.conversation_history:
        st.subheader("📚 Recent Analysis")
        
        # Show last result
        latest_result = st.session_state.conversation_history[-1]
        with st.expander(f"Latest: {latest_result['user_query'][:50]}...", expanded=True):
            display_workflow_results(latest_result, False)


if __name__ == "__main__":
    main() 
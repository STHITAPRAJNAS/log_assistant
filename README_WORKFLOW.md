# LogDetective - Workflow Edition 🔍

**Sophisticated LangGraph-powered Splunk log analysis with fault tolerance**

LogDetective Workflow Edition is a next-generation AI-powered log analysis assistant that transforms natural language queries into actionable Splunk insights using a sophisticated LangGraph workflow architecture.

## 🌟 Key Features

### 🧠 Advanced Workflow Architecture
- **LangGraph Workflow**: Sophisticated node-based execution with intelligent routing
- **Fault Tolerance**: Automatic retry logic with exponential backoff
- **Error Recovery**: Multi-level error handling and recovery mechanisms
- **State Management**: Comprehensive conversation and execution state tracking

### 🤖 AI-Powered Analysis
- **Natural Language Processing**: Convert plain English to SPL queries
- **RAG-Enhanced Generation**: Leverages Splunk documentation knowledge base  
- **AWS Bedrock Integration**: Claude Sonnet 3.5 for intelligent query generation
- **Context-Aware**: Maintains conversation history for better results

### 📊 Production-Ready Features
- **Real-time Execution**: Live workflow monitoring with streaming updates
- **Intelligent Visualization**: Automatic chart generation based on data characteristics
- **Comprehensive Logging**: Detailed execution traces and performance metrics
- **Robust Error Handling**: Graceful degradation and informative error messages

## 🏗️ Architecture Overview

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Streamlit UI  │    │  LangGraph       │    │   Splunk SDK    │
│                 │────│  Workflow        │────│                 │
│  • Query Input  │    │                  │    │  • Query Exec   │
│  • Visualization│    │  • RAG Retrieval │    │  • Field Discovery│
│  • History      │    │  • SPL Generation│    │  • Connection    │
└─────────────────┘    │  • Analysis      │    └─────────────────┘
                       │  • Visualization │
                       │  • Error Recovery│
                       └──────────────────┘
                                │
                       ┌──────────────────┐
                       │   FAISS Vector   │
                       │   Knowledge Store│
                       │                  │
                       │  • Splunk Docs   │
                       │  • SPL Examples  │
                       │  • Best Practices│
                       └──────────────────┘
```

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- AWS Account with Bedrock access
- Splunk instance with API access
- Required credentials configured

### 1. Installation

```bash
# Clone the repository
git clone <repository-url>
cd log_assistant

# Switch to workflow branch
git checkout workflow-redesign

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

Create a `config.py` file:

```python
class Settings:
    # AWS Configuration
    aws_default_region = "us-east-1"
    bedrock_model_id = "anthropic.claude-3-5-sonnet-20241022-v2:0"
    
    # Splunk Configuration
    splunk_host = "your-splunk-host"
    splunk_port = 8089
    splunk_username = "your-username"
    splunk_password = "your-password"
    
    # Target Index
    splunk_index = "104118"

settings = Settings()
```

### 3. Launch Application

```bash
# Start with comprehensive system checks
python start_workflow.py

# Or run directly
streamlit run streamlit_app_workflow.py
```

## 🔧 Workflow Components

### Core Workflow Nodes

1. **Initialize Node** (`initialize`)
   - Sets up conversation context
   - Tests system connections
   - Initializes workflow state

2. **RAG Retrieval Node** (`rag_retrieval`) 
   - Searches knowledge base for relevant documentation
   - Enhances queries with contextual information
   - Manages conversation history

3. **SPL Generation Node** (`spl_generation`)
   - Converts natural language to SPL queries
   - Uses RAG context for accurate generation
   - Provides query explanations and complexity estimates

4. **Query Execution Node** (`query_execution`)
   - Executes SPL against Splunk index 104118
   - Handles connection management and retries
   - Captures execution statistics

5. **Result Analysis Node** (`result_analysis`)
   - Analyzes query results for insights
   - Identifies patterns and anomalies
   - Generates business-relevant summaries

6. **Visualization Node** (`visualization`)
   - Creates appropriate charts based on data
   - Supports bar, line, pie, and heatmap charts
   - Auto-suggests visualization types

7. **Error Recovery Node** (`error_recovery`)
   - Handles workflow failures gracefully
   - Attempts automatic recovery when possible
   - Provides informative error messages

### Fault Tolerance Features

- **Node-level Retries**: Each node can retry up to 3 times with exponential backoff
- **Circuit Breaker**: Prevents cascade failures 
- **Recovery Strategies**: Multiple recovery approaches for different error types
- **State Preservation**: Maintains workflow state across failures

## 💭 Usage Examples

### Basic Log Analysis
```
Query: "Show me the top 10 hosts by event count"
Generated SPL: search index=104118 | stats count by host | sort -count | head 10
```

### Time-based Analysis  
```
Query: "Find all error events in the last hour"
Generated SPL: search index=104118 earliest=-1h level=ERROR | head 100
```

### Advanced Aggregations
```
Query: "What are the most common log levels?"
Generated SPL: search index=104118 | stats count by level | sort -count
```

## 📊 Key Benefits

### vs Traditional Splunk
- **🎯 Natural Language**: No SPL knowledge required
- **🤖 AI-Enhanced**: Intelligent query generation and analysis
- **📚 Context-Aware**: Learns from conversation history
- **🔄 Fault Tolerant**: Handles errors gracefully

### vs Multi-Agent Approach
- **⚡ Performance**: Single workflow vs. multiple agent coordination
- **🎯 Focused**: Purpose-built nodes vs. general agents
- **🔧 Maintainable**: Clear workflow graph vs. complex agent interactions
- **📈 Scalable**: Efficient state management and execution

## 🛠️ Development

### Project Structure
```
log_assistant/
├── workflow_state.py          # State management classes
├── workflow_nodes.py          # Fault-tolerant workflow nodes  
├── logdetective_workflow.py   # Main workflow orchestrator
├── streamlit_app_workflow.py  # Modern Streamlit interface
├── start_workflow.py          # Startup and health checks
├── config.py                  # Configuration settings
├── knowledge_store.py         # FAISS vector store
├── splunk_tools.py           # Splunk SDK wrapper
├── visualization_tools.py     # Chart generation
└── requirements.txt          # Dependencies
```

### Adding Custom Nodes

```python
from workflow_nodes import fault_tolerant_node
from workflow_state import NodeType, LogDetectiveState

@fault_tolerant_node(NodeType.CUSTOM_NODE, max_retries=2)
def custom_analysis_node(state: LogDetectiveState) -> LogDetectiveState:
    """Custom analysis logic."""
    # Your custom logic here
    return state
```

### Extending Workflow

```python
# Add to logdetective_workflow.py
graph.add_node("custom_analysis", custom_analysis_node)
graph.add_conditional_edges(
    "result_analysis",
    routing_node,
    {
        "custom_analysis": "custom_analysis",
        # ... other routes
    }
)
```

## 🔍 Monitoring & Debugging

### Execution Traces
- Detailed node execution logs
- Performance metrics per node
- Error stack traces and recovery attempts

### System Health Checks
- Splunk connection status
- Knowledge store availability  
- AWS Bedrock API access
- Workflow node status

### Debug Mode
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
python start_workflow.py
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch from `workflow-redesign`
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📋 Requirements

### System Requirements
- Python 3.8+  
- 4GB+ RAM (for FAISS vector store)
- Network access to Splunk and AWS

### Dependencies
- `langgraph>=0.2.0` - Workflow orchestration
- `langchain-aws>=0.2.0` - AWS Bedrock integration
- `splunk-sdk>=1.7.0` - Splunk API access
- `streamlit>=1.28.0` - Web interface
- `faiss-cpu>=1.7.0` - Vector similarity search
- `plotly>=5.0.0` - Interactive visualizations

## 📄 License

MIT License - See [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Issues**: GitHub Issues for bug reports
- **Discussions**: GitHub Discussions for questions
- **Documentation**: See `/docs` folder for detailed guides

---

**LogDetective Workflow Edition** - Transform your log analysis with AI-powered intelligence and fault-tolerant execution! 🚀 
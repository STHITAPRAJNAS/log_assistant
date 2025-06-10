# 🔍 LogDetective - AI-Powered Splunk Log Analysis Assistant

LogDetective is an intelligent multi-agent system built with LangGraph that acts as your expert Splunk log analysis assistant. It provides natural language querying, smart data analysis, and automatic visualization generation for Splunk index 104118.

## ✨ Features

- **🤖 Multi-Agent Architecture**: Supervisor pattern with specialized agents for querying, analysis, and visualization
- **🔍 Smart Splunk Querying**: Natural language to SPL conversion with index 104118 focus
- **📊 Automatic Visualizations**: Intelligent chart generation based on data characteristics  
- **🧠 Knowledge Base**: FAISS vector store with Splunk documentation for syntax help
- **🎨 Production-Grade UI**: Beautiful Streamlit interface with real-time connection monitoring
- **☁️ AWS Bedrock Integration**: Powered by Claude Sonnet for advanced reasoning
- **⚡ Real-time Analysis**: Live connection testing and field discovery

## 🏗️ Architecture

### Multi-Agent System
- **Supervisor Agent**: Orchestrates tasks and delegates to specialized agents
- **Query Agent**: Handles SPL query construction and data retrieval
- **Analysis Agent**: Performs data analysis and pattern recognition
- **Visualization Agent**: Creates charts and visual representations

### Key Components
- **Splunk SDK Integration**: Direct connection to Splunk for data retrieval
- **FAISS Knowledge Store**: Vector database with Splunk documentation
- **LangGraph Framework**: Multi-agent coordination and workflow management
- **AWS Bedrock**: Claude Sonnet model for natural language processing

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Access to Splunk instance with index 104118
- AWS account with Bedrock access
- Required credentials (see Configuration section)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd log_assistant
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**
   Create a `.env` file with your credentials:
   ```env
   # Splunk Configuration
   SPLUNK_HOST=your-splunk-host.com
   SPLUNK_PORT=8089
   SPLUNK_USERNAME=your-username
   SPLUNK_PASSWORD=your-password
   SPLUNK_SCHEME=https
   SPLUNK_INDEX=104118
   
   # AWS Bedrock Configuration
   AWS_ACCESS_KEY_ID=your-aws-access-key
   AWS_SECRET_ACCESS_KEY=your-aws-secret-key
   AWS_DEFAULT_REGION=us-east-1
   BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0
   ```

4. **Run the application**
   ```bash
   streamlit run app.py
   ```

5. **Access the interface**
   Open your browser to `http://localhost:8501`

## 🎯 Usage Examples

### Basic Queries
```
"Show me the latest 100 log entries"
"Find all error logs from the last hour"
"Count events by host"
```

### Advanced Analysis
```
"Analyze log patterns and identify anomalies"
"Show me the top 10 hosts by log volume with a chart"
"Create a time series visualization of log activity"
```

### Aggregations
```
"Group logs by sourcetype and show counts"
"Calculate average response times by host"
"Show unique IP addresses in the logs"
```

## 📊 Visualization Capabilities

LogDetective automatically suggests and creates appropriate visualizations:

- **Time Series Charts**: For trending data over time
- **Bar Charts**: For categorical data comparison
- **Pie Charts**: For distribution analysis  
- **Heatmaps**: For correlation analysis
- **Histograms**: For data distribution

## 🔧 Configuration

### Splunk Settings
Configure your Splunk connection in the `config.py` file or via environment variables:

```python
SPLUNK_HOST = "your-splunk-instance.com"
SPLUNK_PORT = 8089
SPLUNK_USERNAME = "your-username"
SPLUNK_PASSWORD = "your-password" 
SPLUNK_INDEX = "104118"
```

### AWS Bedrock Settings
Ensure your AWS credentials have access to Bedrock:

```python
AWS_DEFAULT_REGION = "us-east-1"
BEDROCK_MODEL_ID = "anthropic.claude-3-5-sonnet-20241022-v2:0"
```

### Application Settings
Customize the application behavior:

```python
MAX_SEARCH_RESULTS = 1000
CHART_THEME = "plotly_white"
APP_TITLE = "LogDetective - Splunk Assistant"
```

## 🛠️ Development

### Project Structure
```
log_assistant/
├── agents.py              # Multi-agent system implementation
├── app.py                 # Main Streamlit application
├── config.py              # Configuration management
├── splunk_tools.py        # Splunk SDK tools and utilities
├── knowledge_store.py     # FAISS knowledge base
├── visualization_tools.py # Chart generation utilities
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

### Adding New Agents
To add a new specialized agent:

1. Create the agent in `agents.py`:
```python
new_agent = create_react_agent(
    model=self.llm,
    tools=[your_tools],
    prompt="Your agent prompt",
    name="new_agent"
)
```

2. Add to the supervisor's agent list
3. Update the supervisor prompt to include the new agent

### Adding New Tools
Tools are LangChain compatible functions decorated with `@tool`:

```python
@tool
def your_custom_tool(param: str) -> str:
    """Tool description for the LLM."""
    # Your implementation
    return result
```

## 🔍 Troubleshooting

### Common Issues

**Connection Errors**
- Verify Splunk credentials and network connectivity
- Check if index 104118 exists and is accessible
- Ensure proper SSL/TLS configuration

**AWS Bedrock Errors**
- Verify AWS credentials and region settings
- Check Bedrock model availability in your region
- Ensure proper IAM permissions for Bedrock access

**Performance Issues**
- Optimize Splunk queries with appropriate time ranges
- Limit result sets using `| head` command
- Monitor AWS Bedrock usage and rate limits

### Debug Mode
Enable debug logging by setting:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 📚 Documentation

### Splunk Knowledge Base
The system includes a built-in knowledge base with:
- SPL command documentation
- Query optimization tips
- Field extraction examples
- Best practices

### API Reference
Key classes and functions:

- `LogDetectiveAgents`: Main multi-agent system
- `SplunkConnector`: Splunk SDK wrapper
- `SplunkKnowledgeStore`: FAISS-based knowledge management
- `ChartGenerator`: Visualization utilities

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

### Code Style
- Follow PEP 8 guidelines
- Use type hints where possible
- Include docstrings for all functions
- Maintain consistent error handling

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- [LangGraph](https://langchain-ai.github.io/langgraph/) for the multi-agent framework
- [Splunk SDK](https://github.com/splunk/splunk-sdk-python) for Splunk integration
- [AWS Bedrock](https://aws.amazon.com/bedrock/) for LLM capabilities
- [Streamlit](https://streamlit.io/) for the web interface
- [FAISS](https://github.com/facebookresearch/faiss) for vector search

## 📞 Support

For support and questions:
- Create an issue in the GitHub repository
- Check the troubleshooting section above
- Review the Splunk and AWS Bedrock documentation

---

**LogDetective v1.0** - Making log analysis intelligent and accessible! 🚀 
"""Multi-agent system for LogDetective using LangGraph supervisor pattern."""

from langchain_aws import ChatBedrock
from langgraph.prebuilt import create_react_agent
from langgraph_supervisor import create_supervisor
from langchain.schema import HumanMessage, SystemMessage
from typing import List, Dict, Any, Optional
import json

# Import tools
from splunk_tools import (
    execute_spl_query, 
    get_splunk_index_fields, 
    test_splunk_connection
)
from knowledge_store import search_splunk_documentation, add_splunk_knowledge
from visualization_tools import create_visualization, suggest_visualization
from config import settings


class LogDetectiveAgents:
    """LogDetective multi-agent system."""
    
    def __init__(self):
        self.llm = self._initialize_llm()
        self.agents = self._create_agents()
        self.supervisor = self._create_supervisor()
    
    def _initialize_llm(self) -> ChatBedrock:
        """Initialize the Bedrock LLM."""
        return ChatBedrock(
            model_id=settings.bedrock_model_id,
            region_name=settings.aws_default_region,
            model_kwargs={
                "temperature": 0.1,
                "top_p": 0.9,
                "max_tokens": 4000
            }
        )
    
    def _create_agents(self) -> Dict[str, Any]:
        """Create individual agents."""
        
        # Query Agent - Handles SPL query construction and execution
        query_agent = create_react_agent(
            model=self.llm,
            tools=[
                execute_spl_query,
                get_splunk_index_fields,
                test_splunk_connection,
                search_splunk_documentation
            ],
            prompt="""You are a Splunk SPL Expert specializing in index 104118. Your primary role is to construct and execute proper SPL queries.

CORE RESPONSIBILITIES:
1. **SPL Query Construction**: Build complete, executable SPL queries with proper syntax
2. **Built-in Functions**: Use Splunk's built-in aggregation functions (stats, timechart, chart, etc.)
3. **Data Retrieval**: Execute SPL queries and return structured results
4. **Field Knowledge**: Understand available fields in index 104118

SPL QUERY REQUIREMENTS:
- ALL queries must start with "search index=104118"
- Use proper SPL commands: search, stats, timechart, chart, eval, where, sort, etc.
- Include appropriate aggregations: count, sum, avg, max, min, dc, values, list
- Add time ranges when relevant: earliest=-1h, latest=now
- Limit results appropriately: | head 100, | tail 50
- Sort results meaningfully: | sort -_time, | sort -count

EXAMPLE QUERIES:
- Basic search: "search index=104118 error | head 20"
- Aggregation: "search index=104118 | stats count by host | sort -count"
- Time chart: "search index=104118 | timechart span=1h count"
- Complex: "search index=104118 earliest=-24h | stats count, dc(host) as unique_hosts by sourcetype | sort -count"

Always use get_splunk_index_fields to understand available fields before constructing queries.
Execute complete, production-ready SPL queries using execute_spl_query tool.""",
            name="query_agent"
        )
        
        # Analysis Agent - Analyzes data and provides insights
        analysis_agent = create_react_agent(
            model=self.llm,
            tools=[
                search_splunk_documentation
            ],
            prompt="""You are a Log Analysis Expert specializing in interpreting Splunk query results. Your responsibilities:

1. **Data Interpretation**: Analyze JSON results from SPL queries
2. **Pattern Recognition**: Identify trends, anomalies, and patterns in log data
3. **Insight Generation**: Provide meaningful, actionable insights
4. **Business Translation**: Explain technical findings in business-friendly language
5. **Recommendations**: Suggest next steps or areas of concern

KEY ANALYSIS FOCUS:
- Security patterns and potential threats
- Performance issues and bottlenecks
- Error trends and failure patterns
- Capacity and resource utilization
- User behavior and access patterns
- System health indicators

ANALYSIS APPROACH:
- Examine data for statistical significance
- Look for outliers and unusual patterns
- Consider temporal trends and seasonality
- Identify correlations between different metrics
- Provide context for the findings
- Suggest follow-up investigations

You receive JSON data from executed SPL queries and provide comprehensive analysis and insights.
Focus on actionable intelligence rather than just data description.""",
            name="analysis_agent"
        )
        
        # Visualization Agent - Creates charts and visual representations
        visualization_agent = create_react_agent(
            model=self.llm,
            tools=[
                create_visualization,
                suggest_visualization
            ],
            prompt="""You are a Data Visualization Expert. Your responsibilities:

1. **Chart Creation**: Create appropriate visualizations for log data
2. **Visual Analysis**: Suggest best visualization types for different data
3. **Dashboard Design**: Design effective visual representations
4. **User Experience**: Ensure visualizations are clear and actionable

Key Guidelines:
- Choose appropriate chart types based on data characteristics
- Create clear, readable visualizations
- Provide suggestions for different visualization options
- Focus on highlighting key insights through visuals
- Consider time series data for trending analysis

You work with analyzed data to create meaningful visual representations.""",
            name="visualization_agent"
        )
        
        return {
            "query_agent": query_agent,
            "analysis_agent": analysis_agent,
            "visualization_agent": visualization_agent
        }
    
    def _create_supervisor(self):
        """Create the supervisor agent."""
        return create_supervisor(
            agents=list(self.agents.values()),
            model=self.llm,
            prompt="""You are LogDetective, an AI-powered Splunk Log Analysis Supervisor. You coordinate specialized agents to provide comprehensive log analysis for index 104118.

YOUR TEAM:
1. **Query Agent**: SPL expert who constructs and executes proper Splunk queries
2. **Analysis Agent**: Data analysis specialist who interprets results and provides insights  
3. **Visualization Agent**: Creates charts and visual representations of data

WORKFLOW ORCHESTRATION:
1. **Simple Queries**: Query Agent executes SPL → Provide summary with data table
2. **Analysis Requests**: Query Agent → Analysis Agent → Comprehensive insights + recommendations
3. **Visualization Needs**: Query Agent → Analysis Agent → Visualization Agent → Charts + analysis
4. **Complex Investigations**: Multiple iterations with different agents as needed

RESPONSE REQUIREMENTS:
- Always provide a clear textual summary responding to the user's question
- Include relevant data tables when appropriate  
- Add visualizations when they enhance understanding
- Explain technical findings in accessible language
- Provide actionable insights and recommendations

QUALITY STANDARDS:
- Ensure SPL queries are syntactically correct and optimized
- Focus on answering the user's specific question
- Provide context and business relevance for findings
- Suggest follow-up questions or investigations when relevant
- Maintain professional, helpful tone

Your goal is to make Splunk log analysis accessible and actionable for users of all technical levels."""
        ).compile()
    
    def process_request(self, user_query: str) -> Dict[str, Any]:
        """Process a user request through the multi-agent system."""
        try:
            # Stream the supervisor's response
            response_parts = []
            
            for chunk in self.supervisor.stream({
                "messages": [
                    {
                        "role": "user", 
                        "content": user_query
                    }
                ]
            }):
                response_parts.append(chunk)
            
            # Extract the final response
            final_response = response_parts[-1] if response_parts else {}
            
            return {
                "success": True,
                "response": final_response,
                "query": user_query
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "query": user_query
            }
    
    def get_index_info(self) -> Dict[str, Any]:
        """Get information about the Splunk index."""
        try:
            # Test connection
            connection_result = test_splunk_connection()
            connection_data = json.loads(connection_result)
            
            # Get field information
            fields_result = get_splunk_index_fields()
            fields_data = json.loads(fields_result)
            
            return {
                "connection": connection_data,
                "fields": fields_data,
                "index": settings.splunk_index
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "connection": {"connected": False},
                "fields": {"available_fields": []},
                "index": settings.splunk_index
            }


# Global LogDetective instance
log_detective = LogDetectiveAgents() 
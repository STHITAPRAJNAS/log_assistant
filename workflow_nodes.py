"""Simplified workflow nodes using LangGraph best practices."""

import json
from typing import Dict, Any

from langchain_aws import ChatBedrock
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.messages import HumanMessage

from workflow_state import LogDetectiveState
from knowledge_store import knowledge_store
from splunk_tools import splunk_connector
from visualization_tools import create_visualization, suggest_visualization
from config import settings


# Initialize LLM globally
llm = ChatBedrock(
    model_id=settings.bedrock_model_id,
    region_name=settings.aws_default_region,
    model_kwargs={
        "temperature": 0.1,
        "top_p": 0.9,
        "max_tokens": 4000
    }
)


def initialize_system(state: LogDetectiveState) -> LogDetectiveState:
    """Initialize system and test connections."""
    # Add user message to conversation
    state["messages"].append(HumanMessage(content=state["user_query"]))
    
    # Test Splunk connection
    try:
        state["splunk_connected"] = splunk_connector.test_connection()
        if state["splunk_connected"]:
            state["available_fields"] = splunk_connector.get_index_fields()
    except Exception as e:
        state["error_message"] = f"Splunk connection failed: {str(e)}"
        state["splunk_connected"] = False
        state["available_fields"] = []
    
    return state


def retrieve_knowledge(state: LogDetectiveState) -> LogDetectiveState:
    """Retrieve relevant knowledge using RAG."""
    try:
        # Create enhanced query from user input and conversation history
        search_queries = [state["user_query"]]
        
        # Add context from recent messages
        recent_messages = state["messages"][-3:] if len(state["messages"]) > 1 else []
        for msg in recent_messages:
            if hasattr(msg, 'content') and msg.content != state["user_query"]:
                search_queries.append(msg.content)
        
        # Search knowledge base
        all_docs = []
        for query in search_queries:
            docs = knowledge_store.search(query, k=2)
            all_docs.extend(docs)
        
        # Remove duplicates and store
        unique_docs = []
        seen_content = set()
        for doc in all_docs:
            content = doc.get("content", "")
            if content and content not in seen_content:
                unique_docs.append(doc)
                seen_content.add(content)
        
        state["retrieved_docs"] = unique_docs[:3]  # Top 3 most relevant
        state["rag_query"] = state["user_query"]
        
    except Exception as e:
        state["error_message"] = f"Knowledge retrieval failed: {str(e)}"
        state["retrieved_docs"] = []
    
    return state


def generate_spl_query(state: LogDetectiveState) -> LogDetectiveState:
    """Generate SPL query using LLM."""
    try:
        # Build context for SPL generation
        context_parts = []
        
        # Add retrieved documentation
        if state["retrieved_docs"]:
            context_parts.append("RELEVANT SPLUNK DOCUMENTATION:")
            for doc in state["retrieved_docs"]:
                context_parts.append(f"- {doc.get('content', '')}")
        
        # Add available fields
        if state["available_fields"]:
            context_parts.append(f"\nAVAILABLE FIELDS IN INDEX 104118:")
            context_parts.append(", ".join(state["available_fields"]))
        
        # Create SPL generation prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert Splunk SPL query generator for index 104118.

Generate a complete, production-ready SPL query based on the user's request.

REQUIREMENTS:
1. ALL queries MUST start with "search index=104118"
2. Use proper SPL syntax: stats, timechart, eval, where, sort
3. Add time ranges when relevant: earliest=-1h, latest=now
4. Limit results: | head 100
5. Sort meaningfully: | sort -_time, | sort -count

RESPONSE FORMAT - Return valid JSON:
{{
    "spl_query": "complete SPL query",
    "explanation": "what the query does",
    "complexity": "simple|moderate|complex",
    "visualization_hint": "bar|pie|line|table|null"
}}

CONTEXT:
{context}"""),
            ("human", "Generate SPL query for: {user_query}")
        ])
        
        context_text = "\n".join(context_parts) if context_parts else "No additional context available."
        
        response = llm.invoke(prompt.format_messages(
            context=context_text,
            user_query=state["user_query"]
        ))
        
        # Parse JSON response with fallback
        try:
            parser = JsonOutputParser()
            result = parser.parse(response.content)
        except:
            # Simple fallback
            result = {
                "spl_query": f"search index=104118 {state['user_query']} | head 20",
                "explanation": "Basic search query",
                "complexity": "simple",
                "visualization_hint": "table"
            }
        
        state["spl_query"] = result.get("spl_query")
        state["spl_explanation"] = result.get("explanation")
        state["query_complexity"] = result.get("complexity")
        
    except Exception as e:
        state["error_message"] = f"SPL generation failed: {str(e)}"
        # Provide fallback query
        state["spl_query"] = f"search index=104118 | head 10"
        state["spl_explanation"] = "Fallback query due to generation error"
    
    return state


def execute_splunk_query(state: LogDetectiveState) -> LogDetectiveState:
    """Execute SPL query against Splunk."""
    if not state.get("spl_query"):
        state["error_message"] = "No SPL query to execute"
        return state
    
    try:
        if not state["splunk_connected"]:
            # Try to reconnect
            state["splunk_connected"] = splunk_connector.test_connection()
            if not state["splunk_connected"]:
                state["error_message"] = "Splunk connection unavailable"
                return state
        
        # Execute query
        df, stats = splunk_connector.execute_search(state["spl_query"])
        
        # Store results
        state["query_results"] = {
            "success": not df.empty,
            "data": df.to_dict('records') if not df.empty else [],
            "stats": stats,
            "fields": list(df.columns) if not df.empty else [],
            "count": len(df),
            "query": state["spl_query"]
        }
        
    except Exception as e:
        state["error_message"] = f"Query execution failed: {str(e)}"
        state["query_results"] = {
            "success": False,
            "data": [],
            "error": str(e)
        }
    
    return state


def analyze_results(state: LogDetectiveState) -> LogDetectiveState:
    """Analyze query results and generate insights."""
    if not state.get("query_results") or not state["query_results"].get("success"):
        state["analysis_response"] = "No valid results to analyze. Please check your query or Splunk connection."
        return state
    
    try:
        results = state["query_results"]["data"]
        stats = state["query_results"]["stats"]
        
        # Create analysis prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a Splunk log analysis expert. Provide clear insights from the query results.

Your response should:
1. Summarize key findings
2. Identify patterns or anomalies
3. Answer the user's question directly
4. Be concise and actionable

Focus on business value and clear explanations."""),
            ("human", """Question: {user_query}

SPL Query: {spl_query}

Results Count: {count}
Events Scanned: {scan_count}

Sample Data (first 3 rows):
{sample_data}

Provide analysis and insights.""")
        ])
        
        sample_data = json.dumps(results[:3], indent=2, default=str) if results else "No data"
        
        response = llm.invoke(prompt.format_messages(
            user_query=state["user_query"],
            spl_query=state["spl_query"],
            count=len(results),
            scan_count=stats.get("scan_count", 0),
            sample_data=sample_data
        ))
        
        state["analysis_response"] = response.content
        
    except Exception as e:
        state["analysis_response"] = f"Analysis failed: {str(e)}. Raw results available in data view."
    
    return state


def create_visualization(state: LogDetectiveState) -> LogDetectiveState:
    """Create visualization if appropriate."""
    if not state.get("query_results") or not state["query_results"].get("success"):
        return state
    
    results = state["query_results"]["data"]
    if len(results) < 2:
        return state  # Need at least 2 rows
    
    try:
        # Auto-suggest visualization
        suggestion_result = suggest_visualization(json.dumps(results))
        suggestions = json.loads(suggestion_result)
        
        if suggestions.get("suggestions"):
            chart_type = suggestions["suggestions"][0].get("chart_type")
            
            if chart_type and chart_type != "table":
                viz_result = create_visualization(
                    json.dumps(results),
                    chart_type,
                    title="Query Results Visualization"
                )
                
                viz_config = json.loads(viz_result)
                if "chart_config" in viz_config:
                    state["visualization_config"] = viz_config
    
    except Exception as e:
        # Visualization failure is not critical
        pass
    
    return state


def should_continue(state: LogDetectiveState) -> str:
    """Determine next step in workflow."""
    if state.get("error_message") and state["retry_count"] < 2:
        state["retry_count"] += 1
        return "retry"
    elif state.get("analysis_response"):
        return "end"
    else:
        return "continue" 
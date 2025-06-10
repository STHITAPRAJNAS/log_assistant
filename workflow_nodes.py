"""Sophisticated fault-tolerant workflow nodes for LogDetective."""

import time
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import traceback
from functools import wraps

from langchain_aws import ChatBedrock
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from workflow_state import (
    LogDetectiveState, StateManager, QueryContext, RAGContext, SPLContext,
    ExecutionStatus, NodeType
)
from knowledge_store import knowledge_store
from splunk_tools import splunk_connector
from visualization_tools import create_visualization, suggest_visualization
from config import settings


def fault_tolerant_node(node_type: NodeType, max_retries: int = 3):
    """Decorator for fault-tolerant node execution."""
    def decorator(func):
        @wraps(func)
        def wrapper(state: LogDetectiveState) -> LogDetectiveState:
            node_name = func.__name__
            start_time = time.time()
            
            # Update state to indicate node is running
            state = StateManager.update_node_execution(
                state, node_name, node_type, ExecutionStatus.RUNNING
            )
            state["current_node"] = node_name
            
            retry_count = 0
            last_error = None
            
            while retry_count <= max_retries:
                try:
                    # Execute the node function
                    result = func(state)
                    execution_time = time.time() - start_time
                    
                    # Update state with success
                    state = StateManager.update_node_execution(
                        state, node_name, node_type, ExecutionStatus.SUCCESS,
                        result=result, execution_time=execution_time
                    )
                    
                    return result
                    
                except Exception as e:
                    last_error = str(e)
                    retry_count += 1
                    
                    if retry_count <= max_retries:
                        # Mark for retry
                        state = StateManager.update_node_execution(
                            state, node_name, node_type, ExecutionStatus.RETRY,
                            error_message=last_error
                        )
                        time.sleep(2 ** retry_count)  # Exponential backoff
                    else:
                        # Mark as failed
                        state = StateManager.update_node_execution(
                            state, node_name, node_type, ExecutionStatus.FAILED,
                            error_message=last_error, execution_time=time.time() - start_time
                        )
                        
                        state = StateManager.add_error(
                            state, "node_execution_failure", last_error, node_name
                        )
            
            return state
        return wrapper
    return decorator


class WorkflowNodes:
    """Collection of workflow nodes for LogDetective."""
    
    def __init__(self):
        self.llm = ChatBedrock(
            model_id=settings.bedrock_model_id,
            region_name=settings.aws_default_region,
            model_kwargs={
                "temperature": 0.1,
                "top_p": 0.9,
                "max_tokens": 4000
            }
        )
    
    @fault_tolerant_node(NodeType.RAG_RETRIEVAL)
    def rag_retrieval_node(self, state: LogDetectiveState) -> LogDetectiveState:
        """Retrieve relevant documentation using RAG."""
        if not state["current_turn"]:
            raise ValueError("No current turn in state")
        
        user_query = state["current_turn"].user_query
        
        # Get conversation context
        conversation_context = StateManager.get_conversation_context(state)
        
        # Create enhanced query for RAG
        context_queries = [user_query]
        
        # Add queries from recent conversation
        for turn in conversation_context[:3]:
            if not turn["is_current"] and turn.get("user_query"):
                context_queries.append(turn["user_query"])
        
        # Retrieve relevant documentation
        all_retrieved_docs = []
        
        for query in context_queries:
            docs = knowledge_store.search(query, k=3)
            all_retrieved_docs.extend(docs)
        
        # Remove duplicates
        unique_docs = []
        seen_content = set()
        
        for doc in all_retrieved_docs:
            content = doc.get("content", "")
            if content not in seen_content:
                unique_docs.append(doc)
                seen_content.add(content)
        
        # Sort by relevance score
        unique_docs.sort(key=lambda x: x.get("score", 0.0))
        
        # Create RAG context
        rag_context = RAGContext(
            query=user_query,
            retrieved_docs=unique_docs[:5],
            relevance_scores=[doc.get("score", 0.0) for doc in unique_docs[:5]]
        )
        
        state["rag_context"] = rag_context
        state["current_turn"].rag_context = rag_context
        
        return state
    
    @fault_tolerant_node(NodeType.SPL_GENERATION)
    def spl_generation_node(self, state: LogDetectiveState) -> LogDetectiveState:
        """Generate SPL query using LLM with RAG context."""
        if not state["current_turn"]:
            raise ValueError("No current turn in state")
        
        user_query = state["current_turn"].user_query
        rag_context = state.get("rag_context")
        available_fields = state.get("available_fields", [])
        
        # Build context for SPL generation
        context_parts = []
        
        # Add RAG documentation
        if rag_context and rag_context.retrieved_docs:
            context_parts.append("RELEVANT SPLUNK DOCUMENTATION:")
            for doc in rag_context.retrieved_docs:
                context_parts.append(f"- {doc.get('content', '')}")
        
        # Add available fields
        if available_fields:
            context_parts.append(f"\nAVAILABLE FIELDS IN INDEX 104118:")
            context_parts.append(", ".join(available_fields))
        
        # Create SPL generation prompt
        spl_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert Splunk SPL query generator for index 104118. 

Your task is to generate a complete, production-ready SPL query based on the user's natural language request.

CORE REQUIREMENTS:
1. ALL queries MUST start with "search index=104118"
2. Use proper SPL syntax and built-in functions
3. Include appropriate aggregations: stats, timechart, chart, eval, where, sort
4. Add time ranges when relevant: earliest=-1h, latest=now
5. Limit results: | head 100, | tail 50
6. Sort meaningfully: | sort -_time, | sort -count

RESPONSE FORMAT:
Return a JSON object with:
{{
    "spl_query": "complete SPL query",
    "explanation": "clear explanation of what the query does",
    "complexity": "simple|moderate|complex",
    "estimated_results": "description of expected results",
    "visualization_hint": "bar|pie|line|table|heatmap or null"
}}

CONTEXT:
{context}"""),
            ("human", "Generate SPL query for: {user_query}")
        ])
        
        # Generate SPL query
        context_text = "\n".join(context_parts) if context_parts else "No additional context available."
        
        messages = spl_prompt.format_messages(
            context=context_text,
            user_query=user_query
        )
        
        response = self.llm.invoke(messages)
        
        # Parse JSON response
        try:
            parser = JsonOutputParser()
            spl_result = parser.parse(response.content)
        except:
            # Fallback parsing
            try:
                import re
                json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
                if json_match:
                    spl_result = json.loads(json_match.group())
                else:
                    raise ValueError("Could not parse LLM response")
            except:
                # Create basic result
                spl_result = {
                    "spl_query": f"search index=104118 {user_query} | head 20",
                    "explanation": "Basic search query",
                    "complexity": "simple",
                    "estimated_results": "Log entries matching the query",
                    "visualization_hint": "table"
                }
        
        # Create SPL context
        spl_context = SPLContext(
            generated_query=spl_result.get("spl_query"),
            query_explanation=spl_result.get("explanation"),
            estimated_complexity=spl_result.get("complexity")
        )
        
        # Extract query context
        query_context = QueryContext(
            user_query=user_query,
            visualization_hint=spl_result.get("visualization_hint")
        )
        
        state["spl_context"] = spl_context
        state["query_context"] = query_context
        state["current_turn"].spl_context = spl_context
        state["current_turn"].query_context = query_context
        
        return state
    
    @fault_tolerant_node(NodeType.QUERY_EXECUTION)
    def query_execution_node(self, state: LogDetectiveState) -> LogDetectiveState:
        """Execute SPL query against Splunk."""
        spl_context = state.get("spl_context")
        if not spl_context or not spl_context.generated_query:
            raise ValueError("No SPL query to execute")
        
        # Test connection first
        if not splunk_connector.test_connection():
            state["splunk_connection_status"] = False
            raise ConnectionError("Cannot connect to Splunk")
        
        state["splunk_connection_status"] = True
        
        # Execute the query
        df, stats = splunk_connector.execute_search(spl_context.generated_query)
        
        if df.empty and stats.get("error"):
            raise RuntimeError(f"Query execution failed: {stats.get('error')}")
        
        # Convert results to JSON-serializable format
        results = {
            "success": not df.empty,
            "results": df.to_dict('records') if not df.empty else [],
            "stats": stats,
            "field_count": len(df.columns) if not df.empty else 0,
            "fields": list(df.columns) if not df.empty else [],
            "total_results": len(df),
            "query_executed": spl_context.generated_query
        }
        
        # Update SPL context with results
        spl_context.execution_results = results
        spl_context.query_stats = stats
        
        state["data_results"] = results
        state["spl_context"] = spl_context
        
        return state
    
    @fault_tolerant_node(NodeType.RESULT_ANALYSIS)
    def result_analysis_node(self, state: LogDetectiveState) -> LogDetectiveState:
        """Analyze query results and generate insights."""
        data_results = state.get("data_results")
        spl_context = state.get("spl_context")
        
        if not data_results or not data_results.get("success"):
            raise ValueError("No valid query results to analyze")
        
        user_query = state["current_turn"].user_query
        results = data_results.get("results", [])
        stats = data_results.get("stats", {})
        
        # Create analysis prompt
        analysis_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a Splunk log analysis expert. Analyze the query results and provide insights.

Your task is to:
1. Summarize the key findings from the data
2. Identify patterns, trends, or anomalies
3. Provide business-relevant insights
4. Suggest follow-up questions or investigations
5. Answer the user's original question clearly

Focus on actionable intelligence and clear explanations."""),
            ("human", """Original Question: {user_query}

SPL Query Executed: {spl_query}

Query Statistics:
- Results: {result_count}
- Events Scanned: {scan_count}
- Runtime: {run_duration}s

Sample Results (first 5 rows):
{sample_results}

Please provide a comprehensive analysis and answer to the user's question.""")
        ])
        
        # Prepare sample results
        sample_results = json.dumps(results[:5], indent=2, default=str) if results else "No results"
        
        messages = analysis_prompt.format_messages(
            user_query=user_query,
            spl_query=spl_context.generated_query,
            result_count=stats.get("result_count", 0),
            scan_count=stats.get("scan_count", 0),
            run_duration=stats.get("run_duration", 0),
            sample_results=sample_results
        )
        
        response = self.llm.invoke(messages)
        analysis_text = response.content
        
        state["final_response"] = analysis_text
        state["current_turn"].final_response = analysis_text
        
        return state
    
    @fault_tolerant_node(NodeType.VISUALIZATION)
    def visualization_node(self, state: LogDetectiveState) -> LogDetectiveState:
        """Generate visualizations if appropriate."""
        data_results = state.get("data_results")
        query_context = state.get("query_context")
        
        if not data_results or not data_results.get("success"):
            return state  # Skip visualization if no data
        
        results = data_results.get("results", [])
        if len(results) < 2:
            return state  # Need at least 2 rows for meaningful visualization
        
        # Check if visualization is hinted
        viz_hint = query_context.visualization_hint if query_context else None
        
        if not viz_hint:
            # Auto-suggest visualization
            suggestion_result = suggest_visualization(json.dumps(results))
            try:
                suggestions = json.loads(suggestion_result)
                if suggestions.get("suggestions"):
                    viz_hint = suggestions["suggestions"][0].get("chart_type")
            except:
                pass
        
        # Generate visualization if we have a hint
        if viz_hint and viz_hint != "table":
            try:
                viz_result = create_visualization(
                    json.dumps(results),
                    viz_hint,
                    title=f"Analysis Results - {viz_hint.title()} Chart"
                )
                
                viz_config = json.loads(viz_result)
                if "chart_config" in viz_config:
                    state["visualization_config"] = viz_config
                    state["current_turn"].visualization_data = viz_config
            except Exception as e:
                # Visualization failed, but don't break the workflow
                state = StateManager.add_error(
                    state, "visualization_error", str(e), "visualization_node", recoverable=False
                )
        
        return state
    
    def error_recovery_node(self, state: LogDetectiveState) -> LogDetectiveState:
        """Handle errors and attempt recovery."""
        if not StateManager.can_recover(state):
            # Generate error response
            error_messages = [e["error_message"] for e in state["error_stack"][-3:]]
            error_response = f"I encountered some issues processing your request: {'; '.join(error_messages)}. Please try rephrasing your query or check your Splunk connection."
            
            state["final_response"] = error_response
            state["current_turn"].final_response = error_response
            return state
        
        # Attempt recovery
        state["recovery_attempts"] += 1
        
        # Mark recoverable errors as attempted
        for error in state["error_stack"]:
            if error["recoverable"] and not error["recovery_attempted"]:
                error["recovery_attempted"] = True
        
        # Reset some state for retry
        if not state.get("splunk_connection_status"):
            # Try to reconnect
            try:
                if splunk_connector.test_connection():
                    state["splunk_connection_status"] = True
            except:
                pass
        
        return state
    
    def routing_node(self, state: LogDetectiveState) -> str:
        """Route workflow based on state and errors."""
        # Check for errors
        if state["error_stack"] and not state.get("final_response"):
            if StateManager.can_recover(state):
                return "error_recovery"
            else:
                return "error_final"
        
        # Normal workflow routing
        execution_path = state.get("execution_path", [])
        
        if "rag_retrieval_node" not in execution_path:
            return "rag_retrieval"
        elif "spl_generation_node" not in execution_path:
            return "spl_generation"
        elif "query_execution_node" not in execution_path:
            return "query_execution"
        elif "result_analysis_node" not in execution_path:
            return "result_analysis"
        elif "visualization_node" not in execution_path:
            return "visualization"
        else:
            return "end"


# Global workflow nodes instance
workflow_nodes = WorkflowNodes() 
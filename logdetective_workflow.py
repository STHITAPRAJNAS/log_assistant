"""Main LangGraph workflow for LogDetective with sophisticated fault tolerance."""

import uuid
from typing import Dict, Any
from datetime import datetime

from langgraph.graph import StateGraph, START, END
from langchain_core.messages import HumanMessage

from workflow_state import LogDetectiveState, StateManager
from workflow_nodes import workflow_nodes
from splunk_tools import splunk_connector
from config import settings


class LogDetectiveWorkflow:
    """Main workflow orchestrator for LogDetective."""
    
    def __init__(self):
        self.graph = self._build_workflow_graph()
        self.compiled_graph = self.graph.compile()
    
    def _build_workflow_graph(self) -> StateGraph:
        """Build the LangGraph workflow with sophisticated routing."""
        
        # Create the graph
        graph = StateGraph(LogDetectiveState)
        
        # Add all workflow nodes
        graph.add_node("initialize", self._initialize_node)
        graph.add_node("rag_retrieval", workflow_nodes.rag_retrieval_node)
        graph.add_node("spl_generation", workflow_nodes.spl_generation_node)
        graph.add_node("query_execution", workflow_nodes.query_execution_node)
        graph.add_node("result_analysis", workflow_nodes.result_analysis_node)
        graph.add_node("visualization", workflow_nodes.visualization_node)
        graph.add_node("error_recovery", workflow_nodes.error_recovery_node)
        graph.add_node("finalize", self._finalize_node)
        
        # Define the workflow edges
        graph.add_edge(START, "initialize")
        
        # Conditional routing from initialize
        graph.add_conditional_edges(
            "initialize",
            workflow_nodes.routing_node,
            {
                "rag_retrieval": "rag_retrieval",
                "error_recovery": "error_recovery",
                "end": "finalize"
            }
        )
        
        # Conditional routing from each main node
        for node_name in ["rag_retrieval", "spl_generation", "query_execution", 
                         "result_analysis", "visualization"]:
            graph.add_conditional_edges(
                node_name,
                workflow_nodes.routing_node,
                {
                    "rag_retrieval": "rag_retrieval",
                    "spl_generation": "spl_generation",
                    "query_execution": "query_execution",
                    "result_analysis": "result_analysis",
                    "visualization": "visualization",
                    "error_recovery": "error_recovery",
                    "end": "finalize"
                }
            )
        
        # Error recovery routing
        graph.add_conditional_edges(
            "error_recovery",
            workflow_nodes.routing_node,
            {
                "rag_retrieval": "rag_retrieval",
                "spl_generation": "spl_generation",
                "query_execution": "query_execution",
                "result_analysis": "result_analysis",
                "visualization": "visualization",
                "error_recovery": "error_recovery",
                "end": "finalize",
                "error_final": "finalize"
            }
        )
        
        # Finalize to end
        graph.add_edge("finalize", END)
        
        return graph
    
    def _initialize_node(self, state: LogDetectiveState) -> LogDetectiveState:
        """Initialize the workflow for a new query."""
        # Get the latest message
        latest_message = state["messages"][-1] if state["messages"] else None
        
        if not latest_message or not hasattr(latest_message, 'content'):
            raise ValueError("No user query found in messages")
        
        user_query = latest_message.content
        turn_id = str(uuid.uuid4())[:8]
        
        # Start new conversation turn
        state = StateManager.start_new_turn(state, user_query, turn_id)
        
        # Initialize system state
        try:
            # Test Splunk connection
            connection_status = splunk_connector.test_connection()
            state["splunk_connection_status"] = connection_status
            
            # Get available fields
            if connection_status:
                fields = splunk_connector.get_index_fields()
                state["available_fields"] = fields
            else:
                state["available_fields"] = []
                state = StateManager.add_error(
                    state, "connection_error", 
                    "Cannot connect to Splunk", 
                    "initialize_node"
                )
        except Exception as e:
            state["splunk_connection_status"] = False
            state["available_fields"] = []
            state = StateManager.add_error(
                state, "initialization_error", 
                str(e), 
                "initialize_node"
            )
        
        return state
    
    def _finalize_node(self, state: LogDetectiveState) -> LogDetectiveState:
        """Finalize the workflow and prepare response."""
        if not state["current_turn"]:
            return state
        
        # Calculate total execution time
        start_time = state["current_turn"].timestamp
        end_time = datetime.now()
        total_time = (end_time - start_time).total_seconds()
        state["current_turn"].total_execution_time = total_time
        
        # Ensure we have a final response
        if not state.get("final_response"):
            if state["error_stack"]:
                # Create error response
                recent_errors = state["error_stack"][-3:]
                error_summary = "; ".join([e["error_message"] for e in recent_errors])
                state["final_response"] = f"I encountered some issues processing your request: {error_summary}. Please check your Splunk connection and try again."
            else:
                # Create basic response
                state["final_response"] = "I processed your request but couldn't generate a comprehensive response. Please try rephrasing your query."
        
        # Update current turn
        state["current_turn"].final_response = state["final_response"]
        
        return state
    
    def process_query(self, user_query: str, conversation_history: list = None) -> Dict[str, Any]:
        """Process a user query through the workflow."""
        
        # Create initial state
        initial_state = StateManager.create_initial_state()
        
        # Add conversation history if provided
        if conversation_history:
            # Convert to proper message format
            messages = []
            for turn in conversation_history:
                if isinstance(turn, dict):
                    if turn.get("role") == "user":
                        messages.append(HumanMessage(content=turn.get("content", "")))
            initial_state["messages"] = messages
        
        # Add current user message
        initial_state["messages"].append(HumanMessage(content=user_query))
        
        try:
            # Execute the workflow
            final_state = self.compiled_graph.invoke(initial_state)
            
            # Extract response data
            response_data = {
                "success": True,
                "user_query": user_query,
                "final_response": final_state.get("final_response", ""),
                "data_results": final_state.get("data_results"),
                "visualization_config": final_state.get("visualization_config"),
                "execution_trace": final_state.get("execution_path", []),
                "total_execution_time": final_state["current_turn"].total_execution_time if final_state.get("current_turn") else 0,
                "error_count": final_state["current_turn"].error_count if final_state.get("current_turn") else 0,
                "spl_query": final_state["spl_context"].generated_query if final_state.get("spl_context") else None,
                "splunk_connection_status": final_state.get("splunk_connection_status", False)
            }
            
            return response_data
            
        except Exception as e:
            # Handle workflow-level errors
            return {
                "success": False,
                "user_query": user_query,
                "error": str(e),
                "final_response": f"I encountered a system error while processing your request: {str(e)}. Please try again.",
                "execution_trace": [],
                "total_execution_time": 0,
                "error_count": 1,
                "splunk_connection_status": False
            }
    
    def stream_query(self, user_query: str, conversation_history: list = None):
        """Stream the workflow execution for real-time updates."""
        
        # Create initial state
        initial_state = StateManager.create_initial_state()
        
        # Add conversation history and current message
        if conversation_history:
            messages = []
            for turn in conversation_history:
                if isinstance(turn, dict) and turn.get("role") == "user":
                    messages.append(HumanMessage(content=turn.get("content", "")))
            initial_state["messages"] = messages
        
        initial_state["messages"].append(HumanMessage(content=user_query))
        
        try:
            # Stream the workflow execution
            for chunk in self.compiled_graph.stream(initial_state):
                yield {
                    "node": list(chunk.keys())[0] if chunk else "unknown",
                    "state": chunk,
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            yield {
                "node": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def get_workflow_info(self) -> Dict[str, Any]:
        """Get information about the workflow structure."""
        return {
            "nodes": [
                "initialize", "rag_retrieval", "spl_generation", 
                "query_execution", "result_analysis", "visualization", 
                "error_recovery", "finalize"
            ],
            "fault_tolerance": {
                "max_retries_per_node": 3,
                "max_recovery_attempts": 3,
                "exponential_backoff": True,
                "error_recovery": True
            },
            "capabilities": [
                "RAG-enhanced SPL generation",
                "Fault-tolerant execution",
                "Conversation history management", 
                "Automatic visualization",
                "Error recovery and retry logic"
            ]
        }


# Global workflow instance
log_detective_workflow = LogDetectiveWorkflow() 
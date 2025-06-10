"""Simplified LogDetective workflow using LangGraph best practices."""

from typing import Dict, Any
from datetime import datetime

from langgraph.graph import StateGraph, START, END
from langchain_core.messages import HumanMessage

from workflow_state import LogDetectiveState, create_initial_state
from workflow_nodes import (
    initialize_system,
    retrieve_knowledge, 
    generate_spl_query,
    execute_splunk_query,
    analyze_results,
    create_visualization,
    should_continue
)


def create_workflow() -> StateGraph:
    """Create the LogDetective workflow graph."""
    
    # Create workflow
    workflow = StateGraph(LogDetectiveState)
    
    # Add nodes
    workflow.add_node("initialize", initialize_system)
    workflow.add_node("retrieve_knowledge", retrieve_knowledge)
    workflow.add_node("generate_spl", generate_spl_query)
    workflow.add_node("execute_query", execute_splunk_query)
    workflow.add_node("analyze", analyze_results)
    workflow.add_node("visualize", create_visualization)
    
    # Define flow
    workflow.add_edge(START, "initialize")
    workflow.add_edge("initialize", "retrieve_knowledge")
    workflow.add_edge("retrieve_knowledge", "generate_spl")
    workflow.add_edge("generate_spl", "execute_query")
    workflow.add_edge("execute_query", "analyze")
    workflow.add_edge("analyze", "visualize")
    
    # Conditional ending
    workflow.add_conditional_edges(
        "visualize",
        should_continue,
        {
            "retry": "retrieve_knowledge",  # Retry from knowledge retrieval
            "continue": "visualize",        # Should not happen
            "end": END
        }
    )
    
    return workflow


class LogDetectiveWorkflow:
    """Simplified workflow manager for LogDetective."""
    
    def __init__(self):
        self.workflow = create_workflow()
        self.compiled = self.workflow.compile()
    
    def process_query(self, user_query: str) -> Dict[str, Any]:
        """Process a user query through the workflow."""
        start_time = datetime.now()
        
        try:
            # Create initial state
            initial_state = create_initial_state(user_query)
            
            # Execute workflow
            final_state = self.compiled.invoke(initial_state)
            
            # Calculate duration
            duration = (datetime.now() - start_time).total_seconds()
            final_state["total_duration"] = duration
            
            # Prepare response
            return {
                "success": True,
                "user_query": user_query,
                "turn_id": final_state["turn_id"],
                "spl_query": final_state.get("spl_query"),
                "spl_explanation": final_state.get("spl_explanation"),
                "analysis_response": final_state.get("analysis_response"),
                "query_results": final_state.get("query_results"),
                "visualization_config": final_state.get("visualization_config"),
                "splunk_connected": final_state.get("splunk_connected", False),
                "error_message": final_state.get("error_message"),
                "execution_time": duration,
                "retry_count": final_state.get("retry_count", 0)
            }
            
        except Exception as e:
            return {
                "success": False,
                "user_query": user_query,
                "error": str(e),
                "analysis_response": f"Workflow failed: {str(e)}. Please try again.",
                "execution_time": (datetime.now() - start_time).total_seconds(),
                "splunk_connected": False
            }
    
    def stream_query(self, user_query: str):
        """Stream workflow execution for real-time updates."""
        try:
            initial_state = create_initial_state(user_query)
            
            for step in self.compiled.stream(initial_state):
                yield {
                    "step": list(step.keys())[0] if step else "unknown",
                    "state": step,
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            yield {
                "step": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def get_workflow_info(self) -> Dict[str, Any]:
        """Get workflow information."""
        return {
            "nodes": [
                "initialize", "retrieve_knowledge", "generate_spl",
                "execute_query", "analyze", "visualize"
            ],
            "features": [
                "Natural language to SPL conversion",
                "RAG-enhanced knowledge retrieval",
                "Automatic visualization generation",
                "Error handling and retry logic",
                "Real-time execution streaming"
            ],
            "capabilities": {
                "splunk_integration": True,
                "knowledge_base": True,
                "visualization": True,
                "conversation_memory": True
            }
        }


# Global workflow instance
log_detective_workflow = LogDetectiveWorkflow() 
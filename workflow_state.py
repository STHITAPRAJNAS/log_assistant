"""Simplified state management for LogDetective using LangGraph best practices."""

from typing import Dict, List, Any, Optional, TypedDict, Annotated
from datetime import datetime
import uuid

from langgraph.graph import add_messages
from langchain_core.messages import BaseMessage


class LogDetectiveState(TypedDict):
    """Simplified state for LogDetective workflow using LangGraph best practices."""
    
    # Core message handling - LangGraph built-in
    messages: Annotated[List[BaseMessage], add_messages]
    
    # Current query processing
    user_query: str
    turn_id: str
    
    # RAG and knowledge context
    retrieved_docs: List[Dict[str, Any]]
    rag_query: str
    
    # SPL generation context
    spl_query: Optional[str]
    spl_explanation: Optional[str]
    query_complexity: Optional[str]
    
    # Execution results
    query_results: Optional[Dict[str, Any]]
    analysis_response: Optional[str]
    visualization_config: Optional[Dict[str, Any]]
    
    # System state
    splunk_connected: bool
    available_fields: List[str]
    
    # Error handling
    error_message: Optional[str]
    retry_count: int
    
    # Metadata
    execution_start: Optional[str]
    total_duration: float


def create_initial_state(user_query: str) -> LogDetectiveState:
    """Create initial state for a new query using LangGraph patterns."""
    return LogDetectiveState(
        messages=[],
        user_query=user_query,
        turn_id=str(uuid.uuid4())[:8],
        retrieved_docs=[],
        rag_query="",
        spl_query=None,
        spl_explanation=None,
        query_complexity=None,
        query_results=None,
        analysis_response=None,
        visualization_config=None,
        splunk_connected=False,
        available_fields=[],
        error_message=None,
        retry_count=0,
        execution_start=datetime.now().isoformat(),
        total_duration=0.0
    ) 
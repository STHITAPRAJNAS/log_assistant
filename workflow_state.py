"""State management for LogDetective LangGraph workflow."""

from typing import Dict, List, Any, Optional, TypedDict, Annotated
from dataclasses import dataclass, field
from datetime import datetime
import json
from enum import Enum

# Import for state annotations
from langgraph.graph import add_messages
from langchain_core.messages import BaseMessage


class ExecutionStatus(Enum):
    """Execution status for workflow nodes."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    RETRY = "retry"


class NodeType(Enum):
    """Types of workflow nodes."""
    RAG_RETRIEVAL = "rag_retrieval"
    SPL_GENERATION = "spl_generation"
    QUERY_EXECUTION = "query_execution"
    RESULT_ANALYSIS = "result_analysis"
    VISUALIZATION = "visualization"
    ERROR_HANDLING = "error_handling"


@dataclass
class ExecutionAttempt:
    """Represents a single execution attempt."""
    timestamp: datetime
    status: ExecutionStatus
    error_message: Optional[str] = None
    execution_time: Optional[float] = None
    retry_count: int = 0


@dataclass
class NodeExecution:
    """Tracks execution state for a workflow node."""
    node_type: NodeType
    attempts: List[ExecutionAttempt] = field(default_factory=list)
    max_retries: int = 3
    last_result: Optional[Any] = None
    
    @property
    def current_status(self) -> ExecutionStatus:
        """Get current execution status."""
        return self.attempts[-1].status if self.attempts else ExecutionStatus.PENDING
    
    @property
    def retry_count(self) -> int:
        """Get current retry count."""
        return len([a for a in self.attempts if a.status == ExecutionStatus.RETRY])
    
    def can_retry(self) -> bool:
        """Check if node can be retried."""
        return self.retry_count < self.max_retries and self.current_status == ExecutionStatus.FAILED


@dataclass
class QueryContext:
    """Context for the current query being processed."""
    user_query: str
    intent: Optional[str] = None
    extracted_entities: Dict[str, Any] = field(default_factory=dict)
    time_range: Optional[str] = None
    fields_of_interest: List[str] = field(default_factory=list)
    aggregation_type: Optional[str] = None
    visualization_hint: Optional[str] = None


@dataclass
class RAGContext:
    """Context for RAG retrieval."""
    query: str
    retrieved_docs: List[Dict[str, Any]] = field(default_factory=list)
    relevance_scores: List[float] = field(default_factory=list)
    knowledge_gaps: List[str] = field(default_factory=list)


@dataclass
class SPLContext:
    """Context for SPL query generation and execution."""
    generated_query: Optional[str] = None
    query_explanation: Optional[str] = None
    estimated_complexity: Optional[str] = None
    execution_results: Optional[Dict[str, Any]] = None
    query_stats: Optional[Dict[str, Any]] = None


@dataclass
class ConversationTurn:
    """Represents a single conversation turn."""
    turn_id: str
    timestamp: datetime
    user_query: str
    final_response: Optional[str] = None
    query_context: Optional[QueryContext] = None
    rag_context: Optional[RAGContext] = None
    spl_context: Optional[SPLContext] = None
    visualization_data: Optional[Dict[str, Any]] = None
    execution_trace: List[NodeExecution] = field(default_factory=list)
    error_count: int = 0
    total_execution_time: float = 0.0


class LogDetectiveState(TypedDict):
    """Main state for the LogDetective workflow."""
    
    # Core conversation state
    messages: Annotated[List[BaseMessage], add_messages]
    current_turn: Optional[ConversationTurn]
    conversation_history: List[ConversationTurn]
    
    # Workflow execution state
    current_node: Optional[str]
    execution_path: List[str]
    node_executions: Dict[str, NodeExecution]
    
    # Context and data
    query_context: Optional[QueryContext]
    rag_context: Optional[RAGContext]
    spl_context: Optional[SPLContext]
    
    # Results and outputs
    final_response: Optional[str]
    data_results: Optional[Dict[str, Any]]
    visualization_config: Optional[Dict[str, Any]]
    
    # Error handling and fault tolerance
    error_stack: List[Dict[str, Any]]
    recovery_attempts: int
    max_recovery_attempts: int
    
    # System state
    splunk_connection_status: bool
    available_fields: List[str]
    system_health: Dict[str, Any]


class StateManager:
    """Manages state transitions and persistence."""
    
    @staticmethod
    def create_initial_state() -> LogDetectiveState:
        """Create initial workflow state."""
        return LogDetectiveState(
            messages=[],
            current_turn=None,
            conversation_history=[],
            current_node=None,
            execution_path=[],
            node_executions={},
            query_context=None,
            rag_context=None,
            spl_context=None,
            final_response=None,
            data_results=None,
            visualization_config=None,
            error_stack=[],
            recovery_attempts=0,
            max_recovery_attempts=3,
            splunk_connection_status=False,
            available_fields=[],
            system_health={}
        )
    
    @staticmethod
    def start_new_turn(state: LogDetectiveState, user_query: str, turn_id: str) -> LogDetectiveState:
        """Start a new conversation turn."""
        new_turn = ConversationTurn(
            turn_id=turn_id,
            timestamp=datetime.now(),
            user_query=user_query
        )
        
        # Archive current turn if exists
        if state["current_turn"]:
            state["conversation_history"].append(state["current_turn"])
        
        # Reset state for new turn
        state.update({
            "current_turn": new_turn,
            "current_node": None,
            "execution_path": [],
            "node_executions": {},
            "query_context": None,
            "rag_context": None,
            "spl_context": None,
            "final_response": None,
            "data_results": None,
            "visualization_config": None,
            "error_stack": [],
            "recovery_attempts": 0
        })
        
        return state
    
    @staticmethod
    def update_node_execution(
        state: LogDetectiveState, 
        node_name: str, 
        node_type: NodeType,
        status: ExecutionStatus,
        result: Any = None,
        error_message: str = None,
        execution_time: float = None
    ) -> LogDetectiveState:
        """Update execution state for a node."""
        
        # Initialize node execution if not exists
        if node_name not in state["node_executions"]:
            state["node_executions"][node_name] = NodeExecution(node_type=node_type)
        
        node_exec = state["node_executions"][node_name]
        
        # Add new attempt
        attempt = ExecutionAttempt(
            timestamp=datetime.now(),
            status=status,
            error_message=error_message,
            execution_time=execution_time
        )
        node_exec.attempts.append(attempt)
        
        # Update result if successful
        if status == ExecutionStatus.SUCCESS and result is not None:
            node_exec.last_result = result
        
        # Update current turn execution trace
        if state["current_turn"]:
            state["current_turn"].execution_trace.append(node_exec)
        
        # Update execution path
        if node_name not in state["execution_path"]:
            state["execution_path"].append(node_name)
        
        return state
    
    @staticmethod
    def add_error(
        state: LogDetectiveState, 
        error_type: str, 
        error_message: str, 
        node_name: str = None,
        recoverable: bool = True
    ) -> LogDetectiveState:
        """Add error to the error stack."""
        error_entry = {
            "timestamp": datetime.now().isoformat(),
            "error_type": error_type,
            "error_message": error_message,
            "node_name": node_name,
            "recoverable": recoverable,
            "recovery_attempted": False
        }
        
        state["error_stack"].append(error_entry)
        
        if state["current_turn"]:
            state["current_turn"].error_count += 1
        
        return state
    
    @staticmethod
    def can_recover(state: LogDetectiveState) -> bool:
        """Check if the workflow can attempt recovery."""
        return (
            state["recovery_attempts"] < state["max_recovery_attempts"] and
            len([e for e in state["error_stack"] if e["recoverable"]]) > 0
        )
    
    @staticmethod
    def get_conversation_context(state: LogDetectiveState, max_turns: int = 5) -> List[Dict[str, Any]]:
        """Get recent conversation context for RAG."""
        context = []
        
        # Add current turn
        if state["current_turn"]:
            context.append({
                "user_query": state["current_turn"].user_query,
                "timestamp": state["current_turn"].timestamp.isoformat(),
                "is_current": True
            })
        
        # Add recent history
        recent_history = state["conversation_history"][-max_turns:]
        for turn in reversed(recent_history):
            context.append({
                "user_query": turn.user_query,
                "response": turn.final_response,
                "timestamp": turn.timestamp.isoformat(),
                "spl_query": turn.spl_context.generated_query if turn.spl_context else None,
                "is_current": False
            })
        
        return context 
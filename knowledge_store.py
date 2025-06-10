"""FAISS knowledge store for Splunk documentation."""

import faiss
import numpy as np
import pickle
import os
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer
from langchain_core.tools import tool
import json


class SplunkKnowledgeStore:
    """Vector store for Splunk documentation and knowledge."""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)
        self.index = None
        self.documents = []
        self.metadata = []
        self.dimension = 384  # Default dimension for MiniLM
        
        # Initialize with Splunk documentation
        self._initialize_knowledge_base()
    
    def _initialize_knowledge_base(self):
        """Initialize with basic Splunk documentation."""
        
        # Basic Splunk SPL documentation
        splunk_docs = [
            {
                "content": "search command: The search command is the most basic command in SPL. It filters events based on keywords, field values, or boolean expressions. Example: search error OR failed",
                "category": "search_commands",
                "title": "Search Command"
            },
            {
                "content": "stats command: The stats command calculates statistics for fields. Common functions include count, sum, avg, max, min, dc (distinct count). Example: | stats count by host",
                "category": "search_commands", 
                "title": "Stats Command"
            },
            {
                "content": "eval command: The eval command creates new fields or modifies existing fields using expressions. Example: | eval new_field=field1+field2",
                "category": "search_commands",
                "title": "Eval Command"
            },
            {
                "content": "where command: The where command filters events based on boolean expressions. Example: | where count > 100",
                "category": "search_commands",
                "title": "Where Command"
            },
            {
                "content": "sort command: The sort command sorts events by one or more fields. Use - for descending order. Example: | sort -_time",
                "category": "search_commands",
                "title": "Sort Command"
            },
            {
                "content": "head and tail commands: head returns the first N events, tail returns the last N events. Example: | head 10 or | tail 5",
                "category": "search_commands",
                "title": "Head and Tail Commands"
            },
            {
                "content": "dedup command: The dedup command removes duplicate events based on field values. Example: | dedup host",
                "category": "search_commands",
                "title": "Dedup Command"
            },
            {
                "content": "rex command: The rex command extracts fields using regular expressions. Example: | rex field=_raw \"(?<user>\\w+)\"",
                "category": "search_commands",
                "title": "Rex Command"
            },
            {
                "content": "table command: The table command displays only specified fields in results. Example: | table _time, host, source",
                "category": "search_commands",
                "title": "Table Command"
            },
            {
                "content": "chart command: The chart command creates statistical charts. Example: | chart count over _time by host",
                "category": "visualization",
                "title": "Chart Command"
            },
            {
                "content": "timechart command: The timechart command creates time-based charts. Example: | timechart span=1h count",
                "category": "visualization",
                "title": "Timechart Command"
            },
            {
                "content": "join command: The join command combines results from multiple datasets. Example: | join host [search index=other]",
                "category": "search_commands",
                "title": "Join Command"
            },
            {
                "content": "lookup command: The lookup command enriches events with data from lookup tables. Example: | lookup users.csv username OUTPUT email",
                "category": "search_commands",
                "title": "Lookup Command"
            },
            {
                "content": "Time modifiers: Use earliest and latest to specify time ranges. Examples: earliest=-24h@h latest=@h, earliest=01/01/2023:00:00:00",
                "category": "time_modifiers",
                "title": "Time Modifiers"
            },
            {
                "content": "Boolean operators: Use AND, OR, NOT for complex searches. Parentheses can group conditions. Example: (error OR failed) AND NOT test",
                "category": "search_syntax",
                "title": "Boolean Operators"
            },
            {
                "content": "Wildcards: Use * for multiple characters, ? for single character. Example: host=web* OR source=*.log",
                "category": "search_syntax",
                "title": "Wildcards"
            },
            {
                "content": "Field extraction: Fields are automatically extracted from structured data. Use field=value syntax to search specific fields.",
                "category": "fields",
                "title": "Field Extraction"
            },
            {
                "content": "Common fields: _time (timestamp), _raw (original event), host (hostname), source (data source), sourcetype (data type), index (index name)",
                "category": "fields",
                "title": "Common Fields"
            },
            {
                "content": "Aggregation functions: count, dc (distinct count), sum, avg, max, min, median, mode, stdev, var, values, list",
                "category": "aggregation",
                "title": "Aggregation Functions"
            },
            {
                "content": "subsearch: Use square brackets [] to create subsearches. Example: search [search error | return host]",
                "category": "advanced",
                "title": "Subsearch"
            }
        ]
        
        # Add documents to knowledge base
        for doc in splunk_docs:
            self.add_document(doc["content"], doc)
    
    def add_document(self, content: str, metadata: Dict[str, Any]):
        """Add a document to the knowledge base."""
        # Generate embedding
        embedding = self.model.encode([content])
        
        # Initialize index if needed
        if self.index is None:
            self.dimension = embedding.shape[1]
            self.index = faiss.IndexFlatL2(self.dimension)
        
        # Add to index
        self.index.add(embedding.astype('float32'))
        
        # Store document and metadata
        self.documents.append(content)
        self.metadata.append(metadata)
    
    def search(self, query: str, k: int = 3) -> List[Dict[str, Any]]:
        """Search for relevant documents."""
        if self.index is None or len(self.documents) == 0:
            return []
        
        # Generate query embedding
        query_embedding = self.model.encode([query])
        
        # Search
        distances, indices = self.index.search(query_embedding.astype('float32'), k)
        
        # Prepare results
        results = []
        for i, idx in enumerate(indices[0]):
            if idx < len(self.documents):
                results.append({
                    "content": self.documents[idx],
                    "metadata": self.metadata[idx],
                    "score": float(distances[0][i])
                })
        
        return results
    
    def save(self, filepath: str):
        """Save the knowledge store to disk."""
        # Save FAISS index
        if self.index is not None:
            faiss.write_index(self.index, f"{filepath}.index")
        
        # Save documents and metadata
        with open(f"{filepath}.pkl", 'wb') as f:
            pickle.dump({
                'documents': self.documents,
                'metadata': self.metadata,
                'dimension': self.dimension
            }, f)
    
    def load(self, filepath: str):
        """Load the knowledge store from disk."""
        try:
            # Load FAISS index
            if os.path.exists(f"{filepath}.index"):
                self.index = faiss.read_index(f"{filepath}.index")
            
            # Load documents and metadata
            if os.path.exists(f"{filepath}.pkl"):
                with open(f"{filepath}.pkl", 'rb') as f:
                    data = pickle.load(f)
                    self.documents = data['documents']
                    self.metadata = data['metadata']
                    self.dimension = data['dimension']
        except Exception as e:
            print(f"Error loading knowledge store: {e}")


# Global knowledge store instance
knowledge_store = SplunkKnowledgeStore()

# Try to load existing knowledge store
if os.path.exists("splunk_knowledge.pkl"):
    knowledge_store.load("splunk_knowledge")


@tool
def search_splunk_documentation(query: str, max_results: int = 3) -> str:
    """
    Search Splunk documentation for syntax help and examples.
    
    Args:
        query: Search query for Splunk documentation
        max_results: Maximum number of results to return
    
    Returns:
        JSON string containing relevant documentation
    """
    results = knowledge_store.search(query, max_results)
    
    if not results:
        return json.dumps({
            "results": [],
            "message": "No relevant documentation found"
        })
    
    # Format results
    formatted_results = []
    for result in results:
        formatted_results.append({
            "title": result["metadata"].get("title", "Unknown"),
            "category": result["metadata"].get("category", "general"),
            "content": result["content"],
            "relevance_score": result["score"]
        })
    
    return json.dumps({
        "results": formatted_results,
        "total_results": len(formatted_results)
    }, indent=2)


@tool
def add_splunk_knowledge(content: str, title: str, category: str = "general") -> str:
    """
    Add new knowledge to the Splunk documentation store.
    
    Args:
        content: Documentation content
        title: Title of the documentation
        category: Category of the documentation
    
    Returns:
        Confirmation message
    """
    metadata = {
        "title": title,
        "category": category
    }
    
    knowledge_store.add_document(content, metadata)
    
    # Save the updated knowledge store
    knowledge_store.save("splunk_knowledge")
    
    return json.dumps({
        "message": f"Successfully added knowledge: {title}",
        "category": category,
        "total_documents": len(knowledge_store.documents)
    }, indent=2) 
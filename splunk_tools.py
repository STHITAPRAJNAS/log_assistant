"""Splunk SDK tools for LogDetective."""

import splunklib.client as client
import splunklib.results as results
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
import time
from langchain_core.tools import tool
from config import settings
import json


class SplunkConnector:
    """Manages Splunk connection and operations."""
    
    def __init__(self):
        self.service = None
        self._connect()
    
    def _connect(self):
        """Establish connection to Splunk."""
        try:
            self.service = client.connect(
                host=settings.splunk_host,
                port=settings.splunk_port,
                username=settings.splunk_username,
                password=settings.splunk_password,
                scheme=settings.splunk_scheme
            )
            print("Successfully connected to Splunk")
        except Exception as e:
            print(f"Failed to connect to Splunk: {e}")
            self.service = None
    
    def test_connection(self) -> bool:
        """Test Splunk connection."""
        if not self.service:
            return False
        try:
            # Simple test query
            self.service.indexes.list()
            return True
        except Exception:
            return False
    
    def get_index_fields(self, index_name: str = None) -> List[str]:
        """Get available fields for the specified index."""
        if not self.service:
            return []
        
        index_name = index_name or settings.splunk_index
        
        try:
            # Query to get field names from the index
            search_query = f"| tstats count where index={index_name} by _time | head 1 | fields *"
            
            job = self.service.jobs.create(search_query)
            
            # Wait for job completion
            while not job.is_done():
                time.sleep(0.1)
            
            # Get field names from results
            field_names = []
            for result in results.ResultsReader(job.results()):
                if isinstance(result, dict):
                    field_names = list(result.keys())
                    break
            
            job.cancel()
            
            # Add common Splunk fields
            common_fields = [
                "_time", "_raw", "host", "source", "sourcetype", 
                "index", "_indextime", "splunk_server"
            ]
            
            all_fields = list(set(field_names + common_fields))
            return sorted(all_fields)
            
        except Exception as e:
            print(f"Error getting index fields: {e}")
            return ["_time", "_raw", "host", "source", "sourcetype"]
    
    def execute_search(self, spl_query: str) -> Tuple[pd.DataFrame, Dict]:
        """Execute complete SPL query and return results as DataFrame."""
        if not self.service:
            return pd.DataFrame(), {"error": "Not connected to Splunk"}
        
        try:
            print(f"Executing SPL query: {spl_query}")
            
            # Create and run the search job
            job = self.service.jobs.create(spl_query)
            
            # Wait for job completion with timeout
            timeout = 120  # 2 minutes timeout for complex queries
            start_time = time.time()
            
            while not job.is_done():
                if time.time() - start_time > timeout:
                    job.cancel()
                    return pd.DataFrame(), {"error": "Search timeout - query too complex or large dataset"}
                time.sleep(0.5)
            
            # Get results
            results_data = []
            result_count = 0
            
            for result in results.ResultsReader(job.results()):
                if isinstance(result, dict):
                    results_data.append(result)
                    result_count += 1
                elif isinstance(result, results.Message):
                    print(f"Splunk message: {result}")
            
            # Get job statistics
            stats = {
                "result_count": result_count,
                "scan_count": job.content.get("scanCount", 0),
                "event_count": job.content.get("eventCount", 0),
                "run_duration": job.content.get("runDuration", 0),
                "is_done": job.content.get("isDone", False),
                "search_id": job.content.get("sid", "")
            }
            
            job.cancel()
            
            # Convert to DataFrame
            df = pd.DataFrame(results_data)
            
            return df, stats
            
        except Exception as e:
            print(f"Error executing SPL query: {e}")
            return pd.DataFrame(), {"error": str(e)}


# Global Splunk connector instance
splunk_connector = SplunkConnector()


@tool
def execute_spl_query(spl_query: str) -> str:
    """
    Execute a complete SPL (Splunk Processing Language) query against index 104118.
    
    Args:
        spl_query: Complete SPL query with all necessary commands, aggregations, and functions.
                  The query should be production-ready SPL that can be executed directly.
                  Examples:
                  - "search index=104118 error | head 10"
                  - "search index=104118 | stats count by host | sort -count"
                  - "search index=104118 | timechart span=1h count"
    
    Returns:
        JSON string containing search results, statistics, and metadata
    """
    df, stats = splunk_connector.execute_search(spl_query)
    
    if df.empty:
        return json.dumps({
            "success": False,
            "results": [],
            "stats": stats,
            "field_count": 0,
            "message": "No results found or query execution error occurred",
            "query_executed": spl_query
        })
    
    # Convert DataFrame to list of dictionaries
    results_list = df.to_dict('records')
    
    return json.dumps({
        "success": True,
        "results": results_list,
        "stats": stats,
        "field_count": len(df.columns),
        "fields": list(df.columns),
        "total_results": len(df),
        "query_executed": spl_query
    }, default=str, indent=2)


@tool
def get_splunk_index_fields() -> str:
    """
    Get available fields for the Splunk index 104118.
    
    Returns:
        JSON string containing list of available fields
    """
    fields = splunk_connector.get_index_fields()
    
    return json.dumps({
        "index": settings.splunk_index,
        "available_fields": fields,
        "field_count": len(fields)
    }, indent=2)


@tool
def test_splunk_connection() -> str:
    """
    Test connection to Splunk server.
    
    Returns:
        JSON string containing connection status
    """
    is_connected = splunk_connector.test_connection()
    
    return json.dumps({
        "connected": is_connected,
        "host": settings.splunk_host,
        "port": settings.splunk_port,
        "index": settings.splunk_index,
        "message": "Connection successful" if is_connected else "Connection failed"
    }, indent=2)


 
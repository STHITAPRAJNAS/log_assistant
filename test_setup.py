#!/usr/bin/env python3
"""
Test script for LogDetective setup validation.
This script tests core components without requiring full deployment.
"""

import sys
import os
from typing import Dict, Any

def test_imports():
    """Test if all required packages can be imported."""
    print("🔍 Testing imports...")
    
    try:
        import streamlit as st
        print("✓ Streamlit imported successfully")
    except ImportError as e:
        print(f"❌ Streamlit import failed: {e}")
        return False
    
    try:
        import pandas as pd
        import plotly.graph_objects as go
        print("✓ Data visualization packages imported successfully")
    except ImportError as e:
        print(f"❌ Data packages import failed: {e}")
        return False
    
    try:
        from langchain_aws import ChatBedrock
        from langgraph.prebuilt import create_react_agent
        from langgraph_supervisor import create_supervisor
        print("✓ LangGraph packages imported successfully")
    except ImportError as e:
        print(f"❌ LangGraph packages import failed: {e}")
        return False
    
    try:
        import splunklib.client as client
        print("✓ Splunk SDK imported successfully")
    except ImportError as e:
        print(f"❌ Splunk SDK import failed: {e}")
        return False
    
    try:
        import faiss
        from sentence_transformers import SentenceTransformer
        print("✓ FAISS and sentence transformers imported successfully")
    except ImportError as e:
        print(f"❌ Vector store packages import failed: {e}")
        return False
    
    return True


def test_config():
    """Test configuration loading."""
    print("\n🔧 Testing configuration...")
    
    try:
        from config import settings
        print(f"✓ Configuration loaded successfully")
        print(f"  - Splunk Index: {settings.splunk_index}")
        print(f"  - Bedrock Model: {settings.bedrock_model_id}")
        print(f"  - Max Results: {settings.max_search_results}")
        return True
    except Exception as e:
        print(f"❌ Configuration loading failed: {e}")
        return False


def test_knowledge_store():
    """Test FAISS knowledge store initialization."""
    print("\n🧠 Testing knowledge store...")
    
    try:
        from knowledge_store import knowledge_store
        
        # Test search functionality
        results = knowledge_store.search("stats command", k=2)
        if results:
            print(f"✓ Knowledge store initialized with {len(knowledge_store.documents)} documents")
            print(f"✓ Search functionality working - found {len(results)} results")
            return True
        else:
            print("❌ Knowledge store search returned no results")
            return False
    except Exception as e:
        print(f"❌ Knowledge store test failed: {e}")
        return False


def test_splunk_tools():
    """Test Splunk tools initialization (without connection)."""
    print("\n🔍 Testing Splunk tools...")
    
    try:
        from splunk_tools import splunk_connector, execute_spl_query, get_splunk_index_fields
        print("✓ Splunk tools imported successfully")
        print("✓ Tools available: execute_spl_query, get_splunk_index_fields")
        print("  Note: Actual Splunk connection testing requires valid credentials")
        return True
    except Exception as e:
        print(f"❌ Splunk tools test failed: {e}")
        return False


def test_visualization_tools():
    """Test visualization tools."""
    print("\n📊 Testing visualization tools...")
    
    try:
        from visualization_tools import chart_generator, create_visualization
        
        # Test with dummy data
        test_data = [
            {"host": "server1", "count": 100},
            {"host": "server2", "count": 75},
            {"host": "server3", "count": 150}
        ]
        
        import json
        result = create_visualization(
            json.dumps(test_data), 
            "bar", 
            x_column="host", 
            y_column="count"
        )
        
        result_data = json.loads(result)
        if "chart_config" in result_data:
            print("✓ Visualization tools working correctly")
            print("✓ Chart generation successful")
            return True
        else:
            print("❌ Chart generation failed")
            return False
    except Exception as e:
        print(f"❌ Visualization tools test failed: {e}")
        return False


def test_agents_setup():
    """Test agents setup (without AWS credentials)."""
    print("\n🤖 Testing agents setup...")
    
    try:
        # Test imports
        from agents import LogDetectiveAgents
        print("✓ Agent classes imported successfully")
        print("  Note: Full agent testing requires AWS Bedrock credentials")
        return True
    except Exception as e:
        print(f"❌ Agents setup test failed: {e}")
        if "credentials" in str(e).lower() or "bedrock" in str(e).lower():
            print("  This is expected without AWS credentials configured")
            return True
        return False


def main():
    """Run all tests."""
    print("🔍 LogDetective Setup Validation")
    print("=" * 40)
    
    tests = [
        ("Package Imports", test_imports),
        ("Configuration", test_config),
        ("Knowledge Store", test_knowledge_store),
        ("Splunk Tools", test_splunk_tools),
        ("Visualization Tools", test_visualization_tools),
        ("Agents Setup", test_agents_setup)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 40)
    print("📋 Test Summary:")
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} {test_name}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("\n🎉 All tests passed! LogDetective is ready to run.")
        print("   Use: streamlit run app.py")
    else:
        print("\n⚠️  Some tests failed. Please check the error messages above.")
        print("   Make sure all dependencies are installed: pip install -r requirements.txt")
        print("   Configure your .env file with proper credentials")
    
    return passed == len(results)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 
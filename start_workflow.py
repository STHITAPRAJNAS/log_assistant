#!/usr/bin/env python3
"""Startup script for LogDetective Workflow Edition."""

import sys
import os
import subprocess
import time
from pathlib import Path

def check_dependencies():
    """Check if all required dependencies are installed."""
    print("🔍 Checking dependencies...")
    
    required_packages = [
        'streamlit',
        'langgraph',
        'langchain',
        'langchain-aws',
        'splunklib',
        'pandas',
        'plotly',
        'faiss-cpu',
        'boto3'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"  ✅ {package}")
        except ImportError:
            missing_packages.append(package)
            print(f"  ❌ {package}")
    
    if missing_packages:
        print(f"\n❌ Missing packages: {', '.join(missing_packages)}")
        print("Install them with: pip install -r requirements.txt")
        return False
    
    print("✅ All dependencies satisfied!")
    return True

def check_configuration():
    """Check if configuration is properly set up."""
    print("\n🔧 Checking configuration...")
    
    # Check for config file
    if not Path("config.py").exists():
        print("❌ config.py not found")
        return False
    
    try:
        from config import settings
        
        # Check required settings
        required_settings = [
            'bedrock_model_id',
            'aws_default_region',
            'splunk_host',
            'splunk_port',
            'splunk_username'
        ]
        
        for setting in required_settings:
            if hasattr(settings, setting):
                value = getattr(settings, setting)
                if value:
                    print(f"  ✅ {setting}: {value}")
                else:
                    print(f"  ⚠️  {setting}: Not set")
            else:
                print(f"  ❌ {setting}: Missing")
        
        print("✅ Configuration loaded!")
        return True
        
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        return False

def initialize_knowledge_store():
    """Initialize the knowledge store."""
    print("\n📚 Initializing knowledge store...")
    
    try:
        from knowledge_store import knowledge_store
        
        # Try to search for a test query
        docs = knowledge_store.search("test", k=1)
        print(f"✅ Knowledge store initialized with {len(docs)} documents")
        return True
        
    except Exception as e:
        print(f"❌ Knowledge store error: {e}")
        return False

def test_workflow():
    """Test the workflow system."""
    print("\n🧪 Testing workflow system...")
    
    try:
        from logdetective_workflow import log_detective_workflow
        
        # Get workflow info
        info = log_detective_workflow.get_workflow_info()
        print(f"✅ Workflow initialized with {len(info['nodes'])} nodes")
        
        # Test with a simple query (without actually executing)
        print("✅ Workflow system ready!")
        return True
        
    except Exception as e:
        print(f"❌ Workflow test failed: {e}")
        return False

def test_splunk_connection():
    """Test Splunk connection."""
    print("\n🔗 Testing Splunk connection...")
    
    try:
        from splunk_tools import splunk_connector
        
        # Test connection
        if splunk_connector.test_connection():
            print("✅ Splunk connection successful!")
            
            # Test field discovery
            fields = splunk_connector.get_index_fields()
            print(f"✅ Found {len(fields)} fields in index 104118")
            
            return True
        else:
            print("⚠️  Splunk connection failed - check credentials")
            return False
            
    except Exception as e:
        print(f"❌ Splunk connection error: {e}")
        return False

def start_streamlit():
    """Start the Streamlit application."""
    print("\n🚀 Starting LogDetective Workflow Edition...")
    
    # Check if streamlit app exists
    if not Path("streamlit_app_workflow.py").exists():
        print("❌ streamlit_app_workflow.py not found")
        return False
    
    try:
        # Start Streamlit
        print("🌐 Starting Streamlit server...")
        print("📱 App will be available at: http://localhost:8501")
        print("⏹️  Press Ctrl+C to stop the server")
        
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", 
            "streamlit_app_workflow.py",
            "--server.headless", "false",
            "--server.port", "8501",
            "--browser.gatherUsageStats", "false"
        ])
        
    except KeyboardInterrupt:
        print("\n⏹️  Shutting down LogDetective...")
    except Exception as e:
        print(f"❌ Failed to start Streamlit: {e}")
        return False

def main():
    """Main startup function."""
    print("🔍 " + "="*50)
    print("🚀 LogDetective Workflow Edition Startup")
    print("="*52)
    
    # Run all checks
    checks = [
        ("Dependencies", check_dependencies),
        ("Configuration", check_configuration),
        ("Knowledge Store", initialize_knowledge_store),
        ("Workflow System", test_workflow),
        ("Splunk Connection", test_splunk_connection)
    ]
    
    failed_checks = []
    
    for check_name, check_func in checks:
        if not check_func():
            failed_checks.append(check_name)
            print(f"\n⚠️  {check_name} check failed")
        else:
            print(f"\n✅ {check_name} check passed")
    
    if failed_checks:
        print(f"\n❌ Some checks failed: {', '.join(failed_checks)}")
        print("Please fix the issues before starting the application.")
        
        # Ask if user wants to continue anyway
        response = input("\nDo you want to continue anyway? (y/N): ")
        if response.lower() != 'y':
            print("Startup cancelled.")
            return
    
    print("\n" + "="*52)
    print("🎉 All systems ready!")
    print("="*52)
    
    # Start the application
    start_streamlit()

if __name__ == "__main__":
    main() 
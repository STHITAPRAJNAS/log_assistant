#!/usr/bin/env python3
"""Simplified startup script for LogDetective Workflow."""

import sys
import subprocess
from pathlib import Path

def check_dependencies():
    """Check core dependencies."""
    print("🔍 Checking dependencies...")
    
    required = [
        'streamlit', 'langgraph', 'langchain', 'langchain-aws',
        'splunklib', 'pandas', 'plotly', 'faiss-cpu', 'boto3'
    ]
    
    missing = []
    for pkg in required:
        try:
            __import__(pkg.replace('-', '_'))
            print(f"  ✅ {pkg}")
        except ImportError:
            missing.append(pkg)
            print(f"  ❌ {pkg}")
    
    if missing:
        print(f"\n❌ Missing: {', '.join(missing)}")
        print("Install with: pip install -r requirements.txt")
        return False
    
    print("✅ All dependencies OK!")
    return True

def check_config():
    """Check configuration."""
    print("\n🔧 Checking configuration...")
    
    try:
        from config import settings
        
        checks = [
            ('bedrock_model_id', getattr(settings, 'bedrock_model_id', None)),
            ('aws_default_region', getattr(settings, 'aws_default_region', None)),
            ('splunk_host', getattr(settings, 'splunk_host', None)),
            ('splunk_username', getattr(settings, 'splunk_username', None))
        ]
        
        for name, value in checks:
            if value:
                print(f"  ✅ {name}: {value}")
            else:
                print(f"  ⚠️  {name}: Not set")
        
        print("✅ Configuration loaded!")
        return True
        
    except Exception as e:
        print(f"❌ Config error: {e}")
        return False

def test_systems():
    """Test system components."""
    print("\n🧪 Testing systems...")
    
    try:
        # Test workflow
        from logdetective_workflow import log_detective_workflow
        info = log_detective_workflow.get_workflow_info()
        print(f"✅ Workflow ready ({len(info['nodes'])} nodes)")
        
        # Test knowledge store
        from knowledge_store import knowledge_store
        docs = knowledge_store.search("test", k=1)
        print(f"✅ Knowledge store ready ({len(docs)} docs)")
        
        # Test Splunk (optional)
        try:
            from splunk_tools import splunk_connector
            if splunk_connector.test_connection():
                print("✅ Splunk connected")
            else:
                print("⚠️  Splunk connection failed")
        except:
            print("⚠️  Splunk test failed")
        
        return True
        
    except Exception as e:
        print(f"❌ System test failed: {e}")
        return False

def start_streamlit():
    """Start Streamlit app."""
    print("\n🚀 Starting LogDetective...")
    
    if not Path("streamlit_app_workflow.py").exists():
        print("❌ streamlit_app_workflow.py not found")
        return False
    
    try:
        print("🌐 Starting Streamlit server...")
        print("📱 App will be available at: http://localhost:8501")
        print("⏹️  Press Ctrl+C to stop")
        
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", 
            "streamlit_app_workflow.py",
            "--server.headless", "false",
            "--server.port", "8501"
        ])
        
    except KeyboardInterrupt:
        print("\n⏹️  Shutting down...")
    except Exception as e:
        print(f"❌ Failed to start: {e}")
        return False

def main():
    """Main startup function."""
    print("🔍 " + "="*50)
    print("🚀 LogDetective Workflow Startup")
    print("="*52)
    
    # Run checks
    checks = [
        ("Dependencies", check_dependencies),
        ("Configuration", check_config),
        ("Systems", test_systems)
    ]
    
    failed = []
    for name, check_func in checks:
        if not check_func():
            failed.append(name)
    
    if failed:
        print(f"\n❌ Failed checks: {', '.join(failed)}")
        response = input("\nContinue anyway? (y/N): ")
        if response.lower() != 'y':
            print("Startup cancelled.")
            return
    
    print("\n" + "="*52)
    print("🎉 System ready!")
    print("="*52)
    
    start_streamlit()

if __name__ == "__main__":
    main() 
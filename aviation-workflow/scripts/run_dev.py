#!/usr/bin/env python3
"""
Development server startup script for the Aviation Workflow System.

Starts both FastAPI backend server and Streamlit dashboard for development.
Handles environment setup, module loading, and graceful shutdown.
"""

import sys
import os
import signal
import subprocess
import time
import logging
import threading
from typing import Optional, List
import psutil
import requests

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import settings
from core.database import DatabaseManager
from core.plugin_manager import PluginManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Global process tracking
api_process: Optional[subprocess.Popen] = None
streamlit_process: Optional[subprocess.Popen] = None
shutdown_flag = threading.Event()


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    logger.info(f"\n🛑 Received signal {signum}. Shutting down servers...")
    shutdown_flag.set()
    cleanup_processes()
    sys.exit(0)


def cleanup_processes():
    """Clean up running processes."""
    global api_process, streamlit_process
    
    processes_to_kill = []
    if api_process and api_process.poll() is None:
        processes_to_kill.append(("FastAPI", api_process))
    if streamlit_process and streamlit_process.poll() is None:
        processes_to_kill.append(("Streamlit", streamlit_process))
    
    for name, process in processes_to_kill:
        try:
            logger.info(f"🔄 Stopping {name} server...")
            
            # Try graceful shutdown first
            process.terminate()
            try:
                process.wait(timeout=5)
                logger.info(f"✅ {name} server stopped gracefully")
            except subprocess.TimeoutExpired:
                # Force kill if graceful shutdown failed
                logger.warning(f"⚠️  Force killing {name} server...")
                process.kill()
                process.wait()
                logger.info(f"✅ {name} server force stopped")
                
        except Exception as e:
            logger.error(f"❌ Error stopping {name} server: {e}")
    
    # Kill any remaining processes on our ports
    kill_processes_on_ports([8000, 8501])


def kill_processes_on_ports(ports: List[int]):
    """Kill any processes running on specified ports."""
    for port in ports:
        try:
            for proc in psutil.process_iter(['pid', 'name', 'connections']):
                try:
                    if proc.info['connections']:
                        for conn in proc.info['connections']:
                            if conn.laddr.port == port:
                                logger.info(f"🔄 Killing process {proc.info['pid']} on port {port}")
                                psutil.Process(proc.info['pid']).terminate()
                                break
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception as e:
            logger.error(f"Error killing processes on port {port}: {e}")


def check_port_availability(port: int) -> bool:
    """Check if a port is available."""
    try:
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            result = s.connect_ex(('localhost', port))
            return result != 0
    except Exception:
        return False


def wait_for_service(url: str, timeout: int = 30) -> bool:
    """Wait for a service to become available."""
    logger.info(f"⏳ Waiting for service at {url}...")
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        if shutdown_flag.is_set():
            return False
            
        try:
            response = requests.get(url, timeout=2)
            if response.status_code == 200:
                logger.info(f"✅ Service at {url} is ready")
                return True
        except Exception:
            pass
        
        time.sleep(1)
    
    logger.warning(f"⚠️  Service at {url} not ready after {timeout} seconds")
    return False


def check_database_connection():
    """Test database connection."""
    try:
        db_manager = DatabaseManager()
        engine = db_manager.get_engine()
        
        from sqlmodel import text
        with engine.connect() as conn:
            if settings.database_url.startswith("sqlite"):
                result = conn.execute(text("SELECT 1"))
            else:
                result = conn.execute(text("SELECT version()"))
            
            result.fetchone()
            logger.info("✅ Database connection verified")
            return True
            
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False


def load_enabled_modules() -> List[str]:
    """Load enabled modules."""
    try:
        plugin_manager = PluginManager()
        
        enabled_modules = settings.enabled_modules.split(",")
        enabled_modules = [m.strip() for m in enabled_modules if m.strip()]
        
        logger.info(f"📋 Enabled modules: {', '.join(enabled_modules)}")
        
        loaded_modules = []
        for module_name in enabled_modules:
            try:
                logger.info(f"🔄 Loading module: {module_name}")
                module_interface = plugin_manager.load_module(module_name)
                
                if module_interface:
                    loaded_modules.append(module_name)
                    logger.info(f"✅ Successfully loaded module: {module_name}")
                else:
                    logger.warning(f"⚠️  Module {module_name} returned None")
                    
            except Exception as e:
                logger.error(f"❌ Failed to load module {module_name}: {e}")
                continue
        
        logger.info(f"✅ Loaded {len(loaded_modules)} modules")
        return loaded_modules
        
    except Exception as e:
        logger.error(f"❌ Error loading modules: {e}")
        return []


def start_fastapi_server() -> Optional[subprocess.Popen]:
    """Start the FastAPI server."""
    global api_process
    
    logger.info("🚀 Starting FastAPI server...")
    
    # Check if port 8000 is available
    if not check_port_availability(8000):
        logger.warning("⚠️  Port 8000 is already in use. Attempting to kill existing processes...")
        kill_processes_on_ports([8000])
        time.sleep(2)
        
        if not check_port_availability(8000):
            logger.error("❌ Could not free port 8000")
            return None
    
    try:
        # Start FastAPI with uvicorn
        cmd = [
            sys.executable, "-m", "uvicorn",
            "api.main:app",
            "--host", "0.0.0.0",
            "--port", "8000",
            "--reload",
            "--reload-dir", "api",
            "--reload-dir", "core", 
            "--reload-dir", "modules",
            "--log-level", "info"
        ]
        
        api_process = subprocess.Popen(
            cmd,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        logger.info(f"✅ FastAPI server starting (PID: {api_process.pid})")
        return api_process
        
    except Exception as e:
        logger.error(f"❌ Failed to start FastAPI server: {e}")
        return None


def start_streamlit_dashboard() -> Optional[subprocess.Popen]:
    """Start the Streamlit dashboard."""
    global streamlit_process
    
    logger.info("📊 Starting Streamlit dashboard...")
    
    # Check if port 8501 is available
    if not check_port_availability(8501):
        logger.warning("⚠️  Port 8501 is already in use. Attempting to kill existing processes...")
        kill_processes_on_ports([8501])
        time.sleep(2)
        
        if not check_port_availability(8501):
            logger.error("❌ Could not free port 8501")
            return None
    
    try:
        # Check if dashboard.py exists
        dashboard_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "dashboard",
            "main.py"
        )
        
        if not os.path.exists(dashboard_path):
            logger.warning("⚠️  Streamlit dashboard not found. Creating placeholder...")
            create_placeholder_dashboard(dashboard_path)
        
        cmd = [
            sys.executable, "-m", "streamlit",
            "run", dashboard_path,
            "--server.port", "8501",
            "--server.address", "0.0.0.0",
            "--server.headless", "true",
            "--browser.gatherUsageStats", "false"
        ]
        
        streamlit_process = subprocess.Popen(
            cmd,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        logger.info(f"✅ Streamlit dashboard starting (PID: {streamlit_process.pid})")
        return streamlit_process
        
    except Exception as e:
        logger.error(f"❌ Failed to start Streamlit dashboard: {e}")
        return None


def create_placeholder_dashboard(dashboard_path: str):
    """Create a placeholder Streamlit dashboard."""
    os.makedirs(os.path.dirname(dashboard_path), exist_ok=True)
    
    dashboard_content = '''"""
Aviation Workflow System - Dashboard
Placeholder dashboard for development environment.
"""

import streamlit as st
import requests
import json
from datetime import datetime

st.set_page_config(
    page_title="Aviation Workflow System",
    page_icon="✈️",
    layout="wide"
)

st.title("✈️ Aviation Workflow System Dashboard")
st.markdown("---")

# API Status Check
def check_api_status():
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        return response.status_code == 200, response.json() if response.status_code == 200 else None
    except Exception as e:
        return False, str(e)

# Display API status
col1, col2 = st.columns([3, 1])

with col1:
    st.subheader("🔌 System Status")
    
    api_status, api_data = check_api_status()
    if api_status:
        st.success("✅ API Server: Online")
        if api_data:
            st.info(f"Database: {api_data.get('database', 'Unknown')}")
            st.info(f"Modules: {', '.join(api_data.get('loaded_modules', []))}")
    else:
        st.error("❌ API Server: Offline")
        st.error(f"Error: {api_data}")

with col2:
    if st.button("🔄 Refresh Status"):
        st.rerun()

st.markdown("---")

# Quick Links
st.subheader("🔗 Quick Links")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    **API Documentation**
    - [Swagger UI](http://localhost:8000/docs)
    - [ReDoc](http://localhost:8000/redoc)
    """)

with col2:
    st.markdown("""
    **Development**
    - [Health Check](http://localhost:8000/health)
    - [Module Status](http://localhost:8000/api/system/modules)
    """)

with col3:
    st.markdown("""
    **Database**
    - Initialize: `python scripts/init_db.py`
    - Seed Data: `python scripts/seed_data.py`
    """)

st.markdown("---")

# System Information
st.subheader("ℹ️ System Information")

if api_status and api_data:
    col1, col2 = st.columns(2)
    
    with col1:
        st.json({
            "Environment": "Development",
            "API Version": api_data.get("version", "Unknown"),
            "Database Status": "Connected" if api_status else "Disconnected",
            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
    
    with col2:
        modules = api_data.get("loaded_modules", [])
        if modules:
            st.write("**Loaded Modules:**")
            for module in modules:
                st.write(f"• {module}")
        else:
            st.write("No modules loaded")

st.markdown("---")
st.markdown("*Dashboard created automatically by run_dev.py*")
'''
    
    with open(dashboard_path, 'w') as f:
        f.write(dashboard_content)
    
    logger.info(f"✅ Created placeholder dashboard at {dashboard_path}")


def monitor_processes():
    """Monitor running processes and handle output."""
    global api_process, streamlit_process
    
    def log_output(process, name):
        while process and process.poll() is None and not shutdown_flag.is_set():
            try:
                if process.stdout:
                    line = process.stdout.readline()
                    if line:
                        # Only log important messages to avoid spam
                        line = line.strip()
                        if any(keyword in line.lower() for keyword in ['error', 'warning', 'started', 'ready']):
                            logger.info(f"[{name}] {line}")
            except Exception:
                break
    
    # Start monitoring threads
    if api_process:
        api_thread = threading.Thread(target=log_output, args=(api_process, "API"))
        api_thread.daemon = True
        api_thread.start()
    
    if streamlit_process:
        streamlit_thread = threading.Thread(target=log_output, args=(streamlit_process, "Dashboard"))
        streamlit_thread.daemon = True
        streamlit_thread.start()


def show_startup_info():
    """Display startup information and URLs."""
    print("\n" + "=" * 60)
    print("🎉 AVIATION WORKFLOW SYSTEM - DEVELOPMENT SERVERS")
    print("=" * 60)
    print("🌐 API Server:")
    print("   • Base URL: http://localhost:8000")
    print("   • API Docs: http://localhost:8000/docs")
    print("   • Health Check: http://localhost:8000/health")
    print()
    print("📊 Dashboard:")
    print("   • Streamlit UI: http://localhost:8501")
    print()
    print("🔧 Development Commands:")
    print("   • Initialize DB: python scripts/init_db.py")
    print("   • Seed Data: python scripts/seed_data.py")
    print("   • Stop Servers: Ctrl+C")
    print("=" * 60)
    print("🚀 Servers are starting up... Please wait for ready status.")
    print("📝 Press Ctrl+C to stop all servers gracefully.")
    print()


def main():
    """Main development server startup function."""
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("🚀 Aviation Workflow System - Development Environment")
    print("=" * 60)
    
    # Pre-flight checks
    logger.info("🔍 Running pre-flight checks...")
    
    # Check database connection
    if not check_database_connection():
        logger.error("❌ Database connection failed. Please check configuration.")
        logger.info("💡 Try running: python scripts/init_db.py")
        return 1
    
    # Load modules
    logger.info("🔌 Loading enabled modules...")
    loaded_modules = load_enabled_modules()
    
    if not loaded_modules:
        logger.warning("⚠️  No modules loaded. Some functionality may be limited.")
    
    # Start servers
    logger.info("🔄 Starting development servers...")
    
    # Start FastAPI server
    api_process = start_fastapi_server()
    if not api_process:
        logger.error("❌ Failed to start FastAPI server")
        return 1
    
    # Start Streamlit dashboard
    streamlit_process = start_streamlit_dashboard()
    if not streamlit_process:
        logger.warning("⚠️  Failed to start Streamlit dashboard")
    
    # Show startup information
    show_startup_info()
    
    # Wait for API to be ready
    api_ready = wait_for_service("http://localhost:8000/health", timeout=30)
    if not api_ready:
        logger.error("❌ API server failed to start properly")
        cleanup_processes()
        return 1
    
    # Wait for Streamlit to be ready (if started)
    if streamlit_process:
        dashboard_ready = wait_for_service("http://localhost:8501", timeout=30)
        if dashboard_ready:
            logger.info("🎊 Both servers are ready!")
        else:
            logger.warning("⚠️  Dashboard may not be ready, but API is running")
    else:
        logger.info("✅ API server is ready!")
    
    # Start monitoring
    monitor_processes()
    
    # Keep the script running
    try:
        while not shutdown_flag.is_set():
            time.sleep(1)
            
            # Check if processes are still running
            if api_process and api_process.poll() is not None:
                logger.error("❌ FastAPI server stopped unexpectedly")
                break
            
            if streamlit_process and streamlit_process.poll() is not None:
                logger.warning("⚠️  Streamlit dashboard stopped unexpectedly")
                streamlit_process = None
                
    except KeyboardInterrupt:
        pass
    
    logger.info("🔄 Shutting down development servers...")
    cleanup_processes()
    
    logger.info("👋 Development environment stopped. Goodbye!")
    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        cleanup_processes()
        sys.exit(1)
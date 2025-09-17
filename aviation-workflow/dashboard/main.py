"""
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

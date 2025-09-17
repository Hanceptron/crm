"""
Aviation Workflow System - Main Streamlit Application

Main application entry point for the Streamlit UI, providing a comprehensive
dashboard for managing aviation workflow items with department-based approvals.
"""

import streamlit as st
import requests
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import pandas as pd

# Import custom components
from components.workflow_viz import render_workflow_progress
from components.item_card import render_work_item_card

# Page configuration with aviation theme
st.set_page_config(
    page_title="Aviation Workflow System",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for aviation theme
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .status-card {
        background: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    
    .priority-high {
        border-left: 4px solid #dc3545;
    }
    
    .priority-medium {
        border-left: 4px solid #ffc107;
    }
    
    .priority-low {
        border-left: 4px solid #28a745;
    }
    
    .priority-critical {
        border-left: 4px solid #6f42c1;
    }
    
    .metric-container {
        background: white;
        border-radius: 8px;
        padding: 1rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# API Configuration
API_URL = "http://localhost:8000/api"

def check_api_connection() -> bool:
    """Check if API server is available."""
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        return response.status_code == 200
    except Exception:
        return False

def get_api_data(endpoint: str) -> Optional[Dict]:
    """Get data from API endpoint with error handling."""
    try:
        # Clean up endpoint - remove leading slash if present
        endpoint = endpoint.lstrip('/')
        response = requests.get(f"{API_URL}/{endpoint}", timeout=10)
        if response.status_code == 200:
            try:
                return response.json()
            except ValueError:
                st.error("Invalid JSON response from API")
                return None
        else:
            st.error(f"API Error {response.status_code}: {response.text}")
            return None
    except requests.exceptions.RequestException as e:
        st.error(f"Connection error: {str(e)}")
        return None

def initialize_session_state():
    """Initialize Streamlit session state variables."""
    if "selected_item" not in st.session_state:
        st.session_state.selected_item = None
    
    if "current_user" not in st.session_state:
        st.session_state.current_user = "demo_user@aviation.com"
    
    if "user_department" not in st.session_state:
        st.session_state.user_department = "flight_operations"
    
    if "view_mode" not in st.session_state:
        st.session_state.view_mode = "dashboard"
    
    if "last_refresh" not in st.session_state:
        st.session_state.last_refresh = datetime.now()

def _extract_work_items(data: Any) -> List[Dict]:
    """Normalize API response to a list of work items."""
    items: List[Dict] = []
    if isinstance(data, dict) and isinstance(data.get("items"), list):
        items = data["items"]
    elif isinstance(data, list):
        items = data
    else:
        return []

    # Derive department_ids from workflow_data if missing
    normalized: List[Dict] = []
    for it in items:
        if isinstance(it, dict):
            wf = it.get("workflow_data") or {}
            dept_seq = wf.get("department_sequence") if isinstance(wf, dict) else []
            if "department_ids" not in it:
                it = {**it, "department_ids": dept_seq or []}
            normalized.append(it)
    return normalized


def render_sidebar():
    """Render the sidebar with navigation and system status."""
    with st.sidebar:
        st.markdown("""
        <div style="text-align: center; padding: 1rem;">
            <h1>✈️ Aviation Workflow</h1>
            <p style="color: #666;">Department Approval System</p>
        </div>
        """, unsafe_allow_html=True)
        
        # API Status
        st.subheader("🔌 System Status")
        api_connected = check_api_connection()
        
        if api_connected:
            st.success("✅ API Connected")
            
            # Try to get system health
            health_data = get_api_data("../health")
            if health_data:
                st.info(f"Database: {health_data.get('database', 'Unknown')}")
                
                loaded_modules = health_data.get('loaded_modules', [])
                if loaded_modules and isinstance(loaded_modules, list):
                    st.subheader("📦 Active Modules")
                    for module in loaded_modules:
                        st.write(f"• {module}")
                elif loaded_modules:
                    st.subheader("📦 Active Modules")
                    st.write(f"• {loaded_modules}")
        else:
            st.error("❌ API Disconnected")
            st.warning("Please start the API server")
            
        st.markdown("---")
        
        # User Information (Mock)
        st.subheader("👤 Current User")
        st.info(f"**User:** {st.session_state.current_user}")
        st.info(f"**Department:** {st.session_state.user_department}")
        
        # Department Selector (Mock)
        departments = [
            "flight_operations",
            "maintenance", 
            "safety_quality",
            "ground_services",
            "customer_service"
        ]
        
        new_dept = st.selectbox(
            "Switch Department",
            departments,
            index=departments.index(st.session_state.user_department),
            key="dept_selector"
        )
        
        if new_dept != st.session_state.user_department:
            st.session_state.user_department = new_dept
            st.rerun()
        
        st.markdown("---")
        
        # Quick Stats
        if api_connected:
            st.subheader("📊 Quick Stats")
            
            # Get work items for stats
            raw = get_api_data("work-items")
            work_items = _extract_work_items(raw)
            if work_items is not None:
                total_items = len(work_items)
                # Map API statuses to UI buckets (rough)
                pending_items = len([item for item in work_items if item.get('status') in ['active', 'pending']])
                in_progress_items = len([item for item in work_items if item.get('status') in ['active']])
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Total Items", total_items)
                    st.metric("Pending", pending_items)
                with col2:
                    st.metric("In Progress", in_progress_items)
                    st.metric("My Queue", pending_items // 2)  # Mock calculation
        
        st.markdown("---")
        
        # Refresh Button
        if st.button("🔄 Refresh Data"):
            st.session_state.last_refresh = datetime.now()
            st.rerun()
        
        st.caption(f"Last updated: {st.session_state.last_refresh.strftime('%H:%M:%S')}")

def render_main_dashboard():
    """Render the main dashboard with work items."""
    st.markdown("""
    <div class="main-header">
        <h1>Aviation Workflow Dashboard</h1>
        <p>Manage work items across departments with approval workflows</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Check API connection
    if not check_api_connection():
        st.error("🚫 Cannot connect to API server. Please ensure the backend is running.")
        st.code("python scripts/run_dev.py", language="bash")
        return
    
    # Main content tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "📋 All Work Items", 
        "✅ My Approvals", 
        "📊 Analytics",
        "⚙️ System Info"
    ])
    
    with tab1:
        render_work_items_view()
    
    with tab2:
        render_my_approvals_view()
    
    with tab3:
        render_analytics_view()
    
    with tab4:
        render_system_info_view()

def render_work_items_view():
    """Render the work items list view."""
    st.subheader("📋 Work Items")
    
    # Filters
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        status_filter = st.selectbox(
            "Status Filter",
            ["All", "pending", "in_progress", "approved", "rejected", "completed"],
            key="status_filter"
        )
    
    with col2:
        priority_filter = st.selectbox(
            "Priority Filter", 
            ["All", "critical", "high", "medium", "low"],
            key="priority_filter"
        )
    
    with col3:
        department_filter = st.selectbox(
            "Department Filter",
            ["All", "flight_operations", "maintenance", "safety_quality", "ground_services", "customer_service"],
            key="dept_filter"
        )
    
    with col4:
        sort_by = st.selectbox(
            "Sort By",
            ["Created Date", "Due Date", "Priority", "Title"],
            key="sort_filter"
        )
    
    # Get work items
    raw = get_api_data("work-items")
    work_items = _extract_work_items(raw)
    
    if not work_items:
        st.warning("No work items found or unable to connect to API")
        return
    
    # Apply filters
    filtered_items = work_items.copy()
    
    if status_filter != "All":
        filtered_items = [item for item in filtered_items if item.get('status') == status_filter]
    
    if priority_filter != "All":
        filtered_items = [item for item in filtered_items if item.get('priority') == priority_filter]
    
    if department_filter != "All":
        filtered_items = [item for item in filtered_items 
                         if department_filter in item.get('department_ids', [])]
    
    st.write(f"Showing {len(filtered_items)} of {len(work_items)} work items")
    
    # Display work items
    if filtered_items:
        for item in filtered_items:
            render_work_item_card(item, show_actions=True)
    else:
        st.info("No work items match the current filters")

def render_my_approvals_view():
    """Render the user's pending approvals."""
    st.subheader("✅ My Pending Approvals")
    st.info(f"Showing items pending approval in **{st.session_state.user_department}** department")
    
    raw = get_api_data("work-items")
    work_items = _extract_work_items(raw)
    
    if not work_items:
        st.warning("Unable to load work items")
        return
    
    # Filter items pending in user's department
    pending_approvals = []
    for item in work_items:
        dept_ids = item.get('department_ids', [])
        current_step = item.get('current_step', 0)
        
        # Check if item is at user's department step and pending
        if (current_step < len(dept_ids) and 
            dept_ids[current_step] == st.session_state.user_department and
            item.get('status') in ['pending', 'in_progress']):
            pending_approvals.append(item)
    
    if pending_approvals:
        st.write(f"You have {len(pending_approvals)} items pending approval")
        
        for item in pending_approvals:
            with st.container():
                render_work_item_card(item, show_actions=True, show_approval_actions=True)
                
                # Approval actions
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if st.button(f"✅ Approve", key=f"approve_{item['id']}"):
                        st.success(f"Approved: {item['title']}")
                        st.info("In a real system, this would move the item to the next department")
                
                with col2:
                    if st.button(f"❌ Reject", key=f"reject_{item['id']}"):
                        st.error(f"Rejected: {item['title']}")
                        st.info("In a real system, this would move the item back to the previous step")
                
                with col3:
                    if st.button(f"💬 Comment", key=f"comment_{item['id']}"):
                        st.info("Comment modal would open here")
                
                st.markdown("---")
    else:
        st.info("No items pending your approval")

def render_analytics_view():
    """Render analytics and statistics."""
    st.subheader("📊 System Analytics")
    
    raw = get_api_data("work-items")
    work_items = _extract_work_items(raw)
    
    if not work_items:
        st.warning("Unable to load analytics data")
        return
    
    # Create metrics
    total_items = len(work_items)
    
    # Status distribution
    status_counts = {}
    priority_counts = {}
    
    for item in work_items:
        status = item.get('status', 'unknown')
        priority = item.get('priority', 'unknown')
        
        status_counts[status] = status_counts.get(status, 0) + 1
        priority_counts[priority] = priority_counts.get(priority, 0) + 1
    
    # Display metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Items", total_items)
    with col2:
        st.metric("Pending", status_counts.get('pending', 0))
    with col3:
        st.metric("In Progress", status_counts.get('in_progress', 0))
    with col4:
        st.metric("Completed", status_counts.get('completed', 0))
    
    # Charts
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Status Distribution")
        if status_counts:
            status_df = pd.DataFrame(
                list(status_counts.items()),
                columns=['Status', 'Count']
            )
            st.bar_chart(status_df.set_index('Status'))
    
    with col2:
        st.subheader("Priority Distribution") 
        if priority_counts:
            priority_df = pd.DataFrame(
                list(priority_counts.items()),
                columns=['Priority', 'Count']
            )
            st.bar_chart(priority_df.set_index('Priority'))

def render_system_info_view():
    """Render system information and health status."""
    st.subheader("⚙️ System Information")
    
    # API Health
    health_data = get_api_data("../health")
    
    if health_data:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🏥 System Health")
            st.json({
                "API Status": "Online",
                "Database": health_data.get('database', 'Unknown'),
                "Version": health_data.get('version', '1.0.0'),
                "Environment": "Development"
            })
        
        with col2:
            st.subheader("📦 Loaded Modules")
            modules = health_data.get('loaded_modules', [])
            if modules:
                for module in modules:
                    st.success(f"✅ {module}")
            else:
                st.warning("No modules loaded")
    else:
        st.error("Unable to retrieve system health information")
    
    # Development Info
    st.subheader("🛠️ Development Information")
    st.info("""
    **Development Server URLs:**
    - API Base: http://localhost:8000
    - API Docs: http://localhost:8000/docs
    - Health Check: http://localhost:8000/health
    - Streamlit UI: http://localhost:8501
    """)
    
    # Useful Commands
    st.subheader("💻 Useful Commands")
    st.code("""
    # Initialize database
    python scripts/init_db.py
    
    # Seed sample data
    python scripts/seed_data.py
    
    # Start development servers
    python scripts/run_dev.py
    """, language="bash")

def main():
    """Main application entry point."""
    # Initialize session state
    initialize_session_state()
    
    # Render sidebar
    render_sidebar()
    
    # Render main content
    render_main_dashboard()

if __name__ == "__main__":
    main()

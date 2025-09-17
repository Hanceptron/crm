"""
Dashboard Page - Main overview of work items

Displays work items in grid/list format with filtering capabilities,
quick stats, and real-time updates from the API.
"""

import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import time

# Import custom components (using relative imports for pages)
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from components.workflow_viz import render_workflow_stats
from components.item_card import (
    render_work_item_card, 
    render_work_item_summary, 
    render_work_item_grid,
    render_work_item_table
)

# Page configuration
st.set_page_config(
    page_title="Dashboard - Aviation Workflow",
    page_icon="📋",
    layout="wide"
)

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
        response = requests.get(f"{API_URL}/{endpoint}", timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"API Error {response.status_code}: {response.text}")
            return None
    except requests.exceptions.RequestException as e:
        st.error(f"Connection error: {str(e)}")
        return None

def initialize_session_state():
    """Initialize dashboard-specific session state."""
    if "dashboard_view_mode" not in st.session_state:
        st.session_state.dashboard_view_mode = "grid"
    
    if "auto_refresh" not in st.session_state:
        st.session_state.auto_refresh = False
    
    if "refresh_interval" not in st.session_state:
        st.session_state.refresh_interval = 30
    
    if "last_refresh_time" not in st.session_state:
        st.session_state.last_refresh_time = datetime.now()

def render_header():
    """Render the dashboard header with title and controls."""
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.title("📋 Workflow Dashboard")
        st.markdown("*Real-time overview of all work items*")
    
    with col2:
        # View mode selector
        view_mode = st.selectbox(
            "View Mode",
            ["grid", "list", "table"],
            index=["grid", "list", "table"].index(st.session_state.dashboard_view_mode),
            key="view_mode_selector"
        )
        
        if view_mode != st.session_state.dashboard_view_mode:
            st.session_state.dashboard_view_mode = view_mode
            st.rerun()
    
    with col3:
        # Auto-refresh controls
        auto_refresh = st.checkbox(
            "Auto Refresh",
            value=st.session_state.auto_refresh,
            key="auto_refresh_checkbox"
        )
        
        if auto_refresh != st.session_state.auto_refresh:
            st.session_state.auto_refresh = auto_refresh
        
        if auto_refresh:
            refresh_interval = st.selectbox(
                "Refresh (sec)",
                [10, 30, 60, 120],
                index=[10, 30, 60, 120].index(st.session_state.refresh_interval),
                key="refresh_interval_selector"
            )
            st.session_state.refresh_interval = refresh_interval

def render_api_status():
    """Render API connection status."""
    api_connected = check_api_connection()
    
    if api_connected:
        st.success("✅ API Connected")
        
        # Show last refresh time
        last_refresh = st.session_state.last_refresh_time.strftime("%H:%M:%S")
        st.caption(f"Last updated: {last_refresh}")
    else:
        st.error("❌ API Disconnected")
        st.warning("Please start the API server: `python scripts/run_dev.py`")
        return False
    
    return True

def render_quick_stats(work_items: List[Dict[str, Any]]):
    """Render quick statistics cards."""
    if not work_items:
        return
    
    # Calculate statistics
    total_items = len(work_items)
    
    status_counts = {}
    priority_counts = {}
    overdue_count = 0
    
    for item in work_items:
        status = item.get('status', 'unknown')
        priority = item.get('priority', 'unknown')
        due_date = item.get('due_date')
        
        status_counts[status] = status_counts.get(status, 0) + 1
        priority_counts[priority] = priority_counts.get(priority, 0) + 1
        
        # Check if overdue
        if due_date:
            try:
                due_dt = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
                if due_dt < datetime.now(due_dt.tzinfo):
                    overdue_count += 1
            except Exception:
                pass
    
    # Display metrics in columns
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    
    with col1:
        st.metric(
            "Total Items",
            total_items,
            delta=None
        )
    
    with col2:
        pending_count = status_counts.get('pending', 0)
        st.metric(
            "Pending",
            pending_count,
            delta=f"{(pending_count/total_items*100):.1f}%" if total_items > 0 else None
        )
    
    with col3:
        in_progress_count = status_counts.get('in_progress', 0)
        st.metric(
            "In Progress", 
            in_progress_count,
            delta=f"{(in_progress_count/total_items*100):.1f}%" if total_items > 0 else None
        )
    
    with col4:
        completed_count = status_counts.get('completed', 0)
        st.metric(
            "Completed",
            completed_count,
            delta=f"{(completed_count/total_items*100):.1f}%" if total_items > 0 else None
        )
    
    with col5:
        critical_count = priority_counts.get('critical', 0)
        high_count = priority_counts.get('high', 0)
        urgent_count = critical_count + high_count
        st.metric(
            "Urgent Items",
            urgent_count,
            delta="Critical + High priority"
        )
    
    with col6:
        st.metric(
            "Overdue",
            overdue_count,
            delta="⚠️ Past due date" if overdue_count > 0 else "✅ All on time"
        )

def render_filters():
    """Render filter controls and return filter values."""
    st.subheader("🔍 Filters")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        status_filter = st.selectbox(
            "Status",
            ["All", "pending", "in_progress", "approved", "rejected", "completed"],
            key="dashboard_status_filter"
        )
    
    with col2:
        priority_filter = st.selectbox(
            "Priority",
            ["All", "critical", "high", "medium", "low"],
            key="dashboard_priority_filter"
        )
    
    with col3:
        department_filter = st.selectbox(
            "Department",
            ["All", "flight_operations", "maintenance", "safety_quality", 
             "ground_services", "customer_service"],
            key="dashboard_department_filter"
        )
    
    with col4:
        date_filter = st.selectbox(
            "Date Range",
            ["All", "Today", "This Week", "This Month", "Overdue"],
            key="dashboard_date_filter"
        )
    
    with col5:
        sort_by = st.selectbox(
            "Sort By",
            ["Created Date (Newest)", "Created Date (Oldest)", 
             "Priority (High to Low)", "Due Date", "Title A-Z"],
            key="dashboard_sort_filter"
        )
    
    # Search box
    search_term = st.text_input(
        "🔍 Search items...",
        placeholder="Search by title, description, or ID",
        key="dashboard_search"
    )
    
    return {
        "status": status_filter,
        "priority": priority_filter,
        "department": department_filter,
        "date_range": date_filter,
        "sort_by": sort_by,
        "search": search_term
    }

def apply_filters(work_items: List[Dict[str, Any]], filters: Dict[str, str]) -> List[Dict[str, Any]]:
    """Apply filters to work items list."""
    filtered_items = work_items.copy()
    
    # Status filter
    if filters["status"] != "All":
        filtered_items = [item for item in filtered_items 
                         if item.get('status') == filters["status"]]
    
    # Priority filter
    if filters["priority"] != "All":
        filtered_items = [item for item in filtered_items 
                         if item.get('priority') == filters["priority"]]
    
    # Department filter
    if filters["department"] != "All":
        filtered_items = [item for item in filtered_items 
                         if filters["department"] in item.get('department_ids', [])]
    
    # Date range filter
    if filters["date_range"] != "All":
        now = datetime.now()
        
        if filters["date_range"] == "Today":
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            filtered_items = [item for item in filtered_items 
                             if item.get('created_at') and 
                             datetime.fromisoformat(item['created_at'].replace('Z', '+00:00')) >= today_start]
        
        elif filters["date_range"] == "This Week":
            week_start = now - timedelta(days=now.weekday())
            week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
            filtered_items = [item for item in filtered_items 
                             if item.get('created_at') and 
                             datetime.fromisoformat(item['created_at'].replace('Z', '+00:00')) >= week_start]
        
        elif filters["date_range"] == "This Month":
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            filtered_items = [item for item in filtered_items 
                             if item.get('created_at') and 
                             datetime.fromisoformat(item['created_at'].replace('Z', '+00:00')) >= month_start]
        
        elif filters["date_range"] == "Overdue":
            filtered_items = []
            for item in work_items:
                due_date = item.get('due_date')
                if due_date:
                    try:
                        due_dt = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
                        if due_dt < now:
                            filtered_items.append(item)
                    except Exception:
                        pass
    
    # Search filter
    if filters["search"]:
        search_term = filters["search"].lower()
        filtered_items = [item for item in filtered_items 
                         if search_term in item.get('title', '').lower() or
                         search_term in item.get('description', '').lower() or
                         search_term in item.get('id', '').lower()]
    
    # Sorting
    if filters["sort_by"] == "Created Date (Newest)":
        filtered_items.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    elif filters["sort_by"] == "Created Date (Oldest)":
        filtered_items.sort(key=lambda x: x.get('created_at', ''))
    elif filters["sort_by"] == "Priority (High to Low)":
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        filtered_items.sort(key=lambda x: priority_order.get(x.get('priority', 'medium'), 2))
    elif filters["sort_by"] == "Due Date":
        filtered_items.sort(key=lambda x: x.get('due_date', '9999-12-31'))
    elif filters["sort_by"] == "Title A-Z":
        filtered_items.sort(key=lambda x: x.get('title', '').lower())
    
    return filtered_items

def render_work_items(work_items: List[Dict[str, Any]], view_mode: str):
    """Render work items in the specified view mode."""
    if not work_items:
        st.info("No work items match the current filters")
        return
    
    st.subheader(f"📋 Work Items ({len(work_items)} items)")
    
    if view_mode == "grid":
        render_work_item_grid(work_items, columns=2)
    
    elif view_mode == "table":
        render_work_item_table(work_items)
    
    else:  # list view
        for item in work_items:
            render_work_item_card(item, show_actions=True)

def handle_auto_refresh():
    """Handle auto-refresh functionality."""
    if st.session_state.auto_refresh:
        # Check if it's time to refresh
        now = datetime.now()
        time_since_refresh = (now - st.session_state.last_refresh_time).total_seconds()
        
        if time_since_refresh >= st.session_state.refresh_interval:
            st.session_state.last_refresh_time = now
            st.rerun()
        
        # Show countdown
        time_until_refresh = st.session_state.refresh_interval - time_since_refresh
        if time_until_refresh > 0:
            st.sidebar.info(f"⏱️ Next refresh in {int(time_until_refresh)}s")
        
        # Use Streamlit's auto-refresh mechanism
        time.sleep(1)
        st.rerun()

def main():
    """Main dashboard page function."""
    # Initialize session state
    initialize_session_state()
    
    # Render header
    render_header()
    
    # Check API status
    if not render_api_status():
        return
    
    # Manual refresh button
    if st.button("🔄 Refresh Now"):
        st.session_state.last_refresh_time = datetime.now()
        st.rerun()
    
    # Get work items from API
    work_items = get_api_data("work-items")
    
    if not work_items:
        st.warning("Unable to load work items from API")
        return
    
    # Render quick stats
    render_quick_stats(work_items)
    
    st.markdown("---")
    
    # Render filters
    filters = render_filters()
    
    # Apply filters
    filtered_items = apply_filters(work_items, filters)
    
    # Show filter results
    if len(filtered_items) != len(work_items):
        st.info(f"Showing {len(filtered_items)} of {len(work_items)} items")
    
    st.markdown("---")
    
    # Render work items in selected view mode
    render_work_items(filtered_items, st.session_state.dashboard_view_mode)
    
    # Handle auto-refresh
    if st.session_state.auto_refresh:
        handle_auto_refresh()

if __name__ == "__main__":
    main()
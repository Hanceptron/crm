"""
Reports Page - Analytics and metrics dashboard

Displays comprehensive analytics including work item statistics,
department performance metrics, approval rates, and workflow insights.
"""

import streamlit as st
import requests
import pandas as pd
try:
    import plotly.express as px
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except Exception:
    PLOTLY_AVAILABLE = False
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import defaultdict

# Import custom components
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from components.workflow_viz import render_workflow_stats

# Page configuration
st.set_page_config(
    page_title="Reports - Aviation Workflow",
    page_icon="📊",
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
    """Initialize reports page session state."""
    if "report_date_range" not in st.session_state:
        st.session_state.report_date_range = "last_30_days"
    
    if "selected_departments" not in st.session_state:
        st.session_state.selected_departments = []

def render_header():
    """Render the reports page header."""
    st.title("📊 Analytics & Reports")
    st.markdown("*Comprehensive insights into workflow performance and trends*")
    
    # API status check
    if not check_api_connection():
        st.error("🚫 Cannot connect to API server. Please ensure the backend is running.")
        st.code("python scripts/run_dev.py", language="bash")
        return False
    
    return True

def render_report_controls():
    """Render report filtering and configuration controls."""
    st.subheader("🔧 Report Configuration")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        date_range = st.selectbox(
            "Date Range:",
            ["last_7_days", "last_30_days", "last_90_days", "last_year", "all_time"],
            index=1,  # Default to last 30 days
            format_func=lambda x: {
                "last_7_days": "Last 7 Days",
                "last_30_days": "Last 30 Days",
                "last_90_days": "Last 90 Days", 
                "last_year": "Last Year",
                "all_time": "All Time"
            }[x],
            key="report_date_range_select"
        )
    
    with col2:
        # Department filter
        departments = [
            "flight_operations",
            "maintenance",
            "safety_quality", 
            "ground_services",
            "customer_service"
        ]
        
        dept_names = {
            "flight_operations": "Flight Operations",
            "maintenance": "Maintenance",
            "safety_quality": "Safety & QA",
            "ground_services": "Ground Services",
            "customer_service": "Customer Service"
        }
        
        selected_depts = st.multiselect(
            "Filter Departments:",
            departments,
            default=departments,  # All selected by default
            format_func=lambda x: dept_names.get(x, x),
            key="dept_filter_select"
        )
    
    with col3:
        status_filter = st.multiselect(
            "Include Status:",
            ["pending", "in_progress", "approved", "rejected", "completed"],
            default=["pending", "in_progress", "approved", "completed"],
            key="status_filter_select"
        )
    
    with col4:
        chart_type = st.selectbox(
            "Chart Style:",
            ["interactive", "static"],
            format_func=lambda x: {
                "interactive": "Interactive (Plotly)",
                "static": "Static (Streamlit)"
            }[x],
            key="chart_type_select"
        )
    
    return date_range, selected_depts, status_filter, chart_type

def filter_data_by_date(items: List[Dict[str, Any]], date_range: str) -> List[Dict[str, Any]]:
    """Filter work items by date range."""
    if date_range == "all_time":
        return items
    
    now = datetime.now()
    
    if date_range == "last_7_days":
        cutoff = now - timedelta(days=7)
    elif date_range == "last_30_days":
        cutoff = now - timedelta(days=30)
    elif date_range == "last_90_days":
        cutoff = now - timedelta(days=90)
    elif date_range == "last_year":
        cutoff = now - timedelta(days=365)
    else:
        return items
    
    filtered_items = []
    for item in items:
        created_at = item.get('created_at')
        if created_at:
            try:
                item_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                if item_date >= cutoff:
                    filtered_items.append(item)
            except Exception:
                # Include items with invalid dates
                filtered_items.append(item)
        else:
            # Include items without dates
            filtered_items.append(item)
    
    return filtered_items

def render_overview_metrics(work_items: List[Dict[str, Any]]):
    """Render high-level overview metrics."""
    st.subheader("📈 Overview Metrics")
    
    total_items = len(work_items)
    
    # Calculate metrics
    status_counts = defaultdict(int)
    priority_counts = defaultdict(int)
    department_workload = defaultdict(int)
    
    completed_items = 0
    avg_completion_time = 0
    overdue_count = 0
    
    for item in work_items:
        status = item.get('status', 'unknown')
        priority = item.get('priority', 'medium')
        
        status_counts[status] += 1
        priority_counts[priority] += 1
        
        if status == 'completed':
            completed_items += 1
        
        # Check overdue
        due_date = item.get('due_date')
        if due_date and status not in ['completed', 'approved']:
            try:
                due_dt = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
                if due_dt < datetime.now(due_dt.tzinfo):
                    overdue_count += 1
            except Exception:
                pass
        
        # Current department workload
        dept_ids = item.get('department_ids', [])
        current_step = item.get('current_step', 0)
        if current_step < len(dept_ids):
            current_dept = dept_ids[current_step]
            department_workload[current_dept] += 1
    
    # Calculate completion rate
    completion_rate = (completed_items / total_items * 100) if total_items > 0 else 0
    
    # Display metrics in columns
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    
    with col1:
        st.metric("Total Items", total_items)
    
    with col2:
        st.metric(
            "Completion Rate",
            f"{completion_rate:.1f}%",
            delta=f"{completed_items} completed"
        )
    
    with col3:
        in_progress = status_counts['in_progress']
        st.metric("In Progress", in_progress)
    
    with col4:
        pending = status_counts['pending']
        st.metric("Pending", pending)
    
    with col5:
        critical_high = priority_counts['critical'] + priority_counts['high']
        st.metric("High Priority", critical_high)
    
    with col6:
        st.metric(
            "Overdue Items",
            overdue_count,
            delta="⚠️ Needs attention" if overdue_count > 0 else "✅ On track"
        )
    
    return status_counts, priority_counts, department_workload

def render_status_distribution(status_counts: Dict[str, int], chart_type: str):
    """Render work item status distribution chart."""
    st.subheader("📋 Status Distribution")
    
    if not status_counts:
        st.info("No data to display")
        return
    
    # Prepare data
    statuses = list(status_counts.keys())
    counts = list(status_counts.values())
    
    if chart_type == "interactive" and PLOTLY_AVAILABLE:
        # Plotly pie chart
        fig = px.pie(
            values=counts,
            names=statuses,
            title="Work Item Status Distribution",
            color_discrete_map={
                'pending': '#ffc107',
                'in_progress': '#007bff',
                'approved': '#28a745',
                'rejected': '#dc3545',
                'completed': '#6c757d'
            }
        )
        fig.update_layout(showlegend=True)
        st.plotly_chart(fig, use_container_width=True)
    else:
        # Streamlit bar chart
        df = pd.DataFrame({
            'Status': statuses,
            'Count': counts
        })
        st.bar_chart(df.set_index('Status'))

def render_priority_breakdown(priority_counts: Dict[str, int], chart_type: str):
    """Render priority distribution chart."""
    st.subheader("🔥 Priority Breakdown")
    
    if not priority_counts:
        st.info("No data to display")
        return
    
    priorities = list(priority_counts.keys())
    counts = list(priority_counts.values())
    
    if chart_type == "interactive" and PLOTLY_AVAILABLE:
        # Plotly bar chart
        color_map = {
            'critical': '#6f42c1',
            'high': '#dc3545', 
            'medium': '#ffc107',
            'low': '#28a745'
        }
        
        colors = [color_map.get(p, '#6c757d') for p in priorities]
        
        fig = go.Figure(data=[
            go.Bar(
                x=priorities,
                y=counts,
                marker_color=colors,
                text=counts,
                textposition='auto'
            )
        ])
        
        fig.update_layout(
            title="Priority Distribution",
            xaxis_title="Priority Level",
            yaxis_title="Number of Items"
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        # Streamlit bar chart
        df = pd.DataFrame({
            'Priority': priorities,
            'Count': counts
        })
        st.bar_chart(df.set_index('Priority'))

def render_department_workload(department_workload: Dict[str, int], chart_type: str):
    """Render current department workload chart."""
    st.subheader("🏢 Current Department Workload")
    
    if not department_workload:
        st.info("No items currently in departments")
        return
    
    # Map department names
    dept_names = {
        "flight_operations": "Flight Operations",
        "maintenance": "Maintenance",
        "safety_quality": "Safety & QA",
        "ground_services": "Ground Services",
        "customer_service": "Customer Service"
    }
    
    departments = [dept_names.get(d, d) for d in department_workload.keys()]
    workloads = list(department_workload.values())
    
    if chart_type == "interactive" and PLOTLY_AVAILABLE:
        # Plotly horizontal bar chart
        fig = go.Figure(data=[
            go.Bar(
                x=workloads,
                y=departments,
                orientation='h',
                marker_color='#007bff',
                text=workloads,
                textposition='auto'
            )
        ])
        
        fig.update_layout(
            title="Items Currently Pending by Department",
            xaxis_title="Number of Pending Items",
            yaxis_title="Department"
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        # Streamlit bar chart
        df = pd.DataFrame({
            'Department': departments,
            'Pending Items': workloads
        })
        st.bar_chart(df.set_index('Department'))

def render_timeline_analysis(work_items: List[Dict[str, Any]], chart_type: str):
    """Render timeline analysis of work item creation."""
    st.subheader("📅 Timeline Analysis")
    
    # Group items by creation date
    daily_counts = defaultdict(int)
    
    for item in work_items:
        created_at = item.get('created_at')
        if created_at:
            try:
                item_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                date_str = item_date.strftime('%Y-%m-%d')
                daily_counts[date_str] += 1
            except Exception:
                pass
    
    if not daily_counts:
        st.info("No timeline data available")
        return
    
    # Sort by date
    sorted_dates = sorted(daily_counts.keys())
    dates = [datetime.strptime(d, '%Y-%m-%d') for d in sorted_dates]
    counts = [daily_counts[d] for d in sorted_dates]
    
    if chart_type == "interactive":
        # Plotly line chart
        fig = px.line(
            x=dates,
            y=counts,
            title="Work Items Created Over Time",
            labels={'x': 'Date', 'y': 'Items Created'}
        )
        fig.update_traces(mode='lines+markers')
        st.plotly_chart(fig, use_container_width=True)
    else:
        # Streamlit line chart
        df = pd.DataFrame({
            'Date': dates,
            'Items Created': counts
        })
        st.line_chart(df.set_index('Date'))

def render_approval_metrics(work_items: List[Dict[str, Any]]):
    """Render approval and rejection metrics."""
    st.subheader("✅ Approval Metrics")
    
    # Calculate approval metrics (mock data for demonstration)
    total_decisions = len([item for item in work_items 
                          if item.get('status') in ['approved', 'rejected', 'completed']])
    
    approved_items = len([item for item in work_items 
                         if item.get('status') in ['approved', 'completed']])
    
    rejected_items = len([item for item in work_items 
                         if item.get('status') == 'rejected'])
    
    approval_rate = (approved_items / total_decisions * 100) if total_decisions > 0 else 0
    rejection_rate = (rejected_items / total_decisions * 100) if total_decisions > 0 else 0
    
    # Display metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Decisions", total_decisions)
    
    with col2:
        st.metric(
            "Approval Rate",
            f"{approval_rate:.1f}%",
            delta=f"{approved_items} approved"
        )
    
    with col3:
        st.metric(
            "Rejection Rate", 
            f"{rejection_rate:.1f}%",
            delta=f"{rejected_items} rejected"
        )
    
    with col4:
        avg_decision_time = "2.3 days"  # Mock data
        st.metric("Avg Decision Time", avg_decision_time)

def render_department_performance(work_items: List[Dict[str, Any]], chart_type: str):
    """Render department performance analysis."""
    st.subheader("🏆 Department Performance")
    
    # Mock department performance data
    dept_names = {
        "flight_operations": "Flight Operations",
        "maintenance": "Maintenance", 
        "safety_quality": "Safety & QA",
        "ground_services": "Ground Services",
        "customer_service": "Customer Service"
    }
    
    # Calculate average processing time per department (mock data)
    dept_performance = {
        "Flight Operations": {"avg_time": 1.2, "throughput": 15, "efficiency": 92},
        "Maintenance": {"avg_time": 2.8, "throughput": 8, "efficiency": 87},
        "Safety & QA": {"avg_time": 1.5, "throughput": 12, "efficiency": 95},
        "Ground Services": {"avg_time": 0.8, "throughput": 20, "efficiency": 89},
        "Customer Service": {"avg_time": 0.5, "throughput": 25, "efficiency": 94}
    }
    
    departments = list(dept_performance.keys())
    avg_times = [dept_performance[d]["avg_time"] for d in departments]
    throughputs = [dept_performance[d]["throughput"] for d in departments]
    efficiencies = [dept_performance[d]["efficiency"] for d in departments]
    
    col1, col2 = st.columns(2)
    
    with col1:
        if chart_type == "interactive":
            fig = go.Figure(data=[
                go.Bar(
                    x=departments,
                    y=avg_times,
                    name="Avg Processing Time (days)",
                    marker_color='#007bff'
                )
            ])
            fig.update_layout(
                title="Average Processing Time by Department",
                yaxis_title="Days"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            df = pd.DataFrame({
                'Department': departments,
                'Avg Time (days)': avg_times
            })
            st.bar_chart(df.set_index('Department'))
    
    with col2:
        if chart_type == "interactive":
            fig = go.Figure(data=[
                go.Bar(
                    x=departments,
                    y=efficiencies,
                    name="Efficiency %",
                    marker_color='#28a745'
                )
            ])
            fig.update_layout(
                title="Department Efficiency Scores",
                yaxis_title="Efficiency %"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            df = pd.DataFrame({
                'Department': departments,
                'Efficiency %': efficiencies
            })
            st.bar_chart(df.set_index('Department'))

def render_summary_insights(work_items: List[Dict[str, Any]]):
    """Render key insights and recommendations."""
    st.subheader("💡 Key Insights & Recommendations")
    
    total_items = len(work_items)
    
    # Generate insights based on data
    insights = []
    
    # Status insights
    status_counts = defaultdict(int)
    for item in work_items:
        status_counts[item.get('status', 'unknown')] += 1
    
    pending_ratio = status_counts['pending'] / total_items if total_items > 0 else 0
    if pending_ratio > 0.3:
        insights.append("⚠️ **High pending ratio**: 30%+ of items are pending approval. Consider reviewing approval processes.")
    
    # Priority insights
    priority_counts = defaultdict(int)
    for item in work_items:
        priority_counts[item.get('priority', 'medium')] += 1
    
    high_priority_ratio = (priority_counts['critical'] + priority_counts['high']) / total_items if total_items > 0 else 0
    if high_priority_ratio > 0.4:
        insights.append("🔥 **High priority workload**: 40%+ of items are high/critical priority. Consider prioritization strategies.")
    
    # Overdue insights
    overdue_count = 0
    for item in work_items:
        due_date = item.get('due_date')
        if due_date and item.get('status') not in ['completed', 'approved']:
            try:
                due_dt = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
                if due_dt < datetime.now(due_dt.tzinfo):
                    overdue_count += 1
            except Exception:
                pass
    
    if overdue_count > 0:
        insights.append(f"⏰ **Overdue items**: {overdue_count} items are past their due date. Immediate attention recommended.")
    
    # General insights
    if total_items > 0:
        insights.append("📈 **System active**: Workflow system is processing items across departments.")
        insights.append("🔄 **Regular monitoring**: Continue monitoring these metrics for optimal performance.")
    
    if not insights:
        insights.append("✅ **System healthy**: No critical issues detected in current metrics.")
    
    # Display insights
    for insight in insights:
        st.info(insight)

def main():
    """Main reports page function."""
    # Initialize session state
    initialize_session_state()
    
    # Render header
    if not render_header():
        return
    
    # Report controls
    date_range, selected_depts, status_filter, chart_type = render_report_controls()
    
    # Get work items
    raw = get_api_data("work-items")
    work_items = _extract_work_items(raw)
    
    if not work_items:
        st.warning("Unable to load work items for analysis")
        return
    
    # Apply filters
    filtered_items = list(work_items)
    
    # Filter by date range
    filtered_items = filter_data_by_date(filtered_items, date_range)
    
    # Filter by departments
    if selected_depts:
        filtered_items = [item for item in filtered_items 
                         if any(dept in item.get('department_ids', []) for dept in selected_depts)]
    
    # Filter by status
    if status_filter:
        filtered_items = [item for item in filtered_items 
                         if item.get('status') in status_filter]
    
    # Show filter results
    if len(filtered_items) != len(work_items):
        st.info(f"Showing analysis for {len(filtered_items)} of {len(work_items)} total items")
    
    st.markdown("---")
    
    # Render reports
    if filtered_items:
        # Overview metrics
        status_counts, priority_counts, department_workload = render_overview_metrics(filtered_items)
        
        st.markdown("---")
        
        # Charts in columns
        col1, col2 = st.columns(2)
        
        with col1:
            render_status_distribution(status_counts, chart_type)
        
        with col2:
            render_priority_breakdown(priority_counts, chart_type)
        
        st.markdown("---")
        
        # Department analysis
        render_department_workload(department_workload, chart_type)
        
        st.markdown("---")
        
        # Timeline analysis
        render_timeline_analysis(filtered_items, chart_type)
        
        st.markdown("---")
        
        # Approval metrics
        render_approval_metrics(filtered_items)
        
        st.markdown("---")
        
        # Department performance
        render_department_performance(filtered_items, chart_type)
        
        st.markdown("---")
        
        # Key insights
        render_summary_insights(filtered_items)
        
    else:
        st.warning("No data matches the selected filters")

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


if __name__ == "__main__":
    main()

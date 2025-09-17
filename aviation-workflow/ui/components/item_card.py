"""
Work Item Card Component

Reusable component for displaying work items with consistent formatting,
action buttons, and expandable details sections.
"""

import streamlit as st
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from .workflow_viz import render_compact_workflow_progress


def format_priority(priority: str) -> str:
    """Format priority with appropriate styling."""
    priority_styles = {
        "critical": "🔴 **Critical**",
        "high": "🟠 **High**", 
        "medium": "🟡 **Medium**",
        "low": "🟢 **Low**"
    }
    return priority_styles.get(priority.lower(), f"❓ **{priority.title()}**")


def format_status(status: str) -> str:
    """Format status with appropriate styling."""
    status_styles = {
        "pending": "⏸️ **Pending**",
        "in_progress": "🔄 **In Progress**",
        "approved": "✅ **Approved**",
        "rejected": "❌ **Rejected**",
        "completed": "✅ **Completed**"
    }
    return status_styles.get(status.lower(), f"❓ **{status.title()}**")


def format_datetime(dt_string: str) -> str:
    """Format datetime string for display."""
    if not dt_string:
        return "N/A"
    
    try:
        dt = datetime.fromisoformat(dt_string.replace('Z', '+00:00'))
        now = datetime.now(dt.tzinfo)
        
        # Calculate time difference
        diff = now - dt
        
        if diff.days > 0:
            return f"{diff.days} days ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hours ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} minutes ago"
        else:
            return "Just now"
    except Exception:
        return dt_string


def get_priority_css_class(priority: str) -> str:
    """Get CSS class for priority styling."""
    return f"priority-{priority.lower()}"


def render_work_item_card(
    work_item: Dict[str, Any],
    show_actions: bool = True,
    show_approval_actions: bool = False,
    compact: bool = False
):
    """
    Render a work item card with all relevant information.
    
    Args:
        work_item: Work item data dictionary
        show_actions: Whether to show action buttons
        show_approval_actions: Whether to show approval-specific actions
        compact: Whether to render in compact mode
    """
    
    # Extract work item data
    item_id = work_item.get('id', 'unknown')
    title = work_item.get('title', 'Untitled')
    description = work_item.get('description', '')
    status = work_item.get('status', 'unknown')
    priority = work_item.get('priority', 'medium')
    department_ids = work_item.get('department_ids', [])
    current_step = work_item.get('current_step', 0)
    created_by = work_item.get('created_by', 'Unknown')
    assigned_to = work_item.get('assigned_to', 'Unassigned')
    created_at = work_item.get('created_at', '')
    updated_at = work_item.get('updated_at', '')
    due_date = work_item.get('due_date', '')
    metadata = work_item.get('item_metadata', {}) or work_item.get('metadata', {})
    
    # Create card container with priority styling
    priority_class = get_priority_css_class(priority)
    
    with st.container():
        # Card header
        col1, col2, col3 = st.columns([3, 1, 1])
        
        with col1:
            st.markdown(f"**{title}**")
            if compact:
                st.caption(f"ID: {item_id[:8]}...")
            else:
                st.caption(f"Work Item ID: {item_id}")
        
        with col2:
            st.markdown(format_status(status))
        
        with col3:
            st.markdown(format_priority(priority))
        
        # Workflow progress (compact mode)
        if department_ids:
            if compact:
                render_compact_workflow_progress(department_ids, current_step, status)
            else:
                # Show current department
                if current_step < len(department_ids):
                    current_dept = department_ids[current_step]
                    dept_display = current_dept.replace('_', ' ').title()
                    st.info(f"📍 Current Department: **{dept_display}** (Step {current_step + 1}/{len(department_ids)})")
        
        # Description (if not compact)
        if not compact and description:
            with st.expander("📝 Description"):
                st.write(description)
        
        # Details section
        if not compact:
            col1, col2 = st.columns(2)
            
            with col1:
                st.caption(f"**Created:** {format_datetime(created_at)}")
                st.caption(f"**Created by:** {created_by}")
                if due_date:
                    st.caption(f"**Due date:** {format_datetime(due_date)}")
            
            with col2:
                st.caption(f"**Last updated:** {format_datetime(updated_at)}")
                st.caption(f"**Assigned to:** {assigned_to}")
        
        # Metadata section
        if not compact and metadata:
            with st.expander("ℹ️ Additional Information"):
                # Display relevant metadata
                if metadata.get('template_name'):
                    st.write(f"**Template:** {metadata['template_name']}")
                
                if metadata.get('aircraft_tail'):
                    st.write(f"**Aircraft:** {metadata['aircraft_tail']}")
                
                if metadata.get('location'):
                    st.write(f"**Location:** {metadata['location']}")
                
                if metadata.get('estimated_hours'):
                    st.write(f"**Estimated Hours:** {metadata['estimated_hours']}")
                
                # Show all metadata in expandable JSON
                if st.checkbox("Show raw metadata", key=f"metadata_{item_id}"):
                    st.json(metadata)
        
        # Action buttons
        if show_actions:
            action_col1, action_col2, action_col3, action_col4 = st.columns(4)
            
            with action_col1:
                if st.button("👁️ View Details", key=f"view_{item_id}"):
                    st.session_state.selected_item = item_id
                    st.info(f"Selected item: {title}")
            
            with action_col2:
                if st.button("💬 Comments", key=f"comments_{item_id}"):
                    st.info("Comments panel would open here")
            
            with action_col3:
                if st.button("📊 History", key=f"history_{item_id}"):
                    st.info("Approval history would be shown here")
            
            with action_col4:
                if st.button("✏️ Edit", key=f"edit_{item_id}"):
                    st.info("Edit form would open here")
        
        # Approval actions (if enabled)
        if show_approval_actions:
            st.markdown("---")
            st.subheader("⚖️ Approval Actions")
            
            approval_col1, approval_col2, approval_col3 = st.columns(3)
            
            with approval_col1:
                if st.button(f"✅ Approve", key=f"approve_action_{item_id}"):
                    st.success(f"Item approved and moved to next step")
                    st.balloons()
            
            with approval_col2:
                if st.button(f"❌ Reject", key=f"reject_action_{item_id}"):
                    # Show rejection reason input
                    with st.form(f"reject_form_{item_id}"):
                        reason = st.text_area("Rejection reason:", placeholder="Please provide a reason for rejection...")
                        submitted = st.form_submit_button("Confirm Rejection")
                        
                        if submitted and reason:
                            st.error(f"Item rejected: {reason}")
                            st.info("Item moved back to previous step")
            
            with approval_col3:
                if st.button(f"❓ Request Info", key=f"info_request_{item_id}"):
                    # Show information request form
                    with st.form(f"info_form_{item_id}"):
                        info_request = st.text_area("Information needed:", 
                                                  placeholder="What additional information do you need?")
                        submitted = st.form_submit_button("Send Request")
                        
                        if submitted and info_request:
                            st.warning(f"Information requested: {info_request}")
                            st.info("Request sent to item creator")
        
        # Add separator line
        st.markdown("---")


def render_work_item_summary(work_items: List[Dict[str, Any]]):
    """
    Render a summary of work items with key statistics.
    
    Args:
        work_items: List of work item dictionaries
    """
    if not work_items:
        st.info("No work items to display")
        return
    
    # Calculate summary statistics
    total_items = len(work_items)
    status_counts = {}
    priority_counts = {}
    department_workload = {}
    
    for item in work_items:
        status = item.get('status', 'unknown')
        priority = item.get('priority', 'unknown')
        department_ids = item.get('department_ids', [])
        current_step = item.get('current_step', 0)
        
        status_counts[status] = status_counts.get(status, 0) + 1
        priority_counts[priority] = priority_counts.get(priority, 0) + 1
        
        # Current department workload
        if current_step < len(department_ids):
            current_dept = department_ids[current_step]
            department_workload[current_dept] = department_workload.get(current_dept, 0) + 1
    
    # Display summary
    st.subheader(f"📊 Work Items Summary ({total_items} items)")
    
    # Status summary
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        pending_count = status_counts.get('pending', 0)
        st.metric("Pending", pending_count)
    
    with col2:
        in_progress_count = status_counts.get('in_progress', 0)
        st.metric("In Progress", in_progress_count)
    
    with col3:
        approved_count = status_counts.get('approved', 0)
        st.metric("Approved", approved_count)
    
    with col4:
        completed_count = status_counts.get('completed', 0)
        st.metric("Completed", completed_count)
    
    # Priority breakdown
    st.subheader("Priority Breakdown")
    priority_col1, priority_col2, priority_col3, priority_col4 = st.columns(4)
    
    with priority_col1:
        critical_count = priority_counts.get('critical', 0)
        st.metric("🔴 Critical", critical_count)
    
    with priority_col2:
        high_count = priority_counts.get('high', 0)
        st.metric("🟠 High", high_count)
    
    with priority_col3:
        medium_count = priority_counts.get('medium', 0)
        st.metric("🟡 Medium", medium_count)
    
    with priority_col4:
        low_count = priority_counts.get('low', 0)
        st.metric("🟢 Low", low_count)
    
    # Department workload
    if department_workload:
        st.subheader("Current Department Workload")
        
        # Department name mapping
        dept_names = {
            "flight_operations": "Flight Operations",
            "maintenance": "Maintenance",
            "safety_quality": "Safety & QA",
            "ground_services": "Ground Services",
            "customer_service": "Customer Service"
        }
        
        workload_cols = st.columns(len(department_workload))
        
        for i, (dept_id, count) in enumerate(department_workload.items()):
            with workload_cols[i]:
                dept_name = dept_names.get(dept_id, dept_id.replace('_', ' ').title())
                st.metric(dept_name, count)


def render_work_item_grid(work_items: List[Dict[str, Any]], columns: int = 2):
    """
    Render work items in a grid layout.
    
    Args:
        work_items: List of work item dictionaries
        columns: Number of columns in the grid
    """
    if not work_items:
        st.info("No work items to display")
        return
    
    # Create grid layout
    cols = st.columns(columns)
    
    for i, work_item in enumerate(work_items):
        col_index = i % columns
        
        with cols[col_index]:
            with st.container():
                # Use compact card rendering for grid view
                render_work_item_card(work_item, compact=True, show_actions=True)


def render_work_item_table(work_items: List[Dict[str, Any]]):
    """
    Render work items in a table format.
    
    Args:
        work_items: List of work item dictionaries
    """
    if not work_items:
        st.info("No work items to display")
        return
    
    # Prepare table data
    table_data = []
    
    for item in work_items:
        dept_ids = item.get('department_ids', [])
        current_step = item.get('current_step', 0)
        
        # Current department
        current_dept = "N/A"
        if current_step < len(dept_ids):
            current_dept = dept_ids[current_step].replace('_', ' ').title()
        
        table_data.append({
            "Title": item.get('title', 'Untitled')[:50] + ("..." if len(item.get('title', '')) > 50 else ""),
            "Status": item.get('status', 'unknown').title(),
            "Priority": item.get('priority', 'medium').title(),
            "Current Department": current_dept,
            "Step": f"{current_step + 1}/{len(dept_ids)}" if dept_ids else "N/A",
            "Created By": item.get('created_by', 'Unknown'),
            "Created": format_datetime(item.get('created_at', ''))
        })
    
    # Display table
    import pandas as pd
    df = pd.DataFrame(table_data)
    st.dataframe(df, use_container_width=True)
    
    # Add download button
    csv = df.to_csv(index=False)
    st.download_button(
        label="📥 Download CSV",
        data=csv,
        file_name=f"work_items_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv"
    )
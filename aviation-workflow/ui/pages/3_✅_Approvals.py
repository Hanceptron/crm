"""
Approvals Page - Manage pending approvals and workflow actions

Displays items pending approval for the current user, provides approval/rejection
interfaces, shows item details and history, and includes bulk approval functionality.
"""

import streamlit as st
import requests
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

# Import custom components
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from components.workflow_viz import render_workflow_progress, render_workflow_timeline
from components.item_card import render_work_item_card

# Page configuration
st.set_page_config(
    page_title="Approvals - Aviation Workflow",
    page_icon="✅",
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

def post_api_data(endpoint: str, data: Dict) -> Optional[Dict]:
    """Post data to API endpoint with error handling."""
    try:
        response = requests.post(f"{API_URL}/{endpoint}", json=data, timeout=10)
        if response.status_code in [200, 201]:
            return response.json()
        else:
            st.error(f"API Error {response.status_code}: {response.text}")
            return None
    except requests.exceptions.RequestException as e:
        st.error(f"Connection error: {str(e)}")
        return None

def initialize_session_state():
    """Initialize approvals page session state."""
    if "current_user_dept" not in st.session_state:
        st.session_state.current_user_dept = "flight_operations"
    
    if "selected_items_bulk" not in st.session_state:
        st.session_state.selected_items_bulk = []
    
    if "approval_filter" not in st.session_state:
        st.session_state.approval_filter = "all"
    
    if "show_item_details" not in st.session_state:
        st.session_state.show_item_details = {}

def render_header():
    """Render the approvals page header."""
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.title("✅ Approval Center")
        st.markdown("*Manage pending approvals and workflow actions*")
    
    with col2:
        # Department selector
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
        
        selected_dept = st.selectbox(
            "Acting as Department:",
            departments,
            index=departments.index(st.session_state.current_user_dept),
            format_func=lambda x: dept_names.get(x, x),
            key="dept_selector"
        )
        
        if selected_dept != st.session_state.current_user_dept:
            st.session_state.current_user_dept = selected_dept
            st.rerun()
    
    # API status check
    if not check_api_connection():
        st.error("🚫 Cannot connect to API server. Please ensure the backend is running.")
        st.code("python scripts/run_dev.py", language="bash")
        return False
    
    return True

def get_pending_approvals() -> List[Dict[str, Any]]:
    """Get work items pending approval for current department."""
    work_items = get_api_data("work-items")
    
    if not work_items:
        return []
    
    # Filter items pending in current user's department
    pending_approvals = []
    current_dept = st.session_state.current_user_dept
    
    for item in work_items:
        dept_ids = item.get('department_ids', [])
        current_step = item.get('current_step', 0)
        status = item.get('status', '')
        
        # Check if item is at user's department step and pending approval
        if (current_step < len(dept_ids) and 
            dept_ids[current_step] == current_dept and
            status in ['pending', 'in_progress']):
            pending_approvals.append(item)
    
    return pending_approvals

def render_approval_stats(pending_items: List[Dict[str, Any]]):
    """Render approval statistics."""
    total_pending = len(pending_items)
    
    # Calculate priority breakdown
    priority_counts = {}
    overdue_count = 0
    
    for item in pending_items:
        priority = item.get('priority', 'medium')
        priority_counts[priority] = priority_counts.get(priority, 0) + 1
        
        # Check if overdue
        due_date = item.get('due_date')
        if due_date:
            try:
                due_dt = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
                if due_dt < datetime.now(due_dt.tzinfo):
                    overdue_count += 1
            except Exception:
                pass
    
    # Display metrics
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Total Pending", total_pending)
    
    with col2:
        critical_count = priority_counts.get('critical', 0)
        st.metric("🔴 Critical", critical_count)
    
    with col3:
        high_count = priority_counts.get('high', 0)
        st.metric("🟠 High", high_count)
    
    with col4:
        medium_count = priority_counts.get('medium', 0)
        st.metric("🟡 Medium", medium_count)
    
    with col5:
        st.metric("⚠️ Overdue", overdue_count)

def render_approval_filters():
    """Render filters for approval items."""
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        filter_type = st.selectbox(
            "Filter by:",
            ["all", "priority", "overdue", "recent"],
            format_func=lambda x: {
                "all": "All Items",
                "priority": "High Priority",
                "overdue": "Overdue Items", 
                "recent": "Recent Items"
            }[x],
            key="approval_filter_select"
        )
    
    with col2:
        sort_by = st.selectbox(
            "Sort by:",
            ["due_date", "priority", "created_date", "title"],
            format_func=lambda x: {
                "due_date": "Due Date",
                "priority": "Priority",
                "created_date": "Created Date",
                "title": "Title"
            }[x],
            key="approval_sort_select"
        )
    
    with col3:
        view_mode = st.selectbox(
            "View:",
            ["detailed", "compact", "table"],
            format_func=lambda x: {
                "detailed": "Detailed Cards",
                "compact": "Compact View",
                "table": "Table View"
            }[x],
            key="approval_view_select"
        )
    
    with col4:
        # Bulk selection toggle
        bulk_mode = st.checkbox("Bulk Selection", key="bulk_mode_toggle")
    
    return filter_type, sort_by, view_mode, bulk_mode

def apply_approval_filters(items: List[Dict[str, Any]], filter_type: str, sort_by: str) -> List[Dict[str, Any]]:
    """Apply filters and sorting to approval items."""
    filtered_items = items.copy()
    
    # Apply filters
    if filter_type == "priority":
        filtered_items = [item for item in filtered_items 
                         if item.get('priority') in ['critical', 'high']]
    
    elif filter_type == "overdue":
        now = datetime.now()
        overdue_items = []
        for item in filtered_items:
            due_date = item.get('due_date')
            if due_date:
                try:
                    due_dt = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
                    if due_dt < now:
                        overdue_items.append(item)
                except Exception:
                    pass
        filtered_items = overdue_items
    
    elif filter_type == "recent":
        # Items created in last 24 hours
        cutoff = datetime.now() - timedelta(days=1)
        filtered_items = [item for item in filtered_items 
                         if item.get('created_at') and 
                         datetime.fromisoformat(item['created_at'].replace('Z', '+00:00')) > cutoff]
    
    # Apply sorting
    if sort_by == "due_date":
        filtered_items.sort(key=lambda x: x.get('due_date', '9999-12-31'))
    elif sort_by == "priority":
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        filtered_items.sort(key=lambda x: priority_order.get(x.get('priority', 'medium'), 2))
    elif sort_by == "created_date":
        filtered_items.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    elif sort_by == "title":
        filtered_items.sort(key=lambda x: x.get('title', '').lower())
    
    return filtered_items

def render_approval_action(item_id: str, title: str):
    """Render approval action buttons and forms."""
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("✅ Approve", key=f"approve_{item_id}", type="primary"):
            # Approval form
            with st.form(f"approve_form_{item_id}"):
                st.subheader(f"Approve: {title}")
                
                comment = st.text_area(
                    "Approval Comment (optional):",
                    placeholder="Add any comments about this approval...",
                    key=f"approve_comment_{item_id}"
                )
                
                next_action = st.selectbox(
                    "Next Action:",
                    ["proceed_to_next", "complete_workflow", "reassign"],
                    format_func=lambda x: {
                        "proceed_to_next": "Proceed to Next Department",
                        "complete_workflow": "Mark as Completed",
                        "reassign": "Reassign to Different Department"
                    }[x],
                    key=f"next_action_{item_id}"
                )
                
                submitted = st.form_submit_button("Confirm Approval")
                
                if submitted:
                    # Mock API call for approval
                    approval_data = {
                        "item_id": item_id,
                        "action": "approve",
                        "comment": comment,
                        "next_action": next_action,
                        "approved_by": f"user@{st.session_state.current_user_dept}.com",
                        "department": st.session_state.current_user_dept
                    }
                    
                    # In real implementation, would call API
                    st.success("✅ Item approved successfully!")
                    st.balloons()
                    
                    # Show what happens next
                    if next_action == "proceed_to_next":
                        st.info("📤 Item moved to next department in workflow")
                    elif next_action == "complete_workflow":
                        st.info("🏁 Workflow completed")
                    else:
                        st.info("🔄 Item reassigned")
    
    with col2:
        if st.button("❌ Reject", key=f"reject_{item_id}"):
            # Rejection form
            with st.form(f"reject_form_{item_id}"):
                st.subheader(f"Reject: {title}")
                
                reason = st.text_area(
                    "Rejection Reason *:",
                    placeholder="Please provide a detailed reason for rejection...",
                    key=f"reject_reason_{item_id}"
                )
                
                return_to = st.selectbox(
                    "Return to:",
                    ["previous_step", "creator", "specific_department"],
                    format_func=lambda x: {
                        "previous_step": "Previous Department",
                        "creator": "Original Creator",
                        "specific_department": "Specific Department"
                    }[x],
                    key=f"return_to_{item_id}"
                )
                
                submitted = st.form_submit_button("Confirm Rejection")
                
                if submitted:
                    if not reason:
                        st.error("Please provide a rejection reason")
                    else:
                        # Mock API call for rejection
                        rejection_data = {
                            "item_id": item_id,
                            "action": "reject",
                            "reason": reason,
                            "return_to": return_to,
                            "rejected_by": f"user@{st.session_state.current_user_dept}.com",
                            "department": st.session_state.current_user_dept
                        }
                        
                        st.error("❌ Item rejected and returned")
                        st.info(f"📤 Item returned to: {return_to}")
    
    with col3:
        if st.button("❓ Request Info", key=f"request_info_{item_id}"):
            # Information request form
            with st.form(f"info_request_form_{item_id}"):
                st.subheader(f"Request Information: {title}")
                
                info_request = st.text_area(
                    "Information Needed *:",
                    placeholder="What additional information do you need to make a decision?",
                    key=f"info_request_{item_id}"
                )
                
                urgency = st.selectbox(
                    "Urgency:",
                    ["normal", "urgent", "blocking"],
                    format_func=lambda x: {
                        "normal": "Normal",
                        "urgent": "Urgent",
                        "blocking": "Blocking Approval"
                    }[x],
                    key=f"urgency_{item_id}"
                )
                
                submitted = st.form_submit_button("Send Request")
                
                if submitted:
                    if not info_request:
                        st.error("Please specify what information is needed")
                    else:
                        st.warning("📨 Information request sent")
                        st.info("Item remains in queue pending additional information")

def render_bulk_approval_interface(selected_items: List[str], all_items: List[Dict[str, Any]]):
    """Render bulk approval interface."""
    if not selected_items:
        st.info("Select items above to use bulk approval")
        return
    
    st.subheader(f"🔄 Bulk Actions ({len(selected_items)} items selected)")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("✅ Bulk Approve", type="primary"):
            with st.form("bulk_approve_form"):
                st.write(f"Approve {len(selected_items)} selected items:")
                
                # Show selected items
                for item_id in selected_items:
                    item = next((i for i in all_items if i['id'] == item_id), None)
                    if item:
                        st.write(f"• {item.get('title', 'Unknown')}")
                
                bulk_comment = st.text_area(
                    "Bulk Approval Comment:",
                    placeholder="Comment that will be added to all approved items..."
                )
                
                submitted = st.form_submit_button("Confirm Bulk Approval")
                
                if submitted:
                    st.success(f"✅ {len(selected_items)} items approved!")
                    st.session_state.selected_items_bulk = []
                    st.rerun()
    
    with col2:
        if st.button("❌ Bulk Reject"):
            with st.form("bulk_reject_form"):
                st.write(f"Reject {len(selected_items)} selected items:")
                
                bulk_reason = st.text_area(
                    "Bulk Rejection Reason *:",
                    placeholder="Reason that will be applied to all rejected items..."
                )
                
                submitted = st.form_submit_button("Confirm Bulk Rejection")
                
                if submitted:
                    if not bulk_reason:
                        st.error("Please provide a rejection reason")
                    else:
                        st.error(f"❌ {len(selected_items)} items rejected!")
                        st.session_state.selected_items_bulk = []
                        st.rerun()
    
    with col3:
        if st.button("🗑️ Clear Selection"):
            st.session_state.selected_items_bulk = []
            st.rerun()

def render_approval_items(items: List[Dict[str, Any]], view_mode: str, bulk_mode: bool):
    """Render approval items in specified view mode."""
    if not items:
        st.info("🎉 No items pending approval in your department!")
        st.balloons()
        return
    
    if view_mode == "table":
        render_approval_table(items, bulk_mode)
    else:
        render_approval_cards(items, view_mode, bulk_mode)

def render_approval_table(items: List[Dict[str, Any]], bulk_mode: bool):
    """Render approvals in table format."""
    # Prepare table data
    table_data = []
    
    for item in items:
        dept_ids = item.get('department_ids', [])
        current_step = item.get('current_step', 0)
        
        table_data.append({
            "Select": False if not bulk_mode else item['id'] in st.session_state.selected_items_bulk,
            "Title": item.get('title', 'Untitled'),
            "Priority": item.get('priority', 'medium').title(),
            "Created": item.get('created_at', '')[:10] if item.get('created_at') else 'N/A',
            "Due Date": item.get('due_date', '')[:10] if item.get('due_date') else 'N/A',
            "Created By": item.get('created_by', 'Unknown'),
            "Step": f"{current_step + 1}/{len(dept_ids)}" if dept_ids else "N/A",
            "ID": item['id']
        })
    
    # Display editable dataframe for bulk selection
    if bulk_mode:
        import pandas as pd
        df = pd.DataFrame(table_data)
        
        edited_df = st.data_editor(
            df,
            column_config={
                "Select": st.column_config.CheckboxColumn(
                    "Select",
                    help="Select items for bulk actions",
                    default=False,
                )
            },
            disabled=["Title", "Priority", "Created", "Due Date", "Created By", "Step", "ID"],
            hide_index=True,
            use_container_width=True
        )
        
        # Update selected items
        selected_rows = edited_df[edited_df["Select"] == True]
        st.session_state.selected_items_bulk = selected_rows["ID"].tolist()
    
    else:
        import pandas as pd
        df = pd.DataFrame(table_data)
        del df["Select"]  # Remove select column if not in bulk mode
        st.dataframe(df, use_container_width=True)

def render_approval_cards(items: List[Dict[str, Any]], view_mode: str, bulk_mode: bool):
    """Render approvals as cards."""
    for item in items:
        item_id = item['id']
        
        with st.container():
            # Bulk selection checkbox
            if bulk_mode:
                col1, col2 = st.columns([0.1, 0.9])
                with col1:
                    is_selected = st.checkbox(
                        "",
                        value=item_id in st.session_state.selected_items_bulk,
                        key=f"bulk_select_{item_id}"
                    )
                    
                    if is_selected and item_id not in st.session_state.selected_items_bulk:
                        st.session_state.selected_items_bulk.append(item_id)
                    elif not is_selected and item_id in st.session_state.selected_items_bulk:
                        st.session_state.selected_items_bulk.remove(item_id)
                
                with col2:
                    render_single_approval_card(item, view_mode)
            else:
                render_single_approval_card(item, view_mode)
            
            st.markdown("---")

def render_single_approval_card(item: Dict[str, Any], view_mode: str):
    """Render a single approval card."""
    item_id = item['id']
    title = item.get('title', 'Untitled')
    
    # Card header
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.subheader(title)
        st.caption(f"ID: {item_id[:8]}...")
    
    with col2:
        priority = item.get('priority', 'medium')
        priority_colors = {
            "critical": "🔴",
            "high": "🟠", 
            "medium": "🟡",
            "low": "🟢"
        }
        st.write(f"{priority_colors.get(priority, '❓')} **{priority.title()}**")
    
    with col3:
        due_date = item.get('due_date', '')
        if due_date:
            st.caption(f"Due: {due_date[:10]}")
    
    # Item details (if detailed view)
    if view_mode == "detailed":
        col1, col2 = st.columns(2)
        
        with col1:
            st.write(f"**Description:** {item.get('description', 'N/A')}")
            st.write(f"**Created by:** {item.get('created_by', 'Unknown')}")
        
        with col2:
            st.write(f"**Status:** {item.get('status', 'unknown')}")
            st.write(f"**Created:** {item.get('created_at', 'N/A')[:10]}")
        
        # Workflow progress
        dept_ids = item.get('department_ids', [])
        current_step = item.get('current_step', 0)
        
        if dept_ids:
            with st.expander("🔄 Workflow Progress"):
                render_workflow_progress(dept_ids, current_step, item.get('status', 'pending'))
        
        # Item metadata
        metadata = item.get('item_metadata', {}) or item.get('metadata', {})
        if metadata:
            with st.expander("ℹ️ Additional Details"):
                for key, value in metadata.items():
                    if value:
                        st.write(f"**{key.replace('_', ' ').title()}:** {value}")
    
    # Approval actions
    render_approval_action(item_id, title)

def main():
    """Main approvals page function."""
    # Initialize session state
    initialize_session_state()
    
    # Render header
    if not render_header():
        return
    
    # Get pending approvals
    pending_items = get_pending_approvals()
    
    # Department info
    dept_names = {
        "flight_operations": "Flight Operations",
        "maintenance": "Maintenance", 
        "safety_quality": "Safety & QA",
        "ground_services": "Ground Services",
        "customer_service": "Customer Service"
    }
    
    current_dept_name = dept_names.get(st.session_state.current_user_dept, 
                                      st.session_state.current_user_dept)
    
    st.info(f"📋 Showing items pending approval in **{current_dept_name}** department")
    
    # Approval statistics
    render_approval_stats(pending_items)
    
    st.markdown("---")
    
    # Filters and view controls
    filter_type, sort_by, view_mode, bulk_mode = render_approval_filters()
    
    # Apply filters
    filtered_items = apply_approval_filters(pending_items, filter_type, sort_by)
    
    # Show filter results
    if len(filtered_items) != len(pending_items):
        st.info(f"Showing {len(filtered_items)} of {len(pending_items)} pending items")
    
    # Bulk approval interface
    if bulk_mode:
        render_bulk_approval_interface(st.session_state.selected_items_bulk, filtered_items)
        st.markdown("---")
    
    # Render approval items
    render_approval_items(filtered_items, view_mode, bulk_mode)

if __name__ == "__main__":
    main()
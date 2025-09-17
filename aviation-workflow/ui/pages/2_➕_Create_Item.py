"""
Create Item Page - Form for creating new work items

Provides a comprehensive form for creating work items with template selection,
custom department sequences, and all required fields.
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

from components.workflow_viz import render_workflow_progress

# Page configuration
st.set_page_config(
    page_title="Create Item - Aviation Workflow",
    page_icon="➕",
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
    """Initialize create item session state."""
    if "create_form_data" not in st.session_state:
        st.session_state.create_form_data = {}
    
    if "selected_template" not in st.session_state:
        st.session_state.selected_template = None
    
    if "custom_departments" not in st.session_state:
        st.session_state.custom_departments = []
    
    if "form_mode" not in st.session_state:
        st.session_state.form_mode = "template"  # or "custom"

def render_header():
    """Render the create item header."""
    st.title("➕ Create New Work Item")
    st.markdown("*Create a new work item and assign it to a workflow*")
    
    # API status check
    if not check_api_connection():
        st.error("🚫 Cannot connect to API server. Please ensure the backend is running.")
        st.code("python scripts/run_dev.py", language="bash")
        return False
    
    return True

def render_template_selector():
    """Render template selection interface."""
    st.subheader("📋 Choose Workflow Template")
    
    # Get available templates
    templates = get_api_data("templates")
    
    if not templates:
        st.warning("No workflow templates available")
        return None
    
    # Template selection
    template_options = ["Create Custom Workflow"] + [t['display_name'] for t in templates]
    
    selected_option = st.selectbox(
        "Select a template or create custom workflow:",
        template_options,
        key="template_selector"
    )
    
    if selected_option == "Create Custom Workflow":
        st.session_state.form_mode = "custom"
        st.session_state.selected_template = None
        return None
    else:
        st.session_state.form_mode = "template"
        # Find selected template
        selected_template = next(
            (t for t in templates if t['display_name'] == selected_option), 
            None
        )
        st.session_state.selected_template = selected_template
        
        if selected_template:
            # Show template details
            col1, col2 = st.columns(2)
            
            with col1:
                st.info(f"**Description:** {selected_template.get('description', 'N/A')}")
                st.info(f"**Category:** {selected_template.get('category', 'N/A')}")
            
            with col2:
                dept_sequence = selected_template.get('department_sequence', [])
                if dept_sequence:
                    st.info(f"**Department Flow:** {' → '.join(dept_sequence)}")
                    
                    # Preview workflow
                    with st.expander("🔍 Preview Workflow"):
                        render_workflow_progress(dept_sequence, 0, "pending")
        
        return selected_template

def render_custom_department_builder():
    """Render custom department sequence builder."""
    st.subheader("🔧 Build Custom Workflow")
    
    # Get available departments
    departments = get_api_data("departments")
    
    if not departments:
        st.warning("No departments available")
        return []
    
    # Department selection
    available_departments = {dept['name']: dept['display_name'] for dept in departments}
    
    st.write("**Step 1: Select Departments**")
    st.caption("Choose departments and arrange them in the order items should flow through")
    
    # Multi-select for departments
    selected_dept_names = st.multiselect(
        "Choose departments:",
        list(available_departments.keys()),
        format_func=lambda x: available_departments[x],
        key="dept_multiselect"
    )
    
    if selected_dept_names:
        st.write("**Step 2: Arrange Order**")
        st.caption("Drag and drop to reorder (use selectbox for now)")
        
        # For now, use selectbox to reorder - in production could use drag-and-drop
        ordered_departments = []
        for i in range(len(selected_dept_names)):
            remaining_depts = [d for d in selected_dept_names if d not in ordered_departments]
            if remaining_depts:
                next_dept = st.selectbox(
                    f"Department {i + 1}:",
                    remaining_depts,
                    format_func=lambda x: available_departments[x],
                    key=f"dept_order_{i}"
                )
                ordered_departments.append(next_dept)
        
        st.session_state.custom_departments = ordered_departments
        
        if ordered_departments:
            # Preview custom workflow
            with st.expander("🔍 Preview Custom Workflow"):
                render_workflow_progress(ordered_departments, 0, "pending")
            
            return ordered_departments
    
    return []

def render_work_item_form(department_sequence: List[str]):
    """Render the main work item creation form."""
    st.subheader("📝 Work Item Details")
    
    with st.form("create_work_item_form"):
        # Basic information
        col1, col2 = st.columns(2)
        
        with col1:
            title = st.text_input(
                "Title *",
                placeholder="Brief description of the work item",
                help="Enter a clear, descriptive title for the work item"
            )
            
            priority = st.selectbox(
                "Priority *",
                ["low", "medium", "high", "critical"],
                index=1,  # Default to medium
                format_func=lambda x: {
                    "low": "🟢 Low",
                    "medium": "🟡 Medium", 
                    "high": "🟠 High",
                    "critical": "🔴 Critical"
                }[x]
            )
            
            created_by = st.text_input(
                "Created By *",
                value="demo_user@aviation.com",
                help="Email of the person creating this item"
            )
        
        with col2:
            assigned_to = st.text_input(
                "Assigned To",
                placeholder="user@aviation.com",
                help="Email of the person assigned to this item (optional)"
            )
            
            due_date = st.date_input(
                "Due Date",
                value=datetime.now().date() + timedelta(days=7),
                help="When this item should be completed"
            )
            
            due_time = st.time_input(
                "Due Time",
                value=datetime.now().time().replace(hour=17, minute=0, second=0, microsecond=0),
                help="Time when item is due"
            )
        
        # Description
        description = st.text_area(
            "Description *",
            placeholder="Detailed description of the work to be performed...",
            height=150,
            help="Provide detailed information about what needs to be done"
        )
        
        # Additional metadata
        st.subheader("✈️ Aviation-Specific Information")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            aircraft_tail = st.text_input(
                "Aircraft Tail Number",
                placeholder="N123AB",
                help="Aircraft registration number (if applicable)"
            )
        
        with col2:
            location = st.selectbox(
                "Location",
                ["", "KORD", "KLAX", "KJFK", "KATL", "KDEN", "KIAH", "KPHX", "Other"],
                help="Airport or location code"
            )
            
            if location == "Other":
                location = st.text_input("Custom Location", placeholder="Enter location")
        
        with col3:
            estimated_hours = st.number_input(
                "Estimated Hours",
                min_value=0.0,
                max_value=100.0,
                step=0.5,
                value=1.0,
                help="Expected time to complete (in hours)"
            )
        
        # Additional fields
        with st.expander("📋 Additional Information"):
            maintenance_type = st.selectbox(
                "Maintenance Type",
                ["", "Routine", "Scheduled", "Unscheduled", "Emergency", "Inspection"],
                help="Type of maintenance work (if applicable)"
            )
            
            part_numbers = st.text_input(
                "Part Numbers",
                placeholder="PN123, PN456, PN789",
                help="Comma-separated list of part numbers"
            )
            
            safety_critical = st.checkbox(
                "Safety Critical Item",
                help="Check if this item affects flight safety"
            )
            
            special_instructions = st.text_area(
                "Special Instructions",
                placeholder="Any special handling requirements or notes...",
                help="Additional instructions for handling this item"
            )
        
        # Workflow preview
        if department_sequence:
            st.subheader("🔄 Workflow Preview")
            render_workflow_progress(department_sequence, 0, "pending")
        
        # Form submission
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col1:
            submitted = st.form_submit_button("✅ Create Work Item", type="primary")
        
        with col2:
            save_draft = st.form_submit_button("💾 Save as Draft")
        
        with col3:
            clear_form = st.form_submit_button("🗑️ Clear Form")
        
        # Handle form submission
        if submitted:
            if not title or not description or not created_by:
                st.error("Please fill in all required fields marked with *")
                return
            
            if not department_sequence:
                st.error("Please select a template or create a custom workflow")
                return
            
            # Combine date and time
            due_datetime = datetime.combine(due_date, due_time)
            
            # Prepare work item data
            work_item_data = {
                "title": title,
                "description": description,
                "priority": priority,
                "department_ids": department_sequence,
                "created_by": created_by,
                "assigned_to": assigned_to if assigned_to else None,
                "due_date": due_datetime.isoformat(),
                "metadata": {
                    "aircraft_tail": aircraft_tail,
                    "location": location,
                    "estimated_hours": estimated_hours,
                    "maintenance_type": maintenance_type,
                    "part_numbers": part_numbers,
                    "safety_critical": safety_critical,
                    "special_instructions": special_instructions,
                    "template_id": st.session_state.selected_template.get('id') if st.session_state.selected_template else None,
                    "template_name": st.session_state.selected_template.get('name') if st.session_state.selected_template else "custom"
                }
            }
            
            # Submit to API
            result = post_api_data("work-items", work_item_data)
            
            if result:
                st.success("🎉 Work item created successfully!")
                st.balloons()
                
                # Show created item details
                with st.expander("📋 Created Item Details"):
                    st.json(result)
                
                # Option to create another
                if st.button("➕ Create Another Item"):
                    # Clear form state
                    for key in list(st.session_state.keys()):
                        if key.startswith('create_'):
                            del st.session_state[key]
                    st.rerun()
            else:
                st.error("Failed to create work item. Please try again.")
        
        elif save_draft:
            st.info("Draft saved locally (feature not implemented in MVP)")
        
        elif clear_form:
            # Clear form by clearing session state
            for key in list(st.session_state.keys()):
                if key.startswith('create_') or key in ['selected_template', 'custom_departments', 'form_mode']:
                    del st.session_state[key]
            st.rerun()

def render_recent_items():
    """Render recently created items for reference."""
    st.subheader("🕒 Recently Created Items")
    
    # Get recent work items
    work_items = get_api_data("work-items")
    
    if work_items:
        # Sort by creation date and take latest 5
        sorted_items = sorted(
            work_items, 
            key=lambda x: x.get('created_at', ''), 
            reverse=True
        )[:5]
        
        for item in sorted_items:
            with st.expander(f"{item.get('title', 'Untitled')} - {item.get('status', 'unknown')}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**ID:** {item.get('id', 'N/A')}")
                    st.write(f"**Priority:** {item.get('priority', 'N/A')}")
                    st.write(f"**Created:** {item.get('created_at', 'N/A')}")
                
                with col2:
                    st.write(f"**Status:** {item.get('status', 'N/A')}")
                    st.write(f"**Created by:** {item.get('created_by', 'N/A')}")
                    
                    dept_ids = item.get('department_ids', [])
                    current_step = item.get('current_step', 0)
                    if current_step < len(dept_ids):
                        current_dept = dept_ids[current_step].replace('_', ' ').title()
                        st.write(f"**Current Dept:** {current_dept}")
    else:
        st.info("No recent items found")

def main():
    """Main create item page function."""
    # Initialize session state
    initialize_session_state()
    
    # Render header
    if not render_header():
        return
    
    # Create tabs for different sections
    tab1, tab2 = st.tabs(["🆕 Create Item", "🕒 Recent Items"])
    
    with tab1:
        # Template or custom workflow selection
        if st.session_state.form_mode == "template":
            selected_template = render_template_selector()
            department_sequence = selected_template.get('department_sequence', []) if selected_template else []
        else:
            render_template_selector()  # Still show selector to allow switching
            department_sequence = render_custom_department_builder()
        
        # Main form
        if department_sequence or st.session_state.form_mode == "custom":
            st.markdown("---")
            render_work_item_form(department_sequence)
    
    with tab2:
        render_recent_items()

if __name__ == "__main__":
    main()
"""
Workflow Visualization Component

Visual representation of workflow progress showing department sequence,
current step highlighting, and approval status indicators.
"""

import streamlit as st
from typing import List, Dict, Any, Optional


def render_workflow_progress(
    department_sequence: List[str],
    current_step: int,
    status: str = "in_progress",
    department_names: Optional[Dict[str, str]] = None
):
    """
    Render a visual workflow progress indicator.
    
    Args:
        department_sequence: List of department IDs in workflow order
        current_step: Current step index (0-based)
        status: Current workflow status
        department_names: Optional mapping of dept IDs to display names
    """
    if not department_sequence:
        st.warning("No workflow sequence defined")
        return
    
    # Default department display names
    default_names = {
        "flight_operations": "Flight Operations",
        "maintenance": "Maintenance", 
        "safety_quality": "Safety & QA",
        "ground_services": "Ground Services",
        "customer_service": "Customer Service",
        "engineering": "Engineering",
        "quality_control": "Quality Control"
    }
    
    # Use provided names or fall back to defaults
    display_names = department_names or default_names
    
    # Status colors
    status_colors = {
        "pending": "#ffc107",      # Yellow
        "in_progress": "#007bff",  # Blue
        "approved": "#28a745",     # Green
        "rejected": "#dc3545",     # Red
        "completed": "#6c757d"     # Gray
    }
    
    status_color = status_colors.get(status, "#6c757d")
    
    # Create workflow visualization
    st.markdown(f"""
    <div style="margin: 1rem 0;">
        <h4 style="color: #333; margin-bottom: 0.5rem;">Workflow Progress</h4>
        <p style="color: #666; font-size: 0.9rem;">
            Status: <strong style="color: {status_color};">{status.title()}</strong> 
            | Step {current_step + 1} of {len(department_sequence)}
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Render progress steps
    cols = st.columns(len(department_sequence))
    
    for i, dept_id in enumerate(department_sequence):
        with cols[i]:
            # Determine step status
            if i < current_step:
                # Completed step
                step_status = "completed"
                step_color = "#28a745"
                step_icon = "✅"
            elif i == current_step:
                # Current step
                step_status = "current"
                step_color = status_color
                step_icon = "🔄" if status == "in_progress" else "⏸️"
            else:
                # Future step
                step_status = "pending"
                step_color = "#e9ecef"
                step_icon = "⏳"
            
            # Get display name
            dept_name = display_names.get(dept_id, dept_id.replace("_", " ").title())
            
            # Render step
            st.markdown(f"""
            <div style="
                text-align: center;
                padding: 0.5rem;
                margin: 0.2rem;
                border: 2px solid {step_color};
                border-radius: 8px;
                background-color: {'#f8f9fa' if step_status == 'current' else 'white'};
                {'box-shadow: 0 2px 4px rgba(0,123,255,0.3);' if step_status == 'current' else ''}
            ">
                <div style="font-size: 1.5rem; margin-bottom: 0.25rem;">
                    {step_icon}
                </div>
                <div style="
                    font-weight: {'bold' if step_status == 'current' else 'normal'};
                    color: {step_color if step_status != 'pending' else '#6c757d'};
                    font-size: 0.8rem;
                    line-height: 1.2;
                ">
                    {dept_name}
                </div>
                <div style="
                    font-size: 0.7rem;
                    color: #6c757d;
                    margin-top: 0.25rem;
                ">
                    Step {i + 1}
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    # Add progress bar below
    progress_percent = (current_step) / len(department_sequence) if len(department_sequence) > 0 else 0
    
    st.markdown(f"""
    <div style="margin: 1rem 0;">
        <div style="
            width: 100%;
            background-color: #e9ecef;
            border-radius: 10px;
            height: 6px;
            overflow: hidden;
        ">
            <div style="
                width: {progress_percent * 100}%;
                background-color: {status_color};
                height: 100%;
                border-radius: 10px;
                transition: width 0.3s ease;
            "></div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_compact_workflow_progress(
    department_sequence: List[str],
    current_step: int,
    status: str = "in_progress"
):
    """
    Render a compact single-line workflow progress indicator.
    
    Args:
        department_sequence: List of department IDs in workflow order
        current_step: Current step index (0-based)
        status: Current workflow status
    """
    if not department_sequence:
        return
    
    # Status emojis
    status_emojis = {
        "pending": "⏸️",
        "in_progress": "🔄", 
        "approved": "✅",
        "rejected": "❌",
        "completed": "✅"
    }
    
    status_emoji = status_emojis.get(status, "❓")
    
    # Create compact progress
    progress_parts = []
    
    for i, dept_id in enumerate(department_sequence):
        if i < current_step:
            progress_parts.append("✅")
        elif i == current_step:
            progress_parts.append(status_emoji)
        else:
            progress_parts.append("⏳")
    
    # Display compact progress
    progress_str = " → ".join(progress_parts)
    st.markdown(f"**Workflow:** {progress_str} ({current_step + 1}/{len(department_sequence)})")


def render_workflow_timeline(
    work_item: Dict[str, Any],
    approval_history: Optional[List[Dict[str, Any]]] = None
):
    """
    Render a timeline view of workflow progress with history.
    
    Args:
        work_item: Work item data containing workflow information
        approval_history: Optional list of approval history records
    """
    department_sequence = work_item.get('department_ids', [])
    current_step = work_item.get('current_step', 0)
    
    if not department_sequence:
        st.warning("No workflow sequence defined")
        return
    
    st.subheader("📅 Workflow Timeline")
    
    # Default department names
    dept_names = {
        "flight_operations": "Flight Operations",
        "maintenance": "Maintenance",
        "safety_quality": "Safety & QA", 
        "ground_services": "Ground Services",
        "customer_service": "Customer Service"
    }
    
    # Create timeline
    for i, dept_id in enumerate(department_sequence):
        dept_name = dept_names.get(dept_id, dept_id.replace("_", " ").title())
        
        # Determine status for this step
        if i < current_step:
            step_status = "completed"
            status_color = "#28a745"
            status_text = "✅ Completed"
        elif i == current_step:
            step_status = "current"
            status_color = "#007bff"
            status_text = "🔄 In Progress"
        else:
            step_status = "pending"
            status_color = "#6c757d"
            status_text = "⏳ Pending"
        
        # Create timeline entry
        with st.container():
            col1, col2, col3 = st.columns([1, 3, 2])
            
            with col1:
                st.markdown(f"""
                <div style="
                    text-align: center;
                    padding: 0.5rem;
                    border: 2px solid {status_color};
                    border-radius: 50%;
                    background-color: {'#f8f9fa' if step_status == 'current' else 'white'};
                    width: 60px;
                    height: 60px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    margin: 0 auto;
                ">
                    <strong style="color: {status_color};">{i + 1}</strong>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"""
                <div style="padding: 1rem 0;">
                    <h5 style="color: {status_color}; margin-bottom: 0.25rem;">
                        {dept_name}
                    </h5>
                    <p style="color: {status_color}; font-weight: bold; margin: 0;">
                        {status_text}
                    </p>
                </div>
                """, unsafe_allow_html=True)
            
            with col3:
                if approval_history:
                    # Show relevant history for this step
                    step_history = [h for h in approval_history if h.get('step') == i]
                    if step_history:
                        latest = step_history[-1]
                        st.caption(f"Last action: {latest.get('action', 'N/A')}")
                        st.caption(f"By: {latest.get('user', 'N/A')}")
                        st.caption(f"Date: {latest.get('timestamp', 'N/A')}")
                else:
                    if step_status == "completed":
                        st.caption("✅ Approved")
                    elif step_status == "current":
                        st.caption("📋 Awaiting approval")
                    else:
                        st.caption("⏳ Not started")
        
        # Add connecting line (except for last item)
        if i < len(department_sequence) - 1:
            st.markdown(f"""
            <div style="
                width: 2px;
                height: 20px;
                background-color: {status_color if i < current_step else '#e9ecef'};
                margin: 0 auto;
            "></div>
            """, unsafe_allow_html=True)


def render_workflow_stats(work_items: List[Dict[str, Any]]):
    """
    Render workflow statistics and insights.
    
    Args:
        work_items: List of work items to analyze
    """
    if not work_items:
        st.warning("No work items to analyze")
        return
    
    st.subheader("📊 Workflow Statistics")
    
    # Calculate stats
    total_items = len(work_items)
    dept_workload = {}
    avg_steps = 0
    
    for item in work_items:
        dept_sequence = item.get('department_ids', [])
        current_step = item.get('current_step', 0)
        
        avg_steps += len(dept_sequence)
        
        # Count items per department
        if current_step < len(dept_sequence):
            current_dept = dept_sequence[current_step]
            dept_workload[current_dept] = dept_workload.get(current_dept, 0) + 1
    
    avg_steps = avg_steps / total_items if total_items > 0 else 0
    
    # Display metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Active Items", total_items)
    
    with col2:
        st.metric("Avg Steps per Workflow", f"{avg_steps:.1f}")
    
    with col3:
        busiest_dept = max(dept_workload.items(), key=lambda x: x[1]) if dept_workload else ("N/A", 0)
        st.metric("Busiest Department", busiest_dept[0].replace("_", " ").title())
    
    # Department workload chart
    if dept_workload:
        st.subheader("Current Department Workload")
        
        dept_names = {
            "flight_operations": "Flight Operations",
            "maintenance": "Maintenance",
            "safety_quality": "Safety & QA",
            "ground_services": "Ground Services", 
            "customer_service": "Customer Service"
        }
        
        workload_data = []
        for dept_id, count in dept_workload.items():
            dept_name = dept_names.get(dept_id, dept_id.replace("_", " ").title())
            workload_data.append({"Department": dept_name, "Pending Items": count})
        
        if workload_data:
            import pandas as pd
            df = pd.DataFrame(workload_data)
            st.bar_chart(df.set_index("Department"))
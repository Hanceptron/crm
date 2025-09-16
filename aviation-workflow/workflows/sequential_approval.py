"""
Sequential approval workflow implementation for the Aviation Workflow System.

Implements the main approval workflow using Burr actions for moving work items
through department sequences with approval and rejection capabilities.
"""

from datetime import datetime
from typing import Dict, Any, List, Optional
from burr.core import Action, State, Application, ApplicationBuilder, when, default
from burr.tracking import LocalTrackingClient
from workflows.base_workflow import BaseWorkflowAction, BaseWorkflow


class ApprovalAction(BaseWorkflowAction):
    """Base action for approval workflows"""
    
    @property
    def reads(self) -> List[str]:
        return ["current_step", "department_sequence", "status"]
    
    @property
    def writes(self) -> List[str]:
        return ["current_step", "status", "history"]


class Approve(ApprovalAction):
    """Move to next department"""
    
    def run(self, state: State, comment: str = None) -> Dict[str, Any]:
        """
        Execute approval action to move to next department.
        
        Args:
            state: Current workflow state
            comment: Optional comment for the approval
            
        Returns:
            Dictionary with updated state values
        """
        if not self.validate_state(state):
            raise ValueError("Invalid state for approve action")
        
        current_step = state["current_step"]
        sequence = state["department_sequence"]
        
        next_step = current_step + 1
        is_complete = next_step >= len(sequence)
        
        # Add to history
        history = self.add_to_history(
            state, 
            "approved",
            to_step=next_step if not is_complete else current_step,
            comment=comment,
            from_department=sequence[current_step] if current_step < len(sequence) else None,
            to_department=sequence[next_step] if not is_complete and next_step < len(sequence) else None
        )
        
        return {
            "current_step": next_step if not is_complete else current_step,
            "status": "completed" if is_complete else "active",
            "history": history
        }


class Reject(ApprovalAction):
    """Send back to previous department"""
    
    def run(self, state: State, target_step: int, comment: str) -> Dict[str, Any]:
        """
        Execute rejection action to send back to previous department.
        
        Args:
            state: Current workflow state
            target_step: Step to send the work item back to
            comment: Required comment explaining the rejection
            
        Returns:
            Dictionary with updated state values
        """
        if not self.validate_state(state):
            raise ValueError("Invalid state for reject action")
        
        current_step = state["current_step"]
        sequence = state["department_sequence"]
        
        # Validate target step
        if not self.validate_step_transition(current_step, target_step, len(sequence)):
            raise ValueError(f"Invalid target step {target_step} from current step {current_step}")
        
        # Add to history
        history = self.add_to_history(
            state,
            "rejected",
            to_step=target_step,
            comment=comment,
            from_department=sequence[current_step] if current_step < len(sequence) else None,
            to_department=sequence[target_step] if target_step < len(sequence) else None
        )
        
        return {
            "current_step": target_step,
            "status": "active",
            "history": history
        }


class Cancel(ApprovalAction):
    """Cancel the workflow"""
    
    def run(self, state: State, reason: str = None) -> Dict[str, Any]:
        """
        Execute cancel action to terminate the workflow.
        
        Args:
            state: Current workflow state
            reason: Optional reason for cancellation
            
        Returns:
            Dictionary with updated state values
        """
        if not self.validate_state(state):
            raise ValueError("Invalid state for cancel action")
        
        # Add to history
        history = self.add_to_history(
            state,
            "cancelled",
            reason=reason
        )
        
        return {
            "current_step": state["current_step"],  # Keep current step
            "status": "cancelled",
            "history": history
        }


class SequentialApprovalWorkflow(BaseWorkflow):
    """Sequential approval workflow implementation."""
    
    def get_actions(self) -> Dict[str, Action]:
        """Get all actions available in this workflow."""
        return {
            "approve": Approve(),
            "reject": Reject(),
            "cancel": Cancel()
        }
    
    def get_transitions(self) -> List[tuple]:
        """Get workflow transitions."""
        return [
            ("approve", "approve", when(status="active")),
            ("approve", "complete", when(status="completed")),
            ("reject", "approve", default),
            ("*", "cancel", when(action="cancel")),
        ]
    
    def get_initial_state(self, department_sequence: List[str], **kwargs) -> Dict[str, Any]:
        """Get initial state for the workflow."""
        return self.create_common_initial_state(department_sequence, **kwargs)


def build_approval_workflow(department_sequence: List[str], 
                          tracker: Optional[LocalTrackingClient] = None,
                          app_id: Optional[str] = None) -> Application:
    """
    Build a Burr application for approval workflow.
    
    Args:
        department_sequence: List of department IDs for the workflow
        tracker: Optional tracking client for state persistence
        app_id: Optional application ID for tracking
        
    Returns:
        Configured Burr Application instance
    """
    if not department_sequence:
        raise ValueError("Department sequence cannot be empty")
    
    # Create workflow instance
    workflow = SequentialApprovalWorkflow()
    
    # Build the application
    builder = (
        ApplicationBuilder()
        .with_actions(**workflow.get_actions())
        .with_transitions(*workflow.get_transitions())
        .with_initial_state(**workflow.get_initial_state(department_sequence))
    )
    
    # Add tracking if provided
    if tracker:
        builder = builder.with_tracker(tracker)
    
    # Set app ID if provided
    if app_id:
        builder = builder.with_identifiers(app_id=app_id)
    
    return builder.build()


# Helper functions for workflow management

def create_standard_approval_workflow(department_ids: List[str],
                                    tracking_db_path: str = "burr_state.db",
                                    app_id: Optional[str] = None) -> Application:
    """
    Create a standard approval workflow with default settings.
    
    Args:
        department_ids: List of department IDs
        tracking_db_path: Path to the tracking database
        app_id: Optional application ID
        
    Returns:
        Configured Application instance
    """
    tracker = LocalTrackingClient(tracking_db_path)
    return build_approval_workflow(
        department_sequence=department_ids,
        tracker=tracker,
        app_id=app_id
    )


def get_workflow_status_info(state: State) -> Dict[str, Any]:
    """
    Get comprehensive status information for a workflow.
    
    Args:
        state: Current workflow state
        
    Returns:
        Dictionary with workflow status information
    """
    current_step = state.get("current_step", 0)
    sequence = state.get("department_sequence", [])
    status = state.get("status", "active")
    history = state.get("history", [])
    
    return {
        "status": status,
        "current_step": current_step,
        "total_steps": len(sequence),
        "current_department": sequence[current_step] if current_step < len(sequence) else None,
        "next_department": sequence[current_step + 1] if current_step + 1 < len(sequence) else None,
        "is_final_step": current_step >= len(sequence) - 1,
        "progress_percentage": (current_step / len(sequence)) * 100 if sequence else 0,
        "department_sequence": sequence,
        "history_count": len(history),
        "last_action": history[-1] if history else None
    }
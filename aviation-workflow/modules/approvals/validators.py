"""
Approval validators for the Aviation Workflow System.

Contains validation logic for approval actions including workflow state
validation and business rule enforcement.
"""

import logging
from typing import List, Optional, Dict, Any
from sqlmodel import Session, select

from core.models import WorkItem
from core.workflow_engine import WorkflowEngine, WorkflowEngineError
from .models import Approval

logger = logging.getLogger(__name__)


class ApprovalValidationError(Exception):
    """Base exception for approval validation errors."""
    pass


class InvalidStateError(ApprovalValidationError):
    """Raised when work item is in invalid state for approval."""
    pass


class InvalidStepError(ApprovalValidationError):
    """Raised when target step is invalid for rejection."""
    pass


class WorkflowNotFoundError(ApprovalValidationError):
    """Raised when workflow is not found."""
    pass


class ApprovalValidator:
    """
    Validator class for approval actions.
    
    Provides validation methods for checking approval prerequisites,
    workflow states, and business rules.
    """
    
    def __init__(self, session: Session, workflow_engine: WorkflowEngine):
        """
        Initialize approval validator.
        
        Args:
            session: Database session
            workflow_engine: Workflow engine instance
        """
        self.session = session
        self.workflow_engine = workflow_engine
    
    def validate_can_approve(self, work_item_id: str, action: str) -> Dict[str, Any]:
        """
        Validate that a work item can be approved/rejected/cancelled.
        
        Args:
            work_item_id: Work item identifier
            action: Action to validate (approve/reject/cancel)
            
        Returns:
            Dictionary with validation results and work item data
            
        Raises:
            ApprovalValidationError: If validation fails
        """
        try:
            # Get work item
            work_item = self.session.get(WorkItem, work_item_id)
            if not work_item:
                raise ApprovalValidationError(f"Work item {work_item_id} not found")
            
            # Check work item status
            if work_item.status not in ["active"]:
                raise InvalidStateError(
                    f"Cannot {action} work item with status '{work_item.status}'. "
                    f"Only 'active' items can be processed."
                )
            
            # Check if workflow exists
            if not self.workflow_engine.workflow_exists(work_item_id):
                raise WorkflowNotFoundError(
                    f"Workflow not found for work item {work_item_id}. "
                    f"Workflow may need to be recreated."
                )
            
            # Get available actions from workflow engine
            try:
                available_actions = self.workflow_engine.get_available_actions(work_item_id)
            except WorkflowEngineError as e:
                raise ApprovalValidationError(f"Error getting available actions: {str(e)}")
            
            # Check if requested action is available
            if action.lower() not in [a.lower() for a in available_actions]:
                raise InvalidStateError(
                    f"Action '{action}' not available for work item {work_item_id}. "
                    f"Available actions: {available_actions}"
                )
            
            # Get current workflow state
            try:
                current_state = self.workflow_engine.get_workflow_state(work_item_id)
                if not current_state:
                    raise WorkflowNotFoundError(f"No workflow state found for work item {work_item_id}")
            except WorkflowEngineError as e:
                raise ApprovalValidationError(f"Error getting workflow state: {str(e)}")
            
            # Get department sequence and current step info
            department_sequence = work_item.workflow_data.get("department_sequence", [])
            current_step = work_item.current_step
            
            current_department_id = None
            if 0 <= current_step < len(department_sequence):
                current_department_id = department_sequence[current_step]
            
            return {
                "valid": True,
                "work_item": work_item,
                "current_state": current_state,
                "available_actions": available_actions,
                "department_sequence": department_sequence,
                "current_step": current_step,
                "current_department_id": current_department_id
            }
            
        except ApprovalValidationError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error validating approval for {work_item_id}: {e}")
            raise ApprovalValidationError(f"Validation failed: {str(e)}")
    
    def validate_rejection_target(self, work_item_id: str, target_step: int) -> Dict[str, Any]:
        """
        Validate that a rejection target step is valid.
        
        Args:
            work_item_id: Work item identifier
            target_step: Target step for rejection
            
        Returns:
            Dictionary with validation results and target department info
            
        Raises:
            ApprovalValidationError: If validation fails
        """
        try:
            # First validate that the work item can be rejected
            validation_result = self.validate_can_approve(work_item_id, "reject")
            
            work_item = validation_result["work_item"]
            department_sequence = validation_result["department_sequence"]
            current_step = validation_result["current_step"]
            
            # Validate target step range
            if target_step < 0:
                raise InvalidStepError(f"Target step {target_step} cannot be negative")
            
            if target_step >= len(department_sequence):
                raise InvalidStepError(
                    f"Target step {target_step} exceeds department sequence length "
                    f"({len(department_sequence)})"
                )
            
            # Validate that target step is not the same as current step
            if target_step == current_step:
                raise InvalidStepError(
                    f"Target step {target_step} is the same as current step. "
                    f"Rejection must move to a different step."
                )
            
            # For rejections, typically can only go backwards or to the beginning
            if target_step > current_step:
                raise InvalidStepError(
                    f"Cannot reject forward from step {current_step} to step {target_step}. "
                    f"Rejections typically move backwards in the workflow."
                )
            
            # Get target department info
            target_department_id = department_sequence[target_step]
            
            # Validate target department exists (if departments module is available)
            target_department = None
            try:
                from modules.departments.service import DepartmentService
                dept_service = DepartmentService(self.session)
                target_department = dept_service.get(target_department_id)
                
                if not target_department.is_active:
                    raise InvalidStepError(
                        f"Target department {target_department.name} is not active"
                    )
            except ImportError:
                # Departments module not available, skip department validation
                logger.warning("Departments module not available for validation")
            except Exception as e:
                logger.warning(f"Could not validate target department: {e}")
            
            return {
                "valid": True,
                "target_step": target_step,
                "target_department_id": target_department_id,
                "target_department": target_department,
                "current_step": current_step,
                "can_reject_to_target": True
            }
            
        except ApprovalValidationError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error validating rejection target for {work_item_id}: {e}")
            raise ApprovalValidationError(f"Rejection target validation failed: {str(e)}")
    
    def validate_approval_prerequisites(self, work_item_id: str, 
                                      actor_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Validate prerequisites for approval actions.
        
        Args:
            work_item_id: Work item identifier
            actor_name: Name of the actor performing the approval
            
        Returns:
            Dictionary with validation results and prerequisite info
            
        Raises:
            ApprovalValidationError: If prerequisites are not met
        """
        try:
            # Basic validation
            validation_result = self.validate_can_approve(work_item_id, "approve")
            work_item = validation_result["work_item"]
            
            # Check for any business rules
            prerequisites = {
                "work_item_exists": True,
                "workflow_active": True,
                "actor_specified": actor_name is not None,
                "can_approve": True
            }
            
            # Check if there are any recent approvals that might conflict
            recent_approvals = self.session.exec(
                select(Approval)
                .where(Approval.work_item_id == work_item_id)
                .order_by(Approval.created_at.desc())
            ).all()
            
            # Add recent approval history to validation result
            prerequisites["recent_approvals_count"] = len(recent_approvals)
            prerequisites["last_approval"] = recent_approvals[0] if recent_approvals else None
            
            # Check for potential duplicate approvals
            if recent_approvals:
                last_approval = recent_approvals[0]
                if (last_approval.action == "approved" and 
                    last_approval.actor_name == actor_name and
                    work_item.current_step == validation_result["current_step"]):
                    logger.warning(
                        f"Potential duplicate approval by {actor_name} "
                        f"for work item {work_item_id} at step {work_item.current_step}"
                    )
            
            validation_result.update(prerequisites)
            return validation_result
            
        except ApprovalValidationError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error validating prerequisites for {work_item_id}: {e}")
            raise ApprovalValidationError(f"Prerequisites validation failed: {str(e)}")
    
    def validate_bulk_approval(self, work_item_ids: List[str], 
                              action: str) -> Dict[str, Any]:
        """
        Validate bulk approval operation.
        
        Args:
            work_item_ids: List of work item IDs
            action: Action to perform on all items
            
        Returns:
            Dictionary with validation results for each item
        """
        results = {
            "valid_items": [],
            "invalid_items": [],
            "validation_errors": []
        }
        
        for work_item_id in work_item_ids:
            try:
                validation_result = self.validate_can_approve(work_item_id, action)
                results["valid_items"].append({
                    "work_item_id": work_item_id,
                    "validation": validation_result
                })
            except ApprovalValidationError as e:
                results["invalid_items"].append({
                    "work_item_id": work_item_id,
                    "error": str(e)
                })
                results["validation_errors"].append(f"{work_item_id}: {str(e)}")
        
        results["total_valid"] = len(results["valid_items"])
        results["total_invalid"] = len(results["invalid_items"])
        results["all_valid"] = results["total_invalid"] == 0
        
        return results
    
    def get_approval_history(self, work_item_id: str) -> List[Approval]:
        """
        Get approval history for a work item.
        
        Args:
            work_item_id: Work item identifier
            
        Returns:
            List of approval records ordered by creation time
        """
        return list(self.session.exec(
            select(Approval)
            .where(Approval.work_item_id == work_item_id)
            .order_by(Approval.created_at.asc())
        ).all())
    
    def check_approval_permissions(self, work_item_id: str, 
                                  actor_name: str,
                                  department_id: Optional[str] = None) -> bool:
        """
        Check if an actor has permission to approve/reject a work item.
        
        Args:
            work_item_id: Work item identifier
            actor_name: Name of the actor
            department_id: Department ID (if department-based permissions are used)
            
        Returns:
            True if actor has permission, False otherwise
            
        Note:
            This is a placeholder for future permission system implementation.
            Currently returns True for all actors.
        """
        # TODO: Implement permission checking based on business rules
        # This could check:
        # - Actor role/permissions
        # - Department membership
        # - Work item assignment
        # - Approval delegation rules
        
        logger.debug(f"Permission check for {actor_name} on work item {work_item_id}: granted")
        return True
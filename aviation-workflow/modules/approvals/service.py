"""
Service layer for the approvals module.

Contains business logic for approval operations including workflow integration,
transaction management, and Burr state transitions.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from core.models import WorkItem
from core.workflow_engine import WorkflowEngine, WorkflowEngineError
from .models import Approval
from .schemas import ApprovalRequest, ApprovalResponse, PendingApprovalResponse
from .validators import ApprovalValidator, ApprovalValidationError

logger = logging.getLogger(__name__)


class ApprovalServiceError(Exception):
    """Base exception for approval service errors."""
    pass


class ApprovalService:
    """
    Service class for approval business logic.
    
    Handles approval operations with WorkflowEngine integration,
    transaction management, and state synchronization.
    """
    
    def __init__(self, session: Session, workflow_engine: WorkflowEngine):
        """
        Initialize approval service.
        
        Args:
            session: Database session
            workflow_engine: Workflow engine instance
        """
        self.session = session
        self.workflow_engine = workflow_engine
        self.validator = ApprovalValidator(session, workflow_engine)
    
    def approve_item(self, work_item_id: str, approval_data: ApprovalRequest) -> Dict[str, Any]:
        """
        Approve a work item and trigger Burr state transition.
        
        Args:
            work_item_id: Work item identifier
            approval_data: Approval request data
            
        Returns:
            Dictionary with approval result and updated state
            
        Raises:
            ApprovalServiceError: If approval fails
        """
        try:
            # Validate approval prerequisites
            validation_result = self.validator.validate_approval_prerequisites(
                work_item_id, 
                approval_data.actor_name
            )
            
            work_item = validation_result["work_item"]
            current_state = validation_result["current_state"]
            department_sequence = validation_result["department_sequence"]
            current_step = validation_result["current_step"]
            
            # Get current and next department info
            current_department_id = None
            next_department_id = None
            
            if 0 <= current_step < len(department_sequence):
                current_department_id = department_sequence[current_step]
            
            if current_step + 1 < len(department_sequence):
                next_department_id = department_sequence[current_step + 1]
            
            # Begin database transaction
            try:
                # Execute workflow transition
                context = {
                    "comment": approval_data.comment,
                    "actor": approval_data.actor_name
                }
                
                new_state = self.workflow_engine.execute_transition(
                    workflow_id=work_item_id,
                    action="approve",
                    context=context
                )
                
                # Create approval record
                approval = Approval(
                    work_item_id=work_item_id,
                    action="approved",
                    from_state=work_item.current_state,
                    to_state=new_state.get("status", work_item.status),
                    from_department_id=current_department_id,
                    to_department_id=next_department_id,
                    comment=approval_data.comment,
                    actor_name=approval_data.actor_name,
                    metadata=approval_data.metadata
                )
                
                self.session.add(approval)
                
                # Update work item with new state
                work_item.current_step = new_state.get("current_step", work_item.current_step)
                work_item.status = new_state.get("status", work_item.status)
                work_item.workflow_data = new_state.get_all()
                work_item.update_timestamp()
                
                self.session.add(work_item)
                self.session.commit()
                self.session.refresh(approval)
                self.session.refresh(work_item)
                
                # Get available actions for next step
                available_actions = self.workflow_engine.get_available_actions(work_item_id)
                
                logger.info(
                    f"Successfully approved work item {work_item_id} "
                    f"by {approval_data.actor_name} at step {current_step}"
                )
                
                return {
                    "success": True,
                    "approval": approval,
                    "work_item": work_item,
                    "new_state": new_state.get_all(),
                    "available_actions": available_actions,
                    "message": self._get_approval_message(approval, work_item)
                }
                
            except WorkflowEngineError as e:
                self.session.rollback()
                raise ApprovalServiceError(f"Workflow transition failed: {str(e)}")
            except IntegrityError as e:
                self.session.rollback()
                raise ApprovalServiceError(f"Database constraint violation: {str(e)}")
            
        except ApprovalValidationError as e:
            raise ApprovalServiceError(f"Validation failed: {str(e)}")
        except ApprovalServiceError:
            raise
        except Exception as e:
            self.session.rollback()
            logger.error(f"Unexpected error approving work item {work_item_id}: {e}")
            raise ApprovalServiceError(f"Approval failed: {str(e)}")
    
    def reject_item(self, work_item_id: str, approval_data: ApprovalRequest) -> Dict[str, Any]:
        """
        Reject a work item and trigger Burr state transition.
        
        Args:
            work_item_id: Work item identifier
            approval_data: Rejection request data (must include target_step)
            
        Returns:
            Dictionary with rejection result and updated state
            
        Raises:
            ApprovalServiceError: If rejection fails
        """
        try:
            # Validate rejection prerequisites
            validation_result = self.validator.validate_can_approve(work_item_id, "reject")
            
            # Validate rejection target
            if approval_data.target_step is None:
                raise ApprovalServiceError("target_step is required for rejection")
            
            target_validation = self.validator.validate_rejection_target(
                work_item_id, 
                approval_data.target_step
            )
            
            work_item = validation_result["work_item"]
            current_step = validation_result["current_step"]
            department_sequence = validation_result["department_sequence"]
            
            # Get department info
            current_department_id = None
            target_department_id = target_validation["target_department_id"]
            
            if 0 <= current_step < len(department_sequence):
                current_department_id = department_sequence[current_step]
            
            # Begin database transaction
            try:
                # Execute workflow transition
                context = {
                    "target_step": approval_data.target_step,
                    "comment": approval_data.comment,
                    "actor": approval_data.actor_name
                }
                
                new_state = self.workflow_engine.execute_transition(
                    workflow_id=work_item_id,
                    action="reject",
                    context=context
                )
                
                # Create approval record
                approval = Approval(
                    work_item_id=work_item_id,
                    action="rejected",
                    from_state=work_item.current_state,
                    to_state=new_state.get("status", work_item.status),
                    from_department_id=current_department_id,
                    to_department_id=target_department_id,
                    comment=approval_data.comment,
                    actor_name=approval_data.actor_name,
                    metadata=approval_data.metadata or {}
                )
                
                # Add target step to metadata
                if approval.metadata is None:
                    approval.metadata = {}
                approval.metadata["target_step"] = approval_data.target_step
                
                self.session.add(approval)
                
                # Update work item with new state
                work_item.current_step = new_state.get("current_step", approval_data.target_step)
                work_item.status = new_state.get("status", work_item.status)
                work_item.workflow_data = new_state.get_all()
                work_item.update_timestamp()
                
                self.session.add(work_item)
                self.session.commit()
                self.session.refresh(approval)
                self.session.refresh(work_item)
                
                # Get available actions for next step
                available_actions = self.workflow_engine.get_available_actions(work_item_id)
                
                logger.info(
                    f"Successfully rejected work item {work_item_id} "
                    f"by {approval_data.actor_name} from step {current_step} to step {approval_data.target_step}"
                )
                
                return {
                    "success": True,
                    "approval": approval,
                    "work_item": work_item,
                    "new_state": new_state.get_all(),
                    "available_actions": available_actions,
                    "message": self._get_rejection_message(approval, work_item, approval_data.target_step)
                }
                
            except WorkflowEngineError as e:
                self.session.rollback()
                raise ApprovalServiceError(f"Workflow transition failed: {str(e)}")
            except IntegrityError as e:
                self.session.rollback()
                raise ApprovalServiceError(f"Database constraint violation: {str(e)}")
            
        except ApprovalValidationError as e:
            raise ApprovalServiceError(f"Validation failed: {str(e)}")
        except ApprovalServiceError:
            raise
        except Exception as e:
            self.session.rollback()
            logger.error(f"Unexpected error rejecting work item {work_item_id}: {e}")
            raise ApprovalServiceError(f"Rejection failed: {str(e)}")
    
    def cancel_item(self, work_item_id: str, approval_data: ApprovalRequest) -> Dict[str, Any]:
        """
        Cancel a work item and trigger Burr state transition.
        
        Args:
            work_item_id: Work item identifier
            approval_data: Cancellation request data (must include reason)
            
        Returns:
            Dictionary with cancellation result and updated state
            
        Raises:
            ApprovalServiceError: If cancellation fails
        """
        try:
            # Validate cancellation prerequisites
            validation_result = self.validator.validate_can_approve(work_item_id, "cancel")
            work_item = validation_result["work_item"]
            current_step = validation_result["current_step"]
            department_sequence = validation_result["department_sequence"]
            
            # Get current department info
            current_department_id = None
            if 0 <= current_step < len(department_sequence):
                current_department_id = department_sequence[current_step]
            
            # Begin database transaction
            try:
                # Execute workflow transition
                context = {
                    "reason": approval_data.reason,
                    "comment": approval_data.comment,
                    "actor": approval_data.actor_name
                }
                
                new_state = self.workflow_engine.execute_transition(
                    workflow_id=work_item_id,
                    action="cancel",
                    context=context
                )
                
                # Create approval record
                approval = Approval(
                    work_item_id=work_item_id,
                    action="cancelled",
                    from_state=work_item.current_state,
                    to_state=new_state.get("status", "cancelled"),
                    from_department_id=current_department_id,
                    to_department_id=None,  # No target department for cancellation
                    comment=approval_data.comment,
                    actor_name=approval_data.actor_name,
                    metadata=approval_data.metadata or {}
                )
                
                # Add cancellation reason to metadata
                if approval.metadata is None:
                    approval.metadata = {}
                approval.metadata["cancellation_reason"] = approval_data.reason
                
                self.session.add(approval)
                
                # Update work item with new state
                work_item.status = "cancelled"
                work_item.workflow_data = new_state.get_all()
                work_item.update_timestamp()
                
                self.session.add(work_item)
                self.session.commit()
                self.session.refresh(approval)
                self.session.refresh(work_item)
                
                # Get available actions (should be empty for cancelled items)
                available_actions = self.workflow_engine.get_available_actions(work_item_id)
                
                logger.info(
                    f"Successfully cancelled work item {work_item_id} "
                    f"by {approval_data.actor_name}: {approval_data.reason}"
                )
                
                return {
                    "success": True,
                    "approval": approval,
                    "work_item": work_item,
                    "new_state": new_state.get_all(),
                    "available_actions": available_actions,
                    "message": f"Work item cancelled: {approval_data.reason}"
                }
                
            except WorkflowEngineError as e:
                self.session.rollback()
                raise ApprovalServiceError(f"Workflow transition failed: {str(e)}")
            except IntegrityError as e:
                self.session.rollback()
                raise ApprovalServiceError(f"Database constraint violation: {str(e)}")
            
        except ApprovalValidationError as e:
            raise ApprovalServiceError(f"Validation failed: {str(e)}")
        except ApprovalServiceError:
            raise
        except Exception as e:
            self.session.rollback()
            logger.error(f"Unexpected error cancelling work item {work_item_id}: {e}")
            raise ApprovalServiceError(f"Cancellation failed: {str(e)}")
    
    def get_pending_approvals(self, department_id: Optional[str] = None,
                             priority: Optional[str] = None,
                             limit: int = 100,
                             offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get list of work items pending approval.
        
        Args:
            department_id: Filter by specific department
            priority: Filter by priority (normal, urgent)
            limit: Maximum number of items to return
            offset: Number of items to skip
            
        Returns:
            List of pending approval items with workflow information
        """
        try:
            # Build query for active work items
            query = select(WorkItem).where(WorkItem.status == "active")
            
            if priority:
                query = query.where(WorkItem.priority == priority)
            
            # Apply pagination
            query = query.offset(offset).limit(limit).order_by(
                WorkItem.priority.desc(),  # Urgent first
                WorkItem.created_at.asc()  # Oldest first
            )
            
            work_items = self.session.exec(query).all()
            
            pending_items = []
            
            for work_item in work_items:
                try:
                    # Get workflow information
                    if not self.workflow_engine.workflow_exists(work_item.id):
                        logger.warning(f"No workflow found for work item {work_item.id}")
                        continue
                    
                    available_actions = self.workflow_engine.get_available_actions(work_item.id)
                    
                    # Only include items that can be approved/rejected
                    if not any(action in ['approve', 'reject', 'cancel'] 
                              for action in [a.lower() for a in available_actions]):
                        continue
                    
                    # Get department information
                    department_sequence = work_item.workflow_data.get("department_sequence", [])
                    current_step = work_item.current_step
                    
                    current_department_id = None
                    current_department_name = None
                    
                    if 0 <= current_step < len(department_sequence):
                        current_department_id = department_sequence[current_step]
                        
                        # Get department name if departments module is available
                        try:
                            from modules.departments.service import DepartmentService
                            dept_service = DepartmentService(self.session)
                            dept = dept_service.get(current_department_id)
                            current_department_name = dept.name
                        except (ImportError, Exception):
                            current_department_name = current_department_id
                    
                    # Filter by department if specified
                    if department_id and current_department_id != department_id:
                        continue
                    
                    pending_items.append({
                        "work_item_id": work_item.id,
                        "work_item_title": work_item.title,
                        "current_step": current_step,
                        "current_department_id": current_department_id,
                        "current_department_name": current_department_name,
                        "priority": work_item.priority,
                        "created_at": work_item.created_at.isoformat(),
                        "updated_at": work_item.updated_at.isoformat(),
                        "available_actions": available_actions,
                        "workflow_data": work_item.workflow_data
                    })
                    
                except Exception as e:
                    logger.error(f"Error processing work item {work_item.id}: {e}")
                    continue
            
            return pending_items
            
        except Exception as e:
            logger.error(f"Error getting pending approvals: {e}")
            raise ApprovalServiceError(f"Failed to get pending approvals: {str(e)}")
    
    def get_approval_history(self, work_item_id: str) -> List[Approval]:
        """
        Get approval history for a work item.
        
        Args:
            work_item_id: Work item identifier
            
        Returns:
            List of approval records ordered by creation time
        """
        return self.validator.get_approval_history(work_item_id)
    
    def get_approval_stats(self) -> Dict[str, Any]:
        """
        Get approval statistics.
        
        Returns:
            Dictionary with approval statistics
        """
        try:
            # Get all approvals
            approvals = self.session.exec(select(Approval)).all()
            
            total_approvals = len(approvals)
            approved_count = len([a for a in approvals if a.is_approval()])
            rejected_count = len([a for a in approvals if a.is_rejection()])
            cancelled_count = len([a for a in approvals if a.is_cancellation()])
            
            # Get top actors
            actor_counts = {}
            for approval in approvals:
                if approval.actor_name:
                    actor_counts[approval.actor_name] = actor_counts.get(approval.actor_name, 0) + 1
            
            top_actors = [
                {"actor_name": actor, "approval_count": count}
                for actor, count in sorted(actor_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            ]
            
            # Get recent activity
            recent_approvals = sorted(approvals, key=lambda x: x.created_at, reverse=True)[:10]
            
            return {
                "total_approvals": total_approvals,
                "approved_count": approved_count,
                "rejected_count": rejected_count,
                "cancelled_count": cancelled_count,
                "top_actors": top_actors,
                "recent_activity": recent_approvals
            }
            
        except Exception as e:
            logger.error(f"Error getting approval stats: {e}")
            raise ApprovalServiceError(f"Failed to get approval statistics: {str(e)}")
    
    def _get_approval_message(self, approval: Approval, work_item: WorkItem) -> str:
        """Generate human-readable approval message."""
        if work_item.status == "completed":
            return f"Work item '{work_item.title}' has been fully approved and completed"
        else:
            return f"Work item '{work_item.title}' approved and moved to next step"
    
    def _get_rejection_message(self, approval: Approval, work_item: WorkItem, target_step: int) -> str:
        """Generate human-readable rejection message."""
        return (f"Work item '{work_item.title}' rejected and sent back to step {target_step} "
                f"for revision")
    
    def bulk_approve_items(self, work_item_ids: List[str], 
                          approval_data: ApprovalRequest) -> Dict[str, Any]:
        """
        Perform bulk approval operation.
        
        Args:
            work_item_ids: List of work item IDs
            approval_data: Common approval data
            
        Returns:
            Dictionary with bulk operation results
        """
        results = {
            "successful": [],
            "failed": [],
            "total_processed": 0,
            "total_successful": 0,
            "total_failed": 0
        }
        
        for work_item_id in work_item_ids:
            try:
                result = self.approve_item(work_item_id, approval_data)
                results["successful"].append(result)
                results["total_successful"] += 1
            except ApprovalServiceError as e:
                results["failed"].append({
                    "work_item_id": work_item_id,
                    "error": str(e)
                })
                results["total_failed"] += 1
            
            results["total_processed"] += 1
        
        return results
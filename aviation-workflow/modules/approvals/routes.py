"""
API routes for the approvals module.

Implements approval endpoints with proper workflow integration
and Burr state transition handling.
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import Session

from api.dependencies import get_db_session, get_workflow_engine
from core.workflow_engine import WorkflowEngine
from .models import Approval
from .schemas import (
    ApprovalRequest,
    ApprovalResponse,
    ApprovalActionResult,
    PendingApprovalResponse,
    PendingApprovalListResponse,
    ApprovalStats,
    BulkApprovalRequest,
    BulkApprovalResponse
)
from .service import ApprovalService, ApprovalServiceError

logger = logging.getLogger(__name__)

# Create router with prefix and tags
router = APIRouter(prefix="/api/approvals", tags=["approvals"])


def get_approval_service(
    session: Session = Depends(get_db_session),
    workflow_engine: WorkflowEngine = Depends(get_workflow_engine)
) -> ApprovalService:
    """Dependency to get approval service instance."""
    return ApprovalService(session, workflow_engine)


# Core approval endpoints as specified

@router.post("/approve/{item_id}", response_model=ApprovalActionResult)
async def approve_work_item(
    item_id: str,
    approval_data: ApprovalRequest,
    service: ApprovalService = Depends(get_approval_service)
):
    """
    Approve a work item and trigger Burr state transition.
    
    Args:
        item_id: Work item identifier
        approval_data: Approval request data
        
    Returns:
        Approval result with updated workflow state
    """
    try:
        # Validate action
        if approval_data.action.lower() != "approved":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Action must be 'approved' for this endpoint"
            )
        
        result = service.approve_item(item_id, approval_data)
        
        # Convert approval to response schema
        approval_response = ApprovalResponse(
            id=result["approval"].id,
            work_item_id=result["approval"].work_item_id,
            action=result["approval"].action,
            from_state=result["approval"].from_state,
            to_state=result["approval"].to_state,
            from_department_id=result["approval"].from_department_id,
            to_department_id=result["approval"].to_department_id,
            comment=result["approval"].comment,
            actor_name=result["approval"].actor_name,
            metadata=result["approval"].metadata,
            created_at=result["approval"].created_at.isoformat()
        )
        
        return ApprovalActionResult(
            success=result["success"],
            approval=approval_response,
            work_item=result["work_item"].to_dict(),
            new_state=result["new_state"],
            available_actions=result["available_actions"],
            message=result["message"]
        )
        
    except ApprovalServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error approving work item {item_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to approve work item"
        )


@router.post("/reject/{item_id}", response_model=ApprovalActionResult)
async def reject_work_item(
    item_id: str,
    approval_data: ApprovalRequest,
    service: ApprovalService = Depends(get_approval_service)
):
    """
    Reject a work item and trigger Burr state transition.
    
    Args:
        item_id: Work item identifier
        approval_data: Rejection request data (must include target_step)
        
    Returns:
        Rejection result with updated workflow state
    """
    try:
        # Validate action and target_step
        if approval_data.action.lower() != "rejected":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Action must be 'rejected' for this endpoint"
            )
        
        if approval_data.target_step is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="target_step is required for rejection"
            )
        
        result = service.reject_item(item_id, approval_data)
        
        # Convert approval to response schema
        approval_response = ApprovalResponse(
            id=result["approval"].id,
            work_item_id=result["approval"].work_item_id,
            action=result["approval"].action,
            from_state=result["approval"].from_state,
            to_state=result["approval"].to_state,
            from_department_id=result["approval"].from_department_id,
            to_department_id=result["approval"].to_department_id,
            comment=result["approval"].comment,
            actor_name=result["approval"].actor_name,
            metadata=result["approval"].metadata,
            created_at=result["approval"].created_at.isoformat()
        )
        
        return ApprovalActionResult(
            success=result["success"],
            approval=approval_response,
            work_item=result["work_item"].to_dict(),
            new_state=result["new_state"],
            available_actions=result["available_actions"],
            message=result["message"]
        )
        
    except ApprovalServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error rejecting work item {item_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reject work item"
        )


@router.get("/pending", response_model=PendingApprovalListResponse)
async def get_pending_approvals(
    department_id: Optional[str] = Query(
        default=None,
        description="Filter by specific department"
    ),
    priority: Optional[str] = Query(
        default=None,
        description="Filter by priority (normal, urgent)"
    ),
    limit: int = Query(
        default=100,
        ge=1,
        le=1000,
        description="Maximum number of items to return"
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Number of items to skip"
    ),
    service: ApprovalService = Depends(get_approval_service)
):
    """
    Get list of work items pending approval.
    
    Returns:
        List of items pending approval with workflow information
    """
    try:
        pending_items = service.get_pending_approvals(
            department_id=department_id,
            priority=priority,
            limit=limit,
            offset=offset
        )
        
        # Convert to response schemas
        pending_responses = [
            PendingApprovalResponse(
                work_item_id=item["work_item_id"],
                work_item_title=item["work_item_title"],
                current_step=item["current_step"],
                current_department_id=item["current_department_id"],
                current_department_name=item["current_department_name"],
                priority=item["priority"],
                created_at=item["created_at"],
                updated_at=item["updated_at"],
                available_actions=item["available_actions"],
                workflow_data=item["workflow_data"]
            )
            for item in pending_items
        ]
        
        # Calculate statistics
        total = len(pending_responses)
        by_department = {}
        by_priority = {}
        
        for item in pending_responses:
            # Count by department
            dept_name = item.current_department_name or "Unknown"
            by_department[dept_name] = by_department.get(dept_name, 0) + 1
            
            # Count by priority
            by_priority[item.priority] = by_priority.get(item.priority, 0) + 1
        
        return PendingApprovalListResponse(
            pending_items=pending_responses,
            total=total,
            by_department=by_department,
            by_priority=by_priority
        )
        
    except ApprovalServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting pending approvals: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve pending approvals"
        )


# Additional utility endpoints

@router.post("/cancel/{item_id}", response_model=ApprovalActionResult)
async def cancel_work_item(
    item_id: str,
    approval_data: ApprovalRequest,
    service: ApprovalService = Depends(get_approval_service)
):
    """
    Cancel a work item and trigger Burr state transition.
    
    Args:
        item_id: Work item identifier
        approval_data: Cancellation request data (must include reason)
        
    Returns:
        Cancellation result with updated workflow state
    """
    try:
        # Validate action and reason
        if approval_data.action.lower() != "cancelled":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Action must be 'cancelled' for this endpoint"
            )
        
        if not approval_data.reason:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="reason is required for cancellation"
            )
        
        result = service.cancel_item(item_id, approval_data)
        
        # Convert approval to response schema
        approval_response = ApprovalResponse(
            id=result["approval"].id,
            work_item_id=result["approval"].work_item_id,
            action=result["approval"].action,
            from_state=result["approval"].from_state,
            to_state=result["approval"].to_state,
            from_department_id=result["approval"].from_department_id,
            to_department_id=result["approval"].to_department_id,
            comment=result["approval"].comment,
            actor_name=result["approval"].actor_name,
            metadata=result["approval"].metadata,
            created_at=result["approval"].created_at.isoformat()
        )
        
        return ApprovalActionResult(
            success=result["success"],
            approval=approval_response,
            work_item=result["work_item"].to_dict(),
            new_state=result["new_state"],
            available_actions=result["available_actions"],
            message=result["message"]
        )
        
    except ApprovalServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error cancelling work item {item_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel work item"
        )


@router.get("/history/{item_id}")
async def get_approval_history(
    item_id: str,
    service: ApprovalService = Depends(get_approval_service)
):
    """
    Get approval history for a work item.
    
    Args:
        item_id: Work item identifier
        
    Returns:
        List of approval records for the work item
    """
    try:
        approvals = service.get_approval_history(item_id)
        
        approval_responses = [
            ApprovalResponse(
                id=approval.id,
                work_item_id=approval.work_item_id,
                action=approval.action,
                from_state=approval.from_state,
                to_state=approval.to_state,
                from_department_id=approval.from_department_id,
                to_department_id=approval.to_department_id,
                comment=approval.comment,
                actor_name=approval.actor_name,
                metadata=approval.metadata,
                created_at=approval.created_at.isoformat()
            )
            for approval in approvals
        ]
        
        return {
            "work_item_id": item_id,
            "approval_history": approval_responses,
            "total_approvals": len(approval_responses)
        }
        
    except Exception as e:
        logger.error(f"Error getting approval history for {item_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve approval history"
        )


@router.get("/stats", response_model=ApprovalStats)
async def get_approval_statistics(
    service: ApprovalService = Depends(get_approval_service)
):
    """
    Get approval statistics.
    
    Returns:
        Approval statistics including counts and recent activity
    """
    try:
        stats = service.get_approval_stats()
        
        # Convert recent activity to response schemas
        recent_activity = [
            ApprovalResponse(
                id=approval.id,
                work_item_id=approval.work_item_id,
                action=approval.action,
                from_state=approval.from_state,
                to_state=approval.to_state,
                from_department_id=approval.from_department_id,
                to_department_id=approval.to_department_id,
                comment=approval.comment,
                actor_name=approval.actor_name,
                metadata=approval.metadata,
                created_at=approval.created_at.isoformat()
            )
            for approval in stats["recent_activity"]
        ]
        
        return ApprovalStats(
            total_approvals=stats["total_approvals"],
            approved_count=stats["approved_count"],
            rejected_count=stats["rejected_count"],
            cancelled_count=stats["cancelled_count"],
            top_actors=stats["top_actors"],
            recent_activity=recent_activity
        )
        
    except Exception as e:
        logger.error(f"Error getting approval statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve approval statistics"
        )


@router.post("/bulk", response_model=BulkApprovalResponse)
async def bulk_approve_items(
    bulk_data: BulkApprovalRequest,
    service: ApprovalService = Depends(get_approval_service)
):
    """
    Perform bulk approval operation.
    
    Args:
        bulk_data: Bulk approval request data
        
    Returns:
        Bulk operation results
    """
    try:
        # Create approval request for each item
        approval_data = ApprovalRequest(
            action=bulk_data.action,
            comment=bulk_data.comment,
            actor_name=bulk_data.actor_name
        )
        
        results = service.bulk_approve_items(bulk_data.work_item_ids, approval_data)
        
        # Convert successful results to response schemas
        successful_responses = []
        for result in results["successful"]:
            approval_response = ApprovalResponse(
                id=result["approval"].id,
                work_item_id=result["approval"].work_item_id,
                action=result["approval"].action,
                from_state=result["approval"].from_state,
                to_state=result["approval"].to_state,
                from_department_id=result["approval"].from_department_id,
                to_department_id=result["approval"].to_department_id,
                comment=result["approval"].comment,
                actor_name=result["approval"].actor_name,
                metadata=result["approval"].metadata,
                created_at=result["approval"].created_at.isoformat()
            )
            
            successful_responses.append(ApprovalActionResult(
                success=result["success"],
                approval=approval_response,
                work_item=result["work_item"].to_dict(),
                new_state=result["new_state"],
                available_actions=result["available_actions"],
                message=result["message"]
            ))
        
        return BulkApprovalResponse(
            successful=successful_responses,
            failed=results["failed"],
            total_processed=results["total_processed"],
            total_successful=results["total_successful"],
            total_failed=results["total_failed"]
        )
        
    except Exception as e:
        logger.error(f"Error in bulk approval operation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to perform bulk approval operation"
        )


@router.get("/actions/{item_id}")
async def get_available_actions(
    item_id: str,
    service: ApprovalService = Depends(get_approval_service)
):
    """
    Get available approval actions for a work item.
    
    Args:
        item_id: Work item identifier
        
    Returns:
        Available actions and workflow information
    """
    try:
        # Validate that work item can be processed
        validation_result = service.validator.validate_can_approve(item_id, "approve")
        
        return {
            "work_item_id": item_id,
            "available_actions": validation_result["available_actions"],
            "current_step": validation_result["current_step"],
            "current_department_id": validation_result["current_department_id"],
            "workflow_status": validation_result["work_item"].status
        }
        
    except ApprovalServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting available actions for {item_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get available actions"
        )
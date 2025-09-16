"""
Pydantic schemas for the approvals module.

Defines request and response schemas for approval API endpoints
with proper validation and documentation.
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, validator
from datetime import datetime


class ApprovalBase(BaseModel):
    """Base approval schema with common fields."""
    
    action: str = Field(
        ...,
        description="Action taken (approved/rejected/cancelled)"
    )
    
    comment: Optional[str] = Field(
        None,
        max_length=5000,
        description="Comment provided with the action"
    )
    
    actor_name: Optional[str] = Field(
        None,
        max_length=100,
        description="Name of the person performing the action"
    )
    
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional approval metadata"
    )
    
    @validator('action')
    def validate_action(cls, v):
        """Validate approval action."""
        valid_actions = {'approved', 'rejected', 'cancelled'}
        if v.lower() not in valid_actions:
            raise ValueError(f"Action must be one of: {', '.join(valid_actions)}")
        return v.lower()
    
    @validator('comment')
    def validate_comment(cls, v):
        """Validate comment field."""
        if v is not None:
            v = v.strip()
            if len(v) == 0:
                return None
        return v


class ApprovalRequest(ApprovalBase):
    """Schema for approval/rejection requests."""
    
    target_step: Optional[int] = Field(
        None,
        ge=0,
        description="Target step for rejection actions (required for rejections)"
    )
    
    reason: Optional[str] = Field(
        None,
        max_length=1000,
        description="Reason for cancellation actions"
    )
    
    @validator('target_step')
    def validate_target_step_for_rejection(cls, v, values):
        """Validate that target_step is provided for rejections."""
        action = values.get('action', '').lower()
        if action == 'rejected' and v is None:
            raise ValueError("target_step is required for rejection actions")
        return v
    
    @validator('reason')
    def validate_reason_for_cancellation(cls, v, values):
        """Validate that reason is provided for cancellations."""
        action = values.get('action', '').lower()
        if action == 'cancelled' and not v:
            raise ValueError("reason is required for cancellation actions")
        return v
    
    class Config:
        schema_extra = {
            "examples": [
                {
                    "action": "approved",
                    "comment": "All requirements met, approved for next stage",
                    "actor_name": "John Smith"
                },
                {
                    "action": "rejected",
                    "comment": "Missing required documentation",
                    "target_step": 0,
                    "actor_name": "Jane Doe"
                },
                {
                    "action": "cancelled",
                    "reason": "Project requirements changed",
                    "actor_name": "Manager"
                }
            ]
        }


class ApprovalResponse(ApprovalBase):
    """Schema for approval responses."""
    
    id: str = Field(
        ...,
        description="Unique approval identifier"
    )
    
    work_item_id: str = Field(
        ...,
        description="ID of the work item"
    )
    
    from_state: Optional[str] = Field(
        None,
        description="Previous workflow state"
    )
    
    to_state: Optional[str] = Field(
        None,
        description="New workflow state after action"
    )
    
    from_department_id: Optional[str] = Field(
        None,
        description="Department that processed the approval"
    )
    
    to_department_id: Optional[str] = Field(
        None,
        description="Department the item was sent to"
    )
    
    created_at: str = Field(
        ...,
        description="Timestamp when approval was created (ISO format)"
    )
    
    class Config:
        orm_mode = True
        schema_extra = {
            "example": {
                "id": "a1b2c3d4e5f6",
                "work_item_id": "w1x2y3z4a5b6",
                "action": "approved",
                "from_state": "in_review",
                "to_state": "in_review",
                "from_department_id": "eng123",
                "to_department_id": "qc456",
                "comment": "Technical requirements satisfied",
                "actor_name": "John Smith",
                "metadata": {
                    "urgency": "normal",
                    "review_duration": "2 hours"
                },
                "created_at": "2023-01-01T12:00:00"
            }
        }


class ApprovalListResponse(BaseModel):
    """Schema for paginated approval lists."""
    
    approvals: List[ApprovalResponse] = Field(
        ...,
        description="List of approvals"
    )
    
    total: int = Field(
        ...,
        description="Total number of approvals"
    )
    
    approved_count: int = Field(
        ...,
        description="Number of approved actions"
    )
    
    rejected_count: int = Field(
        ...,
        description="Number of rejected actions"
    )
    
    cancelled_count: int = Field(
        ...,
        description="Number of cancelled actions"
    )


class PendingApprovalResponse(BaseModel):
    """Schema for pending approval responses."""
    
    work_item_id: str = Field(
        ...,
        description="Work item ID"
    )
    
    work_item_title: str = Field(
        ...,
        description="Work item title"
    )
    
    current_step: int = Field(
        ...,
        description="Current step in workflow"
    )
    
    current_department_id: Optional[str] = Field(
        None,
        description="Current department ID"
    )
    
    current_department_name: Optional[str] = Field(
        None,
        description="Current department name"
    )
    
    priority: str = Field(
        ...,
        description="Work item priority"
    )
    
    created_at: str = Field(
        ...,
        description="Work item creation timestamp"
    )
    
    updated_at: str = Field(
        ...,
        description="Work item last update timestamp"
    )
    
    available_actions: List[str] = Field(
        ...,
        description="Available approval actions"
    )
    
    workflow_data: Dict[str, Any] = Field(
        ...,
        description="Current workflow data"
    )


class PendingApprovalListResponse(BaseModel):
    """Schema for pending approval lists."""
    
    pending_items: List[PendingApprovalResponse] = Field(
        ...,
        description="List of items pending approval"
    )
    
    total: int = Field(
        ...,
        description="Total number of pending items"
    )
    
    by_department: Dict[str, int] = Field(
        ...,
        description="Count of pending items by department"
    )
    
    by_priority: Dict[str, int] = Field(
        ...,
        description="Count of pending items by priority"
    )


class ApprovalActionResult(BaseModel):
    """Schema for approval action results."""
    
    success: bool = Field(
        ...,
        description="Whether the action was successful"
    )
    
    approval: ApprovalResponse = Field(
        ...,
        description="Created approval record"
    )
    
    work_item: Dict[str, Any] = Field(
        ...,
        description="Updated work item data"
    )
    
    new_state: Dict[str, Any] = Field(
        ...,
        description="New workflow state"
    )
    
    available_actions: List[str] = Field(
        ...,
        description="Available actions for next step"
    )
    
    message: str = Field(
        ...,
        description="Human-readable result message"
    )


class ApprovalStats(BaseModel):
    """Schema for approval statistics."""
    
    total_approvals: int = Field(
        ...,
        description="Total number of approval records"
    )
    
    approved_count: int = Field(
        ...,
        description="Number of approved actions"
    )
    
    rejected_count: int = Field(
        ...,
        description="Number of rejected actions"
    )
    
    cancelled_count: int = Field(
        ...,
        description="Number of cancelled actions"
    )
    
    average_processing_time: Optional[float] = Field(
        None,
        description="Average time between work item creation and approval (hours)"
    )
    
    top_actors: List[Dict[str, Any]] = Field(
        ...,
        description="Top actors by approval count"
    )
    
    recent_activity: List[ApprovalResponse] = Field(
        ...,
        description="Recent approval activity"
    )


class BulkApprovalRequest(BaseModel):
    """Schema for bulk approval operations."""
    
    work_item_ids: List[str] = Field(
        ...,
        min_items=1,
        max_items=50,
        description="List of work item IDs to approve/reject"
    )
    
    action: str = Field(
        ...,
        description="Action to perform on all items"
    )
    
    comment: Optional[str] = Field(
        None,
        description="Common comment for all actions"
    )
    
    actor_name: Optional[str] = Field(
        None,
        description="Name of the person performing bulk action"
    )
    
    @validator('action')
    def validate_bulk_action(cls, v):
        """Validate bulk action."""
        valid_actions = {'approved', 'rejected', 'cancelled'}
        if v.lower() not in valid_actions:
            raise ValueError(f"Action must be one of: {', '.join(valid_actions)}")
        return v.lower()


class BulkApprovalResponse(BaseModel):
    """Schema for bulk approval results."""
    
    successful: List[ApprovalActionResult] = Field(
        ...,
        description="Successfully processed items"
    )
    
    failed: List[Dict[str, Any]] = Field(
        ...,
        description="Failed items with error messages"
    )
    
    total_processed: int = Field(
        ...,
        description="Total number of items processed"
    )
    
    total_successful: int = Field(
        ...,
        description="Number of successful operations"
    )
    
    total_failed: int = Field(
        ...,
        description="Number of failed operations"
    )
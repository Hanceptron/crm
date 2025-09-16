"""
Approval models for the Aviation Workflow System.

Defines the Approval SQLModel matching the schema specified in architecture.md
with foreign key relationships to work_items and departments.
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from sqlmodel import SQLModel, Field, Column, Index, JSON, ForeignKey
from sqlalchemy import String, DateTime, Text


def generate_id() -> str:
    """Generate a unique ID for approvals."""
    return uuid.uuid4().hex


class Approval(SQLModel, table=True):
    """
    Approval model for tracking workflow approval/rejection actions.
    
    Records all approval and rejection actions taken on work items,
    including state transitions and department changes.
    """
    
    __tablename__ = "approvals"
    
    # Primary key with auto-generated UUID
    id: Optional[str] = Field(
        default_factory=generate_id,
        primary_key=True,
        description="Unique identifier for the approval record"
    )
    
    # Foreign key to work items
    work_item_id: str = Field(
        foreign_key="work_items.id",
        description="ID of the work item being approved/rejected"
    )
    
    # Action taken
    action: str = Field(
        max_length=20,
        description="Action taken (approved/rejected/cancelled)"
    )
    
    # State transition information
    from_state: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Previous workflow state"
    )
    
    to_state: Optional[str] = Field(
        default=None,
        max_length=50,
        description="New workflow state after action"
    )
    
    # Department transition information
    from_department_id: Optional[str] = Field(
        default=None,
        foreign_key="departments.id",
        description="Department that processed the approval"
    )
    
    to_department_id: Optional[str] = Field(
        default=None,
        foreign_key="departments.id",
        description="Department the item was sent to"
    )
    
    # Optional comment
    comment: Optional[str] = Field(
        default=None,
        sa_column=Column(Text),
        description="Comment provided with the approval/rejection"
    )
    
    # Actor information
    actor_name: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Name of the person who performed the action"
    )
    
    # Flexible metadata storage
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSON),
        description="Additional approval metadata"
    )
    
    # Audit timestamp
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime),
        description="Timestamp when approval was created"
    )
    
    def __init__(self, **data):
        """Initialize approval with automatic timestamp."""
        super().__init__(**data)
        if not self.created_at:
            self.created_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert approval to dictionary representation.
        
        Returns:
            Dictionary containing all approval fields
        """
        return {
            "id": self.id,
            "work_item_id": self.work_item_id,
            "action": self.action,
            "from_state": self.from_state,
            "to_state": self.to_state,
            "from_department_id": self.from_department_id,
            "to_department_id": self.to_department_id,
            "comment": self.comment,
            "actor_name": self.actor_name,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Approval":
        """
        Create approval from dictionary representation.
        
        Args:
            data: Dictionary containing approval fields
            
        Returns:
            New Approval instance
        """
        # Handle datetime conversion
        if "created_at" in data and isinstance(data["created_at"], str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        
        # Handle JSON fields
        if "metadata" in data and isinstance(data["metadata"], str):
            import json
            data["metadata"] = json.loads(data["metadata"])
        
        return cls(**data)
    
    def is_approval(self) -> bool:
        """Check if this is an approval action."""
        return self.action == "approved"
    
    def is_rejection(self) -> bool:
        """Check if this is a rejection action."""
        return self.action == "rejected"
    
    def is_cancellation(self) -> bool:
        """Check if this is a cancellation action."""
        return self.action == "cancelled"
    
    def has_comment(self) -> bool:
        """Check if approval has a comment."""
        return self.comment is not None and self.comment.strip() != ""
    
    def get_metadata_value(self, key: str, default: Any = None) -> Any:
        """
        Get a metadata value.
        
        Args:
            key: Metadata key
            default: Default value if key not found
            
        Returns:
            Metadata value or default
        """
        return self.metadata.get(key, default) if self.metadata else default
    
    def set_metadata_value(self, key: str, value: Any) -> None:
        """
        Set a metadata value.
        
        Args:
            key: Metadata key
            value: Metadata value
        """
        if self.metadata is None:
            self.metadata = {}
        self.metadata[key] = value
    
    def get_transition_summary(self) -> str:
        """
        Get a human-readable summary of the state transition.
        
        Returns:
            String describing the transition
        """
        if self.is_approval():
            if self.from_state and self.to_state:
                return f"Approved: {self.from_state} → {self.to_state}"
            else:
                return "Approved"
        elif self.is_rejection():
            if self.from_state and self.to_state:
                return f"Rejected: {self.from_state} → {self.to_state}"
            else:
                return "Rejected"
        elif self.is_cancellation():
            return "Cancelled"
        else:
            return f"Action: {self.action}"
    
    def __str__(self) -> str:
        """String representation of approval."""
        return f"Approval({self.action} for {self.work_item_id})"
    
    def __repr__(self) -> str:
        """Developer representation of approval."""
        return (f"Approval(id='{self.id}', work_item_id='{self.work_item_id}', "
                f"action='{self.action}', actor='{self.actor_name}')")


# Define indexes for performance
approval_work_item_index = Index("idx_approvals_work_item", Approval.work_item_id)
approval_action_index = Index("idx_approvals_action", Approval.action)
approval_from_dept_index = Index("idx_approvals_from_dept", Approval.from_department_id)
approval_to_dept_index = Index("idx_approvals_to_dept", Approval.to_department_id)
approval_created_at_index = Index("idx_approvals_created_at", Approval.created_at)
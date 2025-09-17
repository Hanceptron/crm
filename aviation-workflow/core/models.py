"""
Core data models for the Aviation Workflow System.

Contains the WorkItem model which represents the central entity
flowing through the workflow system. This is the only core model
- all other models are provided by pluggable modules.
"""

import json
import uuid
from datetime import datetime
from typing import Any, Dict, Optional
from sqlmodel import SQLModel, Field, Column, Index, JSON
from sqlalchemy import String, DateTime, Integer, Text


def generate_id() -> str:
    """Generate a unique ID for work items."""
    return uuid.uuid4().hex


class WorkItem(SQLModel, table=True):
    """
    Core work item model representing items flowing through workflows.
    
    This is the central entity in the system. Work items move through
    configurable department sequences with approval/rejection actions.
    All workflow state is managed by the Burr engine.
    """
    
    __tablename__ = "work_items"
    
    # Primary key with auto-generated UUID
    id: Optional[str] = Field(
        default_factory=generate_id,
        primary_key=True,
        description="Unique identifier for the work item"
    )
    
    # Basic work item information
    title: str = Field(
        max_length=255,
        description="Work item title"
    )
    
    description: Optional[str] = Field(
        default=None,
        sa_column=Column(Text),
        description="Detailed description of the work item"
    )
    
    # Workflow configuration
    workflow_template: str = Field(
        max_length=100,
        description="References workflow configuration template"
    )
    
    # Workflow state (managed by Burr)
    current_state: str = Field(
        max_length=50,
        description="Current Burr workflow state"
    )
    
    current_step: int = Field(
        default=0,
        description="Current step in the department sequence"
    )
    
    workflow_data: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        description="Serialized Burr workflow state and data"
    )
    
    # Additional flexible data
    item_metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSON),
        description="Flexible additional metadata"
    )
    
    # Status and priority
    status: str = Field(
        default="active",
        max_length=20,
        description="Work item status: active/completed/cancelled"
    )
    
    priority: str = Field(
        default="normal",
        max_length=20,
        description="Priority level: normal/urgent"
    )
    
    # Audit fields
    created_by: str = Field(
        default="system",
        max_length=100,
        description="User who created the work item"
    )
    
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime),
        description="Timestamp when work item was created"
    )
    
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime),
        description="Timestamp when work item was last updated"
    )
    
    def __init__(self, **data):
        """Initialize work item with automatic timestamp updates."""
        super().__init__(**data)
        if not self.updated_at:
            self.updated_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert work item to dictionary representation.
        
        Returns:
            Dictionary containing all work item fields with JSON-serializable values
        """
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "workflow_template": self.workflow_template,
            "current_state": self.current_state,
            "current_step": self.current_step,
            "workflow_data": self.workflow_data,
            "metadata": self.item_metadata,
            "status": self.status,
            "priority": self.priority,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkItem":
        """
        Create work item from dictionary representation.
        
        Args:
            data: Dictionary containing work item fields
            
        Returns:
            New WorkItem instance
        """
        # Handle datetime conversion
        if "created_at" in data and isinstance(data["created_at"], str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        
        if "updated_at" in data and isinstance(data["updated_at"], str):
            data["updated_at"] = datetime.fromisoformat(data["updated_at"])
        
        # Handle JSON fields
        if "workflow_data" in data and isinstance(data["workflow_data"], str):
            data["workflow_data"] = json.loads(data["workflow_data"])
        
        if "metadata" in data and isinstance(data["metadata"], str):
            data["metadata"] = json.loads(data["metadata"])
        
        # Map metadata field to item_metadata
        if "metadata" in data:
            data["item_metadata"] = data.pop("metadata")
        
        return cls(**data)
    
    def update_timestamp(self) -> None:
        """Update the updated_at timestamp to current time."""
        self.updated_at = datetime.utcnow()
    
    def is_active(self) -> bool:
        """Check if work item is in active status."""
        return self.status == "active"
    
    def is_completed(self) -> bool:
        """Check if work item is completed."""
        return self.status == "completed"
    
    def is_cancelled(self) -> bool:
        """Check if work item is cancelled."""
        return self.status == "cancelled"
    
    def is_urgent(self) -> bool:
        """Check if work item has urgent priority."""
        return self.priority == "urgent"
    
    def get_workflow_data_value(self, key: str, default: Any = None) -> Any:
        """
        Get value from workflow_data with default fallback.
        
        Args:
            key: Key to retrieve from workflow_data
            default: Default value if key not found
            
        Returns:
            Value from workflow_data or default
        """
        return self.workflow_data.get(key, default)
    
    def set_workflow_data_value(self, key: str, value: Any) -> None:
        """
        Set value in workflow_data and update timestamp.
        
        Args:
            key: Key to set in workflow_data
            value: Value to set
        """
        if self.workflow_data is None:
            self.workflow_data = {}
        self.workflow_data[key] = value
        self.update_timestamp()
    
    def add_to_history(self, action: str, **kwargs) -> None:
        """
        Add an entry to the workflow history.
        
        Args:
            action: Action taken (approve, reject, etc.)
            **kwargs: Additional data to store in history entry
        """
        if self.workflow_data is None:
            self.workflow_data = {}
        
        if "history" not in self.workflow_data:
            self.workflow_data["history"] = []
        
        history_entry = {
            "action": action,
            "timestamp": datetime.utcnow().isoformat(),
            "from_step": self.current_step,
            "from_state": self.current_state,
            **kwargs
        }
        
        self.workflow_data["history"].append(history_entry)
        self.update_timestamp()


# Define indexes as specified in architecture
work_items_status_index = Index("idx_work_items_status", WorkItem.status)
work_items_current_state_index = Index("idx_work_items_current_state", WorkItem.current_state)
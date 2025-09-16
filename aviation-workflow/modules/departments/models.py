"""
Department models for the Aviation Workflow System.

Defines the Department SQLModel matching the schema specified in architecture.md
with all required fields, constraints, and indexes.
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from sqlmodel import SQLModel, Field, Column, Index, JSON
from sqlalchemy import String, DateTime, Boolean, Text


def generate_id() -> str:
    """Generate a unique ID for departments."""
    return uuid.uuid4().hex


class Department(SQLModel, table=True):
    """
    Department model for organizing workflow approvals.
    
    Represents departments that participate in the approval workflow.
    Each department can approve or reject work items in their step.
    """
    
    __tablename__ = "departments"
    
    # Primary key with auto-generated UUID
    id: Optional[str] = Field(
        default_factory=generate_id,
        primary_key=True,
        description="Unique identifier for the department"
    )
    
    # Department name (must be unique)
    name: str = Field(
        max_length=255,
        unique=True,
        description="Department name (unique)"
    )
    
    # Department code (must be unique)
    code: str = Field(
        max_length=50,
        unique=True,
        description="Department code (unique identifier)"
    )
    
    # Optional description
    description: Optional[str] = Field(
        default=None,
        sa_column=Column(Text),
        description="Department description"
    )
    
    # Flexible metadata storage
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSON),
        description="Additional department metadata"
    )
    
    # Active status
    is_active: bool = Field(
        default=True,
        description="Whether the department is active"
    )
    
    # Audit timestamp
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime),
        description="Timestamp when department was created"
    )
    
    def __init__(self, **data):
        """Initialize department with automatic timestamp."""
        super().__init__(**data)
        if not self.created_at:
            self.created_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert department to dictionary representation.
        
        Returns:
            Dictionary containing all department fields
        """
        return {
            "id": self.id,
            "name": self.name,
            "code": self.code,
            "description": self.description,
            "metadata": self.metadata,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Department":
        """
        Create department from dictionary representation.
        
        Args:
            data: Dictionary containing department fields
            
        Returns:
            New Department instance
        """
        # Handle datetime conversion
        if "created_at" in data and isinstance(data["created_at"], str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        
        # Handle JSON fields
        if "metadata" in data and isinstance(data["metadata"], str):
            import json
            data["metadata"] = json.loads(data["metadata"])
        
        return cls(**data)
    
    def activate(self) -> None:
        """Activate the department."""
        self.is_active = True
    
    def deactivate(self) -> None:
        """Deactivate the department (soft delete)."""
        self.is_active = False
    
    def update_metadata(self, key: str, value: Any) -> None:
        """
        Update a metadata field.
        
        Args:
            key: Metadata key
            value: Metadata value
        """
        if self.metadata is None:
            self.metadata = {}
        self.metadata[key] = value
    
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
    
    def __str__(self) -> str:
        """String representation of department."""
        return f"Department({self.code}: {self.name})"
    
    def __repr__(self) -> str:
        """Developer representation of department."""
        return f"Department(id='{self.id}', code='{self.code}', name='{self.name}', active={self.is_active})"


# Define indexes for performance
department_name_index = Index("idx_departments_name", Department.name)
department_code_index = Index("idx_departments_code", Department.code)
department_active_index = Index("idx_departments_active", Department.is_active)
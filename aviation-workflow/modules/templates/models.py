"""
Workflow template models for the Aviation Workflow System.

Provides SQLModel classes for storing and managing reusable workflow configurations.
Templates define department sequences, approval rules, and workflow behavior.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlmodel import SQLModel, Field, Column, DateTime, JSON, Text
from sqlalchemy import func

from core.models import generate_id


class WorkflowTemplate(SQLModel, table=True):
    """
    Workflow template model for storing reusable workflow configurations.
    
    Templates define the structure of workflows including department sequences,
    approval rules, and configurable parameters for work item processing.
    """
    __tablename__ = "workflow_templates"
    
    # Primary key
    id: Optional[str] = Field(default_factory=generate_id, primary_key=True)
    
    # Required fields
    name: str = Field(
        max_length=255,
        unique=True,
        index=True,
        description="Template name (must be unique)"
    )
    
    display_name: str = Field(
        max_length=255,
        description="Human-readable template name"
    )
    
    description: str = Field(
        max_length=1000,
        description="Template description and purpose"
    )
    
    # Workflow configuration
    department_sequence: List[str] = Field(
        sa_column=Column(JSON),
        description="Ordered list of department IDs for workflow progression"
    )
    
    approval_rules: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        description="Approval rules and validation logic"
    )
    
    workflow_config: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        description="Burr workflow configuration and parameters"
    )
    
    # Template metadata
    category: str = Field(
        default="general",
        max_length=100,
        index=True,
        description="Template category for organization"
    )
    
    version: str = Field(
        default="1.0.0",
        max_length=50,
        description="Template version"
    )
    
    tags: List[str] = Field(
        default_factory=list,
        sa_column=Column(JSON),
        description="Tags for template classification"
    )
    
    # Status and lifecycle
    is_active: bool = Field(
        default=True,
        index=True,
        description="Whether template is active and available for use"
    )
    
    is_default: bool = Field(
        default=False,
        index=True,
        description="Whether this is the default template for its category"
    )
    
    # Usage tracking
    usage_count: int = Field(
        default=0,
        description="Number of times this template has been used"
    )
    
    # Additional configuration
    template_data: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        description="Additional template configuration and metadata"
    )
    
    # Ownership and permissions
    created_by: str = Field(
        max_length=255,
        description="User who created this template"
    )
    
    # Timestamps
    created_at: datetime = Field(
        default_factory=datetime.now,
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
        description="When the template was created"
    )
    
    updated_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), onupdate=func.now()),
        description="When the template was last updated"
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert template to dictionary representation.
        
        Returns:
            Dictionary with template data
        """
        return {
            "id": self.id,
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "department_sequence": self.department_sequence,
            "approval_rules": self.approval_rules,
            "workflow_config": self.workflow_config,
            "category": self.category,
            "version": self.version,
            "tags": self.tags,
            "is_active": self.is_active,
            "is_default": self.is_default,
            "usage_count": self.usage_count,
            "template_data": self.template_data,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    def get_department_count(self) -> int:
        """
        Get the number of departments in the sequence.
        
        Returns:
            Number of departments in the workflow sequence
        """
        return len(self.department_sequence) if self.department_sequence else 0
    
    def get_max_steps(self) -> int:
        """
        Get the maximum number of workflow steps.
        
        Returns:
            Maximum step number (department count - 1)
        """
        return max(0, self.get_department_count() - 1)
    
    def is_valid_step(self, step: int) -> bool:
        """
        Check if a step number is valid for this template.
        
        Args:
            step: Step number to validate
            
        Returns:
            True if step is valid, False otherwise
        """
        return 0 <= step < self.get_department_count()
    
    def get_department_at_step(self, step: int) -> Optional[str]:
        """
        Get the department ID at a specific step.
        
        Args:
            step: Step number
            
        Returns:
            Department ID at the step, or None if invalid step
        """
        if not self.is_valid_step(step):
            return None
        return self.department_sequence[step]
    
    def get_next_department(self, current_step: int) -> Optional[str]:
        """
        Get the next department in the sequence.
        
        Args:
            current_step: Current workflow step
            
        Returns:
            Next department ID, or None if at end of sequence
        """
        next_step = current_step + 1
        return self.get_department_at_step(next_step)
    
    def get_previous_department(self, current_step: int) -> Optional[str]:
        """
        Get the previous department in the sequence.
        
        Args:
            current_step: Current workflow step
            
        Returns:
            Previous department ID, or None if at beginning of sequence
        """
        prev_step = current_step - 1
        return self.get_department_at_step(prev_step)
    
    def can_approve_from_step(self, step: int) -> bool:
        """
        Check if approval is allowed from a specific step.
        
        Args:
            step: Step number to check
            
        Returns:
            True if approval is allowed, False otherwise
        """
        # Can approve unless at the final step
        return self.is_valid_step(step) and step < self.get_max_steps()
    
    def can_reject_to_step(self, from_step: int, to_step: int) -> bool:
        """
        Check if rejection to a specific step is allowed.
        
        Args:
            from_step: Current step
            to_step: Target step for rejection
            
        Returns:
            True if rejection is allowed, False otherwise
        """
        # Can reject to any previous step
        return (self.is_valid_step(from_step) and 
                self.is_valid_step(to_step) and 
                to_step < from_step)
    
    def get_approval_rule(self, rule_name: str, default: Any = None) -> Any:
        """
        Get a specific approval rule value.
        
        Args:
            rule_name: Name of the approval rule
            default: Default value if rule not found
            
        Returns:
            Rule value or default
        """
        return self.approval_rules.get(rule_name, default)
    
    def requires_comment_for_rejection(self) -> bool:
        """
        Check if comments are required for rejections.
        
        Returns:
            True if comment is required for rejection, False otherwise
        """
        return self.get_approval_rule("require_comment_for_rejection", True)
    
    def allows_skip_steps(self) -> bool:
        """
        Check if skipping steps is allowed.
        
        Returns:
            True if step skipping is allowed, False otherwise
        """
        return self.get_approval_rule("allow_skip_steps", False)
    
    def get_min_approvals_per_step(self) -> int:
        """
        Get minimum number of approvals required per step.
        
        Returns:
            Minimum approvals required (default 1)
        """
        return self.get_approval_rule("min_approvals_per_step", 1)
    
    def increment_usage(self) -> None:
        """Increment the usage counter for this template."""
        self.usage_count += 1
    
    def __repr__(self) -> str:
        """String representation of template."""
        return f"<WorkflowTemplate(id={self.id}, name={self.name}, active={self.is_active})>"
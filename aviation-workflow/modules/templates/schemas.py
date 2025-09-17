"""
Pydantic schemas for the templates module.

Defines request and response schemas for workflow template operations.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, validator


class TemplateRequest(BaseModel):
    """Schema for creating a new workflow template."""
    
    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Template name (must be unique)"
    )
    
    display_name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Human-readable template name"
    )
    
    description: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Template description and purpose"
    )
    
    department_sequence: List[str] = Field(
        ...,
        min_items=1,
        description="Ordered list of department IDs for workflow progression"
    )
    
    approval_rules: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Approval rules and validation logic"
    )
    
    workflow_config: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Burr workflow configuration and parameters"
    )
    
    category: Optional[str] = Field(
        default="general",
        max_length=100,
        description="Template category for organization"
    )
    
    version: Optional[str] = Field(
        default="1.0.0",
        max_length=50,
        description="Template version"
    )
    
    tags: Optional[List[str]] = Field(
        default_factory=list,
        description="Tags for template classification"
    )
    
    is_active: Optional[bool] = Field(
        default=True,
        description="Whether template is active and available for use"
    )
    
    is_default: Optional[bool] = Field(
        default=False,
        description="Whether this is the default template for its category"
    )
    
    template_data: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Additional template configuration and metadata"
    )
    
    created_by: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="User who created this template"
    )
    
    @validator('name')
    def validate_name(cls, v):
        """Validate template name."""
        if not v or not v.strip():
            raise ValueError('Template name cannot be empty')
        # Convert to lowercase with underscores for consistency
        return v.strip().lower().replace(' ', '_').replace('-', '_')
    
    @validator('department_sequence')
    def validate_department_sequence(cls, v):
        """Validate department sequence."""
        if not v or len(v) == 0:
            raise ValueError('Department sequence cannot be empty')
        
        # Check for duplicates
        if len(v) != len(set(v)):
            raise ValueError('Department sequence cannot contain duplicates')
        
        # Ensure all department IDs are valid strings
        for i, dept_id in enumerate(v):
            if not isinstance(dept_id, str) or not dept_id.strip():
                raise ValueError(f'Department ID at position {i} is invalid')
        
        return [dept_id.strip() for dept_id in v]
    
    @validator('approval_rules')
    def validate_approval_rules(cls, v):
        """Validate approval rules."""
        if v is None:
            return {}
        
        # Validate specific rules if present
        if 'min_approvals_per_step' in v:
            min_approvals = v['min_approvals_per_step']
            if not isinstance(min_approvals, int) or min_approvals < 1:
                raise ValueError('min_approvals_per_step must be a positive integer')
        
        if 'require_comment_for_rejection' in v:
            if not isinstance(v['require_comment_for_rejection'], bool):
                raise ValueError('require_comment_for_rejection must be a boolean')
        
        if 'allow_skip_steps' in v:
            if not isinstance(v['allow_skip_steps'], bool):
                raise ValueError('allow_skip_steps must be a boolean')
        
        if 'escalation_timeout_hours' in v:
            timeout = v['escalation_timeout_hours']
            if not isinstance(timeout, (int, float)) or timeout <= 0:
                raise ValueError('escalation_timeout_hours must be a positive number')
        
        return v
    
    @validator('category')
    def validate_category(cls, v):
        """Validate category."""
        if v:
            allowed_categories = [
                'general', 'engineering', 'quality', 'operations', 
                'maintenance', 'safety', 'compliance', 'administrative'
            ]
            if v.lower() not in allowed_categories:
                raise ValueError(f'Category must be one of: {", ".join(allowed_categories)}')
            return v.lower()
        return v


class TemplateUpdateRequest(BaseModel):
    """Schema for updating an existing workflow template."""
    
    display_name: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Human-readable template name"
    )
    
    description: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Template description and purpose"
    )
    
    department_sequence: Optional[List[str]] = Field(
        default=None,
        min_items=1,
        description="Ordered list of department IDs for workflow progression"
    )
    
    approval_rules: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Approval rules and validation logic"
    )
    
    workflow_config: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Burr workflow configuration and parameters"
    )
    
    category: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Template category for organization"
    )
    
    version: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Template version"
    )
    
    tags: Optional[List[str]] = Field(
        default=None,
        description="Tags for template classification"
    )
    
    is_active: Optional[bool] = Field(
        default=None,
        description="Whether template is active and available for use"
    )
    
    is_default: Optional[bool] = Field(
        default=None,
        description="Whether this is the default template for its category"
    )
    
    template_data: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional template configuration and metadata"
    )
    
    @validator('department_sequence')
    def validate_department_sequence(cls, v):
        """Validate department sequence."""
        if v is not None:
            if len(v) == 0:
                raise ValueError('Department sequence cannot be empty')
            
            # Check for duplicates
            if len(v) != len(set(v)):
                raise ValueError('Department sequence cannot contain duplicates')
            
            # Ensure all department IDs are valid strings
            for i, dept_id in enumerate(v):
                if not isinstance(dept_id, str) or not dept_id.strip():
                    raise ValueError(f'Department ID at position {i} is invalid')
            
            return [dept_id.strip() for dept_id in v]
        return v


class TemplateResponse(BaseModel):
    """Schema for template response data."""
    
    id: str
    name: str
    display_name: str
    description: str
    department_sequence: List[str]
    approval_rules: Dict[str, Any]
    workflow_config: Dict[str, Any]
    category: str
    version: str
    tags: List[str]
    is_active: bool
    is_default: bool
    usage_count: int
    template_data: Dict[str, Any]
    created_by: str
    created_at: str
    updated_at: Optional[str]
    
    # Computed fields
    department_count: Optional[int] = None
    max_steps: Optional[int] = None
    
    class Config:
        """Pydantic config."""
        from_attributes = True


class TemplateListResponse(BaseModel):
    """Schema for listing templates."""
    
    templates: List[TemplateResponse]
    total: int
    
    # Statistics
    by_category: Dict[str, int] = Field(
        default_factory=dict,
        description="Template count by category"
    )
    by_status: Dict[str, int] = Field(
        default_factory=dict,
        description="Template count by status (active/inactive)"
    )
    total_usage: int = Field(
        default=0,
        description="Total usage count across all templates"
    )


class TemplateValidationRequest(BaseModel):
    """Schema for template validation requests."""
    
    department_sequence: List[str] = Field(
        ...,
        min_items=1,
        description="Department sequence to validate"
    )
    
    approval_rules: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Approval rules to validate"
    )
    
    check_department_existence: Optional[bool] = Field(
        default=True,
        description="Whether to check if departments exist in the system"
    )
    
    @validator('department_sequence')
    def validate_department_sequence(cls, v):
        """Validate department sequence."""
        if not v or len(v) == 0:
            raise ValueError('Department sequence cannot be empty')
        
        # Check for duplicates
        if len(v) != len(set(v)):
            raise ValueError('Department sequence cannot contain duplicates')
        
        # Ensure all department IDs are valid strings
        for i, dept_id in enumerate(v):
            if not isinstance(dept_id, str) or not dept_id.strip():
                raise ValueError(f'Department ID at position {i} is invalid')
        
        return [dept_id.strip() for dept_id in v]


class TemplateValidationResponse(BaseModel):
    """Schema for template validation results."""
    
    is_valid: bool
    errors: List[str] = Field(
        default_factory=list,
        description="Validation error messages"
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Validation warning messages"
    )
    
    # Validation details
    department_validation: Dict[str, Any] = Field(
        default_factory=dict,
        description="Department validation details"
    )
    approval_rules_validation: Dict[str, Any] = Field(
        default_factory=dict,
        description="Approval rules validation details"
    )
    
    # Computed information
    department_count: int
    max_steps: int
    estimated_completion_time: Optional[str] = None


class TemplateStats(BaseModel):
    """Schema for template statistics."""
    
    total_templates: int
    active_templates: int
    inactive_templates: int
    default_templates: int
    
    by_category: Dict[str, int] = Field(
        description="Template count by category"
    )
    by_usage: Dict[str, int] = Field(
        description="Usage statistics"
    )
    
    most_used_templates: List[TemplateResponse]
    recent_templates: List[TemplateResponse]


class TemplateUsageRequest(BaseModel):
    """Schema for template usage tracking."""
    
    work_item_id: str = Field(
        ...,
        description="Work item ID that used this template"
    )
    
    used_by: str = Field(
        ...,
        description="User who used this template"
    )
    
    usage_context: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Additional context about template usage"
    )
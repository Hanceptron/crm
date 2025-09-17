"""
Pydantic schemas for the comments module.

Defines request and response schemas for comment operations.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, validator


class CommentRequest(BaseModel):
    """Schema for creating a new comment."""
    
    work_item_id: str = Field(
        ...,
        min_length=1,
        description="ID of the work item to comment on"
    )
    
    content: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="Comment content"
    )
    
    author_name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Name of the comment author"
    )
    
    comment_type: Optional[str] = Field(
        default="general",
        max_length=50,
        description="Type of comment"
    )
    
    is_internal: Optional[bool] = Field(
        default=False,
        description="Whether this is an internal comment"
    )
    
    parent_comment_id: Optional[str] = Field(
        default=None,
        description="ID of parent comment for replies"
    )
    
    additional_data: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Additional comment data and metadata"
    )
    
    @validator('content')
    def validate_content(cls, v):
        """Validate comment content."""
        if not v or not v.strip():
            raise ValueError('Comment content cannot be empty')
        return v.strip()
    
    @validator('comment_type')
    def validate_comment_type(cls, v):
        """Validate comment type."""
        if v:
            allowed_types = [
                'general', 'review', 'note', 'question', 'clarification',
                'approval', 'rejection', 'escalation', 'technical', 'business'
            ]
            if v.lower() not in allowed_types:
                raise ValueError(f'Comment type must be one of: {", ".join(allowed_types)}')
            return v.lower()
        return v


class CommentUpdateRequest(BaseModel):
    """Schema for updating an existing comment."""
    
    content: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="Updated comment content"
    )
    
    comment_type: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Updated comment type"
    )
    
    is_internal: Optional[bool] = Field(
        default=None,
        description="Updated internal flag"
    )
    
    additional_data: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Updated comment data and metadata"
    )
    
    @validator('content')
    def validate_content(cls, v):
        """Validate comment content."""
        if not v or not v.strip():
            raise ValueError('Comment content cannot be empty')
        return v.strip()
    
    @validator('comment_type')
    def validate_comment_type(cls, v):
        """Validate comment type."""
        if v:
            allowed_types = [
                'general', 'review', 'note', 'question', 'clarification',
                'approval', 'rejection', 'escalation', 'technical', 'business'
            ]
            if v.lower() not in allowed_types:
                raise ValueError(f'Comment type must be one of: {", ".join(allowed_types)}')
            return v.lower()
        return v


class CommentResponse(BaseModel):
    """Schema for comment response data."""
    
    id: str
    work_item_id: str
    content: str
    author_name: str
    comment_type: str
    is_internal: bool
    parent_comment_id: Optional[str]
    additional_data: Dict[str, Any]
    created_at: str
    updated_at: Optional[str]
    
    class Config:
        """Pydantic config."""
        from_attributes = True


class CommentListResponse(BaseModel):
    """Schema for listing comments."""
    
    comments: List[CommentResponse]
    total: int
    work_item_id: str
    
    # Statistics
    by_author: Dict[str, int] = Field(
        default_factory=dict,
        description="Comment count by author"
    )
    by_type: Dict[str, int] = Field(
        default_factory=dict,
        description="Comment count by type"
    )
    has_internal: bool = Field(
        default=False,
        description="Whether there are internal comments"
    )


class CommentStats(BaseModel):
    """Schema for comment statistics."""
    
    total_comments: int
    by_work_item: Dict[str, int] = Field(
        description="Comment count by work item"
    )
    by_author: Dict[str, int] = Field(
        description="Comment count by author"
    )
    by_type: Dict[str, int] = Field(
        description="Comment count by type"
    )
    internal_comments: int
    recent_activity: List[CommentResponse]


class BulkCommentRequest(BaseModel):
    """Schema for bulk comment operations."""
    
    comment_ids: List[str] = Field(
        ...,
        min_items=1,
        description="List of comment IDs"
    )
    
    action: str = Field(
        ...,
        description="Action to perform (delete, toggle_internal)"
    )
    
    author_name: str = Field(
        ...,
        description="Name of the person performing the action"
    )
    
    @validator('action')
    def validate_action(cls, v):
        """Validate bulk action."""
        allowed_actions = ['delete', 'toggle_internal']
        if v.lower() not in allowed_actions:
            raise ValueError(f'Action must be one of: {", ".join(allowed_actions)}')
        return v.lower()


class BulkCommentResponse(BaseModel):
    """Schema for bulk comment operation results."""
    
    successful: List[str] = Field(
        description="IDs of successfully processed comments"
    )
    failed: List[Dict[str, str]] = Field(
        description="Failed operations with error messages"
    )
    total_processed: int
    total_successful: int
    total_failed: int
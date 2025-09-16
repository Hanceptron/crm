"""
Comment models for the Aviation Workflow System.

Provides SQLModel classes for storing and managing comments on work items.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from sqlmodel import SQLModel, Field, Column, DateTime, JSON
from sqlalchemy import func

from core.models import generate_id


class Comment(SQLModel, table=True):
    """
    Comment model for storing comments on work items.
    
    Represents user comments and notes attached to work items in the workflow.
    Comments are standalone entities that can be added, retrieved, and deleted
    without affecting the work item workflow.
    """
    __tablename__ = "comments"
    
    # Primary key
    id: Optional[str] = Field(default_factory=generate_id, primary_key=True)
    
    # Required fields
    work_item_id: str = Field(
        foreign_key="work_items.id",
        index=True,
        description="ID of the work item this comment belongs to"
    )
    
    content: str = Field(
        min_length=1,
        max_length=5000,
        description="Comment content"
    )
    
    author_name: str = Field(
        max_length=255,
        description="Name of the person who created the comment"
    )
    
    # Optional fields
    comment_type: str = Field(
        default="general",
        max_length=50,
        description="Type of comment (general, review, note, question, etc.)"
    )
    
    is_internal: bool = Field(
        default=False,
        description="Whether this comment is internal (not visible to external parties)"
    )
    
    parent_comment_id: Optional[str] = Field(
        default=None,
        foreign_key="comments.id",
        description="ID of parent comment for threading (optional)"
    )
    
    # Metadata
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        description="Additional comment metadata"
    )
    
    # Timestamps
    created_at: datetime = Field(
        default_factory=datetime.now,
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
        description="When the comment was created"
    )
    
    updated_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), onupdate=func.now()),
        description="When the comment was last updated (if edited)"
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert comment to dictionary representation.
        
        Returns:
            Dictionary with comment data
        """
        return {
            "id": self.id,
            "work_item_id": self.work_item_id,
            "content": self.content,
            "author_name": self.author_name,
            "comment_type": self.comment_type,
            "is_internal": self.is_internal,
            "parent_comment_id": self.parent_comment_id,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    def is_reply(self) -> bool:
        """
        Check if this comment is a reply to another comment.
        
        Returns:
            True if this is a reply, False otherwise
        """
        return self.parent_comment_id is not None
    
    def is_editable(self) -> bool:
        """
        Check if this comment can be edited.
        
        Returns:
            True if comment can be edited, False otherwise
            
        Note:
            Currently allows editing of all comments.
            Can be extended with business rules.
        """
        return True
    
    def get_content_preview(self, max_length: int = 100) -> str:
        """
        Get a preview of the comment content.
        
        Args:
            max_length: Maximum length of preview
            
        Returns:
            Preview string
        """
        if len(self.content) <= max_length:
            return self.content
        return self.content[:max_length-3] + "..."
    
    def __repr__(self) -> str:
        """String representation of comment."""
        return f"<Comment(id={self.id}, work_item_id={self.work_item_id}, author={self.author_name})>"
"""
Comment service for the Aviation Workflow System.

Provides business logic and data operations for comment management.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from sqlmodel import Session, select, func, desc, asc
from sqlalchemy.exc import IntegrityError

from core.models import WorkItem
from .models import Comment
from .schemas import CommentRequest, CommentUpdateRequest

logger = logging.getLogger(__name__)


class CommentServiceError(Exception):
    """Base exception for comment service errors."""
    pass


class CommentNotFoundError(CommentServiceError):
    """Raised when a comment is not found."""
    pass


class WorkItemNotFoundError(CommentServiceError):
    """Raised when a work item is not found."""
    pass


class CommentService:
    """
    Service class for comment operations.
    
    Provides methods for creating, retrieving, updating, and deleting comments
    on work items in the workflow system.
    """
    
    def __init__(self, session: Session):
        """
        Initialize comment service.
        
        Args:
            session: Database session
        """
        self.session = session
    
    def add_comment(self, comment_data: CommentRequest) -> Comment:
        """
        Add a new comment to a work item.
        
        Args:
            comment_data: Comment request data
            
        Returns:
            Created comment
            
        Raises:
            WorkItemNotFoundError: If work item doesn't exist
            CommentServiceError: If comment creation fails
        """
        try:
            # Verify work item exists
            work_item = self.session.get(WorkItem, comment_data.work_item_id)
            if not work_item:
                raise WorkItemNotFoundError(f"Work item {comment_data.work_item_id} not found")
            
            # Verify parent comment exists if specified
            if comment_data.parent_comment_id:
                parent_comment = self.session.get(Comment, comment_data.parent_comment_id)
                if not parent_comment:
                    raise CommentServiceError(f"Parent comment {comment_data.parent_comment_id} not found")
                
                # Ensure parent comment is for the same work item
                if parent_comment.work_item_id != comment_data.work_item_id:
                    raise CommentServiceError("Parent comment must be for the same work item")
            
            # Create comment
            comment = Comment(
                work_item_id=comment_data.work_item_id,
                content=comment_data.content,
                author_name=comment_data.author_name,
                comment_type=comment_data.comment_type or "general",
                is_internal=comment_data.is_internal or False,
                parent_comment_id=comment_data.parent_comment_id,
                additional_data=comment_data.additional_data or {}
            )
            
            self.session.add(comment)
            self.session.commit()
            self.session.refresh(comment)
            
            logger.info(f"Created comment {comment.id} for work item {comment_data.work_item_id}")
            return comment
            
        except (WorkItemNotFoundError, CommentServiceError):
            self.session.rollback()
            raise
        except IntegrityError as e:
            self.session.rollback()
            logger.error(f"Database integrity error creating comment: {e}")
            raise CommentServiceError(f"Failed to create comment: database constraint violation")
        except Exception as e:
            self.session.rollback()
            logger.error(f"Unexpected error creating comment: {e}")
            raise CommentServiceError(f"Failed to create comment: {str(e)}")
    
    def get_comments_for_item(self, work_item_id: str, 
                             include_internal: bool = True,
                             author_filter: Optional[str] = None,
                             comment_type_filter: Optional[str] = None,
                             limit: Optional[int] = None,
                             offset: int = 0) -> List[Comment]:
        """
        Get all comments for a work item.
        
        Args:
            work_item_id: Work item identifier
            include_internal: Whether to include internal comments
            author_filter: Filter by author name
            comment_type_filter: Filter by comment type
            limit: Maximum number of comments to return
            offset: Number of comments to skip
            
        Returns:
            List of comments ordered by creation time
            
        Raises:
            WorkItemNotFoundError: If work item doesn't exist
        """
        try:
            # Verify work item exists
            work_item = self.session.get(WorkItem, work_item_id)
            if not work_item:
                raise WorkItemNotFoundError(f"Work item {work_item_id} not found")
            
            # Build query
            query = select(Comment).where(Comment.work_item_id == work_item_id)
            
            # Apply filters
            if not include_internal:
                query = query.where(Comment.is_internal == False)
            
            if author_filter:
                query = query.where(Comment.author_name.ilike(f"%{author_filter}%"))
            
            if comment_type_filter:
                query = query.where(Comment.comment_type == comment_type_filter)
            
            # Order by creation time (oldest first)
            query = query.order_by(asc(Comment.created_at))
            
            # Apply pagination
            if offset > 0:
                query = query.offset(offset)
            if limit:
                query = query.limit(limit)
            
            comments = list(self.session.exec(query).all())
            
            logger.debug(f"Retrieved {len(comments)} comments for work item {work_item_id}")
            return comments
            
        except WorkItemNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error retrieving comments for work item {work_item_id}: {e}")
            raise CommentServiceError(f"Failed to retrieve comments: {str(e)}")
    
    def get_comment(self, comment_id: str) -> Comment:
        """
        Get a single comment by ID.
        
        Args:
            comment_id: Comment identifier
            
        Returns:
            Comment instance
            
        Raises:
            CommentNotFoundError: If comment doesn't exist
        """
        comment = self.session.get(Comment, comment_id)
        if not comment:
            raise CommentNotFoundError(f"Comment {comment_id} not found")
        return comment
    
    def update_comment(self, comment_id: str, update_data: CommentUpdateRequest) -> Comment:
        """
        Update an existing comment.
        
        Args:
            comment_id: Comment identifier
            update_data: Updated comment data
            
        Returns:
            Updated comment
            
        Raises:
            CommentNotFoundError: If comment doesn't exist
            CommentServiceError: If update fails
        """
        try:
            comment = self.get_comment(comment_id)
            
            # Check if comment is editable
            if not comment.is_editable():
                raise CommentServiceError(f"Comment {comment_id} is not editable")
            
            # Update fields
            comment.content = update_data.content
            comment.updated_at = datetime.now()
            
            if update_data.comment_type is not None:
                comment.comment_type = update_data.comment_type
            
            if update_data.is_internal is not None:
                comment.is_internal = update_data.is_internal
            
            if update_data.additional_data is not None:
                comment.additional_data = update_data.additional_data
            
            self.session.add(comment)
            self.session.commit()
            self.session.refresh(comment)
            
            logger.info(f"Updated comment {comment_id}")
            return comment
            
        except CommentNotFoundError:
            raise
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error updating comment {comment_id}: {e}")
            raise CommentServiceError(f"Failed to update comment: {str(e)}")
    
    def delete_comment(self, comment_id: str) -> bool:
        """
        Delete a comment.
        
        Args:
            comment_id: Comment identifier
            
        Returns:
            True if comment was deleted
            
        Raises:
            CommentNotFoundError: If comment doesn't exist
            CommentServiceError: If deletion fails
        """
        try:
            comment = self.get_comment(comment_id)
            
            # Check if there are child comments (replies)
            child_comments = list(self.session.exec(
                select(Comment).where(Comment.parent_comment_id == comment_id)
            ).all())
            
            if child_comments:
                # Option 1: Prevent deletion if there are replies
                raise CommentServiceError(
                    f"Cannot delete comment {comment_id} because it has {len(child_comments)} replies. "
                    f"Delete replies first."
                )
                
                # Option 2: Delete replies as well (cascade delete)
                # for child in child_comments:
                #     self.session.delete(child)
            
            self.session.delete(comment)
            self.session.commit()
            
            logger.info(f"Deleted comment {comment_id}")
            return True
            
        except CommentNotFoundError:
            raise
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error deleting comment {comment_id}: {e}")
            raise CommentServiceError(f"Failed to delete comment: {str(e)}")
    
    def get_comment_stats(self) -> Dict[str, Any]:
        """
        Get comment statistics.
        
        Returns:
            Dictionary with comment statistics
        """
        try:
            # Total comment count
            total_comments = self.session.exec(
                select(func.count(Comment.id))
            ).one()
            
            # Comments by work item
            by_work_item = dict(self.session.exec(
                select(Comment.work_item_id, func.count(Comment.id))
                .group_by(Comment.work_item_id)
            ).all())
            
            # Comments by author
            by_author = dict(self.session.exec(
                select(Comment.author_name, func.count(Comment.id))
                .group_by(Comment.author_name)
                .order_by(desc(func.count(Comment.id)))
                .limit(10)  # Top 10 authors
            ).all())
            
            # Comments by type
            by_type = dict(self.session.exec(
                select(Comment.comment_type, func.count(Comment.id))
                .group_by(Comment.comment_type)
            ).all())
            
            # Internal comments count
            internal_comments = self.session.exec(
                select(func.count(Comment.id))
                .where(Comment.is_internal == True)
            ).one()
            
            # Recent activity (last 10 comments)
            recent_activity = list(self.session.exec(
                select(Comment)
                .order_by(desc(Comment.created_at))
                .limit(10)
            ).all())
            
            return {
                "total_comments": total_comments,
                "by_work_item": by_work_item,
                "by_author": by_author,
                "by_type": by_type,
                "internal_comments": internal_comments,
                "recent_activity": recent_activity
            }
            
        except Exception as e:
            logger.error(f"Error getting comment statistics: {e}")
            raise CommentServiceError(f"Failed to get statistics: {str(e)}")
    
    def search_comments(self, search_term: str, 
                       work_item_id: Optional[str] = None,
                       author_filter: Optional[str] = None,
                       include_internal: bool = True,
                       limit: int = 50) -> List[Comment]:
        """
        Search comments by content.
        
        Args:
            search_term: Term to search for in comment content
            work_item_id: Optional work item filter
            author_filter: Optional author filter
            include_internal: Whether to include internal comments
            limit: Maximum results to return
            
        Returns:
            List of matching comments
        """
        try:
            query = select(Comment).where(
                Comment.content.ilike(f"%{search_term}%")
            )
            
            if work_item_id:
                query = query.where(Comment.work_item_id == work_item_id)
            
            if author_filter:
                query = query.where(Comment.author_name.ilike(f"%{author_filter}%"))
            
            if not include_internal:
                query = query.where(Comment.is_internal == False)
            
            query = query.order_by(desc(Comment.created_at)).limit(limit)
            
            comments = list(self.session.exec(query).all())
            
            logger.debug(f"Found {len(comments)} comments matching '{search_term}'")
            return comments
            
        except Exception as e:
            logger.error(f"Error searching comments: {e}")
            raise CommentServiceError(f"Search failed: {str(e)}")
    
    def bulk_delete_comments(self, comment_ids: List[str], 
                            author_name: str) -> Tuple[List[str], List[Dict[str, str]]]:
        """
        Delete multiple comments in bulk.
        
        Args:
            comment_ids: List of comment IDs to delete
            author_name: Name of person performing bulk delete
            
        Returns:
            Tuple of (successful_ids, failed_items)
        """
        successful = []
        failed = []
        
        for comment_id in comment_ids:
            try:
                self.delete_comment(comment_id)
                successful.append(comment_id)
            except Exception as e:
                failed.append({
                    "comment_id": comment_id,
                    "error": str(e)
                })
        
        logger.info(
            f"Bulk delete by {author_name}: {len(successful)} successful, {len(failed)} failed"
        )
        
        return successful, failed
    
    def get_comment_thread(self, parent_comment_id: str) -> List[Comment]:
        """
        Get all replies to a comment (comment thread).
        
        Args:
            parent_comment_id: ID of the parent comment
            
        Returns:
            List of reply comments ordered by creation time
        """
        try:
            # Get parent comment first to verify it exists
            parent_comment = self.get_comment(parent_comment_id)
            
            # Get all replies
            replies = list(self.session.exec(
                select(Comment)
                .where(Comment.parent_comment_id == parent_comment_id)
                .order_by(asc(Comment.created_at))
            ).all())
            
            return [parent_comment] + replies
            
        except CommentNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error getting comment thread for {parent_comment_id}: {e}")
            raise CommentServiceError(f"Failed to get comment thread: {str(e)}")
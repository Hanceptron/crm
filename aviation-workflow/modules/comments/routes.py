"""
API routes for the comments module.

Implements comment endpoints for adding, retrieving, updating, and deleting
comments on work items.
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import Session

from api.dependencies import get_db_session
from .models import Comment
from .schemas import (
    CommentRequest,
    CommentUpdateRequest,
    CommentResponse,
    CommentListResponse,
    CommentStats,
    BulkCommentRequest,
    BulkCommentResponse
)
from .service import CommentService, CommentServiceError, CommentNotFoundError, WorkItemNotFoundError

logger = logging.getLogger(__name__)

# Create router with prefix and tags
router = APIRouter(prefix="/api/comments", tags=["comments"])


def get_comment_service(session: Session = Depends(get_db_session)) -> CommentService:
    """Dependency to get comment service instance."""
    return CommentService(session)


# Core comment endpoints

@router.post("", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
async def add_comment(
    comment_data: CommentRequest,
    service: CommentService = Depends(get_comment_service)
):
    """
    Add a new comment to a work item.
    
    Args:
        comment_data: Comment creation data
        
    Returns:
        Created comment
    """
    try:
        comment = service.add_comment(comment_data)
        
        return CommentResponse(
            id=comment.id,
            work_item_id=comment.work_item_id,
            content=comment.content,
            author_name=comment.author_name,
            comment_type=comment.comment_type,
            is_internal=comment.is_internal,
            parent_comment_id=comment.parent_comment_id,
            additional_data=comment.additional_data,
            created_at=comment.created_at.isoformat(),
            updated_at=comment.updated_at.isoformat() if comment.updated_at else None
        )
        
    except WorkItemNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except CommentServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error adding comment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add comment"
        )


@router.get("/work-item/{work_item_id}", response_model=CommentListResponse)
async def get_comments_for_work_item(
    work_item_id: str,
    include_internal: bool = Query(
        default=True,
        description="Whether to include internal comments"
    ),
    author_filter: Optional[str] = Query(
        default=None,
        description="Filter comments by author name"
    ),
    comment_type_filter: Optional[str] = Query(
        default=None,
        description="Filter comments by type"
    ),
    limit: Optional[int] = Query(
        default=None,
        ge=1,
        le=1000,
        description="Maximum number of comments to return"
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Number of comments to skip"
    ),
    service: CommentService = Depends(get_comment_service)
):
    """
    Get all comments for a work item.
    
    Args:
        work_item_id: Work item identifier
        include_internal: Whether to include internal comments
        author_filter: Optional author name filter
        comment_type_filter: Optional comment type filter
        limit: Maximum number of comments
        offset: Number of comments to skip
        
    Returns:
        List of comments with statistics
    """
    try:
        comments = service.get_comments_for_item(
            work_item_id=work_item_id,
            include_internal=include_internal,
            author_filter=author_filter,
            comment_type_filter=comment_type_filter,
            limit=limit,
            offset=offset
        )
        
        # Convert to response schemas
        comment_responses = [
            CommentResponse(
                id=comment.id,
                work_item_id=comment.work_item_id,
                content=comment.content,
                author_name=comment.author_name,
                comment_type=comment.comment_type,
                is_internal=comment.is_internal,
                parent_comment_id=comment.parent_comment_id,
                additional_data=comment.additional_data,
                created_at=comment.created_at.isoformat(),
                updated_at=comment.updated_at.isoformat() if comment.updated_at else None
            )
            for comment in comments
        ]
        
        # Calculate statistics
        by_author = {}
        by_type = {}
        has_internal = False
        
        for comment in comments:
            # Count by author
            by_author[comment.author_name] = by_author.get(comment.author_name, 0) + 1
            
            # Count by type
            by_type[comment.comment_type] = by_type.get(comment.comment_type, 0) + 1
            
            # Check for internal comments
            if comment.is_internal:
                has_internal = True
        
        return CommentListResponse(
            comments=comment_responses,
            total=len(comment_responses),
            work_item_id=work_item_id,
            by_author=by_author,
            by_type=by_type,
            has_internal=has_internal
        )
        
    except WorkItemNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except CommentServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting comments for work item {work_item_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve comments"
        )


@router.get("/{comment_id}", response_model=CommentResponse)
async def get_comment(
    comment_id: str,
    service: CommentService = Depends(get_comment_service)
):
    """
    Get a single comment by ID.
    
    Args:
        comment_id: Comment identifier
        
    Returns:
        Comment details
    """
    try:
        comment = service.get_comment(comment_id)
        
        return CommentResponse(
            id=comment.id,
            work_item_id=comment.work_item_id,
            content=comment.content,
            author_name=comment.author_name,
            comment_type=comment.comment_type,
            is_internal=comment.is_internal,
            parent_comment_id=comment.parent_comment_id,
            additional_data=comment.additional_data,
            created_at=comment.created_at.isoformat(),
            updated_at=comment.updated_at.isoformat() if comment.updated_at else None
        )
        
    except CommentNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting comment {comment_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve comment"
        )


@router.put("/{comment_id}", response_model=CommentResponse)
async def update_comment(
    comment_id: str,
    update_data: CommentUpdateRequest,
    service: CommentService = Depends(get_comment_service)
):
    """
    Update an existing comment.
    
    Args:
        comment_id: Comment identifier
        update_data: Updated comment data
        
    Returns:
        Updated comment
    """
    try:
        comment = service.update_comment(comment_id, update_data)
        
        return CommentResponse(
            id=comment.id,
            work_item_id=comment.work_item_id,
            content=comment.content,
            author_name=comment.author_name,
            comment_type=comment.comment_type,
            is_internal=comment.is_internal,
            parent_comment_id=comment.parent_comment_id,
            additional_data=comment.additional_data,
            created_at=comment.created_at.isoformat(),
            updated_at=comment.updated_at.isoformat() if comment.updated_at else None
        )
        
    except CommentNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except CommentServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error updating comment {comment_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update comment"
        )


@router.delete("/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    comment_id: str,
    service: CommentService = Depends(get_comment_service)
):
    """
    Delete a comment.
    
    Args:
        comment_id: Comment identifier
    """
    try:
        service.delete_comment(comment_id)
        
    except CommentNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except CommentServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error deleting comment {comment_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete comment"
        )


# Additional utility endpoints

@router.get("/thread/{parent_comment_id}")
async def get_comment_thread(
    parent_comment_id: str,
    service: CommentService = Depends(get_comment_service)
):
    """
    Get a comment thread (parent comment plus all replies).
    
    Args:
        parent_comment_id: ID of the parent comment
        
    Returns:
        Comment thread with parent and replies
    """
    try:
        thread_comments = service.get_comment_thread(parent_comment_id)
        
        thread_responses = [
            CommentResponse(
                id=comment.id,
                work_item_id=comment.work_item_id,
                content=comment.content,
                author_name=comment.author_name,
                comment_type=comment.comment_type,
                is_internal=comment.is_internal,
                parent_comment_id=comment.parent_comment_id,
                additional_data=comment.additional_data,
                created_at=comment.created_at.isoformat(),
                updated_at=comment.updated_at.isoformat() if comment.updated_at else None
            )
            for comment in thread_comments
        ]
        
        return {
            "parent_comment_id": parent_comment_id,
            "thread": thread_responses,
            "total_replies": len(thread_responses) - 1  # Exclude parent from count
        }
        
    except CommentNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except CommentServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting comment thread for {parent_comment_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve comment thread"
        )


@router.get("/search", response_model=List[CommentResponse])
async def search_comments(
    q: str = Query(..., min_length=1, description="Search term"),
    work_item_id: Optional[str] = Query(
        default=None,
        description="Filter by work item ID"
    ),
    author_filter: Optional[str] = Query(
        default=None,
        description="Filter by author name"
    ),
    include_internal: bool = Query(
        default=True,
        description="Whether to include internal comments"
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=500,
        description="Maximum number of results"
    ),
    service: CommentService = Depends(get_comment_service)
):
    """
    Search comments by content.
    
    Args:
        q: Search term
        work_item_id: Optional work item filter
        author_filter: Optional author filter
        include_internal: Whether to include internal comments
        limit: Maximum results
        
    Returns:
        List of matching comments
    """
    try:
        comments = service.search_comments(
            search_term=q,
            work_item_id=work_item_id,
            author_filter=author_filter,
            include_internal=include_internal,
            limit=limit
        )
        
        return [
            CommentResponse(
                id=comment.id,
                work_item_id=comment.work_item_id,
                content=comment.content,
                author_name=comment.author_name,
                comment_type=comment.comment_type,
                is_internal=comment.is_internal,
                parent_comment_id=comment.parent_comment_id,
                additional_data=comment.additional_data,
                created_at=comment.created_at.isoformat(),
                updated_at=comment.updated_at.isoformat() if comment.updated_at else None
            )
            for comment in comments
        ]
        
    except Exception as e:
        logger.error(f"Error searching comments: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Search failed"
        )


@router.get("/stats", response_model=CommentStats)
async def get_comment_statistics(
    service: CommentService = Depends(get_comment_service)
):
    """
    Get comment statistics.
    
    Returns:
        Comment statistics including counts and recent activity
    """
    try:
        stats = service.get_comment_stats()
        
        # Convert recent activity to response schemas
        recent_activity = [
            CommentResponse(
                id=comment.id,
                work_item_id=comment.work_item_id,
                content=comment.content,
                author_name=comment.author_name,
                comment_type=comment.comment_type,
                is_internal=comment.is_internal,
                parent_comment_id=comment.parent_comment_id,
                additional_data=comment.additional_data,
                created_at=comment.created_at.isoformat(),
                updated_at=comment.updated_at.isoformat() if comment.updated_at else None
            )
            for comment in stats["recent_activity"]
        ]
        
        return CommentStats(
            total_comments=stats["total_comments"],
            by_work_item=stats["by_work_item"],
            by_author=stats["by_author"],
            by_type=stats["by_type"],
            internal_comments=stats["internal_comments"],
            recent_activity=recent_activity
        )
        
    except Exception as e:
        logger.error(f"Error getting comment statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve comment statistics"
        )


@router.post("/bulk", response_model=BulkCommentResponse)
async def bulk_comment_operation(
    bulk_data: BulkCommentRequest,
    service: CommentService = Depends(get_comment_service)
):
    """
    Perform bulk comment operations.
    
    Args:
        bulk_data: Bulk operation request data
        
    Returns:
        Bulk operation results
    """
    try:
        if bulk_data.action == "delete":
            successful, failed = service.bulk_delete_comments(
                comment_ids=bulk_data.comment_ids,
                author_name=bulk_data.author_name
            )
            
            return BulkCommentResponse(
                successful=successful,
                failed=failed,
                total_processed=len(bulk_data.comment_ids),
                total_successful=len(successful),
                total_failed=len(failed)
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported bulk action: {bulk_data.action}"
            )
        
    except Exception as e:
        logger.error(f"Error in bulk comment operation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to perform bulk operation"
        )
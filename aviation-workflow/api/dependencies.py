"""
FastAPI dependencies for the Aviation Workflow System.

Provides dependency injection for database sessions, workflow engine,
plugin manager, and common query parameters used across endpoints.
"""

from typing import Generator, Optional
from fastapi import Depends, HTTPException, Query
from sqlmodel import Session
from core.database import get_session
from core.workflow_engine import workflow_engine, WorkflowEngine
from core.plugin_manager import plugin_manager, PluginManager


# Database Dependencies

def get_db_session() -> Generator[Session, None, None]:
    """
    FastAPI dependency for database sessions.
    
    Yields:
        Database session that automatically closes after use
    """
    yield from get_session()


# Workflow Engine Dependencies

def get_workflow_engine() -> WorkflowEngine:
    """
    FastAPI dependency for workflow engine access.
    
    Returns:
        Global workflow engine instance
    """
    return workflow_engine


# Plugin Manager Dependencies

def get_plugin_manager() -> PluginManager:
    """
    FastAPI dependency for plugin manager access.
    
    Returns:
        Global plugin manager instance
    """
    return plugin_manager


# Common Query Parameters

class PaginationParams:
    """Common pagination parameters for list endpoints."""
    
    def __init__(
        self,
        limit: int = Query(
            default=100,
            ge=1,
            le=1000,
            description="Maximum number of items to return"
        ),
        offset: int = Query(
            default=0,
            ge=0,
            description="Number of items to skip"
        )
    ):
        self.limit = limit
        self.offset = offset


class WorkItemFilterParams:
    """Common filter parameters for work item endpoints."""
    
    def __init__(
        self,
        status: Optional[str] = Query(
            default=None,
            description="Filter by work item status (active, completed, cancelled)"
        ),
        priority: Optional[str] = Query(
            default=None,
            description="Filter by priority (normal, urgent)"
        ),
        workflow_template: Optional[str] = Query(
            default=None,
            description="Filter by workflow template"
        ),
        current_state: Optional[str] = Query(
            default=None,
            description="Filter by current workflow state"
        ),
        created_by: Optional[str] = Query(
            default=None,
            description="Filter by creator"
        )
    ):
        self.status = status
        self.priority = priority
        self.workflow_template = workflow_template
        self.current_state = current_state
        self.created_by = created_by
    
    def to_filter_dict(self) -> dict:
        """Convert filter parameters to dictionary for database queries."""
        filters = {}
        if self.status:
            filters["status"] = self.status
        if self.priority:
            filters["priority"] = self.priority
        if self.workflow_template:
            filters["workflow_template"] = self.workflow_template
        if self.current_state:
            filters["current_state"] = self.current_state
        if self.created_by:
            filters["created_by"] = self.created_by
        return filters


# Dependency Functions for Common Parameters

def get_pagination_params(
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0)
) -> PaginationParams:
    """Get pagination parameters as a dependency."""
    return PaginationParams(limit=limit, offset=offset)


def get_work_item_filters(
    status: Optional[str] = Query(default=None),
    priority: Optional[str] = Query(default=None),
    workflow_template: Optional[str] = Query(default=None),
    current_state: Optional[str] = Query(default=None),
    created_by: Optional[str] = Query(default=None)
) -> WorkItemFilterParams:
    """Get work item filter parameters as a dependency."""
    return WorkItemFilterParams(
        status=status,
        priority=priority,
        workflow_template=workflow_template,
        current_state=current_state,
        created_by=created_by
    )


# Validation Dependencies

def validate_work_item_id(item_id: str) -> str:
    """
    Validate work item ID format.
    
    Args:
        item_id: Work item identifier
        
    Returns:
        Validated item ID
        
    Raises:
        HTTPException: If item ID format is invalid
    """
    if not item_id or not item_id.strip():
        raise HTTPException(
            status_code=400,
            detail="Work item ID cannot be empty"
        )
    
    # Basic format validation - should be hex string
    if not all(c in "0123456789abcdefABCDEF" for c in item_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid work item ID format"
        )
    
    return item_id.strip()


def validate_workflow_action(action: str) -> str:
    """
    Validate workflow action.
    
    Args:
        action: Action to validate
        
    Returns:
        Validated action
        
    Raises:
        HTTPException: If action is invalid
    """
    valid_actions = {"approve", "reject", "cancel"}
    
    if not action or action.lower() not in valid_actions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid action. Must be one of: {', '.join(valid_actions)}"
        )
    
    return action.lower()


def validate_department_sequence(department_ids: list[str]) -> list[str]:
    """
    Validate department sequence.
    
    Args:
        department_ids: List of department IDs
        
    Returns:
        Validated department sequence
        
    Raises:
        HTTPException: If department sequence is invalid
    """
    if not department_ids or len(department_ids) == 0:
        raise HTTPException(
            status_code=400,
            detail="Department sequence cannot be empty"
        )
    
    # Check for empty or invalid department IDs
    for i, dept_id in enumerate(department_ids):
        if not dept_id or not dept_id.strip():
            raise HTTPException(
                status_code=400,
                detail=f"Department ID at position {i} cannot be empty"
            )
    
    # Remove duplicates while preserving order
    seen = set()
    unique_departments = []
    for dept_id in department_ids:
        dept_id = dept_id.strip()
        if dept_id not in seen:
            seen.add(dept_id)
            unique_departments.append(dept_id)
    
    return unique_departments


# Health Check Dependencies

def get_system_health() -> dict:
    """
    Get system health status.
    
    Returns:
        Dictionary with system health information
    """
    from core.database import db_manager
    from core.config import settings
    
    health_status = {
        "status": "healthy",
        "timestamp": None,
        "database": "unknown",
        "workflow_engine": "unknown",
        "plugin_manager": "unknown"
    }
    
    try:
        # Check database connectivity
        if db_manager.health_check():
            health_status["database"] = "healthy"
        else:
            health_status["database"] = "unhealthy"
            health_status["status"] = "degraded"
    except Exception:
        health_status["database"] = "error"
        health_status["status"] = "unhealthy"
    
    try:
        # Check workflow engine
        workflows = workflow_engine.list_workflows()
        health_status["workflow_engine"] = "healthy"
        health_status["active_workflows"] = len(workflows)
    except Exception:
        health_status["workflow_engine"] = "error"
        health_status["status"] = "degraded"
    
    try:
        # Check plugin manager
        loaded_modules = plugin_manager.get_loaded_modules()
        health_status["plugin_manager"] = "healthy"
        health_status["loaded_modules"] = len(loaded_modules)
    except Exception:
        health_status["plugin_manager"] = "error"
        health_status["status"] = "degraded"
    
    # Add timestamp
    from datetime import datetime
    health_status["timestamp"] = datetime.utcnow().isoformat()
    
    return health_status
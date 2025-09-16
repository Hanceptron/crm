"""
Main FastAPI application for the Aviation Workflow System.

Implements the core API endpoints and integrates all middleware,
dependencies, and plugin management functionality.
"""

import logging
from typing import List, Optional, Dict, Any
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlmodel import Session, select
from pydantic import BaseModel, Field

from core.config import settings
from core.database import init_db, db_manager
from core.models import WorkItem
from core.workflow_engine import WorkflowEngine, WorkflowEngineError
from core.plugin_manager import PluginManager
from api.dependencies import (
    get_db_session,
    get_workflow_engine, 
    get_plugin_manager,
    get_pagination_params,
    get_work_item_filters,
    get_system_health,
    validate_work_item_id,
    validate_workflow_action,
    validate_department_sequence,
    PaginationParams,
    WorkItemFilterParams
)
from api.middleware import (
    configure_middleware,
    configure_exception_handlers,
    configure_production_middleware
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Pydantic models for request/response

class WorkItemCreate(BaseModel):
    """Request model for creating work items."""
    title: str = Field(..., min_length=1, max_length=255, description="Work item title")
    description: Optional[str] = Field(None, max_length=5000, description="Work item description")
    template_id: str = Field(..., description="Workflow template identifier")
    department_ids: List[str] = Field(..., min_items=1, description="List of department IDs for workflow")
    priority: Optional[str] = Field("normal", description="Priority level (normal, urgent)")
    created_by: Optional[str] = Field("system", description="User who created the work item")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class WorkItemResponse(BaseModel):
    """Response model for work items."""
    id: str
    title: str
    description: Optional[str]
    workflow_template: str
    current_state: str
    current_step: int
    workflow_data: Dict[str, Any]
    metadata: Optional[Dict[str, Any]]
    status: str
    priority: str
    created_by: str
    created_at: str
    updated_at: str


class WorkItemListResponse(BaseModel):
    """Response model for work item lists."""
    items: List[WorkItemResponse]
    total: int
    offset: int
    limit: int


class TransitionRequest(BaseModel):
    """Request model for workflow transitions."""
    action: str = Field(..., description="Action to execute (approve, reject, cancel)")
    comment: Optional[str] = Field(None, description="Optional comment for the action")
    target_step: Optional[int] = Field(None, description="Target step for reject actions")
    reason: Optional[str] = Field(None, description="Reason for cancel actions")


class TransitionResponse(BaseModel):
    """Response model for workflow transitions."""
    success: bool
    work_item: WorkItemResponse
    new_state: Dict[str, Any]
    available_actions: List[str]


# Application lifespan management

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager for startup and shutdown tasks.
    
    Args:
        app: FastAPI application instance
    """
    # Startup
    logger.info("🚀 Starting Aviation Workflow System")
    
    try:
        # Initialize database
        logger.info("📊 Initializing database...")
        init_db()
        
        # Load enabled modules
        logger.info("🔌 Loading enabled modules...")
        plugin_manager = get_plugin_manager()
        plugin_manager.load_enabled_modules()
        
        # Register module routes
        logger.info("🛣️  Registering module routes...")
        plugin_manager.register_routes(app)
        
        logger.info("✅ Application startup complete")
        
        yield
        
    except Exception as e:
        logger.error(f"❌ Application startup failed: {e}")
        raise
    
    finally:
        # Shutdown
        logger.info("🛑 Shutting down Aviation Workflow System")
        
        try:
            # Close database connections
            db_manager.close()
            logger.info("📊 Database connections closed")
            
        except Exception as e:
            logger.error(f"❌ Error during shutdown: {e}")
        
        logger.info("✅ Application shutdown complete")


# Initialize FastAPI application

app = FastAPI(
    title="Aviation Workflow System",
    description="Modular workflow management system for aviation companies",
    version="1.0.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan
)

# Configure middleware and exception handlers
configure_middleware(app)
configure_exception_handlers(app)
configure_production_middleware(app)


# Core endpoints (always available)

@app.get("/health", tags=["system"])
async def health_check():
    """
    Health check endpoint.
    
    Returns:
        System health status and component information
    """
    health_status = get_system_health()
    
    # Return appropriate status code based on health
    status_code = status.HTTP_200_OK
    if health_status["status"] == "degraded":
        status_code = status.HTTP_200_OK  # Still functional
    elif health_status["status"] == "unhealthy":
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    
    return JSONResponse(content=health_status, status_code=status_code)


@app.get("/api/work-items", response_model=WorkItemListResponse, tags=["work-items"])
async def list_work_items(
    pagination: PaginationParams = Depends(get_pagination_params),
    filters: WorkItemFilterParams = Depends(get_work_item_filters),
    session: Session = Depends(get_db_session)
):
    """
    List all work items with filtering and pagination.
    
    Args:
        pagination: Pagination parameters
        filters: Filter parameters
        session: Database session
        
    Returns:
        Paginated list of work items
    """
    try:
        # Build query with filters
        query = select(WorkItem)
        
        # Apply filters
        filter_dict = filters.to_filter_dict()
        for field, value in filter_dict.items():
            if hasattr(WorkItem, field):
                query = query.where(getattr(WorkItem, field) == value)
        
        # Get total count
        count_query = select(WorkItem)
        for field, value in filter_dict.items():
            if hasattr(WorkItem, field):
                count_query = count_query.where(getattr(WorkItem, field) == value)
        
        total = len(session.exec(count_query).all())
        
        # Apply pagination
        query = query.offset(pagination.offset).limit(pagination.limit)
        
        # Execute query
        work_items = session.exec(query).all()
        
        # Convert to response models
        items = [
            WorkItemResponse(
                id=item.id,
                title=item.title,
                description=item.description,
                workflow_template=item.workflow_template,
                current_state=item.current_state,
                current_step=item.current_step,
                workflow_data=item.workflow_data,
                metadata=item.metadata,
                status=item.status,
                priority=item.priority,
                created_by=item.created_by,
                created_at=item.created_at.isoformat(),
                updated_at=item.updated_at.isoformat()
            )
            for item in work_items
        ]
        
        return WorkItemListResponse(
            items=items,
            total=total,
            offset=pagination.offset,
            limit=pagination.limit
        )
        
    except Exception as e:
        logger.error(f"Error listing work items: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve work items"
        )


@app.post("/api/work-items", response_model=WorkItemResponse, tags=["work-items"])
async def create_work_item(
    work_item_data: WorkItemCreate,
    session: Session = Depends(get_db_session),
    workflow_engine: WorkflowEngine = Depends(get_workflow_engine)
):
    """
    Create new work item with workflow.
    
    Args:
        work_item_data: Work item creation data
        session: Database session
        workflow_engine: Workflow engine instance
        
    Returns:
        Created work item with workflow information
    """
    try:
        # Validate department sequence
        department_ids = validate_department_sequence(work_item_data.department_ids)
        
        # Create work item
        work_item = WorkItem(
            title=work_item_data.title,
            description=work_item_data.description,
            workflow_template=work_item_data.template_id,
            current_state="draft",
            current_step=0,
            workflow_data={"department_sequence": department_ids},
            metadata=work_item_data.metadata,
            priority=work_item_data.priority,
            created_by=work_item_data.created_by
        )
        
        # Save to database
        session.add(work_item)
        session.commit()
        session.refresh(work_item)
        
        # Create workflow
        try:
            workflow_engine.create_workflow(
                template=work_item_data.template_id,
                workflow_id=work_item.id,
                department_sequence=department_ids
            )
            
            # Update work item with initial workflow state
            work_item.current_state = "active"
            work_item.update_timestamp()
            session.add(work_item)
            session.commit()
            session.refresh(work_item)
            
        except WorkflowEngineError as e:
            # Rollback work item creation if workflow creation fails
            session.delete(work_item)
            session.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to create workflow: {str(e)}"
            )
        
        # Return created work item
        return WorkItemResponse(
            id=work_item.id,
            title=work_item.title,
            description=work_item.description,
            workflow_template=work_item.workflow_template,
            current_state=work_item.current_state,
            current_step=work_item.current_step,
            workflow_data=work_item.workflow_data,
            metadata=work_item.metadata,
            status=work_item.status,
            priority=work_item.priority,
            created_by=work_item.created_by,
            created_at=work_item.created_at.isoformat(),
            updated_at=work_item.updated_at.isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating work item: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create work item"
        )


@app.get("/api/work-items/{item_id}", response_model=WorkItemResponse, tags=["work-items"])
async def get_work_item(
    item_id: str = Depends(validate_work_item_id),
    session: Session = Depends(get_db_session)
):
    """
    Get single work item with full state.
    
    Args:
        item_id: Work item identifier
        session: Database session
        
    Returns:
        Work item details
    """
    try:
        # Find work item
        work_item = session.get(WorkItem, item_id)
        
        if not work_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Work item {item_id} not found"
            )
        
        # Return work item
        return WorkItemResponse(
            id=work_item.id,
            title=work_item.title,
            description=work_item.description,
            workflow_template=work_item.workflow_template,
            current_state=work_item.current_state,
            current_step=work_item.current_step,
            workflow_data=work_item.workflow_data,
            metadata=work_item.metadata,
            status=work_item.status,
            priority=work_item.priority,
            created_by=work_item.created_by,
            created_at=work_item.created_at.isoformat(),
            updated_at=work_item.updated_at.isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting work item {item_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve work item"
        )


@app.post("/api/work-items/{item_id}/transition", response_model=TransitionResponse, tags=["work-items"])
async def execute_transition(
    item_id: str,
    transition_data: TransitionRequest,
    session: Session = Depends(get_db_session),
    workflow_engine: WorkflowEngine = Depends(get_workflow_engine)
):
    """
    Execute workflow transition.
    
    Args:
        item_id: Work item identifier
        transition_data: Transition request data
        session: Database session
        workflow_engine: Workflow engine instance
        
    Returns:
        Transition result with updated work item state
    """
    try:
        # Validate inputs
        item_id = validate_work_item_id(item_id)
        action = validate_workflow_action(transition_data.action)
        
        # Find work item
        work_item = session.get(WorkItem, item_id)
        if not work_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Work item {item_id} not found"
            )
        
        # Check if work item is in a state that allows transitions
        if work_item.status not in ["active"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot execute transition on work item with status: {work_item.status}"
            )
        
        # Prepare transition context
        context = {}
        if transition_data.comment:
            context["comment"] = transition_data.comment
        if transition_data.target_step is not None:
            context["target_step"] = transition_data.target_step
        if transition_data.reason:
            context["reason"] = transition_data.reason
        
        # Execute workflow transition
        try:
            new_state = workflow_engine.execute_transition(
                workflow_id=item_id,
                action=action,
                context=context
            )
            
            # Update work item with new state
            work_item.current_step = new_state.get("current_step", work_item.current_step)
            work_item.status = new_state.get("status", work_item.status)
            work_item.workflow_data = new_state.get_all()
            work_item.update_timestamp()
            
            session.add(work_item)
            session.commit()
            session.refresh(work_item)
            
            # Get available actions for next step
            available_actions = workflow_engine.get_available_actions(item_id)
            
            # Return transition result
            return TransitionResponse(
                success=True,
                work_item=WorkItemResponse(
                    id=work_item.id,
                    title=work_item.title,
                    description=work_item.description,
                    workflow_template=work_item.workflow_template,
                    current_state=work_item.current_state,
                    current_step=work_item.current_step,
                    workflow_data=work_item.workflow_data,
                    metadata=work_item.metadata,
                    status=work_item.status,
                    priority=work_item.priority,
                    created_by=work_item.created_by,
                    created_at=work_item.created_at.isoformat(),
                    updated_at=work_item.updated_at.isoformat()
                ),
                new_state=new_state.get_all(),
                available_actions=available_actions
            )
            
        except WorkflowEngineError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Workflow transition failed: {str(e)}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing transition for work item {item_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to execute workflow transition"
        )


# Additional utility endpoints

@app.get("/api/work-items/{item_id}/actions", tags=["work-items"])
async def get_available_actions(
    item_id: str = Depends(validate_work_item_id),
    workflow_engine: WorkflowEngine = Depends(get_workflow_engine)
):
    """
    Get available actions for a work item.
    
    Args:
        item_id: Work item identifier
        workflow_engine: Workflow engine instance
        
    Returns:
        List of available actions
    """
    try:
        if not workflow_engine.workflow_exists(item_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow for work item {item_id} not found"
            )
        
        actions = workflow_engine.get_available_actions(item_id)
        
        return {
            "work_item_id": item_id,
            "available_actions": actions
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting available actions for {item_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get available actions"
        )


@app.get("/api/system/info", tags=["system"])
async def get_system_info(
    plugin_manager: PluginManager = Depends(get_plugin_manager)
):
    """
    Get system information and loaded modules.
    
    Args:
        plugin_manager: Plugin manager instance
        
    Returns:
        System information including loaded modules
    """
    return {
        "app_name": settings.app_name,
        "app_env": settings.app_env,
        "debug": settings.debug,
        "loaded_modules": list(plugin_manager.get_loaded_modules().keys()),
        "module_status": plugin_manager.get_module_status()
    }


# Initialize plugin manager and register module routes
plugin_manager = get_plugin_manager()

# Note: Module routes will be registered during application startup
# via the lifespan manager to ensure proper initialization order
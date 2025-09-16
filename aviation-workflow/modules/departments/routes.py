"""
API routes for the departments module.

Implements all CRUD endpoints for department management with proper
dependency injection and error handling.
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import Session

from api.dependencies import get_db_session
from .models import Department
from .schemas import (
    DepartmentCreate,
    DepartmentUpdate,
    DepartmentResponse,
    DepartmentListResponse,
    DepartmentStats,
    DepartmentBulkCreate,
    DepartmentBulkResponse
)
from .service import (
    DepartmentService,
    DepartmentServiceError,
    DepartmentNotFoundError,
    DepartmentAlreadyExistsError
)

logger = logging.getLogger(__name__)

# Create router with prefix and tags as specified in architecture
router = APIRouter(prefix="/api/departments", tags=["departments"])


def get_department_service(session: Session = Depends(get_db_session)) -> DepartmentService:
    """Dependency to get department service instance."""
    return DepartmentService(session)


# Core CRUD endpoints as specified in architecture

@router.get("/", response_model=DepartmentListResponse)
async def list_departments(
    active_only: bool = Query(
        default=False,
        description="Filter to only active departments"
    ),
    limit: int = Query(
        default=100,
        ge=1,
        le=1000,
        description="Maximum number of departments to return"
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Number of departments to skip"
    ),
    search: Optional[str] = Query(
        default=None,
        description="Search departments by name, code, or description"
    ),
    service: DepartmentService = Depends(get_department_service)
):
    """
    List all departments with optional filtering and pagination.
    
    Returns:
        Paginated list of departments with statistics
    """
    try:
        if search:
            departments = service.search(search, active_only=active_only)
            # Apply pagination to search results
            paginated_departments = departments[offset:offset + limit]
        else:
            departments = service.list(active_only=active_only, limit=limit, offset=offset)
            paginated_departments = departments
        
        # Get counts for response
        total = service.count()
        active_count = service.count(active_only=True)
        inactive_count = total - active_count
        
        # Convert to response models
        department_responses = [
            DepartmentResponse(
                id=dept.id,
                name=dept.name,
                code=dept.code,
                description=dept.description,
                metadata=dept.metadata,
                is_active=dept.is_active,
                created_at=dept.created_at.isoformat()
            )
            for dept in paginated_departments
        ]
        
        return DepartmentListResponse(
            departments=department_responses,
            total=len(departments) if search else total,
            active_count=active_count,
            inactive_count=inactive_count
        )
        
    except Exception as e:
        logger.error(f"Error listing departments: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve departments"
        )


@router.post("/", response_model=DepartmentResponse, status_code=status.HTTP_201_CREATED)
async def create_department(
    department: DepartmentCreate,
    service: DepartmentService = Depends(get_department_service)
):
    """
    Create new department.
    
    Args:
        department: Department creation data
        
    Returns:
        Created department
    """
    try:
        created_department = service.create(department)
        
        return DepartmentResponse(
            id=created_department.id,
            name=created_department.name,
            code=created_department.code,
            description=created_department.description,
            metadata=created_department.metadata,
            is_active=created_department.is_active,
            created_at=created_department.created_at.isoformat()
        )
        
    except DepartmentAlreadyExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except DepartmentServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating department: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create department"
        )


@router.get("/{dept_id}", response_model=DepartmentResponse)
async def get_department(
    dept_id: str,
    service: DepartmentService = Depends(get_department_service)
):
    """
    Get department by ID.
    
    Args:
        dept_id: Department identifier
        
    Returns:
        Department details
    """
    try:
        department = service.get(dept_id)
        
        return DepartmentResponse(
            id=department.id,
            name=department.name,
            code=department.code,
            description=department.description,
            metadata=department.metadata,
            is_active=department.is_active,
            created_at=department.created_at.isoformat()
        )
        
    except DepartmentNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting department {dept_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve department"
        )


@router.put("/{dept_id}", response_model=DepartmentResponse)
async def update_department(
    dept_id: str,
    department: DepartmentUpdate,
    service: DepartmentService = Depends(get_department_service)
):
    """
    Update department.
    
    Args:
        dept_id: Department identifier
        department: Department update data
        
    Returns:
        Updated department
    """
    try:
        updated_department = service.update(dept_id, department)
        
        return DepartmentResponse(
            id=updated_department.id,
            name=updated_department.name,
            code=updated_department.code,
            description=updated_department.description,
            metadata=updated_department.metadata,
            is_active=updated_department.is_active,
            created_at=updated_department.created_at.isoformat()
        )
        
    except DepartmentNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except DepartmentAlreadyExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except DepartmentServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error updating department {dept_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update department"
        )


@router.delete("/{dept_id}")
async def delete_department(
    dept_id: str,
    hard_delete: bool = Query(
        default=False,
        description="If true, permanently delete department. Otherwise, soft delete."
    ),
    service: DepartmentService = Depends(get_department_service)
):
    """
    Soft delete department (mark as inactive).
    
    Args:
        dept_id: Department identifier
        hard_delete: If true, permanently delete the department
        
    Returns:
        Success message
    """
    try:
        service.delete(dept_id, soft_delete=not hard_delete)
        
        return {
            "message": f"Department {'permanently deleted' if hard_delete else 'deactivated'} successfully",
            "department_id": dept_id
        }
        
    except DepartmentNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except DepartmentServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error deleting department {dept_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete department"
        )


# Additional utility endpoints

@router.post("/{dept_id}/activate", response_model=DepartmentResponse)
async def activate_department(
    dept_id: str,
    service: DepartmentService = Depends(get_department_service)
):
    """
    Activate a department.
    
    Args:
        dept_id: Department identifier
        
    Returns:
        Activated department
    """
    try:
        department = service.activate(dept_id)
        
        return DepartmentResponse(
            id=department.id,
            name=department.name,
            code=department.code,
            description=department.description,
            metadata=department.metadata,
            is_active=department.is_active,
            created_at=department.created_at.isoformat()
        )
        
    except DepartmentNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error activating department {dept_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to activate department"
        )


@router.post("/{dept_id}/deactivate", response_model=DepartmentResponse)
async def deactivate_department(
    dept_id: str,
    service: DepartmentService = Depends(get_department_service)
):
    """
    Deactivate a department.
    
    Args:
        dept_id: Department identifier
        
    Returns:
        Deactivated department
    """
    try:
        department = service.deactivate(dept_id)
        
        return DepartmentResponse(
            id=department.id,
            name=department.name,
            code=department.code,
            description=department.description,
            metadata=department.metadata,
            is_active=department.is_active,
            created_at=department.created_at.isoformat()
        )
        
    except DepartmentNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error deactivating department {dept_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to deactivate department"
        )


@router.get("/code/{code}", response_model=DepartmentResponse)
async def get_department_by_code(
    code: str,
    service: DepartmentService = Depends(get_department_service)
):
    """
    Get department by code.
    
    Args:
        code: Department code
        
    Returns:
        Department details
    """
    try:
        department = service.get_by_code(code.upper())
        
        return DepartmentResponse(
            id=department.id,
            name=department.name,
            code=department.code,
            description=department.description,
            metadata=department.metadata,
            is_active=department.is_active,
            created_at=department.created_at.isoformat()
        )
        
    except DepartmentNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting department by code {code}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve department"
        )


@router.get("/stats/summary", response_model=DepartmentStats)
async def get_department_stats(
    service: DepartmentService = Depends(get_department_service)
):
    """
    Get department statistics.
    
    Returns:
        Department statistics including counts and newest department
    """
    try:
        stats = service.get_stats()
        
        newest_dept = None
        if stats["newest_department"]:
            dept = stats["newest_department"]
            newest_dept = DepartmentResponse(
                id=dept.id,
                name=dept.name,
                code=dept.code,
                description=dept.description,
                metadata=dept.metadata,
                is_active=dept.is_active,
                created_at=dept.created_at.isoformat()
            )
        
        return DepartmentStats(
            total_departments=stats["total_departments"],
            active_departments=stats["active_departments"],
            inactive_departments=stats["inactive_departments"],
            newest_department=newest_dept
        )
        
    except Exception as e:
        logger.error(f"Error getting department stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve department statistics"
        )


@router.post("/bulk", response_model=DepartmentBulkResponse)
async def bulk_create_departments(
    bulk_data: DepartmentBulkCreate,
    service: DepartmentService = Depends(get_department_service)
):
    """
    Create multiple departments in bulk.
    
    Args:
        bulk_data: Bulk creation data
        
    Returns:
        Bulk creation results
    """
    try:
        results = service.bulk_create(bulk_data.departments)
        
        # Convert created departments to response models
        created_responses = [
            DepartmentResponse(
                id=dept.id,
                name=dept.name,
                code=dept.code,
                description=dept.description,
                metadata=dept.metadata,
                is_active=dept.is_active,
                created_at=dept.created_at.isoformat()
            )
            for dept in results["created"]
        ]
        
        return DepartmentBulkResponse(
            created=created_responses,
            errors=results["errors"],
            total_created=results["total_created"],
            total_errors=results["total_errors"]
        )
        
    except Exception as e:
        logger.error(f"Error in bulk department creation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create departments in bulk"
        )
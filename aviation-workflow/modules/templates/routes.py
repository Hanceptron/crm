"""
API routes for the templates module.

Implements workflow template endpoints for CRUD operations,
validation, and template management functionality.
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import Session

from api.dependencies import get_db_session
from .models import WorkflowTemplate
from .schemas import (
    TemplateRequest,
    TemplateUpdateRequest,
    TemplateResponse,
    TemplateListResponse,
    TemplateValidationRequest,
    TemplateValidationResponse,
    TemplateStats,
    TemplateUsageRequest
)
from .service import (
    TemplateService, 
    TemplateServiceError, 
    TemplateNotFoundError, 
    TemplateValidationError,
    DuplicateTemplateError
)

logger = logging.getLogger(__name__)

# Create router with prefix and tags
router = APIRouter(prefix="/api/templates", tags=["templates"])


def get_template_service(session: Session = Depends(get_db_session)) -> TemplateService:
    """Dependency to get template service instance."""
    return TemplateService(session)


# Core template CRUD endpoints

@router.post("", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(
    template_data: TemplateRequest,
    service: TemplateService = Depends(get_template_service)
):
    """
    Create a new workflow template.
    
    Args:
        template_data: Template creation data
        
    Returns:
        Created template
    """
    try:
        template = service.create_template(template_data)
        
        return TemplateResponse(
            id=template.id,
            name=template.name,
            display_name=template.display_name,
            description=template.description,
            department_sequence=template.department_sequence,
            approval_rules=template.approval_rules,
            workflow_config=template.workflow_config,
            category=template.category,
            version=template.version,
            tags=template.tags,
            is_active=template.is_active,
            is_default=template.is_default,
            usage_count=template.usage_count,
            template_data=template.template_data,
            created_by=template.created_by,
            created_at=template.created_at.isoformat(),
            updated_at=template.updated_at.isoformat() if template.updated_at else None,
            department_count=template.get_department_count(),
            max_steps=template.get_max_steps()
        )
        
    except DuplicateTemplateError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except TemplateValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except TemplateServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating template: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create template"
        )


@router.get("", response_model=TemplateListResponse)
async def list_templates(
    include_inactive: bool = Query(
        default=False,
        description="Include inactive templates"
    ),
    category: Optional[str] = Query(
        default=None,
        description="Filter by category"
    ),
    search: Optional[str] = Query(
        default=None,
        description="Search in name, display_name, or description"
    ),
    limit: Optional[int] = Query(
        default=None,
        ge=1,
        le=1000,
        description="Maximum number of templates to return"
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Number of templates to skip"
    ),
    service: TemplateService = Depends(get_template_service)
):
    """
    List workflow templates with filtering options.
    
    Args:
        include_inactive: Include inactive templates
        category: Filter by category
        search: Search term
        limit: Maximum results
        offset: Skip count
        
    Returns:
        List of templates with statistics
    """
    try:
        templates = service.list_all_templates(
            include_inactive=include_inactive,
            category=category,
            search=search,
            limit=limit,
            offset=offset
        )
        
        # Convert to response schemas
        template_responses = []
        for template in templates:
            template_responses.append(TemplateResponse(
                id=template.id,
                name=template.name,
                display_name=template.display_name,
                description=template.description,
                department_sequence=template.department_sequence,
                approval_rules=template.approval_rules,
                workflow_config=template.workflow_config,
                category=template.category,
                version=template.version,
                tags=template.tags,
                is_active=template.is_active,
                is_default=template.is_default,
                usage_count=template.usage_count,
                template_data=template.template_data,
                created_by=template.created_by,
                created_at=template.created_at.isoformat(),
                updated_at=template.updated_at.isoformat() if template.updated_at else None,
                department_count=template.get_department_count(),
                max_steps=template.get_max_steps()
            ))
        
        # Calculate statistics
        by_category = {}
        by_status = {"active": 0, "inactive": 0}
        total_usage = 0
        
        for template in templates:
            # Count by category
            by_category[template.category] = by_category.get(template.category, 0) + 1
            
            # Count by status
            if template.is_active:
                by_status["active"] += 1
            else:
                by_status["inactive"] += 1
                
            # Sum usage
            total_usage += template.usage_count
        
        return TemplateListResponse(
            templates=template_responses,
            total=len(template_responses),
            by_category=by_category,
            by_status=by_status,
            total_usage=total_usage
        )
        
    except TemplateServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error listing templates: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve templates"
        )


@router.get("/active", response_model=List[TemplateResponse])
async def list_active_templates(
    category: Optional[str] = Query(
        default=None,
        description="Filter by category"
    ),
    limit: Optional[int] = Query(
        default=None,
        ge=1,
        le=500,
        description="Maximum number of templates to return"
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Number of templates to skip"
    ),
    service: TemplateService = Depends(get_template_service)
):
    """
    List active workflow templates only.
    
    Args:
        category: Filter by category
        limit: Maximum results
        offset: Skip count
        
    Returns:
        List of active templates
    """
    try:
        templates = service.list_active_templates(
            category=category,
            limit=limit,
            offset=offset
        )
        
        return [
            TemplateResponse(
                id=template.id,
                name=template.name,
                display_name=template.display_name,
                description=template.description,
                department_sequence=template.department_sequence,
                approval_rules=template.approval_rules,
                workflow_config=template.workflow_config,
                category=template.category,
                version=template.version,
                tags=template.tags,
                is_active=template.is_active,
                is_default=template.is_default,
                usage_count=template.usage_count,
                template_data=template.template_data,
                created_by=template.created_by,
                created_at=template.created_at.isoformat(),
                updated_at=template.updated_at.isoformat() if template.updated_at else None,
                department_count=template.get_department_count(),
                max_steps=template.get_max_steps()
            )
            for template in templates
        ]
        
    except TemplateServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error listing active templates: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve active templates"
        )


@router.get("/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: str,
    service: TemplateService = Depends(get_template_service)
):
    """
    Get a single template by ID.
    
    Args:
        template_id: Template identifier
        
    Returns:
        Template details
    """
    try:
        template = service.get_template(template_id)
        
        return TemplateResponse(
            id=template.id,
            name=template.name,
            display_name=template.display_name,
            description=template.description,
            department_sequence=template.department_sequence,
            approval_rules=template.approval_rules,
            workflow_config=template.workflow_config,
            category=template.category,
            version=template.version,
            tags=template.tags,
            is_active=template.is_active,
            is_default=template.is_default,
            usage_count=template.usage_count,
            template_data=template.template_data,
            created_by=template.created_by,
            created_at=template.created_at.isoformat(),
            updated_at=template.updated_at.isoformat() if template.updated_at else None,
            department_count=template.get_department_count(),
            max_steps=template.get_max_steps()
        )
        
    except TemplateNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting template {template_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve template"
        )


@router.get("/name/{template_name}", response_model=TemplateResponse)
async def get_template_by_name(
    template_name: str,
    service: TemplateService = Depends(get_template_service)
):
    """
    Get a single template by name.
    
    Args:
        template_name: Template name
        
    Returns:
        Template details
    """
    try:
        template = service.get_template_by_name(template_name)
        
        return TemplateResponse(
            id=template.id,
            name=template.name,
            display_name=template.display_name,
            description=template.description,
            department_sequence=template.department_sequence,
            approval_rules=template.approval_rules,
            workflow_config=template.workflow_config,
            category=template.category,
            version=template.version,
            tags=template.tags,
            is_active=template.is_active,
            is_default=template.is_default,
            usage_count=template.usage_count,
            template_data=template.template_data,
            created_by=template.created_by,
            created_at=template.created_at.isoformat(),
            updated_at=template.updated_at.isoformat() if template.updated_at else None,
            department_count=template.get_department_count(),
            max_steps=template.get_max_steps()
        )
        
    except TemplateNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting template by name {template_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve template"
        )


@router.put("/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: str,
    update_data: TemplateUpdateRequest,
    service: TemplateService = Depends(get_template_service)
):
    """
    Update an existing template.
    
    Args:
        template_id: Template identifier
        update_data: Updated template data
        
    Returns:
        Updated template
    """
    try:
        template = service.update_template(template_id, update_data)
        
        return TemplateResponse(
            id=template.id,
            name=template.name,
            display_name=template.display_name,
            description=template.description,
            department_sequence=template.department_sequence,
            approval_rules=template.approval_rules,
            workflow_config=template.workflow_config,
            category=template.category,
            version=template.version,
            tags=template.tags,
            is_active=template.is_active,
            is_default=template.is_default,
            usage_count=template.usage_count,
            template_data=template.template_data,
            created_by=template.created_by,
            created_at=template.created_at.isoformat(),
            updated_at=template.updated_at.isoformat() if template.updated_at else None,
            department_count=template.get_department_count(),
            max_steps=template.get_max_steps()
        )
        
    except TemplateNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except TemplateValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except TemplateServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error updating template {template_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update template"
        )


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_id: str,
    service: TemplateService = Depends(get_template_service)
):
    """
    Delete a template.
    
    Args:
        template_id: Template identifier
    """
    try:
        service.delete_template(template_id)
        
    except TemplateNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except TemplateServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error deleting template {template_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete template"
        )


# Template validation endpoint

@router.post("/validate", response_model=TemplateValidationResponse)
async def validate_template(
    validation_data: TemplateValidationRequest,
    service: TemplateService = Depends(get_template_service)
):
    """
    Validate a template configuration.
    
    Args:
        validation_data: Template validation request data
        
    Returns:
        Validation results with errors and warnings
    """
    try:
        validation_result = service.validate_department_sequence(
            validation_data.department_sequence,
            check_existence=validation_data.check_department_existence
        )
        
        # Calculate estimated completion time (placeholder logic)
        estimated_time = None
        if validation_result["is_valid"]:
            dept_count = len(validation_data.department_sequence)
            estimated_days = dept_count * 2  # Rough estimate: 2 days per department
            if estimated_days == 1:
                estimated_time = "1 day"
            elif estimated_days < 7:
                estimated_time = f"{estimated_days} days"
            elif estimated_days < 30:
                weeks = estimated_days // 7
                estimated_time = f"{weeks} week{'s' if weeks > 1 else ''}"
            else:
                months = estimated_days // 30
                estimated_time = f"{months} month{'s' if months > 1 else ''}"
        
        return TemplateValidationResponse(
            is_valid=validation_result["is_valid"],
            errors=validation_result["errors"],
            warnings=validation_result["warnings"],
            department_validation=validation_result["department_details"],
            approval_rules_validation={},  # Could add approval rules validation here
            department_count=len(validation_data.department_sequence),
            max_steps=len(validation_data.department_sequence) - 1,
            estimated_completion_time=estimated_time
        )
        
    except Exception as e:
        logger.error(f"Error validating template: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate template"
        )


# Utility endpoints

@router.get("/default/{category}", response_model=Optional[TemplateResponse])
async def get_default_template(
    category: str,
    service: TemplateService = Depends(get_template_service)
):
    """
    Get the default template for a category.
    
    Args:
        category: Template category
        
    Returns:
        Default template for the category, or null if none
    """
    try:
        template = service.get_default_template(category)
        
        if not template:
            return None
        
        return TemplateResponse(
            id=template.id,
            name=template.name,
            display_name=template.display_name,
            description=template.description,
            department_sequence=template.department_sequence,
            approval_rules=template.approval_rules,
            workflow_config=template.workflow_config,
            category=template.category,
            version=template.version,
            tags=template.tags,
            is_active=template.is_active,
            is_default=template.is_default,
            usage_count=template.usage_count,
            template_data=template.template_data,
            created_by=template.created_by,
            created_at=template.created_at.isoformat(),
            updated_at=template.updated_at.isoformat() if template.updated_at else None,
            department_count=template.get_department_count(),
            max_steps=template.get_max_steps()
        )
        
    except Exception as e:
        logger.error(f"Error getting default template for category {category}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve default template"
        )


@router.post("/{template_id}/use", status_code=status.HTTP_204_NO_CONTENT)
async def record_template_usage(
    template_id: str,
    usage_data: TemplateUsageRequest,
    service: TemplateService = Depends(get_template_service)
):
    """
    Record template usage for tracking.
    
    Args:
        template_id: Template identifier
        usage_data: Usage tracking data
    """
    try:
        service.record_template_usage(
            template_id=template_id,
            work_item_id=usage_data.work_item_id,
            used_by=usage_data.used_by
        )
        
    except TemplateNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error recording template usage: {e}")
        # Don't fail the request for usage tracking errors
        pass


@router.get("/stats", response_model=TemplateStats)
async def get_template_statistics(
    service: TemplateService = Depends(get_template_service)
):
    """
    Get template statistics.
    
    Returns:
        Template statistics including counts and usage data
    """
    try:
        stats = service.get_template_stats()
        
        # Convert template lists to response schemas
        most_used_responses = [
            TemplateResponse(
                id=template.id,
                name=template.name,
                display_name=template.display_name,
                description=template.description,
                department_sequence=template.department_sequence,
                approval_rules=template.approval_rules,
                workflow_config=template.workflow_config,
                category=template.category,
                version=template.version,
                tags=template.tags,
                is_active=template.is_active,
                is_default=template.is_default,
                usage_count=template.usage_count,
                template_data=template.template_data,
                created_by=template.created_by,
                created_at=template.created_at.isoformat(),
                updated_at=template.updated_at.isoformat() if template.updated_at else None,
                department_count=template.get_department_count(),
                max_steps=template.get_max_steps()
            )
            for template in stats["most_used_templates"]
        ]
        
        recent_responses = [
            TemplateResponse(
                id=template.id,
                name=template.name,
                display_name=template.display_name,
                description=template.description,
                department_sequence=template.department_sequence,
                approval_rules=template.approval_rules,
                workflow_config=template.workflow_config,
                category=template.category,
                version=template.version,
                tags=template.tags,
                is_active=template.is_active,
                is_default=template.is_default,
                usage_count=template.usage_count,
                template_data=template.template_data,
                created_by=template.created_by,
                created_at=template.created_at.isoformat(),
                updated_at=template.updated_at.isoformat() if template.updated_at else None,
                department_count=template.get_department_count(),
                max_steps=template.get_max_steps()
            )
            for template in stats["recent_templates"]
        ]
        
        return TemplateStats(
            total_templates=stats["total_templates"],
            active_templates=stats["active_templates"],
            inactive_templates=stats["inactive_templates"],
            default_templates=stats["default_templates"],
            by_category=stats["by_category"],
            by_usage={"total": stats["total_usage"]},
            most_used_templates=most_used_responses,
            recent_templates=recent_responses
        )
        
    except Exception as e:
        logger.error(f"Error getting template statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve template statistics"
        )
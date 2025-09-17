"""
Template service for the Aviation Workflow System.

Provides business logic and data operations for workflow template management.
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from sqlmodel import Session, select, func, desc, asc, and_, or_
from sqlalchemy.exc import IntegrityError

from .models import WorkflowTemplate
from .schemas import TemplateRequest, TemplateUpdateRequest, TemplateValidationRequest

logger = logging.getLogger(__name__)


class TemplateServiceError(Exception):
    """Base exception for template service errors."""
    pass


class TemplateNotFoundError(TemplateServiceError):
    """Raised when a template is not found."""
    pass


class TemplateValidationError(TemplateServiceError):
    """Raised when template validation fails."""
    pass


class DuplicateTemplateError(TemplateServiceError):
    """Raised when attempting to create a duplicate template."""
    pass


class TemplateService:
    """
    Service class for workflow template operations.
    
    Provides methods for creating, retrieving, updating, and validating
    workflow templates with department sequences and approval rules.
    """
    
    def __init__(self, session: Session):
        """
        Initialize template service.
        
        Args:
            session: Database session
        """
        self.session = session
    
    def create_template(self, template_data: TemplateRequest) -> WorkflowTemplate:
        """
        Create a new workflow template.
        
        Args:
            template_data: Template creation data
            
        Returns:
            Created template
            
        Raises:
            DuplicateTemplateError: If template name already exists
            TemplateValidationError: If template data is invalid
            TemplateServiceError: If template creation fails
        """
        try:
            # Check if template name already exists
            existing = self.session.exec(
                select(WorkflowTemplate).where(WorkflowTemplate.name == template_data.name)
            ).first()
            
            if existing:
                raise DuplicateTemplateError(f"Template with name '{template_data.name}' already exists")
            
            # Validate department sequence
            validation_result = self.validate_department_sequence(
                template_data.department_sequence,
                check_existence=True
            )
            
            if not validation_result["is_valid"]:
                raise TemplateValidationError(f"Invalid department sequence: {'; '.join(validation_result['errors'])}")
            
            # Handle default template logic
            if template_data.is_default:
                self._clear_default_templates(template_data.category)
            
            # Create template
            template = WorkflowTemplate(
                name=template_data.name,
                display_name=template_data.display_name,
                description=template_data.description,
                department_sequence=template_data.department_sequence,
                approval_rules=template_data.approval_rules or {},
                workflow_config=template_data.workflow_config or {},
                category=template_data.category or "general",
                version=template_data.version or "1.0.0",
                tags=template_data.tags or [],
                is_active=template_data.is_active if template_data.is_active is not None else True,
                is_default=template_data.is_default if template_data.is_default is not None else False,
                template_data=template_data.template_data or {},
                created_by=template_data.created_by
            )
            
            self.session.add(template)
            self.session.commit()
            self.session.refresh(template)
            
            logger.info(f"Created template {template.id} ({template.name})")
            return template
            
        except (DuplicateTemplateError, TemplateValidationError):
            self.session.rollback()
            raise
        except IntegrityError as e:
            self.session.rollback()
            logger.error(f"Database integrity error creating template: {e}")
            raise TemplateServiceError(f"Failed to create template: database constraint violation")
        except Exception as e:
            self.session.rollback()
            logger.error(f"Unexpected error creating template: {e}")
            raise TemplateServiceError(f"Failed to create template: {str(e)}")
    
    def get_template(self, template_id: str) -> WorkflowTemplate:
        """
        Get a single template by ID.
        
        Args:
            template_id: Template identifier
            
        Returns:
            Template instance
            
        Raises:
            TemplateNotFoundError: If template doesn't exist
        """
        template = self.session.get(WorkflowTemplate, template_id)
        if not template:
            raise TemplateNotFoundError(f"Template {template_id} not found")
        return template
    
    def get_template_by_name(self, name: str) -> WorkflowTemplate:
        """
        Get a single template by name.
        
        Args:
            name: Template name
            
        Returns:
            Template instance
            
        Raises:
            TemplateNotFoundError: If template doesn't exist
        """
        template = self.session.exec(
            select(WorkflowTemplate).where(WorkflowTemplate.name == name)
        ).first()
        
        if not template:
            raise TemplateNotFoundError(f"Template '{name}' not found")
        return template
    
    def list_active_templates(self, category: Optional[str] = None,
                             limit: Optional[int] = None,
                             offset: int = 0) -> List[WorkflowTemplate]:
        """
        List all active templates.
        
        Args:
            category: Filter by category
            limit: Maximum number of templates to return
            offset: Number of templates to skip
            
        Returns:
            List of active templates
        """
        try:
            query = select(WorkflowTemplate).where(WorkflowTemplate.is_active == True)
            
            if category:
                query = query.where(WorkflowTemplate.category == category)
            
            # Order by usage count (most used first), then by name
            query = query.order_by(desc(WorkflowTemplate.usage_count), asc(WorkflowTemplate.name))
            
            if offset > 0:
                query = query.offset(offset)
            if limit:
                query = query.limit(limit)
            
            templates = list(self.session.exec(query).all())
            
            logger.debug(f"Retrieved {len(templates)} active templates")
            return templates
            
        except Exception as e:
            logger.error(f"Error retrieving active templates: {e}")
            raise TemplateServiceError(f"Failed to retrieve templates: {str(e)}")
    
    def list_all_templates(self, include_inactive: bool = True,
                          category: Optional[str] = None,
                          search: Optional[str] = None,
                          limit: Optional[int] = None,
                          offset: int = 0) -> List[WorkflowTemplate]:
        """
        List all templates with filtering options.
        
        Args:
            include_inactive: Whether to include inactive templates
            category: Filter by category
            search: Search term for name or description
            limit: Maximum number of templates to return
            offset: Number of templates to skip
            
        Returns:
            List of templates
        """
        try:
            query = select(WorkflowTemplate)
            
            if not include_inactive:
                query = query.where(WorkflowTemplate.is_active == True)
            
            if category:
                query = query.where(WorkflowTemplate.category == category)
            
            if search:
                search_pattern = f"%{search}%"
                query = query.where(
                    or_(
                        WorkflowTemplate.name.ilike(search_pattern),
                        WorkflowTemplate.display_name.ilike(search_pattern),
                        WorkflowTemplate.description.ilike(search_pattern)
                    )
                )
            
            # Order by default status, then usage count, then name
            query = query.order_by(
                desc(WorkflowTemplate.is_default),
                desc(WorkflowTemplate.usage_count),
                asc(WorkflowTemplate.name)
            )
            
            if offset > 0:
                query = query.offset(offset)
            if limit:
                query = query.limit(limit)
            
            templates = list(self.session.exec(query).all())
            
            logger.debug(f"Retrieved {len(templates)} templates")
            return templates
            
        except Exception as e:
            logger.error(f"Error retrieving templates: {e}")
            raise TemplateServiceError(f"Failed to retrieve templates: {str(e)}")
    
    def update_template(self, template_id: str, update_data: TemplateUpdateRequest) -> WorkflowTemplate:
        """
        Update an existing template.
        
        Args:
            template_id: Template identifier
            update_data: Updated template data
            
        Returns:
            Updated template
            
        Raises:
            TemplateNotFoundError: If template doesn't exist
            TemplateValidationError: If update data is invalid
            TemplateServiceError: If update fails
        """
        try:
            template = self.get_template(template_id)
            
            # Validate department sequence if provided
            if update_data.department_sequence is not None:
                validation_result = self.validate_department_sequence(
                    update_data.department_sequence,
                    check_existence=True
                )
                
                if not validation_result["is_valid"]:
                    raise TemplateValidationError(f"Invalid department sequence: {'; '.join(validation_result['errors'])}")
            
            # Handle default template logic
            if update_data.is_default is True and not template.is_default:
                self._clear_default_templates(template.category)
            
            # Update fields
            if update_data.display_name is not None:
                template.display_name = update_data.display_name
            
            if update_data.description is not None:
                template.description = update_data.description
            
            if update_data.department_sequence is not None:
                template.department_sequence = update_data.department_sequence
            
            if update_data.approval_rules is not None:
                template.approval_rules = update_data.approval_rules
            
            if update_data.workflow_config is not None:
                template.workflow_config = update_data.workflow_config
            
            if update_data.category is not None:
                # If changing category and template is default, clear default status
                if update_data.category != template.category and template.is_default:
                    template.is_default = False
                template.category = update_data.category
            
            if update_data.version is not None:
                template.version = update_data.version
            
            if update_data.tags is not None:
                template.tags = update_data.tags
            
            if update_data.is_active is not None:
                template.is_active = update_data.is_active
            
            if update_data.is_default is not None:
                template.is_default = update_data.is_default
            
            if update_data.template_data is not None:
                template.template_data = update_data.template_data
            
            # Update timestamp
            template.updated_at = datetime.now()
            
            self.session.add(template)
            self.session.commit()
            self.session.refresh(template)
            
            logger.info(f"Updated template {template_id}")
            return template
            
        except (TemplateNotFoundError, TemplateValidationError):
            raise
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error updating template {template_id}: {e}")
            raise TemplateServiceError(f"Failed to update template: {str(e)}")
    
    def delete_template(self, template_id: str) -> bool:
        """
        Delete a template.
        
        Args:
            template_id: Template identifier
            
        Returns:
            True if template was deleted
            
        Raises:
            TemplateNotFoundError: If template doesn't exist
            TemplateServiceError: If deletion fails
        """
        try:
            template = self.get_template(template_id)
            
            # Check if template is in use (this would require checking work_items)
            # For now, we'll allow deletion but could add usage validation later
            
            self.session.delete(template)
            self.session.commit()
            
            logger.info(f"Deleted template {template_id}")
            return True
            
        except TemplateNotFoundError:
            raise
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error deleting template {template_id}: {e}")
            raise TemplateServiceError(f"Failed to delete template: {str(e)}")
    
    def validate_department_sequence(self, department_sequence: List[str],
                                   check_existence: bool = True) -> Dict[str, Any]:
        """
        Validate a department sequence.
        
        Args:
            department_sequence: List of department IDs
            check_existence: Whether to check if departments exist in the system
            
        Returns:
            Dictionary with validation results
        """
        validation_result = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "department_details": {}
        }
        
        try:
            # Basic validation
            if not department_sequence or len(department_sequence) == 0:
                validation_result["is_valid"] = False
                validation_result["errors"].append("Department sequence cannot be empty")
                return validation_result
            
            # Check for duplicates
            if len(department_sequence) != len(set(department_sequence)):
                validation_result["is_valid"] = False
                validation_result["errors"].append("Department sequence cannot contain duplicates")
            
            # Validate each department ID
            for i, dept_id in enumerate(department_sequence):
                if not isinstance(dept_id, str) or not dept_id.strip():
                    validation_result["is_valid"] = False
                    validation_result["errors"].append(f"Department ID at position {i} is invalid")
            
            # Check department existence if requested
            if check_existence and validation_result["is_valid"]:
                try:
                    from modules.departments.service import DepartmentService
                    dept_service = DepartmentService(self.session)
                    
                    for dept_id in department_sequence:
                        try:
                            department = dept_service.get(dept_id)
                            validation_result["department_details"][dept_id] = {
                                "name": department.name,
                                "is_active": department.is_active
                            }
                            
                            if not department.is_active:
                                validation_result["warnings"].append(
                                    f"Department {department.name} ({dept_id}) is inactive"
                                )
                        except Exception:
                            validation_result["is_valid"] = False
                            validation_result["errors"].append(f"Department {dept_id} not found")
                            
                except ImportError:
                    validation_result["warnings"].append(
                        "Departments module not available - skipping existence check"
                    )
                except Exception as e:
                    validation_result["warnings"].append(
                        f"Could not validate department existence: {e}"
                    )
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Error validating department sequence: {e}")
            return {
                "is_valid": False,
                "errors": [f"Validation failed: {str(e)}"],
                "warnings": [],
                "department_details": {}
            }
    
    def get_default_template(self, category: str = "general") -> Optional[WorkflowTemplate]:
        """
        Get the default template for a category.
        
        Args:
            category: Template category
            
        Returns:
            Default template for the category, or None if not found
        """
        try:
            template = self.session.exec(
                select(WorkflowTemplate).where(
                    and_(
                        WorkflowTemplate.category == category,
                        WorkflowTemplate.is_default == True,
                        WorkflowTemplate.is_active == True
                    )
                )
            ).first()
            
            return template
            
        except Exception as e:
            logger.error(f"Error getting default template for category {category}: {e}")
            return None
    
    def record_template_usage(self, template_id: str, work_item_id: str,
                            used_by: str) -> None:
        """
        Record template usage for tracking.
        
        Args:
            template_id: Template identifier
            work_item_id: Work item that used the template
            used_by: User who used the template
        """
        try:
            template = self.get_template(template_id)
            template.increment_usage()
            
            self.session.add(template)
            self.session.commit()
            
            logger.info(f"Recorded template usage: {template_id} for work item {work_item_id}")
            
        except TemplateNotFoundError:
            logger.warning(f"Attempted to record usage for non-existent template {template_id}")
        except Exception as e:
            logger.error(f"Error recording template usage: {e}")
    
    def get_template_stats(self) -> Dict[str, Any]:
        """
        Get template statistics.
        
        Returns:
            Dictionary with template statistics
        """
        try:
            # Total counts
            total_templates = self.session.exec(
                select(func.count(WorkflowTemplate.id))
            ).one()
            
            active_templates = self.session.exec(
                select(func.count(WorkflowTemplate.id))
                .where(WorkflowTemplate.is_active == True)
            ).one()
            
            inactive_templates = total_templates - active_templates
            
            default_templates = self.session.exec(
                select(func.count(WorkflowTemplate.id))
                .where(WorkflowTemplate.is_default == True)
            ).one()
            
            # Templates by category
            by_category = dict(self.session.exec(
                select(WorkflowTemplate.category, func.count(WorkflowTemplate.id))
                .group_by(WorkflowTemplate.category)
            ).all())
            
            # Usage statistics
            total_usage = self.session.exec(
                select(func.sum(WorkflowTemplate.usage_count))
            ).one() or 0
            
            # Most used templates
            most_used = list(self.session.exec(
                select(WorkflowTemplate)
                .where(WorkflowTemplate.is_active == True)
                .order_by(desc(WorkflowTemplate.usage_count))
                .limit(5)
            ).all())
            
            # Recent templates
            recent_templates = list(self.session.exec(
                select(WorkflowTemplate)
                .order_by(desc(WorkflowTemplate.created_at))
                .limit(5)
            ).all())
            
            return {
                "total_templates": total_templates,
                "active_templates": active_templates,
                "inactive_templates": inactive_templates,
                "default_templates": default_templates,
                "by_category": by_category,
                "total_usage": total_usage,
                "most_used_templates": most_used,
                "recent_templates": recent_templates
            }
            
        except Exception as e:
            logger.error(f"Error getting template statistics: {e}")
            raise TemplateServiceError(f"Failed to get statistics: {str(e)}")
    
    def _clear_default_templates(self, category: str) -> None:
        """
        Clear default status for all templates in a category.
        
        Args:
            category: Template category
        """
        try:
            templates = self.session.exec(
                select(WorkflowTemplate).where(
                    and_(
                        WorkflowTemplate.category == category,
                        WorkflowTemplate.is_default == True
                    )
                )
            ).all()
            
            for template in templates:
                template.is_default = False
                self.session.add(template)
            
        except Exception as e:
            logger.error(f"Error clearing default templates for category {category}: {e}")
            raise TemplateServiceError(f"Failed to clear default templates: {str(e)}")
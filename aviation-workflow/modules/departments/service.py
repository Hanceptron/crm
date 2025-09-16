"""
Service layer for the departments module.

Contains business logic for department operations including CRUD operations,
validation, and business rules enforcement.
"""

import logging
from typing import List, Optional, Dict, Any
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status

from .models import Department
from .schemas import DepartmentCreate, DepartmentUpdate, DepartmentResponse

logger = logging.getLogger(__name__)


class DepartmentServiceError(Exception):
    """Base exception for department service errors."""
    pass


class DepartmentNotFoundError(DepartmentServiceError):
    """Raised when a department is not found."""
    pass


class DepartmentAlreadyExistsError(DepartmentServiceError):
    """Raised when trying to create a department with duplicate name/code."""
    pass


class DepartmentService:
    """
    Service class for department business logic.
    
    Handles all department operations including CRUD, validation,
    and business rule enforcement.
    """
    
    def __init__(self, session: Session):
        """
        Initialize department service.
        
        Args:
            session: Database session
        """
        self.session = session
    
    def create(self, department_data: DepartmentCreate) -> Department:
        """
        Create a new department.
        
        Args:
            department_data: Department creation data
            
        Returns:
            Created department
            
        Raises:
            DepartmentAlreadyExistsError: If department with same name/code exists
            DepartmentServiceError: For other creation errors
        """
        try:
            # Check for existing department with same name or code
            existing = self.session.exec(
                select(Department).where(
                    (Department.name == department_data.name) |
                    (Department.code == department_data.code)
                )
            ).first()
            
            if existing:
                if existing.name == department_data.name:
                    raise DepartmentAlreadyExistsError(f"Department with name '{department_data.name}' already exists")
                else:
                    raise DepartmentAlreadyExistsError(f"Department with code '{department_data.code}' already exists")
            
            # Create new department
            department = Department(
                name=department_data.name,
                code=department_data.code,
                description=department_data.description,
                metadata=department_data.metadata,
                is_active=department_data.is_active
            )
            
            self.session.add(department)
            self.session.commit()
            self.session.refresh(department)
            
            logger.info(f"Created department: {department.code} - {department.name}")
            return department
            
        except DepartmentAlreadyExistsError:
            raise
        except IntegrityError as e:
            self.session.rollback()
            logger.error(f"Database integrity error creating department: {e}")
            raise DepartmentServiceError("Failed to create department due to data constraints")
        except Exception as e:
            self.session.rollback()
            logger.error(f"Unexpected error creating department: {e}")
            raise DepartmentServiceError(f"Failed to create department: {str(e)}")
    
    def get(self, department_id: str) -> Department:
        """
        Get department by ID.
        
        Args:
            department_id: Department identifier
            
        Returns:
            Department instance
            
        Raises:
            DepartmentNotFoundError: If department not found
        """
        department = self.session.get(Department, department_id)
        
        if not department:
            raise DepartmentNotFoundError(f"Department with ID '{department_id}' not found")
        
        return department
    
    def get_by_code(self, code: str) -> Department:
        """
        Get department by code.
        
        Args:
            code: Department code
            
        Returns:
            Department instance
            
        Raises:
            DepartmentNotFoundError: If department not found
        """
        department = self.session.exec(
            select(Department).where(Department.code == code)
        ).first()
        
        if not department:
            raise DepartmentNotFoundError(f"Department with code '{code}' not found")
        
        return department
    
    def list(self, active_only: bool = False, 
             limit: int = 100, offset: int = 0) -> List[Department]:
        """
        List departments with optional filtering.
        
        Args:
            active_only: If True, only return active departments
            limit: Maximum number of departments to return
            offset: Number of departments to skip
            
        Returns:
            List of departments
        """
        query = select(Department)
        
        if active_only:
            query = query.where(Department.is_active == True)
        
        query = query.offset(offset).limit(limit).order_by(Department.name)
        
        return list(self.session.exec(query).all())
    
    def count(self, active_only: bool = False) -> int:
        """
        Count departments.
        
        Args:
            active_only: If True, only count active departments
            
        Returns:
            Number of departments
        """
        query = select(Department)
        
        if active_only:
            query = query.where(Department.is_active == True)
        
        return len(self.session.exec(query).all())
    
    def update(self, department_id: str, update_data: DepartmentUpdate) -> Department:
        """
        Update department.
        
        Args:
            department_id: Department identifier
            update_data: Update data
            
        Returns:
            Updated department
            
        Raises:
            DepartmentNotFoundError: If department not found
            DepartmentAlreadyExistsError: If update would create duplicate
            DepartmentServiceError: For other update errors
        """
        try:
            # Get existing department
            department = self.get(department_id)
            
            # Check for conflicts with name/code if they're being updated
            if update_data.name or update_data.code:
                existing_query = select(Department).where(Department.id != department_id)
                
                if update_data.name:
                    existing_query = existing_query.where(Department.name == update_data.name)
                elif update_data.code:
                    existing_query = existing_query.where(Department.code == update_data.code)
                
                existing = self.session.exec(existing_query).first()
                
                if existing:
                    if update_data.name and existing.name == update_data.name:
                        raise DepartmentAlreadyExistsError(f"Department with name '{update_data.name}' already exists")
                    elif update_data.code and existing.code == update_data.code:
                        raise DepartmentAlreadyExistsError(f"Department with code '{update_data.code}' already exists")
            
            # Update fields
            update_dict = update_data.dict(exclude_unset=True)
            for field, value in update_dict.items():
                setattr(department, field, value)
            
            self.session.add(department)
            self.session.commit()
            self.session.refresh(department)
            
            logger.info(f"Updated department: {department.id}")
            return department
            
        except (DepartmentNotFoundError, DepartmentAlreadyExistsError):
            raise
        except IntegrityError as e:
            self.session.rollback()
            logger.error(f"Database integrity error updating department: {e}")
            raise DepartmentServiceError("Failed to update department due to data constraints")
        except Exception as e:
            self.session.rollback()
            logger.error(f"Unexpected error updating department: {e}")
            raise DepartmentServiceError(f"Failed to update department: {str(e)}")
    
    def delete(self, department_id: str, soft_delete: bool = True) -> bool:
        """
        Delete department (soft delete by default).
        
        Args:
            department_id: Department identifier
            soft_delete: If True, mark as inactive instead of deleting
            
        Returns:
            True if deleted successfully
            
        Raises:
            DepartmentNotFoundError: If department not found
            DepartmentServiceError: For other deletion errors
        """
        try:
            department = self.get(department_id)
            
            if soft_delete:
                # Soft delete - mark as inactive
                department.deactivate()
                self.session.add(department)
                self.session.commit()
                logger.info(f"Soft deleted department: {department.id}")
            else:
                # Hard delete - actually remove from database
                self.session.delete(department)
                self.session.commit()
                logger.info(f"Hard deleted department: {department.id}")
            
            return True
            
        except DepartmentNotFoundError:
            raise
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error deleting department: {e}")
            raise DepartmentServiceError(f"Failed to delete department: {str(e)}")
    
    def activate(self, department_id: str) -> Department:
        """
        Activate a department.
        
        Args:
            department_id: Department identifier
            
        Returns:
            Activated department
            
        Raises:
            DepartmentNotFoundError: If department not found
        """
        department = self.get(department_id)
        department.activate()
        
        self.session.add(department)
        self.session.commit()
        self.session.refresh(department)
        
        logger.info(f"Activated department: {department.id}")
        return department
    
    def deactivate(self, department_id: str) -> Department:
        """
        Deactivate a department.
        
        Args:
            department_id: Department identifier
            
        Returns:
            Deactivated department
            
        Raises:
            DepartmentNotFoundError: If department not found
        """
        department = self.get(department_id)
        department.deactivate()
        
        self.session.add(department)
        self.session.commit()
        self.session.refresh(department)
        
        logger.info(f"Deactivated department: {department.id}")
        return department
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get department statistics.
        
        Returns:
            Dictionary with department statistics
        """
        total = self.count()
        active = self.count(active_only=True)
        inactive = total - active
        
        # Get newest department
        newest = self.session.exec(
            select(Department).order_by(Department.created_at.desc())
        ).first()
        
        return {
            "total_departments": total,
            "active_departments": active,
            "inactive_departments": inactive,
            "newest_department": newest
        }
    
    def search(self, query: str, active_only: bool = True) -> List[Department]:
        """
        Search departments by name or code.
        
        Args:
            query: Search query
            active_only: If True, only search active departments
            
        Returns:
            List of matching departments
        """
        search_query = select(Department).where(
            (Department.name.contains(query)) |
            (Department.code.contains(query)) |
            (Department.description.contains(query) if Department.description else False)
        )
        
        if active_only:
            search_query = search_query.where(Department.is_active == True)
        
        search_query = search_query.order_by(Department.name)
        
        return list(self.session.exec(search_query).all())
    
    def bulk_create(self, departments_data: List[DepartmentCreate]) -> Dict[str, Any]:
        """
        Create multiple departments in bulk.
        
        Args:
            departments_data: List of department creation data
            
        Returns:
            Dictionary with creation results
        """
        created = []
        errors = []
        
        for i, dept_data in enumerate(departments_data):
            try:
                department = self.create(dept_data)
                created.append(department)
            except DepartmentServiceError as e:
                errors.append({
                    "index": i,
                    "data": dept_data.dict(),
                    "error": str(e)
                })
        
        return {
            "created": created,
            "errors": errors,
            "total_created": len(created),
            "total_errors": len(errors)
        }
    
    def validate_department_sequence(self, department_ids: List[str]) -> bool:
        """
        Validate that all department IDs exist and are active.
        
        Args:
            department_ids: List of department IDs to validate
            
        Returns:
            True if all departments exist and are active
            
        Raises:
            DepartmentServiceError: If validation fails
        """
        departments = self.session.exec(
            select(Department).where(Department.id.in_(department_ids))
        ).all()
        
        found_ids = {dept.id for dept in departments}
        missing_ids = set(department_ids) - found_ids
        
        if missing_ids:
            raise DepartmentServiceError(f"Departments not found: {missing_ids}")
        
        inactive_departments = [dept for dept in departments if not dept.is_active]
        if inactive_departments:
            inactive_names = [dept.name for dept in inactive_departments]
            raise DepartmentServiceError(f"Inactive departments in sequence: {inactive_names}")
        
        return True
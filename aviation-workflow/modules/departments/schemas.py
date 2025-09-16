"""
Pydantic schemas for the departments module.

Defines request and response schemas for department API endpoints
with proper validation and documentation.
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, validator


class DepartmentBase(BaseModel):
    """Base department schema with common fields."""
    
    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Department name"
    )
    
    code: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Department code (unique identifier)"
    )
    
    description: Optional[str] = Field(
        None,
        max_length=5000,
        description="Department description"
    )
    
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional department metadata"
    )
    
    @validator('code')
    def validate_code(cls, v):
        """Validate department code format."""
        if not v:
            raise ValueError("Department code cannot be empty")
        
        # Code should be alphanumeric with underscores/dashes
        if not all(c.isalnum() or c in '_-' for c in v):
            raise ValueError("Department code can only contain letters, numbers, underscores, and dashes")
        
        return v.upper()  # Normalize to uppercase
    
    @validator('name')
    def validate_name(cls, v):
        """Validate department name."""
        if not v or not v.strip():
            raise ValueError("Department name cannot be empty")
        
        return v.strip()


class DepartmentCreate(DepartmentBase):
    """Schema for creating a new department."""
    
    is_active: Optional[bool] = Field(
        True,
        description="Whether the department is active"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "name": "Engineering",
                "code": "ENG",
                "description": "Engineering department responsible for technical reviews",
                "is_active": True,
                "metadata": {
                    "location": "Building A",
                    "manager": "John Doe",
                    "contact_email": "engineering@company.com"
                }
            }
        }


class DepartmentUpdate(BaseModel):
    """Schema for updating an existing department."""
    
    name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=255,
        description="Department name"
    )
    
    code: Optional[str] = Field(
        None,
        min_length=1,
        max_length=50,
        description="Department code"
    )
    
    description: Optional[str] = Field(
        None,
        max_length=5000,
        description="Department description"
    )
    
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional department metadata"
    )
    
    is_active: Optional[bool] = Field(
        None,
        description="Whether the department is active"
    )
    
    @validator('code')
    def validate_code(cls, v):
        """Validate department code format."""
        if v is not None:
            if not v:
                raise ValueError("Department code cannot be empty")
            
            # Code should be alphanumeric with underscores/dashes
            if not all(c.isalnum() or c in '_-' for c in v):
                raise ValueError("Department code can only contain letters, numbers, underscores, and dashes")
            
            return v.upper()  # Normalize to uppercase
        return v
    
    @validator('name')
    def validate_name(cls, v):
        """Validate department name."""
        if v is not None:
            if not v or not v.strip():
                raise ValueError("Department name cannot be empty")
            return v.strip()
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "name": "Quality Control",
                "description": "Updated description for QC department",
                "metadata": {
                    "location": "Building B",
                    "manager": "Jane Smith"
                }
            }
        }


class DepartmentResponse(DepartmentBase):
    """Schema for department responses with all fields."""
    
    id: str = Field(
        ...,
        description="Unique department identifier"
    )
    
    is_active: bool = Field(
        ...,
        description="Whether the department is active"
    )
    
    created_at: str = Field(
        ...,
        description="Timestamp when department was created (ISO format)"
    )
    
    class Config:
        orm_mode = True
        schema_extra = {
            "example": {
                "id": "a1b2c3d4e5f6",
                "name": "Engineering",
                "code": "ENG",
                "description": "Engineering department responsible for technical reviews",
                "metadata": {
                    "location": "Building A",
                    "manager": "John Doe",
                    "contact_email": "engineering@company.com"
                },
                "is_active": True,
                "created_at": "2023-01-01T12:00:00"
            }
        }


class DepartmentListResponse(BaseModel):
    """Schema for paginated department lists."""
    
    departments: list[DepartmentResponse] = Field(
        ...,
        description="List of departments"
    )
    
    total: int = Field(
        ...,
        description="Total number of departments"
    )
    
    active_count: int = Field(
        ...,
        description="Number of active departments"
    )
    
    inactive_count: int = Field(
        ...,
        description="Number of inactive departments"
    )


class DepartmentStats(BaseModel):
    """Schema for department statistics."""
    
    total_departments: int = Field(
        ...,
        description="Total number of departments"
    )
    
    active_departments: int = Field(
        ...,
        description="Number of active departments"
    )
    
    inactive_departments: int = Field(
        ...,
        description="Number of inactive departments"
    )
    
    newest_department: Optional[DepartmentResponse] = Field(
        None,
        description="Most recently created department"
    )


class DepartmentBulkCreate(BaseModel):
    """Schema for bulk department creation."""
    
    departments: list[DepartmentCreate] = Field(
        ...,
        min_items=1,
        max_items=100,
        description="List of departments to create"
    )
    
    @validator('departments')
    def validate_unique_codes(cls, v):
        """Ensure all department codes are unique within the batch."""
        codes = [dept.code for dept in v]
        if len(codes) != len(set(codes)):
            raise ValueError("Department codes must be unique within the batch")
        return v


class DepartmentBulkResponse(BaseModel):
    """Schema for bulk operation responses."""
    
    created: list[DepartmentResponse] = Field(
        ...,
        description="Successfully created departments"
    )
    
    errors: list[dict] = Field(
        ...,
        description="Errors encountered during creation"
    )
    
    total_created: int = Field(
        ...,
        description="Number of departments successfully created"
    )
    
    total_errors: int = Field(
        ...,
        description="Number of errors encountered"
    )
"""
Tests for the Departments module.

Tests CRUD operations, constraints, soft delete functionality, 
and module loading/unloading to ensure the departments module
follows the ModuleInterface specification.
"""

import pytest
from datetime import datetime, timedelta
from sqlmodel import select
from fastapi.testclient import TestClient

from modules.departments.models import Department
from modules.departments.service import DepartmentService, DepartmentServiceError, DuplicateNameError
from modules.departments.schemas import DepartmentRequest, DepartmentResponse
from modules.departments import module_interface
from core.plugin_manager import ModuleInterface


@pytest.mark.unit
class TestDepartmentModel:
    """Test Department SQLModel functionality."""
    
    def test_department_creation(self, test_session):
        """Test creating a department with valid data."""
        dept = Department(
            name="test_department",
            display_name="Test Department",
            description="A test department",
            manager="Test Manager",
            contact_email="test@aviation.com",
            phone="+1-555-0123",
            location="Test Location"
        )
        
        test_session.add(dept)
        test_session.commit()
        test_session.refresh(dept)
        
        assert dept.id is not None
        assert dept.name == "test_department"
        assert dept.display_name == "Test Department"
        assert dept.is_active is True
        assert dept.created_at is not None
        assert dept.updated_at is not None
    
    def test_department_unique_name_constraint(self, test_session):
        """Test that department names must be unique."""
        # Create first department
        dept1 = Department(
            name="unique_dept",
            display_name="First Department",
            contact_email="test1@aviation.com"
        )
        test_session.add(dept1)
        test_session.commit()
        
        # Attempt to create second department with same name
        dept2 = Department(
            name="unique_dept",  # Same name
            display_name="Second Department",
            contact_email="test2@aviation.com"
        )
        test_session.add(dept2)
        
        with pytest.raises(Exception):  # Database constraint violation
            test_session.commit()
    
    def test_department_email_validation(self, test_session):
        """Test email validation in department model."""
        # Valid email should work
        dept = Department(
            name="valid_email_dept",
            display_name="Valid Email Department",
            contact_email="valid@aviation.com"
        )
        test_session.add(dept)
        test_session.commit()
        assert dept.id is not None
    
    def test_department_soft_delete(self, test_session):
        """Test soft delete functionality."""
        dept = Department(
            name="soft_delete_dept",
            display_name="Soft Delete Department",
            contact_email="softdelete@aviation.com"
        )
        test_session.add(dept)
        test_session.commit()
        dept_id = dept.id
        
        # Soft delete
        dept.is_active = False
        dept.updated_at = datetime.utcnow()
        test_session.commit()
        
        # Verify still exists but inactive
        result = test_session.get(Department, dept_id)
        assert result is not None
        assert result.is_active is False
    
    def test_department_to_dict(self, test_session):
        """Test department to_dict method."""
        dept = Department(
            name="dict_test_dept",
            display_name="Dict Test Department",
            description="Testing to_dict method",
            manager="Test Manager",
            contact_email="dict@aviation.com",
            phone="+1-555-0456",
            location="Test Location"
        )
        test_session.add(dept)
        test_session.commit()
        
        dept_dict = dept.to_dict()
        
        assert isinstance(dept_dict, dict)
        assert dept_dict["name"] == "dict_test_dept"
        assert dept_dict["display_name"] == "Dict Test Department"
        assert dept_dict["is_active"] is True
        assert "id" in dept_dict
        assert "created_at" in dept_dict


@pytest.mark.unit
class TestDepartmentService:
    """Test DepartmentService business logic."""
    
    def test_create_department_success(self, test_session):
        """Test successful department creation via service."""
        service = DepartmentService(test_session)
        
        dept_data = DepartmentRequest(
            name="service_test_dept",
            display_name="Service Test Department",
            description="Created via service",
            manager="Service Manager",
            contact_email="service@aviation.com",
            phone="+1-555-0789",
            location="Service Location"
        )
        
        created_dept = service.create_department(dept_data)
        
        assert created_dept.id is not None
        assert created_dept.name == "service_test_dept"
        assert created_dept.display_name == "Service Test Department"
        assert created_dept.is_active is True
    
    def test_create_department_duplicate_name(self, test_session):
        """Test creating department with duplicate name raises error."""
        service = DepartmentService(test_session)
        
        # Create first department
        dept_data = DepartmentRequest(
            name="duplicate_dept",
            display_name="First Department",
            contact_email="first@aviation.com"
        )
        service.create_department(dept_data)
        
        # Attempt to create duplicate
        duplicate_data = DepartmentRequest(
            name="duplicate_dept",  # Same name
            display_name="Duplicate Department",
            contact_email="duplicate@aviation.com"
        )
        
        with pytest.raises(DuplicateNameError):
            service.create_department(duplicate_data)
    
    def test_get_department_by_id_success(self, test_session, sample_departments):
        """Test retrieving department by ID."""
        service = DepartmentService(test_session)
        dept = sample_departments[0]
        
        retrieved_dept = service.get_department_by_id(dept.id)
        
        assert retrieved_dept is not None
        assert retrieved_dept.id == dept.id
        assert retrieved_dept.name == dept.name
    
    def test_get_department_by_id_not_found(self, test_session):
        """Test retrieving non-existent department."""
        service = DepartmentService(test_session)
        
        with pytest.raises(DepartmentServiceError, match="Department not found"):
            service.get_department_by_id("non-existent-id")
    
    def test_get_department_by_name_success(self, test_session, sample_departments):
        """Test retrieving department by name."""
        service = DepartmentService(test_session)
        dept = sample_departments[0]
        
        retrieved_dept = service.get_department_by_name(dept.name)
        
        assert retrieved_dept is not None
        assert retrieved_dept.name == dept.name
        assert retrieved_dept.id == dept.id
    
    def test_get_department_by_name_not_found(self, test_session):
        """Test retrieving department with non-existent name."""
        service = DepartmentService(test_session)
        
        result = service.get_department_by_name("non_existent_dept")
        assert result is None
    
    def test_list_departments_all(self, test_session, sample_departments):
        """Test listing all departments."""
        service = DepartmentService(test_session)
        
        departments = service.list_departments(include_inactive=True)
        
        assert len(departments) >= len(sample_departments)
        dept_names = [d.name for d in departments]
        for sample_dept in sample_departments:
            assert sample_dept.name in dept_names
    
    def test_list_departments_active_only(self, test_session, sample_departments):
        """Test listing only active departments."""
        service = DepartmentService(test_session)
        
        # Deactivate one department
        sample_departments[0].is_active = False
        test_session.commit()
        
        active_departments = service.list_departments(include_inactive=False)
        
        # Should not include deactivated department
        active_names = [d.name for d in active_departments]
        assert sample_departments[0].name not in active_names
        assert sample_departments[1].name in active_names
    
    def test_update_department_success(self, test_session, sample_departments):
        """Test updating department information."""
        service = DepartmentService(test_session)
        dept = sample_departments[0]
        
        update_data = {
            "display_name": "Updated Department Name",
            "description": "Updated description",
            "manager": "New Manager"
        }
        
        updated_dept = service.update_department(dept.id, update_data)
        
        assert updated_dept.display_name == "Updated Department Name"
        assert updated_dept.description == "Updated description"
        assert updated_dept.manager == "New Manager"
        assert updated_dept.name == dept.name  # Should not change
        assert updated_dept.updated_at > dept.updated_at
    
    def test_update_department_not_found(self, test_session):
        """Test updating non-existent department."""
        service = DepartmentService(test_session)
        
        with pytest.raises(DepartmentServiceError, match="Department not found"):
            service.update_department("non-existent-id", {"display_name": "Updated"})
    
    def test_soft_delete_department(self, test_session, sample_departments):
        """Test soft deleting a department."""
        service = DepartmentService(test_session)
        dept = sample_departments[0]
        dept_id = dept.id
        
        result = service.soft_delete_department(dept_id)
        
        assert result is True
        
        # Verify department is deactivated
        deleted_dept = test_session.get(Department, dept_id)
        assert deleted_dept is not None
        assert deleted_dept.is_active is False
    
    def test_soft_delete_department_not_found(self, test_session):
        """Test soft deleting non-existent department."""
        service = DepartmentService(test_session)
        
        with pytest.raises(DepartmentServiceError, match="Department not found"):
            service.soft_delete_department("non-existent-id")
    
    def test_restore_department(self, test_session, sample_departments):
        """Test restoring a soft-deleted department."""
        service = DepartmentService(test_session)
        dept = sample_departments[0]
        
        # First soft delete
        service.soft_delete_department(dept.id)
        assert not test_session.get(Department, dept.id).is_active
        
        # Then restore
        result = service.restore_department(dept.id)
        assert result is True
        
        # Verify restoration
        restored_dept = test_session.get(Department, dept.id)
        assert restored_dept.is_active is True
    
    def test_department_exists(self, test_session, sample_departments):
        """Test checking if department exists."""
        service = DepartmentService(test_session)
        dept = sample_departments[0]
        
        # Test with existing department
        assert service.department_exists(dept.name) is True
        
        # Test with non-existent department
        assert service.department_exists("non_existent_dept") is False
    
    def test_get_department_statistics(self, test_session, sample_departments):
        """Test getting department statistics."""
        service = DepartmentService(test_session)
        
        # Deactivate one department for testing
        sample_departments[0].is_active = False
        test_session.commit()
        
        stats = service.get_department_statistics()
        
        assert "total_departments" in stats
        assert "active_departments" in stats
        assert "inactive_departments" in stats
        assert stats["total_departments"] == len(sample_departments)
        assert stats["active_departments"] == len(sample_departments) - 1
        assert stats["inactive_departments"] == 1


@pytest.mark.unit
class TestDepartmentSchemas:
    """Test Pydantic schemas for departments."""
    
    def test_department_request_validation(self):
        """Test DepartmentRequest schema validation."""
        # Valid request
        valid_data = {
            "name": "valid_dept",
            "display_name": "Valid Department",
            "description": "A valid department",
            "manager": "Manager Name",
            "contact_email": "valid@aviation.com",
            "phone": "+1-555-1234",
            "location": "Valid Location"
        }
        
        request = DepartmentRequest(**valid_data)
        assert request.name == "valid_dept"
        assert request.contact_email == "valid@aviation.com"
    
    def test_department_request_name_normalization(self):
        """Test that department names are normalized."""
        request = DepartmentRequest(
            name="Test Department Name",  # With spaces and caps
            display_name="Test Department",
            contact_email="test@aviation.com"
        )
        
        # Should be normalized to lowercase with underscores
        assert request.name == "test_department_name"
    
    def test_department_request_invalid_email(self):
        """Test invalid email validation."""
        with pytest.raises(ValueError, match="Invalid email format"):
            DepartmentRequest(
                name="test_dept",
                display_name="Test Department",
                contact_email="invalid-email"  # Invalid email
            )
    
    def test_department_response_serialization(self, sample_departments):
        """Test DepartmentResponse serialization."""
        dept = sample_departments[0]
        
        response = DepartmentResponse.from_orm(dept)
        
        assert response.id == dept.id
        assert response.name == dept.name
        assert response.display_name == dept.display_name
        assert response.is_active == dept.is_active


@pytest.mark.api
class TestDepartmentAPI:
    """Test Department API endpoints."""
    
    def test_create_department_endpoint(self, test_client):
        """Test POST /api/departments endpoint."""
        dept_data = {
            "name": "api_test_dept",
            "display_name": "API Test Department",
            "description": "Created via API",
            "manager": "API Manager",
            "contact_email": "api@aviation.com",
            "phone": "+1-555-9999",
            "location": "API Location"
        }
        
        response = test_client.post("/api/departments", json=dept_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "api_test_dept"
        assert data["display_name"] == "API Test Department"
        assert "id" in data
    
    def test_create_department_duplicate_name(self, test_client, sample_departments):
        """Test creating department with duplicate name via API."""
        existing_dept = sample_departments[0]
        
        dept_data = {
            "name": existing_dept.name,  # Duplicate name
            "display_name": "Duplicate Department",
            "contact_email": "duplicate@aviation.com"
        }
        
        response = test_client.post("/api/departments", json=dept_data)
        
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]
    
    def test_get_departments_list(self, test_client, sample_departments):
        """Test GET /api/departments endpoint."""
        response = test_client.get("/api/departments")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= len(sample_departments)
        
        # Check structure of returned data
        if data:
            dept = data[0]
            assert "id" in dept
            assert "name" in dept
            assert "display_name" in dept
    
    def test_get_department_by_id(self, test_client, sample_departments):
        """Test GET /api/departments/{id} endpoint."""
        dept = sample_departments[0]
        
        response = test_client.get(f"/api/departments/{dept.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == dept.id
        assert data["name"] == dept.name
    
    def test_get_department_by_id_not_found(self, test_client):
        """Test GET /api/departments/{id} with non-existent ID."""
        response = test_client.get("/api/departments/non-existent-id")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
    
    def test_update_department_endpoint(self, test_client, sample_departments):
        """Test PUT /api/departments/{id} endpoint."""
        dept = sample_departments[0]
        
        update_data = {
            "display_name": "Updated via API",
            "description": "Updated description"
        }
        
        response = test_client.put(f"/api/departments/{dept.id}", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["display_name"] == "Updated via API"
        assert data["description"] == "Updated description"
    
    def test_delete_department_endpoint(self, test_client, sample_departments):
        """Test DELETE /api/departments/{id} endpoint."""
        dept = sample_departments[0]
        
        response = test_client.delete(f"/api/departments/{dept.id}")
        
        assert response.status_code == 200
        
        # Verify department is soft deleted
        get_response = test_client.get(f"/api/departments/{dept.id}")
        assert get_response.status_code == 200
        data = get_response.json()
        assert data["is_active"] is False


@pytest.mark.unit
class TestDepartmentModuleInterface:
    """Test Department module interface compliance."""
    
    def test_module_interface_implementation(self):
        """Test that departments module implements ModuleInterface."""
        assert isinstance(module_interface, ModuleInterface)
        assert module_interface.name == "departments"
        assert module_interface.version is not None
        assert module_interface.description is not None
    
    def test_module_interface_components(self):
        """Test module interface components."""
        # Test router
        assert module_interface.router is not None
        assert hasattr(module_interface.router, 'routes')
        
        # Test models
        assert module_interface.models is not None
        assert Department in module_interface.models
        
        # Test dependencies
        assert module_interface.dependencies is not None
        assert isinstance(module_interface.dependencies, list)
    
    def test_module_lifecycle_methods(self):
        """Test module lifecycle methods."""
        # Test on_load
        result = module_interface.on_load()
        assert isinstance(result, bool)
        
        # Test validate_config
        result = module_interface.validate_config({})
        assert isinstance(result, bool)
        
        # Test on_unload
        result = module_interface.on_unload()
        assert isinstance(result, bool)
    
    def test_module_capabilities(self):
        """Test module capability reporting."""
        capabilities = module_interface.get_capabilities()
        assert isinstance(capabilities, dict)
        assert "crud_operations" in capabilities
        assert "soft_delete" in capabilities
        assert capabilities["crud_operations"] is True
        assert capabilities["soft_delete"] is True


@pytest.mark.integration
class TestDepartmentModuleLoading:
    """Test department module loading and unloading."""
    
    def test_module_loading_success(self, test_plugin_manager):
        """Test successful module loading."""
        # Load the departments module
        loaded_module = test_plugin_manager.load_module("departments")
        
        assert loaded_module is not None
        assert loaded_module.name == "departments"
        assert test_plugin_manager.is_module_loaded("departments")
    
    def test_module_unloading_success(self, test_plugin_manager):
        """Test successful module unloading."""
        # Load first
        test_plugin_manager.load_module("departments")
        assert test_plugin_manager.is_module_loaded("departments")
        
        # Then unload
        result = test_plugin_manager.unload_module("departments")
        assert result is True
        assert not test_plugin_manager.is_module_loaded("departments")
    
    def test_module_status_reporting(self, test_plugin_manager):
        """Test module status reporting."""
        # Load module
        test_plugin_manager.load_module("departments")
        
        # Get status
        status = test_plugin_manager.get_module_status()
        assert "departments" in status
        
        module_status = status["departments"]
        assert module_status["loaded"] is True
        assert module_status["name"] == "departments"
        assert "version" in module_status


@pytest.mark.integration
class TestDepartmentWorkflowIntegration:
    """Test department integration with workflow system."""
    
    def test_department_in_workflow_sequence(self, test_session, sample_departments):
        """Test using departments in workflow sequences."""
        # This would test integration with workflow templates
        # For now, verify departments can be referenced by name
        dept_names = [dept.name for dept in sample_departments]
        
        # Simulate workflow template using department sequence
        workflow_sequence = dept_names[:2]  # Use first 2 departments
        
        assert len(workflow_sequence) == 2
        assert workflow_sequence[0] in dept_names
        assert workflow_sequence[1] in dept_names
    
    def test_department_validation_for_workflows(self, test_session, sample_departments):
        """Test department validation for workflow creation."""
        service = DepartmentService(test_session)
        
        # Valid department sequence
        valid_sequence = [dept.name for dept in sample_departments]
        validation_result = service.validate_department_sequence(valid_sequence)
        assert validation_result["valid"] is True
        assert len(validation_result["invalid_departments"]) == 0
        
        # Invalid department sequence
        invalid_sequence = ["valid_dept", "invalid_dept"]
        invalid_sequence[0] = sample_departments[0].name  # Make first one valid
        
        validation_result = service.validate_department_sequence(invalid_sequence)
        assert validation_result["valid"] is False
        assert "invalid_dept" in validation_result["invalid_departments"]
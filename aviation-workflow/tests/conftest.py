"""
Pytest configuration and fixtures for the Aviation Workflow System.

Provides test database setup, FastAPI test client, mock services,
and factory functions for creating test data.
"""

import pytest
import tempfile
import os
from typing import Generator, Dict, Any
from datetime import datetime, timedelta
from sqlmodel import SQLModel, create_engine, Session
from fastapi.testclient import TestClient
import factory
from factory import Faker

# Import application components
from api.main import app
from core.database import DatabaseManager
from core.config import settings
from core.models import WorkItem
from core.plugin_manager import PluginManager
from core.workflow_engine import WorkflowEngine

# Import module models
from modules.departments.models import Department
from modules.templates.models import WorkflowTemplate
from modules.comments.models import Comment


# =============================================================================
# DATABASE FIXTURES
# =============================================================================

@pytest.fixture(scope="session")
def test_engine():
    """Create a test database engine using in-memory SQLite."""
    # Use in-memory SQLite for fast tests
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,  # Set to True for SQL debugging
        connect_args={"check_same_thread": False}
    )
    
    # Create all tables
    SQLModel.metadata.create_all(engine)
    
    yield engine
    
    # Cleanup
    engine.dispose()


@pytest.fixture
def test_session(test_engine) -> Generator[Session, None, None]:
    """Create a test database session."""
    with Session(test_engine) as session:
        yield session
        # Rollback any changes made during the test
        session.rollback()


@pytest.fixture
def db_session(test_session):
    """Alias for test_session for backward compatibility."""
    return test_session


# =============================================================================
# FASTAPI TEST CLIENT
# =============================================================================

@pytest.fixture
def test_client(test_session) -> TestClient:
    """Create a FastAPI test client with test database."""
    
    # Override the database dependency to use test session
    def get_test_session():
        return test_session
    
    # Override dependencies
    app.dependency_overrides[DatabaseManager().get_session] = get_test_session
    
    client = TestClient(app)
    
    yield client
    
    # Cleanup
    app.dependency_overrides.clear()


@pytest.fixture
def authenticated_client(test_client) -> TestClient:
    """Create an authenticated test client (mock authentication)."""
    # In a real system, this would handle JWT tokens
    # For testing, we'll mock the authentication
    test_client.headers.update({"Authorization": "Bearer mock-token"})
    return test_client


# =============================================================================
# PLUGIN MANAGER AND MODULE FIXTURES
# =============================================================================

@pytest.fixture
def test_plugin_manager():
    """Create a test plugin manager with controlled module loading."""
    plugin_manager = PluginManager()
    
    # Override settings for testing
    original_modules = settings.enabled_modules
    settings.enabled_modules = "departments,templates,comments"
    
    yield plugin_manager
    
    # Restore original settings
    settings.enabled_modules = original_modules


@pytest.fixture
def loaded_modules(test_plugin_manager):
    """Load test modules and return loaded module interfaces."""
    modules = {}
    
    # Load core test modules
    for module_name in ["departments", "templates", "comments"]:
        try:
            module_interface = test_plugin_manager.load_module(module_name)
            if module_interface:
                modules[module_name] = module_interface
        except Exception as e:
            pytest.skip(f"Could not load module {module_name}: {e}")
    
    return modules


# =============================================================================
# WORKFLOW ENGINE FIXTURES
# =============================================================================

@pytest.fixture
def test_workflow_engine():
    """Create a test workflow engine."""
    # Use temporary directory for test state storage
    with tempfile.TemporaryDirectory() as temp_dir:
        engine = WorkflowEngine(state_dir=temp_dir)
        yield engine


@pytest.fixture
def mock_workflow_state():
    """Create mock workflow state data."""
    return {
        "current_step": 0,
        "department_sequence": ["department_1", "department_2", "department_3"],
        "status": "pending",
        "history": [],
        "metadata": {
            "created_at": datetime.utcnow().isoformat(),
            "created_by": "test_user@aviation.com"
        }
    }


# =============================================================================
# DATA FACTORIES
# =============================================================================

class DepartmentFactory(factory.Factory):
    """Factory for creating test Department instances."""
    
    class Meta:
        model = Department
    
    name = factory.Sequence(lambda n: f"department_{n}")
    display_name = factory.Faker("company")
    description = factory.Faker("text", max_nb_chars=200)
    manager = factory.Faker("name")
    contact_email = factory.Faker("email")
    phone = factory.Faker("phone_number")
    location = factory.Faker("address")
    is_active = True
    created_at = factory.LazyFunction(datetime.utcnow)
    updated_at = factory.LazyFunction(datetime.utcnow)


class WorkflowTemplateFactory(factory.Factory):
    """Factory for creating test WorkflowTemplate instances."""
    
    class Meta:
        model = WorkflowTemplate
    
    name = factory.Sequence(lambda n: f"template_{n}")
    display_name = factory.Faker("sentence", nb_words=3)
    description = factory.Faker("text", max_nb_chars=200)
    department_sequence = factory.LazyFunction(
        lambda: ["department_1", "department_2", "department_3"]
    )
    approval_rules = factory.LazyFunction(
        lambda: {
            "require_comment": True,
            "min_approvals": 1,
            "allow_parallel_approval": False
        }
    )
    workflow_config = factory.LazyFunction(
        lambda: {"timeout": 3600, "auto_approve_minor": False}
    )
    category = factory.Faker("word")
    is_active = True
    created_by = factory.Faker("email")
    created_at = factory.LazyFunction(datetime.utcnow)
    updated_at = factory.LazyFunction(datetime.utcnow)


class WorkItemFactory(factory.Factory):
    """Factory for creating test WorkItem instances."""
    
    class Meta:
        model = WorkItem
    
    title = factory.Faker("sentence", nb_words=5)
    description = factory.Faker("text", max_nb_chars=500)
    priority = factory.Faker("random_element", elements=["low", "medium", "high", "critical"])
    status = factory.Faker("random_element", elements=["pending", "in_progress", "approved", "rejected"])
    department_ids = factory.LazyFunction(
        lambda: ["department_1", "department_2"]
    )
    current_step = 0
    created_by = factory.Faker("email")
    assigned_to = factory.Faker("email")
    due_date = factory.LazyFunction(
        lambda: datetime.utcnow() + timedelta(days=7)
    )
    created_at = factory.LazyFunction(datetime.utcnow)
    updated_at = factory.LazyFunction(datetime.utcnow)
    item_metadata = factory.LazyFunction(
        lambda: {
            "aircraft_tail": "N123AB",
            "location": "KORD",
            "estimated_hours": 2.0
        }
    )


class CommentFactory(factory.Factory):
    """Factory for creating test Comment instances."""
    
    class Meta:
        model = Comment
    
    work_item_id = factory.Faker("uuid4")
    content = factory.Faker("text", max_nb_chars=300)
    comment_type = factory.Faker("random_element", 
                                elements=["status_update", "approval", "rejection", "question"])
    created_by = factory.Faker("email")
    department_id = factory.Faker("uuid4")
    is_internal = factory.Faker("boolean")
    created_at = factory.LazyFunction(datetime.utcnow)
    metadata = factory.LazyFunction(
        lambda: {"approval_status": "pending"}
    )


# =============================================================================
# SAMPLE DATA FIXTURES
# =============================================================================

@pytest.fixture
def sample_departments(test_session):
    """Create sample departments in the test database."""
    departments = []
    
    # Create standard aviation departments
    dept_data = [
        {
            "name": "flight_operations",
            "display_name": "Flight Operations",
            "description": "Flight planning and operations",
            "manager": "Captain Jane Smith",
            "contact_email": "flight.ops@test.com"
        },
        {
            "name": "maintenance",
            "display_name": "Aircraft Maintenance", 
            "description": "Aircraft maintenance and repairs",
            "manager": "Chief Engineer Bob Johnson",
            "contact_email": "maintenance@test.com"
        },
        {
            "name": "safety_quality",
            "display_name": "Safety & Quality",
            "description": "Safety compliance and quality assurance",
            "manager": "Safety Director Alice Brown",
            "contact_email": "safety@test.com"
        }
    ]
    
    for data in dept_data:
        dept = Department(**data)
        test_session.add(dept)
        departments.append(dept)
    
    test_session.commit()
    return departments


@pytest.fixture
def sample_template(test_session, sample_departments):
    """Create a sample workflow template."""
    template = WorkflowTemplateFactory(
        name="test_maintenance_workflow",
        display_name="Test Maintenance Workflow",
        department_sequence=[dept.name for dept in sample_departments],
        created_by="test@aviation.com"
    )
    
    test_session.add(template)
    test_session.commit()
    test_session.refresh(template)
    
    return template


@pytest.fixture
def sample_work_item(test_session, sample_template):
    """Create a sample work item."""
    work_item = WorkItemFactory(
        title="Test Aircraft Maintenance",
        department_ids=sample_template.department_sequence,
        created_by="test@aviation.com"
    )
    
    test_session.add(work_item)
    test_session.commit()
    test_session.refresh(work_item)
    
    return work_item


@pytest.fixture
def sample_comment(test_session, sample_work_item, sample_departments):
    """Create a sample comment."""
    comment = CommentFactory(
        work_item_id=sample_work_item.id,
        department_id=sample_departments[0].id,
        created_by="test@aviation.com"
    )
    
    test_session.add(comment)
    test_session.commit()
    test_session.refresh(comment)
    
    return comment


# =============================================================================
# UTILITY FIXTURES
# =============================================================================

@pytest.fixture
def mock_user():
    """Create mock user data for testing."""
    return {
        "id": "test-user-id",
        "email": "test@aviation.com",
        "name": "Test User",
        "department": "flight_operations",
        "role": "approver",
        "permissions": ["read", "write", "approve"]
    }


@pytest.fixture
def aviation_test_data():
    """Provide aviation-specific test data."""
    return {
        "aircraft_tails": ["N123AB", "N456CD", "N789EF"],
        "airports": ["KORD", "KLAX", "KJFK", "KATL"],
        "maintenance_types": ["Routine", "Scheduled", "Emergency"],
        "priorities": ["low", "medium", "high", "critical"],
        "statuses": ["pending", "in_progress", "approved", "rejected", "completed"]
    }


@pytest.fixture
def mock_api_responses():
    """Mock API response data for external service testing."""
    return {
        "work_items": {
            "GET": [
                {
                    "id": "test-id-1",
                    "title": "Test Work Item",
                    "status": "pending",
                    "priority": "medium"
                }
            ],
            "POST": {
                "id": "test-id-new",
                "title": "New Work Item",
                "status": "pending"
            }
        },
        "departments": {
            "GET": [
                {
                    "id": "dept-1",
                    "name": "test_department",
                    "display_name": "Test Department"
                }
            ]
        }
    }


# =============================================================================
# CLEANUP AND TEARDOWN
# =============================================================================

@pytest.fixture(autouse=True)
def cleanup_after_test():
    """Automatic cleanup after each test."""
    yield
    
    # Clear any cached data
    # Reset any global state
    # Clean up temporary files if needed


# =============================================================================
# PYTEST CONFIGURATION
# =============================================================================

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "api: mark test as API test"
    )
    config.addinivalue_line(
        "markers", "workflow: mark test as workflow test"
    )


def pytest_collection_modifyitems(config, items):
    """Modify collected test items."""
    # Add markers to tests based on their location
    for item in items:
        if "test_integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "test_core" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "test_modules" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        
        if "workflow" in item.name.lower():
            item.add_marker(pytest.mark.workflow)
        
        if "api" in item.name.lower():
            item.add_marker(pytest.mark.api)


# =============================================================================
# MOCK FIXTURES FOR EXTERNAL DEPENDENCIES
# =============================================================================

@pytest.fixture
def mock_email_service():
    """Mock email service for notification testing."""
    class MockEmailService:
        def __init__(self):
            self.sent_emails = []
        
        def send_email(self, to, subject, body):
            self.sent_emails.append({
                "to": to,
                "subject": subject,
                "body": body,
                "sent_at": datetime.utcnow()
            })
            return True
        
        def get_sent_emails(self):
            return self.sent_emails
        
        def clear_sent_emails(self):
            self.sent_emails = []
    
    return MockEmailService()


@pytest.fixture
def mock_redis_client():
    """Mock Redis client for caching tests."""
    class MockRedisClient:
        def __init__(self):
            self.data = {}
        
        def get(self, key):
            return self.data.get(key)
        
        def set(self, key, value, ex=None):
            self.data[key] = value
            return True
        
        def delete(self, key):
            return self.data.pop(key, None) is not None
        
        def exists(self, key):
            return key in self.data
        
        def flushall(self):
            self.data.clear()
    
    return MockRedisClient()


@pytest.fixture
def temp_file():
    """Create a temporary file for testing."""
    fd, path = tempfile.mkstemp()
    
    yield path
    
    # Cleanup
    os.close(fd)
    os.unlink(path)
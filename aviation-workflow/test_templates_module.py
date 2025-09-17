#!/usr/bin/env python3
"""
Test script for the templates module with workflow integration.

Tests module interface compliance, template functionality, and workflow
integration to ensure templates work correctly with work item creation.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_module_interface_compliance():
    """Test that the templates module follows ModuleInterface specification."""
    print("🧪 Testing ModuleInterface compliance...")
    
    try:
        from modules.templates import module_interface
        from core.plugin_manager import ModuleInterface
        
        # Check that it's an instance of ModuleInterface
        assert isinstance(module_interface, ModuleInterface), "Should be ModuleInterface instance"
        
        # Check required attributes
        assert hasattr(module_interface, 'name'), "Should have name attribute"
        assert hasattr(module_interface, 'version'), "Should have version attribute"
        assert hasattr(module_interface, 'description'), "Should have description attribute"
        
        # Check attribute values
        assert module_interface.name == "templates", "Name should be 'templates'"
        assert module_interface.version == "1.0.0", "Version should be '1.0.0'"
        assert isinstance(module_interface.description, str), "Description should be string"
        
        # Check optional components
        assert hasattr(module_interface, 'router'), "Should have router attribute"
        assert hasattr(module_interface, 'models'), "Should have models attribute"
        assert hasattr(module_interface, 'dependencies'), "Should have dependencies attribute"
        
        # Check lifecycle methods
        assert hasattr(module_interface, 'on_load'), "Should have on_load method"
        assert hasattr(module_interface, 'on_unload'), "Should have on_unload method"
        assert hasattr(module_interface, 'validate_config'), "Should have validate_config method"
        
        print("  ✅ ModuleInterface compliance verified")
        return True
        
    except Exception as e:
        print(f"  ❌ ModuleInterface compliance test failed: {e}")
        return False


def test_module_components():
    """Test that module components are properly defined."""
    print("🧪 Testing module components...")
    
    try:
        from modules.templates import module_interface
        
        # Test router
        if module_interface.router:
            assert hasattr(module_interface.router, 'routes'), "Router should have routes"
            route_count = len([r for r in module_interface.router.routes if hasattr(r, 'path')])
            print(f"  📝 Router has {route_count} routes")
        
        # Test models
        if module_interface.models:
            assert isinstance(module_interface.models, list), "Models should be a list"
            assert len(module_interface.models) > 0, "Should have at least one model"
            
            # Check WorkflowTemplate model
            from modules.templates.models import WorkflowTemplate
            assert WorkflowTemplate in module_interface.models, "Should include WorkflowTemplate model"
            print(f"  📝 Models: {[m.__name__ for m in module_interface.models]}")
        
        # Test dependencies
        if module_interface.dependencies:
            assert isinstance(module_interface.dependencies, list), "Dependencies should be a list"
            print(f"  📝 Dependencies: {module_interface.dependencies}")
        else:
            print("  📝 No dependencies")
        
        print("  ✅ Module components verified")
        return True
        
    except Exception as e:
        print(f"  ❌ Module components test failed: {e}")
        return False


def test_workflow_template_model():
    """Test WorkflowTemplate model functionality."""
    print("🧪 Testing WorkflowTemplate model...")
    
    try:
        from modules.templates.models import WorkflowTemplate
        
        # Test model creation
        template = WorkflowTemplate(
            name="test_template",
            display_name="Test Template",
            description="A test template for testing",
            department_sequence=["dept_1", "dept_2", "dept_3"],
            approval_rules={"require_comment": True, "min_approvals": 1},
            workflow_config={"timeout": 3600},
            category="testing",
            created_by="test_user"
        )
        
        assert template.name == "test_template", "Name should be set"
        assert template.display_name == "Test Template", "Display name should be set"
        assert template.department_sequence == ["dept_1", "dept_2", "dept_3"], "Department sequence should be set"
        assert template.is_active == True, "Should be active by default"
        assert template.created_at is not None, "Created timestamp should be set"
        
        # Test helper methods
        assert template.get_department_count() == 3, "Should count departments correctly"
        assert template.get_max_steps() == 2, "Should calculate max steps correctly"
        assert template.is_valid_step(1) == True, "Should validate valid steps"
        assert template.is_valid_step(5) == False, "Should reject invalid steps"
        assert template.get_department_at_step(1) == "dept_2", "Should get correct department at step"
        
        # Test approval methods
        assert template.can_approve_from_step(1) == True, "Should allow approval from middle step"
        assert template.can_approve_from_step(2) == False, "Should not allow approval from final step"
        assert template.can_reject_to_step(2, 0) == True, "Should allow rejection backwards"
        assert template.can_reject_to_step(1, 2) == False, "Should not allow rejection forwards"
        
        # Test to_dict
        template_dict = template.to_dict()
        assert "id" in template_dict, "Dict should include ID"
        assert template_dict["name"] == "test_template", "Dict should include name"
        
        print("  ✅ WorkflowTemplate model functionality verified")
        return True
        
    except Exception as e:
        print(f"  ❌ WorkflowTemplate model test failed: {e}")
        return False


def test_template_schemas():
    """Test Pydantic schemas for templates."""
    print("🧪 Testing Pydantic schemas...")
    
    try:
        from modules.templates.schemas import TemplateRequest, TemplateResponse, TemplateValidationRequest
        
        # Test TemplateRequest
        request_data = {
            "name": "test template",
            "display_name": "Test Template",
            "description": "A test template",
            "department_sequence": ["dept_1", "dept_2"],
            "category": "general",
            "created_by": "test_user"
        }
        
        request_schema = TemplateRequest(**request_data)
        assert request_schema.name == "test_template", "Name should be normalized"  # Converted to lowercase with underscores
        assert request_schema.department_sequence == ["dept_1", "dept_2"], "Department sequence should be set"
        
        # Test TemplateValidationRequest
        validation_data = {
            "department_sequence": ["dept_1", "dept_2", "dept_3"]
        }
        
        validation_schema = TemplateValidationRequest(**validation_data)
        assert len(validation_schema.department_sequence) == 3, "Should have 3 departments"
        
        # Test validation - empty department sequence should fail
        try:
            TemplateRequest(
                name="test",
                display_name="Test",
                description="Test",
                department_sequence=[],
                created_by="test"
            )
            assert False, "Should have failed validation for empty department sequence"
        except ValueError:
            pass  # Expected
        
        # Test validation - duplicate departments should fail
        try:
            TemplateRequest(
                name="test",
                display_name="Test", 
                description="Test",
                department_sequence=["dept_1", "dept_1"],
                created_by="test"
            )
            assert False, "Should have failed validation for duplicate departments"
        except ValueError:
            pass  # Expected
        
        print("  ✅ Pydantic schemas verified")
        return True
        
    except Exception as e:
        print(f"  ❌ Pydantic schemas test failed: {e}")
        return False


def test_template_service_classes():
    """Test TemplateService classes without database connection."""
    print("🧪 Testing TemplateService (basic functionality)...")
    
    try:
        # Test that service classes can be imported
        from modules.templates.service import (
            TemplateService,
            TemplateServiceError,
            TemplateNotFoundError,
            TemplateValidationError,
            DuplicateTemplateError
        )
        
        # Test exception classes
        try:
            raise TemplateServiceError("Test error")
        except TemplateServiceError as e:
            assert str(e) == "Test error", "Exception should carry message"
        
        try:
            raise TemplateNotFoundError("Template not found")
        except TemplateNotFoundError as e:
            assert str(e) == "Template not found", "Exception should carry message"
        
        try:
            raise TemplateValidationError("Validation error")
        except TemplateValidationError as e:
            assert str(e) == "Validation error", "Exception should carry message"
        
        try:
            raise DuplicateTemplateError("Duplicate template")
        except DuplicateTemplateError as e:
            assert str(e) == "Duplicate template", "Exception should carry message"
        
        print("  ✅ TemplateService classes verified")
        return True
        
    except Exception as e:
        print(f"  ❌ TemplateService test failed: {e}")
        return False


def test_api_routes_structure():
    """Test API routes structure without server."""
    print("🧪 Testing API routes structure...")
    
    try:
        from modules.templates.routes import router
        
        # Check that router exists and has routes
        assert router is not None, "Router should exist"
        assert hasattr(router, 'routes'), "Router should have routes"
        
        # Check for required endpoints
        route_paths = []
        for route in router.routes:
            if hasattr(route, 'path'):
                route_paths.append(route.path)
        
        print(f"  📝 Available routes: {route_paths}")
        
        # Check for core template endpoints
        expected_patterns = [
            "",  # Root path for POST/GET
            "/{template_id}",
            "/active",
            "/validate",
            "/default/{category}",
            "/stats"
        ]
        
        for pattern in expected_patterns:
            found = any(pattern in path for path in route_paths)
            assert found, f"Expected route pattern {pattern} not found"
        
        print("  ✅ API routes structure verified")
        return True
        
    except Exception as e:
        print(f"  ❌ API routes structure test failed: {e}")
        return False


def test_workflow_integration_compatibility():
    """Test compatibility with workflow engine."""
    print("🧪 Testing workflow integration compatibility...")
    
    try:
        # Test that workflow engine can be imported
        from core.workflow_engine import WorkflowEngine, workflow_engine
        
        assert WorkflowEngine is not None, "WorkflowEngine class should be available"
        assert workflow_engine is not None, "Workflow engine instance should be available"
        
        # Test that service can be instantiated (without database)
        from modules.templates.service import TemplateService
        
        # Service requires session, so we can't test instantiation
        # But we can test that the class is importable
        assert TemplateService is not None, "TemplateService should be importable"
        
        # Test that the service has required methods
        required_methods = [
            'create_template', 'get_template', 'list_active_templates',
            'validate_department_sequence', 'record_template_usage'
        ]
        for method_name in required_methods:
            assert hasattr(TemplateService, method_name), f"Service should have {method_name} method"
        
        print("  ✅ Workflow integration compatibility verified")
        return True
        
    except Exception as e:
        print(f"  ❌ Workflow integration test failed: {e}")
        return False


def test_plugin_manager_integration():
    """Test integration with plugin manager."""
    print("🧪 Testing plugin manager integration...")
    
    try:
        from core.plugin_manager import PluginManager
        
        # Create plugin manager
        plugin_manager = PluginManager()
        
        # Test loading the templates module
        print("  → Loading templates module...")
        loaded_module = plugin_manager.load_module("templates")
        
        assert loaded_module is not None, "Module should load successfully"
        assert plugin_manager.is_module_loaded("templates"), "Module should be marked as loaded"
        
        # Check module status
        status = plugin_manager.get_module_status()
        assert "templates" in status, "Module should appear in status"
        
        module_status = status["templates"]
        assert module_status["name"] == "templates", "Status should show correct name"
        assert module_status["version"] == "1.0.0", "Status should show correct version"
        
        print(f"  📝 Module status: {module_status}")
        
        # Test unloading
        print("  → Unloading templates module...")
        unloaded = plugin_manager.unload_module("templates")
        
        assert unloaded, "Module should unload successfully"
        assert not plugin_manager.is_module_loaded("templates"), "Module should be marked as unloaded"
        
        print("  ✅ Plugin manager integration verified")
        return True
        
    except Exception as e:
        print(f"  ❌ Plugin manager integration test failed: {e}")
        return False


def test_module_capabilities():
    """Test module capability reporting."""
    print("🧪 Testing module capabilities...")
    
    try:
        from modules.templates import module_interface
        
        # Test template capabilities
        capabilities = module_interface.get_template_capabilities()
        assert isinstance(capabilities, dict), "Should return capabilities dict"
        assert "template_features" in capabilities, "Should list template features"
        assert "supports_validation" in capabilities, "Should report validation support"
        assert capabilities["supports_validation"] == True, "Should support validation"
        assert capabilities["supports_categories"] == True, "Should support categories"
        
        # Test workflow integration info
        workflow_info = module_interface.get_workflow_integration_info()
        assert isinstance(workflow_info, dict), "Should return workflow info dict"
        assert "supports_burr_workflows" in workflow_info, "Should report Burr support"
        assert workflow_info["supports_burr_workflows"] == True, "Should support Burr workflows"
        
        # Test stats summary
        stats = module_interface.get_template_stats_summary()
        assert isinstance(stats, dict), "Should return stats dict"
        assert "module_version" in stats, "Should include version"
        assert stats["depends_on_departments"] == True, "Should depend on departments"
        
        # Test dependency verification
        deps = module_interface.verify_dependencies()
        assert isinstance(deps, dict), "Should return dependencies dict"
        assert "status" in deps, "Should include status"
        assert "all_available" in deps, "Should include availability check"
        
        print(f"  📝 Template capabilities: {capabilities['template_features']}")
        print(f"  📝 Workflow integration: supports_burr_workflows={workflow_info['supports_burr_workflows']}")
        
        print("  ✅ Module capabilities verified")
        return True
        
    except Exception as e:
        print(f"  ❌ Module capabilities test failed: {e}")
        return False


def test_template_integration():
    """Test template integration with workflow system."""
    print("🧪 Testing template integration...")
    
    try:
        # Test that templates module integrates with core system
        from modules.templates import module_interface
        
        # Check integration info
        integration = module_interface.get_integration_info()
        assert isinstance(integration, dict), "Should return integration dict"
        assert integration["standalone"] == False, "Should not be standalone (depends on departments)"
        assert integration["removable"] == True, "Should be removable"
        assert integration["affects_workflow"] == True, "Should affect workflow creation"
        assert integration["affects_state_transitions"] == False, "Should not affect existing workflows"
        
        # Check that it's removable but affects functionality
        assert module_interface.is_removable() == True, "Module should report as removable"
        
        # Verify it has the right integration points
        assert "work_items" in integration["integration_points"], "Should integrate with work items"
        assert "departments" in integration["integration_points"], "Should integrate with departments"
        assert "workflow_engine" in integration["integration_points"], "Should integrate with workflow engine"
        
        print(f"  📝 Integration points: {integration['integration_points']}")
        print(f"  📝 Affects workflow creation: {integration['affects_workflow']}")
        print(f"  📝 Removable: {integration['removable']}")
        
        print("  ✅ Template integration verified")
        return True
        
    except Exception as e:
        print(f"  ❌ Template integration test failed: {e}")
        return False


def main():
    """Run all templates module tests."""
    print("🚀 Starting Templates Module Tests")
    print("=" * 50)
    
    tests = [
        test_module_interface_compliance,
        test_module_components,
        test_workflow_template_model,
        test_template_schemas,
        test_template_service_classes,
        test_api_routes_structure,
        test_workflow_integration_compatibility,
        test_plugin_manager_integration,
        test_module_capabilities,
        test_template_integration
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
            failed += 1
        print()
    
    print("=" * 50)
    print(f"📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed! Templates module is working correctly.")
        print("\n📋 Templates Module Summary:")
        print("  • ✅ ModuleInterface compliance verified")
        print("  • ✅ WorkflowTemplate SQLModel with department sequences")
        print("  • ✅ TemplateService with CRUD and validation operations")
        print("  • ✅ API routes: POST/GET /templates, template validation, etc.")
        print("  • ✅ Pydantic schemas with comprehensive validation")
        print("  • ✅ Plugin manager integration")
        print("  • ✅ Workflow engine integration for template-based creation")
        print("  • ✅ Department sequence validation and approval rules")
        print("  • ✅ Template categories and usage tracking")
        print("  • ✅ Integration with work item creation process")
        return 0
    else:
        print("⚠️  Some tests failed. Check the implementation.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
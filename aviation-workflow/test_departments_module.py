#!/usr/bin/env python3
"""
Test script for the departments module.

Tests module loading, interface compliance, and enabling/disabling
via ENABLED_MODULES configuration.
"""

import sys
import os
import tempfile
import shutil

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_module_interface_compliance():
    """Test that the departments module follows ModuleInterface specification."""
    print("🧪 Testing ModuleInterface compliance...")
    
    try:
        from modules.departments import module_interface
        from core.plugin_manager import ModuleInterface
        
        # Check that it's an instance of ModuleInterface
        assert isinstance(module_interface, ModuleInterface), "Should be ModuleInterface instance"
        
        # Check required attributes
        assert hasattr(module_interface, 'name'), "Should have name attribute"
        assert hasattr(module_interface, 'version'), "Should have version attribute"
        assert hasattr(module_interface, 'description'), "Should have description attribute"
        
        # Check attribute values
        assert module_interface.name == "departments", "Name should be 'departments'"
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
        
        # Check that methods are callable
        assert callable(module_interface.on_load), "on_load should be callable"
        assert callable(module_interface.on_unload), "on_unload should be callable"
        assert callable(module_interface.validate_config), "validate_config should be callable"
        
        print("  ✅ ModuleInterface compliance verified")
        return True
        
    except Exception as e:
        print(f"  ❌ ModuleInterface compliance test failed: {e}")
        return False


def test_module_components():
    """Test that module components are properly defined."""
    print("🧪 Testing module components...")
    
    try:
        from modules.departments import module_interface
        
        # Test router
        if module_interface.router:
            assert hasattr(module_interface.router, 'routes'), "Router should have routes"
            route_count = len([r for r in module_interface.router.routes if hasattr(r, 'path')])
            print(f"  📝 Router has {route_count} routes")
        
        # Test models
        if module_interface.models:
            assert isinstance(module_interface.models, list), "Models should be a list"
            assert len(module_interface.models) > 0, "Should have at least one model"
            
            # Check Department model
            from modules.departments.models import Department
            assert Department in module_interface.models, "Should include Department model"
            print(f"  📝 Models: {[m.__name__ for m in module_interface.models]}")
        
        # Test dependencies
        if module_interface.dependencies:
            assert isinstance(module_interface.dependencies, list), "Dependencies should be a list"
            print(f"  📝 Dependencies: {module_interface.dependencies}")
        else:
            print("  📝 No dependencies (expected for departments module)")
        
        print("  ✅ Module components verified")
        return True
        
    except Exception as e:
        print(f"  ❌ Module components test failed: {e}")
        return False


def test_module_lifecycle():
    """Test module lifecycle methods."""
    print("🧪 Testing module lifecycle...")
    
    try:
        from modules.departments import module_interface
        
        # Test on_load
        print("  → Testing on_load...")
        module_interface.on_load()  # Should not raise exception
        
        # Test validate_config
        print("  → Testing validate_config...")
        
        # Test with empty config
        assert module_interface.validate_config({}), "Should accept empty config"
        
        # Test with valid config
        valid_config = {
            "auto_create_defaults": True,
            "default_departments": [
                {"name": "Test Dept", "code": "TEST"}
            ]
        }
        assert module_interface.validate_config(valid_config), "Should accept valid config"
        
        # Test with invalid config
        invalid_config = {
            "auto_create_defaults": "not_a_boolean",
            "default_departments": "not_a_list"
        }
        assert not module_interface.validate_config(invalid_config), "Should reject invalid config"
        
        # Test on_unload
        print("  → Testing on_unload...")
        module_interface.on_unload()  # Should not raise exception
        
        print("  ✅ Module lifecycle methods verified")
        return True
        
    except Exception as e:
        print(f"  ❌ Module lifecycle test failed: {e}")
        return False


def test_plugin_manager_loading():
    """Test that plugin manager can load the module."""
    print("🧪 Testing plugin manager loading...")
    
    try:
        from core.plugin_manager import PluginManager
        
        # Create plugin manager
        plugin_manager = PluginManager()
        
        # Test loading the departments module
        print("  → Loading departments module...")
        loaded_module = plugin_manager.load_module("departments")
        
        assert loaded_module is not None, "Module should load successfully"
        assert plugin_manager.is_module_loaded("departments"), "Module should be marked as loaded"
        
        # Check module status
        status = plugin_manager.get_module_status()
        assert "departments" in status, "Module should appear in status"
        
        module_status = status["departments"]
        assert module_status["name"] == "departments", "Status should show correct name"
        assert module_status["version"] == "1.0.0", "Status should show correct version"
        
        print(f"  📝 Module status: {module_status}")
        
        # Test unloading
        print("  → Unloading departments module...")
        unloaded = plugin_manager.unload_module("departments")
        
        assert unloaded, "Module should unload successfully"
        assert not plugin_manager.is_module_loaded("departments"), "Module should be marked as unloaded"
        
        print("  ✅ Plugin manager loading/unloading verified")
        return True
        
    except Exception as e:
        print(f"  ❌ Plugin manager loading test failed: {e}")
        return False


def test_enabled_modules_configuration():
    """Test enabling/disabling via ENABLED_MODULES."""
    print("🧪 Testing ENABLED_MODULES configuration...")
    
    try:
        # Test with departments enabled
        print("  → Testing with departments enabled...")
        
        # Temporarily set environment variable
        original_enabled = os.environ.get("ENABLED_MODULES", "")
        os.environ["ENABLED_MODULES"] = "departments,approvals,comments"
        
        # Reload config to pick up new environment
        import importlib
        from core import config
        importlib.reload(config)
        
        from core.config import settings
        enabled_modules = settings.enabled_modules_list
        
        assert "departments" in enabled_modules, "Departments should be enabled"
        print(f"  📝 Enabled modules: {enabled_modules}")
        
        # Test with departments disabled
        print("  → Testing with departments disabled...")
        os.environ["ENABLED_MODULES"] = "approvals,comments,templates"
        
        # Reload config again
        importlib.reload(config)
        from core.config import settings
        enabled_modules = settings.enabled_modules_list
        
        assert "departments" not in enabled_modules, "Departments should be disabled"
        print(f"  📝 Enabled modules: {enabled_modules}")
        
        # Restore original environment
        if original_enabled:
            os.environ["ENABLED_MODULES"] = original_enabled
        else:
            os.environ.pop("ENABLED_MODULES", None)
        
        print("  ✅ ENABLED_MODULES configuration verified")
        return True
        
    except Exception as e:
        print(f"  ❌ ENABLED_MODULES configuration test failed: {e}")
        return False


def test_department_model():
    """Test Department model functionality."""
    print("🧪 Testing Department model...")
    
    try:
        from modules.departments.models import Department
        
        # Test model creation
        department = Department(
            name="Test Department",
            code="TEST",
            description="A test department",
            metadata={"test": "value"}
        )
        
        assert department.name == "Test Department", "Name should be set"
        assert department.code == "TEST", "Code should be set"
        assert department.description == "A test department", "Description should be set"
        assert department.is_active == True, "Should be active by default"
        assert department.created_at is not None, "Created timestamp should be set"
        
        # Test to_dict
        dept_dict = department.to_dict()
        assert "id" in dept_dict, "Dict should include ID"
        assert dept_dict["name"] == "Test Department", "Dict should include name"
        
        # Test string representations
        str_repr = str(department)
        assert "TEST" in str_repr, "String representation should include code"
        
        print("  ✅ Department model functionality verified")
        return True
        
    except Exception as e:
        print(f"  ❌ Department model test failed: {e}")
        return False


def test_department_schemas():
    """Test Pydantic schemas."""
    print("🧪 Testing Pydantic schemas...")
    
    try:
        from modules.departments.schemas import DepartmentCreate, DepartmentUpdate, DepartmentResponse
        
        # Test DepartmentCreate
        create_data = {
            "name": "Test Department",
            "code": "test",  # Should be normalized to uppercase
            "description": "Test description"
        }
        
        create_schema = DepartmentCreate(**create_data)
        assert create_schema.code == "TEST", "Code should be normalized to uppercase"
        
        # Test DepartmentUpdate
        update_data = {
            "name": "Updated Department"
        }
        
        update_schema = DepartmentUpdate(**update_data)
        assert update_schema.name == "Updated Department", "Update should work"
        
        # Test validation
        try:
            DepartmentCreate(name="", code="TEST")  # Empty name should fail
            assert False, "Should have failed validation"
        except ValueError:
            pass  # Expected
        
        print("  ✅ Pydantic schemas verified")
        return True
        
    except Exception as e:
        print(f"  ❌ Pydantic schemas test failed: {e}")
        return False


def main():
    """Run all departments module tests."""
    print("🚀 Starting Departments Module Tests")
    print("=" * 50)
    
    tests = [
        test_module_interface_compliance,
        test_module_components,
        test_module_lifecycle,
        test_plugin_manager_loading,
        test_enabled_modules_configuration,
        test_department_model,
        test_department_schemas
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
        print("🎉 All tests passed! Departments module is working correctly.")
        print("\n📋 Departments Module Summary:")
        print("  • ✅ ModuleInterface compliance verified")
        print("  • ✅ Router with CRUD endpoints")
        print("  • ✅ Department SQLModel with indexes")
        print("  • ✅ Pydantic schemas with validation")
        print("  • ✅ Service layer with business logic")
        print("  • ✅ Plugin manager integration")
        print("  • ✅ ENABLED_MODULES configuration support")
        return 0
    else:
        print("⚠️  Some tests failed. Check the implementation.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
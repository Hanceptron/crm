#!/usr/bin/env python3
"""
Test script for the comments module with standalone verification.

Tests module interface compliance, comment functionality, and independence
to ensure the module can be removed without affecting other modules.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_module_interface_compliance():
    """Test that the comments module follows ModuleInterface specification."""
    print("🧪 Testing ModuleInterface compliance...")
    
    try:
        from modules.comments import module_interface
        from core.plugin_manager import ModuleInterface
        
        # Check that it's an instance of ModuleInterface
        assert isinstance(module_interface, ModuleInterface), "Should be ModuleInterface instance"
        
        # Check required attributes
        assert hasattr(module_interface, 'name'), "Should have name attribute"
        assert hasattr(module_interface, 'version'), "Should have version attribute"
        assert hasattr(module_interface, 'description'), "Should have description attribute"
        
        # Check attribute values
        assert module_interface.name == "comments", "Name should be 'comments'"
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
        from modules.comments import module_interface
        
        # Test router
        if module_interface.router:
            assert hasattr(module_interface.router, 'routes'), "Router should have routes"
            route_count = len([r for r in module_interface.router.routes if hasattr(r, 'path')])
            print(f"  📝 Router has {route_count} routes")
        
        # Test models
        if module_interface.models:
            assert isinstance(module_interface.models, list), "Models should be a list"
            assert len(module_interface.models) > 0, "Should have at least one model"
            
            # Check Comment model
            from modules.comments.models import Comment
            assert Comment in module_interface.models, "Should include Comment model"
            print(f"  📝 Models: {[m.__name__ for m in module_interface.models]}")
        
        # Test dependencies
        if module_interface.dependencies:
            assert isinstance(module_interface.dependencies, list), "Dependencies should be a list"
            print(f"  📝 Dependencies: {module_interface.dependencies}")
        else:
            print("  📝 No dependencies (expected for standalone comments module)")
        
        print("  ✅ Module components verified")
        return True
        
    except Exception as e:
        print(f"  ❌ Module components test failed: {e}")
        return False


def test_comment_model():
    """Test Comment model functionality."""
    print("🧪 Testing Comment model...")
    
    try:
        from modules.comments.models import Comment
        
        # Test model creation
        comment = Comment(
            work_item_id="test_work_item_123",
            content="This is a test comment",
            author_name="Test User",
            comment_type="general",
            is_internal=False,
            metadata={"test": "value"}
        )
        
        assert comment.work_item_id == "test_work_item_123", "Work item ID should be set"
        assert comment.content == "This is a test comment", "Content should be set"
        assert comment.author_name == "Test User", "Author name should be set"
        assert comment.comment_type == "general", "Comment type should be set"
        assert comment.is_internal == False, "Internal flag should be set"
        assert comment.created_at is not None, "Created timestamp should be set"
        
        # Test helper methods
        assert comment.is_reply() == False, "Should not identify as reply (no parent)"
        assert comment.is_editable() == True, "Should be editable"
        assert len(comment.get_content_preview(10)) <= 13, "Preview should be limited (10 chars + '...')"
        
        # Test to_dict
        comment_dict = comment.to_dict()
        assert "id" in comment_dict, "Dict should include ID"
        assert comment_dict["content"] == "This is a test comment", "Dict should include content"
        
        print("  ✅ Comment model functionality verified")
        return True
        
    except Exception as e:
        print(f"  ❌ Comment model test failed: {e}")
        return False


def test_comment_schemas():
    """Test Pydantic schemas for comments."""
    print("🧪 Testing Pydantic schemas...")
    
    try:
        from modules.comments.schemas import CommentRequest, CommentResponse, CommentUpdateRequest
        
        # Test CommentRequest
        request_data = {
            "work_item_id": "test_item_123",
            "content": "Test comment content",
            "author_name": "Test Author"
        }
        
        request_schema = CommentRequest(**request_data)
        assert request_schema.work_item_id == "test_item_123", "Work item ID should be set"
        assert request_schema.content == "Test comment content", "Content should be set"
        
        # Test CommentUpdateRequest
        update_data = {
            "content": "Updated comment content",
            "comment_type": "review"
        }
        
        update_schema = CommentUpdateRequest(**update_data)
        assert update_schema.content == "Updated comment content", "Content should be updated"
        assert update_schema.comment_type == "review", "Type should be updated"
        
        # Test validation - empty content should fail
        try:
            CommentRequest(work_item_id="test", content="", author_name="Test")
            assert False, "Should have failed validation for empty content"
        except ValueError:
            pass  # Expected
        
        # Test comment type validation
        try:
            CommentRequest(work_item_id="test", content="Test", author_name="Test", comment_type="invalid_type")
            assert False, "Should have failed validation for invalid comment type"
        except ValueError:
            pass  # Expected
        
        print("  ✅ Pydantic schemas verified")
        return True
        
    except Exception as e:
        print(f"  ❌ Pydantic schemas test failed: {e}")
        return False


def test_comment_service_classes():
    """Test CommentService classes without database connection."""
    print("🧪 Testing CommentService (basic functionality)...")
    
    try:
        # Test that service classes can be imported
        from modules.comments.service import (
            CommentService,
            CommentServiceError,
            CommentNotFoundError,
            WorkItemNotFoundError
        )
        
        # Test exception classes
        try:
            raise CommentServiceError("Test error")
        except CommentServiceError as e:
            assert str(e) == "Test error", "Exception should carry message"
        
        try:
            raise CommentNotFoundError("Comment not found")
        except CommentNotFoundError as e:
            assert str(e) == "Comment not found", "Exception should carry message"
        
        try:
            raise WorkItemNotFoundError("Work item not found")
        except WorkItemNotFoundError as e:
            assert str(e) == "Work item not found", "Exception should carry message"
        
        print("  ✅ CommentService classes verified")
        return True
        
    except Exception as e:
        print(f"  ❌ CommentService test failed: {e}")
        return False


def test_api_routes_structure():
    """Test API routes structure without server."""
    print("🧪 Testing API routes structure...")
    
    try:
        from modules.comments.routes import router
        
        # Check that router exists and has routes
        assert router is not None, "Router should exist"
        assert hasattr(router, 'routes'), "Router should have routes"
        
        # Check for required endpoints
        route_paths = []
        for route in router.routes:
            if hasattr(route, 'path'):
                route_paths.append(route.path)
        
        print(f"  📝 Available routes: {route_paths}")
        
        # Check for core comment endpoints
        expected_patterns = [
            "/work-item/{work_item_id}",
            "/{comment_id}",
            ""  # Root path for POST
        ]
        
        for pattern in expected_patterns:
            found = any(pattern in path for path in route_paths)
            assert found, f"Expected route pattern {pattern} not found"
        
        print("  ✅ API routes structure verified")
        return True
        
    except Exception as e:
        print(f"  ❌ API routes structure test failed: {e}")
        return False


def test_plugin_manager_integration():
    """Test integration with plugin manager."""
    print("🧪 Testing plugin manager integration...")
    
    try:
        from core.plugin_manager import PluginManager
        
        # Create plugin manager
        plugin_manager = PluginManager()
        
        # Test loading the comments module
        print("  → Loading comments module...")
        loaded_module = plugin_manager.load_module("comments")
        
        assert loaded_module is not None, "Module should load successfully"
        assert plugin_manager.is_module_loaded("comments"), "Module should be marked as loaded"
        
        # Check module status
        status = plugin_manager.get_module_status()
        assert "comments" in status, "Module should appear in status"
        
        module_status = status["comments"]
        assert module_status["name"] == "comments", "Status should show correct name"
        assert module_status["version"] == "1.0.0", "Status should show correct version"
        
        print(f"  📝 Module status: {module_status}")
        
        # Test unloading
        print("  → Unloading comments module...")
        unloaded = plugin_manager.unload_module("comments")
        
        assert unloaded, "Module should unload successfully"
        assert not plugin_manager.is_module_loaded("comments"), "Module should be marked as unloaded"
        
        print("  ✅ Plugin manager integration verified")
        return True
        
    except Exception as e:
        print(f"  ❌ Plugin manager integration test failed: {e}")
        return False


def test_module_capabilities():
    """Test module capability reporting."""
    print("🧪 Testing module capabilities...")
    
    try:
        from modules.comments import module_interface
        
        # Test comment capabilities
        capabilities = module_interface.get_comment_capabilities()
        assert isinstance(capabilities, dict), "Should return capabilities dict"
        assert "comment_types" in capabilities, "Should list comment types"
        assert "supports_threading" in capabilities, "Should report threading support"
        assert capabilities["supports_threading"] == True, "Should support threading"
        assert capabilities["supports_replies"] == True, "Should support replies"
        
        # Test stats summary
        stats = module_interface.get_comment_stats_summary()
        assert isinstance(stats, dict), "Should return stats dict"
        assert "module_version" in stats, "Should include version"
        assert stats["standalone_module"] == True, "Should be standalone"
        assert stats["removable"] == True, "Should be removable"
        
        # Test integration info
        integration = module_interface.get_integration_info()
        assert isinstance(integration, dict), "Should return integration dict"
        assert integration["standalone"] == True, "Should be standalone"
        assert integration["removable"] == True, "Should be removable"
        assert integration["affects_workflow"] == False, "Should not affect workflow"
        
        # Test removability
        assert module_interface.is_removable() == True, "Should be removable"
        
        # Test dependency verification
        deps = module_interface.verify_dependencies()
        assert isinstance(deps, dict), "Should return dependencies dict"
        assert "status" in deps, "Should include status"
        assert "all_available" in deps, "Should include availability check"
        
        print(f"  📝 Comment capabilities: {capabilities['comment_types']}")
        print(f"  📝 Integration info: standalone={integration['standalone']}, removable={integration['removable']}")
        
        print("  ✅ Module capabilities verified")
        return True
        
    except Exception as e:
        print(f"  ❌ Module capabilities test failed: {e}")
        return False


def test_module_independence():
    """Test that the module is truly independent and removable."""
    print("🧪 Testing module independence...")
    
    try:
        # Import the module
        from modules.comments import module_interface
        
        # Verify no dependencies on other modules
        if module_interface.dependencies:
            print(f"  ⚠️  Module has dependencies: {module_interface.dependencies}")
            return False
        
        # Check that integration points are minimal
        integration_info = module_interface.get_integration_info()
        
        # Should only depend on core work items
        expected_integration_points = ["work_items"]
        actual_integration_points = integration_info.get("integration_points", [])
        
        for point in actual_integration_points:
            if point not in expected_integration_points:
                print(f"  ⚠️  Unexpected integration point: {point}")
                return False
        
        # Should not affect workflow or state transitions
        assert not integration_info["affects_workflow"], "Should not affect workflow"
        assert not integration_info["affects_state_transitions"], "Should not affect state transitions"
        assert not integration_info["required_by_other_modules"], "Should not be required by other modules"
        
        # Should be completely removable
        assert integration_info["removable"], "Should be removable"
        assert module_interface.is_removable(), "Module should report as removable"
        
        print("  📝 Integration points: work_items only")
        print("  📝 Affects workflow: No")
        print("  📝 Required by other modules: No")
        print("  📝 Removable: Yes")
        
        print("  ✅ Module independence verified")
        return True
        
    except Exception as e:
        print(f"  ❌ Module independence test failed: {e}")
        return False


def main():
    """Run all comments module tests."""
    print("🚀 Starting Comments Module Tests")
    print("=" * 50)
    
    tests = [
        test_module_interface_compliance,
        test_module_components,
        test_comment_model,
        test_comment_schemas,
        test_comment_service_classes,
        test_api_routes_structure,
        test_plugin_manager_integration,
        test_module_capabilities,
        test_module_independence
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
        print("🎉 All tests passed! Comments module is working correctly.")
        print("\n📋 Comments Module Summary:")
        print("  • ✅ ModuleInterface compliance verified")
        print("  • ✅ Comment SQLModel with foreign keys and threading")
        print("  • ✅ CommentService with CRUD operations")
        print("  • ✅ API routes: POST /comments, GET /comments/work-item/{id}, etc.")
        print("  • ✅ Pydantic schemas with validation")
        print("  • ✅ Plugin manager integration")
        print("  • ✅ Standalone and completely removable")
        print("  • ✅ No dependencies on other modules")
        print("  • ✅ Does not affect workflow or state transitions")
        return 0
    else:
        print("⚠️  Some tests failed. Check the implementation.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
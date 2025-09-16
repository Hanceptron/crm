#!/usr/bin/env python3
"""
Test script for the Aviation Workflow System's Burr integration.

Tests workflow creation, state transitions, and validation to ensure
the workflow engine is working correctly.
"""

import os
import sys
import tempfile
import shutil
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.workflow_engine import WorkflowEngine, WorkflowEngineError
from workflows.sequential_approval import build_approval_workflow, get_workflow_status_info
from burr.tracking import LocalTrackingClient


def test_basic_workflow_creation():
    """Test basic workflow creation and initialization."""
    print("🧪 Testing basic workflow creation...")
    
    # Create temporary directory for testing
    temp_dir = tempfile.mkdtemp()
    
    try:
        engine = WorkflowEngine()
        
        # Test creating a workflow
        department_sequence = ["engineering", "quality_control", "operations"]
        workflow_id = "test_workflow_001"
        
        app = engine.create_workflow(
            template="sequential_approval",
            workflow_id=workflow_id,
            department_sequence=department_sequence
        )
        
        # Verify workflow was created
        assert engine.workflow_exists(workflow_id), "Workflow should exist"
        
        # Check initial state
        state = engine.get_workflow_state(workflow_id)
        assert state is not None, "State should not be None"
        assert state["current_step"] == 0, "Should start at step 0"
        assert state["status"] == "active", "Should be active"
        assert state["department_sequence"] == department_sequence, "Department sequence should match"
        
        print("✅ Basic workflow creation test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Basic workflow creation test failed: {e}")
        return False
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_workflow_transitions():
    """Test workflow state transitions."""
    print("🧪 Testing workflow state transitions...")
    
    try:
        engine = WorkflowEngine()
        
        department_sequence = ["dept1", "dept2", "dept3"]
        workflow_id = "test_transitions_001"
        
        # Create workflow
        app = engine.create_workflow(
            template="sequential_approval",
            workflow_id=workflow_id,
            department_sequence=department_sequence
        )
        
        # Test approval transition
        print("  → Testing approval transition...")
        new_state = engine.execute_transition(
            workflow_id=workflow_id,
            action="approve",
            context={"comment": "Looks good!"}
        )
        
        assert new_state["current_step"] == 1, "Should advance to step 1"
        assert new_state["status"] == "active", "Should still be active"
        assert len(new_state["history"]) == 1, "Should have one history entry"
        
        # Test another approval
        print("  → Testing second approval...")
        new_state = engine.execute_transition(
            workflow_id=workflow_id,
            action="approve",
            context={"comment": "Approved by QC"}
        )
        
        assert new_state["current_step"] == 2, "Should advance to step 2"
        assert new_state["status"] == "active", "Should still be active"
        
        # Test final approval (should complete workflow)
        print("  → Testing final approval...")
        new_state = engine.execute_transition(
            workflow_id=workflow_id,
            action="approve",
            context={"comment": "Final approval"}
        )
        
        assert new_state["current_step"] == 2, "Should stay at final step"
        assert new_state["status"] == "completed", "Should be completed"
        
        print("✅ Workflow transitions test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Workflow transitions test failed: {e}")
        return False


def test_rejection_flow():
    """Test workflow rejection and backward transitions."""
    print("🧪 Testing workflow rejection flow...")
    
    try:
        engine = WorkflowEngine()
        
        department_sequence = ["dept1", "dept2", "dept3"]
        workflow_id = "test_rejection_001"
        
        # Create workflow and advance to step 2
        app = engine.create_workflow(
            template="sequential_approval",
            workflow_id=workflow_id,
            department_sequence=department_sequence
        )
        
        # Advance to step 2
        engine.execute_transition(workflow_id, "approve", {"comment": "Step 1 approved"})
        engine.execute_transition(workflow_id, "approve", {"comment": "Step 2 approved"})
        
        state = engine.get_workflow_state(workflow_id)
        assert state["current_step"] == 2, "Should be at step 2"
        
        # Test rejection back to step 0
        print("  → Testing rejection to step 0...")
        new_state = engine.execute_transition(
            workflow_id=workflow_id,
            action="reject",
            context={"target_step": 0, "comment": "Needs major revisions"}
        )
        
        assert new_state["current_step"] == 0, "Should be back to step 0"
        assert new_state["status"] == "active", "Should be active for rework"
        
        history = new_state["history"]
        assert len(history) == 3, "Should have 3 history entries"
        assert history[-1]["action"] == "rejected", "Last action should be rejection"
        
        print("✅ Rejection flow test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Rejection flow test failed: {e}")
        return False


def test_cancellation():
    """Test workflow cancellation."""
    print("🧪 Testing workflow cancellation...")
    
    try:
        engine = WorkflowEngine()
        
        department_sequence = ["dept1", "dept2"]
        workflow_id = "test_cancel_001"
        
        # Create workflow
        app = engine.create_workflow(
            template="sequential_approval",
            workflow_id=workflow_id,
            department_sequence=department_sequence
        )
        
        # Test cancellation
        print("  → Testing cancel action...")
        new_state = engine.execute_transition(
            workflow_id=workflow_id,
            action="cancel",
            context={"reason": "Project cancelled"}
        )
        
        assert new_state["status"] == "cancelled", "Should be cancelled"
        
        history = new_state["history"]
        assert len(history) == 1, "Should have one history entry"
        assert history[0]["action"] == "cancelled", "Should be cancellation action"
        
        print("✅ Cancellation test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Cancellation test failed: {e}")
        return False


def test_error_handling():
    """Test error handling for invalid operations."""
    print("🧪 Testing error handling...")
    
    try:
        engine = WorkflowEngine()
        
        # Test invalid workflow template
        try:
            engine.create_workflow(
                template="nonexistent_template",
                workflow_id="test_error",
                department_sequence=["dept1"]
            )
            assert False, "Should have raised WorkflowEngineError"
        except WorkflowEngineError:
            print("  ✅ Invalid template error handling works")
        
        # Test invalid workflow ID for transition
        try:
            engine.execute_transition("nonexistent_workflow", "approve")
            assert False, "Should have raised WorkflowNotFoundError"
        except WorkflowEngineError:
            print("  ✅ Invalid workflow ID error handling works")
        
        print("✅ Error handling test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        return False


def test_workflow_status_info():
    """Test workflow status information retrieval."""
    print("🧪 Testing workflow status information...")
    
    try:
        engine = WorkflowEngine()
        
        department_sequence = ["engineering", "quality", "operations"]
        workflow_id = "test_status_001"
        
        # Create workflow
        app = engine.create_workflow(
            template="sequential_approval",
            workflow_id=workflow_id,
            department_sequence=department_sequence
        )
        
        # Get initial status
        state = engine.get_workflow_state(workflow_id)
        status_info = get_workflow_status_info(state)
        
        assert status_info["status"] == "active", "Should be active"
        assert status_info["current_step"] == 0, "Should be at step 0"
        assert status_info["current_department"] == "engineering", "Should be at engineering"
        assert status_info["next_department"] == "quality", "Next should be quality"
        assert status_info["is_final_step"] == False, "Should not be final step"
        assert status_info["progress_percentage"] == 0, "Should be 0% progress"
        
        # Advance one step
        engine.execute_transition(workflow_id, "approve", {"comment": "Engineering approved"})
        
        state = engine.get_workflow_state(workflow_id)
        status_info = get_workflow_status_info(state)
        
        assert status_info["current_step"] == 1, "Should be at step 1"
        assert status_info["current_department"] == "quality", "Should be at quality"
        assert status_info["progress_percentage"] > 0, "Should have some progress"
        
        print("✅ Workflow status information test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Workflow status information test failed: {e}")
        return False


def main():
    """Run all workflow tests."""
    print("🚀 Starting Aviation Workflow System Tests")
    print("=" * 50)
    
    tests = [
        test_basic_workflow_creation,
        test_workflow_transitions, 
        test_rejection_flow,
        test_cancellation,
        test_error_handling,
        test_workflow_status_info
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
        print("🎉 All tests passed! Workflow engine is working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Check the implementation.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
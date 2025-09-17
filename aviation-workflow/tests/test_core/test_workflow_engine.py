"""
Tests for the Workflow Engine module.

Tests workflow creation, state transitions, persistence, and error handling
to ensure the Burr-based workflow engine functions correctly.
"""

import pytest
from datetime import datetime, timedelta
from typing import Dict, Any, List
from unittest.mock import Mock, patch, MagicMock

from core.workflow_engine import WorkflowEngine, WorkflowError, WorkflowNotFoundError
from core.models import WorkItem


@pytest.mark.workflow
class TestWorkflowEngine:
    """Test suite for WorkflowEngine functionality."""
    
    def test_workflow_engine_initialization(self, test_workflow_engine):
        """Test that WorkflowEngine initializes correctly."""
        assert test_workflow_engine is not None
        assert hasattr(test_workflow_engine, 'create_workflow')
        assert hasattr(test_workflow_engine, 'get_workflow')
        assert hasattr(test_workflow_engine, 'execute_action')
    
    def test_create_workflow_success(self, test_workflow_engine, sample_work_item):
        """Test successful workflow creation."""
        workflow_id = sample_work_item.id
        department_sequence = ["dept_1", "dept_2", "dept_3"]
        
        # Create workflow
        workflow = test_workflow_engine.create_workflow(
            workflow_id=workflow_id,
            department_sequence=department_sequence,
            initial_data={
                "title": sample_work_item.title,
                "priority": sample_work_item.priority
            }
        )
        
        assert workflow is not None
        assert workflow.workflow_id == workflow_id
        
        # Verify initial state
        state = test_workflow_engine.get_current_state(workflow_id)
        assert state["current_step"] == 0
        assert state["department_sequence"] == department_sequence
        assert state["status"] == "pending"
    
    def test_create_workflow_with_invalid_department_sequence(self, test_workflow_engine):
        """Test workflow creation with invalid department sequence."""
        with pytest.raises(WorkflowError, match="Department sequence cannot be empty"):
            test_workflow_engine.create_workflow(
                workflow_id="test-workflow",
                department_sequence=[],  # Empty sequence
                initial_data={}
            )
    
    def test_create_workflow_duplicate_id(self, test_workflow_engine, sample_work_item):
        """Test creating workflow with duplicate ID should raise error."""
        workflow_id = sample_work_item.id
        department_sequence = ["dept_1", "dept_2"]
        
        # Create first workflow
        test_workflow_engine.create_workflow(
            workflow_id=workflow_id,
            department_sequence=department_sequence,
            initial_data={}
        )
        
        # Attempt to create duplicate
        with pytest.raises(WorkflowError, match="Workflow already exists"):
            test_workflow_engine.create_workflow(
                workflow_id=workflow_id,
                department_sequence=department_sequence,
                initial_data={}
            )
    
    def test_get_workflow_success(self, test_workflow_engine, sample_work_item):
        """Test successful workflow retrieval."""
        workflow_id = sample_work_item.id
        department_sequence = ["dept_1", "dept_2"]
        
        # Create workflow first
        original_workflow = test_workflow_engine.create_workflow(
            workflow_id=workflow_id,
            department_sequence=department_sequence,
            initial_data={}
        )
        
        # Retrieve workflow
        retrieved_workflow = test_workflow_engine.get_workflow(workflow_id)
        
        assert retrieved_workflow is not None
        assert retrieved_workflow.workflow_id == original_workflow.workflow_id
    
    def test_get_workflow_not_found(self, test_workflow_engine):
        """Test retrieving non-existent workflow."""
        with pytest.raises(WorkflowNotFoundError, match="Workflow not found"):
            test_workflow_engine.get_workflow("non-existent-workflow")
    
    def test_execute_approve_action(self, test_workflow_engine, sample_work_item):
        """Test executing approve action advances workflow."""
        workflow_id = sample_work_item.id
        department_sequence = ["dept_1", "dept_2", "dept_3"]
        
        # Create workflow
        test_workflow_engine.create_workflow(
            workflow_id=workflow_id,
            department_sequence=department_sequence,
            initial_data={}
        )
        
        # Execute approve action
        result = test_workflow_engine.execute_action(
            workflow_id=workflow_id,
            action="approve",
            context={
                "approved_by": "test@aviation.com",
                "comment": "Approved for testing",
                "department": "dept_1"
            }
        )
        
        assert result["success"] is True
        
        # Verify state change
        state = test_workflow_engine.get_current_state(workflow_id)
        assert state["current_step"] == 1  # Advanced to next step
        assert state["status"] == "in_progress"
        
        # Verify history
        assert len(state["history"]) == 1
        history_entry = state["history"][0]
        assert history_entry["action"] == "approve"
        assert history_entry["approved_by"] == "test@aviation.com"
        assert history_entry["comment"] == "Approved for testing"
    
    def test_execute_reject_action(self, test_workflow_engine, sample_work_item):
        """Test executing reject action moves workflow backward."""
        workflow_id = sample_work_item.id
        department_sequence = ["dept_1", "dept_2", "dept_3"]
        
        # Create workflow and advance to step 1
        test_workflow_engine.create_workflow(
            workflow_id=workflow_id,
            department_sequence=department_sequence,
            initial_data={}
        )
        
        # First approve to advance
        test_workflow_engine.execute_action(
            workflow_id=workflow_id,
            action="approve",
            context={"approved_by": "test@aviation.com"}
        )
        
        # Now reject
        result = test_workflow_engine.execute_action(
            workflow_id=workflow_id,
            action="reject",
            context={
                "rejected_by": "test2@aviation.com",
                "reason": "Insufficient documentation",
                "return_to_step": 0
            }
        )
        
        assert result["success"] is True
        
        # Verify state change
        state = test_workflow_engine.get_current_state(workflow_id)
        assert state["current_step"] == 0  # Returned to previous step
        assert state["status"] == "rejected"
        
        # Verify history
        assert len(state["history"]) == 2  # Approve + Reject
        reject_entry = state["history"][1]
        assert reject_entry["action"] == "reject"
        assert reject_entry["reason"] == "Insufficient documentation"
    
    def test_execute_complete_workflow(self, test_workflow_engine, sample_work_item):
        """Test completing entire workflow through all steps."""
        workflow_id = sample_work_item.id
        department_sequence = ["dept_1", "dept_2"]
        
        # Create workflow
        test_workflow_engine.create_workflow(
            workflow_id=workflow_id,
            department_sequence=department_sequence,
            initial_data={}
        )
        
        # Approve through all steps
        for i, dept in enumerate(department_sequence):
            result = test_workflow_engine.execute_action(
                workflow_id=workflow_id,
                action="approve",
                context={
                    "approved_by": f"approver_{i}@aviation.com",
                    "department": dept
                }
            )
            assert result["success"] is True
        
        # Verify final state
        state = test_workflow_engine.get_current_state(workflow_id)
        assert state["status"] == "completed"
        assert state["current_step"] == len(department_sequence)
        assert len(state["history"]) == len(department_sequence)
    
    def test_execute_invalid_action(self, test_workflow_engine, sample_work_item):
        """Test executing invalid action raises error."""
        workflow_id = sample_work_item.id
        department_sequence = ["dept_1", "dept_2"]
        
        # Create workflow
        test_workflow_engine.create_workflow(
            workflow_id=workflow_id,
            department_sequence=department_sequence,
            initial_data={}
        )
        
        # Execute invalid action
        with pytest.raises(WorkflowError, match="Invalid action"):
            test_workflow_engine.execute_action(
                workflow_id=workflow_id,
                action="invalid_action",
                context={}
            )
    
    def test_execute_action_on_completed_workflow(self, test_workflow_engine, sample_work_item):
        """Test that actions on completed workflow are rejected."""
        workflow_id = sample_work_item.id
        department_sequence = ["dept_1"]
        
        # Create and complete workflow
        test_workflow_engine.create_workflow(
            workflow_id=workflow_id,
            department_sequence=department_sequence,
            initial_data={}
        )
        
        test_workflow_engine.execute_action(
            workflow_id=workflow_id,
            action="approve",
            context={"approved_by": "test@aviation.com"}
        )
        
        # Verify workflow is completed
        state = test_workflow_engine.get_current_state(workflow_id)
        assert state["status"] == "completed"
        
        # Attempt another action
        with pytest.raises(WorkflowError, match="Cannot modify completed workflow"):
            test_workflow_engine.execute_action(
                workflow_id=workflow_id,
                action="approve",
                context={"approved_by": "test@aviation.com"}
            )
    
    def test_get_available_actions_pending(self, test_workflow_engine, sample_work_item):
        """Test getting available actions for pending workflow."""
        workflow_id = sample_work_item.id
        department_sequence = ["dept_1", "dept_2"]
        
        # Create workflow
        test_workflow_engine.create_workflow(
            workflow_id=workflow_id,
            department_sequence=department_sequence,
            initial_data={}
        )
        
        # Get available actions
        actions = test_workflow_engine.get_available_actions(workflow_id)
        
        assert "approve" in actions
        assert "reject" in actions
        assert "request_info" in actions
    
    def test_get_available_actions_completed(self, test_workflow_engine, sample_work_item):
        """Test getting available actions for completed workflow."""
        workflow_id = sample_work_item.id
        department_sequence = ["dept_1"]
        
        # Create and complete workflow
        test_workflow_engine.create_workflow(
            workflow_id=workflow_id,
            department_sequence=department_sequence,
            initial_data={}
        )
        
        test_workflow_engine.execute_action(
            workflow_id=workflow_id,
            action="approve",
            context={"approved_by": "test@aviation.com"}
        )
        
        # Get available actions
        actions = test_workflow_engine.get_available_actions(workflow_id)
        
        assert len(actions) == 0  # No actions available for completed workflow
    
    def test_workflow_state_persistence(self, test_workflow_engine, sample_work_item):
        """Test that workflow state persists correctly."""
        workflow_id = sample_work_item.id
        department_sequence = ["dept_1", "dept_2"]
        
        # Create workflow and execute action
        test_workflow_engine.create_workflow(
            workflow_id=workflow_id,
            department_sequence=department_sequence,
            initial_data={"test_data": "value"}
        )
        
        test_workflow_engine.execute_action(
            workflow_id=workflow_id,
            action="approve",
            context={
                "approved_by": "test@aviation.com",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
        # Get state
        state = test_workflow_engine.get_current_state(workflow_id)
        
        # Verify state persistence
        assert state["current_step"] == 1
        assert state["test_data"] == "value"
        assert len(state["history"]) == 1
        assert state["history"][0]["approved_by"] == "test@aviation.com"
    
    def test_workflow_rollback(self, test_workflow_engine, sample_work_item):
        """Test workflow rollback functionality."""
        workflow_id = sample_work_item.id
        department_sequence = ["dept_1", "dept_2", "dept_3"]
        
        # Create workflow and advance multiple steps
        test_workflow_engine.create_workflow(
            workflow_id=workflow_id,
            department_sequence=department_sequence,
            initial_data={}
        )
        
        # Advance to step 2
        test_workflow_engine.execute_action(
            workflow_id=workflow_id,
            action="approve",
            context={"approved_by": "test1@aviation.com"}
        )
        
        test_workflow_engine.execute_action(
            workflow_id=workflow_id,
            action="approve",
            context={"approved_by": "test2@aviation.com"}
        )
        
        # Verify at step 2
        state = test_workflow_engine.get_current_state(workflow_id)
        assert state["current_step"] == 2
        
        # Rollback to step 0
        result = test_workflow_engine.rollback_to_step(workflow_id, 0)
        assert result["success"] is True
        
        # Verify rollback
        state = test_workflow_engine.get_current_state(workflow_id)
        assert state["current_step"] == 0
        assert state["status"] == "pending"
        
        # Verify rollback is recorded in history
        rollback_entries = [h for h in state["history"] if h.get("action") == "rollback"]
        assert len(rollback_entries) == 1
    
    def test_workflow_metadata_tracking(self, test_workflow_engine, sample_work_item):
        """Test that workflow metadata is tracked correctly."""
        workflow_id = sample_work_item.id
        department_sequence = ["dept_1", "dept_2"]
        
        initial_metadata = {
            "priority": "high",
            "aircraft_tail": "N123AB",
            "location": "KORD"
        }
        
        # Create workflow with metadata
        test_workflow_engine.create_workflow(
            workflow_id=workflow_id,
            department_sequence=department_sequence,
            initial_data=initial_metadata
        )
        
        # Execute action with additional metadata
        test_workflow_engine.execute_action(
            workflow_id=workflow_id,
            action="approve",
            context={
                "approved_by": "test@aviation.com",
                "approval_duration": 3600,
                "notes": "Approved after inspection"
            }
        )
        
        # Verify metadata preservation
        state = test_workflow_engine.get_current_state(workflow_id)
        assert state["priority"] == "high"
        assert state["aircraft_tail"] == "N123AB"
        assert state["location"] == "KORD"
        
        # Verify action metadata
        assert state["history"][0]["approval_duration"] == 3600
        assert state["history"][0]["notes"] == "Approved after inspection"
    
    def test_concurrent_workflow_operations(self, test_workflow_engine):
        """Test concurrent operations on different workflows."""
        # Create multiple workflows
        workflows = []
        for i in range(3):
            workflow_id = f"workflow_{i}"
            test_workflow_engine.create_workflow(
                workflow_id=workflow_id,
                department_sequence=["dept_1", "dept_2"],
                initial_data={"index": i}
            )
            workflows.append(workflow_id)
        
        # Execute actions on different workflows
        for i, workflow_id in enumerate(workflows):
            test_workflow_engine.execute_action(
                workflow_id=workflow_id,
                action="approve",
                context={"approved_by": f"test{i}@aviation.com"}
            )
        
        # Verify each workflow state independently
        for i, workflow_id in enumerate(workflows):
            state = test_workflow_engine.get_current_state(workflow_id)
            assert state["current_step"] == 1
            assert state["index"] == i
            assert state["history"][0]["approved_by"] == f"test{i}@aviation.com"


@pytest.mark.workflow
class TestWorkflowEngineErrorHandling:
    """Test error handling in WorkflowEngine."""
    
    def test_invalid_workflow_id(self, test_workflow_engine):
        """Test operations with invalid workflow ID."""
        invalid_id = "invalid-workflow-id"
        
        with pytest.raises(WorkflowNotFoundError):
            test_workflow_engine.get_workflow(invalid_id)
        
        with pytest.raises(WorkflowNotFoundError):
            test_workflow_engine.execute_action(invalid_id, "approve", {})
        
        with pytest.raises(WorkflowNotFoundError):
            test_workflow_engine.get_current_state(invalid_id)
    
    def test_invalid_rollback_step(self, test_workflow_engine, sample_work_item):
        """Test rollback to invalid step."""
        workflow_id = sample_work_item.id
        department_sequence = ["dept_1", "dept_2"]
        
        test_workflow_engine.create_workflow(
            workflow_id=workflow_id,
            department_sequence=department_sequence,
            initial_data={}
        )
        
        # Attempt rollback to invalid step
        with pytest.raises(WorkflowError, match="Invalid step"):
            test_workflow_engine.rollback_to_step(workflow_id, -1)
        
        with pytest.raises(WorkflowError, match="Invalid step"):
            test_workflow_engine.rollback_to_step(workflow_id, 10)
    
    def test_workflow_engine_persistence_failure(self, test_workflow_engine):
        """Test handling of persistence failures."""
        # Mock persistence failure
        with patch.object(test_workflow_engine, '_save_state', side_effect=Exception("Persistence failed")):
            with pytest.raises(WorkflowError, match="Failed to persist workflow state"):
                test_workflow_engine.create_workflow(
                    workflow_id="test-workflow",
                    department_sequence=["dept_1"],
                    initial_data={}
                )


@pytest.mark.workflow
@pytest.mark.integration
class TestWorkflowEngineIntegration:
    """Integration tests for WorkflowEngine with other components."""
    
    def test_workflow_with_work_item_model(self, test_workflow_engine, test_session):
        """Test workflow integration with WorkItem model."""
        # Create work item
        work_item = WorkItem(
            title="Test Integration",
            description="Testing workflow integration",
            priority="medium",
            department_ids=["dept_1", "dept_2"],
            current_step=0,
            status="pending",
            created_by="test@aviation.com"
        )
        
        test_session.add(work_item)
        test_session.commit()
        test_session.refresh(work_item)
        
        # Create corresponding workflow
        workflow = test_workflow_engine.create_workflow(
            workflow_id=work_item.id,
            department_sequence=work_item.department_ids,
            initial_data={
                "title": work_item.title,
                "priority": work_item.priority,
                "work_item_id": work_item.id
            }
        )
        
        # Execute action
        result = test_workflow_engine.execute_action(
            workflow_id=work_item.id,
            action="approve",
            context={"approved_by": "test@aviation.com"}
        )
        
        assert result["success"] is True
        
        # Verify workflow state matches expected work item state
        state = test_workflow_engine.get_current_state(work_item.id)
        assert state["current_step"] == 1
        assert state["work_item_id"] == work_item.id
        assert state["title"] == work_item.title
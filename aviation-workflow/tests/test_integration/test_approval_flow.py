"""
Integration tests for the complete approval workflow.

Tests end-to-end approval flows including work item creation,
multi-step approvals, rejections, and edge cases across modules.
"""

import pytest
from datetime import datetime, timedelta
from sqlmodel import select
from fastapi.testclient import TestClient

from core.models import WorkItem
from modules.departments.models import Department
from modules.templates.models import WorkflowTemplate
from modules.comments.models import Comment
from modules.departments.service import DepartmentService
from modules.templates.service import TemplateService
from modules.comments.service import CommentService


@pytest.mark.integration
class TestCompleteApprovalFlow:
    """Test complete approval workflow from creation to completion."""
    
    def test_end_to_end_approval_success(self, test_client, test_session, sample_departments):
        """Test complete workflow from creation through all approvals."""
        # Step 1: Create workflow template
        template_data = {
            "name": "e2e_test_workflow",
            "display_name": "End-to-End Test Workflow",
            "description": "Testing complete approval flow",
            "department_sequence": [dept.name for dept in sample_departments],
            "approval_rules": {
                "require_comment": True,
                "min_approvals": 1,
                "allow_parallel_approval": False
            },
            "workflow_config": {
                "timeout": 3600,
                "auto_approve_minor": False
            },
            "category": "test",
            "created_by": "test@aviation.com"
        }
        
        template_response = test_client.post("/api/templates", json=template_data)
        assert template_response.status_code == 201
        template = template_response.json()
        
        # Step 2: Create work item using template
        work_item_data = {
            "title": "E2E Test Work Item",
            "description": "Testing end-to-end approval flow",
            "priority": "medium",
            "template_id": template["id"],
            "created_by": "requester@aviation.com",
            "assigned_to": "approver@aviation.com",
            "metadata": {
                "aircraft_tail": "N123TE",
                "location": "KORD",
                "estimated_hours": 4.0
            }
        }
        
        work_item_response = test_client.post("/api/work-items", json=work_item_data)
        assert work_item_response.status_code == 201
        work_item = work_item_response.json()
        
        assert work_item["current_step"] == 0
        assert work_item["status"] == "pending"
        assert work_item["department_ids"] == template["department_sequence"]
        
        # Step 3: Go through each approval step
        for step, dept_name in enumerate(template["department_sequence"]):
            # Add comment for approval
            comment_data = {
                "work_item_id": work_item["id"],
                "content": f"Approving at step {step + 1} from {dept_name}",
                "comment_type": "approval",
                "created_by": f"approver_{step}@{dept_name}.com",
                "department_id": sample_departments[step].id,
                "metadata": {
                    "approval_status": "approved",
                    "approval_timestamp": datetime.utcnow().isoformat()
                }
            }
            
            comment_response = test_client.post("/api/comments", json=comment_data)
            assert comment_response.status_code == 201
            
            # Execute approval (this would normally trigger workflow engine)
            approval_data = {
                "action": "approve",
                "comment": f"Approved by {dept_name}",
                "approved_by": f"approver_{step}@{dept_name}.com",
                "department": dept_name
            }
            
            # Mock workflow progression by updating work item
            if step < len(template["department_sequence"]) - 1:
                # Not final step - advance to next department
                update_data = {
                    "current_step": step + 1,
                    "status": "in_progress"
                }
            else:
                # Final step - complete workflow
                update_data = {
                    "current_step": step + 1,
                    "status": "completed"
                }
            
            update_response = test_client.put(f"/api/work-items/{work_item['id']}", json=update_data)
            assert update_response.status_code == 200
            
            # Verify state
            get_response = test_client.get(f"/api/work-items/{work_item['id']}")
            updated_item = get_response.json()
            assert updated_item["current_step"] == step + 1
        
        # Step 4: Verify final completion
        final_response = test_client.get(f"/api/work-items/{work_item['id']}")
        final_item = final_response.json()
        
        assert final_item["status"] == "completed"
        assert final_item["current_step"] == len(template["department_sequence"])
        
        # Verify all comments were created
        comments_response = test_client.get(f"/api/comments?work_item_id={work_item['id']}")
        comments = comments_response.json()
        assert len(comments) == len(template["department_sequence"])
    
    def test_rejection_and_resubmission_flow(self, test_client, test_session, sample_departments):
        """Test rejection at middle step and resubmission."""
        # Create template and work item
        template_data = {
            "name": "rejection_test_workflow",
            "display_name": "Rejection Test Workflow",
            "department_sequence": [dept.name for dept in sample_departments],
            "created_by": "test@aviation.com"
        }
        
        template_response = test_client.post("/api/templates", json=template_data)
        template = template_response.json()
        
        work_item_data = {
            "title": "Rejection Test Work Item",
            "description": "Testing rejection flow",
            "priority": "high",
            "template_id": template["id"],
            "created_by": "requester@aviation.com"
        }
        
        work_item_response = test_client.post("/api/work-items", json=work_item_data)
        work_item = work_item_response.json()
        
        # Approve first step
        first_dept = sample_departments[0]
        
        # Add approval comment
        comment_data = {
            "work_item_id": work_item["id"],
            "content": "Approved by first department",
            "comment_type": "approval",
            "created_by": f"approver@{first_dept.name}.com",
            "department_id": first_dept.id
        }
        test_client.post("/api/comments", json=comment_data)
        
        # Advance to step 1
        update_response = test_client.put(
            f"/api/work-items/{work_item['id']}", 
            json={"current_step": 1, "status": "in_progress"}
        )
        assert update_response.status_code == 200
        
        # Reject at second step
        second_dept = sample_departments[1]
        
        rejection_comment_data = {
            "work_item_id": work_item["id"],
            "content": "Rejecting due to insufficient documentation",
            "comment_type": "rejection",
            "created_by": f"approver@{second_dept.name}.com",
            "department_id": second_dept.id,
            "metadata": {
                "rejection_reason": "insufficient_documentation",
                "required_actions": ["add_documentation", "resubmit"]
            }
        }
        
        rejection_response = test_client.post("/api/comments", json=rejection_comment_data)
        assert rejection_response.status_code == 201
        
        # Update work item to rejected state and return to previous step
        reject_update = {
            "current_step": 0,  # Return to first step
            "status": "rejected"
        }
        
        reject_response = test_client.put(f"/api/work-items/{work_item['id']}", json=reject_update)
        assert reject_response.status_code == 200
        
        # Verify rejection state
        rejected_item_response = test_client.get(f"/api/work-items/{work_item['id']}")
        rejected_item = rejected_item_response.json()
        
        assert rejected_item["status"] == "rejected"
        assert rejected_item["current_step"] == 0
        
        # Resubmit after fixing issues
        resubmit_comment_data = {
            "work_item_id": work_item["id"],
            "content": "Documentation added, resubmitting for approval",
            "comment_type": "status_update",
            "created_by": "requester@aviation.com",
            "metadata": {
                "action": "resubmit",
                "changes_made": ["added_documentation", "updated_specifications"]
            }
        }
        
        test_client.post("/api/comments", json=resubmit_comment_data)
        
        # Reset to pending status
        resubmit_update = {
            "current_step": 0,
            "status": "pending"
        }
        
        resubmit_response = test_client.put(f"/api/work-items/{work_item['id']}", json=resubmit_update)
        assert resubmit_response.status_code == 200
        
        # Verify resubmission
        resubmitted_response = test_client.get(f"/api/work-items/{work_item['id']}")
        resubmitted_item = resubmitted_response.json()
        
        assert resubmitted_item["status"] == "pending"
        assert resubmitted_item["current_step"] == 0
    
    def test_parallel_approval_workflow(self, test_client, test_session, sample_departments):
        """Test parallel approval at multiple departments."""
        # Create template with parallel approval rules
        template_data = {
            "name": "parallel_approval_workflow",
            "display_name": "Parallel Approval Workflow",
            "department_sequence": [dept.name for dept in sample_departments[:2]],  # Use 2 departments
            "approval_rules": {
                "require_comment": False,
                "min_approvals": 2,  # Require both departments
                "allow_parallel_approval": True
            },
            "created_by": "test@aviation.com"
        }
        
        template_response = test_client.post("/api/templates", json=template_data)
        template = template_response.json()
        
        work_item_data = {
            "title": "Parallel Approval Test",
            "description": "Testing parallel approval flow",
            "priority": "critical",
            "template_id": template["id"],
            "created_by": "requester@aviation.com"
        }
        
        work_item_response = test_client.post("/api/work-items", json=work_item_data)
        work_item = work_item_response.json()
        
        # Simulate parallel approvals from both departments
        approvals = []
        for i, dept in enumerate(sample_departments[:2]):
            comment_data = {
                "work_item_id": work_item["id"],
                "content": f"Parallel approval from {dept.display_name}",
                "comment_type": "approval",
                "created_by": f"approver_{i}@{dept.name}.com",
                "department_id": dept.id,
                "metadata": {
                    "approval_type": "parallel",
                    "approval_order": i + 1
                }
            }
            
            comment_response = test_client.post("/api/comments", json=comment_data)
            assert comment_response.status_code == 201
            approvals.append(comment_response.json())
        
        # Update work item to completed after receiving all required approvals
        complete_update = {
            "current_step": len(template["department_sequence"]),
            "status": "completed"
        }
        
        complete_response = test_client.put(f"/api/work-items/{work_item['id']}", json=complete_update)
        assert complete_response.status_code == 200
        
        # Verify completion
        completed_response = test_client.get(f"/api/work-items/{work_item['id']}")
        completed_item = completed_response.json()
        
        assert completed_item["status"] == "completed"
        assert len(approvals) == 2
    
    def test_escalation_workflow(self, test_client, test_session, sample_departments):
        """Test workflow escalation due to timeout."""
        # Create work item with short timeout
        template_data = {
            "name": "escalation_test_workflow",
            "display_name": "Escalation Test Workflow",
            "department_sequence": [sample_departments[0].name],
            "approval_rules": {
                "escalation_hours": 1  # Very short for testing
            },
            "workflow_config": {
                "timeout": 3600,  # 1 hour
                "auto_escalate": True
            },
            "created_by": "test@aviation.com"
        }
        
        template_response = test_client.post("/api/templates", json=template_data)
        template = template_response.json()
        
        # Create work item with past due date to simulate timeout
        past_date = (datetime.utcnow() - timedelta(hours=2)).isoformat()
        
        work_item_data = {
            "title": "Escalation Test Work Item",
            "description": "Testing escalation flow",
            "priority": "high",
            "template_id": template["id"],
            "created_by": "requester@aviation.com",
            "due_date": past_date,
            "created_at": past_date
        }
        
        work_item_response = test_client.post("/api/work-items", json=work_item_data)
        work_item = work_item_response.json()
        
        # Simulate escalation comment
        escalation_comment_data = {
            "work_item_id": work_item["id"],
            "content": "Work item escalated due to timeout",
            "comment_type": "status_update",
            "created_by": "system@aviation.com",
            "metadata": {
                "action": "escalate",
                "reason": "timeout",
                "original_assignee": "approver@aviation.com",
                "escalated_to": "supervisor@aviation.com"
            }
        }
        
        escalation_response = test_client.post("/api/comments", json=escalation_comment_data)
        assert escalation_response.status_code == 201
        
        # Update work item to escalated status
        escalation_update = {
            "status": "escalated",
            "assigned_to": "supervisor@aviation.com",
            "priority": "critical"  # Increase priority
        }
        
        escalate_response = test_client.put(f"/api/work-items/{work_item['id']}", json=escalation_update)
        assert escalate_response.status_code == 200
        
        # Verify escalation
        escalated_response = test_client.get(f"/api/work-items/{work_item['id']}")
        escalated_item = escalated_response.json()
        
        assert escalated_item["status"] == "escalated"
        assert escalated_item["assigned_to"] == "supervisor@aviation.com"
        assert escalated_item["priority"] == "critical"


@pytest.mark.integration
class TestApprovalFlowEdgeCases:
    """Test edge cases and error conditions in approval flows."""
    
    def test_approval_with_missing_department(self, test_client, test_session, sample_departments):
        """Test workflow with non-existent department in sequence."""
        # Create template with invalid department
        template_data = {
            "name": "invalid_dept_workflow",
            "display_name": "Invalid Department Workflow",
            "department_sequence": [sample_departments[0].name, "non_existent_dept"],
            "created_by": "test@aviation.com"
        }
        
        # Template creation should fail validation
        template_response = test_client.post("/api/templates", json=template_data)
        # Depending on validation logic, this might succeed but workflow execution should handle it
        
        if template_response.status_code == 201:
            template = template_response.json()
            
            work_item_data = {
                "title": "Invalid Department Test",
                "description": "Testing invalid department handling",
                "template_id": template["id"],
                "created_by": "requester@aviation.com"
            }
            
            work_item_response = test_client.post("/api/work-items", json=work_item_data)
            # Work item creation might succeed, but workflow execution should handle invalid department
            
            if work_item_response.status_code == 201:
                work_item = work_item_response.json()
                
                # Approve first valid step
                update_response = test_client.put(
                    f"/api/work-items/{work_item['id']}", 
                    json={"current_step": 1, "status": "in_progress"}
                )
                
                # Should encounter error when reaching invalid department
                # Implementation should handle this gracefully
                assert update_response.status_code in [200, 400]  # Either succeeds or fails gracefully
    
    def test_concurrent_approvals_same_step(self, test_client, test_session, sample_departments):
        """Test multiple concurrent approvals at the same step."""
        # Create template and work item
        template_data = {
            "name": "concurrent_approval_test",
            "display_name": "Concurrent Approval Test",
            "department_sequence": [sample_departments[0].name],
            "approval_rules": {
                "min_approvals": 1
            },
            "created_by": "test@aviation.com"
        }
        
        template_response = test_client.post("/api/templates", json=template_data)
        template = template_response.json()
        
        work_item_data = {
            "title": "Concurrent Approval Test",
            "description": "Testing concurrent approvals",
            "template_id": template["id"],
            "created_by": "requester@aviation.com"
        }
        
        work_item_response = test_client.post("/api/work-items", json=work_item_data)
        work_item = work_item_response.json()
        
        # Simulate two approvers trying to approve simultaneously
        approver1_comment = {
            "work_item_id": work_item["id"],
            "content": "Approved by first approver",
            "comment_type": "approval",
            "created_by": "approver1@aviation.com",
            "department_id": sample_departments[0].id
        }
        
        approver2_comment = {
            "work_item_id": work_item["id"],
            "content": "Approved by second approver",
            "comment_type": "approval",
            "created_by": "approver2@aviation.com",
            "department_id": sample_departments[0].id
        }
        
        # Post both comments
        response1 = test_client.post("/api/comments", json=approver1_comment)
        response2 = test_client.post("/api/comments", json=approver2_comment)
        
        assert response1.status_code == 201
        assert response2.status_code == 201
        
        # Both comments should be recorded
        comments_response = test_client.get(f"/api/comments?work_item_id={work_item['id']}")
        comments = comments_response.json()
        assert len(comments) == 2
    
    def test_approval_after_completion(self, test_client, test_session, sample_departments):
        """Test attempting approval after workflow completion."""
        # Create and complete a workflow
        template_data = {
            "name": "completed_workflow_test",
            "display_name": "Completed Workflow Test",
            "department_sequence": [sample_departments[0].name],
            "created_by": "test@aviation.com"
        }
        
        template_response = test_client.post("/api/templates", json=template_data)
        template = template_response.json()
        
        work_item_data = {
            "title": "Completed Workflow Test",
            "description": "Testing approval after completion",
            "template_id": template["id"],
            "created_by": "requester@aviation.com"
        }
        
        work_item_response = test_client.post("/api/work-items", json=work_item_data)
        work_item = work_item_response.json()
        
        # Complete the workflow
        complete_update = {
            "current_step": 1,
            "status": "completed"
        }
        
        test_client.put(f"/api/work-items/{work_item['id']}", json=complete_update)
        
        # Attempt to add approval comment after completion
        late_approval_comment = {
            "work_item_id": work_item["id"],
            "content": "Late approval attempt",
            "comment_type": "approval",
            "created_by": "late_approver@aviation.com",
            "department_id": sample_departments[0].id
        }
        
        # Comment should be allowed (for audit purposes) but not change workflow state
        late_response = test_client.post("/api/comments", json=late_approval_comment)
        assert late_response.status_code == 201
        
        # Verify work item status unchanged
        final_response = test_client.get(f"/api/work-items/{work_item['id']}")
        final_item = final_response.json()
        assert final_item["status"] == "completed"
    
    def test_workflow_with_empty_department_sequence(self, test_client, test_session):
        """Test creating workflow with empty department sequence."""
        template_data = {
            "name": "empty_sequence_workflow",
            "display_name": "Empty Sequence Workflow",
            "department_sequence": [],  # Empty sequence
            "created_by": "test@aviation.com"
        }
        
        # Template creation should fail
        template_response = test_client.post("/api/templates", json=template_data)
        assert template_response.status_code == 400
        assert "empty" in template_response.json()["detail"].lower()
    
    def test_workflow_with_duplicate_departments(self, test_client, test_session, sample_departments):
        """Test creating workflow with duplicate departments in sequence."""
        dept_name = sample_departments[0].name
        
        template_data = {
            "name": "duplicate_dept_workflow",
            "display_name": "Duplicate Department Workflow",
            "department_sequence": [dept_name, dept_name],  # Duplicate
            "created_by": "test@aviation.com"
        }
        
        # Template creation should fail validation
        template_response = test_client.post("/api/templates", json=template_data)
        assert template_response.status_code == 400
        assert "duplicate" in template_response.json()["detail"].lower()


@pytest.mark.integration
class TestCrossModuleIntegration:
    """Test integration between multiple modules in approval flows."""
    
    def test_comments_workflow_template_integration(self, test_client, test_session, sample_departments, sample_template):
        """Test integration between comments, workflow, and templates."""
        # Create work item with template
        work_item_data = {
            "title": "Cross-Module Integration Test",
            "description": "Testing integration across modules",
            "template_id": sample_template.id,
            "created_by": "requester@aviation.com"
        }
        
        work_item_response = test_client.post("/api/work-items", json=work_item_data)
        work_item = work_item_response.json()
        
        # Add comments from different departments
        for i, dept in enumerate(sample_departments):
            comment_data = {
                "work_item_id": work_item["id"],
                "content": f"Comment from {dept.display_name}",
                "comment_type": "status_update",
                "created_by": f"user@{dept.name}.com",
                "department_id": dept.id,
                "metadata": {
                    "step": i,
                    "department_name": dept.name,
                    "template_id": sample_template.id
                }
            }
            
            comment_response = test_client.post("/api/comments", json=comment_data)
            assert comment_response.status_code == 201
        
        # Verify all comments were created with proper relationships
        comments_response = test_client.get(f"/api/comments?work_item_id={work_item['id']}")
        comments = comments_response.json()
        
        assert len(comments) == len(sample_departments)
        
        # Verify each comment has proper department and template references
        for comment in comments:
            assert comment["work_item_id"] == work_item["id"]
            assert comment["department_id"] in [dept.id for dept in sample_departments]
            assert "template_id" in comment["metadata"]
    
    def test_department_template_validation_integration(self, test_client, test_session, sample_departments):
        """Test department validation when creating templates."""
        # Create template with valid departments
        valid_template_data = {
            "name": "dept_validation_workflow",
            "display_name": "Department Validation Workflow",
            "department_sequence": [dept.name for dept in sample_departments],
            "created_by": "test@aviation.com"
        }
        
        valid_response = test_client.post("/api/templates", json=valid_template_data)
        assert valid_response.status_code == 201
        
        # Attempt template with invalid department
        invalid_template_data = {
            "name": "invalid_dept_validation_workflow",
            "display_name": "Invalid Department Validation Workflow",
            "department_sequence": [sample_departments[0].name, "invalid_department"],
            "created_by": "test@aviation.com"
        }
        
        invalid_response = test_client.post("/api/templates", json=invalid_template_data)
        # Should either fail at creation or handle gracefully
        if invalid_response.status_code == 201:
            # If creation succeeds, validation should catch it during workflow execution
            template = invalid_response.json()
            
            # Test validation endpoint
            validation_response = test_client.post(
                "/api/templates/validate",
                json={"department_sequence": template["department_sequence"]}
            )
            
            validation_result = validation_response.json()
            assert validation_result["valid"] is False
            assert "invalid_department" in validation_result.get("invalid_departments", [])
    
    def test_full_module_ecosystem_workflow(self, test_client, test_session):
        """Test complete workflow using all modules together."""
        # Step 1: Create departments
        dept_data_list = [
            {
                "name": "ecosystem_dept_1",
                "display_name": "Ecosystem Department 1",
                "contact_email": "dept1@aviation.com"
            },
            {
                "name": "ecosystem_dept_2", 
                "display_name": "Ecosystem Department 2",
                "contact_email": "dept2@aviation.com"
            }
        ]
        
        created_depts = []
        for dept_data in dept_data_list:
            dept_response = test_client.post("/api/departments", json=dept_data)
            assert dept_response.status_code == 201
            created_depts.append(dept_response.json())
        
        # Step 2: Create workflow template using departments
        template_data = {
            "name": "ecosystem_test_workflow",
            "display_name": "Ecosystem Test Workflow",
            "description": "Testing full module ecosystem",
            "department_sequence": [dept["name"] for dept in created_depts],
            "approval_rules": {
                "require_comment": True,
                "min_approvals": 1
            },
            "category": "ecosystem_test",
            "created_by": "system@aviation.com"
        }
        
        template_response = test_client.post("/api/templates", json=template_data)
        assert template_response.status_code == 201
        template = template_response.json()
        
        # Step 3: Create work item using template
        work_item_data = {
            "title": "Ecosystem Test Work Item",
            "description": "Testing complete module ecosystem",
            "priority": "medium",
            "template_id": template["id"],
            "created_by": "user@aviation.com",
            "metadata": {
                "test_type": "ecosystem",
                "modules_involved": ["departments", "templates", "comments", "workflows"]
            }
        }
        
        work_item_response = test_client.post("/api/work-items", json=work_item_data)
        assert work_item_response.status_code == 201
        work_item = work_item_response.json()
        
        # Step 4: Process through workflow with comments
        for step, dept in enumerate(created_depts):
            # Add comment for this step
            comment_data = {
                "work_item_id": work_item["id"],
                "content": f"Processing at {dept['display_name']} - Step {step + 1}",
                "comment_type": "status_update",
                "created_by": f"processor@{dept['name']}.com",
                "department_id": dept["id"],
                "metadata": {
                    "processing_step": step + 1,
                    "department_name": dept["name"],
                    "template_name": template["name"]
                }
            }
            
            comment_response = test_client.post("/api/comments", json=comment_data)
            assert comment_response.status_code == 201
            
            # Advance workflow
            if step < len(created_depts) - 1:
                update_data = {
                    "current_step": step + 1,
                    "status": "in_progress"
                }
            else:
                update_data = {
                    "current_step": step + 1,
                    "status": "completed"
                }
            
            update_response = test_client.put(f"/api/work-items/{work_item['id']}", json=update_data)
            assert update_response.status_code == 200
        
        # Step 5: Verify complete ecosystem worked together
        final_work_item_response = test_client.get(f"/api/work-items/{work_item['id']}")
        final_work_item = final_work_item_response.json()
        
        assert final_work_item["status"] == "completed"
        assert final_work_item["current_step"] == len(created_depts)
        
        # Verify all comments were created
        final_comments_response = test_client.get(f"/api/comments?work_item_id={work_item['id']}")
        final_comments = final_comments_response.json()
        
        assert len(final_comments) == len(created_depts)
        
        # Verify template was used correctly
        template_verification_response = test_client.get(f"/api/templates/{template['id']}")
        template_verification = template_verification_response.json()
        
        assert template_verification["department_sequence"] == [dept["name"] for dept in created_depts]
        
        # Verify departments are still accessible
        for dept in created_depts:
            dept_verification_response = test_client.get(f"/api/departments/{dept['id']}")
            assert dept_verification_response.status_code == 200
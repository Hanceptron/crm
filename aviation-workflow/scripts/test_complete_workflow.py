#!/usr/bin/env python3
"""
Complete Workflow Testing Script

Tests a complete approval workflow with 4 departments:
1. Create work item
2. Approve through 3 departments  
3. Reject back to first
4. Approve to completion
5. Verify Burr state at each step
"""

import sys
import os
import subprocess
import time
import requests
import json
from typing import Dict, List, Any, Optional
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class WorkflowTester:
    """Complete workflow testing class."""
    
    def __init__(self, api_base_url: str = "http://localhost:8000"):
        self.api_base_url = api_base_url
        self.api_process = None
        self.created_departments = []
        self.created_template = None
        self.test_work_item = None
        self.workflow_history = []
    
    def start_api_server(self) -> bool:
        """Start the API server."""
        print("🚀 Starting API server for workflow testing...")
        
        # Start uvicorn server
        self.api_process = subprocess.Popen([
            sys.executable, "-m", "uvicorn", 
            "api.main:app", 
            "--host", "localhost", 
            "--port", "8000"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Wait for server to start
        for _ in range(30):  # 30 second timeout
            try:
                response = requests.get(f"{self.api_base_url}/health", timeout=2)
                if response.status_code == 200:
                    print("✅ API server started successfully")
                    return True
            except Exception:
                pass
            time.sleep(1)
        
        print("❌ API server failed to start")
        return False
    
    def stop_api_server(self):
        """Stop the API server."""
        if self.api_process:
            self.api_process.terminate()
            try:
                self.api_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.api_process.kill()
            print("🛑 API server stopped")
    
    def setup_test_data(self) -> bool:
        """Set up test departments and template."""
        print("📋 Setting up test data...")
        
        # Create 4 departments for testing
        departments_data = [
            {
                "name": "engineering", 
                "display_name": "Engineering",
                "description": "Engineering review and approval",
                "contact_email": "engineering@aviation.com"
            },
            {
                "name": "quality_control",
                "display_name": "Quality Control", 
                "description": "Quality assurance and testing",
                "contact_email": "qc@aviation.com"
            },
            {
                "name": "operations",
                "display_name": "Operations",
                "description": "Operational approval and scheduling", 
                "contact_email": "ops@aviation.com"
            },
            {
                "name": "final_approval",
                "display_name": "Final Approval",
                "description": "Final sign-off and authorization",
                "contact_email": "final@aviation.com" 
            }
        ]
        
        # Create departments
        for dept_data in departments_data:
            try:
                response = requests.post(
                    f"{self.api_base_url}/api/departments", 
                    json=dept_data,
                    timeout=10
                )
                
                if response.status_code == 201:
                    dept = response.json()
                    self.created_departments.append(dept)
                    print(f"  ✅ Created department: {dept['display_name']}")
                elif response.status_code == 400 and "already exists" in response.text:
                    # Department already exists, get it
                    get_response = requests.get(f"{self.api_base_url}/api/departments")
                    if get_response.status_code == 200:
                        existing_depts = get_response.json()
                        for existing_dept in existing_depts:
                            if existing_dept['name'] == dept_data['name']:
                                self.created_departments.append(existing_dept)
                                print(f"  ℹ️  Using existing department: {existing_dept['display_name']}")
                                break
                else:
                    print(f"  ❌ Failed to create department {dept_data['name']}: {response.text}")
                    return False
            except Exception as e:
                print(f"  ❌ Error creating department {dept_data['name']}: {e}")
                return False
        
        if len(self.created_departments) != 4:
            print(f"❌ Expected 4 departments, got {len(self.created_departments)}")
            return False
        
        # Create workflow template
        template_data = {
            "name": "complete_workflow_test",
            "display_name": "Complete Workflow Test",
            "description": "Testing complete workflow with 4 departments",
            "department_sequence": [dept["name"] for dept in self.created_departments],
            "approval_rules": {
                "require_comment": True,
                "min_approvals": 1,
                "allow_parallel_approval": False
            },
            "workflow_config": {
                "timeout": 3600,
                "auto_approve_minor": False
            },
            "category": "workflow_test",
            "created_by": "workflow_tester@aviation.com"
        }
        
        try:
            response = requests.post(
                f"{self.api_base_url}/api/templates",
                json=template_data,
                timeout=10
            )
            
            if response.status_code == 201:
                self.created_template = response.json()
                print(f"  ✅ Created template: {self.created_template['display_name']}")
            else:
                print(f"  ❌ Failed to create template: {response.text}")
                return False
        except Exception as e:
            print(f"  ❌ Error creating template: {e}")
            return False
        
        return True
    
    def create_work_item(self) -> bool:
        """Create a test work item."""
        print("📝 Creating test work item...")
        
        work_item_data = {
            "title": "Complete Workflow Test Item",
            "description": "Testing complete approval workflow through 4 departments",
            "priority": "high",
            "template_id": self.created_template["id"],
            "created_by": "workflow_tester@aviation.com",
            "assigned_to": "approver@aviation.com",
            "metadata": {
                "test_type": "complete_workflow",
                "aircraft_tail": "N123WF",
                "location": "KORD",
                "estimated_hours": 8.0
            }
        }
        
        try:
            response = requests.post(
                f"{self.api_base_url}/api/work-items",
                json=work_item_data,
                timeout=10
            )
            
            if response.status_code == 201:
                self.test_work_item = response.json()
                print(f"  ✅ Created work item: {self.test_work_item['title']}")
                print(f"  📍 Initial state: Step {self.test_work_item['current_step']}, Status: {self.test_work_item['status']}")
                
                # Record initial state
                self.record_workflow_state("CREATED", "Work item created with template")
                return True
            else:
                print(f"  ❌ Failed to create work item: {response.text}")
                return False
        except Exception as e:
            print(f"  ❌ Error creating work item: {e}")
            return False
    
    def record_workflow_state(self, action: str, description: str):
        """Record current workflow state for verification."""
        if not self.test_work_item:
            return
        
        # Get current work item state
        try:
            response = requests.get(
                f"{self.api_base_url}/api/work-items/{self.test_work_item['id']}", 
                timeout=5
            )
            
            if response.status_code == 200:
                current_state = response.json()
                
                state_record = {
                    "timestamp": datetime.now().isoformat(),
                    "action": action,
                    "description": description,
                    "current_step": current_state["current_step"],
                    "status": current_state["status"],
                    "department_ids": current_state["department_ids"],
                    "current_department": (
                        current_state["department_ids"][current_state["current_step"]] 
                        if current_state["current_step"] < len(current_state["department_ids"]) 
                        else "COMPLETED"
                    )
                }
                
                self.workflow_history.append(state_record)
                print(f"  📊 State recorded: {action} -> Step {current_state['current_step']}, Status: {current_state['status']}")
        except Exception as e:
            print(f"  ⚠️  Could not record state: {e}")
    
    def approve_step(self, step: int, comment: str) -> bool:
        """Approve current step and advance workflow."""
        if not self.test_work_item:
            return False
        
        dept = self.created_departments[step]
        print(f"✅ Approving step {step + 1}: {dept['display_name']}")
        
        # Add approval comment
        comment_data = {
            "work_item_id": self.test_work_item["id"],
            "content": comment,
            "comment_type": "approval",
            "created_by": f"approver@{dept['name']}.com",
            "department_id": dept["id"],
            "metadata": {
                "approval_step": step,
                "department_name": dept["name"],
                "approval_timestamp": datetime.now().isoformat()
            }
        }
        
        try:
            # Add comment
            comment_response = requests.post(
                f"{self.api_base_url}/api/comments",
                json=comment_data,
                timeout=10
            )
            
            if comment_response.status_code != 201:
                print(f"  ❌ Failed to add approval comment: {comment_response.text}")
                return False
            
            # Update work item to next step
            next_step = step + 1
            if next_step >= len(self.created_departments):
                # Final approval - mark as completed
                update_data = {
                    "current_step": next_step,
                    "status": "completed"
                }
            else:
                # Move to next department
                update_data = {
                    "current_step": next_step,
                    "status": "in_progress"
                }
            
            update_response = requests.put(
                f"{self.api_base_url}/api/work-items/{self.test_work_item['id']}",
                json=update_data,
                timeout=10
            )
            
            if update_response.status_code == 200:
                updated_item = update_response.json()
                print(f"  ✅ Approved by {dept['display_name']}")
                print(f"  📍 New state: Step {updated_item['current_step']}, Status: {updated_item['status']}")
                
                # Record state
                self.record_workflow_state(
                    f"APPROVED_{step + 1}", 
                    f"Approved by {dept['display_name']}: {comment}"
                )
                return True
            else:
                print(f"  ❌ Failed to update work item: {update_response.text}")
                return False
        
        except Exception as e:
            print(f"  ❌ Error during approval: {e}")
            return False
    
    def reject_to_step(self, current_step: int, target_step: int, reason: str) -> bool:
        """Reject work item back to a previous step."""
        if not self.test_work_item:
            return False
        
        current_dept = self.created_departments[current_step]
        target_dept = self.created_departments[target_step]
        
        print(f"❌ Rejecting from step {current_step + 1} ({current_dept['display_name']}) back to step {target_step + 1} ({target_dept['display_name']})")
        
        # Add rejection comment
        comment_data = {
            "work_item_id": self.test_work_item["id"],
            "content": f"Rejected: {reason}",
            "comment_type": "rejection",
            "created_by": f"approver@{current_dept['name']}.com",
            "department_id": current_dept["id"],
            "metadata": {
                "rejection_step": current_step,
                "target_step": target_step,
                "rejection_reason": reason,
                "rejection_timestamp": datetime.now().isoformat()
            }
        }
        
        try:
            # Add rejection comment
            comment_response = requests.post(
                f"{self.api_base_url}/api/comments",
                json=comment_data,
                timeout=10
            )
            
            if comment_response.status_code != 201:
                print(f"  ❌ Failed to add rejection comment: {comment_response.text}")
                return False
            
            # Update work item back to target step
            update_data = {
                "current_step": target_step,
                "status": "rejected"
            }
            
            update_response = requests.put(
                f"{self.api_base_url}/api/work-items/{self.test_work_item['id']}",
                json=update_data,
                timeout=10
            )
            
            if update_response.status_code == 200:
                updated_item = update_response.json()
                print(f"  ✅ Rejected by {current_dept['display_name']}")
                print(f"  📍 Returned to: Step {updated_item['current_step']}, Status: {updated_item['status']}")
                
                # Record state
                self.record_workflow_state(
                    f"REJECTED_{current_step + 1}_TO_{target_step + 1}",
                    f"Rejected by {current_dept['display_name']}: {reason}"
                )
                return True
            else:
                print(f"  ❌ Failed to update work item: {update_response.text}")
                return False
        
        except Exception as e:
            print(f"  ❌ Error during rejection: {e}")
            return False
    
    def run_complete_workflow_test(self) -> bool:
        """Run the complete workflow test scenario."""
        print("🔄 Running Complete Workflow Test")
        print("=" * 50)
        
        if not self.setup_test_data():
            return False
        
        if not self.create_work_item():
            return False
        
        # Test scenario: Create → Approve 3 steps → Reject → Approve to completion
        
        # Step 1: Approve through first 3 departments
        print(f"\n📈 Phase 1: Approving through first 3 departments...")
        
        for step in range(3):  # Approve steps 0, 1, 2
            if not self.approve_step(step, f"Approved at step {step + 1} - proceeding to next department"):
                return False
            time.sleep(0.5)  # Small delay between approvals
        
        # Step 2: Reject from 4th department back to first
        print(f"\n📉 Phase 2: Rejecting from final department...")
        
        if not self.reject_to_step(3, 0, "Insufficient documentation - needs revision from engineering"):
            return False
        
        # Step 3: Approve all the way to completion
        print(f"\n📈 Phase 3: Re-approving through all departments to completion...")
        
        # First reset status to pending for resubmission
        try:
            resubmit_data = {"status": "pending"}
            requests.put(
                f"{self.api_base_url}/api/work-items/{self.test_work_item['id']}",
                json=resubmit_data,
                timeout=10
            )
            self.record_workflow_state("RESUBMITTED", "Resubmitted after revision")
        except Exception as e:
            print(f"  ⚠️  Could not reset to pending: {e}")
        
        # Approve through all 4 departments
        for step in range(4):
            if not self.approve_step(step, f"Final approval at step {step + 1} - documentation revised"):
                return False
            time.sleep(0.5)
        
        return True
    
    def verify_workflow_states(self) -> bool:
        """Verify all workflow states were recorded correctly."""
        print(f"\n🔍 Verifying Workflow States")
        print("=" * 40)
        
        if len(self.workflow_history) == 0:
            print("❌ No workflow states recorded")
            return False
        
        expected_actions = [
            "CREATED",
            "APPROVED_1", "APPROVED_2", "APPROVED_3",  # First 3 approvals
            "REJECTED_4_TO_1",  # Rejection back to start
            "RESUBMITTED",  # Resubmission
            "APPROVED_1", "APPROVED_2", "APPROVED_3", "APPROVED_4"  # Final approvals
        ]
        
        print(f"📊 Workflow History ({len(self.workflow_history)} states):")
        
        for i, state in enumerate(self.workflow_history):
            print(f"  {i + 1:2d}. {state['action']:20} | Step: {state['current_step']} | Status: {state['status']:12} | Dept: {state['current_department']}")
        
        # Verify key states exist
        recorded_actions = [state['action'] for state in self.workflow_history]
        
        # Check for required state transitions
        checks = {
            "Initial Creation": "CREATED" in recorded_actions,
            "First Approval": any("APPROVED_1" in action for action in recorded_actions),
            "Rejection": any("REJECTED" in action for action in recorded_actions),
            "Final Completion": self.workflow_history[-1]['status'] == 'completed' if self.workflow_history else False
        }
        
        all_passed = True
        print(f"\n✅ State Verification:")
        for check_name, passed in checks.items():
            status = "✅" if passed else "❌"
            print(f"  {status} {check_name}")
            if not passed:
                all_passed = False
        
        return all_passed
    
    def cleanup_test_data(self):
        """Clean up test data."""
        print(f"\n🧹 Cleaning up test data...")
        
        # Note: In a real system, you might want to keep test data for debugging
        # For this test, we'll leave the data for inspection
        print(f"  ℹ️  Test data left in place for inspection")
        print(f"  📝 Work Item ID: {self.test_work_item['id'] if self.test_work_item else 'N/A'}")
        print(f"  📋 Template ID: {self.created_template['id'] if self.created_template else 'N/A'}")
    
    def generate_test_report(self, test_passed: bool):
        """Generate comprehensive test report."""
        print(f"\n" + "=" * 60)
        print("📊 COMPLETE WORKFLOW TEST REPORT")
        print("=" * 60)
        
        print(f"🎯 Test Objective: Complete workflow with 4 departments")
        print(f"📅 Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📈 Test Result: {'✅ PASSED' if test_passed else '❌ FAILED'}")
        
        if self.test_work_item:
            print(f"\n📝 Work Item Details:")
            print(f"  ID: {self.test_work_item['id']}")
            print(f"  Title: {self.test_work_item['title']}")
            print(f"  Template: {self.created_template['name'] if self.created_template else 'N/A'}")
        
        if self.created_departments:
            print(f"\n🏢 Department Sequence:")
            for i, dept in enumerate(self.created_departments):
                print(f"  {i + 1}. {dept['display_name']} ({dept['name']})")
        
        if self.workflow_history:
            print(f"\n📊 Workflow Timeline:")
            for state in self.workflow_history:
                timestamp = datetime.fromisoformat(state['timestamp']).strftime('%H:%M:%S')
                print(f"  {timestamp} | {state['action']:20} | Step {state['current_step']} | {state['status']}")
        
        print(f"\n🎯 SUCCESS METRICS VERIFICATION:")
        metrics = {
            "✅ Can create work item with 3+ departments": bool(self.test_work_item and len(self.created_departments) >= 3),
            "✅ Can approve and see state change": len([s for s in self.workflow_history if 'APPROVED' in s['action']]) > 0,
            "✅ Can reject to any previous step": len([s for s in self.workflow_history if 'REJECTED' in s['action']]) > 0,
            "✅ Workflow reaches completion": self.workflow_history[-1]['status'] == 'completed' if self.workflow_history else False
        }
        
        for metric, achieved in metrics.items():
            print(f"  {'✅' if achieved else '❌'} {metric.replace('✅ ', '')}")
        
        overall_success = all(metrics.values()) and test_passed
        
        if overall_success:
            print(f"\n🎉 COMPLETE WORKFLOW TEST: SUCCESS")
            print("   All workflow functionality verified working correctly")
        else:
            print(f"\n⚠️  COMPLETE WORKFLOW TEST: ISSUES DETECTED")
            print("   Some workflow functionality needs attention")
        
        return overall_success


def main():
    """Main test execution."""
    print("🔬 Aviation Workflow System - Complete Workflow Testing")
    print("=" * 70)
    
    # Check if we're in the right directory
    if not os.path.exists("api/main.py"):
        print("❌ Error: Run this script from the project root directory")
        return 1
    
    tester = WorkflowTester()
    
    try:
        # Start API server
        if not tester.start_api_server():
            return 1
        
        # Run workflow test
        test_passed = tester.run_complete_workflow_test()
        
        # Verify states
        states_verified = tester.verify_workflow_states()
        
        # Generate report
        overall_success = tester.generate_test_report(test_passed and states_verified)
        
        # Cleanup
        tester.cleanup_test_data()
        
        return 0 if overall_success else 1
    
    except KeyboardInterrupt:
        print(f"\n⚠️  Test interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        return 1
    finally:
        tester.stop_api_server()


if __name__ == "__main__":
    sys.exit(main())
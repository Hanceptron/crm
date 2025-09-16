"""
Burr-based workflow engine for the Aviation Workflow System.

Handles ONLY state transitions, not business logic. Provides a clean
interface for creating workflows from templates and executing transitions
with proper validation and persistence.
"""

import os
import logging
from typing import Dict, List, Optional, Any
from burr.core import State, Action, Application, ApplicationBuilder
from burr.tracking import LocalTrackingClient
from core.config import settings

logger = logging.getLogger(__name__)


class WorkflowEngineError(Exception):
    """Base exception for workflow engine errors."""
    pass


class InvalidTransitionError(WorkflowEngineError):
    """Raised when an invalid state transition is attempted."""
    pass


class WorkflowNotFoundError(WorkflowEngineError):
    """Raised when a workflow is not found."""
    pass


class WorkflowEngine:
    """
    Burr-based workflow engine for state management.
    
    Handles ONLY state transitions, not business logic. Manages workflow
    creation from templates, state persistence, and transition validation.
    """
    
    def __init__(self):
        """Initialize workflow engine with state tracking."""
        self._applications: Dict[str, Application] = {}
        self._ensure_state_directory()
        self._tracking_client = self._create_tracking_client()
    
    def _ensure_state_directory(self) -> None:
        """Ensure the Burr state directory exists."""
        if not os.path.exists(settings.burr_state_dir):
            os.makedirs(settings.burr_state_dir, exist_ok=True)
            logger.info(f"Created Burr state directory: {settings.burr_state_dir}")
    
    def _create_tracking_client(self) -> LocalTrackingClient:
        """Create Burr tracking client for state persistence."""
        tracker_path = os.path.join(settings.burr_state_dir, "burr_state.db")
        return LocalTrackingClient(tracker_path)
    
    def create_workflow(self, template: str, workflow_id: str, 
                       department_sequence: List[str], 
                       initial_data: Optional[Dict[str, Any]] = None) -> Application:
        """
        Create workflow from template.
        
        Args:
            template: Workflow template name (e.g., 'sequential_approval')
            workflow_id: Unique identifier for this workflow instance
            department_sequence: List of department IDs for the workflow
            initial_data: Optional initial data for the workflow
            
        Returns:
            Burr Application instance
            
        Raises:
            WorkflowEngineError: If template is not found or creation fails
        """
        try:
            if template == "sequential_approval":
                from workflows.sequential_approval import build_approval_workflow
                
                # Create application with tracking
                app = build_approval_workflow(
                    department_sequence=department_sequence,
                    tracker=self._tracking_client,
                    app_id=workflow_id
                )
                
                # Set initial data if provided
                if initial_data:
                    current_state = app.state
                    for key, value in initial_data.items():
                        current_state = current_state.update(**{key: value})
                    app = app.with_state(**current_state.get_all())
                
                # Store the application
                self._applications[workflow_id] = app
                
                logger.info(f"Created workflow {workflow_id} with template {template}")
                return app
            
            else:
                raise WorkflowEngineError(f"Unknown workflow template: {template}")
        
        except ImportError as e:
            raise WorkflowEngineError(f"Failed to import workflow template {template}: {e}")
        except Exception as e:
            raise WorkflowEngineError(f"Failed to create workflow {workflow_id}: {e}")
    
    def execute_transition(self, workflow_id: str, action: str, 
                          context: Optional[Dict[str, Any]] = None) -> State:
        """
        Execute state transition with validation.
        
        Args:
            workflow_id: Unique workflow identifier
            action: Action to execute (e.g., 'approve', 'reject')
            context: Optional context data for the action
            
        Returns:
            New state after transition
            
        Raises:
            WorkflowNotFoundError: If workflow is not found
            InvalidTransitionError: If transition is not valid
            WorkflowEngineError: For other execution errors
        """
        if workflow_id not in self._applications:
            raise WorkflowNotFoundError(f"Workflow {workflow_id} not found")
        
        app = self._applications[workflow_id]
        context = context or {}
        
        try:
            # Check if action is available
            available_actions = app.get_next_action()
            if available_actions is None:
                raise InvalidTransitionError(f"No actions available for workflow {workflow_id}")
            
            # For single action, convert to list for consistency
            if isinstance(available_actions, str):
                available_actions = [available_actions]
            elif hasattr(available_actions, 'name'):
                available_actions = [available_actions.name]
            elif isinstance(available_actions, tuple):
                available_actions = list(available_actions)
            
            if action not in available_actions:
                raise InvalidTransitionError(
                    f"Action '{action}' not available. Available actions: {available_actions}"
                )
            
            # Execute the action
            action_result, new_app = app.run(
                halt_after=[action],
                inputs=context
            )
            
            # Update stored application
            self._applications[workflow_id] = new_app
            
            # Get the new state
            new_state = new_app.state
            
            logger.info(f"Executed transition {action} for workflow {workflow_id}")
            return new_state
        
        except InvalidTransitionError:
            raise
        except Exception as e:
            raise WorkflowEngineError(f"Failed to execute transition {action} for workflow {workflow_id}: {e}")
    
    def get_available_actions(self, workflow_id: str) -> List[str]:
        """
        Get valid actions for current state.
        
        Args:
            workflow_id: Unique workflow identifier
            
        Returns:
            List of available action names
            
        Raises:
            WorkflowNotFoundError: If workflow is not found
        """
        if workflow_id not in self._applications:
            raise WorkflowNotFoundError(f"Workflow {workflow_id} not found")
        
        app = self._applications[workflow_id]
        
        try:
            next_action = app.get_next_action()
            
            if next_action is None:
                return []
            
            # Handle different return types from get_next_action
            if isinstance(next_action, str):
                return [next_action]
            elif hasattr(next_action, 'name'):
                return [next_action.name]
            elif isinstance(next_action, (list, tuple)):
                return [action.name if hasattr(action, 'name') else str(action) for action in next_action]
            else:
                return [str(next_action)]
        
        except Exception as e:
            logger.error(f"Error getting available actions for workflow {workflow_id}: {e}")
            return []
    
    def get_workflow_state(self, workflow_id: str) -> Optional[State]:
        """
        Get current state of a workflow.
        
        Args:
            workflow_id: Unique workflow identifier
            
        Returns:
            Current workflow state or None if not found
        """
        if workflow_id not in self._applications:
            return None
        
        return self._applications[workflow_id].state
    
    def get_workflow_history(self, workflow_id: str) -> List[Dict[str, Any]]:
        """
        Get execution history for a workflow.
        
        Args:
            workflow_id: Unique workflow identifier
            
        Returns:
            List of execution history entries
        """
        try:
            return self._tracking_client.list_app_runs(
                partition_key=workflow_id,
                limit=100
            )
        except Exception as e:
            logger.error(f"Error getting workflow history for {workflow_id}: {e}")
            return []
    
    def workflow_exists(self, workflow_id: str) -> bool:
        """Check if a workflow exists."""
        return workflow_id in self._applications
    
    def remove_workflow(self, workflow_id: str) -> bool:
        """
        Remove a workflow from memory.
        
        Args:
            workflow_id: Unique workflow identifier
            
        Returns:
            True if removed, False if not found
        """
        if workflow_id in self._applications:
            del self._applications[workflow_id]
            logger.info(f"Removed workflow {workflow_id}")
            return True
        return False
    
    def list_workflows(self) -> List[str]:
        """Get list of all active workflow IDs."""
        return list(self._applications.keys())
    
    def get_workflow_info(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a workflow.
        
        Args:
            workflow_id: Unique workflow identifier
            
        Returns:
            Dictionary with workflow information or None if not found
        """
        if workflow_id not in self._applications:
            return None
        
        app = self._applications[workflow_id]
        state = app.state
        
        return {
            "workflow_id": workflow_id,
            "current_state": state.get_all(),
            "available_actions": self.get_available_actions(workflow_id),
            "app_id": getattr(app, 'app_id', workflow_id)
        }


# Global workflow engine instance
workflow_engine = WorkflowEngine()
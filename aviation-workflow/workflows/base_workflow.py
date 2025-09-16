"""
Abstract base workflow for the Aviation Workflow System.

Provides common validation methods, shared transition logic, and base
functionality that all concrete workflow implementations can inherit from.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any, List, Optional
from burr.core import Action, State, Application


class BaseWorkflowAction(Action, ABC):
    """
    Abstract base class for all workflow actions.
    
    Provides common functionality and validation that all workflow
    actions should implement.
    """
    
    @property
    @abstractmethod
    def reads(self) -> List[str]:
        """State keys this action reads from."""
        pass
    
    @property
    @abstractmethod
    def writes(self) -> List[str]:
        """State keys this action writes to."""
        pass
    
    def validate_state(self, state: State) -> bool:
        """
        Validate that the current state is valid for this action.
        
        Args:
            state: Current workflow state
            
        Returns:
            True if state is valid, False otherwise
        """
        # Check that all required read keys exist
        for key in self.reads:
            if key not in state:
                return False
        
        return True
    
    def add_to_history(self, state: State, action_name: str, **kwargs) -> Dict[str, Any]:
        """
        Add an entry to the workflow history.
        
        Args:
            state: Current workflow state
            action_name: Name of the action being performed
            **kwargs: Additional data to store in history
            
        Returns:
            Updated history list
        """
        history = state.get("history", [])
        
        history_entry = {
            "action": action_name,
            "timestamp": datetime.utcnow().isoformat(),
            "from_step": state.get("current_step", 0),
            "from_state": state.get("current_state", "unknown"),
            **kwargs
        }
        
        history.append(history_entry)
        return history
    
    def validate_step_transition(self, current_step: int, target_step: int, 
                                sequence_length: int) -> bool:
        """
        Validate that a step transition is valid.
        
        Args:
            current_step: Current step in the sequence
            target_step: Target step to transition to
            sequence_length: Total length of the department sequence
            
        Returns:
            True if transition is valid, False otherwise
        """
        # Can't go to negative steps
        if target_step < 0:
            return False
        
        # Can't go beyond the sequence
        if target_step >= sequence_length:
            return False
        
        # For forward transitions, can only go to next step
        if target_step > current_step and target_step != current_step + 1:
            return False
        
        return True
    
    def get_current_department(self, state: State) -> Optional[str]:
        """
        Get the current department from the workflow state.
        
        Args:
            state: Current workflow state
            
        Returns:
            Current department ID or None if not found
        """
        current_step = state.get("current_step", 0)
        sequence = state.get("department_sequence", [])
        
        if 0 <= current_step < len(sequence):
            return sequence[current_step]
        
        return None
    
    def get_next_department(self, state: State) -> Optional[str]:
        """
        Get the next department in the sequence.
        
        Args:
            state: Current workflow state
            
        Returns:
            Next department ID or None if at end
        """
        current_step = state.get("current_step", 0)
        sequence = state.get("department_sequence", [])
        next_step = current_step + 1
        
        if 0 <= next_step < len(sequence):
            return sequence[next_step]
        
        return None
    
    def is_final_step(self, state: State) -> bool:
        """
        Check if current step is the final step in the sequence.
        
        Args:
            state: Current workflow state
            
        Returns:
            True if at final step, False otherwise
        """
        current_step = state.get("current_step", 0)
        sequence = state.get("department_sequence", [])
        
        return current_step >= len(sequence) - 1


class BaseWorkflow(ABC):
    """
    Abstract base class for all workflow implementations.
    
    Provides common patterns and utilities for building Burr workflows
    with consistent behavior and validation.
    """
    
    @abstractmethod
    def get_actions(self) -> Dict[str, Action]:
        """
        Get all actions available in this workflow.
        
        Returns:
            Dictionary mapping action names to Action instances
        """
        pass
    
    @abstractmethod
    def get_transitions(self) -> List[tuple]:
        """
        Get workflow transitions.
        
        Returns:
            List of transition tuples for ApplicationBuilder
        """
        pass
    
    @abstractmethod
    def get_initial_state(self, **kwargs) -> Dict[str, Any]:
        """
        Get initial state for the workflow.
        
        Args:
            **kwargs: Additional parameters for state initialization
            
        Returns:
            Initial state dictionary
        """
        pass
    
    def validate_department_sequence(self, sequence: List[str]) -> bool:
        """
        Validate that a department sequence is valid.
        
        Args:
            sequence: List of department IDs
            
        Returns:
            True if sequence is valid, False otherwise
        """
        # Must have at least one department
        if not sequence or len(sequence) == 0:
            return False
        
        # All departments must be non-empty strings
        for dept in sequence:
            if not isinstance(dept, str) or not dept.strip():
                return False
        
        return True
    
    def create_common_initial_state(self, department_sequence: List[str], 
                                   **kwargs) -> Dict[str, Any]:
        """
        Create common initial state elements.
        
        Args:
            department_sequence: List of department IDs
            **kwargs: Additional state data
            
        Returns:
            Initial state dictionary with common elements
        """
        if not self.validate_department_sequence(department_sequence):
            raise ValueError("Invalid department sequence")
        
        initial_state = {
            "current_step": 0,
            "department_sequence": department_sequence,
            "status": "active",
            "history": [],
            "created_at": datetime.utcnow().isoformat(),
            **kwargs
        }
        
        return initial_state
    
    def get_workflow_status(self, state: State) -> str:
        """
        Determine workflow status from current state.
        
        Args:
            state: Current workflow state
            
        Returns:
            Status string (active, completed, cancelled)
        """
        return state.get("status", "active")
    
    def get_progress_percentage(self, state: State) -> float:
        """
        Calculate workflow progress as percentage.
        
        Args:
            state: Current workflow state
            
        Returns:
            Progress percentage (0.0 to 100.0)
        """
        current_step = state.get("current_step", 0)
        sequence = state.get("department_sequence", [])
        
        if not sequence:
            return 0.0
        
        # If completed, return 100%
        if self.get_workflow_status(state) == "completed":
            return 100.0
        
        # Calculate progress based on current step
        progress = (current_step / len(sequence)) * 100.0
        return min(progress, 100.0)
    
    def get_current_department_info(self, state: State) -> Dict[str, Any]:
        """
        Get information about the current department.
        
        Args:
            state: Current workflow state
            
        Returns:
            Dictionary with current department information
        """
        current_step = state.get("current_step", 0)
        sequence = state.get("department_sequence", [])
        
        info = {
            "current_step": current_step,
            "total_steps": len(sequence),
            "current_department": None,
            "next_department": None,
            "is_final_step": False
        }
        
        if 0 <= current_step < len(sequence):
            info["current_department"] = sequence[current_step]
            info["is_final_step"] = current_step >= len(sequence) - 1
            
            if not info["is_final_step"]:
                info["next_department"] = sequence[current_step + 1]
        
        return info
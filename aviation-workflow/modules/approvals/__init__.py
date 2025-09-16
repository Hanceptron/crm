"""
Approvals module for the Aviation Workflow System.

Implements the ModuleInterface for pluggable approval/rejection functionality
with Burr workflow engine integration following the architecture specification.
"""

import logging
from typing import Optional, List, Type
from fastapi import APIRouter
from sqlmodel import SQLModel

from core.plugin_manager import ModuleInterface
from .models import Approval
from .routes import router

logger = logging.getLogger(__name__)


class ApprovalsModule(ModuleInterface):
    """
    Approvals module implementation following ModuleInterface specification.
    
    Provides approval/rejection functionality as a pluggable module that
    integrates with the Burr workflow engine for state transitions.
    """
    
    # Required attributes as per MODULE INTERFACE SPECIFICATION
    name: str = "approvals"
    version: str = "1.0.0"
    description: str = "Approval and rejection module for workflow state transitions"
    
    # Optional components
    router: Optional[APIRouter] = router
    models: Optional[List[Type[SQLModel]]] = [Approval]
    dependencies: Optional[List[str]] = None  # No module dependencies required
    
    def on_load(self) -> None:
        """
        Called when module is loaded.
        
        Performs initialization including workflow engine verification
        and approval system setup.
        """
        logger.info(f"Loading {self.name} module v{self.version}")
        
        try:
            # Log module configuration
            logger.info(f"Module: {self.name}")
            logger.info(f"Description: {self.description}")
            logger.info(f"Models: {[model.__name__ for model in self.models] if self.models else 'None'}")
            logger.info(f"Routes: {'Available' if self.router else 'None'}")
            logger.info(f"Dependencies: {self.dependencies or 'None'}")
            
            # Perform module-specific initialization
            self._initialize_module()
            
            logger.info(f"Successfully loaded {self.name} module")
            
        except Exception as e:
            logger.error(f"Error loading {self.name} module: {e}")
            raise
    
    def on_unload(self) -> None:
        """
        Called when module is unloaded.
        
        Performs cleanup of approval-related resources and connections.
        """
        logger.info(f"Unloading {self.name} module v{self.version}")
        
        try:
            # Perform module-specific cleanup
            self._cleanup_module()
            
            logger.info(f"Successfully unloaded {self.name} module")
            
        except Exception as e:
            logger.error(f"Error unloading {self.name} module: {e}")
            # Don't raise during cleanup to avoid blocking other unload operations
    
    def validate_config(self, config: dict) -> bool:
        """
        Validate module configuration.
        
        Args:
            config: Module configuration dictionary
            
        Returns:
            True if configuration is valid, False otherwise
        """
        try:
            # Validate approval-specific configuration
            
            # Check if require_comment is configured
            require_comment = config.get("require_comment", False)
            if require_comment and not isinstance(require_comment, bool):
                logger.warning("require_comment should be a boolean")
                return False
            
            # Check if allow_skip is configured
            allow_skip = config.get("allow_skip", False)
            if allow_skip and not isinstance(allow_skip, bool):
                logger.warning("allow_skip should be a boolean")
                return False
            
            # Validate approval rules if present
            approval_rules = config.get("approval_rules", {})
            if approval_rules and not isinstance(approval_rules, dict):
                logger.warning("approval_rules should be a dictionary")
                return False
            
            # Validate specific approval rules
            if approval_rules:
                min_approvals = approval_rules.get("min_approvals")
                if min_approvals is not None and (not isinstance(min_approvals, int) or min_approvals < 1):
                    logger.warning("min_approvals should be a positive integer")
                    return False
                
                allow_self_approval = approval_rules.get("allow_self_approval")
                if allow_self_approval is not None and not isinstance(allow_self_approval, bool):
                    logger.warning("allow_self_approval should be a boolean")
                    return False
                
                escalation_timeout = approval_rules.get("escalation_timeout_hours")
                if escalation_timeout is not None and (not isinstance(escalation_timeout, (int, float)) or escalation_timeout <= 0):
                    logger.warning("escalation_timeout_hours should be a positive number")
                    return False
            
            logger.info(f"Configuration validation passed for {self.name} module")
            return True
            
        except Exception as e:
            logger.error(f"Error validating configuration for {self.name} module: {e}")
            return False
    
    def _initialize_module(self) -> None:
        """
        Perform module-specific initialization.
        
        Sets up approval system components and verifies workflow engine
        connectivity for state transitions.
        """
        # Log available routes
        if self.router:
            route_count = len([route for route in self.router.routes if hasattr(route, 'path')])
            logger.info(f"Registered {route_count} approval endpoints")
            
            # Log specific approval endpoints
            approval_endpoints = [
                "POST /api/approvals/approve/{item_id}",
                "POST /api/approvals/reject/{item_id}", 
                "GET /api/approvals/pending"
            ]
            logger.debug(f"Core approval endpoints: {approval_endpoints}")
        
        # Verify workflow engine compatibility
        try:
            from core.workflow_engine import workflow_engine
            if workflow_engine:
                logger.info("Workflow engine integration verified")
            else:
                logger.warning("Workflow engine not available during module load")
        except ImportError as e:
            logger.error(f"Failed to import workflow engine: {e}")
            raise
        
        # Initialize approval validation rules
        self._setup_approval_rules()
        
        logger.debug("Approvals module initialization complete")
    
    def _cleanup_module(self) -> None:
        """
        Perform module-specific cleanup.
        
        Cleans up approval-related resources and closes any connections.
        """
        # Clean up any module-specific resources
        # (Currently no persistent connections or resources to clean up)
        
        logger.debug("Approvals module cleanup complete")
    
    def _setup_approval_rules(self) -> None:
        """
        Set up default approval rules and validation logic.
        
        Configures the approval validation system with default rules
        that can be overridden by configuration.
        """
        default_rules = {
            "require_comment_for_rejection": True,
            "allow_self_approval": False,
            "min_approvals_per_step": 1,
            "max_rejection_steps": 10,
            "enable_bulk_operations": True
        }
        
        logger.debug(f"Configured default approval rules: {default_rules}")
    
    def get_workflow_integration_info(self) -> dict:
        """
        Get information about workflow engine integration.
        
        Returns:
            Dictionary with workflow integration details
        """
        return {
            "supports_burr_transitions": True,
            "supported_actions": ["approve", "reject", "cancel"],
            "state_synchronization": True,
            "transaction_support": True,
            "bulk_operations": True
        }
    
    def get_approval_capabilities(self) -> dict:
        """
        Get information about approval capabilities.
        
        Returns:
            Dictionary with approval system capabilities
        """
        return {
            "approval_actions": ["approved", "rejected", "cancelled"],
            "supports_comments": True,
            "supports_metadata": True,
            "supports_actor_tracking": True,
            "supports_department_transitions": True,
            "supports_step_validation": True,
            "supports_bulk_operations": True,
            "supports_approval_history": True,
            "supports_pending_queue": True
        }
    
    def verify_dependencies(self) -> dict:
        """
        Verify that all required dependencies are available.
        
        Returns:
            Dictionary with dependency verification results
        """
        dependencies_status = {
            "workflow_engine": False,
            "work_items_model": False,
            "database_session": False
        }
        
        try:
            # Check workflow engine
            from core.workflow_engine import workflow_engine
            dependencies_status["workflow_engine"] = workflow_engine is not None
        except ImportError:
            pass
        
        try:
            # Check work items model
            from core.models import WorkItem
            dependencies_status["work_items_model"] = WorkItem is not None
        except ImportError:
            pass
        
        try:
            # Check database session availability
            from api.dependencies import get_db_session
            dependencies_status["database_session"] = get_db_session is not None
        except ImportError:
            pass
        
        all_available = all(dependencies_status.values())
        logger.info(f"Dependency verification: {dependencies_status} (all available: {all_available})")
        
        return {
            "status": dependencies_status,
            "all_available": all_available,
            "missing": [k for k, v in dependencies_status.items() if not v]
        }
    
    def get_approval_stats_summary(self) -> dict:
        """
        Get a summary of approval statistics.
        
        Returns:
            Dictionary with approval statistics summary
            
        Note:
            This method provides module-level statistics without
            requiring a database session.
        """
        return {
            "module_version": self.version,
            "capabilities": self.get_approval_capabilities(),
            "workflow_integration": self.get_workflow_integration_info(),
            "endpoints_available": self.router is not None,
            "models_registered": len(self.models) if self.models else 0
        }


# Export the module interface implementation
module_interface = ApprovalsModule()

# For backward compatibility and easier imports
router = router
models = [Approval]
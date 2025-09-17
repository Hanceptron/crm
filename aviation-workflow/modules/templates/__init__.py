"""
Workflow Templates module for the Aviation Workflow System.

Implements the ModuleInterface for pluggable workflow template functionality
allowing users to create, manage, and use reusable workflow configurations.
"""

import logging
from typing import Optional, List, Type
from fastapi import APIRouter
from sqlmodel import SQLModel

from core.plugin_manager import ModuleInterface
from .models import WorkflowTemplate
from .routes import router

logger = logging.getLogger(__name__)


class TemplatesModule(ModuleInterface):
    """
    Templates module implementation following ModuleInterface specification.
    
    Provides workflow template functionality as a pluggable module that allows
    users to create and manage reusable workflow configurations with department
    sequences and approval rules.
    """
    
    # Required attributes as per MODULE INTERFACE SPECIFICATION
    name: str = "templates"
    version: str = "1.0.0"
    description: str = "Workflow template management for reusable workflow configurations"
    
    # Optional components
    router: Optional[APIRouter] = router
    models: Optional[List[Type[SQLModel]]] = [WorkflowTemplate]
    dependencies: Optional[List[str]] = ["departments"]  # Depends on departments for validation
    
    def on_load(self) -> None:
        """
        Called when module is loaded.
        
        Performs initialization including template system setup
        and workflow integration verification.
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
        
        Performs cleanup of template-related resources.
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
            # Validate template-specific configuration
            
            # Check default template category
            default_category = config.get("default_template_category", "general")
            if not isinstance(default_category, str):
                logger.warning("default_template_category should be a string")
                return False
            
            # Check max templates per user
            max_templates_per_user = config.get("max_templates_per_user", 100)
            if not isinstance(max_templates_per_user, int) or max_templates_per_user <= 0:
                logger.warning("max_templates_per_user should be a positive integer")
                return False
            
            # Check template validation settings
            validation_config = config.get("validation", {})
            if validation_config and not isinstance(validation_config, dict):
                logger.warning("validation should be a dictionary")
                return False
            
            if validation_config:
                require_dept_validation = validation_config.get("require_department_validation", True)
                if not isinstance(require_dept_validation, bool):
                    logger.warning("validation.require_department_validation should be a boolean")
                    return False
                
                allow_empty_sequences = validation_config.get("allow_empty_sequences", False)
                if not isinstance(allow_empty_sequences, bool):
                    logger.warning("validation.allow_empty_sequences should be a boolean")
                    return False
            
            # Check template categories
            allowed_categories = config.get("allowed_categories")
            if allowed_categories is not None:
                if not isinstance(allowed_categories, list):
                    logger.warning("allowed_categories should be a list")
                    return False
                
                if not all(isinstance(cat, str) for cat in allowed_categories):
                    logger.warning("All categories in allowed_categories should be strings")
                    return False
            
            # Check approval rules defaults
            default_approval_rules = config.get("default_approval_rules", {})
            if not isinstance(default_approval_rules, dict):
                logger.warning("default_approval_rules should be a dictionary")
                return False
            
            if default_approval_rules:
                # Validate specific approval rule defaults
                min_approvals = default_approval_rules.get("min_approvals_per_step")
                if min_approvals is not None and (not isinstance(min_approvals, int) or min_approvals < 1):
                    logger.warning("default_approval_rules.min_approvals_per_step should be a positive integer")
                    return False
            
            logger.info(f"Configuration validation passed for {self.name} module")
            return True
            
        except Exception as e:
            logger.error(f"Error validating configuration for {self.name} module: {e}")
            return False
    
    def _initialize_module(self) -> None:
        """
        Perform module-specific initialization.
        
        Sets up template system components and validates dependencies.
        """
        # Log available routes
        if self.router:
            route_count = len([route for route in self.router.routes if hasattr(route, 'path')])
            logger.info(f"Registered {route_count} template endpoints")
            
            # Log specific template endpoints
            template_endpoints = [
                "POST /api/templates",
                "GET /api/templates",
                "GET /api/templates/active",
                "GET /api/templates/{template_id}",
                "PUT /api/templates/{template_id}",
                "DELETE /api/templates/{template_id}",
                "POST /api/templates/validate",
                "GET /api/templates/default/{category}",
                "GET /api/templates/stats"
            ]
            logger.debug(f"Core template endpoints: {template_endpoints}")
        
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
        
        # Initialize default template rules
        self._setup_default_template_rules()
        
        logger.debug("Templates module initialization complete")
    
    def _cleanup_module(self) -> None:
        """
        Perform module-specific cleanup.
        
        Cleans up template-related resources.
        """
        # Clean up any module-specific resources
        # (Currently no persistent connections or resources to clean up)
        
        logger.debug("Templates module cleanup complete")
    
    def _setup_default_template_rules(self) -> None:
        """
        Set up default template rules and validation logic.
        
        Configures the template system with default rules
        that can be overridden by configuration.
        """
        default_rules = {
            "default_category": "general",
            "require_department_sequence": True,
            "allow_duplicate_names": False,
            "max_department_sequence_length": 20,
            "default_approval_rules": {
                "require_comment_for_rejection": True,
                "min_approvals_per_step": 1,
                "allow_skip_steps": False,
                "escalation_timeout_hours": 72
            },
            "template_versioning": {
                "auto_increment_version": True,
                "preserve_old_versions": True
            }
        }
        
        logger.debug(f"Configured default template rules: {default_rules}")
    
    def get_template_capabilities(self) -> dict:
        """
        Get information about template capabilities.
        
        Returns:
            Dictionary with template system capabilities
        """
        return {
            "template_features": [
                "department_sequences",
                "approval_rules",
                "workflow_config",
                "template_categories",
                "version_management",
                "usage_tracking",
                "default_templates",
                "template_validation"
            ],
            "supports_validation": True,
            "supports_categories": True,
            "supports_versioning": True,
            "supports_usage_tracking": True,
            "supports_default_templates": True,
            "supports_approval_rules": True,
            "supports_workflow_config": True,
            "max_department_sequence": 50,
            "template_categories": [
                "general", "engineering", "quality", "operations", 
                "maintenance", "safety", "compliance", "administrative"
            ],
            "approval_rule_types": [
                "min_approvals_per_step",
                "require_comment_for_rejection", 
                "allow_skip_steps",
                "escalation_timeout_hours"
            ]
        }
    
    def get_workflow_integration_info(self) -> dict:
        """
        Get information about workflow engine integration.
        
        Returns:
            Dictionary with workflow integration details
        """
        return {
            "supports_burr_workflows": True,
            "workflow_template_types": ["sequential_approval"],
            "department_based_routing": True,
            "dynamic_workflow_creation": True,
            "workflow_state_validation": True,
            "approval_state_transitions": True,
            "rejection_routing": True,
            "cancellation_support": True
        }
    
    def get_template_stats_summary(self) -> dict:
        """
        Get a summary of template statistics.
        
        Returns:
            Dictionary with template statistics summary
            
        Note:
            This method provides module-level statistics without
            requiring a database session.
        """
        return {
            "module_version": self.version,
            "capabilities": self.get_template_capabilities(),
            "workflow_integration": self.get_workflow_integration_info(),
            "endpoints_available": self.router is not None,
            "models_registered": len(self.models) if self.models else 0,
            "depends_on_departments": True,
            "provides_default_templates": True
        }
    
    def verify_dependencies(self) -> dict:
        """
        Verify that all required dependencies are available.
        
        Returns:
            Dictionary with dependency verification results
        """
        dependencies_status = {
            "workflow_engine": False,
            "departments_module": False,
            "database_session": False
        }
        
        try:
            # Check workflow engine
            from core.workflow_engine import workflow_engine
            dependencies_status["workflow_engine"] = workflow_engine is not None
        except ImportError:
            pass
        
        try:
            # Check departments module (optional but recommended)
            from modules.departments.service import DepartmentService
            dependencies_status["departments_module"] = DepartmentService is not None
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
            "missing": [k for k, v in dependencies_status.items() if not v],
            "critical_missing": [k for k, v in dependencies_status.items() 
                               if not v and k in ["workflow_engine", "database_session"]]
        }
    
    def get_integration_info(self) -> dict:
        """
        Get information about module integration capabilities.
        
        Returns:
            Dictionary with integration details
        """
        return {
            "standalone": False,  # Depends on departments module
            "removable": True,    # Can be removed but affects work item creation
            "affects_workflow": True,  # Provides templates for workflow creation
            "affects_state_transitions": False,  # Doesn't affect existing workflows
            "required_by_other_modules": False,  # No other modules require this
            "integration_points": ["work_items", "departments", "workflow_engine"],
            "api_endpoints": 9,   # Number of API endpoints provided
            "database_tables": 1  # Number of database tables
        }
    
    def is_removable(self) -> bool:
        """
        Check if this module can be safely removed.
        
        Returns:
            True if module can be removed (but affects template-based workflow creation)
        """
        # Templates module can be removed, but it will affect the ability
        # to create work items from templates
        return True


# Export the module interface implementation
module_interface = TemplatesModule()

# For backward compatibility and easier imports
router = router
models = [WorkflowTemplate]
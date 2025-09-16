"""
Comments module for the Aviation Workflow System.

Implements the ModuleInterface for pluggable comment functionality
allowing users to add, view, update, and delete comments on work items.
"""

import logging
from typing import Optional, List, Type
from fastapi import APIRouter
from sqlmodel import SQLModel

from core.plugin_manager import ModuleInterface
from .models import Comment
from .routes import router

logger = logging.getLogger(__name__)


class CommentsModule(ModuleInterface):
    """
    Comments module implementation following ModuleInterface specification.
    
    Provides comment functionality as a pluggable module that allows
    users to add notes and discussions to work items.
    """
    
    # Required attributes as per MODULE INTERFACE SPECIFICATION
    name: str = "comments"
    version: str = "1.0.0"
    description: str = "Comment and discussion module for work item collaboration"
    
    # Optional components
    router: Optional[APIRouter] = router
    models: Optional[List[Type[SQLModel]]] = [Comment]
    dependencies: Optional[List[str]] = None  # No module dependencies required
    
    def on_load(self) -> None:
        """
        Called when module is loaded.
        
        Performs initialization including comment system setup
        and database table verification.
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
        
        Performs cleanup of comment-related resources.
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
            # Validate comment-specific configuration
            
            # Check if max_comment_length is configured
            max_comment_length = config.get("max_comment_length", 5000)
            if not isinstance(max_comment_length, int) or max_comment_length <= 0:
                logger.warning("max_comment_length should be a positive integer")
                return False
            
            # Check if allow_replies is configured
            allow_replies = config.get("allow_replies", True)
            if not isinstance(allow_replies, bool):
                logger.warning("allow_replies should be a boolean")
                return False
            
            # Check if require_author is configured
            require_author = config.get("require_author", True)
            if not isinstance(require_author, bool):
                logger.warning("require_author should be a boolean")
                return False
            
            # Validate comment types if configured
            allowed_comment_types = config.get("allowed_comment_types")
            if allowed_comment_types is not None:
                if not isinstance(allowed_comment_types, list):
                    logger.warning("allowed_comment_types should be a list")
                    return False
                
                # Check that all types are strings
                if not all(isinstance(ct, str) for ct in allowed_comment_types):
                    logger.warning("All comment types should be strings")
                    return False
            
            # Validate moderation settings if present
            moderation = config.get("moderation", {})
            if moderation and not isinstance(moderation, dict):
                logger.warning("moderation should be a dictionary")
                return False
            
            if moderation:
                enable_moderation = moderation.get("enabled", False)
                if not isinstance(enable_moderation, bool):
                    logger.warning("moderation.enabled should be a boolean")
                    return False
                
                auto_hide_flagged = moderation.get("auto_hide_flagged", False)
                if not isinstance(auto_hide_flagged, bool):
                    logger.warning("moderation.auto_hide_flagged should be a boolean")
                    return False
            
            logger.info(f"Configuration validation passed for {self.name} module")
            return True
            
        except Exception as e:
            logger.error(f"Error validating configuration for {self.name} module: {e}")
            return False
    
    def _initialize_module(self) -> None:
        """
        Perform module-specific initialization.
        
        Sets up comment system components and validates dependencies.
        """
        # Log available routes
        if self.router:
            route_count = len([route for route in self.router.routes if hasattr(route, 'path')])
            logger.info(f"Registered {route_count} comment endpoints")
            
            # Log specific comment endpoints
            comment_endpoints = [
                "POST /api/comments",
                "GET /api/comments/work-item/{work_item_id}",
                "GET /api/comments/{comment_id}",
                "PUT /api/comments/{comment_id}",
                "DELETE /api/comments/{comment_id}"
            ]
            logger.debug(f"Core comment endpoints: {comment_endpoints}")
        
        # Initialize comment system rules
        self._setup_comment_rules()
        
        logger.debug("Comments module initialization complete")
    
    def _cleanup_module(self) -> None:
        """
        Perform module-specific cleanup.
        
        Cleans up comment-related resources.
        """
        # Clean up any module-specific resources
        # (Currently no persistent connections or resources to clean up)
        
        logger.debug("Comments module cleanup complete")
    
    def _setup_comment_rules(self) -> None:
        """
        Set up default comment rules and validation logic.
        
        Configures the comment system with default rules
        that can be overridden by configuration.
        """
        default_rules = {
            "max_comment_length": 5000,
            "allow_replies": True,
            "require_author": True,
            "allow_editing": True,
            "allow_deletion": True,
            "enable_threading": True,
            "max_thread_depth": 10
        }
        
        logger.debug(f"Configured default comment rules: {default_rules}")
    
    def get_comment_capabilities(self) -> dict:
        """
        Get information about comment capabilities.
        
        Returns:
            Dictionary with comment system capabilities
        """
        return {
            "comment_types": [
                "general", "review", "note", "question", "clarification",
                "technical", "business", "escalation"
            ],
            "supports_threading": True,
            "supports_replies": True,
            "supports_editing": True,
            "supports_deletion": True,
            "supports_internal_comments": True,
            "supports_metadata": True,
            "supports_search": True,
            "supports_bulk_operations": True,
            "max_comment_length": 5000,
            "supports_author_tracking": True
        }
    
    def get_comment_stats_summary(self) -> dict:
        """
        Get a summary of comment statistics.
        
        Returns:
            Dictionary with comment statistics summary
            
        Note:
            This method provides module-level statistics without
            requiring a database session.
        """
        return {
            "module_version": self.version,
            "capabilities": self.get_comment_capabilities(),
            "endpoints_available": self.router is not None,
            "models_registered": len(self.models) if self.models else 0,
            "standalone_module": True,
            "removable": True
        }
    
    def verify_dependencies(self) -> dict:
        """
        Verify that all required dependencies are available.
        
        Returns:
            Dictionary with dependency verification results
        """
        dependencies_status = {
            "work_items_model": False,
            "database_session": False
        }
        
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
    
    def get_integration_info(self) -> dict:
        """
        Get information about module integration capabilities.
        
        Returns:
            Dictionary with integration details
        """
        return {
            "standalone": True,
            "removable": True,
            "affects_workflow": False,
            "affects_state_transitions": False,
            "required_by_other_modules": False,
            "integration_points": ["work_items"],
            "api_endpoints": 8,  # Number of API endpoints provided
            "database_tables": 1  # Number of database tables
        }
    
    def is_removable(self) -> bool:
        """
        Check if this module can be safely removed.
        
        Returns:
            True if module can be removed without affecting other components
        """
        # Comments module is completely standalone and can be removed
        # without affecting workflows or other modules
        return True


# Export the module interface implementation
module_interface = CommentsModule()

# For backward compatibility and easier imports
router = router
models = [Comment]
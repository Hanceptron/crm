"""
Departments module for the Aviation Workflow System.

Implements the ModuleInterface for pluggable department management
functionality following the architecture specification exactly.
"""

import logging
from typing import Optional, List, Type
from fastapi import APIRouter
from sqlmodel import SQLModel

from core.plugin_manager import ModuleInterface
from .models import Department
from .routes import router

logger = logging.getLogger(__name__)


class DepartmentsModule(ModuleInterface):
    """
    Departments module implementation following ModuleInterface specification.
    
    Provides department management functionality as a pluggable module
    that can be loaded and unloaded dynamically.
    """
    
    # Required attributes as per MODULE INTERFACE SPECIFICATION
    name: str = "departments"
    version: str = "1.0.0"
    description: str = "Department management module for organizing workflow approvals"
    
    # Optional components
    router: Optional[APIRouter] = router
    models: Optional[List[Type[SQLModel]]] = [Department]
    dependencies: Optional[List[str]] = None  # No dependencies for departments module
    
    def on_load(self) -> None:
        """
        Called when module is loaded.
        
        Performs any necessary initialization when the module is loaded
        by the plugin manager.
        """
        logger.info(f"Loading {self.name} module v{self.version}")
        
        try:
            # Log module configuration
            logger.info(f"Module: {self.name}")
            logger.info(f"Description: {self.description}")
            logger.info(f"Models: {[model.__name__ for model in self.models] if self.models else 'None'}")
            logger.info(f"Routes: {'Available' if self.router else 'None'}")
            logger.info(f"Dependencies: {self.dependencies or 'None'}")
            
            # Perform any module-specific initialization
            self._initialize_module()
            
            logger.info(f"Successfully loaded {self.name} module")
            
        except Exception as e:
            logger.error(f"Error loading {self.name} module: {e}")
            raise
    
    def on_unload(self) -> None:
        """
        Called when module is unloaded.
        
        Performs cleanup when the module is being unloaded by the
        plugin manager.
        """
        logger.info(f"Unloading {self.name} module v{self.version}")
        
        try:
            # Perform any module-specific cleanup
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
            # Validate any required configuration for departments module
            
            # Check if auto_create_defaults is configured
            auto_create = config.get("auto_create_defaults", False)
            if auto_create and not isinstance(auto_create, bool):
                logger.warning("auto_create_defaults should be a boolean")
                return False
            
            # Check default_departments configuration
            default_departments = config.get("default_departments", [])
            if default_departments and not isinstance(default_departments, list):
                logger.warning("default_departments should be a list")
                return False
            
            # Validate each default department
            for dept in default_departments:
                if not isinstance(dept, dict):
                    logger.warning("Each default department should be a dictionary")
                    return False
                
                if "name" not in dept or "code" not in dept:
                    logger.warning("Each default department must have 'name' and 'code'")
                    return False
            
            logger.info(f"Configuration validation passed for {self.name} module")
            return True
            
        except Exception as e:
            logger.error(f"Error validating configuration for {self.name} module: {e}")
            return False
    
    def _initialize_module(self) -> None:
        """
        Perform module-specific initialization.
        
        This method is called during on_load() to handle any specific
        initialization logic for the departments module.
        """
        # Log available routes
        if self.router:
            route_count = len([route for route in self.router.routes if hasattr(route, 'path')])
            logger.info(f"Registered {route_count} department endpoints")
        
        # Initialize any module-specific resources
        logger.debug("Departments module initialization complete")
    
    def _cleanup_module(self) -> None:
        """
        Perform module-specific cleanup.
        
        This method is called during on_unload() to handle any specific
        cleanup logic for the departments module.
        """
        # Clean up any module-specific resources
        logger.debug("Departments module cleanup complete")
    
    def get_default_departments(self) -> List[dict]:
        """
        Get list of default departments for initialization.
        
        Returns:
            List of default department configurations
        """
        return [
            {
                "name": "Engineering",
                "code": "ENG",
                "description": "Engineering department responsible for technical reviews and design approval",
                "metadata": {
                    "type": "technical",
                    "priority_level": 1,
                    "approval_authority": "technical_specifications"
                }
            },
            {
                "name": "Quality Control", 
                "code": "QC",
                "description": "Quality Control department ensuring compliance with standards",
                "metadata": {
                    "type": "quality",
                    "priority_level": 2,
                    "approval_authority": "quality_standards"
                }
            },
            {
                "name": "Operations",
                "code": "OPS", 
                "description": "Operations department managing deployment and execution",
                "metadata": {
                    "type": "operational",
                    "priority_level": 3,
                    "approval_authority": "operational_deployment"
                }
            }
        ]
    
    def create_default_departments_if_needed(self, session) -> None:
        """
        Create default departments if they don't exist.
        
        Args:
            session: Database session
        """
        from .service import DepartmentService
        from .schemas import DepartmentCreate
        
        try:
            service = DepartmentService(session)
            
            # Check if any departments exist
            existing_count = service.count()
            if existing_count > 0:
                logger.info("Departments already exist, skipping default creation")
                return
            
            # Create default departments
            default_depts = self.get_default_departments()
            created_count = 0
            
            for dept_config in default_depts:
                try:
                    dept_data = DepartmentCreate(**dept_config)
                    service.create(dept_data)
                    created_count += 1
                    logger.info(f"Created default department: {dept_config['code']}")
                except Exception as e:
                    logger.error(f"Failed to create default department {dept_config['code']}: {e}")
            
            logger.info(f"Created {created_count} default departments")
            
        except Exception as e:
            logger.error(f"Error creating default departments: {e}")


# Export the module interface implementation
module_interface = DepartmentsModule()

# For backward compatibility and easier imports
router = router
models = [Department]
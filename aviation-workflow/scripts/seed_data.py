#!/usr/bin/env python3
"""
Database seeding script for the Aviation Workflow System.

Creates realistic sample data including departments, workflow templates,
work items, and comments to demonstrate system functionality.
"""

import sys
import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
from sqlmodel import create_engine, Session, select, text
from sqlalchemy import inspect
import random

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import settings
from core.database import DatabaseManager
from core.plugin_manager import PluginManager

# Import models
from core.models import WorkItem
from modules.departments.models import Department
from modules.templates.models import WorkflowTemplate
from modules.comments.models import Comment

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def check_database_connection():
    """Test database connection."""
    try:
        engine = create_engine(settings.database_url)
        
        with engine.connect() as conn:
            if settings.database_url.startswith("sqlite"):
                result = conn.execute(text("SELECT 1"))
            else:
                result = conn.execute(text("SELECT version()"))
            
            result.fetchone()
            logger.info("✅ Database connection successful")
            return True
            
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False


def check_existing_data():
    """Check if database already has sample data."""
    try:
        db_manager = DatabaseManager()
        engine = db_manager.get_engine()
        
        with Session(engine) as session:
            # Check for existing departments
            departments = session.exec(select(Department)).all()
            work_items = session.exec(select(WorkItem)).all()
            
            return len(departments) > 0 or len(work_items) > 0
            
    except Exception as e:
        logger.error(f"Error checking existing data: {e}")
        return False


def get_existing_tables():
    """Get list of existing tables in the database."""
    try:
        engine = create_engine(settings.database_url)
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        return tables
    except Exception as e:
        logger.error(f"Error getting existing tables: {e}")
        return []


def load_required_modules():
    """Load required modules for seeding."""
    try:
        plugin_manager = PluginManager()
        
        required_modules = ['departments', 'templates', 'comments']
        loaded_modules = []
        
        for module_name in required_modules:
            try:
                logger.info(f"🔄 Loading module: {module_name}")
                module_interface = plugin_manager.load_module(module_name)
                
                if module_interface:
                    loaded_modules.append(module_name)
                    logger.info(f"✅ Successfully loaded module: {module_name}")
                else:
                    logger.warning(f"⚠️  Module {module_name} returned None")
                    
            except Exception as e:
                logger.error(f"❌ Failed to load module {module_name}: {e}")
                continue
        
        logger.info(f"✅ Loaded {len(loaded_modules)} modules: {', '.join(loaded_modules)}")
        return loaded_modules
        
    except Exception as e:
        logger.error(f"❌ Error loading modules: {e}")
        return []


def create_sample_departments(session: Session) -> List[Department]:
    """Create 5 sample aviation departments."""
    logger.info("🏢 Creating sample departments...")
    
    departments_data = [
        {
            "name": "flight_operations",
            "display_name": "Flight Operations",
            "description": "Manages flight planning, crew scheduling, and operational oversight",
            "manager": "Captain Sarah Mitchell",
            "contact_email": "flight.ops@aviation.com",
            "phone": "+1-555-0101",
            "location": "Operations Center, Building A"
        },
        {
            "name": "maintenance",
            "display_name": "Aircraft Maintenance",
            "description": "Responsible for aircraft maintenance, inspections, and airworthiness",
            "manager": "Chief Engineer Robert Chen",
            "contact_email": "maintenance@aviation.com", 
            "phone": "+1-555-0102",
            "location": "Maintenance Hangar, Building C"
        },
        {
            "name": "safety_quality",
            "display_name": "Safety & Quality Assurance",
            "description": "Ensures safety compliance, quality standards, and regulatory adherence",
            "manager": "Safety Director Maria Rodriguez",
            "contact_email": "safety@aviation.com",
            "phone": "+1-555-0103",
            "location": "Safety Office, Building B"
        },
        {
            "name": "ground_services",
            "display_name": "Ground Services",
            "description": "Handles baggage, cargo, fueling, and ground support operations",
            "manager": "Ground Supervisor James Wilson",
            "contact_email": "ground@aviation.com",
            "phone": "+1-555-0104", 
            "location": "Ground Operations, Terminal 1"
        },
        {
            "name": "customer_service",
            "display_name": "Customer Service",
            "description": "Manages passenger services, complaints, and customer experience",
            "manager": "Service Director Lisa Thompson",
            "contact_email": "service@aviation.com",
            "phone": "+1-555-0105",
            "location": "Customer Service Center, Terminal 2"
        }
    ]
    
    departments = []
    for dept_data in departments_data:
        try:
            department = Department(**dept_data)
            session.add(department)
            departments.append(department)
            logger.info(f"  📝 Created department: {department.display_name}")
        except Exception as e:
            logger.error(f"  ❌ Failed to create department {dept_data['name']}: {e}")
    
    session.commit()
    logger.info(f"✅ Created {len(departments)} departments")
    return departments


def create_sample_templates(session: Session, departments: List[Department]) -> List[WorkflowTemplate]:
    """Create 3 workflow templates with different department sequences."""
    logger.info("📋 Creating workflow templates...")
    
    dept_names = [dept.name for dept in departments]
    
    templates_data = [
        {
            "name": "aircraft_maintenance_workflow",
            "display_name": "Aircraft Maintenance Workflow",
            "description": "Standard workflow for aircraft maintenance requests and approvals",
            "department_sequence": ["maintenance", "safety_quality", "flight_operations"],
            "approval_rules": {
                "require_comment": True,
                "min_approvals": 2,
                "allow_parallel_approval": False,
                "escalation_hours": 24
            },
            "workflow_config": {
                "timeout": 7200,  # 2 hours
                "auto_approve_minor": False,
                "require_supervisor_approval": True
            },
            "category": "maintenance",
            "created_by": "system_admin"
        },
        {
            "name": "safety_incident_workflow", 
            "display_name": "Safety Incident Reporting",
            "description": "Workflow for processing safety incidents and corrective actions",
            "department_sequence": ["safety_quality", "flight_operations", "maintenance"],
            "approval_rules": {
                "require_comment": True,
                "min_approvals": 1,
                "allow_parallel_approval": True,
                "escalation_hours": 4
            },
            "workflow_config": {
                "timeout": 3600,  # 1 hour
                "auto_approve_minor": False,
                "require_supervisor_approval": True,
                "priority": "high"
            },
            "category": "safety",
            "created_by": "safety_admin"
        },
        {
            "name": "customer_complaint_workflow",
            "display_name": "Customer Complaint Resolution",
            "description": "Standard process for handling customer complaints and feedback",
            "department_sequence": ["customer_service", "ground_services"],
            "approval_rules": {
                "require_comment": False,
                "min_approvals": 1,
                "allow_parallel_approval": True,
                "escalation_hours": 48
            },
            "workflow_config": {
                "timeout": 14400,  # 4 hours
                "auto_approve_minor": True,
                "require_supervisor_approval": False
            },
            "category": "customer_service",
            "created_by": "service_admin"
        }
    ]
    
    templates = []
    for template_data in templates_data:
        try:
            template = WorkflowTemplate(**template_data)
            session.add(template)
            templates.append(template)
            logger.info(f"  📝 Created template: {template.display_name}")
            logger.info(f"      → Department sequence: {' → '.join(template.department_sequence)}")
        except Exception as e:
            logger.error(f"  ❌ Failed to create template {template_data['name']}: {e}")
    
    session.commit()
    logger.info(f"✅ Created {len(templates)} workflow templates")
    return templates


def create_sample_work_items(session: Session, departments: List[Department], templates: List[WorkflowTemplate]) -> List[WorkItem]:
    """Create 10 sample work items in various states."""
    logger.info("📄 Creating sample work items...")
    
    # Define realistic aviation work items
    work_items_data = [
        {
            "title": "Engine Inspection Required - Aircraft N123AB",
            "description": "Routine 100-hour engine inspection needed before next scheduled flight",
            "priority": "high",
            "template": "aircraft_maintenance_workflow",
            "current_step": 1,
            "status": "in_progress"
        },
        {
            "title": "Passenger Complaint - Flight AA456 Delay",
            "description": "Customer complaint regarding 3-hour delay without proper communication",
            "priority": "medium",
            "template": "customer_complaint_workflow", 
            "current_step": 0,
            "status": "pending"
        },
        {
            "title": "Safety Incident - Ground Equipment Collision",
            "description": "Baggage cart collided with aircraft during loading operations",
            "priority": "high",
            "template": "safety_incident_workflow",
            "current_step": 2,
            "status": "in_progress"
        },
        {
            "title": "Fuel System Maintenance - Aircraft N789CD",
            "description": "Scheduled fuel system inspection and component replacement",
            "priority": "medium",
            "template": "aircraft_maintenance_workflow",
            "current_step": 0,
            "status": "pending"
        },
        {
            "title": "Lost Baggage Report - Flight BB789",
            "description": "Passenger's luggage missing after connecting flight",
            "priority": "low",
            "template": "customer_complaint_workflow",
            "current_step": 1,
            "status": "approved"
        },
        {
            "title": "Runway Incursion Investigation",
            "description": "Investigation into unauthorized vehicle on runway during landing",
            "priority": "critical",
            "template": "safety_incident_workflow",
            "current_step": 0,
            "status": "pending"
        },
        {
            "title": "Hydraulic System Repair - Aircraft N456EF",
            "description": "Hydraulic leak detected during pre-flight inspection",
            "priority": "critical",
            "template": "aircraft_maintenance_workflow",
            "current_step": 2,
            "status": "completed"
        },
        {
            "title": "Catering Service Complaint - Flight CC123",
            "description": "Multiple passengers reported food quality issues",
            "priority": "medium",
            "template": "customer_complaint_workflow",
            "current_step": 0,
            "status": "rejected"
        },
        {
            "title": "Weather Radar Calibration - Aircraft N678GH",
            "description": "Annual weather radar system calibration and testing",
            "priority": "low",
            "template": "aircraft_maintenance_workflow",
            "current_step": 1,
            "status": "in_progress"
        },
        {
            "title": "Bird Strike Damage Assessment",
            "description": "Aircraft sustained bird strike during takeoff, damage assessment needed",
            "priority": "high",
            "template": "safety_incident_workflow",
            "current_step": 1,
            "status": "in_progress"
        }
    ]
    
    # Create template lookup
    template_lookup = {t.name: t for t in templates}
    
    work_items = []
    for i, item_data in enumerate(work_items_data):
        try:
            template = template_lookup[item_data["template"]]
            
            # Calculate dates
            created_date = datetime.utcnow() - timedelta(days=random.randint(1, 30))
            due_date = created_date + timedelta(days=random.randint(1, 14))
            
            # Create work item
            work_item = WorkItem(
                title=item_data["title"],
                description=item_data["description"],
                priority=item_data["priority"],
                status=item_data["status"],
                department_ids=template.department_sequence.copy(),
                current_step=item_data["current_step"],
                created_by=f"user_{i+1}@aviation.com",
                assigned_to=f"manager_{random.randint(1, 5)}@aviation.com",
                due_date=due_date,
                created_at=created_date,
                updated_at=created_date + timedelta(hours=random.randint(1, 48)),
                item_metadata={
                    "template_id": template.id,
                    "template_name": template.name,
                    "aircraft_tail": item_data.get("aircraft_tail", f"N{random.randint(100, 999)}{chr(65+random.randint(0, 25))}{chr(65+random.randint(0, 25))}"),
                    "location": random.choice(["KORD", "KLAX", "KJFK", "KATL", "KDEN"]),
                    "estimated_hours": random.randint(1, 8)
                }
            )
            
            session.add(work_item)
            work_items.append(work_item)
            logger.info(f"  📝 Created work item: {work_item.title[:50]}...")
            
        except Exception as e:
            logger.error(f"  ❌ Failed to create work item {item_data['title']}: {e}")
    
    session.commit()
    logger.info(f"✅ Created {len(work_items)} work items")
    return work_items


def create_sample_comments(session: Session, work_items: List[WorkItem], departments: List[Department]) -> List[Comment]:
    """Add sample comments and approval history to work items."""
    logger.info("💬 Creating sample comments...")
    
    comment_templates = [
        "Initial assessment completed. Moving to next department for approval.",
        "Additional documentation required before proceeding.",
        "Approved after review. All safety requirements met.",
        "Rejected due to insufficient information. Please provide more details.",
        "Escalating to supervisor for urgent review.",
        "Work completed successfully. Closing item.",
        "Partial approval granted. Conditional on additional testing.",
        "Delayed due to parts availability. Estimated completion: next week.",
        "Quality check passed. Ready for final approval.",
        "Customer has been notified of resolution."
    ]
    
    comment_types = ["status_update", "approval", "rejection", "question", "resolution"]
    
    comments = []
    for work_item in work_items:
        # Create 1-4 comments per work item
        num_comments = random.randint(1, 4)
        
        for i in range(num_comments):
            try:
                comment_date = work_item.created_at + timedelta(
                    hours=random.randint(1, 48 * (i + 1))
                )
                
                comment = Comment(
                    work_item_id=work_item.id,
                    content=random.choice(comment_templates),
                    comment_type=random.choice(comment_types),
                    created_by=f"user_{random.randint(1, 10)}@aviation.com",
                    department_id=random.choice([dept.id for dept in departments]),
                    created_at=comment_date,
                    is_internal=random.choice([True, False]),
                    metadata={
                        "approval_status": random.choice(["pending", "approved", "rejected"]) if random.random() > 0.5 else None,
                        "priority_change": random.choice(["low", "medium", "high"]) if random.random() > 0.8 else None,
                        "estimated_completion": comment_date + timedelta(hours=random.randint(1, 72))
                    }
                )
                
                session.add(comment)
                comments.append(comment)
                
            except Exception as e:
                logger.error(f"  ❌ Failed to create comment for work item {work_item.id}: {e}")
    
    session.commit()
    logger.info(f"✅ Created {len(comments)} comments across all work items")
    return comments


def show_seeding_summary(departments: List[Department], templates: List[WorkflowTemplate], 
                        work_items: List[WorkItem], comments: List[Comment]):
    """Display summary of seeded data."""
    print("\n" + "=" * 60)
    print("📊 SAMPLE DATA SUMMARY")
    print("=" * 60)
    
    print(f"🏢 Departments Created: {len(departments)}")
    for dept in departments:
        print(f"   • {dept.display_name} ({dept.name})")
    
    print(f"\n📋 Workflow Templates: {len(templates)}")
    for template in templates:
        print(f"   • {template.display_name}")
        print(f"     → Sequence: {' → '.join(template.department_sequence)}")
    
    print(f"\n📄 Work Items: {len(work_items)}")
    status_counts = {}
    priority_counts = {}
    for item in work_items:
        status_counts[item.status] = status_counts.get(item.status, 0) + 1
        priority_counts[item.priority] = priority_counts.get(item.priority, 0) + 1
    
    print("   Status Distribution:")
    for status, count in status_counts.items():
        print(f"     • {status}: {count}")
    
    print("   Priority Distribution:")
    for priority, count in priority_counts.items():
        print(f"     • {priority}: {count}")
    
    print(f"\n💬 Comments: {len(comments)}")
    print(f"   Average per work item: {len(comments) / len(work_items):.1f}")
    
    print("=" * 60)


def main():
    """Main seeding function."""
    print("🌱 Aviation Workflow System - Database Seeding")
    print("=" * 60)
    
    # Check database connection
    logger.info("🔌 Testing database connection...")
    if not check_database_connection():
        logger.error("❌ Cannot connect to database. Check your configuration.")
        return 1
    
    # Check for existing data
    if check_existing_data():
        response = input("\n❓ Database already contains data. Continue with seeding? (y/N): ")
        if response.lower() not in ['y', 'yes']:
            logger.info("⏭️  Skipping data seeding")
            return 0
        
        # Ask about clearing existing data
        response = input("❓ Clear existing data before seeding? (y/N): ")
        if response.lower() in ['y', 'yes']:
            logger.info("🗑️  Clearing existing data...")
            # Note: In production, you might want to be more selective about what to clear
    
    # Load required modules
    logger.info("🔌 Loading required modules...")
    loaded_modules = load_required_modules()
    
    required_modules = ['departments', 'templates', 'comments']
    missing_modules = [m for m in required_modules if m not in loaded_modules]
    
    if missing_modules:
        logger.error(f"❌ Missing required modules: {', '.join(missing_modules)}")
        logger.error("   Please ensure all required modules are enabled and available.")
        return 1
    
    # Verify tables exist
    tables = get_existing_tables()
    required_tables = ['departments', 'workflow_templates', 'work_items', 'comments']
    missing_tables = [t for t in required_tables if t not in tables]
    
    if missing_tables:
        logger.error(f"❌ Missing required tables: {', '.join(missing_tables)}")
        logger.error("   Please run 'python scripts/init_db.py' first to create tables.")
        return 1
    
    try:
        # Create database session
        db_manager = DatabaseManager()
        engine = db_manager.get_engine()
        
        with Session(engine) as session:
            # Create sample data
            departments = create_sample_departments(session)
            templates = create_sample_templates(session, departments)
            work_items = create_sample_work_items(session, departments, templates)
            comments = create_sample_comments(session, work_items, departments)
            
            # Show summary
            show_seeding_summary(departments, templates, work_items, comments)
            
    except Exception as e:
        logger.error(f"❌ Error during data seeding: {e}")
        return 1
    
    logger.info("🎉 Database seeding completed successfully!")
    
    print("\n" + "💡 NEXT STEPS:")
    print("  1. Run 'python scripts/run_dev.py' to start the development server")
    print("  2. Visit the API docs at http://localhost:8000/docs")
    print("  3. Check the Streamlit dashboard at http://localhost:8501")
    
    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("\n⚠️  Database seeding interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        sys.exit(1)
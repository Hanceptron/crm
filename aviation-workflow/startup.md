# 🚀 Aviation Workflow System - Startup Guide

A comprehensive guide to get the Aviation Workflow System up and running, including testing procedures.

## 📋 Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [System Testing](#system-testing)
- [Manual Testing Guide](#manual-testing-guide)
- [API Testing](#api-testing)
- [Troubleshooting](#troubleshooting)
- [Production Deployment](#production-deployment)
- [Success Metrics](#success-metrics)

---

## 🛠️ Prerequisites

### System Requirements
- **Python 3.11+** (required)
- **8GB RAM** (recommended)
- **SQLite** (development) or **PostgreSQL** (production)
- **Modern web browser** (Chrome, Firefox, Safari, Edge)

### Check Your Python Version
```bash
python3 --version
# Should show Python 3.11.x or higher
```

---

## ⚡ Quick Start

### Step 1: Navigate to Project Directory
```bash
cd /Users/emirhan/Documents/Projects/CRM/aviation-workflow
```

### Step 2: Create Virtual Environment (Recommended)
```bash
# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate     # Windows
```

### Step 3: Install Dependencies
```bash
# Upgrade pip first
pip install --upgrade pip

# Core dependencies (including pydantic-settings fix)
pip install fastapi[all] uvicorn sqlmodel streamlit burr pydantic pydantic-settings python-dotenv

# Optional testing dependencies
pip install requests psutil pytest
```

### Step 4: Environment Setup
```bash
# Create environment file
cat > .env << 'EOF'
# Database Configuration
DATABASE_URL="sqlite:///./workflow.db"

# Module Configuration
ENABLED_MODULES="departments,templates,comments,approvals"

# API Configuration
API_PREFIX="/api"
CORS_ORIGINS="http://localhost:8501"

# Environment Settings
APP_ENV="development"
DEBUG=true
LOG_LEVEL="INFO"
EOF
```

### Step 5: Initialize Database
```bash
# Create database schema
echo "🗄️  Initializing database..."
python scripts/init_db.py

# Seed with sample data
echo "🌱 Adding sample data..."
python scripts/seed_data.py
```

### Step 6: Start the System
```bash
# Option A: Start both services together
echo "🚀 Starting Aviation Workflow System..."
python scripts/run_dev.py

# Option B: Start services separately (use 2 terminals)
# Terminal 1 - API Server
uvicorn api.main:app --host localhost --port 8000 --reload

# Terminal 2 - UI Dashboard
streamlit run ui/app.py --server.port 8501
```

### Step 7: Verify System is Running
Open your browser to:

- **✈️ Main Dashboard**: http://localhost:8501
- **📚 API Documentation**: http://localhost:8000/docs
- **❤️ Health Check**: http://localhost:8000/health

---

## 🧪 System Testing

### Automated Test Suite

Run these tests in order to validate system functionality:

#### 1. Structure Validation
```bash
echo "🔍 Testing system structure..."
python scripts/validate_mvp_simple.py
```
**Expected**: 100% success rate (9/9 tests passed)

#### 2. Module Independence Test
```bash
echo "🔗 Testing module independence..."
python scripts/test_module_independence.py
```
**Expected**: Core system works with each module disabled

#### 3. Complete Workflow Test
```bash
echo "🔄 Testing complete workflow cycle..."
python scripts/test_complete_workflow.py
```
**Expected**: Full approval cycle through 4 departments

#### 4. Load Testing
```bash
echo "⚡ Running load tests..."
python scripts/load_test.py
```
**Expected**: Handle 100 work items + 50 concurrent approvals

#### 5. Full MVP Validation
```bash
echo "🎯 Running full MVP validation..."
# Requires: pip install psutil requests
python scripts/validate_mvp.py
```
**Expected**: All 8 SUCCESS METRICS validated

---

## 🖱️ Manual Testing Guide

### Dashboard Testing (http://localhost:8501)

#### Page 1: 📋 Dashboard
1. **Navigate to Dashboard**
   - Should show work item statistics
   - Department status overview
   - Recent activity feed
   
2. **Verify Data Display**
   - Work items count > 0
   - Department widgets visible
   - Charts/graphs rendering properly

#### Page 2: ➕ Create Item  
1. **Create New Work Item**
   - Fill in title: "Test Work Item"
   - Add description: "Manual testing item"
   - Select priority: "High"
   - Choose workflow template
   
2. **Submit and Verify**
   - Click "Create Work Item"
   - Should see success message
   - Item should appear in dashboard

#### Page 3: ✅ Approvals
1. **Find Pending Items**
   - Should show items waiting for approval
   - View item details
   
2. **Test Approval Process**
   - Select a work item
   - Add approval comment
   - Click "Approve" 
   - Verify state change

3. **Test Rejection Process**
   - Select another item
   - Add rejection reason
   - Choose "Reject to previous step"
   - Verify item moves back

#### Page 4: 📊 Reports
1. **View Analytics**
   - Processing time charts
   - Department performance metrics
   - Workflow statistics
   
2. **Verify Data Accuracy**
   - Numbers match dashboard
   - Charts update with new data

---

## 🔌 API Testing

### Basic Health Checks
```bash
# System health
curl http://localhost:8000/health
# Expected: {"status": "healthy", "timestamp": "..."}

# API documentation
curl http://localhost:8000/docs
# Expected: HTML response with Swagger UI
```

### Core Endpoints Testing
```bash
# List all work items
curl http://localhost:8000/api/work-items | python -m json.tool

# Get specific work item
curl http://localhost:8000/api/work-items/{item-id} | python -m json.tool

# List departments  
curl http://localhost:8000/api/departments | python -m json.tool

# List workflow templates
curl http://localhost:8000/api/templates | python -m json.tool
```

### Create Work Item via API
```bash
# Create new work item
curl -X POST http://localhost:8000/api/work-items \
  -H "Content-Type: application/json" \
  -d '{
    "title": "API Test Work Item",
    "description": "Testing via API",
    "priority": "high",
    "workflow_template": "standard",
    "created_by": "tester@aviation.com"
  }' | python -m json.tool
```

### Test Approval Process
```bash
# Approve work item (replace {item-id} with actual ID)
curl -X POST http://localhost:8000/api/work-items/{item-id}/approve \
  -H "Content-Type: application/json" \
  -d '{
    "action": "approve",
    "comment": "API approval test",
    "approved_by": "tester@aviation.com"
  }' | python -m json.tool
```

---

## 🚨 Troubleshooting

### Common Issues and Solutions

#### 🔴 Port Already in Use
```bash
# Check what's using the ports
lsof -i :8000
lsof -i :8501

# Kill processes if needed
lsof -ti:8000 | xargs kill -9
lsof -ti:8501 | xargs kill -9

# Restart services
python scripts/run_dev.py
```

#### 🔴 Database Issues
```bash
# Complete database reset
echo "🗄️ Resetting database..."
rm -f workflow.db burr_state.db
python scripts/init_db.py
python scripts/seed_data.py
echo "✅ Database reset complete"
```

#### 🔴 Module Loading Errors
```bash
# Check current module configuration
python -c "
from core.config import settings
print('Enabled modules:', settings.enabled_modules)
print('Database URL:', settings.database_url)
"

# Reset module configuration
echo 'ENABLED_MODULES="departments,templates,comments,approvals"' >> .env
```

#### 🔴 Python Import Errors
```bash
# Verify you're using virtual environment
echo "Virtual environment: $VIRTUAL_ENV"
which python3

# If not in virtual environment, activate it:
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Reinstall dependencies with pydantic-settings fix
pip install --upgrade pip
pip install --force-reinstall fastapi[all] uvicorn sqlmodel streamlit burr pydantic pydantic-settings python-dotenv requests psutil
```

#### 🔴 Streamlit UI Errors
```bash
# If you see TypeError or AttributeError in Streamlit pages
# The UI has been fixed to handle various data types properly

# Check if all UI files have valid syntax
python3 -c "
import ast
files = ['ui/app.py', 'ui/pages/1_📋_Dashboard.py', 'ui/pages/2_➕_Create_Item.py', 'ui/pages/3_✅_Approvals.py', 'ui/pages/4_📊_Reports.py']
for f in files:
    try:
        ast.parse(open(f).read())
        print(f'✅ {f}: OK')
    except Exception as e:
        print(f'❌ {f}: {e}')
"
```

#### 🔴 Virtual Environment Issues
```bash
# Deactivate and recreate virtual environment
deactivate
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt  # if available
# or install dependencies manually as shown above
```

### 🔍 Diagnostic Commands
```bash
# Check system status
echo "🔍 System Diagnostic"
echo "==================="
echo "Python version: $(python3 --version)"
echo "Current directory: $(pwd)"
echo "Virtual environment: $VIRTUAL_ENV"
echo "Database file exists: $(test -f workflow.db && echo 'Yes' || echo 'No')"
echo "API accessible: $(curl -s http://localhost:8000/health >/dev/null && echo 'Yes' || echo 'No')"
echo "UI accessible: $(curl -s http://localhost:8501 >/dev/null && echo 'Yes' || echo 'No')"
```

---

## 🚢 Production Deployment

### Environment Configuration
```bash
# Production environment file
cat > .env.production << 'EOF'
APP_ENV="production"
DEBUG=false
DATABASE_URL="postgresql://user:password@localhost:5432/aviation_workflow"
CORS_ORIGINS="https://your-domain.com"
LOG_LEVEL="WARNING"
ENABLED_MODULES="departments,templates,comments,approvals"
EOF
```

### Production Services
```bash
# API Server with multiple workers
uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4

# Streamlit with production settings
streamlit run ui/app.py \
  --server.port 8501 \
  --server.address 0.0.0.0 \
  --server.headless true
```

### Docker Deployment (if available)
```bash
# Build and start all services
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

---

## 🎯 Success Metrics

The system validates these **8 SUCCESS METRICS** from architecture.md:

### ✅ Core Functionality
1. **Work Item with 3+ Departments** - Workflow supports department sequences
2. **Approval State Changes** - Real-time state updates
3. **Rejection to Previous Steps** - Flexible backward workflow

### ✅ Architecture
4. **Module Independence** - 6 pluggable modules can be disabled
5. **Burr State Tracking** - Workflow engine manages all transitions
6. **Streamlit Visualization** - Complete UI with workflow diagrams

### ✅ Performance  
7. **8GB RAM Efficiency** - Lightweight design with SQLite + FastAPI
8. **System Resilience** - Core functions work without any module

### Validation Commands
```bash
# Quick structure check
python scripts/validate_mvp_simple.py

# Full system validation
python scripts/validate_mvp.py

# Performance testing
python scripts/load_test.py
```

---

## 🎉 System Ready Checklist

- [ ] ✅ Python 3.11+ installed
- [ ] ✅ Virtual environment activated  
- [ ] ✅ Dependencies installed
- [ ] ✅ Database initialized with sample data
- [ ] ✅ API server running on port 8000
- [ ] ✅ Streamlit UI running on port 8501
- [ ] ✅ Health check returns healthy status
- [ ] ✅ Can create and approve work items
- [ ] ✅ All modules loading correctly
- [ ] ✅ Automated tests passing

### Final Verification
```bash
echo "🎯 Final System Check"
echo "===================="
echo "API Health: $(curl -s http://localhost:8000/health | grep -o '"status":"[^"]*"' || echo 'FAILED')"
echo "UI Status: $(curl -s -o /dev/null -w '%{http_code}' http://localhost:8501)"
echo "Work Items: $(curl -s http://localhost:8000/api/work-items | python -c "import json,sys; print(len(json.load(sys.stdin)))" 2>/dev/null || echo 'N/A')"
echo ""
echo "🚀 Aviation Workflow System is ready for use!"
echo "   Dashboard: http://localhost:8501"
echo "   API Docs:  http://localhost:8000/docs"
```

---

## 🆘 Getting Help

### System Information
- **Architecture**: See `architecture.md` for detailed system design
- **User Guide**: See `README.md` for development workflows  
- **API Reference**: http://localhost:8000/docs (when running)

### Support Resources
- **Health Endpoint**: http://localhost:8000/health
- **System Logs**: Check console output from `run_dev.py`
- **Database**: SQLite browser tools can inspect `workflow.db`

**Built for the aviation industry with ❤️ and ✈️**
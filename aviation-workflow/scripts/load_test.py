#!/usr/bin/env python3
"""
Load Testing Script for Aviation Workflow System

Tests system performance with:
- 100 work items
- 50 concurrent approvals
- Memory usage monitoring (should stay under 1GB)
"""

import sys
import os
import subprocess
import time
import requests
import threading
import psutil
import statistics
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import json

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class LoadTester:
    """Load testing class for the aviation workflow system."""
    
    def __init__(self, api_base_url: str = "http://localhost:8000"):
        self.api_base_url = api_base_url
        self.api_process = None
        self.test_departments = []
        self.test_template = None
        self.created_work_items = []
        self.performance_metrics = {
            "memory_usage": [],
            "response_times": [],
            "success_count": 0,
            "error_count": 0,
            "start_time": None,
            "end_time": None
        }
        self.memory_monitor_active = False
    
    def start_api_server(self) -> bool:
        """Start the API server for testing."""
        print("🚀 Starting API server for load testing...")
        
        # Start uvicorn server with multiple workers for better performance
        self.api_process = subprocess.Popen([
            sys.executable, "-m", "uvicorn", 
            "api.main:app", 
            "--host", "localhost", 
            "--port", "8000",
            "--workers", "2"  # Multiple workers for better performance
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Wait for server to start
        for _ in range(30):
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
                self.api_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.api_process.kill()
            print("🛑 API server stopped")
    
    def monitor_memory_usage(self):
        """Monitor memory usage during testing."""
        print("📊 Starting memory monitoring...")
        self.memory_monitor_active = True
        
        while self.memory_monitor_active:
            try:
                # Get current process memory usage
                process = psutil.Process(os.getpid())
                memory_mb = process.memory_info().rss / 1024 / 1024
                
                # Also monitor API server if we can find it
                api_memory = 0
                for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                    try:
                        if proc.info['cmdline'] and 'uvicorn' in ' '.join(proc.info['cmdline']):
                            api_memory += proc.memory_info().rss / 1024 / 1024
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                
                total_memory = memory_mb + api_memory
                self.performance_metrics["memory_usage"].append({
                    "timestamp": datetime.now().isoformat(),
                    "test_script_mb": memory_mb,
                    "api_server_mb": api_memory,
                    "total_mb": total_memory
                })
                
                # Print memory usage every 10 seconds during high load
                if len(self.performance_metrics["memory_usage"]) % 20 == 0:
                    print(f"  💾 Memory: Test={memory_mb:.1f}MB, API={api_memory:.1f}MB, Total={total_memory:.1f}MB")
                
            except Exception as e:
                print(f"  ⚠️  Memory monitoring error: {e}")
            
            time.sleep(0.5)  # Monitor every 500ms
    
    def setup_load_test_data(self) -> bool:
        """Set up departments and template for load testing."""
        print("📋 Setting up load test data...")
        
        # Create test departments
        departments_data = [
            {"name": "load_test_dept_1", "display_name": "Load Test Dept 1", "contact_email": "dept1@loadtest.com"},
            {"name": "load_test_dept_2", "display_name": "Load Test Dept 2", "contact_email": "dept2@loadtest.com"},
            {"name": "load_test_dept_3", "display_name": "Load Test Dept 3", "contact_email": "dept3@loadtest.com"}
        ]
        
        for dept_data in departments_data:
            try:
                response = requests.post(f"{self.api_base_url}/api/departments", json=dept_data, timeout=10)
                if response.status_code == 201:
                    dept = response.json()
                    self.test_departments.append(dept)
                    print(f"  ✅ Created department: {dept['display_name']}")
                elif response.status_code == 400 and "already exists" in response.text:
                    # Department exists, get it
                    get_response = requests.get(f"{self.api_base_url}/api/departments")
                    if get_response.status_code == 200:
                        existing_depts = get_response.json()
                        for existing_dept in existing_depts:
                            if existing_dept['name'] == dept_data['name']:
                                self.test_departments.append(existing_dept)
                                print(f"  ℹ️  Using existing department: {existing_dept['display_name']}")
                                break
                else:
                    print(f"  ❌ Failed to create department: {response.text}")
                    return False
            except Exception as e:
                print(f"  ❌ Error creating department: {e}")
                return False
        
        # Create test template
        template_data = {
            "name": "load_test_template",
            "display_name": "Load Test Template",
            "description": "Template for load testing",
            "department_sequence": [dept["name"] for dept in self.test_departments],
            "approval_rules": {"require_comment": False, "min_approvals": 1},
            "category": "load_test",
            "created_by": "load_tester@aviation.com"
        }
        
        try:
            response = requests.post(f"{self.api_base_url}/api/templates", json=template_data, timeout=10)
            if response.status_code == 201:
                self.test_template = response.json()
                print(f"  ✅ Created template: {self.test_template['display_name']}")
                return True
            else:
                print(f"  ❌ Failed to create template: {response.text}")
                return False
        except Exception as e:
            print(f"  ❌ Error creating template: {e}")
            return False
    
    def create_work_item(self, item_index: int) -> Tuple[bool, float]:
        """Create a single work item and measure response time."""
        start_time = time.time()
        
        work_item_data = {
            "title": f"Load Test Work Item {item_index + 1}",
            "description": f"Load testing work item number {item_index + 1}",
            "priority": ["low", "medium", "high"][item_index % 3],
            "template_id": self.test_template["id"],
            "created_by": f"load_tester_{item_index}@aviation.com",
            "metadata": {
                "test_type": "load_test",
                "item_index": item_index,
                "aircraft_tail": f"N{100 + item_index}LT"
            }
        }
        
        try:
            response = requests.post(f"{self.api_base_url}/api/work-items", json=work_item_data, timeout=30)
            response_time = time.time() - start_time
            
            if response.status_code == 201:
                work_item = response.json()
                self.created_work_items.append(work_item)
                return True, response_time
            else:
                print(f"  ❌ Failed to create work item {item_index + 1}: {response.text}")
                return False, response_time
        except Exception as e:
            response_time = time.time() - start_time
            print(f"  ❌ Error creating work item {item_index + 1}: {e}")
            return False, response_time
    
    def approve_work_item(self, work_item: Dict[str, Any], approval_index: int) -> Tuple[bool, float]:
        """Approve a work item and measure response time."""
        start_time = time.time()
        
        try:
            # Add approval comment
            comment_data = {
                "work_item_id": work_item["id"],
                "content": f"Load test approval {approval_index + 1}",
                "comment_type": "approval",
                "created_by": f"load_approver_{approval_index}@aviation.com",
                "department_id": self.test_departments[0]["id"]  # Always approve from first department
            }
            
            comment_response = requests.post(f"{self.api_base_url}/api/comments", json=comment_data, timeout=30)
            
            if comment_response.status_code != 201:
                response_time = time.time() - start_time
                return False, response_time
            
            # Update work item status
            update_data = {
                "current_step": 1,
                "status": "in_progress"
            }
            
            update_response = requests.put(
                f"{self.api_base_url}/api/work-items/{work_item['id']}", 
                json=update_data, 
                timeout=30
            )
            
            response_time = time.time() - start_time
            
            if update_response.status_code == 200:
                return True, response_time
            else:
                return False, response_time
        
        except Exception as e:
            response_time = time.time() - start_time
            print(f"  ❌ Error approving work item: {e}")
            return False, response_time
    
    def run_load_test_create_items(self) -> bool:
        """Create 100 work items with performance monitoring."""
        print("📝 Creating 100 work items...")
        
        # Start memory monitoring
        memory_thread = threading.Thread(target=self.monitor_memory_usage)
        memory_thread.daemon = True
        memory_thread.start()
        
        self.performance_metrics["start_time"] = datetime.now()
        
        # Create work items with threading for better performance
        success_count = 0
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(self.create_work_item, i) for i in range(100)]
            
            for i, future in enumerate(as_completed(futures)):
                try:
                    success, response_time = future.result()
                    self.performance_metrics["response_times"].append(response_time)
                    
                    if success:
                        success_count += 1
                        self.performance_metrics["success_count"] += 1
                    else:
                        self.performance_metrics["error_count"] += 1
                    
                    # Progress indicator
                    if (i + 1) % 20 == 0:
                        print(f"  📊 Created {i + 1}/100 work items (Success: {success_count}, Avg time: {statistics.mean(self.performance_metrics['response_times']):.2f}s)")
                
                except Exception as e:
                    print(f"  ❌ Error in work item creation: {e}")
                    self.performance_metrics["error_count"] += 1
        
        print(f"✅ Completed creating work items: {success_count}/100 successful")
        return success_count >= 95  # 95% success rate threshold
    
    def run_load_test_concurrent_approvals(self) -> bool:
        """Run 50 concurrent approvals."""
        print("✅ Running 50 concurrent approvals...")
        
        if len(self.created_work_items) < 50:
            print(f"❌ Not enough work items for concurrent approvals (have {len(self.created_work_items)}, need 50)")
            return False
        
        # Select first 50 work items for approval
        items_to_approve = self.created_work_items[:50]
        
        approval_success_count = 0
        approval_start_time = time.time()
        
        # Run concurrent approvals
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(self.approve_work_item, item, i) for i, item in enumerate(items_to_approve)]
            
            for i, future in enumerate(as_completed(futures)):
                try:
                    success, response_time = future.result()
                    self.performance_metrics["response_times"].append(response_time)
                    
                    if success:
                        approval_success_count += 1
                        self.performance_metrics["success_count"] += 1
                    else:
                        self.performance_metrics["error_count"] += 1
                    
                    # Progress indicator
                    if (i + 1) % 10 == 0:
                        elapsed = time.time() - approval_start_time
                        print(f"  📊 Completed {i + 1}/50 approvals (Success: {approval_success_count}, Elapsed: {elapsed:.1f}s)")
                
                except Exception as e:
                    print(f"  ❌ Error in approval: {e}")
                    self.performance_metrics["error_count"] += 1
        
        self.performance_metrics["end_time"] = datetime.now()
        
        # Stop memory monitoring
        self.memory_monitor_active = False
        
        print(f"✅ Completed concurrent approvals: {approval_success_count}/50 successful")
        return approval_success_count >= 45  # 90% success rate threshold
    
    def analyze_performance_results(self) -> Dict[str, Any]:
        """Analyze performance test results."""
        print("📊 Analyzing performance results...")
        
        # Calculate response time statistics
        response_times = self.performance_metrics["response_times"]
        memory_usage = self.performance_metrics["memory_usage"]
        
        if not response_times:
            print("❌ No response time data available")
            return {}
        
        # Response time analysis
        avg_response_time = statistics.mean(response_times)
        median_response_time = statistics.median(response_times)
        p95_response_time = sorted(response_times)[int(len(response_times) * 0.95)] if response_times else 0
        max_response_time = max(response_times)
        min_response_time = min(response_times)
        
        # Memory analysis
        max_memory = 0
        avg_memory = 0
        if memory_usage:
            max_memory = max(m["total_mb"] for m in memory_usage)
            avg_memory = statistics.mean(m["total_mb"] for m in memory_usage)
        
        # Test duration
        test_duration = 0
        if self.performance_metrics["start_time"] and self.performance_metrics["end_time"]:
            test_duration = (self.performance_metrics["end_time"] - self.performance_metrics["start_time"]).total_seconds()
        
        # Success rate
        total_operations = self.performance_metrics["success_count"] + self.performance_metrics["error_count"]
        success_rate = (self.performance_metrics["success_count"] / total_operations * 100) if total_operations > 0 else 0
        
        results = {
            "total_operations": total_operations,
            "success_count": self.performance_metrics["success_count"],
            "error_count": self.performance_metrics["error_count"],
            "success_rate_percent": success_rate,
            "test_duration_seconds": test_duration,
            "response_times": {
                "average_seconds": avg_response_time,
                "median_seconds": median_response_time,
                "p95_seconds": p95_response_time,
                "max_seconds": max_response_time,
                "min_seconds": min_response_time
            },
            "memory_usage": {
                "max_mb": max_memory,
                "average_mb": avg_memory,
                "under_1gb": max_memory < 1024
            },
            "throughput": {
                "operations_per_second": total_operations / test_duration if test_duration > 0 else 0
            }
        }
        
        return results
    
    def generate_load_test_report(self, results: Dict[str, Any]) -> bool:
        """Generate comprehensive load test report."""
        print("\n" + "=" * 60)
        print("📊 LOAD TEST REPORT")
        print("=" * 60)
        
        print(f"🎯 Test Objectives:")
        print(f"  • Create 100 work items")
        print(f"  • Run 50 concurrent approvals")
        print(f"  • Monitor memory usage (target: <1GB)")
        
        print(f"\n📈 Performance Results:")
        print(f"  Total Operations: {results.get('total_operations', 0)}")
        print(f"  Successful: {results.get('success_count', 0)}")
        print(f"  Failed: {results.get('error_count', 0)}")
        print(f"  Success Rate: {results.get('success_rate_percent', 0):.1f}%")
        print(f"  Test Duration: {results.get('test_duration_seconds', 0):.1f} seconds")
        
        response_times = results.get('response_times', {})
        print(f"\n⏱️  Response Times:")
        print(f"  Average: {response_times.get('average_seconds', 0):.3f}s")
        print(f"  Median: {response_times.get('median_seconds', 0):.3f}s")
        print(f"  95th Percentile: {response_times.get('p95_seconds', 0):.3f}s")
        print(f"  Max: {response_times.get('max_seconds', 0):.3f}s")
        print(f"  Min: {response_times.get('min_seconds', 0):.3f}s")
        
        memory_usage = results.get('memory_usage', {})
        print(f"\n💾 Memory Usage:")
        print(f"  Maximum: {memory_usage.get('max_mb', 0):.1f} MB")
        print(f"  Average: {memory_usage.get('average_mb', 0):.1f} MB")
        print(f"  Under 1GB: {'✅ Yes' if memory_usage.get('under_1gb', False) else '❌ No'}")
        
        throughput = results.get('throughput', {})
        print(f"\n🚀 Throughput:")
        print(f"  Operations/second: {throughput.get('operations_per_second', 0):.2f}")
        
        # Performance thresholds
        print(f"\n🎯 Performance Thresholds:")
        thresholds = {
            "Success Rate ≥95%": results.get('success_rate_percent', 0) >= 95,
            "Average Response <2s": response_times.get('average_seconds', 0) < 2.0,
            "P95 Response <5s": response_times.get('p95_seconds', 0) < 5.0,
            "Memory Usage <1GB": memory_usage.get('under_1gb', False),
            "Throughput >10 ops/s": throughput.get('operations_per_second', 0) > 10
        }
        
        passed_thresholds = 0
        for threshold, passed in thresholds.items():
            status = "✅" if passed else "❌"
            print(f"  {status} {threshold}")
            if passed:
                passed_thresholds += 1
        
        overall_success = passed_thresholds >= 4  # At least 4 out of 5 thresholds
        
        print(f"\n📊 LOAD TEST RESULT: {'✅ PASSED' if overall_success else '❌ FAILED'}")
        print(f"   Passed {passed_thresholds}/5 performance thresholds")
        
        if overall_success:
            print(f"\n🎉 SYSTEM PERFORMANCE: EXCELLENT")
            print("   System handles load testing requirements successfully")
        else:
            print(f"\n⚠️  SYSTEM PERFORMANCE: NEEDS OPTIMIZATION")
            print("   Some performance metrics need improvement")
        
        return overall_success


def main():
    """Main load test execution."""
    print("🔬 Aviation Workflow System - Load Testing")
    print("=" * 60)
    
    # Check if we're in the right directory
    if not os.path.exists("api/main.py"):
        print("❌ Error: Run this script from the project root directory")
        return 1
    
    tester = LoadTester()
    
    try:
        # Start API server
        if not tester.start_api_server():
            return 1
        
        # Setup test data
        if not tester.setup_load_test_data():
            return 1
        
        # Run load tests
        print(f"\n🏁 Starting Load Test Sequence...")
        
        create_success = tester.run_load_test_create_items()
        if not create_success:
            print("❌ Work item creation test failed")
            return 1
        
        approval_success = tester.run_load_test_concurrent_approvals()
        if not approval_success:
            print("❌ Concurrent approval test failed")
            return 1
        
        # Analyze results
        results = tester.analyze_performance_results()
        if not results:
            print("❌ Failed to analyze performance results")
            return 1
        
        # Generate report
        overall_success = tester.generate_load_test_report(results)
        
        return 0 if overall_success else 1
    
    except KeyboardInterrupt:
        print(f"\n⚠️  Load test interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Load test failed with error: {e}")
        return 1
    finally:
        tester.stop_api_server()


if __name__ == "__main__":
    sys.exit(main())
#!/usr/bin/env python3
"""
Comprehensive Backend Testing for CodeForge LeetCode/CodeChef Clone
Tests all backend functionality including authentication, problems, submissions, contests, and discussions.
"""

import requests
import json
import time
import os
from typing import Dict, Any, Optional

class CodeForgeBackendTester:
    def __init__(self):
        # Get backend URL from frontend .env file
        self.base_url = self._get_backend_url()
        self.session = requests.Session()
        self.auth_token = None
        self.test_user_data = {
            "username": "testcoder123",
            "email": "testcoder123@example.com", 
            "password": "SecurePass123!"
        }
        self.test_results = []
        
    def _get_backend_url(self) -> str:
        """Get backend URL from frontend .env file"""
        try:
            with open('/app/frontend/.env', 'r') as f:
                for line in f:
                    if line.startswith('REACT_APP_BACKEND_URL='):
                        backend_url = line.split('=', 1)[1].strip()
                        return f"{backend_url}/api"
            return "http://localhost:8001/api"  # fallback
        except Exception as e:
            print(f"Warning: Could not read frontend .env file: {e}")
            return "http://localhost:8001/api"  # fallback
    
    def log_test(self, test_name: str, success: bool, message: str = "", details: Any = None):
        """Log test results"""
        status = "✅ PASS" if success else "❌ FAIL"
        result = {
            "test": test_name,
            "status": status,
            "success": success,
            "message": message,
            "details": details
        }
        self.test_results.append(result)
        print(f"{status}: {test_name}")
        if message:
            print(f"    {message}")
        if not success and details:
            print(f"    Details: {details}")
        print()
    
    def make_request(self, method: str, endpoint: str, data: Dict = None, headers: Dict = None) -> requests.Response:
        """Make HTTP request with proper error handling"""
        url = f"{self.base_url}{endpoint}"
        request_headers = {"Content-Type": "application/json"}
        
        if self.auth_token:
            request_headers["Authorization"] = f"Bearer {self.auth_token}"
        
        if headers:
            request_headers.update(headers)
        
        try:
            if method.upper() == "GET":
                response = self.session.get(url, headers=request_headers, timeout=10)
            elif method.upper() == "POST":
                response = self.session.post(url, json=data, headers=request_headers, timeout=10)
            elif method.upper() == "PUT":
                response = self.session.put(url, json=data, headers=request_headers, timeout=10)
            elif method.upper() == "DELETE":
                response = self.session.delete(url, headers=request_headers, timeout=10)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            return response
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            raise
    
    def test_health_check(self):
        """Test basic API health check"""
        try:
            response = self.make_request("GET", "/")
            if response.status_code == 200:
                data = response.json()
                if "message" in data and "status" in data:
                    self.log_test("Health Check", True, f"API is healthy: {data['message']}")
                    return True
                else:
                    self.log_test("Health Check", False, "Invalid health check response format", data)
                    return False
            else:
                self.log_test("Health Check", False, f"HTTP {response.status_code}", response.text)
                return False
        except Exception as e:
            self.log_test("Health Check", False, f"Connection failed: {str(e)}")
            return False
    
    def test_user_registration(self):
        """Test user registration functionality"""
        try:
            response = self.make_request("POST", "/auth/register", self.test_user_data)
            
            if response.status_code == 200:
                data = response.json()
                if "access_token" in data and "user" in data:
                    self.auth_token = data["access_token"]
                    user_info = data["user"]
                    expected_fields = ["id", "username", "email", "total_solved", "created_at"]
                    
                    if all(field in user_info for field in expected_fields):
                        self.log_test("User Registration", True, f"User registered successfully: {user_info['username']}")
                        return True
                    else:
                        missing_fields = [f for f in expected_fields if f not in user_info]
                        self.log_test("User Registration", False, f"Missing user fields: {missing_fields}", data)
                        return False
                else:
                    self.log_test("User Registration", False, "Missing access_token or user in response", data)
                    return False
            elif response.status_code == 400:
                # User might already exist, try login instead
                return self.test_user_login()
            else:
                self.log_test("User Registration", False, f"HTTP {response.status_code}", response.text)
                return False
        except Exception as e:
            self.log_test("User Registration", False, f"Registration failed: {str(e)}")
            return False
    
    def test_user_login(self):
        """Test user login functionality"""
        try:
            login_data = {
                "email": self.test_user_data["email"],
                "password": self.test_user_data["password"]
            }
            response = self.make_request("POST", "/auth/login", login_data)
            
            if response.status_code == 200:
                data = response.json()
                if "access_token" in data and "user" in data:
                    self.auth_token = data["access_token"]
                    user_info = data["user"]
                    self.log_test("User Login", True, f"Login successful: {user_info['username']}")
                    return True
                else:
                    self.log_test("User Login", False, "Missing access_token or user in response", data)
                    return False
            else:
                self.log_test("User Login", False, f"HTTP {response.status_code}", response.text)
                return False
        except Exception as e:
            self.log_test("User Login", False, f"Login failed: {str(e)}")
            return False
    
    def test_protected_endpoint_auth(self):
        """Test that protected endpoints require authentication"""
        try:
            # Save current token
            original_token = self.auth_token
            
            # Test without token
            self.auth_token = None
            response = self.make_request("GET", "/auth/me")
            
            if response.status_code == 401:
                self.log_test("Protected Endpoint Auth", True, "Correctly rejected unauthenticated request")
                # Restore token
                self.auth_token = original_token
                return True
            else:
                self.log_test("Protected Endpoint Auth", False, f"Should return 401, got {response.status_code}")
                # Restore token
                self.auth_token = original_token
                return False
        except Exception as e:
            self.log_test("Protected Endpoint Auth", False, f"Auth test failed: {str(e)}")
            return False
    
    def test_get_current_user(self):
        """Test getting current user information"""
        try:
            response = self.make_request("GET", "/auth/me")
            
            if response.status_code == 200:
                data = response.json()
                expected_fields = ["id", "username", "email", "total_solved", "easy_solved", "medium_solved", "hard_solved"]
                
                if all(field in data for field in expected_fields):
                    self.log_test("Get Current User", True, f"User info retrieved: {data['username']}")
                    return True
                else:
                    missing_fields = [f for f in expected_fields if f not in data]
                    self.log_test("Get Current User", False, f"Missing fields: {missing_fields}", data)
                    return False
            else:
                self.log_test("Get Current User", False, f"HTTP {response.status_code}", response.text)
                return False
        except Exception as e:
            self.log_test("Get Current User", False, f"Get user failed: {str(e)}")
            return False
    
    def test_get_problems_list(self):
        """Test retrieving problems list"""
        try:
            response = self.make_request("GET", "/problems")
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and len(data) > 0:
                    problem = data[0]
                    expected_fields = ["id", "number", "title", "description", "difficulty", "tags", "examples"]
                    
                    if all(field in problem for field in expected_fields):
                        self.log_test("Get Problems List", True, f"Retrieved {len(data)} problems")
                        return True, data
                    else:
                        missing_fields = [f for f in expected_fields if f not in problem]
                        self.log_test("Get Problems List", False, f"Missing problem fields: {missing_fields}", problem)
                        return False, None
                else:
                    self.log_test("Get Problems List", False, "No problems found or invalid format", data)
                    return False, None
            else:
                self.log_test("Get Problems List", False, f"HTTP {response.status_code}", response.text)
                return False, None
        except Exception as e:
            self.log_test("Get Problems List", False, f"Get problems failed: {str(e)}")
            return False, None
    
    def test_get_individual_problem(self, problem_id: str):
        """Test retrieving individual problem"""
        try:
            response = self.make_request("GET", f"/problems/{problem_id}")
            
            if response.status_code == 200:
                data = response.json()
                expected_fields = ["id", "number", "title", "description", "difficulty", "tags", "examples", "starter_code"]
                
                if all(field in data for field in expected_fields):
                    self.log_test("Get Individual Problem", True, f"Problem retrieved: {data['title']}")
                    return True, data
                else:
                    missing_fields = [f for f in expected_fields if f not in data]
                    self.log_test("Get Individual Problem", False, f"Missing fields: {missing_fields}", data)
                    return False, None
            else:
                self.log_test("Get Individual Problem", False, f"HTTP {response.status_code}", response.text)
                return False, None
        except Exception as e:
            self.log_test("Get Individual Problem", False, f"Get problem failed: {str(e)}")
            return False, None
    
    def test_code_execution(self, problem_id: str):
        """Test code execution functionality"""
        try:
            # Simple Python code that should work
            test_code = """
def two_sum(nums, target):
    for i in range(len(nums)):
        for j in range(i + 1, len(nums)):
            if nums[i] + nums[j] == target:
                return [i, j]
    return []

# Test with example input
nums = [2, 7, 11, 15]
target = 9
result = two_sum(nums, target)
print(result)
"""
            
            execution_data = {
                "problem_id": problem_id,
                "language": "python",
                "code": test_code,
                "test_input": ""
            }
            
            response = self.make_request("POST", "/code/run", execution_data)
            
            if response.status_code == 200:
                data = response.json()
                expected_fields = ["status", "output"]
                
                if all(field in data for field in expected_fields):
                    self.log_test("Code Execution", True, f"Code executed: {data['status']}")
                    return True, data
                else:
                    missing_fields = [f for f in expected_fields if f not in data]
                    self.log_test("Code Execution", False, f"Missing fields: {missing_fields}", data)
                    return False, None
            else:
                self.log_test("Code Execution", False, f"HTTP {response.status_code}", response.text)
                return False, None
        except Exception as e:
            self.log_test("Code Execution", False, f"Code execution failed: {str(e)}")
            return False, None
    
    def test_code_submission(self, problem_id: str):
        """Test code submission functionality"""
        try:
            # Simple Python solution for Two Sum
            solution_code = """
def two_sum(nums, target):
    num_map = {}
    for i, num in enumerate(nums):
        complement = target - num
        if complement in num_map:
            return [num_map[complement], i]
        num_map[num] = i
    return []

# For the submission system
nums = [2, 7, 11, 15]
target = 9
result = two_sum(nums, target)
print(result)
"""
            
            submission_data = {
                "problem_id": problem_id,
                "language": "python",
                "code": solution_code
            }
            
            response = self.make_request("POST", "/code/submit", submission_data)
            
            if response.status_code == 200:
                data = response.json()
                expected_fields = ["id", "status", "passed_test_cases", "total_test_cases"]
                
                if all(field in data for field in expected_fields):
                    self.log_test("Code Submission", True, f"Submission created: {data['status']}")
                    return True, data
                else:
                    missing_fields = [f for f in expected_fields if f not in data]
                    self.log_test("Code Submission", False, f"Missing fields: {missing_fields}", data)
                    return False, None
            else:
                self.log_test("Code Submission", False, f"HTTP {response.status_code}", response.text)
                return False, None
        except Exception as e:
            self.log_test("Code Submission", False, f"Code submission failed: {str(e)}")
            return False, None
    
    def test_user_statistics(self):
        """Test user statistics retrieval"""
        try:
            response = self.make_request("GET", "/users/stats")
            
            if response.status_code == 200:
                data = response.json()
                expected_fields = ["total_problems", "solved_problems", "easy_solved", "medium_solved", "hard_solved", "acceptance_rate"]
                
                if all(field in data for field in expected_fields):
                    self.log_test("User Statistics", True, f"Stats retrieved - Solved: {data['solved_problems']}/{data['total_problems']}")
                    return True, data
                else:
                    missing_fields = [f for f in expected_fields if f not in data]
                    self.log_test("User Statistics", False, f"Missing fields: {missing_fields}", data)
                    return False, None
            else:
                self.log_test("User Statistics", False, f"HTTP {response.status_code}", response.text)
                return False, None
        except Exception as e:
            self.log_test("User Statistics", False, f"Get stats failed: {str(e)}")
            return False, None
    
    def test_contests_list(self):
        """Test contests list retrieval"""
        try:
            response = self.make_request("GET", "/contests")
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    if len(data) > 0:
                        contest = data[0]
                        expected_fields = ["id", "title", "description", "status", "start_time", "duration"]
                        
                        if all(field in contest for field in expected_fields):
                            self.log_test("Contests List", True, f"Retrieved {len(data)} contests")
                            return True, data
                        else:
                            missing_fields = [f for f in expected_fields if f not in contest]
                            self.log_test("Contests List", False, f"Missing contest fields: {missing_fields}", contest)
                            return False, None
                    else:
                        self.log_test("Contests List", True, "No contests found (empty list is valid)")
                        return True, data
                else:
                    self.log_test("Contests List", False, "Invalid response format", data)
                    return False, None
            else:
                self.log_test("Contests List", False, f"HTTP {response.status_code}", response.text)
                return False, None
        except Exception as e:
            self.log_test("Contests List", False, f"Get contests failed: {str(e)}")
            return False, None
    
    def test_discussions_list(self):
        """Test discussions list retrieval"""
        try:
            response = self.make_request("GET", "/discussions")
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    if len(data) > 0:
                        discussion = data[0]
                        expected_fields = ["id", "title", "content", "author_username", "tags", "created_at"]
                        
                        if all(field in discussion for field in expected_fields):
                            self.log_test("Discussions List", True, f"Retrieved {len(data)} discussions")
                            return True, data
                        else:
                            missing_fields = [f for f in expected_fields if f not in discussion]
                            self.log_test("Discussions List", False, f"Missing discussion fields: {missing_fields}", discussion)
                            return False, None
                    else:
                        self.log_test("Discussions List", True, "No discussions found (empty list is valid)")
                        return True, data
                else:
                    self.log_test("Discussions List", False, "Invalid response format", data)
                    return False, None
            else:
                self.log_test("Discussions List", False, f"HTTP {response.status_code}", response.text)
                return False, None
        except Exception as e:
            self.log_test("Discussions List", False, f"Get discussions failed: {str(e)}")
            return False, None
    
    def test_create_discussion(self):
        """Test creating a new discussion"""
        try:
            discussion_data = {
                "title": "Test Discussion - Algorithm Help",
                "content": "I need help understanding dynamic programming concepts. Can someone explain the basic approach?",
                "tags": ["Dynamic Programming", "Help", "Algorithms"]
            }
            
            response = self.make_request("POST", "/discussions", discussion_data)
            
            if response.status_code == 200:
                data = response.json()
                expected_fields = ["id", "title", "content", "author_username", "tags", "created_at"]
                
                if all(field in data for field in expected_fields):
                    self.log_test("Create Discussion", True, f"Discussion created: {data['title']}")
                    return True, data
                else:
                    missing_fields = [f for f in expected_fields if f not in data]
                    self.log_test("Create Discussion", False, f"Missing fields: {missing_fields}", data)
                    return False, None
            else:
                self.log_test("Create Discussion", False, f"HTTP {response.status_code}", response.text)
                return False, None
        except Exception as e:
            self.log_test("Create Discussion", False, f"Create discussion failed: {str(e)}")
            return False, None
    
    def run_all_tests(self):
        """Run all backend tests"""
        print("=" * 60)
        print("CODEFORGE BACKEND TESTING")
        print("=" * 60)
        print(f"Testing backend at: {self.base_url}")
        print()
        
        # Test 1: Health Check
        if not self.test_health_check():
            print("❌ CRITICAL: Backend is not responding. Stopping tests.")
            return self.generate_summary()
        
        # Test 2: User Registration/Login
        auth_success = self.test_user_registration()
        if not auth_success:
            print("❌ CRITICAL: Authentication failed. Stopping tests.")
            return self.generate_summary()
        
        # Test 3: Protected endpoint authentication
        self.test_protected_endpoint_auth()
        
        # Test 4: Get current user
        self.test_get_current_user()
        
        # Test 5: Get problems list
        problems_success, problems_data = self.test_get_problems_list()
        
        # Test 6: Get individual problem (if problems exist)
        if problems_success and problems_data:
            problem_id = problems_data[0]["id"]
            problem_success, problem_data = self.test_get_individual_problem(problem_id)
            
            # Test 7: Code execution (if problem retrieved successfully)
            if problem_success:
                self.test_code_execution(problem_id)
                
                # Test 8: Code submission
                self.test_code_submission(problem_id)
        
        # Test 9: User statistics
        self.test_user_statistics()
        
        # Test 10: Contests
        self.test_contests_list()
        
        # Test 11: Discussions
        self.test_discussions_list()
        
        # Test 12: Create discussion
        self.test_create_discussion()
        
        return self.generate_summary()
    
    def generate_summary(self):
        """Generate test summary"""
        print("=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests*100):.1f}%")
        print()
        
        if failed_tests > 0:
            print("FAILED TESTS:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"❌ {result['test']}: {result['message']}")
            print()
        
        print("DETAILED RESULTS:")
        for result in self.test_results:
            print(f"{result['status']}: {result['test']}")
        
        return {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "success_rate": passed_tests/total_tests*100,
            "results": self.test_results
        }

def main():
    """Main function to run all tests"""
    tester = CodeForgeBackendTester()
    summary = tester.run_all_tests()
    
    # Return exit code based on test results
    if summary["failed_tests"] == 0:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️  {summary['failed_tests']} test(s) failed!")
        return 1

if __name__ == "__main__":
    exit(main())
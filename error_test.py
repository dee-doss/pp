#!/usr/bin/env python3
"""
Additional Backend Error Testing for CodeForge
Tests error scenarios and edge cases.
"""

import requests
import json

def test_error_scenarios():
    base_url = "https://6a973be4-7aab-446a-a805-fa489383395e.preview.emergentagent.com/api"
    
    print("=" * 60)
    print("CODEFORGE BACKEND ERROR SCENARIO TESTING")
    print("=" * 60)
    
    # Test 1: Invalid login credentials
    print("Testing invalid login credentials...")
    response = requests.post(f"{base_url}/auth/login", json={
        "email": "nonexistent@example.com",
        "password": "wrongpassword"
    })
    print(f"Invalid login - Status: {response.status_code} (Expected: 401)")
    print(f"Response: {response.json()}")
    print()
    
    # Test 2: Duplicate user registration
    print("Testing duplicate user registration...")
    user_data = {
        "username": "testcoder123",
        "email": "testcoder123@example.com",
        "password": "SecurePass123!"
    }
    response = requests.post(f"{base_url}/auth/register", json=user_data)
    print(f"Duplicate registration - Status: {response.status_code} (Expected: 400)")
    if response.status_code == 400:
        print(f"Response: {response.json()}")
    print()
    
    # Test 3: Invalid problem ID
    print("Testing invalid problem ID...")
    # First get a valid token
    login_response = requests.post(f"{base_url}/auth/login", json={
        "email": "testcoder123@example.com",
        "password": "SecurePass123!"
    })
    
    if login_response.status_code == 200:
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        response = requests.get(f"{base_url}/problems/invalid-id", headers=headers)
        print(f"Invalid problem ID - Status: {response.status_code} (Expected: 404)")
        if response.status_code == 404:
            print(f"Response: {response.json()}")
        print()
        
        # Test 4: Code execution with invalid problem ID
        print("Testing code execution with invalid problem ID...")
        response = requests.post(f"{base_url}/code/run", json={
            "problem_id": "invalid-id",
            "language": "python",
            "code": "print('hello')"
        }, headers=headers)
        print(f"Invalid problem for code execution - Status: {response.status_code} (Expected: 404)")
        if response.status_code == 404:
            print(f"Response: {response.json()}")
        print()
        
        # Test 5: Code submission with invalid problem ID
        print("Testing code submission with invalid problem ID...")
        response = requests.post(f"{base_url}/code/submit", json={
            "problem_id": "invalid-id",
            "language": "python",
            "code": "print('hello')"
        }, headers=headers)
        print(f"Invalid problem for submission - Status: {response.status_code} (Expected: 404)")
        if response.status_code == 404:
            print(f"Response: {response.json()}")
        print()
        
        # Test 6: Invalid contest ID
        print("Testing invalid contest ID...")
        response = requests.get(f"{base_url}/contests/invalid-id", headers=headers)
        print(f"Invalid contest ID - Status: {response.status_code} (Expected: 404)")
        if response.status_code == 404:
            print(f"Response: {response.json()}")
        print()
    
    print("=" * 60)
    print("ERROR SCENARIO TESTING COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    test_error_scenarios()
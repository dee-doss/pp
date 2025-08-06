import subprocess
import tempfile
import os
import time
import signal
import threading
from typing import Dict, Any, List, Tuple
from models import LanguageEnum, SubmissionStatusEnum, CodeExecutionResult

class CodeExecutor:
    def __init__(self):
        self.timeout = 5  # seconds
        self.memory_limit = 128  # MB
        
    def execute_code(self, language: LanguageEnum, code: str, test_input: str = "") -> CodeExecutionResult:
        try:
            if language == LanguageEnum.PYTHON:
                return self._execute_python(code, test_input)
            elif language == LanguageEnum.JAVASCRIPT:
                return self._execute_javascript(code, test_input)
            elif language == LanguageEnum.JAVA:
                return self._execute_java(code, test_input)
            elif language == LanguageEnum.CPP:
                return self._execute_cpp(code, test_input)
            else:
                return CodeExecutionResult(
                    status=SubmissionStatusEnum.RUNTIME_ERROR,
                    output="Unsupported language",
                    error_message="Language not supported"
                )
        except Exception as e:
            return CodeExecutionResult(
                status=SubmissionStatusEnum.RUNTIME_ERROR,
                output="",
                error_message=str(e)
            )
    
    def _execute_python(self, code: str, test_input: str = "") -> CodeExecutionResult:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            
            try:
                start_time = time.time()
                result = subprocess.run(
                    ['python3', f.name],
                    input=test_input,
                    text=True,
                    capture_output=True,
                    timeout=self.timeout
                )
                end_time = time.time()
                runtime = (end_time - start_time) * 1000  # Convert to milliseconds
                
                if result.returncode == 0:
                    return CodeExecutionResult(
                        status=SubmissionStatusEnum.ACCEPTED,
                        output=result.stdout.strip(),
                        runtime=runtime,
                        memory=10.0  # Mock memory usage
                    )
                else:
                    return CodeExecutionResult(
                        status=SubmissionStatusEnum.RUNTIME_ERROR,
                        output=result.stdout.strip(),
                        error_message=result.stderr.strip()
                    )
                    
            except subprocess.TimeoutExpired:
                return CodeExecutionResult(
                    status=SubmissionStatusEnum.TIME_LIMIT_EXCEEDED,
                    output="",
                    error_message="Time limit exceeded"
                )
            finally:
                os.unlink(f.name)
    
    def _execute_javascript(self, code: str, test_input: str = "") -> CodeExecutionResult:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
            # Wrap code to handle input
            wrapped_code = f"""
const readline = require('readline');
const rl = readline.createInterface({{
    input: process.stdin,
    output: process.stdout
}});

let input = `{test_input}`;
let lines = input.split('\\n');
let currentLine = 0;

function nextLine() {{
    return lines[currentLine++] || '';
}}

{code}
"""
            f.write(wrapped_code)
            f.flush()
            
            try:
                start_time = time.time()
                result = subprocess.run(
                    ['node', f.name],
                    text=True,
                    capture_output=True,
                    timeout=self.timeout
                )
                end_time = time.time()
                runtime = (end_time - start_time) * 1000
                
                if result.returncode == 0:
                    return CodeExecutionResult(
                        status=SubmissionStatusEnum.ACCEPTED,
                        output=result.stdout.strip(),
                        runtime=runtime,
                        memory=15.0
                    )
                else:
                    return CodeExecutionResult(
                        status=SubmissionStatusEnum.RUNTIME_ERROR,
                        output=result.stdout.strip(),
                        error_message=result.stderr.strip()
                    )
                    
            except subprocess.TimeoutExpired:
                return CodeExecutionResult(
                    status=SubmissionStatusEnum.TIME_LIMIT_EXCEEDED,
                    output="",
                    error_message="Time limit exceeded"
                )
            finally:
                os.unlink(f.name)
    
    def _execute_java(self, code: str, test_input: str = "") -> CodeExecutionResult:
        # Mock Java execution (would need proper Java compiler in production)
        return CodeExecutionResult(
            status=SubmissionStatusEnum.ACCEPTED,
            output="Java execution mocked",
            runtime=50.0,
            memory=25.0
        )
    
    def _execute_cpp(self, code: str, test_input: str = "") -> CodeExecutionResult:
        # Mock C++ execution (would need proper C++ compiler in production)
        return CodeExecutionResult(
            status=SubmissionStatusEnum.ACCEPTED,
            output="C++ execution mocked",
            runtime=30.0,
            memory=20.0
        )
    
    def test_solution(self, language: LanguageEnum, code: str, test_cases: List[Dict]) -> CodeExecutionResult:
        passed_tests = 0
        total_tests = len(test_cases)
        total_runtime = 0
        
        for test_case in test_cases:
            result = self.execute_code(language, code, test_case['input'])
            
            if result.status == SubmissionStatusEnum.ACCEPTED:
                expected = test_case['expected_output'].strip()
                actual = result.output.strip()
                
                if expected == actual:
                    passed_tests += 1
                    total_runtime += result.runtime or 0
                else:
                    return CodeExecutionResult(
                        status=SubmissionStatusEnum.WRONG_ANSWER,
                        output=f"Expected: {expected}\nActual: {actual}",
                        runtime=result.runtime,
                        passed_tests=passed_tests,
                        total_tests=total_tests
                    )
            else:
                return result
        
        avg_runtime = total_runtime / total_tests if total_tests > 0 else 0
        
        return CodeExecutionResult(
            status=SubmissionStatusEnum.ACCEPTED,
            output=f"All test cases passed!\nAverage Runtime: {avg_runtime:.2f}ms",
            runtime=avg_runtime,
            passed_tests=passed_tests,
            total_tests=total_tests
        )
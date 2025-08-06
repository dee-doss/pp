from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
import uuid

# Enums
class DifficultyEnum(str, Enum):
    EASY = "Easy"
    MEDIUM = "Medium"
    HARD = "Hard"

class SubmissionStatusEnum(str, Enum):
    ACCEPTED = "Accepted"
    WRONG_ANSWER = "Wrong Answer"
    TIME_LIMIT_EXCEEDED = "Time Limit Exceeded"
    MEMORY_LIMIT_EXCEEDED = "Memory Limit Exceeded"
    RUNTIME_ERROR = "Runtime Error"
    COMPILE_ERROR = "Compile Error"

class ContestStatusEnum(str, Enum):
    UPCOMING = "upcoming"
    RUNNING = "running"
    ENDED = "ended"

class LanguageEnum(str, Enum):
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    JAVA = "java"
    CPP = "cpp"

# User Models
class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    username: str
    email: EmailStr
    password_hash: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    total_solved: int = 0
    easy_solved: int = 0
    medium_solved: int = 0
    hard_solved: int = 0
    ranking: int = 0
    streak: int = 0
    acceptance_rate: float = 0.0
    avatar: str = ""

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    username: str
    email: EmailStr
    total_solved: int
    easy_solved: int
    medium_solved: int
    hard_solved: int
    ranking: int
    streak: int
    acceptance_rate: float
    avatar: str
    created_at: datetime

# Problem Models
class TestCase(BaseModel):
    input: str
    expected_output: str
    is_hidden: bool = False

class Example(BaseModel):
    input: str
    output: str
    explanation: Optional[str] = None

class StarterCode(BaseModel):
    python: str = ""
    javascript: str = ""
    java: str = ""
    cpp: str = ""

class Problem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    number: int
    title: str
    description: str
    difficulty: DifficultyEnum
    tags: List[str]
    examples: List[Example]
    constraints: List[str]
    test_cases: List[TestCase]
    starter_code: StarterCode
    acceptance_rate: float = 0.0
    total_submissions: int = 0
    accepted_submissions: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ProblemCreate(BaseModel):
    number: int
    title: str
    description: str
    difficulty: DifficultyEnum
    tags: List[str]
    examples: List[Example]
    constraints: List[str]
    test_cases: List[TestCase]
    starter_code: StarterCode

class ProblemResponse(BaseModel):
    id: str
    number: int
    title: str
    description: str
    difficulty: DifficultyEnum
    tags: List[str]
    examples: List[Example]
    constraints: List[str]
    starter_code: StarterCode
    acceptance_rate: float
    total_submissions: int
    solved: bool = False  # Will be populated based on user's submissions

# Submission Models
class Submission(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    problem_id: str
    language: LanguageEnum
    code: str
    status: SubmissionStatusEnum
    runtime: Optional[float] = None
    memory: Optional[float] = None
    passed_test_cases: int = 0
    total_test_cases: int = 0
    error_message: Optional[str] = None
    submitted_at: datetime = Field(default_factory=datetime.utcnow)

class SubmissionCreate(BaseModel):
    problem_id: str
    language: LanguageEnum
    code: str

class SubmissionResponse(BaseModel):
    id: str
    user_id: str
    problem_id: str
    language: LanguageEnum
    code: str
    status: SubmissionStatusEnum
    runtime: Optional[float]
    memory: Optional[float]
    passed_test_cases: int
    total_test_cases: int
    error_message: Optional[str]
    submitted_at: datetime

# Contest Models
class Contest(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: str
    status: ContestStatusEnum
    start_time: datetime
    duration: int  # in minutes
    problems: List[str]  # problem IDs
    participants: List[str] = []  # user IDs
    created_at: datetime = Field(default_factory=datetime.utcnow)
    image: str = ""

class ContestCreate(BaseModel):
    title: str
    description: str
    start_time: datetime
    duration: int
    problems: List[str]
    image: str = ""

class ContestResponse(BaseModel):
    id: str
    title: str
    description: str
    status: ContestStatusEnum
    start_time: datetime
    duration: int
    problems: List[str]
    participants_count: int
    image: str

# Discussion Models
class Discussion(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    content: str
    author_id: str
    author_username: str
    tags: List[str]
    replies_count: int = 0
    views_count: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_activity: datetime = Field(default_factory=datetime.utcnow)

class DiscussionCreate(BaseModel):
    title: str
    content: str
    tags: List[str] = []

class DiscussionResponse(BaseModel):
    id: str
    title: str
    content: str
    author_username: str
    tags: List[str]
    replies_count: int
    views_count: int
    created_at: datetime
    last_activity: datetime

# Reply Models
class Reply(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    discussion_id: str
    content: str
    author_id: str
    author_username: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ReplyCreate(BaseModel):
    content: str

class ReplyResponse(BaseModel):
    id: str
    content: str
    author_username: str
    created_at: datetime

# Code execution models
class CodeExecutionRequest(BaseModel):
    problem_id: str
    language: LanguageEnum
    code: str
    test_input: Optional[str] = None

class CodeExecutionResult(BaseModel):
    status: SubmissionStatusEnum
    output: str
    runtime: Optional[float] = None
    memory: Optional[float] = None
    passed_tests: int = 0
    total_tests: int = 0
    error_message: Optional[str] = None

# Statistics Models
class UserStats(BaseModel):
    total_problems: int
    solved_problems: int
    easy_solved: int
    medium_solved: int
    hard_solved: int
    acceptance_rate: float
    ranking: int
    streak: int
    recent_submissions: List[SubmissionResponse]

# Token Model
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
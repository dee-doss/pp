from fastapi import FastAPI, APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from starlette.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
from typing import List, Optional
import logging
from pathlib import Path
import asyncio

# Import our modules
from database import connect_to_mongo, close_mongo_connection, get_database, create_indexes
from models import *
from auth import authenticate_user, create_access_token, get_current_user, get_password_hash
from code_executor import CodeExecutor

# Initialize FastAPI app
app = FastAPI(title="CodeForge API", description="LeetCode/CodeChef Clone Backend", version="1.0.0")
api_router = APIRouter(prefix="/api")

# Initialize code executor
code_executor = CodeExecutor()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Startup event
@app.on_event("startup")
async def startup_event():
    await connect_to_mongo()
    await create_indexes()
    await seed_initial_data()
    logger.info("Application started successfully")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    await close_mongo_connection()
    logger.info("Application shut down successfully")

# Health check
@api_router.get("/")
async def root():
    return {"message": "CodeForge API is running!", "status": "healthy", "timestamp": datetime.utcnow()}

# ==================== AUTH ROUTES ====================

@api_router.post("/auth/register", response_model=dict)
async def register(user_data: UserCreate):
    db = await get_database()
    
    # Check if user exists
    existing_user = await db.users.find_one({"$or": [{"email": user_data.email}, {"username": user_data.username}]})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email or username already exists"
        )
    
    # Create new user
    user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
        avatar="https://images.pexels.com/photos/5475812/pexels-photo-5475812.jpeg"
    )
    
    await db.users.insert_one(user.dict())
    
    # Create access token
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserResponse(**user.dict())
    }

@api_router.post("/auth/login", response_model=dict)
async def login(user_credentials: UserLogin):
    user = await authenticate_user(user_credentials.email, user_credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserResponse(**user.dict())
    }

@api_router.get("/auth/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    return UserResponse(**current_user.dict())

# ==================== PROBLEM ROUTES ====================

@api_router.get("/problems", response_model=List[ProblemResponse])
async def get_problems(
    difficulty: Optional[DifficultyEnum] = None,
    tag: Optional[str] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    db = await get_database()
    
    # Build filter
    filter_dict = {}
    if difficulty:
        filter_dict["difficulty"] = difficulty.value
    if tag:
        filter_dict["tags"] = {"$in": [tag]}
    if search:
        filter_dict["title"] = {"$regex": search, "$options": "i"}
    
    problems = await db.problems.find(filter_dict).sort("number", 1).to_list(None)
    
    # Get user's solved problems
    user_submissions = await db.submissions.find({
        "user_id": current_user.id,
        "status": SubmissionStatusEnum.ACCEPTED
    }).distinct("problem_id")
    
    # Prepare response
    response = []
    for problem in problems:
        problem_response = ProblemResponse(**problem)
        problem_response.solved = problem["id"] in user_submissions
        response.append(problem_response)
    
    return response

@api_router.get("/problems/{problem_id}", response_model=ProblemResponse)
async def get_problem(problem_id: str, current_user: User = Depends(get_current_user)):
    db = await get_database()
    
    problem = await db.problems.find_one({"id": problem_id})
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")
    
    # Check if user solved this problem
    submission = await db.submissions.find_one({
        "user_id": current_user.id,
        "problem_id": problem_id,
        "status": SubmissionStatusEnum.ACCEPTED
    })
    
    problem_response = ProblemResponse(**problem)
    problem_response.solved = submission is not None
    
    return problem_response

# ==================== CODE EXECUTION ROUTES ====================

@api_router.post("/code/run", response_model=CodeExecutionResult)
async def run_code(
    request: CodeExecutionRequest,
    current_user: User = Depends(get_current_user)
):
    db = await get_database()
    
    problem = await db.problems.find_one({"id": request.problem_id})
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")
    
    # Use custom test input or first example
    if request.test_input:
        result = code_executor.execute_code(request.language, request.code, request.test_input)
    else:
        # Use first example as test input
        if problem.get("examples"):
            example_input = problem["examples"][0]["input"]
            result = code_executor.execute_code(request.language, request.code, example_input)
        else:
            result = code_executor.execute_code(request.language, request.code, "")
    
    return result

@api_router.post("/code/submit", response_model=SubmissionResponse)
async def submit_code(
    request: SubmissionCreate,
    current_user: User = Depends(get_current_user)
):
    db = await get_database()
    
    problem = await db.problems.find_one({"id": request.problem_id})
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")
    
    # Test against all test cases
    test_cases = problem.get("test_cases", [])
    if not test_cases:
        # Mock test cases if none exist
        test_cases = [
            {"input": problem["examples"][0]["input"], "expected_output": problem["examples"][0]["output"]}
        ] if problem.get("examples") else []
    
    result = code_executor.test_solution(request.language, request.code, test_cases)
    
    # Create submission record
    submission = Submission(
        user_id=current_user.id,
        problem_id=request.problem_id,
        language=request.language,
        code=request.code,
        status=result.status,
        runtime=result.runtime,
        memory=result.memory,
        passed_test_cases=result.passed_tests,
        total_test_cases=result.total_tests,
        error_message=result.error_message
    )
    
    await db.submissions.insert_one(submission.dict())
    
    # Update problem statistics
    await db.problems.update_one(
        {"id": request.problem_id},
        {"$inc": {"total_submissions": 1}}
    )
    
    if result.status == SubmissionStatusEnum.ACCEPTED:
        await db.problems.update_one(
            {"id": request.problem_id},
            {"$inc": {"accepted_submissions": 1}}
        )
        
        # Update user statistics
        problem_obj = Problem(**problem)
        difficulty = problem_obj.difficulty
        
        # Check if this is user's first accepted submission for this problem
        existing_accepted = await db.submissions.find_one({
            "user_id": current_user.id,
            "problem_id": request.problem_id,
            "status": SubmissionStatusEnum.ACCEPTED
        })
        
        if not existing_accepted or existing_accepted["id"] == submission.id:
            update_dict = {"$inc": {"total_solved": 1}}
            if difficulty == DifficultyEnum.EASY:
                update_dict["$inc"]["easy_solved"] = 1
            elif difficulty == DifficultyEnum.MEDIUM:
                update_dict["$inc"]["medium_solved"] = 1
            elif difficulty == DifficultyEnum.HARD:
                update_dict["$inc"]["hard_solved"] = 1
            
            await db.users.update_one({"id": current_user.id}, update_dict)
    
    return SubmissionResponse(**submission.dict())

# ==================== USER STATS ROUTES ====================

@api_router.get("/users/stats", response_model=UserStats)
async def get_user_stats(current_user: User = Depends(get_current_user)):
    db = await get_database()
    
    # Get total problems count
    total_problems = await db.problems.count_documents({})
    
    # Get recent submissions
    recent_submissions_data = await db.submissions.find(
        {"user_id": current_user.id}
    ).sort("submitted_at", -1).limit(10).to_list(None)
    
    recent_submissions = [SubmissionResponse(**sub) for sub in recent_submissions_data]
    
    # Calculate acceptance rate
    total_user_submissions = await db.submissions.count_documents({"user_id": current_user.id})
    accepted_submissions = await db.submissions.count_documents({
        "user_id": current_user.id,
        "status": SubmissionStatusEnum.ACCEPTED
    })
    
    acceptance_rate = (accepted_submissions / total_user_submissions * 100) if total_user_submissions > 0 else 0
    
    return UserStats(
        total_problems=total_problems,
        solved_problems=current_user.total_solved,
        easy_solved=current_user.easy_solved,
        medium_solved=current_user.medium_solved,
        hard_solved=current_user.hard_solved,
        acceptance_rate=round(acceptance_rate, 1),
        ranking=current_user.ranking or 15430,
        streak=current_user.streak or 12,
        recent_submissions=recent_submissions
    )

# ==================== CONTEST ROUTES ====================

@api_router.get("/contests", response_model=List[ContestResponse])
async def get_contests():
    db = await get_database()
    
    contests = await db.contests.find().sort("start_time", -1).to_list(None)
    
    response = []
    for contest in contests:
        contest_response = ContestResponse(
            **contest,
            participants_count=len(contest.get("participants", []))
        )
        response.append(contest_response)
    
    return response

@api_router.get("/contests/{contest_id}", response_model=ContestResponse)
async def get_contest(contest_id: str):
    db = await get_database()
    
    contest = await db.contests.find_one({"id": contest_id})
    if not contest:
        raise HTTPException(status_code=404, detail="Contest not found")
    
    return ContestResponse(
        **contest,
        participants_count=len(contest.get("participants", []))
    )

# ==================== DISCUSSION ROUTES ====================

@api_router.get("/discussions", response_model=List[DiscussionResponse])
async def get_discussions():
    db = await get_database()
    
    discussions = await db.discussions.find().sort("last_activity", -1).to_list(None)
    
    return [DiscussionResponse(**discussion) for discussion in discussions]

@api_router.post("/discussions", response_model=DiscussionResponse)
async def create_discussion(
    discussion_data: DiscussionCreate,
    current_user: User = Depends(get_current_user)
):
    db = await get_database()
    
    discussion = Discussion(
        title=discussion_data.title,
        content=discussion_data.content,
        author_id=current_user.id,
        author_username=current_user.username,
        tags=discussion_data.tags
    )
    
    await db.discussions.insert_one(discussion.dict())
    
    return DiscussionResponse(**discussion.dict())

# Include router
app.include_router(api_router)

# ==================== SEED DATA ====================

async def seed_initial_data():
    db = await get_database()
    
    # Check if data already exists
    if await db.problems.count_documents({}) > 0:
        return
    
    logger.info("Seeding initial data...")
    
    # Seed problems
    problems_data = [
        {
            "number": 1,
            "title": "Two Sum",
            "description": "Given an array of integers nums and an integer target, return indices of the two numbers such that they add up to target.",
            "difficulty": "Easy",
            "tags": ["Array", "Hash Table"],
            "examples": [
                {
                    "input": "nums = [2,7,11,15], target = 9",
                    "output": "[0,1]",
                    "explanation": "Because nums[0] + nums[1] == 9, we return [0, 1]."
                }
            ],
            "constraints": [
                "2 <= nums.length <= 10^4",
                "-10^9 <= nums[i] <= 10^9",
                "-10^9 <= target <= 10^9",
                "Only one valid answer exists."
            ],
            "test_cases": [
                {"input": "[2,7,11,15]\n9", "expected_output": "[0,1]", "is_hidden": False},
                {"input": "[3,2,4]\n6", "expected_output": "[1,2]", "is_hidden": False},
                {"input": "[3,3]\n6", "expected_output": "[0,1]", "is_hidden": True}
            ],
            "starter_code": {
                "python": "class Solution:\n    def twoSum(self, nums: List[int], target: int) -> List[int]:\n        pass",
                "javascript": "var twoSum = function(nums, target) {\n    \n};",
                "java": "class Solution {\n    public int[] twoSum(int[] nums, int target) {\n        \n    }\n}",
                "cpp": "class Solution {\npublic:\n    vector<int> twoSum(vector<int>& nums, int target) {\n        \n    }\n};"
            },
            "acceptance_rate": 49.8,
            "total_submissions": 0,
            "accepted_submissions": 0
        },
        {
            "number": 2,
            "title": "Add Two Numbers",
            "description": "You are given two non-empty linked lists representing two non-negative integers. The digits are stored in reverse order, and each of their nodes contains a single digit. Add the two numbers and return the sum as a linked list.",
            "difficulty": "Medium",
            "tags": ["Linked List", "Math"],
            "examples": [
                {
                    "input": "l1 = [2,4,3], l2 = [5,6,4]",
                    "output": "[7,0,8]",
                    "explanation": "342 + 465 = 807."
                }
            ],
            "constraints": [
                "The number of nodes in each linked list is in the range [1, 100].",
                "0 <= Node.val <= 9",
                "It is guaranteed that the list represents a number that does not have leading zeros."
            ],
            "test_cases": [
                {"input": "[2,4,3]\n[5,6,4]", "expected_output": "[7,0,8]", "is_hidden": False}
            ],
            "starter_code": {
                "python": "# Definition for singly-linked list.\n# class ListNode:\n#     def __init__(self, val=0, next=None):\n#         self.val = val\n#         self.next = next\nclass Solution:\n    def addTwoNumbers(self, l1: Optional[ListNode], l2: Optional[ListNode]) -> Optional[ListNode]:\n        pass",
                "javascript": "var addTwoNumbers = function(l1, l2) {\n    \n};",
                "java": "class Solution {\n    public ListNode addTwoNumbers(ListNode l1, ListNode l2) {\n        \n    }\n}",
                "cpp": "class Solution {\npublic:\n    ListNode* addTwoNumbers(ListNode* l1, ListNode* l2) {\n        \n    }\n};"
            },
            "acceptance_rate": 34.2,
            "total_submissions": 0,
            "accepted_submissions": 0
        }
    ]
    
    for problem_data in problems_data:
        problem = Problem(**problem_data)
        await db.problems.insert_one(problem.dict())
    
    # Seed contests
    contests_data = [
        {
            "title": "Weekly Contest 420",
            "description": "Test your skills in this weekly programming contest",
            "status": "running",
            "start_time": datetime.utcnow() - timedelta(hours=1),
            "duration": 90,
            "problems": [],
            "participants": [],
            "image": "https://images.unsplash.com/photo-1660165458059-57cfb6cc87e5?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDQ2NDN8MHwxfHNlYXJjaHwxfHxhbGdvcml0aG18ZW58MHx8fGJsdWV8MTc1NDQ2MzQ2Mnww&ixlib=rb-4.1.0&q=85"
        },
        {
            "title": "Biweekly Contest 145",
            "description": "Biweekly challenge for advanced programmers",
            "status": "upcoming",
            "start_time": datetime.utcnow() + timedelta(days=2),
            "duration": 90,
            "problems": [],
            "participants": [],
            "image": "https://images.unsplash.com/photo-1655720855348-a5eeeddd1bc4?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDQ2NDN8MHwxfHNlYXJjaHwyfHxhbGdvcml0aG18ZW58MHx8fGJsdWV8MTc1NDQ2MzQ2Mnww&ixlib=rb-4.1.0&q=85"
        }
    ]
    
    for contest_data in contests_data:
        contest = Contest(**contest_data)
        await db.contests.insert_one(contest.dict())
    
    # Seed discussions
    discussions_data = [
        {
            "title": "Two Sum - Optimal Solution Discussion",
            "content": "Let's discuss the most optimal approaches to solve the Two Sum problem.",
            "author_id": "system",
            "author_username": "system",
            "tags": ["Array", "Hash Table"],
            "replies_count": 15,
            "views_count": 342
        },
        {
            "title": "Dynamic Programming Patterns Everyone Should Know",
            "content": "A comprehensive guide to common DP patterns that appear in coding interviews.",
            "author_id": "system",
            "author_username": "system",
            "tags": ["Dynamic Programming", "Tutorial"],
            "replies_count": 28,
            "views_count": 1205
        }
    ]
    
    for discussion_data in discussions_data:
        discussion = Discussion(**discussion_data)
        await db.discussions.insert_one(discussion.dict())
    
    logger.info("Initial data seeded successfully")
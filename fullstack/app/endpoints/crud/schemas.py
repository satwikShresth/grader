from pydantic import BaseModel
from typing import Optional, Dict
from datetime import datetime


class AssignmentCreate(BaseModel):
    name: str
    rubric: dict
    due_date: datetime


class AssignmentUpdate(BaseModel):
    name: Optional[str] = None
    rubric: Optional[dict] = None
    due_date: Optional[datetime] = None


class SubmissionCreate(BaseModel):
    grade: Optional[float] = None
    submission_date: Optional[datetime] = None
    feedback: Optional[dict]
    file_path: str
    student_id: str
    assignment_id: int


class SubmissionUpdate(BaseModel):
    grade: Optional[float] = None
    feedback: Optional[str] = None


class StudentCreate(BaseModel):
    UserID: str
    Name: str
    DrexelID: str
    group_id: Optional[int] = None


class GroupCreate(BaseModel):
    group_number: int


class SubmissionUpdateGradeFeedback(BaseModel):
    grade: Optional[float]
    feedback: Optional[Dict]


class SubmissionUpdateTestCases(BaseModel):
    test_cases: Optional[Dict]

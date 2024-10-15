import os
import logging
import json
from fastapi.templating import Jinja2Templates
from fastapi import APIRouter, Request, HTTPException, Depends, Query
from fastapi.responses import HTMLResponse
from app.database import get_db, Session
from app.models import Student, Assignment, Submission
from app.utils.testrunner import TestRunner
from app import BASE_DIR
from pathlib import Path
from functools import lru_cache
from cachetools import TTLCache


logger = logging.getLogger('uvicorn.error')
router = APIRouter(tags=["grading"])
templates = Jinja2Templates(directory=BASE_DIR / "templates")
html_cache = TTLCache(maxsize=100, ttl=300)  # Cache expires after 5 minutes


def load_grading_data(assignment_number):
    config_path: Path = BASE_DIR / 'config'

    try:
        with open(str(config_path / f"assignment_{assignment_number}.json"), "r") as file:
            grading_data = json.load(file)
    except Exception as e:
        raise RuntimeError(f"Error loading grading configuration: {str(e)}")

    return grading_data


@router.get("/assignment/{assignment_number}", response_class=HTMLResponse)
async def get_assignment_form(request: Request, assignment_number: int, db: Session = Depends(get_db)):
    students = db.query(Student).all()

    submissions = db.query(Submission).filter(
        Submission.assignment_id == assignment_number).all()

    submissions_map = {
        submission.student_id: submission for submission in submissions
    }

    student_data = []
    groups = set()

    for student in students:
        group_number = student.group.group_number if student.group else "Ungrouped"

        groups.add(group_number)

        student_info = {
            "UserID": student.UserID,
            "Name": student.Name,
            "group": group_number,  # Include the group in student data
            "submission_date": submissions_map.get(student.UserID).submission_date if student.UserID in submissions_map else None,
            "grade": submissions_map.get(student.UserID).grade if student.UserID in submissions_map else None,
            "link": f"/grade/assignment/{assignment_number}/{student.UserID}" if student.UserID in submissions_map else None
        }
        student_data.append(student_info)

    return templates.TemplateResponse(
        "center.html",
        {
            "request": request,
            "assignment_number": assignment_number,
            "students": student_data,
            "groups": sorted(groups),  # Pass groups to the template
            "username": request.state.user,
        }
    )


@router.get("/assignment/{assignment_number}/{user_id}", response_class=HTMLResponse)
async def grade_assignment_form(
    request: Request,
    assignment_number: int,
    user_id: str,
    db: Session = Depends(get_db)
):
    student = db.query(Student).filter(Student.UserID == user_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    submission = db.query(Submission).filter(
        Submission.assignment_id == assignment_number,
        Submission.student_id == user_id
    ).first()

    assignment = db.query(Assignment).filter(
        Assignment.id == assignment_number).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    rubric = assignment.rubric

    if submission:
        submission_data = {
            "grade": submission.grade,
            "feedback": submission.feedback
        }
    else:
        submission_data = None

    return templates.TemplateResponse(
        "form.html",
        {
            "request": request,
            "assignment_number": assignment_number,
            "student": student,
            "rubric": rubric,  # Ensure rubric is passed to the template
            "submission": submission_data,
            "user_id": user_id,
            "username": request.state.user,
        }
    )


@router.get("/assignment/{assignment_number}/{user_id}/submission", response_class=HTMLResponse)
async def grade_assignment_form(
    request: Request,
    assignment_number: int,
    user_id: str,
    force_rerender: bool = Query(False),
    db: Session = Depends(get_db)
):
    student = db.query(Student).filter(Student.UserID == user_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    submission = db.query(Submission).filter(
        Submission.assignment_id == assignment_number,
        Submission.student_id == user_id
    ).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    assignment = db.query(Assignment).filter(
        Assignment.id == assignment_number
    ).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    rubric = assignment.rubric

    file_path = Path(submission.file_path)
    logger.error(f"Path:{submission.file_path}")
    if not file_path.exists():
        raise HTTPException(
            status_code=404, detail="Submission file not found")

    if not file_path.is_dir():
        raise HTTPException(
            status_code=400, detail="Invalid submission folder path")

    result_html_path = file_path / 'result.html'

    submission_mtime = os.path.getmtime(file_path)
    result_html_mtime = os.path.getmtime(
        result_html_path) if result_html_path.exists() else 0

    if result_html_path.exists() and result_html_mtime >= submission_mtime and not force_rerender:
        html_content = result_html_path.read_text(encoding='utf-8')
        return HTMLResponse(content=html_content)
    else:
        runner = TestRunner(submission_folder=file_path)
        tabs = runner.generate_tabs(commands=[
            ('bfs', None),
            ('dfs', '-|--|-OO|O--O|-OOOO'),
            ('a_star', 'O|OO|OOO|OOOO|OOOOO'),
            ('random', None)
        ])

        context = {
            "request": request,
            "assignment_number": assignment_number,
            "student": student,
            "rubric": rubric,
            "submission": submission,
            "tabs": tabs,
            "username": request.state.user,
        }
        html_content = templates.get_template(
            "test_result.html").render(context)

        result_html_path.write_text(html_content, encoding='utf-8')

        return HTMLResponse(content=html_content)


@router.get("/assignment", response_class=HTMLResponse)
async def get_assignments(request: Request, db: Session = Depends(get_db)):
    assignments = db.query(Assignment).all()

    return templates.TemplateResponse(
        "available.html",
        {
            "request": request,
            "assignments": assignments,
            "username": request.state.user,
        }
    )

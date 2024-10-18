import os
import json
import logging
import asyncio
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
from fastapi import APIRouter, Request, HTTPException, Depends, Query, BackgroundTasks
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app import BASE_DIR
from app.database import get_db
from app.models import Student, Assignment, Submission
from app.utils.testrunner import TestRunner

logger = logging.getLogger('uvicorn.error')
router = APIRouter(tags=["grading"])
templates = Jinja2Templates(directory=BASE_DIR / "templates")


@router.get("/assignment", response_class=HTMLResponse)
async def get_assignments(request: Request, db: Session = Depends(get_db)):
    assignments = db.query(Assignment).all()
    submissions = db.query(Submission).all()

    return templates.TemplateResponse(
        "available.html",
        {
            "request": request,
            "assignments": assignments,
            "username": request.state.user,
            "num_submissions": len(submissions)
        }
    )


@router.get("/assignment/{assignment_number}", response_class=HTMLResponse)
async def get_assignment_form(request: Request, assignment_number: int, db: Session = Depends(get_db)):
    students = db.query(Student).all()
    submissions = db.query(Submission).filter(
        Submission.assignment_id == assignment_number).all()

    submissions_map = {s.student_id: s for s in submissions}
    student_data = [
        {
            "UserID": student.UserID,
            "Name": student.Name,
            "group": student.group.group_number if student.group else "Ungrouped",
            "submission_date": submissions_map.get(student.UserID).submission_date if student.UserID in submissions_map else None,
            "grade": submissions_map.get(student.UserID).grade if student.UserID in submissions_map else None,
            "link": f"/grade/assignment/{assignment_number}/{student.UserID}" if student.UserID in submissions_map else None
        }
        for student in students
    ]

    groups = sorted({s['group'] for s in student_data})

    return templates.TemplateResponse(
        "center.html",
        {
            "request": request,
            "assignment_number": assignment_number,
            "students": student_data,
            "groups": groups,
            "username": request.state.user,
        }
    )


@router.get("/assignment/{assignment_number}/{user_id}", response_class=HTMLResponse)
async def grade_assignment_form(request: Request, assignment_number: int, user_id: str, db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.UserID == user_id).first()
    assignment = db.query(Assignment).filter(
        Assignment.id == assignment_number).first()

    if not student or not assignment:
        raise HTTPException(
            status_code=404, detail="Student or assignment not found")

    submission = db.query(Submission).filter(
        Submission.assignment_id == assignment_number,
        Submission.student_id == user_id
    ).first()

    submission_data = {
        "grade": submission.grade,
        "feedback": submission.feedback
    } if submission else None

    return templates.TemplateResponse(
        "form.html",
        {
            "request": request,
            "assignment_number": assignment_number,
            "student": student,
            "rubric": assignment.rubric,
            "submission": submission_data,
            "user_id": user_id,
            "username": request.state.user,
        }
    )


@router.get("/assignment/{assignment_number}/{user_id}/submission", response_class=HTMLResponse)
async def get_submission_details(
    request: Request,
    assignment_number: int,
    user_id: str,
    force_rerender: bool = Query(False),
    db: Session = Depends(get_db)
):
    student = db.query(Student).filter(Student.UserID == user_id).first()
    submission = db.query(Submission).filter(
        Submission.assignment_id == assignment_number,
        Submission.student_id == user_id
    ).first()
    assignment = db.query(Assignment).filter(
        Assignment.id == assignment_number).first()

    if not student or not submission or not assignment:
        raise HTTPException(
            status_code=404, detail="Student, submission, or assignment not found")

    file_path = Path(submission.file_path)
    result_html_path = file_path / 'result.html'

    if result_html_path.exists() and os.path.getmtime(result_html_path) >= os.path.getmtime(file_path) and not force_rerender:
        html_content = result_html_path.read_text(encoding='utf-8')
        return HTMLResponse(content=html_content)

    # Generate test results
    test_cases = assignment.rubric.get('test_cases', {})
    files = assignment.rubric.get('files', [])

    runner = TestRunner(submission_folder=file_path, files=files)
    tabs = runner.generate_tabs(test_cases=test_cases)

    context = {
        "request": request,
        "assignment_number": assignment_number,
        "user_id": student.UserID,
        "submission": submission,
        "tabs": tabs,
        "username": request.state.user,
        "title": f"Assignment {assignment_number} Submission for {student.Name}",
    }
    html_content = templates.get_template("test_result.html").render(context)
    result_html_path.write_text(html_content, encoding='utf-8')

    return HTMLResponse(content=html_content)


def process_submission(file_path, submission, student, assignment, user):
    logger.info(f"Processing submission for student: {student.Name}")
    test_cases = assignment.rubric.get('test_cases', {})
    files = assignment.rubric.get('files', [])

    runner = TestRunner(submission_folder=file_path, files=files)
    tabs = runner.generate_tabs(test_cases=test_cases)

    result_html_path = file_path / 'result.html'

    context = {
        "assignment_number": submission.assignment_id,
        "user_id": student.UserID,
        "submission": submission,
        "tabs": tabs,
        "username": user,
        "title": f"Assignment {submission.assignment_id} Submission for {student.Name}",
    }

    html_content = templates.get_template("test_result.html").render(context)
    result_html_path.write_text(html_content, encoding='utf-8')


async def process_submissions_in_background(user, submissions, assignment, db):
    tasks = []
    loop = asyncio.get_running_loop()
    with ProcessPoolExecutor() as pool:
        for submission in submissions:
            file_path = Path(submission.file_path)
            student = db.query(Student).filter(
                Student.UserID == submission.student_id).first()

            if file_path.exists() and student:
                tasks.append(loop.run_in_executor(
                    pool,
                    process_submission,
                    file_path,
                    submission,
                    student,
                    assignment,
                    user
                ))
            else:
                logger.error(f"Missing file or student for submission: {
                             submission.student_id}")

        await asyncio.gather(*tasks)


@router.post("/assignment/process-submissions")
async def process_all_submissions(
    request: Request,
    background_tasks: BackgroundTasks,
    assignment_number: int = Query(...),
    db: Session = Depends(get_db)
):
    submissions = db.query(Submission).filter(
        Submission.assignment_id == assignment_number).all()
    assignment = db.query(Assignment).filter(
        Assignment.id == assignment_number).first()

    if not submissions or not assignment:
        raise HTTPException(
            status_code=404, detail="No submissions or assignment found")

    background_tasks.add_task(
        process_submissions_in_background,
        request.state.user,
        submissions,
        assignment,
        db
    )

    return {"status": "Processing submissions in background"}


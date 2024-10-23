from typing import List, Optional
from collections import defaultdict
from datetime import timedelta, timezone
import os
import logging
import asyncio
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
from fastapi import APIRouter, Request, HTTPException, Depends, Query, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
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
            "title": f"Assignment {submission.assignment_id} Submission for {student.Name}",
        }
    )


@router.get("/assignment/{assignment_number}/{user_id}/submission", response_class=JSONResponse)
async def get_submission_details(
    request: Request,
    assignment_number: int,
    user_id: str,
    background_tasks: BackgroundTasks,
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

    background_tasks.add_task(
        process_submission,
        file_path,
        submission,
        student,
        assignment,
        request.state.user,
    )

    # # Generate test results
    # test_cases = assignment.rubric.get('test_cases', {})
    # files = assignment.rubric.get('files', [])
    #
    # runner = TestRunner(submission_folder=file_path, files=files)
    # tabs = runner.generate_tabs(test_cases=test_cases)
    #
    # context = {
    #     "request": request,
    #     "assignment_number": assignment_number,
    #     "user_id": student.UserID,
    #     "submission": submission,
    #     "tabs": tabs,
    #     "username": request.state.user,
    #     "title": f"Assignment {assignment_number} Submission for {student.Name}",
    # }
    # html_content = templates.get_template("test_result.html").render(context)
    # result_html_path.write_text(html_content, encoding='utf-8')

    return {"status": f"Processing submission of {student.UserID} in background"}


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


@ router.post("/assignment/process-submissions", response_class=JSONResponse)
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


@router.post("/assignment/late", response_class=JSONResponse)
async def get_late_submissions(
    assignment_number: int = Query(
        ..., description="The ID of the assignment (must be an integer)"),
    groups: Optional[List[int]] = Query(
        None, description="List of group numbers to filter by (optional)"),
    db: Session = Depends(get_db)
):
    # Fetch the assignment using the assignment number
    assignment = db.query(Assignment).filter(
        Assignment.id == assignment_number).first()

    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    # Define the grace period: 15 minutes after the due date
    grace_period = assignment.due_date + timedelta(minutes=5)

    # Fetch submissions that are past due (and not exactly at 23:59)
    late_submissions = db.query(Submission).filter(
        Submission.assignment_id == assignment_number,
        Submission.submission_date > grace_period,  # Submissions after the grace period
        Submission.submission_date != assignment.due_date.replace(
            hour=23, minute=59)  # Exclude exactly 23:59
    ).all()

    if not late_submissions:
        return {"message": "No late submissions found"}

    # Ensure that grace_period is timezone-aware, and compare it correctly with submission dates
    if grace_period.tzinfo is None:
        # Assuming UTC if no timezone info is present
        grace_period = grace_period.replace(tzinfo=timezone.utc)

    # Create a response with late submission details grouped by student group
    grouped_late_students = defaultdict(list)

    for submission in late_submissions:
        submission_date = submission.submission_date
        if submission_date.tzinfo is None:
            # Assuming UTC if no timezone info is present for submission date
            submission_date = submission_date.replace(tzinfo=timezone.utc)

        # Calculate "late by" duration
        late_by_duration = submission_date - grace_period

        # Convert the late_by_duration into days, hours, and minutes
        days = late_by_duration.days
        hours, remainder = divmod(late_by_duration.seconds, 3600)
        minutes = remainder // 60

        # Format the "late by" string
        late_by_str = f"{days} day{'s' if days != 1 else ''} {hours} hour{
            's' if hours != 1 else ''} {minutes} min{'s' if minutes != 1 else ''}"

        # Get the student's group (if any), or assign 'Ungrouped' if no group exists
        group = submission.student.group.group_number if submission.student.group else "Ungrouped"

        # If groups are provided, only include submissions from the specified groups
        if groups and group != "Ungrouped" and group not in groups:
            continue

        # Append the late student data to the appropriate group
        grouped_late_students[group].append({
            "UserID": submission.student.UserID,
            "Name": submission.student.Name,
            "submission_date": submission.submission_date,
            "grade": submission.grade,
            "late_by": late_by_str
        })

    # Return the grouped data
    return {"late_submissions": grouped_late_students}

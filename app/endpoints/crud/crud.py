from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.models import Assignment, Submission, Student, Group
from app.database import SessionLocal, get_db
from .schemas import AssignmentCreate, SubmissionCreate, StudentCreate, GroupCreate, AssignmentUpdate, SubmissionUpdate, SubmissionUpdateGradeFeedback

from typing import List

router = APIRouter(tags=["CRUD"], dependencies=[Depends(get_db)])


@router.post("/assignments/", response_model=AssignmentCreate)
def create_assignment(assignment: AssignmentCreate, db: Session = Depends(get_db)):
    db_assignment = Assignment(**assignment.dict())
    db.add(db_assignment)
    db.commit()
    db.refresh(db_assignment)
    return db_assignment


@router.get("/assignments/", response_model=List[AssignmentCreate])
def list_assignments(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    assignments = db.query(Assignment).offset(skip).limit(limit).all()
    return assignments


@router.get("/assignments/{assignment_id}", response_model=AssignmentCreate)
def get_assignment(assignment_id: int, db: Session = Depends(get_db)):
    assignment = db.query(Assignment).filter(
        Assignment.id == assignment_id).first()
    if assignment is None:
        raise HTTPException(status_code=404, detail="Assignment not found")
    return assignment


@router.put("/assignments/{assignment_id}", response_model=AssignmentCreate)
def update_assignment(assignment_id: int, assignment: AssignmentUpdate, db: Session = Depends(get_db)):
    db_assignment = db.query(Assignment).filter(
        Assignment.id == assignment_id).first()
    if db_assignment is None:
        raise HTTPException(status_code=404, detail="Assignment not found")

    for key, value in assignment.dict(exclude_unset=True).items():
        setattr(db_assignment, key, value)

    db.commit()
    db.refresh(db_assignment)
    return db_assignment


@router.delete("/assignments/{assignment_id}", response_model=dict)
def delete_assignment(assignment_id: int, db: Session = Depends(get_db)):
    db_assignment = db.query(Assignment).filter(
        Assignment.id == assignment_id).first()
    if db_assignment is None:
        raise HTTPException(status_code=404, detail="Assignment not found")

    db.delete(db_assignment)
    db.commit()
    return {"message": "Assignment deleted successfully"}


@router.post("/submissions/", response_model=SubmissionCreate)
def create_submission(submission: SubmissionCreate, db: Session = Depends(get_db)):
    db_submission = Submission(**submission.dict())
    db.add(db_submission)
    db.commit()
    db.refresh(db_submission)
    return db_submission


@router.delete("/submissions/{submission_id}", response_model=dict)
def delete_submission(submission_id: int, db: Session = Depends(get_db)):
    db_submission = db.query(Submission).filter(
        Submission.id == submission_id).first()
    if db_submission is None:
        raise HTTPException(status_code=404, detail="Submission not found")

    db.delete(db_submission)
    db.commit()
    return {"message": "Submission deleted successfully"}


@router.post("/students/", response_model=StudentCreate)
def create_student(student: StudentCreate, db: Session = Depends(get_db)):
    db_student = Student(**student.dict())
    db.add(db_student)
    db.commit()
    db.refresh(db_student)
    return db_student


@router.get("/students/", response_model=List[StudentCreate])
def list_students(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    students = db.query(Student).offset(skip).limit(limit).all()
    return students


@router.get("/students/{user_id}", response_model=StudentCreate)
def get_student(user_id: str, db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.UserID == user_id).first()
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found")
    return student


@router.put("/students/{user_id}", response_model=StudentCreate)
def update_student(user_id: str, student: StudentCreate, db: Session = Depends(get_db)):
    db_student = db.query(Student).filter(Student.UserID == user_id).first()
    if db_student is None:
        raise HTTPException(status_code=404, detail="Student not found")

    for key, value in student.dict(exclude_unset=True).items():
        setattr(db_student, key, value)

    db.commit()
    db.refresh(db_student)
    return db_student


@router.delete("/students/{user_id}", response_model=dict)
def delete_student(user_id: str, db: Session = Depends(get_db)):
    db_student = db.query(Student).filter(Student.UserID == user_id).first()
    if db_student is None:
        raise HTTPException(status_code=404, detail="Student not found")

    db.delete(db_student)
    db.commit()
    return {"message": "Student deleted successfully"}


@router.post("/groups/", response_model=GroupCreate)
def create_group(group: GroupCreate, db: Session = Depends(get_db)):
    db_group = Group(**group.dict())
    db.add(db_group)
    db.commit()
    db.refresh(db_group)
    return db_group


@router.get("/groups/", response_model=List[GroupCreate])
def list_groups(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    groups = db.query(Group).offset(skip).limit(limit).all()
    return groups


@router.get("/groups/{group_id}", response_model=GroupCreate)
def get_group(group_id: int, db: Session = Depends(get_db)):
    group = db.query(Group).filter(Group.id == group_id).first()
    if group is None:
        raise HTTPException(status_code=404, detail="Group not found")
    return group


@router.put("/groups/{group_id}", response_model=GroupCreate)
def update_group(group_id: int, group: GroupCreate, db: Session = Depends(get_db)):
    db_group = db.query(Group).filter(Group.id == group_id).first()
    if db_group is None:
        raise HTTPException(status_code=404, detail="Group not found")

    for key, value in group.dict(exclude_unset=True).items():
        setattr(db_group, key, value)

    db.commit()
    db.refresh(db_group)
    return db_group


@router.delete("/groups/{group_id}", response_model=dict)
def delete_group(group_id: int, db: Session = Depends(get_db)):
    db_group = db.query(Group).filter(Group.id == group_id).first()
    if db_group is None:
        raise HTTPException(status_code=404, detail="Group not found")

    db.delete(db_group)
    db.commit()
    return {"message": "Group deleted successfully"}


@router.put("/submissions/feedback", response_model=dict)
def update_grade_feedback_by_userid(
    submission_data: SubmissionUpdateGradeFeedback,
    userid: str = Query(...),
    assignment_number: int = Query(...),
    db: Session = Depends(get_db)
):
    db_submission = db.query(Submission).join(Student).filter(
        Student.UserID == userid,
        Submission.assignment_id == assignment_number
    ).first()

    if db_submission is None:
        raise HTTPException(
            status_code=404, detail="Submission not found for this user and assignment")

    # Update grade if provided
    if submission_data.grade is not None:
        db_submission.grade = submission_data.grade

    # Update feedback if provided
    if submission_data.feedback is not None:
        db_submission.feedback = submission_data.feedback

    # Commit changes to the database
    db.commit()
    db.refresh(db_submission)

    # Return the updated submission
    return {
        "grade": db_submission.grade,
        "feedback": db_submission.feedback
    }


@router.get("/submissions/feedback", response_model=dict)
def get_grade_feedback_by_userid(
    userid: str = Query(..., description="User ID of the student"),
    assignment_number: int = Query(..., description="Assignment number"),
    db: Session = Depends(get_db)
):
    # Query for the submission by user ID and assignment number
    db_submission = db.query(Submission).join(Student).filter(
        Student.UserID == userid,
        Submission.assignment_id == assignment_number
    ).first()

    # Handle case where submission is not found
    if db_submission is None:
        raise HTTPException(
            status_code=404, detail="Submission not found for this user and assignment"
        )

    # Return the grade and feedback in a dictionary
    return {
        "grade": db_submission.grade,
        "feedback": db_submission.feedback
    }

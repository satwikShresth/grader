from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Form
from fastapi.responses import JSONResponse
from pathlib import Path
from app import UNZIP_DIR, UPLOAD_DIR
from app.utils import parser, organizer
from app.database import get_db, Session
from app.models import Assignment
from datetime import datetime
import json
import zipfile
import shutil

router = APIRouter(tags=["upload"])


def handle_rubric_file(rubric_file: UploadFile):
    if not rubric_file.filename.endswith(".json"):
        raise HTTPException(
            status_code=400, detail="Only .json files are allowed for the rubric")

    rubric_file_location = UPLOAD_DIR / rubric_file.filename
    with open(rubric_file_location, "wb") as buffer:
        shutil.copyfileobj(rubric_file.file, buffer)

    with open(rubric_file_location, "r") as rubric_file:
        try:
            rubric_content = json.load(rubric_file)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=400, detail="Invalid JSON format in the rubric file")

    return rubric_content


def handle_gradebook_file(gradebook_file: UploadFile):
    if not gradebook_file.filename.endswith(".zip"):
        raise HTTPException(
            status_code=400, detail="Only .zip files are allowed for the gradebook")

    gradebook_file_location = UPLOAD_DIR / gradebook_file.filename
    with open(gradebook_file_location, "wb") as buffer:
        shutil.copyfileobj(gradebook_file.file, buffer)

    target_path = UNZIP_DIR
    target_path.mkdir(exist_ok=True)

    try:
        with zipfile.ZipFile(gradebook_file_location, 'r') as zip_ref:
            zip_ref.extractall(target_path)
    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="Invalid zip file")

    return target_path


def organize_files(target_path: Path, assignment_id: int):
    org = organizer.Organizer(target_path, assignment_id)
    org.organize()


def parse_due_date(due_date_str: str):
    try:
        due_date = datetime.strptime(due_date_str, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid due date format")
    return due_date


@router.post("/all/")
async def upload_all(
    assignmentName: str = Form(...),
    assignmentId: int = Form(...),
    dueDate: str = Form(...),
    rubricFile: UploadFile = File(...),
    gradebookFile: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    rubric_content = handle_rubric_file(rubricFile)

    target_path = handle_gradebook_file(gradebookFile)

    organize_files(target_path, assignmentId)

    due_date_parsed = parse_due_date(dueDate)

    new_assignment = Assignment(
        id=assignmentId,
        name=assignmentName,
        rubric=rubric_content,  # Store the JSON content directly into the rubric column
        due_date=due_date_parsed
    )

    db.add(new_assignment)
    db.commit()
    db.refresh(new_assignment)

    # Return a success message
    return JSONResponse(content={
        "status": "Assignment and files uploaded successfully",
        "assignmentId": new_assignment.id,
        "assignmentName": new_assignment.name,
        "dueDate": new_assignment.due_date.strftime("%Y-%m-%d")
    })


@router.post("/group/")
async def upload_group(groupFile: UploadFile = File(...), db: Session = Depends(get_db)):
    if not groupFile.filename.endswith(".txt"):
        return JSONResponse(content={"error": "Only .txt files are allowed"}, status_code=400)

    content = await groupFile.read()

    class_data = parser.parse_group_file(content.decode("utf-8"))
    parser.insert_group_data(db, class_data)

    return JSONResponse(content={"status": "Group.txt uploaded and processed successfully"})


@router.post("/gradebook/")
async def upload_gradebook(
    assignmentId: int = Form(...),
    gradebookFile: UploadFile = File(...)
):
    target_path = handle_gradebook_file(gradebookFile)

    organize_files(target_path, assignmentId)

    return JSONResponse(content={"status": "Gradebook file uploaded and organized successfully"})


@router.post("/rubric/")
async def upload_rubric(
    assignmentName: str = Form(...),
    assignmentId: int = Form(...),
    dueDate: str = Form(...),
    rubricFile: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    rubric_content = handle_rubric_file(rubricFile)

    due_date_parsed = parse_due_date(dueDate)

    assignment = db.query(Assignment).filter(
        Assignment.id == assignmentId).first()

    if assignment:
        assignment.name = assignmentName
        assignment.rubric = rubric_content
        assignment.due_date = due_date_parsed
    else:
        new_assignment = Assignment(
            id=assignmentId,
            name=assignmentName,
            rubric=rubric_content,  # Store the JSON content directly into the rubric column
            due_date=due_date_parsed
        )
        db.add(new_assignment)
        db.commit()
        db.refresh(new_assignment)

    db.commit()

    return JSONResponse(content={"status": "Rubric file uploaded and assignment created/updated successfully"})

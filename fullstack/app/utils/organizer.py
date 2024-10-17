import re
from pathlib import Path
from typing import Dict
from zipfile import ZipFile
from datetime import datetime
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Submission, Student, Assignment
import json
import logging

logger = logging.getLogger('uvicorn.error')


class Organizer:
    def __init__(self, target_path, assignment_id: int):
        self.assignment_id: int = assignment_id
        self.target_path = target_path

    def organize(self):
        current_dir = Path(self.target_path)

        for filename in current_dir.iterdir():
            if filename.is_file():
                self.splitAndStore(filename.name, current_dir)

        for dirName in current_dir.iterdir():
            if dirName.is_dir() and dirName.name != 'archive':
                self.unzip_recursive(dirName)

        return 0

    def splitAndStore(self, filename: str, current_dir):
        userid_pattern = r'_([a-zA-Z]{2,5}\d{2,6})_'

        match = re.search(userid_pattern, filename)
        if match:
            userid = match.group(1)
            directory_name = userid
        else:
            print(f"No user ID found in filename '{filename}'. Skipping file.")
            return

        original_file_path = current_dir / filename

        if original_file_path.exists():
            directory_path = current_dir / directory_name

            if Path(filename).suffix == '.zip':
                directory_path /= "submission"

            directory_path.mkdir(exist_ok=True, parents=True)

            if Path(filename).suffix == '.txt':
                filename = 'submission.log'

            new_file_path = directory_path / filename
            original_file_path.rename(new_file_path)

            # After renaming, read submission.log and extract submission date
            if filename == 'submission.log':
                self.process_submission_log(
                    new_file_path, userid, new_file_path.parent)

            print(f"File '{filename}' stored in directory '{directory_name}'")
        else:
            print(f"File '{filename}' does not exist in the directory.")

    def process_submission_log(self, log_path: Path, userid: str, submission_dir: Path):
        submission_pattern = r"Date Submitted:\s+(.*)\s+[A-Z]{3,4}$"
        date_format = "%A, %B %d, %Y %I:%M:%S %p"

        submission_date = None

        with open(log_path, "r") as file:
            for line in file:
                match = re.search(submission_pattern, line)
                if match:
                    # Extract the date part without timezone
                    date_str = match.group(1)

                    try:
                        submission_date = datetime.strptime(
                            date_str, date_format)
                        print(f"Extracted submission date: {submission_date}")
                    except ValueError as e:
                        print(f"Error parsing date: {e}")
                    break

        if submission_date:
            # Populate the Submission DB
            self.populate_submission_db(
                userid, submission_date, submission_dir)

    def populate_submission_db(self, userid: str, submission_date: datetime, submission_dir: Path):
        """Populates the Submission DB by linking to the student and saving the submission date."""
        db: Session = SessionLocal()

        try:
            # Fetch the student by their user ID
            student = db.query(Student).filter(
                Student.UserID == userid).first()

            if student:
                assignment = db.query(Assignment).filter(
                    Assignment.id == self.assignment_id).first()
                if assignment:
                    rubrics = assignment.rubric  # Assuming a relationship exists
                    test_cases = rubrics.get("test_cases")
                    logger.info(test_cases)

                    cleaned_test_cases = self.clean_test_cases(test_cases)

                    feedback = {
                        'test_cases': cleaned_test_cases
                    }

                    new_submission = Submission(
                        student_id=student.UserID,
                        assignment_id=self.assignment_id,
                        submission_date=submission_date,
                        feedback=feedback,
                        grade=0.0,
                        file_path=str(submission_dir)
                    )

                    db.add(new_submission)
                    db.commit()
                    db.refresh(new_submission)

                    print(f"Submission for student {
                          student.Name} added to DB.")
                else:
                    print(f"Assignment with ID {
                          self.assignment_id} not found.")
            else:
                print(f"Student with UserID {userid} not found.")
        finally:
            db.close()

    def clean_test_cases(self, test_cases):
        """Recursively replaces non-dictionary values in test_cases with None."""
        if isinstance(test_cases, dict):
            cleaned = {}
            for key, value in test_cases.items():
                cleaned[key] = self.clean_test_cases(value)
            return cleaned
        else:
            return None

    def unzip_recursive(self, dir_path):
        for item in dir_path.iterdir():
            if item.is_file() and item.suffix == '.zip':
                with ZipFile(item, 'r') as zip_ref:
                    zip_ref.extractall(dir_path)
                item.unlink()
        for subdir in dir_path.iterdir():
            if subdir.is_dir():
                self.unzip_recursive(subdir)


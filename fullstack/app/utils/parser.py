import logging
from app.models import Group, Student
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

logger = logging.getLogger('uvicorn.error')


def parse_group_file(fileContent):
    class_data = []

    for line in fileContent.split('\n'):
        line = line.strip()
        logger.error(line)
        if line.startswith("Group"):
            group_number = int(line.split()[-1])  # Extract group number
        elif line:
            parts = line.split()
            if len(parts) >= 3:
                student_data = {
                    "DrexelID": parts[0],
                    "Name": " ".join(parts[1:-1]),
                    "UserID": parts[-1],
                    "GroupID": group_number
                }
                class_data.append(student_data)

    return class_data


def insert_group_data(db: Session, class_data):
    group_objects = {}

    try:
        # Iterate over class data to insert groups and students
        for student_data in class_data:
            group_number = student_data["GroupID"]

            # Check if the group already exists in the current session
            if group_number not in group_objects:
                new_group = Group(group_number=group_number)
                db.add(new_group)
                db.commit()  # Commit the group to get its ID
                db.refresh(new_group)  # Refresh the group to get the new ID
                group_objects[group_number] = new_group

                logger.info(f"Group {group_number} created with ID {
                            new_group.id}")

            student = Student(
                UserID=student_data["UserID"],
                Name=student_data["Name"],
                DrexelID=student_data["DrexelID"],
                group_id=group_objects[group_number].id
            )

            db.add(student)

        db.commit()
        logger.info("All students successfully added to the database.")

    except IntegrityError as e:
        db.rollback()
        logger.error(f"Database integrity error: {e}")
        raise HTTPException(status_code=400, detail="Database integrity error")

    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(
            status_code=500, detail="Unexpected error while inserting group and student data")

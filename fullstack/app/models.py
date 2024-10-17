from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey,
    DateTime,
    JSON,
    Float,
    UniqueConstraint
)
from sqlalchemy.orm import relationship
from app.database import Base
from sqlalchemy.sql import func


class Submission(Base):
    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True, index=True)
    grade = Column(Float, nullable=True)
    submission_date = Column(DateTime(timezone=True),
                             server_default=func.now())
    feedback = Column(JSON, nullable=False)
    test_cases = Column(JSON, nullable=False)
    file_path = Column(String, nullable=False)  # Column to store file path

    student_id = Column(String, ForeignKey("students.UserID"), nullable=False)
    assignment_id = Column(Integer, ForeignKey(
        "assignments.id"), nullable=False)

    student = relationship("Student", back_populates="submissions")
    assignment = relationship("Assignment", back_populates="submissions")

    __table_args__ = (
        UniqueConstraint('student_id', 'assignment_id',
                         name='_student_assignment_uc'),
    )


class Assignment(Base):
    __tablename__ = "assignments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    rubric = Column(JSON, nullable=False)
    due_date = Column(DateTime, nullable=False)

    submissions = relationship("Submission", back_populates="assignment")


class Student(Base):
    __tablename__ = "students"

    UserID = Column(String, primary_key=True, index=True)
    Name = Column(String, nullable=False)
    DrexelID = Column(String, nullable=False)
    group_id = Column(Integer, ForeignKey("groups.id"))

    group = relationship("Group", back_populates="students")
    submissions = relationship("Submission", back_populates="student")


class Group(Base):
    __tablename__ = "groups"

    id = Column(Integer, primary_key=True, index=True)
    group_number = Column(Integer, nullable=False)

    students = relationship("Student", back_populates="group")

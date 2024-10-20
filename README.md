# CS: 380 Grading Tool

## Overview
The **CS: 380 Grading Tool** is designed to streamline the grading process for assignments. It allows instructors to manage assignments, rubrics, and grades with a simple interface, and supports automated testing of student submissions.

## Development Setup

### Prerequisites
- Python 3.x
- UV (Optional download directly)

### Steps to Setup

1. **Install Dependencies**:
   ```bash
   cd fullstack
   pip install uv
   uv sync
   ```

2. **Run the Application**:
   ```bash
   uv run -- fastapi dev --app app --reload
   ```

3. **Database**:
   - create a database dir outside of `./app` 
   - The app uses SQLite by default. You can switch to PostgreSQL by updating the connection string in `database.py`.

## Using Docker

### Steps to Setup with Docker

1. **Build the Docker Image**:
   ```bash
   docker compose up --build
   ```

Access the app at `http://localhost:8000`.


## Pre-requisites

You will need add a file for all the studnets, divided into Groups.

Access all the app api documentation at `http://localhost:8000/docs`.

use the uploads/group post api to add the students file.

## License
This project is licensed under the MIT License.

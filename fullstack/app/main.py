import logging
from pathlib import Path
from app.endpoints import upload, grading
from app.endpoints.crud import crud
from app.endpoints.middleware import session
from app.database import engine, Base
from app import TEMPLATES, STATIC, DATABASE_URL

from fastapi import status
from uuid import uuid4
from sqlalchemy.exc import SQLAlchemyError
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi import FastAPI, Request, HTTPException, Depends


logger = logging.getLogger('uvicorn.error')

try:
    Base.metadata.create_all(bind=engine)
except SQLAlchemyError as e:
    logger.error(f"Error creating database: {e}")
    raise HTTPException(
        status_code=500, detail="Database initialization error")

app = FastAPI()


async def get_current_user(request: Request):
    user = request.session.get('user')
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    request.state.user = user


app.add_middleware(SessionMiddleware, secret_key="abc123")
templates = Jinja2Templates(directory=TEMPLATES)
app.mount("/static", StaticFiles(directory=STATIC), name="static")

app.include_router(
    upload.router,
    prefix="/upload",
    dependencies=[Depends(get_current_user)]
)

app.include_router(
    grading.router,
    prefix="/grade",
    dependencies=[Depends(get_current_user)]
)

app.include_router(crud.router, prefix="/api")
app.include_router(session.router)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc):
    if exc.status_code == status.HTTP_401_UNAUTHORIZED:
        return RedirectResponse(url='/login')
    return templates.TemplateResponse(
        'error.html',
        {
            "request": request,
            "detail": exc.detail,
            "status_code": exc.status_code,
            "headers": exc.headers if exc.headers else "No headers",
        },
        status_code=exc.status_code
    )


@app.get("/", response_class=HTMLResponse, dependencies=[Depends(get_current_user)])
async def read_homepage(request: Request):
    return templates.TemplateResponse(
        "homepage.html",
        {
            "request": request,
            "title": "CS: 380 Grading Tool",
            "gradebookStatus": False,
            "studentDatabaseStatus": True,
            "username": request.state.user,
        },
    )

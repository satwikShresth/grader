from app import TEMPLATES
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi import APIRouter, Form, Request, status

router = APIRouter()
templates = Jinja2Templates(directory=TEMPLATES)


@router.get("/login", response_class=HTMLResponse)
async def enter_name(request: Request):
    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "title": "Enter Your Name",
        },
    )


@router.post('/login')
async def login_post(request: Request, username: str = Form(...)):
    if username:
        request.session['user'] = username
        return RedirectResponse(url='/', status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse('login.html', {'request': request, 'error': 'Invalid credentials'})


@router.get('/logout')
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url='/login')

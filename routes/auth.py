import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import re
from datetime import datetime

from fastapi import APIRouter, Depends, Form, Request, Response
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import SESSION_COOKIE_NAME
from database import get_db
from dependencies import create_session_token, get_current_user
from models.user import User

router = APIRouter()

templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))


@router.get("/login")
async def login_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user = await get_current_user(request, db)
    if user is not None:
        if user.is_admin():
            return RedirectResponse(url="/dashboard/", status_code=302)
        return RedirectResponse(url="/inventory/", status_code=302)

    return templates.TemplateResponse(
        request,
        "auth/login.html",
        context={
            "user": None,
            "error": None,
            "username": "",
            "messages": [],
            "now": datetime.utcnow(),
        },
    )


@router.post("/login")
async def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()

    if user is None or not user.verify_password(password):
        return templates.TemplateResponse(
            request,
            "auth/login.html",
            context={
                "user": None,
                "error": "Invalid username or password.",
                "username": username,
                "messages": [],
                "now": datetime.utcnow(),
            },
        )

    token = create_session_token(user.id)
    if user.is_admin():
        redirect_url = "/dashboard/"
    else:
        redirect_url = "/inventory/"

    response = RedirectResponse(url=redirect_url, status_code=302)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=86400,
    )
    return response


@router.get("/register")
async def register_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user = await get_current_user(request, db)
    if user is not None:
        if user.is_admin():
            return RedirectResponse(url="/dashboard/", status_code=302)
        return RedirectResponse(url="/inventory/", status_code=302)

    return templates.TemplateResponse(
        request,
        "auth/register.html",
        context={
            "user": None,
            "error": None,
            "display_name": "",
            "username": "",
            "messages": [],
            "now": datetime.utcnow(),
        },
    )


@router.post("/register")
async def register_submit(
    request: Request,
    display_name: str = Form(...),
    username: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    error = None

    display_name = display_name.strip()
    username = username.strip()

    if not display_name or len(display_name) > 64:
        error = "Display name is required and must be at most 64 characters."
    elif len(username) < 3 or len(username) > 32:
        error = "Username must be between 3 and 32 characters."
    elif not re.match(r"^[a-zA-Z0-9_]+$", username):
        error = "Username can only contain letters, numbers, and underscores."
    elif len(password) < 8:
        error = "Password must be at least 8 characters."
    elif password != confirm_password:
        error = "Passwords do not match."

    if error is None:
        result = await db.execute(select(User).where(User.username == username))
        existing_user = result.scalar_one_or_none()
        if existing_user is not None:
            error = "Username is already taken. Please choose a different one."

    if error is not None:
        return templates.TemplateResponse(
            request,
            "auth/register.html",
            context={
                "user": None,
                "error": error,
                "display_name": display_name,
                "username": username,
                "messages": [],
                "now": datetime.utcnow(),
            },
        )

    new_user = User(
        username=username,
        display_name=display_name,
        role="staff",
        is_default_admin=False,
    )
    new_user.set_password(password)
    db.add(new_user)
    await db.flush()

    token = create_session_token(new_user.id)
    response = RedirectResponse(url="/inventory/", status_code=302)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=86400,
    )
    return response


@router.get("/logout")
async def logout(request: Request):
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie(key=SESSION_COOKIE_NAME)
    return response


@router.post("/logout")
async def logout_post(request: Request):
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie(key=SESSION_COOKIE_NAME)
    return response
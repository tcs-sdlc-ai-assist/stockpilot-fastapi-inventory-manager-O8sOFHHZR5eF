import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import DEFAULT_ADMIN_USERNAME
from database import get_db
from dependencies import require_admin
from models.user import User

router = APIRouter()

templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))


@router.get("/users/")
async def list_users(
    request: Request,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    users = result.scalars().all()

    return templates.TemplateResponse(
        request,
        "users/list.html",
        context={
            "user": user,
            "users": users,
            "default_admin_username": DEFAULT_ADMIN_USERNAME,
        },
    )


@router.post("/users/add")
async def add_user(
    request: Request,
    display_name: str = Form(...),
    username: str = Form(...),
    password: str = Form(...),
    role: str = Form("staff"),
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    username = username.strip()
    display_name = display_name.strip()

    if len(username) < 3 or len(username) > 32:
        result = await db.execute(select(User).order_by(User.created_at.desc()))
        users = result.scalars().all()
        return templates.TemplateResponse(
            request,
            "users/list.html",
            context={
                "user": user,
                "users": users,
                "default_admin_username": DEFAULT_ADMIN_USERNAME,
                "messages": [{"category": "error", "text": "Username must be between 3 and 32 characters."}],
            },
        )

    if len(password) < 8:
        result = await db.execute(select(User).order_by(User.created_at.desc()))
        users = result.scalars().all()
        return templates.TemplateResponse(
            request,
            "users/list.html",
            context={
                "user": user,
                "users": users,
                "default_admin_username": DEFAULT_ADMIN_USERNAME,
                "messages": [{"category": "error", "text": "Password must be at least 8 characters."}],
            },
        )

    if role not in ("admin", "staff"):
        role = "staff"

    result = await db.execute(select(User).where(User.username == username))
    existing_user = result.scalar_one_or_none()

    if existing_user is not None:
        result = await db.execute(select(User).order_by(User.created_at.desc()))
        users = result.scalars().all()
        return templates.TemplateResponse(
            request,
            "users/list.html",
            context={
                "user": user,
                "users": users,
                "default_admin_username": DEFAULT_ADMIN_USERNAME,
                "messages": [{"category": "error", "text": f"Username '{username}' is already taken."}],
            },
        )

    new_user = User(
        username=username,
        display_name=display_name,
        role=role,
    )
    new_user.set_password(password)
    db.add(new_user)
    await db.flush()

    return RedirectResponse(url="/users/", status_code=303)


@router.post("/users/{user_id}/delete")
async def delete_user(
    request: Request,
    user_id: int,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    if user_id == user.id:
        result = await db.execute(select(User).order_by(User.created_at.desc()))
        users = result.scalars().all()
        return templates.TemplateResponse(
            request,
            "users/list.html",
            context={
                "user": user,
                "users": users,
                "default_admin_username": DEFAULT_ADMIN_USERNAME,
                "messages": [{"category": "error", "text": "You cannot delete your own account."}],
            },
        )

    result = await db.execute(select(User).where(User.id == user_id))
    target_user = result.scalar_one_or_none()

    if target_user is None:
        result = await db.execute(select(User).order_by(User.created_at.desc()))
        users = result.scalars().all()
        return templates.TemplateResponse(
            request,
            "users/list.html",
            context={
                "user": user,
                "users": users,
                "default_admin_username": DEFAULT_ADMIN_USERNAME,
                "messages": [{"category": "error", "text": "User not found."}],
            },
        )

    if target_user.username == DEFAULT_ADMIN_USERNAME:
        result = await db.execute(select(User).order_by(User.created_at.desc()))
        users = result.scalars().all()
        return templates.TemplateResponse(
            request,
            "users/list.html",
            context={
                "user": user,
                "users": users,
                "default_admin_username": DEFAULT_ADMIN_USERNAME,
                "messages": [{"category": "error", "text": "Cannot delete the default admin account."}],
            },
        )

    await db.delete(target_user)
    await db.flush()

    return RedirectResponse(url="/users/", status_code=303)
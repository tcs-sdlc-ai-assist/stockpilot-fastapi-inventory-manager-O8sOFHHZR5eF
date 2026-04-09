import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from dependencies import require_admin
from models.category import Category
from models.item import InventoryItem
from models.user import User

router = APIRouter()

templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parent.parent / "templates")
)


@router.get("/categories/")
async def list_categories(
    request: Request,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(
            Category,
            func.count(InventoryItem.id).label("item_count"),
        )
        .outerjoin(InventoryItem, InventoryItem.category_id == Category.id)
        .group_by(Category.id)
        .order_by(Category.name)
    )
    rows = result.all()

    categories = []
    for row in rows:
        category = row[0]
        category.item_count = row[1]
        categories.append(category)

    messages = []
    flash = request.cookies.get("flash_message")
    flash_cat = request.cookies.get("flash_category", "info")
    if flash:
        messages.append({"text": flash, "category": flash_cat})

    response = templates.TemplateResponse(
        request,
        "categories/list.html",
        context={
            "user": user,
            "categories": categories,
            "messages": messages,
        },
    )

    if flash:
        response.delete_cookie("flash_message")
        response.delete_cookie("flash_category")

    return response


@router.post("/categories/add")
async def add_category(
    request: Request,
    name: str = Form(...),
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    clean_name = name.strip()

    if not clean_name:
        response = RedirectResponse(url="/categories/", status_code=303)
        response.set_cookie("flash_message", "Category name cannot be empty.", max_age=10)
        response.set_cookie("flash_category", "error", max_age=10)
        return response

    if len(clean_name) > 32:
        response = RedirectResponse(url="/categories/", status_code=303)
        response.set_cookie(
            "flash_message",
            "Category name must be 32 characters or fewer.",
            max_age=10,
        )
        response.set_cookie("flash_category", "error", max_age=10)
        return response

    result = await db.execute(
        select(Category).where(func.lower(Category.name) == clean_name.lower())
    )
    existing = result.scalar_one_or_none()

    if existing is not None:
        response = RedirectResponse(url="/categories/", status_code=303)
        response.set_cookie(
            "flash_message",
            f"Category '{clean_name}' already exists.",
            max_age=10,
        )
        response.set_cookie("flash_category", "error", max_age=10)
        return response

    category = Category(name=clean_name)
    db.add(category)
    await db.flush()

    response = RedirectResponse(url="/categories/", status_code=303)
    response.set_cookie(
        "flash_message",
        f"Category '{clean_name}' created successfully.",
        max_age=10,
    )
    response.set_cookie("flash_category", "success", max_age=10)
    return response


@router.post("/categories/{category_id}/delete")
async def delete_category(
    request: Request,
    category_id: int,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Category).where(Category.id == category_id))
    category = result.scalar_one_or_none()

    if category is None:
        response = RedirectResponse(url="/categories/", status_code=303)
        response.set_cookie("flash_message", "Category not found.", max_age=10)
        response.set_cookie("flash_category", "error", max_age=10)
        return response

    item_count_result = await db.execute(
        select(func.count(InventoryItem.id)).where(
            InventoryItem.category_id == category_id
        )
    )
    item_count = item_count_result.scalar() or 0

    if item_count > 0:
        response = RedirectResponse(url="/categories/", status_code=303)
        response.set_cookie(
            "flash_message",
            f"Cannot delete category '{category.name}' because it has {item_count} item{'s' if item_count != 1 else ''} assigned.",
            max_age=10,
        )
        response.set_cookie("flash_category", "error", max_age=10)
        return response

    category_name = category.name
    await db.delete(category)
    await db.flush()

    response = RedirectResponse(url="/categories/", status_code=303)
    response.set_cookie(
        "flash_message",
        f"Category '{category_name}' deleted successfully.",
        max_age=10,
    )
    response.set_cookie("flash_category", "success", max_age=10)
    return response
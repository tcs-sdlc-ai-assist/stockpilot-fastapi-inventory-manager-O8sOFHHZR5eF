import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import datetime

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database import get_db
from dependencies import require_auth
from models.activity_log import ActivityLog
from models.category import Category
from models.item import InventoryItem
from models.user import User

router = APIRouter()

templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))


@router.get("/inventory/")
async def inventory_list(
    request: Request,
    search: str = "",
    category_id: str = "",
    sort: str = "name",
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(InventoryItem).options(
        selectinload(InventoryItem.category),
        selectinload(InventoryItem.owner),
    )

    if search:
        stmt = stmt.where(InventoryItem.name.ilike(f"%{search}%"))

    selected_category_id = None
    if category_id:
        try:
            selected_category_id = int(category_id)
            stmt = stmt.where(InventoryItem.category_id == selected_category_id)
        except (ValueError, TypeError):
            selected_category_id = None

    if sort == "name":
        stmt = stmt.order_by(InventoryItem.name.asc())
    elif sort == "name_desc":
        stmt = stmt.order_by(InventoryItem.name.desc())
    elif sort == "quantity":
        stmt = stmt.order_by(InventoryItem.quantity.asc())
    elif sort == "quantity_desc":
        stmt = stmt.order_by(InventoryItem.quantity.desc())
    elif sort == "updated_at":
        stmt = stmt.order_by(InventoryItem.updated_at.asc())
    elif sort == "updated_at_desc":
        stmt = stmt.order_by(InventoryItem.updated_at.desc())
    else:
        stmt = stmt.order_by(InventoryItem.name.asc())

    result = await db.execute(stmt)
    items = result.scalars().all()

    cat_result = await db.execute(select(Category).order_by(Category.name.asc()))
    categories = cat_result.scalars().all()

    return templates.TemplateResponse(
        request,
        "inventory/list.html",
        context={
            "user": user,
            "items": items,
            "categories": categories,
            "search": search,
            "selected_category_id": selected_category_id,
            "sort": sort,
            "now": datetime.utcnow(),
        },
    )


@router.get("/inventory/add")
async def inventory_add_form(
    request: Request,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    cat_result = await db.execute(select(Category).order_by(Category.name.asc()))
    categories = cat_result.scalars().all()

    return templates.TemplateResponse(
        request,
        "inventory/form.html",
        context={
            "user": user,
            "item": None,
            "categories": categories,
            "now": datetime.utcnow(),
        },
    )


@router.post("/inventory/add")
async def inventory_add(
    request: Request,
    name: str = Form(...),
    category_id: int = Form(...),
    quantity: int = Form(0),
    unit: str = Form(""),
    unit_price: float = Form(0.0),
    reorder_level: int = Form(0),
    description: str = Form(""),
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    cat_result = await db.execute(select(Category).order_by(Category.name.asc()))
    categories = cat_result.scalars().all()

    name = name.strip()
    if not name:
        return templates.TemplateResponse(
            request,
            "inventory/form.html",
            context={
                "user": user,
                "item": None,
                "categories": categories,
                "messages": [{"category": "error", "text": "Item name is required."}],
                "now": datetime.utcnow(),
            },
        )

    item = InventoryItem(
        name=name,
        description=description.strip() if description else None,
        category_id=category_id,
        owner_id=user.id,
        quantity=max(0, quantity),
        unit=unit.strip() if unit else None,
        unit_price=max(0.0, unit_price),
        reorder_level=max(0, reorder_level),
    )
    db.add(item)
    await db.flush()

    activity = ActivityLog(
        action="created",
        item_name=item.name,
        user_id=user.id,
        item_id=item.id,
    )
    db.add(activity)
    await db.flush()

    return RedirectResponse(url=f"/inventory/{item.id}", status_code=303)


@router.get("/inventory/{item_id}")
async def inventory_detail(
    request: Request,
    item_id: int,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(InventoryItem)
        .where(InventoryItem.id == item_id)
        .options(
            selectinload(InventoryItem.category),
            selectinload(InventoryItem.owner),
        )
    )
    item = result.scalar_one_or_none()

    if item is None:
        return templates.TemplateResponse(
            request,
            "errors/404.html",
            context={
                "user": user,
                "now": datetime.utcnow(),
            },
            status_code=404,
        )

    return templates.TemplateResponse(
        request,
        "inventory/detail.html",
        context={
            "user": user,
            "item": item,
            "now": datetime.utcnow(),
        },
    )


@router.get("/inventory/{item_id}/edit")
async def inventory_edit_form(
    request: Request,
    item_id: int,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(InventoryItem)
        .where(InventoryItem.id == item_id)
        .options(
            selectinload(InventoryItem.category),
            selectinload(InventoryItem.owner),
        )
    )
    item = result.scalar_one_or_none()

    if item is None:
        return templates.TemplateResponse(
            request,
            "errors/404.html",
            context={
                "user": user,
                "now": datetime.utcnow(),
            },
            status_code=404,
        )

    if user.role != "admin" and user.id != item.owner_id:
        return RedirectResponse(url=f"/inventory/{item_id}", status_code=303)

    cat_result = await db.execute(select(Category).order_by(Category.name.asc()))
    categories = cat_result.scalars().all()

    return templates.TemplateResponse(
        request,
        "inventory/form.html",
        context={
            "user": user,
            "item": item,
            "categories": categories,
            "now": datetime.utcnow(),
        },
    )


@router.post("/inventory/{item_id}/edit")
async def inventory_edit(
    request: Request,
    item_id: int,
    name: str = Form(...),
    category_id: int = Form(...),
    quantity: int = Form(0),
    unit: str = Form(""),
    unit_price: float = Form(0.0),
    reorder_level: int = Form(0),
    description: str = Form(""),
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(InventoryItem)
        .where(InventoryItem.id == item_id)
        .options(
            selectinload(InventoryItem.category),
            selectinload(InventoryItem.owner),
        )
    )
    item = result.scalar_one_or_none()

    if item is None:
        return templates.TemplateResponse(
            request,
            "errors/404.html",
            context={
                "user": user,
                "now": datetime.utcnow(),
            },
            status_code=404,
        )

    if user.role != "admin" and user.id != item.owner_id:
        return RedirectResponse(url=f"/inventory/{item_id}", status_code=303)

    cat_result = await db.execute(select(Category).order_by(Category.name.asc()))
    categories = cat_result.scalars().all()

    name = name.strip()
    if not name:
        return templates.TemplateResponse(
            request,
            "inventory/form.html",
            context={
                "user": user,
                "item": item,
                "categories": categories,
                "messages": [{"category": "error", "text": "Item name is required."}],
                "now": datetime.utcnow(),
            },
        )

    item.name = name
    item.description = description.strip() if description else None
    item.category_id = category_id
    item.quantity = max(0, quantity)
    item.unit = unit.strip() if unit else None
    item.unit_price = max(0.0, unit_price)
    item.reorder_level = max(0, reorder_level)
    item.updated_at = datetime.utcnow()

    activity = ActivityLog(
        action="updated",
        item_name=item.name,
        user_id=user.id,
        item_id=item.id,
    )
    db.add(activity)
    await db.flush()

    return RedirectResponse(url=f"/inventory/{item.id}", status_code=303)


@router.post("/inventory/{item_id}/delete")
async def inventory_delete(
    request: Request,
    item_id: int,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(InventoryItem)
        .where(InventoryItem.id == item_id)
        .options(
            selectinload(InventoryItem.category),
            selectinload(InventoryItem.owner),
        )
    )
    item = result.scalar_one_or_none()

    if item is None:
        return RedirectResponse(url="/inventory/", status_code=303)

    if user.role != "admin" and user.id != item.owner_id:
        return RedirectResponse(url=f"/inventory/{item_id}", status_code=303)

    item_name = item.name

    activity = ActivityLog(
        action="deleted",
        item_name=item_name,
        user_id=user.id,
        item_id=None,
    )
    db.add(activity)

    await db.delete(item)
    await db.flush()

    return RedirectResponse(url="/inventory/", status_code=303)
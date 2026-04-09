import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database import get_db
from dependencies import require_admin
from models.activity_log import ActivityLog
from models.item import InventoryItem
from models.user import User

router = APIRouter()

templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))


@router.get("/dashboard/")
async def dashboard(
    request: Request,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> Response:
    total_items_result = await db.execute(select(func.count(InventoryItem.id)))
    total_items = total_items_result.scalar() or 0

    total_value_result = await db.execute(
        select(func.coalesce(func.sum(InventoryItem.quantity * InventoryItem.unit_price), 0.0))
    )
    total_value = total_value_result.scalar() or 0.0

    low_stock_result = await db.execute(
        select(InventoryItem)
        .where(InventoryItem.quantity <= InventoryItem.reorder_level)
        .options(
            selectinload(InventoryItem.category),
            selectinload(InventoryItem.owner),
        )
        .order_by(InventoryItem.quantity.asc())
    )
    low_stock_items = list(low_stock_result.scalars().all())

    total_users_result = await db.execute(select(func.count(User.id)))
    total_users = total_users_result.scalar() or 0

    recent_activity_result = await db.execute(
        select(ActivityLog)
        .options(
            selectinload(ActivityLog.user),
            selectinload(ActivityLog.item),
        )
        .order_by(ActivityLog.timestamp.desc())
        .limit(5)
    )
    recent_activity = list(recent_activity_result.scalars().all())

    return templates.TemplateResponse(
        request,
        "dashboard/index.html",
        context={
            "user": user,
            "total_items": total_items,
            "total_value": total_value,
            "low_stock_items": low_stock_items,
            "total_users": total_users,
            "recent_activity": recent_activity,
        },
    )
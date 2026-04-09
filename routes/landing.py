import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import datetime

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from dependencies import get_current_user
from models.user import User

router = APIRouter()

templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))


@router.get("/")
async def landing_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Response:
    user = await get_current_user(request, db)
    return templates.TemplateResponse(
        request,
        "landing.html",
        context={
            "user": user,
            "now": datetime.utcnow(),
            "messages": [],
        },
    )
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from database import create_tables
from seed import seed_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()
    await seed_database()
    yield


app = FastAPI(
    title="StockPilot",
    description="Intelligent Inventory Management System",
    version="1.0.0",
    lifespan=lifespan,
)

base_dir = Path(__file__).resolve().parent

static_path = base_dir / "static"
static_path.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

templates = Jinja2Templates(directory=str(base_dir / "templates"))

from routes import (
    auth_router,
    categories_router,
    dashboard_router,
    inventory_router,
    landing_router,
    users_router,
)

app.include_router(landing_router)
app.include_router(auth_router)
app.include_router(inventory_router)
app.include_router(categories_router)
app.include_router(dashboard_router)
app.include_router(users_router)


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    from dependencies import get_current_user
    from database import async_session

    user = None
    try:
        async with async_session() as db:
            user = await _get_user_from_request(request, db)
    except Exception:
        pass

    from datetime import datetime

    return templates.TemplateResponse(
        request,
        "errors/404.html",
        context={
            "user": user,
            "now": datetime.utcnow(),
            "messages": [],
        },
        status_code=404,
    )


async def _get_user_from_request(request: Request, db):
    from config import SESSION_COOKIE_NAME
    from dependencies import decode_session_token
    from sqlalchemy import select
    from models.user import User

    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        return None

    data = decode_session_token(token)
    if data is None:
        return None

    user_id = data.get("user_id")
    if user_id is None:
        return None

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    return user
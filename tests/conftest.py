import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))

import asyncio
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from database import Base, get_db
from models.category import Category
from models.item import InventoryItem
from models.user import User


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def test_engine():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        future=True,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def test_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    test_async_session = sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with test_async_session() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def client(test_engine) -> AsyncGenerator[AsyncClient, None]:
    test_async_session = sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async def override_get_db():
        async with test_async_session() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    from main import app

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def admin_user(test_session: AsyncSession) -> User:
    user = User(
        username="testadmin",
        display_name="Test Admin",
        role="admin",
        is_default_admin=True,
    )
    user.set_password("adminpass123")
    test_session.add(user)
    await test_session.commit()
    await test_session.refresh(user)
    return user


@pytest_asyncio.fixture(scope="function")
async def staff_user(test_session: AsyncSession) -> User:
    user = User(
        username="teststaff",
        display_name="Test Staff",
        role="staff",
        is_default_admin=False,
    )
    user.set_password("staffpass123")
    test_session.add(user)
    await test_session.commit()
    await test_session.refresh(user)
    return user


@pytest_asyncio.fixture(scope="function")
async def admin_client(client: AsyncClient, admin_user: User) -> AsyncClient:
    from dependencies import create_session_token
    from config import SESSION_COOKIE_NAME

    token = create_session_token(admin_user.id)
    client.cookies.set(SESSION_COOKIE_NAME, token)
    return client


@pytest_asyncio.fixture(scope="function")
async def staff_client(client: AsyncClient, staff_user: User) -> AsyncClient:
    from dependencies import create_session_token
    from config import SESSION_COOKIE_NAME

    token = create_session_token(staff_user.id)
    client.cookies.set(SESSION_COOKIE_NAME, token)
    return client


@pytest_asyncio.fixture(scope="function")
async def sample_categories(test_session: AsyncSession) -> list[Category]:
    categories = []
    for name in ["Electronics", "Furniture", "Office Supplies"]:
        category = Category(name=name)
        test_session.add(category)
        categories.append(category)
    await test_session.commit()
    for cat in categories:
        await test_session.refresh(cat)
    return categories


@pytest_asyncio.fixture(scope="function")
async def sample_items(
    test_session: AsyncSession,
    sample_categories: list[Category],
    admin_user: User,
) -> list[InventoryItem]:
    items = []
    item1 = InventoryItem(
        name="Laptop",
        description="A high-end laptop",
        quantity=50,
        unit="pcs",
        unit_price=999.99,
        reorder_level=10,
        category_id=sample_categories[0].id,
        owner_id=admin_user.id,
    )
    test_session.add(item1)
    items.append(item1)

    item2 = InventoryItem(
        name="Office Chair",
        description="Ergonomic office chair",
        quantity=5,
        unit="pcs",
        unit_price=299.50,
        reorder_level=10,
        category_id=sample_categories[1].id,
        owner_id=admin_user.id,
    )
    test_session.add(item2)
    items.append(item2)

    item3 = InventoryItem(
        name="Stapler",
        description="Heavy duty stapler",
        quantity=0,
        unit="pcs",
        unit_price=12.99,
        reorder_level=5,
        category_id=sample_categories[2].id,
        owner_id=admin_user.id,
    )
    test_session.add(item3)
    items.append(item3)

    await test_session.commit()
    for item in items:
        await test_session.refresh(item)
    return items
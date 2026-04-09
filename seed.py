import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from sqlalchemy import select

from config import DEFAULT_ADMIN_PASSWORD, DEFAULT_ADMIN_USERNAME
from database import async_session
from models.category import Category
from models.user import User

DEFAULT_CATEGORIES = [
    "Electronics",
    "Furniture",
    "Office Supplies",
    "Food & Beverage",
    "Clothing",
    "Tools",
    "Raw Materials",
    "Other",
]


async def seed_database() -> None:
    async with async_session() as session:
        try:
            result = await session.execute(
                select(User).where(User.username == DEFAULT_ADMIN_USERNAME)
            )
            admin_user = result.scalars().first()

            if admin_user is None:
                admin_user = User(
                    username=DEFAULT_ADMIN_USERNAME,
                    display_name="Administrator",
                    role="admin",
                    is_default_admin=True,
                )
                admin_user.set_password(DEFAULT_ADMIN_PASSWORD)
                session.add(admin_user)
                await session.flush()

            for category_name in DEFAULT_CATEGORIES:
                result = await session.execute(
                    select(Category).where(Category.name == category_name)
                )
                existing_category = result.scalars().first()

                if existing_category is None:
                    category = Category(name=category_name)
                    session.add(category)

            await session.commit()
        except Exception:
            await session.rollback()
            raise
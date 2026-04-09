import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User
from models.category import Category
from models.item import InventoryItem


class TestAdminOnlyRoutesUnauthenticated:
    """Unauthenticated users should be redirected to /login for admin-only routes."""

    @pytest.mark.asyncio
    async def test_dashboard_redirects_unauthenticated(self, client: AsyncClient):
        response = await client.get("/dashboard/", follow_redirects=False)
        assert response.status_code == 302
        assert "/login" in response.headers.get("location", "")

    @pytest.mark.asyncio
    async def test_categories_redirects_unauthenticated(self, client: AsyncClient):
        response = await client.get("/categories/", follow_redirects=False)
        assert response.status_code == 302
        assert "/login" in response.headers.get("location", "")

    @pytest.mark.asyncio
    async def test_users_redirects_unauthenticated(self, client: AsyncClient):
        response = await client.get("/users/", follow_redirects=False)
        assert response.status_code == 302
        assert "/login" in response.headers.get("location", "")

    @pytest.mark.asyncio
    async def test_add_category_redirects_unauthenticated(self, client: AsyncClient):
        response = await client.post(
            "/categories/add",
            data={"name": "TestCategory"},
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert "/login" in response.headers.get("location", "")

    @pytest.mark.asyncio
    async def test_delete_category_redirects_unauthenticated(self, client: AsyncClient):
        response = await client.post(
            "/categories/1/delete",
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert "/login" in response.headers.get("location", "")

    @pytest.mark.asyncio
    async def test_add_user_redirects_unauthenticated(self, client: AsyncClient):
        response = await client.post(
            "/users/add",
            data={
                "display_name": "New User",
                "username": "newuser",
                "password": "password123",
                "role": "staff",
            },
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert "/login" in response.headers.get("location", "")

    @pytest.mark.asyncio
    async def test_delete_user_redirects_unauthenticated(self, client: AsyncClient):
        response = await client.post(
            "/users/1/delete",
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert "/login" in response.headers.get("location", "")


class TestAdminOnlyRoutesStaffUser:
    """Staff users should be redirected away from admin-only routes."""

    @pytest.mark.asyncio
    async def test_dashboard_redirects_staff(self, staff_client: AsyncClient):
        response = await staff_client.get("/dashboard/", follow_redirects=False)
        assert response.status_code == 302
        assert "/login" not in response.headers.get("location", "") or "/" in response.headers.get("location", "")

    @pytest.mark.asyncio
    async def test_categories_redirects_staff(self, staff_client: AsyncClient):
        response = await staff_client.get("/categories/", follow_redirects=False)
        assert response.status_code == 302

    @pytest.mark.asyncio
    async def test_users_redirects_staff(self, staff_client: AsyncClient):
        response = await staff_client.get("/users/", follow_redirects=False)
        assert response.status_code == 302

    @pytest.mark.asyncio
    async def test_add_category_redirects_staff(self, staff_client: AsyncClient):
        response = await staff_client.post(
            "/categories/add",
            data={"name": "StaffCategory"},
            follow_redirects=False,
        )
        assert response.status_code == 302

    @pytest.mark.asyncio
    async def test_delete_category_redirects_staff(self, staff_client: AsyncClient):
        response = await staff_client.post(
            "/categories/1/delete",
            follow_redirects=False,
        )
        assert response.status_code == 302

    @pytest.mark.asyncio
    async def test_add_user_redirects_staff(self, staff_client: AsyncClient):
        response = await staff_client.post(
            "/users/add",
            data={
                "display_name": "Hacker",
                "username": "hacker",
                "password": "password123",
                "role": "admin",
            },
            follow_redirects=False,
        )
        assert response.status_code == 302

    @pytest.mark.asyncio
    async def test_delete_user_redirects_staff(self, staff_client: AsyncClient):
        response = await staff_client.post(
            "/users/1/delete",
            follow_redirects=False,
        )
        assert response.status_code == 302


class TestAdminRoutesAccessible:
    """Admin users should be able to access admin-only routes."""

    @pytest.mark.asyncio
    async def test_dashboard_accessible_by_admin(self, admin_client: AsyncClient):
        response = await admin_client.get("/dashboard/", follow_redirects=False)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_categories_accessible_by_admin(self, admin_client: AsyncClient):
        response = await admin_client.get("/categories/", follow_redirects=False)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_users_accessible_by_admin(self, admin_client: AsyncClient):
        response = await admin_client.get("/users/", follow_redirects=False)
        assert response.status_code == 200


class TestInventoryOwnershipEnforcement:
    """Tests that inventory edit/delete respects ownership rules."""

    @pytest.mark.asyncio
    async def test_staff_cannot_edit_others_item(
        self,
        staff_client: AsyncClient,
        sample_items: list[InventoryItem],
    ):
        item = sample_items[0]
        response = await staff_client.get(
            f"/inventory/{item.id}/edit",
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert f"/inventory/{item.id}" in response.headers.get("location", "")

    @pytest.mark.asyncio
    async def test_staff_cannot_post_edit_others_item(
        self,
        staff_client: AsyncClient,
        sample_items: list[InventoryItem],
        sample_categories: list[Category],
    ):
        item = sample_items[0]
        response = await staff_client.post(
            f"/inventory/{item.id}/edit",
            data={
                "name": "Hacked Name",
                "category_id": str(sample_categories[0].id),
                "quantity": "999",
                "unit": "pcs",
                "unit_price": "1.00",
                "reorder_level": "0",
                "description": "hacked",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert f"/inventory/{item.id}" in response.headers.get("location", "")

    @pytest.mark.asyncio
    async def test_staff_cannot_delete_others_item(
        self,
        staff_client: AsyncClient,
        sample_items: list[InventoryItem],
    ):
        item = sample_items[0]
        response = await staff_client.post(
            f"/inventory/{item.id}/delete",
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert f"/inventory/{item.id}" in response.headers.get("location", "")

    @pytest.mark.asyncio
    async def test_admin_can_edit_any_item(
        self,
        admin_client: AsyncClient,
        sample_items: list[InventoryItem],
        sample_categories: list[Category],
    ):
        item = sample_items[0]
        response = await admin_client.get(
            f"/inventory/{item.id}/edit",
            follow_redirects=False,
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_admin_can_delete_any_item(
        self,
        admin_client: AsyncClient,
        sample_items: list[InventoryItem],
    ):
        item = sample_items[0]
        response = await admin_client.post(
            f"/inventory/{item.id}/delete",
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert "/inventory/" in response.headers.get("location", "")

    @pytest.mark.asyncio
    async def test_owner_can_edit_own_item(
        self,
        test_session: AsyncSession,
        client: AsyncClient,
        sample_categories: list[Category],
    ):
        from dependencies import create_session_token
        from config import SESSION_COOKIE_NAME

        staff = User(
            username="itemowner",
            display_name="Item Owner",
            role="staff",
            is_default_admin=False,
        )
        staff.set_password("ownerpass123")
        test_session.add(staff)
        await test_session.commit()
        await test_session.refresh(staff)

        item = InventoryItem(
            name="Owner Item",
            description="Owned by staff",
            quantity=10,
            unit="pcs",
            unit_price=5.00,
            reorder_level=2,
            category_id=sample_categories[0].id,
            owner_id=staff.id,
        )
        test_session.add(item)
        await test_session.commit()
        await test_session.refresh(item)

        token = create_session_token(staff.id)
        client.cookies.set(SESSION_COOKIE_NAME, token)

        response = await client.get(
            f"/inventory/{item.id}/edit",
            follow_redirects=False,
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_owner_can_delete_own_item(
        self,
        test_session: AsyncSession,
        client: AsyncClient,
        sample_categories: list[Category],
    ):
        from dependencies import create_session_token
        from config import SESSION_COOKIE_NAME

        staff = User(
            username="itemowner2",
            display_name="Item Owner 2",
            role="staff",
            is_default_admin=False,
        )
        staff.set_password("ownerpass123")
        test_session.add(staff)
        await test_session.commit()
        await test_session.refresh(staff)

        item = InventoryItem(
            name="Owner Item 2",
            description="Owned by staff 2",
            quantity=10,
            unit="pcs",
            unit_price=5.00,
            reorder_level=2,
            category_id=sample_categories[0].id,
            owner_id=staff.id,
        )
        test_session.add(item)
        await test_session.commit()
        await test_session.refresh(item)

        token = create_session_token(staff.id)
        client.cookies.set(SESSION_COOKIE_NAME, token)

        response = await client.post(
            f"/inventory/{item.id}/delete",
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert "/inventory/" in response.headers.get("location", "")


class TestDefaultAdminProtection:
    """Tests that the default admin account cannot be deleted."""

    @pytest.mark.asyncio
    async def test_cannot_delete_default_admin(
        self,
        admin_client: AsyncClient,
        test_session: AsyncSession,
    ):
        from config import DEFAULT_ADMIN_USERNAME

        default_admin = User(
            username=DEFAULT_ADMIN_USERNAME,
            display_name="Default Admin",
            role="admin",
            is_default_admin=True,
        )
        default_admin.set_password("defaultadminpass")
        test_session.add(default_admin)
        await test_session.commit()
        await test_session.refresh(default_admin)

        response = await admin_client.post(
            f"/users/{default_admin.id}/delete",
            follow_redirects=False,
        )
        assert response.status_code == 200
        assert "Cannot delete" in response.text or "default admin" in response.text.lower()

        result = await test_session.execute(
            select(User).where(User.username == DEFAULT_ADMIN_USERNAME)
        )
        user = result.scalar_one_or_none()
        assert user is not None


class TestAdminCannotDeleteSelf:
    """Tests that an admin cannot delete their own account."""

    @pytest.mark.asyncio
    async def test_admin_cannot_delete_self(
        self,
        admin_client: AsyncClient,
        admin_user: User,
        test_session: AsyncSession,
    ):
        response = await admin_client.post(
            f"/users/{admin_user.id}/delete",
            follow_redirects=False,
        )
        assert response.status_code == 200
        assert "cannot delete" in response.text.lower() or "your own" in response.text.lower()

        result = await test_session.execute(
            select(User).where(User.id == admin_user.id)
        )
        user = result.scalar_one_or_none()
        assert user is not None


class TestInventoryAuthRequired:
    """Tests that inventory routes require authentication."""

    @pytest.mark.asyncio
    async def test_inventory_list_requires_auth(self, client: AsyncClient):
        response = await client.get("/inventory/", follow_redirects=False)
        assert response.status_code == 302
        assert "/login" in response.headers.get("location", "")

    @pytest.mark.asyncio
    async def test_inventory_add_form_requires_auth(self, client: AsyncClient):
        response = await client.get("/inventory/add", follow_redirects=False)
        assert response.status_code == 302
        assert "/login" in response.headers.get("location", "")

    @pytest.mark.asyncio
    async def test_inventory_add_post_requires_auth(self, client: AsyncClient):
        response = await client.post(
            "/inventory/add",
            data={
                "name": "Test",
                "category_id": "1",
                "quantity": "10",
                "unit": "pcs",
                "unit_price": "5.00",
                "reorder_level": "2",
                "description": "test",
            },
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert "/login" in response.headers.get("location", "")

    @pytest.mark.asyncio
    async def test_inventory_detail_requires_auth(self, client: AsyncClient):
        response = await client.get("/inventory/1", follow_redirects=False)
        assert response.status_code == 302
        assert "/login" in response.headers.get("location", "")

    @pytest.mark.asyncio
    async def test_inventory_edit_requires_auth(self, client: AsyncClient):
        response = await client.get("/inventory/1/edit", follow_redirects=False)
        assert response.status_code == 302
        assert "/login" in response.headers.get("location", "")

    @pytest.mark.asyncio
    async def test_inventory_delete_requires_auth(self, client: AsyncClient):
        response = await client.post("/inventory/1/delete", follow_redirects=False)
        assert response.status_code == 302
        assert "/login" in response.headers.get("location", "")


class TestStaffCanAccessInventory:
    """Tests that staff users can access basic inventory routes."""

    @pytest.mark.asyncio
    async def test_staff_can_view_inventory_list(self, staff_client: AsyncClient):
        response = await staff_client.get("/inventory/", follow_redirects=False)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_staff_can_view_add_form(self, staff_client: AsyncClient):
        response = await staff_client.get("/inventory/add", follow_redirects=False)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_staff_can_view_item_detail(
        self,
        staff_client: AsyncClient,
        sample_items: list[InventoryItem],
    ):
        item = sample_items[0]
        response = await staff_client.get(
            f"/inventory/{item.id}",
            follow_redirects=False,
        )
        assert response.status_code == 200
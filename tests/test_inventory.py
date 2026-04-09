import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.category import Category
from models.item import InventoryItem
from models.user import User


class TestInventoryListPage:
    """Tests for GET /inventory/ route."""

    @pytest.mark.asyncio
    async def test_inventory_list_requires_auth(self, client: AsyncClient):
        response = await client.get("/inventory/", follow_redirects=False)
        assert response.status_code == 302
        assert "/login" in response.headers.get("location", "")

    @pytest.mark.asyncio
    async def test_inventory_list_renders_for_staff(
        self, staff_client: AsyncClient, sample_items: list[InventoryItem]
    ):
        response = await staff_client.get("/inventory/")
        assert response.status_code == 200
        assert "Inventory" in response.text
        assert "Laptop" in response.text
        assert "Office Chair" in response.text
        assert "Stapler" in response.text

    @pytest.mark.asyncio
    async def test_inventory_list_renders_for_admin(
        self, admin_client: AsyncClient, sample_items: list[InventoryItem]
    ):
        response = await admin_client.get("/inventory/")
        assert response.status_code == 200
        assert "Inventory" in response.text
        assert "Laptop" in response.text

    @pytest.mark.asyncio
    async def test_inventory_list_empty(self, staff_client: AsyncClient):
        response = await staff_client.get("/inventory/")
        assert response.status_code == 200
        assert "No inventory items found" in response.text

    @pytest.mark.asyncio
    async def test_inventory_list_search(
        self, staff_client: AsyncClient, sample_items: list[InventoryItem]
    ):
        response = await staff_client.get("/inventory/?search=Laptop")
        assert response.status_code == 200
        assert "Laptop" in response.text
        assert "Office Chair" not in response.text

    @pytest.mark.asyncio
    async def test_inventory_list_search_no_results(
        self, staff_client: AsyncClient, sample_items: list[InventoryItem]
    ):
        response = await staff_client.get("/inventory/?search=NonExistentItem")
        assert response.status_code == 200
        assert "No inventory items found" in response.text

    @pytest.mark.asyncio
    async def test_inventory_list_filter_by_category(
        self,
        staff_client: AsyncClient,
        sample_items: list[InventoryItem],
        sample_categories: list[Category],
    ):
        electronics_id = sample_categories[0].id
        response = await staff_client.get(f"/inventory/?category_id={electronics_id}")
        assert response.status_code == 200
        assert "Laptop" in response.text
        assert "Office Chair" not in response.text

    @pytest.mark.asyncio
    async def test_inventory_list_sort_by_name_asc(
        self, staff_client: AsyncClient, sample_items: list[InventoryItem]
    ):
        response = await staff_client.get("/inventory/?sort=name")
        assert response.status_code == 200
        text = response.text
        laptop_pos = text.find("Laptop")
        chair_pos = text.find("Office Chair")
        stapler_pos = text.find("Stapler")
        assert laptop_pos < chair_pos < stapler_pos

    @pytest.mark.asyncio
    async def test_inventory_list_sort_by_name_desc(
        self, staff_client: AsyncClient, sample_items: list[InventoryItem]
    ):
        response = await staff_client.get("/inventory/?sort=name_desc")
        assert response.status_code == 200
        text = response.text
        stapler_pos = text.find("Stapler")
        chair_pos = text.find("Office Chair")
        laptop_pos = text.find("Laptop")
        assert stapler_pos < chair_pos < laptop_pos

    @pytest.mark.asyncio
    async def test_inventory_list_sort_by_quantity(
        self, staff_client: AsyncClient, sample_items: list[InventoryItem]
    ):
        response = await staff_client.get("/inventory/?sort=quantity")
        assert response.status_code == 200
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_inventory_list_sort_by_quantity_desc(
        self, staff_client: AsyncClient, sample_items: list[InventoryItem]
    ):
        response = await staff_client.get("/inventory/?sort=quantity_desc")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_inventory_list_low_stock_highlighting(
        self, staff_client: AsyncClient, sample_items: list[InventoryItem]
    ):
        response = await staff_client.get("/inventory/")
        assert response.status_code == 200
        assert "Low Stock" in response.text
        assert "Out of Stock" in response.text


class TestInventoryAddItem:
    """Tests for GET/POST /inventory/add route."""

    @pytest.mark.asyncio
    async def test_add_form_requires_auth(self, client: AsyncClient):
        response = await client.get("/inventory/add", follow_redirects=False)
        assert response.status_code == 302
        assert "/login" in response.headers.get("location", "")

    @pytest.mark.asyncio
    async def test_add_form_renders(
        self,
        staff_client: AsyncClient,
        sample_categories: list[Category],
    ):
        response = await staff_client.get("/inventory/add")
        assert response.status_code == 200
        assert "Add" in response.text
        assert "Electronics" in response.text

    @pytest.mark.asyncio
    async def test_add_item_success(
        self,
        staff_client: AsyncClient,
        sample_categories: list[Category],
    ):
        response = await staff_client.post(
            "/inventory/add",
            data={
                "name": "New Widget",
                "category_id": sample_categories[0].id,
                "quantity": 25,
                "unit": "pcs",
                "unit_price": 15.99,
                "reorder_level": 5,
                "description": "A brand new widget",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert "/inventory/" in response.headers.get("location", "")

    @pytest.mark.asyncio
    async def test_add_item_empty_name(
        self,
        staff_client: AsyncClient,
        sample_categories: list[Category],
    ):
        response = await staff_client.post(
            "/inventory/add",
            data={
                "name": "   ",
                "category_id": sample_categories[0].id,
                "quantity": 10,
                "unit": "pcs",
                "unit_price": 5.00,
                "reorder_level": 2,
                "description": "",
            },
        )
        assert response.status_code == 200
        assert "Item name is required" in response.text

    @pytest.mark.asyncio
    async def test_add_item_creates_activity_log(
        self,
        staff_client: AsyncClient,
        sample_categories: list[Category],
        test_session: AsyncSession,
    ):
        response = await staff_client.post(
            "/inventory/add",
            data={
                "name": "Activity Log Test Item",
                "category_id": sample_categories[0].id,
                "quantity": 10,
                "unit": "pcs",
                "unit_price": 9.99,
                "reorder_level": 2,
                "description": "",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303

        from models.activity_log import ActivityLog

        result = await test_session.execute(
            select(ActivityLog).where(ActivityLog.item_name == "Activity Log Test Item")
        )
        log = result.scalar_one_or_none()
        assert log is not None
        assert log.action == "created"

    @pytest.mark.asyncio
    async def test_add_item_post_requires_auth(self, client: AsyncClient):
        response = await client.post(
            "/inventory/add",
            data={
                "name": "Unauthorized Item",
                "category_id": 1,
                "quantity": 1,
                "unit": "pcs",
                "unit_price": 1.00,
                "reorder_level": 0,
                "description": "",
            },
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert "/login" in response.headers.get("location", "")


class TestInventoryDetailPage:
    """Tests for GET /inventory/{item_id} route."""

    @pytest.mark.asyncio
    async def test_detail_requires_auth(
        self, client: AsyncClient, sample_items: list[InventoryItem]
    ):
        response = await client.get(
            f"/inventory/{sample_items[0].id}", follow_redirects=False
        )
        assert response.status_code == 302
        assert "/login" in response.headers.get("location", "")

    @pytest.mark.asyncio
    async def test_detail_renders(
        self, staff_client: AsyncClient, sample_items: list[InventoryItem]
    ):
        response = await staff_client.get(f"/inventory/{sample_items[0].id}")
        assert response.status_code == 200
        assert "Laptop" in response.text
        assert "999.99" in response.text
        assert "Electronics" in response.text

    @pytest.mark.asyncio
    async def test_detail_not_found(self, staff_client: AsyncClient):
        response = await staff_client.get("/inventory/99999")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_detail_low_stock_warning(
        self, staff_client: AsyncClient, sample_items: list[InventoryItem]
    ):
        low_stock_item = sample_items[1]
        response = await staff_client.get(f"/inventory/{low_stock_item.id}")
        assert response.status_code == 200
        assert "Low Stock Warning" in response.text

    @pytest.mark.asyncio
    async def test_detail_out_of_stock_warning(
        self, staff_client: AsyncClient, sample_items: list[InventoryItem]
    ):
        out_of_stock_item = sample_items[2]
        response = await staff_client.get(f"/inventory/{out_of_stock_item.id}")
        assert response.status_code == 200
        assert "Low Stock Warning" in response.text


class TestInventoryEditItem:
    """Tests for GET/POST /inventory/{item_id}/edit route."""

    @pytest.mark.asyncio
    async def test_edit_form_requires_auth(
        self, client: AsyncClient, sample_items: list[InventoryItem]
    ):
        response = await client.get(
            f"/inventory/{sample_items[0].id}/edit", follow_redirects=False
        )
        assert response.status_code == 302
        assert "/login" in response.headers.get("location", "")

    @pytest.mark.asyncio
    async def test_edit_form_renders_for_owner(
        self, admin_client: AsyncClient, sample_items: list[InventoryItem]
    ):
        response = await admin_client.get(f"/inventory/{sample_items[0].id}/edit")
        assert response.status_code == 200
        assert "Edit" in response.text
        assert "Laptop" in response.text

    @pytest.mark.asyncio
    async def test_edit_form_not_found(self, admin_client: AsyncClient):
        response = await admin_client.get("/inventory/99999/edit")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_staff_cannot_edit_others_item(
        self, staff_client: AsyncClient, sample_items: list[InventoryItem]
    ):
        response = await staff_client.get(
            f"/inventory/{sample_items[0].id}/edit", follow_redirects=False
        )
        assert response.status_code == 303
        assert f"/inventory/{sample_items[0].id}" in response.headers.get(
            "location", ""
        )

    @pytest.mark.asyncio
    async def test_admin_can_edit_any_item(
        self, admin_client: AsyncClient, sample_items: list[InventoryItem]
    ):
        response = await admin_client.get(f"/inventory/{sample_items[0].id}/edit")
        assert response.status_code == 200
        assert "Edit" in response.text

    @pytest.mark.asyncio
    async def test_edit_item_success(
        self,
        admin_client: AsyncClient,
        sample_items: list[InventoryItem],
        sample_categories: list[Category],
    ):
        item = sample_items[0]
        response = await admin_client.post(
            f"/inventory/{item.id}/edit",
            data={
                "name": "Updated Laptop",
                "category_id": sample_categories[0].id,
                "quantity": 100,
                "unit": "pcs",
                "unit_price": 1099.99,
                "reorder_level": 15,
                "description": "Updated description",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert f"/inventory/{item.id}" in response.headers.get("location", "")

    @pytest.mark.asyncio
    async def test_edit_item_empty_name(
        self,
        admin_client: AsyncClient,
        sample_items: list[InventoryItem],
        sample_categories: list[Category],
    ):
        item = sample_items[0]
        response = await admin_client.post(
            f"/inventory/{item.id}/edit",
            data={
                "name": "   ",
                "category_id": sample_categories[0].id,
                "quantity": 100,
                "unit": "pcs",
                "unit_price": 1099.99,
                "reorder_level": 15,
                "description": "",
            },
        )
        assert response.status_code == 200
        assert "Item name is required" in response.text

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
                "category_id": sample_categories[0].id,
                "quantity": 999,
                "unit": "pcs",
                "unit_price": 0.01,
                "reorder_level": 0,
                "description": "",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert f"/inventory/{item.id}" in response.headers.get("location", "")

    @pytest.mark.asyncio
    async def test_edit_item_not_found(
        self, admin_client: AsyncClient, sample_categories: list[Category]
    ):
        response = await admin_client.post(
            "/inventory/99999/edit",
            data={
                "name": "Ghost Item",
                "category_id": sample_categories[0].id,
                "quantity": 1,
                "unit": "pcs",
                "unit_price": 1.00,
                "reorder_level": 0,
                "description": "",
            },
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_edit_creates_activity_log(
        self,
        admin_client: AsyncClient,
        sample_items: list[InventoryItem],
        sample_categories: list[Category],
        test_session: AsyncSession,
    ):
        item = sample_items[0]
        await admin_client.post(
            f"/inventory/{item.id}/edit",
            data={
                "name": "Laptop Pro",
                "category_id": sample_categories[0].id,
                "quantity": 75,
                "unit": "pcs",
                "unit_price": 1299.99,
                "reorder_level": 10,
                "description": "Upgraded laptop",
            },
            follow_redirects=False,
        )

        from models.activity_log import ActivityLog

        result = await test_session.execute(
            select(ActivityLog).where(
                ActivityLog.item_id == item.id, ActivityLog.action == "updated"
            )
        )
        log = result.scalar_one_or_none()
        assert log is not None
        assert log.item_name == "Laptop Pro"

    @pytest.mark.asyncio
    async def test_staff_can_edit_own_item(
        self,
        staff_client: AsyncClient,
        staff_user: User,
        sample_categories: list[Category],
        test_session: AsyncSession,
    ):
        item = InventoryItem(
            name="Staff Item",
            description="Owned by staff",
            quantity=10,
            unit="pcs",
            unit_price=5.00,
            reorder_level=2,
            category_id=sample_categories[0].id,
            owner_id=staff_user.id,
        )
        test_session.add(item)
        await test_session.commit()
        await test_session.refresh(item)

        response = await staff_client.get(f"/inventory/{item.id}/edit")
        assert response.status_code == 200
        assert "Staff Item" in response.text

        response = await staff_client.post(
            f"/inventory/{item.id}/edit",
            data={
                "name": "Updated Staff Item",
                "category_id": sample_categories[0].id,
                "quantity": 20,
                "unit": "pcs",
                "unit_price": 7.50,
                "reorder_level": 3,
                "description": "Updated by staff",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303


class TestInventoryDeleteItem:
    """Tests for POST /inventory/{item_id}/delete route."""

    @pytest.mark.asyncio
    async def test_delete_requires_auth(
        self, client: AsyncClient, sample_items: list[InventoryItem]
    ):
        response = await client.post(
            f"/inventory/{sample_items[0].id}/delete", follow_redirects=False
        )
        assert response.status_code == 302
        assert "/login" in response.headers.get("location", "")

    @pytest.mark.asyncio
    async def test_admin_can_delete_any_item(
        self,
        admin_client: AsyncClient,
        sample_items: list[InventoryItem],
        test_session: AsyncSession,
    ):
        item = sample_items[0]
        item_id = item.id
        response = await admin_client.post(
            f"/inventory/{item_id}/delete", follow_redirects=False
        )
        assert response.status_code == 303
        assert "/inventory/" in response.headers.get("location", "")

        result = await test_session.execute(
            select(InventoryItem).where(InventoryItem.id == item_id)
        )
        deleted_item = result.scalar_one_or_none()
        assert deleted_item is None

    @pytest.mark.asyncio
    async def test_staff_cannot_delete_others_item(
        self,
        staff_client: AsyncClient,
        sample_items: list[InventoryItem],
        test_session: AsyncSession,
    ):
        item = sample_items[0]
        item_id = item.id
        response = await staff_client.post(
            f"/inventory/{item_id}/delete", follow_redirects=False
        )
        assert response.status_code == 303
        assert f"/inventory/{item_id}" in response.headers.get("location", "")

        result = await test_session.execute(
            select(InventoryItem).where(InventoryItem.id == item_id)
        )
        still_exists = result.scalar_one_or_none()
        assert still_exists is not None

    @pytest.mark.asyncio
    async def test_staff_can_delete_own_item(
        self,
        staff_client: AsyncClient,
        staff_user: User,
        sample_categories: list[Category],
        test_session: AsyncSession,
    ):
        item = InventoryItem(
            name="Staff Deletable Item",
            description="Owned by staff for deletion",
            quantity=5,
            unit="pcs",
            unit_price=3.00,
            reorder_level=1,
            category_id=sample_categories[0].id,
            owner_id=staff_user.id,
        )
        test_session.add(item)
        await test_session.commit()
        await test_session.refresh(item)
        item_id = item.id

        response = await staff_client.post(
            f"/inventory/{item_id}/delete", follow_redirects=False
        )
        assert response.status_code == 303
        assert "/inventory/" in response.headers.get("location", "")

        result = await test_session.execute(
            select(InventoryItem).where(InventoryItem.id == item_id)
        )
        deleted_item = result.scalar_one_or_none()
        assert deleted_item is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_item(self, admin_client: AsyncClient):
        response = await admin_client.post(
            "/inventory/99999/delete", follow_redirects=False
        )
        assert response.status_code == 303
        assert "/inventory/" in response.headers.get("location", "")

    @pytest.mark.asyncio
    async def test_delete_creates_activity_log(
        self,
        admin_client: AsyncClient,
        sample_items: list[InventoryItem],
        test_session: AsyncSession,
    ):
        item = sample_items[0]
        item_name = item.name
        await admin_client.post(
            f"/inventory/{item.id}/delete", follow_redirects=False
        )

        from models.activity_log import ActivityLog

        result = await test_session.execute(
            select(ActivityLog).where(
                ActivityLog.item_name == item_name, ActivityLog.action == "deleted"
            )
        )
        log = result.scalar_one_or_none()
        assert log is not None
        assert log.item_id is None


class TestInventoryLowStockDisplay:
    """Tests for low-stock and out-of-stock visual indicators."""

    @pytest.mark.asyncio
    async def test_out_of_stock_item_shows_indicator(
        self, staff_client: AsyncClient, sample_items: list[InventoryItem]
    ):
        response = await staff_client.get("/inventory/")
        assert response.status_code == 200
        assert "Out of Stock" in response.text

    @pytest.mark.asyncio
    async def test_low_stock_item_shows_indicator(
        self, staff_client: AsyncClient, sample_items: list[InventoryItem]
    ):
        response = await staff_client.get("/inventory/")
        assert response.status_code == 200
        assert "Low Stock" in response.text

    @pytest.mark.asyncio
    async def test_well_stocked_item_no_warning(
        self, staff_client: AsyncClient, sample_items: list[InventoryItem]
    ):
        well_stocked_item = sample_items[0]
        response = await staff_client.get(f"/inventory/{well_stocked_item.id}")
        assert response.status_code == 200
        assert "Low Stock Warning" not in response.text

    @pytest.mark.asyncio
    async def test_detail_page_low_stock_warning_message(
        self, staff_client: AsyncClient, sample_items: list[InventoryItem]
    ):
        low_stock_item = sample_items[1]
        response = await staff_client.get(f"/inventory/{low_stock_item.id}")
        assert response.status_code == 200
        assert "Low Stock Warning" in response.text
        assert "Consider restocking" in response.text


class TestInventoryOwnershipDisplay:
    """Tests for ownership-based UI elements (edit/delete buttons)."""

    @pytest.mark.asyncio
    async def test_admin_sees_edit_delete_on_any_item(
        self, admin_client: AsyncClient, sample_items: list[InventoryItem]
    ):
        response = await admin_client.get(f"/inventory/{sample_items[0].id}")
        assert response.status_code == 200
        assert "Edit" in response.text
        assert "Delete" in response.text

    @pytest.mark.asyncio
    async def test_staff_sees_edit_delete_on_own_item(
        self,
        staff_client: AsyncClient,
        staff_user: User,
        sample_categories: list[Category],
        test_session: AsyncSession,
    ):
        item = InventoryItem(
            name="Staff Owned Item",
            description="For ownership test",
            quantity=10,
            unit="pcs",
            unit_price=5.00,
            reorder_level=2,
            category_id=sample_categories[0].id,
            owner_id=staff_user.id,
        )
        test_session.add(item)
        await test_session.commit()
        await test_session.refresh(item)

        response = await staff_client.get(f"/inventory/{item.id}")
        assert response.status_code == 200
        assert "Edit" in response.text
        assert "Delete" in response.text

    @pytest.mark.asyncio
    async def test_staff_no_edit_delete_on_others_item(
        self, staff_client: AsyncClient, sample_items: list[InventoryItem]
    ):
        response = await staff_client.get(f"/inventory/{sample_items[0].id}")
        assert response.status_code == 200
        text = response.text
        edit_link = f"/inventory/{sample_items[0].id}/edit"
        assert edit_link not in text
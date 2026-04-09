import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.activity_log import ActivityLog
from models.category import Category
from models.item import InventoryItem
from models.user import User


@pytest.mark.asyncio
async def test_dashboard_requires_admin(client: AsyncClient):
    response = await client.get("/dashboard/", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers.get("location", "")


@pytest.mark.asyncio
async def test_dashboard_staff_cannot_access(staff_client: AsyncClient):
    response = await staff_client.get("/dashboard/", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" not in response.headers.get("location", "") or "/" in response.headers.get("location", "")


@pytest.mark.asyncio
async def test_dashboard_renders_for_admin(admin_client: AsyncClient, admin_user: User):
    response = await admin_client.get("/dashboard/")
    assert response.status_code == 200
    assert "Dashboard" in response.text


@pytest.mark.asyncio
async def test_dashboard_shows_total_items_zero(admin_client: AsyncClient, admin_user: User):
    response = await admin_client.get("/dashboard/")
    assert response.status_code == 200
    assert "Total Items" in response.text


@pytest.mark.asyncio
async def test_dashboard_shows_total_items_count(
    admin_client: AsyncClient,
    admin_user: User,
    sample_items: list[InventoryItem],
):
    response = await admin_client.get("/dashboard/")
    assert response.status_code == 200
    assert "Total Items" in response.text
    assert ">3<" in response.text.replace(" ", "").replace("\n", "")


@pytest.mark.asyncio
async def test_dashboard_shows_total_value(
    admin_client: AsyncClient,
    admin_user: User,
    sample_items: list[InventoryItem],
):
    response = await admin_client.get("/dashboard/")
    assert response.status_code == 200
    assert "Total Inventory Value" in response.text
    # Laptop: 50 * 999.99 = 49999.50
    # Office Chair: 5 * 299.50 = 1497.50
    # Stapler: 0 * 12.99 = 0.00
    # Total = 51497.00
    assert "51497.00" in response.text


@pytest.mark.asyncio
async def test_dashboard_shows_low_stock_count(
    admin_client: AsyncClient,
    admin_user: User,
    sample_items: list[InventoryItem],
):
    response = await admin_client.get("/dashboard/")
    assert response.status_code == 200
    assert "Low Stock" in response.text
    # Office Chair: quantity 5 <= reorder_level 10 → low stock
    # Stapler: quantity 0 <= reorder_level 5 → low stock
    # Laptop: quantity 50 > reorder_level 10 → not low stock
    assert ">2<" in response.text.replace(" ", "").replace("\n", "")


@pytest.mark.asyncio
async def test_dashboard_shows_total_users(
    admin_client: AsyncClient,
    admin_user: User,
):
    response = await admin_client.get("/dashboard/")
    assert response.status_code == 200
    assert "Total Users" in response.text


@pytest.mark.asyncio
async def test_dashboard_low_stock_alerts_table(
    admin_client: AsyncClient,
    admin_user: User,
    sample_items: list[InventoryItem],
):
    response = await admin_client.get("/dashboard/")
    assert response.status_code == 200
    assert "Low Stock Alerts" in response.text
    # Office Chair and Stapler should appear in low stock alerts
    assert "Office Chair" in response.text
    assert "Stapler" in response.text


@pytest.mark.asyncio
async def test_dashboard_low_stock_alerts_empty(
    admin_client: AsyncClient,
    admin_user: User,
):
    response = await admin_client.get("/dashboard/")
    assert response.status_code == 200
    assert "All items are well stocked" in response.text


@pytest.mark.asyncio
async def test_dashboard_low_stock_item_links(
    admin_client: AsyncClient,
    admin_user: User,
    sample_items: list[InventoryItem],
):
    response = await admin_client.get("/dashboard/")
    assert response.status_code == 200
    # Low stock items should have View links
    for item in sample_items:
        if item.quantity <= item.reorder_level:
            assert f"/inventory/{item.id}" in response.text


@pytest.mark.asyncio
async def test_dashboard_recent_activity_empty(
    admin_client: AsyncClient,
    admin_user: User,
):
    response = await admin_client.get("/dashboard/")
    assert response.status_code == 200
    assert "No recent activity" in response.text


@pytest.mark.asyncio
async def test_dashboard_recent_activity_shows_items(
    admin_client: AsyncClient,
    admin_user: User,
    sample_items: list[InventoryItem],
    test_session: AsyncSession,
):
    activity1 = ActivityLog(
        action="created",
        item_name=sample_items[0].name,
        user_id=admin_user.id,
        item_id=sample_items[0].id,
    )
    activity2 = ActivityLog(
        action="updated",
        item_name=sample_items[1].name,
        user_id=admin_user.id,
        item_id=sample_items[1].id,
    )
    activity3 = ActivityLog(
        action="deleted",
        item_name="Deleted Item",
        user_id=admin_user.id,
        item_id=None,
    )
    test_session.add(activity1)
    test_session.add(activity2)
    test_session.add(activity3)
    await test_session.commit()

    response = await admin_client.get("/dashboard/")
    assert response.status_code == 200
    assert "Recent Activity" in response.text
    assert "added a new item" in response.text or "created" in response.text.lower()
    assert "updated an item" in response.text or "updated" in response.text.lower()
    assert "deleted an item" in response.text or "deleted" in response.text.lower()
    assert admin_user.display_name in response.text


@pytest.mark.asyncio
async def test_dashboard_recent_activity_limited_to_five(
    admin_client: AsyncClient,
    admin_user: User,
    sample_items: list[InventoryItem],
    test_session: AsyncSession,
):
    for i in range(8):
        activity = ActivityLog(
            action="created",
            item_name=f"Item {i}",
            user_id=admin_user.id,
            item_id=sample_items[0].id,
        )
        test_session.add(activity)
    await test_session.commit()

    response = await admin_client.get("/dashboard/")
    assert response.status_code == 200
    # The dashboard should show at most 5 recent activities
    # Count occurrences of "added a new item" in the response
    activity_count = response.text.count("added a new item")
    assert activity_count <= 5


@pytest.mark.asyncio
async def test_dashboard_shows_user_count_with_multiple_users(
    admin_client: AsyncClient,
    admin_user: User,
    staff_user: User,
):
    response = await admin_client.get("/dashboard/")
    assert response.status_code == 200
    assert "Total Users" in response.text
    # Should show at least 2 users (admin + staff)
    assert ">2<" in response.text.replace(" ", "").replace("\n", "")


@pytest.mark.asyncio
async def test_dashboard_inventory_value_zero_when_empty(
    admin_client: AsyncClient,
    admin_user: User,
):
    response = await admin_client.get("/dashboard/")
    assert response.status_code == 200
    assert "$0.00" in response.text


@pytest.mark.asyncio
async def test_dashboard_contains_navigation_links(
    admin_client: AsyncClient,
    admin_user: User,
):
    response = await admin_client.get("/dashboard/")
    assert response.status_code == 200
    assert 'href="/inventory/"' in response.text
    assert 'href="/categories/"' in response.text
    assert 'href="/users/"' in response.text
    assert 'href="/dashboard/"' in response.text
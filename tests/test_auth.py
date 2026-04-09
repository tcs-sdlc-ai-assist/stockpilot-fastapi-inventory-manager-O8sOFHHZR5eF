import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User


@pytest.mark.asyncio
async def test_login_page_renders(client: AsyncClient):
    response = await client.get("/login")
    assert response.status_code == 200
    assert "Sign in to StockPilot" in response.text
    assert 'name="username"' in response.text
    assert 'name="password"' in response.text


@pytest.mark.asyncio
async def test_login_page_has_register_link(client: AsyncClient):
    response = await client.get("/login")
    assert response.status_code == 200
    assert 'href="/register"' in response.text


@pytest.mark.asyncio
async def test_login_success_admin_redirects_to_dashboard(
    client: AsyncClient, admin_user: User
):
    response = await client.post(
        "/login",
        data={"username": "testadmin", "password": "adminpass123"},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers["location"] == "/dashboard/"
    assert "stockpilot_session" in response.cookies


@pytest.mark.asyncio
async def test_login_success_staff_redirects_to_inventory(
    client: AsyncClient, staff_user: User
):
    response = await client.post(
        "/login",
        data={"username": "teststaff", "password": "staffpass123"},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers["location"] == "/inventory/"
    assert "stockpilot_session" in response.cookies


@pytest.mark.asyncio
async def test_login_failure_wrong_password(client: AsyncClient, admin_user: User):
    response = await client.post(
        "/login",
        data={"username": "testadmin", "password": "wrongpassword"},
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert "Invalid username or password" in response.text


@pytest.mark.asyncio
async def test_login_failure_nonexistent_user(client: AsyncClient):
    response = await client.post(
        "/login",
        data={"username": "nonexistent", "password": "somepassword"},
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert "Invalid username or password" in response.text


@pytest.mark.asyncio
async def test_login_failure_preserves_username(client: AsyncClient, admin_user: User):
    response = await client.post(
        "/login",
        data={"username": "testadmin", "password": "wrongpassword"},
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert 'value="testadmin"' in response.text


@pytest.mark.asyncio
async def test_register_page_renders(client: AsyncClient):
    response = await client.get("/register")
    assert response.status_code == 200
    assert "Create your account" in response.text
    assert 'name="display_name"' in response.text
    assert 'name="username"' in response.text
    assert 'name="password"' in response.text
    assert 'name="confirm_password"' in response.text


@pytest.mark.asyncio
async def test_register_page_has_login_link(client: AsyncClient):
    response = await client.get("/register")
    assert response.status_code == 200
    assert 'href="/login"' in response.text


@pytest.mark.asyncio
async def test_register_success_creates_staff_user(
    client: AsyncClient, test_session: AsyncSession
):
    response = await client.post(
        "/register",
        data={
            "display_name": "New User",
            "username": "newuser",
            "password": "password123",
            "confirm_password": "password123",
        },
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers["location"] == "/inventory/"
    assert "stockpilot_session" in response.cookies

    result = await test_session.execute(select(User).where(User.username == "newuser"))
    user = result.scalar_one_or_none()
    assert user is not None
    assert user.display_name == "New User"
    assert user.role == "staff"
    assert user.is_default_admin is False
    assert user.verify_password("password123")


@pytest.mark.asyncio
async def test_register_duplicate_username(
    client: AsyncClient, admin_user: User
):
    response = await client.post(
        "/register",
        data={
            "display_name": "Another Admin",
            "username": "testadmin",
            "password": "password123",
            "confirm_password": "password123",
        },
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert "Username is already taken" in response.text


@pytest.mark.asyncio
async def test_register_password_mismatch(client: AsyncClient):
    response = await client.post(
        "/register",
        data={
            "display_name": "Test User",
            "username": "mismatchuser",
            "password": "password123",
            "confirm_password": "differentpassword",
        },
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert "Passwords do not match" in response.text


@pytest.mark.asyncio
async def test_register_password_too_short(client: AsyncClient):
    response = await client.post(
        "/register",
        data={
            "display_name": "Test User",
            "username": "shortpwuser",
            "password": "short",
            "confirm_password": "short",
        },
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert "Password must be at least 8 characters" in response.text


@pytest.mark.asyncio
async def test_register_username_too_short(client: AsyncClient):
    response = await client.post(
        "/register",
        data={
            "display_name": "Test User",
            "username": "ab",
            "password": "password123",
            "confirm_password": "password123",
        },
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert "Username must be between 3 and 32 characters" in response.text


@pytest.mark.asyncio
async def test_register_username_invalid_characters(client: AsyncClient):
    response = await client.post(
        "/register",
        data={
            "display_name": "Test User",
            "username": "bad user!",
            "password": "password123",
            "confirm_password": "password123",
        },
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert "Username can only contain letters, numbers, and underscores" in response.text


@pytest.mark.asyncio
async def test_register_display_name_too_long(client: AsyncClient):
    response = await client.post(
        "/register",
        data={
            "display_name": "A" * 65,
            "username": "longdisplay",
            "password": "password123",
            "confirm_password": "password123",
        },
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert "Display name is required and must be at most 64 characters" in response.text


@pytest.mark.asyncio
async def test_register_preserves_form_values_on_error(client: AsyncClient):
    response = await client.post(
        "/register",
        data={
            "display_name": "My Display Name",
            "username": "myusername",
            "password": "short",
            "confirm_password": "short",
        },
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert 'value="My Display Name"' in response.text
    assert 'value="myusername"' in response.text


@pytest.mark.asyncio
async def test_logout_clears_session(admin_client: AsyncClient):
    response = await admin_client.get("/logout", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "/"
    cookie_header = response.headers.get("set-cookie", "")
    assert "stockpilot_session" in cookie_header


@pytest.mark.asyncio
async def test_logout_post_clears_session(admin_client: AsyncClient):
    response = await admin_client.post("/logout", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "/"


@pytest.mark.asyncio
async def test_authenticated_admin_redirected_from_login(admin_client: AsyncClient):
    response = await admin_client.get("/login", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "/dashboard/"


@pytest.mark.asyncio
async def test_authenticated_staff_redirected_from_login(staff_client: AsyncClient):
    response = await staff_client.get("/login", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "/inventory/"


@pytest.mark.asyncio
async def test_authenticated_admin_redirected_from_register(admin_client: AsyncClient):
    response = await admin_client.get("/register", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "/dashboard/"


@pytest.mark.asyncio
async def test_authenticated_staff_redirected_from_register(staff_client: AsyncClient):
    response = await staff_client.get("/register", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "/inventory/"
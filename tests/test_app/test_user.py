import pytest

from app.dto import UserDTO, UserPwdDTO
from app.models.models import User


@pytest.mark.asyncio
async def test_login_success(client, auth_headers, test_user, db_engine):
    user_data = UserPwdDTO(username="testuser", email="test@example.com", password="test123")
    response = client.post("/login/", json=user_data.dict())
    assert response.status_code == 200
    data = response.json()
    assert data["role"] == test_user.role
    assert data["user_id"] == str(test_user.id)


@pytest.mark.asyncio
async def test_login_invalid(client, db_engine):
    user_data = UserPwdDTO(username="invalid", email="invalid@example.com", password="dd")
    response = client.post("/login/", json=user_data.dict())
    assert response.status_code == 401  # Предполагаем, что AuthService возвращает 401


@pytest.mark.asyncio
async def test_logout(client, auth_headers):
    response = client.delete("/logout/", headers=auth_headers)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_users(client, auth_headers, test_user, test_user2):
    response = client.get("/users/", headers=auth_headers)
    assert response.status_code == 200
    users = response.json()
    assert len(users) >= 2
    assert any(u["username"] == "testuser" for u in users)
    assert any(u["username"] == "testuser2" for u in users)


@pytest.mark.asyncio
async def test_get_user(client, auth_headers, test_user):
    response = client.get(f"/user/{test_user.id}/", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser"


@pytest.mark.asyncio
async def test_create_user(client, auth_headers):
    user_data = UserPwdDTO(username="newuser", email="new@example.com", password="test123")
    response = client.post("/user/", json=user_data.dict(), headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "newuser"


@pytest.mark.asyncio
async def test_update_user(client, auth_headers, test_user):
    user_data = UserDTO(username="updateduser", email="test@example.com")
    response = client.patch(f"/user/{test_user.id}/", json=user_data.dict(), headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "updateduser"


@pytest.mark.asyncio
async def test_delete_user(client, auth_headers, test_user, db_session):
    response = client.delete(f"/user/{test_user.id}/", headers=auth_headers)
    assert response.status_code == 200
    user = await User.first(id=test_user.id, session=db_session)
    assert user is None

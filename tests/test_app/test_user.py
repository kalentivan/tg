import pytest
from httpx import ASGITransport, AsyncClient

from app.dto import RTokenDTO, UserDTO, UserPwdDTO
from app.models.models import User
from main import app


@pytest.mark.asyncio
async def test_login_success(client, auth_headers, test_user, db_engine):
    user_data = UserPwdDTO(username="testuser", email="test@example.com", password="test123")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post("/login/", json=user_data.model_dump())
    assert response.status_code == 200
    data = response.json()
    assert data["role"] == test_user.role
    assert data["user_id"] == str(test_user.id)


@pytest.mark.asyncio
async def test_login_invalid(client, db_engine):
    user_data = UserPwdDTO(username="invalid", email="invalid@example.com", password="dd")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post("/login/", json=user_data.model_dump())
    assert response.status_code == 401  # Предполагаем, что AuthService возвращает 401


@pytest.mark.asyncio
async def test_logout(client, auth_headers):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.delete("/logout/", headers=auth_headers)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_refresh_tokens_success(test_user, valid_refresh_token, db_session, auth_service):
    """Проверяет успешное обновление токенов."""
    refresh_token, device_id = valid_refresh_token
    data = RTokenDTO(refresh_token=refresh_token)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/token/refresh/",
            json=data.model_dump(),
            headers={
                "Authorization": f"Bearer {auth_service._jwt_auth.generate_access_token(subject=str(test_user.id),
                                                                                        payload={"device_id": device_id})}"})

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_users(client, auth_headers, test_user, test_user2):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/users/", headers=auth_headers)
    assert response.status_code == 200
    users = response.json()
    assert len(users) >= 2
    assert any(u["username"] == "testuser" for u in users)
    assert any(u["username"] == "testuser2" for u in users)


@pytest.mark.asyncio
async def test_get_user(client, auth_headers, test_user):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(f"/user/{test_user.id}/", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser"


@pytest.mark.asyncio
async def test_create_user(client, auth_headers):
    user_data = UserPwdDTO(username="newuser", email="new@example.com", password="test123")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post("/user/", json=user_data.model_dump(), headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "newuser"


@pytest.mark.asyncio
async def test_update_user(client, auth_headers, test_user):
    user_data = UserDTO(username="updateduser", email="test@example.com")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.patch(f"/user/{test_user.id}/", json=user_data.model_dump(), headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "updateduser"


@pytest.mark.asyncio
async def test_delete_user(client, auth_headers, test_user, db_session):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.delete(f"/user/{test_user.id}/", headers=auth_headers)
    assert response.status_code == 200
    user = await User.first(id=test_user.id, session=db_session)
    assert user is None

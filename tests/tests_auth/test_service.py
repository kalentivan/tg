# import datetime as dt
# import uuid
#
# import pytest
# from sqlalchemy import select, update
# from sqlalchemy.ext.asyncio import AsyncSession
# from starlette import status
# from starlette.exceptions import HTTPException
#
# from app.auth.service import AuthService
# from app.dto import UserPwdDTO
# from app.models.models import IssuedJWTToken
#
#
# @pytest.fixture
# def auth_service():
#     """Фикстура для создания экземпляра AuthService."""
#     return AuthService()
#
#
# @pytest.mark.asyncio
# async def test_register_success(auth_service, db_session: AsyncSession):
#     """Проверяет успешную регистрацию пользователя."""
#     user_data = UserPwdDTO(username="newuser", email="new@example.com", password="test123")
#     user, tokens = await auth_service.register(data=user_data, session=db_session)
#     assert user is not None
#     assert user.email == "new@example.com"
#     assert user.username == "newuser"
#     assert tokens is not None
#     assert tokens.access_token
#     assert tokens.refresh_token
#     tokens_db = await db_session.execute(
#         select(IssuedJWTToken).where(IssuedJWTToken.user_id == user.id)
#     )
#     tokens_db = tokens_db.scalars().all()
#     assert len(tokens_db) == 2  # Access и refresh токены
#
#
# @pytest.mark.asyncio
# async def test_register_conflict(auth_service, db_session: AsyncSession, test_user):
#     """Проверяет конфликт при регистрации с существующим email."""
#     user_data = UserPwdDTO(username="conflictuser", email="test@example.com", password="test123")
#     with pytest.raises(HTTPException) as exc:
#         await auth_service.register(data=user_data, session=db_session)
#     assert exc.value.status_code == status.HTTP_409_CONFLICT
#     assert exc.value.detail == "CONFLICT"
#
#
# @pytest.mark.asyncio
# async def test_login_success(auth_service, db_session: AsyncSession, test_user):
#     """Проверяет успешный вход пользователя."""
#     user_data = UserPwdDTO(username="testuser", email="test@example.com", password="test123")
#     tokens = await auth_service.login(data=user_data, session=db_session)
#     assert tokens is not None
#     assert tokens.access_token
#     assert tokens.refresh_token
#     assert tokens.user_id == str(test_user.id)
#     tokens_db = await db_session.execute(
#         select(IssuedJWTToken).where(IssuedJWTToken.user_id == test_user.id)
#     )
#     tokens_db = tokens_db.scalars().all()
#     assert len(tokens_db) == 2 + 2  # Новые токены
#
#
# @pytest.mark.asyncio
# async def test_login_invalid_password(auth_service, db_session: AsyncSession, test_user):
#     """Проверяет вход с неверным паролем."""
#     user_data = UserPwdDTO(username="testuser", email="test@example.com", password="wrongpassword")
#     with pytest.raises(HTTPException) as exc:
#         await auth_service.login(data=user_data, session=db_session)
#     assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED
#     assert exc.value.detail == "HTTP_401_UNAUTHORIZED"
#
#
# @pytest.mark.asyncio
# async def test_login_invalid_email(auth_service, db_session: AsyncSession):
#     """Проверяет вход с несуществующим email."""
#     user_data = UserPwdDTO(username="nonuser", email="nonexistent@example.com", password="test123")
#     with pytest.raises(HTTPException) as exc:
#         await auth_service.login(data=user_data, session=db_session)
#     assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED
#
#
# @pytest.mark.asyncio
# async def test_logout_success(auth_service, db_session: AsyncSession, test_user):
#     """Проверяет успешный выход пользователя."""
#     device_id = "test-device-id"
#     jti = uuid.uuid4()
#     token = IssuedJWTToken(
#         user_id=test_user.id,
#         jti=jti,
#         device_id=device_id,
#         revoked=False,
#         expired_time=dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=1)
#     )
#     db_session.add(token)
#     await db_session.commit()
#
#     await auth_service.logout(user=test_user, device_id=device_id, session=db_session)
#     updated_token = await db_session.get(IssuedJWTToken, (jti,))
#     assert updated_token.revoked is True
#
#
# @pytest.mark.asyncio
# async def test_logout_no_token(auth_service, db_session: AsyncSession, test_user):
#     """Проверяет выход без существующих токенов."""
#     device_id = "non-existent-device-id"
#     await auth_service.logout(user=test_user, device_id=device_id, session=db_session)
#     tokens = await db_session.execute(
#         select(IssuedJWTToken).where(IssuedJWTToken.user_id == test_user.id,
#                                      IssuedJWTToken.device_id == device_id)
#     )
#     tokens = tokens.scalars().all()
#     # Проверяем, что ничего не изменилось, если токенов нет
#     assert len(tokens) == 0  # Предполагаем, что токенов изначально нет
#
#
# @pytest.mark.asyncio
# async def test_update_tokens_success(auth_service, db_session: AsyncSession, test_user):
#     """Проверяет успешное обновление токенов."""
#     device_id = "test-device-id"
#     _, refresh_token, notes = auth_service._issue_tokens_for_user(test_user, device_id)
#     for note in notes:
#         db_session.add(note)
#     await db_session.commit()
#
#     new_tokens = await auth_service.update_tokens(user=test_user, refresh_token=refresh_token, session=db_session)
#     assert new_tokens is not None
#     assert new_tokens.access_token
#     assert new_tokens.refresh_token
#     updated_tokens = await db_session.execute(
#         select(IssuedJWTToken).where(IssuedJWTToken.user_id == test_user.id)
#     )
#     updated_tokens = updated_tokens.scalars().all()
#     assert any(token.revoked for token in updated_tokens if token.jti == notes[1].jti)  # Старый refresh токен отозван
#
#
# @pytest.mark.asyncio
# async def test_update_tokens_invalid_token(auth_service, db_session: AsyncSession, test_user):
#     """Проверяет обновление с невалидным токеном."""
#     with pytest.raises(HTTPException) as exc:
#         await auth_service.update_tokens(user=test_user, refresh_token="invalid_token", session=db_session)
#     assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED
#     assert exc.value.detail == "Некорректный токен"
#
#
# @pytest.mark.asyncio
# async def test_update_tokens_not_refresh(auth_service, db_session: AsyncSession, test_user):
#     """Проверяет обновление с access токеном вместо refresh."""
#     access_token, _, notes = auth_service._issue_tokens_for_user(test_user)
#     for note in notes:
#         db_session.add(note)
#     await db_session.commit()
#
#     result = await auth_service.update_tokens(user=test_user, refresh_token=access_token, session=db_session)
#     assert result is None  # Возвращает None, если токен не refresh
#
#
# @pytest.mark.asyncio
# async def test_update_tokens_revoked(auth_service, db_session: AsyncSession, test_user):
#     """Проверяет обновление с отозванным токеном."""
#     device_id = "test-device-id"
#     _, refresh_token, notes = auth_service._issue_tokens_for_user(test_user, device_id)
#     for note in notes:
#         db_session.add(note)
#     await db_session.commit()
#     await db_session.execute(
#         update(IssuedJWTToken)
#         .where(IssuedJWTToken.jti == notes[1].jti)  # Предполагаем, что второй токен - refresh
#         .values(revoked=True)
#     )
#     await db_session.commit()
#     result = await auth_service.update_tokens(user=test_user, refresh_token=refresh_token, session=db_session)
#     assert result is None
#     all_tokens = await db_session.execute(select(IssuedJWTToken).where(IssuedJWTToken.user_id == test_user.id))
#     all_tokens = all_tokens.scalars().all()
#     assert any(token.revoked for token in all_tokens if token.jti == notes[1].jti)  # Все токены отозваны
#

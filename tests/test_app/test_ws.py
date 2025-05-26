# import asyncio
# import uuid
#
# import pytest
# from asgiref.sync import async_to_sync
# from sqlalchemy import select
# from starlette.testclient import TestClient
# from starlette.websockets import WebSocketDisconnect
#
# from app.auth.service import AuthService
# from app.dto import UserPwdDTO
# from app.models.models import Chat, GroupMember, Message, MessageRead, User
# from main import app
#
#
# # @pytest.fixture(scope="session")
# # def event_loop():
# #     loop = asyncio.get_event_loop_policy().new_event_loop()
# #     yield loop
# #     loop.close()
#
#
# @pytest.fixture
# def client(db_engine):
#     return TestClient(app)
#
#
# @pytest.fixture
# def db_session_sync(db_engine):
#     # Создаём синхронную сессию
#     from sqlalchemy.orm import sessionmaker
#     SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()
#
#
# @pytest.mark.asyncio
# async def test_websocket_connect_disconnect(client, db_session):
#     # Создаём тестового пользователя
#     user = await User.first(email="test@example.com", session=db_session)
#     auth_service = AuthService()
#     if not user:
#         user_data = UserPwdDTO(
#             username="testuser",
#             email="test@example.com",
#             password="test123"
#         )
#         user, _ = await auth_service.register(user_data, session=db_session)
#         await db_session.commit()
#
#     # Создаём второй тестовый пользователь
#     user2 = await User.first(email="test2@example.com", session=db_session)
#     if not user2:
#         user2_data = UserPwdDTO(
#             username="testuser2",
#             email="test2@example.com",
#             password="test123"
#         )
#         user2, _ = await auth_service.register(user2_data, session=db_session)
#         await db_session.commit()
#
#     # Создаём чат
#     chat = await Chat.create(name=None, is_group=False, session=db_session)
#     db_session.add(GroupMember(user_id=user.id, chat_id=chat.id, is_admin=True))
#     db_session.add(GroupMember(user_id=user2.id, chat_id=chat.id))
#     await db_session.commit()
#
#     # Генерируем токен
#     payload = {"device_id": str(uuid.uuid4())}
#     token = auth_service._jwt_auth.generate_access_token(subject=str(user.id), payload=payload)
#     auth_headers = {"Authorization": f"Bearer {token}"}
#
#     # Тестируем WebSocket
#     try:
#         # Используем run_in_executor для синхронного TestClient в асинхронном тесте
#         loop = asyncio.get_event_loop()
#         task = loop.run_in_executor(
#             None,
#             lambda: client.websocket_connect(f"/ws/{chat.id}", headers=auth_headers).__enter__()
#         )
#         websocket = await asyncio.wait_for(task, timeout=5.0)
#
#         assert websocket is not None
#         websocket.close()
#     except WebSocketDisconnect as e:
#         assert e.code == 1008  # Ожидаемое закрытие, если пользователь не в чате
#     except Exception as e:
#         pytest.fail(f"Неожиданная ошибка: {e}")
#
#
# # def test_websocket_connect_disconnect(client, db_session_sync):
# #     # Создаём тестового пользователя (синхронно)
# #     db_session = db_session_sync
# #     user = db_session.execute(
# #         select(User).filter_by(email="test@example.com")
# #     ).scalars().first()
# #     auth_service = AuthService()
# #     if not user:
# #         user_data = UserPwdDTO(
# #             username="testuser",
# #             email="test@example.com",
# #             password="test123"
# #         )
# #
# #         # Вызываем асинхронный register в изолированном цикле
# #         async def register_user():
# #             return await auth_service.register(user_data)  # session=None, так как используется внешняя
# #
# #         user, _ = asyncio.run(register_user())
# #         db_session.add(user)
# #         db_session.commit()
# #
# #     # Создаём второй тестовый пользователь
# #     user2 = db_session.execute(
# #         select(User).filter_by(email="test2@example.com")
# #     ).scalars().first()
# #     if not user2:
# #         user2_data = UserPwdDTO(
# #             username="testuser2",
# #             email="test2@example.com",
# #             password="test123"
# #         )
# #
# #         async def register_user2():
# #             return await auth_service.register(user2_data)
# #
# #         user2, _ = asyncio.run(register_user2())
# #         db_session.add(user2)
# #         db_session.commit()
# #
# #     # Создаём чат (синхронно)
# #     chat = Chat(id=uuid.uuid4(), name=None, is_group=False)
# #     db_session.add(chat)
# #     db_session.flush()
# #     db_session.add(GroupMember(user_id=user.id, chat_id=chat.id, is_admin=True))
# #     db_session.add(GroupMember(user_id=user2.id, chat_id=chat.id))
# #     db_session.commit()
# #
# #     # Генерируем токен
# #     payload = {"device_id": str(uuid.uuid4())}
# #     token = auth_service._jwt_auth.generate_access_token(subject=str(user.id), payload=payload)
# #     auth_headers = {"Authorization": f"Bearer {token}"}
# #
# #     # Тестируем WebSocket
# #     try:
# #         with client.websocket_connect(f"/ws/{chat.id}", headers=auth_headers) as websocket:
# #             assert websocket is not None
# #     except WebSocketDisconnect as e:
# #         assert e.code == 1008  # Ожидаемое закрытие, если пользователь не в чате (но он есть)
# #     except Exception as e:
# #         pytest.fail(f"Неожиданная ошибка: {e}")
#
#
# @pytest.mark.asyncio
# async def test_websocket_send_message(client, auth_headers, personal_chat, test_user, db_session):
#     # ---------------------- #
#     test_user = await test_user
#     auth_service = AuthService()
#     payload = {"device_id": str(uuid.uuid4())}
#     token = auth_service._jwt_auth.generate_access_token(subject=str(test_user.id), payload=payload)
#     auth_headers = {"Authorization": f"Bearer {token}"}
#     # ---------------------- #
#     if not (test_user := await User.first(email="test@example.com", session=db_session)):
#         user_data = UserPwdDTO(
#             username="testuser",
#             email="test@example.com",
#             password="test123"
#         )
#         auth_service = AuthService()
#         test_user, _ = await auth_service.register(user_data, session=db_session)
#     if not (user2 := await User.first(email="test2@example.com", session=db_session)):
#         user_data = UserPwdDTO(
#             username="testuser2",
#             email="test2@example.com",
#             password="test123"
#         )
#         auth_service = AuthService()
#         user2, tokens = await auth_service.register(user_data, session=db_session)
#         await db_session.refresh(user2)
#     # ---------------------- #
#     chat = await Chat.create(
#         name=None,
#         is_group=False,
#         session=db_session
#     )
#     db_session.add(GroupMember(user_id=test_user.id, chat_id=chat.id, is_admin=True))
#     db_session.add(GroupMember(user_id=test_user2.id, chat_id=chat.id))
#     await db_session.commit()
#     # ---------------------- #
#
#     with client.websocket_connect(f"/ws/{personal_chat.id}", headers=auth_headers) as ws:
#         message_uuid = uuid.uuid4()
#         ws.send_json({
#             "action": "send_message",
#             "text": "Test message",
#             "uuid": str(message_uuid)
#         })
#         response = ws.receive_json()
#         assert response["text"] == "Test message"
#         message = await Message.first(id=message_uuid, session=db_session)
#         assert message is not None
#         assert message.text == "Test message"
#
#
# @pytest.mark.asyncio
# async def test_websocket_message_read_personal(client, auth_headers, personal_chat, test_user, test_user2, db_session):
#     # Создаем сообщение
#     message = await Message.create(
#         chat_id=personal_chat.id,
#         sender_id=test_user.id,
#         text="Test message",
#         session=db_session
#     )
#     # Подключаемся от имени второго пользователя
#     auth_service = AuthService()
#     token = auth_service._jwt_auth.generate_access_token({"sub": str(test_user2.id)})
#     headers = {"Authorization": f"Bearer {token}"}
#     with client.websocket_connect(f"/ws/{personal_chat.id}", headers=headers) as ws:
#         ws.send_json({
#             "action": "message_read",
#             "message_id": str(message.id)
#         })
#         # Проверяем, что is_read обновлено
#         updated_message = await Message.get_or_404(id=message.id, session=db_session)
#         assert updated_message.is_read is True
#
#
# @pytest.mark.asyncio
# async def test_websocket_message_read_group(client, auth_headers, group_chat, test_user, test_user2, db_session):
#     # Создаем сообщение
#     message = await Message.create(
#         chat_id=group_chat.id,
#         sender_id=test_user.id,
#         text="Test group message",
#         session=db_session
#     )
#     # Подключаемся от имени второго пользователя
#     auth_service = AuthService()
#     token = auth_service._jwt_auth.generate_access_token({"sub": str(test_user2.id)})
#     headers = {"Authorization": f"Bearer {token}"}
#     with client.websocket_connect(f"/ws/{group_chat.id}", headers=headers) as ws:
#         ws.send_json({
#             "action": "message_read",
#             "message_id": str(message.id)
#         })
#         # Проверяем, что создана запись в MessageRead
#         message_read = await MessageRead.first(message_id=message.id, user_id=test_user2.id, session=db_session)
#         assert message_read is not None

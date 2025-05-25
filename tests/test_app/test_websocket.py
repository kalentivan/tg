# import asyncio
# import uuid
#
# import pytest
# from sqlalchemy.ext.asyncio import AsyncSession
# from starlette.websockets import WebSocketDisconnect
#
# from app.auth.service import AuthService
# from app.models.models import Message, MessageRead
#
#
# @pytest.mark.asyncio
# async def test_websocket_connect_disconnect(client, auth_headers, personal_chat, test_user):
#     try:
#         with client.websocket_connect(f"/ws/{personal_chat.id}", headers=auth_headers) as ws:
#             pass
#     except WebSocketDisconnect as e:
#         assert e.code == 1008  # Ожидаемое закрытие из-за политики
#         assert e.reason == ""
#
#
# @pytest.mark.asyncio
# async def test_websocket_send_message(client, auth_headers, personal_chat, test_user, db_session):
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
# async def test_websocket_message_read_personal(client, auth_headers, personal_chat, test_user, test_user2,
#                                                db_session, db_engine):
#     # Создаем сообщение
#     message = await Message.create(
#         chat_id=personal_chat.id,
#         sender_id=test_user.id,
#         text="Test message",
#         session=db_session
#     )
#     # Подключаемся от имени второго пользователя
#     auth_service = AuthService()
#     token = auth_service._jwt_auth.generate_access_token(subject=str(test_user2.id))
#     headers = {"Authorization": f"Bearer {token}"}
#     with client.websocket_connect(f"/ws/{personal_chat.id}", headers=headers) as ws:
#         ws.send_json({
#             "action": "message_read",
#             "message_id": str(message.id)
#         })
#         # Проверяем, что is_read обновлено
#         await asyncio.sleep(0.1)  # Даём время на обработку
#         # Создаём новую сессию для проверки, чтобы избежать кэширования
#         async with AsyncSession(db_engine) as check_session:
#             updated_message = await Message.get_or_404(id=message.id, session=check_session)
#             assert updated_message.is_read is True
#
#
# @pytest.mark.asyncio
# async def test_websocket_message_read_group(client, auth_headers, group_chat, test_user, test_user2, db_session, db_engine):
#     # Создаем сообщение
#     message = await Message.create(
#         chat_id=group_chat.id,
#         sender_id=test_user.id,
#         text="Test group message",
#         session=db_session
#     )
#     # Подключаемся от имени второго пользователя
#     auth_service = AuthService()
#     token = auth_service._jwt_auth.generate_access_token(subject=str(test_user2.id))
#     headers = {"Authorization": f"Bearer {token}"}
#     with client.websocket_connect(f"/ws/{group_chat.id}", headers=headers) as ws:
#         ws.send_json({
#             "action": "message_read",
#             "message_id": str(message.id)
#         })
#         # Проверяем, что создана запись в MessageRead
#         # Проверяем, что is_read обновлено
#         await asyncio.sleep(0.1)  # Даём время на обработку
#         # Создаём новую сессию для проверки, чтобы избежать кэширования
#         async with AsyncSession(db_engine) as check_session:
#             message_read = await MessageRead.first(message_id=message.id, user_id=test_user2.id, session=check_session)
#             assert message_read is not None

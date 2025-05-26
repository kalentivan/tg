# import pytest
# from httpx import ASGITransport, AsyncClient
#
# from app.models.models import GroupMember, Message, MessageRead
# from main import app
#
#
# @pytest.mark.asyncio
# async def test_chat_history_with_data(client, auth_headers, test_data, db_session):
#     # Берем случайный чат из тестовых данных
#     chat = test_data["personal_chats"][0]
#     transport = ASGITransport(app=app)
#     async with AsyncClient(transport=transport, base_url="http://test") as ac:
#         response = await ac.post(f"/chat/{chat.id}/history/", headers=auth_headers)
#     assert response.status_code == 200
#     answer = response.json()
#     messages, total = answer["messages"], answer["total"]
#     # Проверяем, что возвращено правильное количество сообщений
#     db_messages = await Message.list(session=db_session, chat_id=chat.id)
#     assert total == len(db_messages)
#     assert len(messages) <= 10  # По умолчанию limit=10
#
#
# @pytest.mark.asyncio
# async def test_group_chat_members_with_data(client, auth_headers, test_data, db_session):
#     # Берем групповой чат
#     chat = test_data["group_chats"][0]
#     members = await GroupMember.list(session=db_session, chat_id=chat.id)
#     expected_members = test_data["group_chat_members"][chat.id]
#     assert len(members) == expected_members, f"Ожидалось {expected_members} участников, но найдено {len(members)}"
#
#
# @pytest.mark.asyncio
# async def test_message_reads_in_group_chat(client, auth_headers, test_data, db_session):
#     # Берем групповой чат и его сообщения
#     chat = test_data["group_chats"][0]
#     messages = [m for m in test_data["messages"] if m.chat_id == chat.id]
#     expected_message_count = test_data["chat_messages"][chat.id]
#     assert len(messages) == expected_message_count, f"Ожидалось {expected_message_count} сообщений, но найдено {len(messages)}"
#
#     # Проверяем, что есть сообщения с прочтениями
#     message_with_reads = None
#     for message in messages:
#         reads = await MessageRead.list(session=db_session, message_id=message.id)
#         if reads:  # Если есть прочтения
#             message_with_reads = message
#             break
#
#     # Используем данные из test_data для проверки наличия сообщений с прочтениями
#     expected_messages_with_reads = test_data["messages_with_reads"][chat.id]
#     assert expected_messages_with_reads, "В групповом чате должны быть сообщения с прочтениями"
#     assert message_with_reads is not None, "Не найдено сообщение с прочтениями"
#     assert message_with_reads.id in expected_messages_with_reads, "Найденное сообщение с прочтениями не соответствует ожидаемому"
#

"""
Роуты авторизации
"""
from typing import List

from fastapi import APIRouter, Depends
from starlette.responses import Response

from app.auth.auth import get_current_user, get_current_user_and_device
from app.auth.init import get_auth_service
from app.auth.service import AuthService
from app.auth.token import del_tokens, set_tokens
from app.database import AsyncSessionLocal, get_db
from app.dto import TokensDTO, UserDTO, UserPwdDTO
from app.models.models import User
from app.tools import validate_uuid

router = APIRouter()

LOGIN_ROUTES = ["Авторизация"]
USER_ROUTES = ["Пользователь"]


@router.post("/login/",
             response_model=TokensDTO,
             tags=LOGIN_ROUTES)
async def route_login(response: Response,
                      user_data: UserPwdDTO,
                      auth_service: AuthService = Depends(get_auth_service),
                      session=Depends(get_db)) -> TokensDTO:
    """

    :param session:
    :param response:
    :param user_data:
    :param auth_service:
    :return:
    """
    tokens = await auth_service.login(data=user_data, session=session)
    response.status_code = 200
    set_tokens(response, tokens.access_token, tokens.refresh_token)
    return tokens


@router.delete("/logout/",
               tags=LOGIN_ROUTES,
               response_model=None)
async def route_logout(response: Response,
                       session_data: tuple[User, str] = Depends(get_current_user_and_device),
                       auth_service: AuthService = Depends(get_auth_service),
                       session: AsyncSessionLocal = Depends(get_db),
                       ) -> Response:
    """
    С токеном авторизации
    :param session:
    :param response:
    :param session_data:
    :param auth_service:
    :return:
    """
    user, device_id = session_data
    await auth_service.logout(user=user, device_id=device_id, session=session)
    del_tokens(response)
    response.status_code = 200
    return response


@router.get("/users/",
            response_model=List[UserDTO],
            tags=USER_ROUTES)
async def route_get_user(response: Response,
                         admin: User = Depends(get_current_user),
                         session=Depends(get_db)) -> list[dict]:
    """Получение данных пользователя. Без токена авторизации."""
    users_data = await User.list_rows(session=session)
    response.status_code = 200
    return users_data


@router.get("/user/{item_id}/",
            response_model=UserDTO,
            tags=USER_ROUTES)
async def route_get_user(response: Response,
                         item_id: str,
                         user: User = Depends(get_current_user),
                         session=Depends(get_db)) -> dict:
    """Получение данных пользователя. С токеном авторизации."""
    item_id = validate_uuid(item_id)
    response.status_code = 200
    user = await User.get_or_404(id=item_id, session=session)
    return user.to_dict()


@router.post("/user/",
             response_model=UserDTO,
             tags=USER_ROUTES)
async def route_create_user(response: Response,
                            user_data: UserPwdDTO,
                            auth_service: AuthService = Depends(get_auth_service),
                            session=Depends(get_db)) -> dict[str, str | None]:
    """Создание пользователя. С токеном авторизации"""
    user, tokens = await auth_service.register(user_data, session=session)
    response.status_code = 200
    set_tokens(response, tokens.access_token, tokens.refresh_token)
    return user.to_dict()


@router.patch("/user/{item_id}/",
              response_model=UserDTO,
              tags=USER_ROUTES)
async def route_edit_user(response: Response,
                          user_data: UserDTO,
                          item_id: str,
                          user: User = Depends(get_current_user),
                          session=Depends(get_db)) -> dict:
    """Редактирование данных пользователя. С токеном авторизации."""
    item_id = validate_uuid(item_id)
    user = await User.get_or_404(id=item_id, session=session)
    user.username = user_data.username
    await user.save(update_fields=["username"], session=session)
    response.status_code = 200
    return user.to_dict()


@router.delete("/user/{item_id}/",
               tags=USER_ROUTES)
async def route_delete_user(response: Response,
                            item_id: str,
                            user: User = Depends(get_current_user),
                            session=Depends(get_db)) -> Response:
    """Удаление пользователя из базы данных. С токеном авторизации."""
    item_id = validate_uuid(item_id)
    user = await User.get_or_404(id=item_id, session=session)
    await user.delete(session=session)
    response.status_code = 200
    return response

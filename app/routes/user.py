"""
Роуты авторизации
"""
from typing import List

from fastapi import APIRouter, Depends
from starlette.responses import Response

from app.auth.auth import get_current_user
from app.auth.init import get_auth_service
from app.auth.service import AuthService
from app.database import get_db
from app.dto import UserDTO, UserPwdDTO
from app.models.models import User
from core.types import ID

router = APIRouter()

LOGIN_ROUTES = ["Авторизация"]
USER_ROUTES = ["Пользователь"]


@router.post("/login/",
             response_model=UserDTO,
             tags=LOGIN_ROUTES)
async def route_login(response: Response,
                      user_data: UserDTO,
                      auth_service: AuthService = Depends(get_auth_service),
                      session=Depends(get_db)) -> dict:
    """

    :param session:
    :param response:
    :param user_data:
    :param auth_service:
    :return:
    """
    user = await auth_service.login(data=user_data, session=session)
    response.status_code = 200
    return user.fields


@router.delete("/logout/",
               tags=LOGIN_ROUTES)
async def route_logout(response: Response,
                       user: User = Depends(get_current_user),
                       auth_service: AuthService = Depends(get_auth_service),
                       session=Depends(get_db)) -> Response:
    """
    С токеном авторизации
    :param session:
    :param response:
    :param user:
    :param auth_service:
    :return:
    """
    await auth_service.logout(user=user, session=session)
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
                         item_id: ID,
                         user: User = Depends(get_current_user),
                         session=Depends(get_db)) -> dict:
    """Получение данных пользователя. С токеном авторизации."""
    response.status_code = 200
    user = await User.get_or_404(id=item_id, session=session)
    return user.fields


@router.post("/user/",
             response_model=UserDTO,
             tags=USER_ROUTES)
async def route_create_user(response: Response,
                            user_data: UserPwdDTO,
                            auth_service: AuthService = Depends(get_auth_service),
                            session=Depends(get_db)) -> dict[str, str | None]:
    """Создание пользователя. С токеном авторизации"""
    user = await auth_service.register(user_data, session=session)
    response.status_code = 200
    return user.to_dict()


@router.patch("/user/{item_id}/",
              response_model=UserDTO,
              tags=USER_ROUTES)
async def route_edit_user(response: Response,
                          item_id: ID,
                          user_data: UserDTO,
                          user: User = Depends(get_current_user),
                          session=Depends(get_db)) -> dict:
    """Редактирование данных пользователя. С токеном авторизации."""
    user = await User.get_or_404(id=item_id, session=session)
    user.username = user_data.username
    await user.save(update_fields=["username"], session=session)
    response.status_code = 200
    return user.to_dict()


@router.delete("/user/{item_id}/",
               tags=USER_ROUTES)
async def route_delete_user(response: Response,
                            item_id: ID,
                            user: User = Depends(get_current_user),
                            session=Depends(get_db)) -> Response:
    """Удаление пользователя из базы данных. С токеном авторизации."""
    user = await User.get_or_404(id=item_id, session=session)
    await user.save(session=session)
    response.status_code = 200
    return response

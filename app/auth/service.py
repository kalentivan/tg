from fastapi import HTTPException
from starlette import status

from app.auth.my_jwt import JWTAuth
from app.auth.password import get_password_hash, verify_password
from app.dto import UserDTO
from app.models.models import User


class AuthService:
    """
    Регистрация пользователя, вход, выход пользователя
    """

    def __init__(self) -> None:
        self._jwt_auth = JWTAuth()

    async def register(self,
                       data: UserDTO,
                       session) -> User:
        """
        Регистрация пользователя.
        Создать пользователя, создать токены
        :param session:
        :param data:
        :return:
        """
        if await User.first(email=data.email, session=session):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='CONFLICT')
        return await User.create(email=data.email, password=get_password_hash(password=data.password), session=session)

    async def login(self,
                    data: UserDTO, session) -> User:
        """
        Вход пользователя
        :param session:
        :param data:
        :return:
        """
        user = await User.get_or_404(email=data.email, session=session)
        if not verify_password(data.password, user.password):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='UNAUTHORIZED')
        return user

    @classmethod
    async def logout(cls,
                     user: User, session) -> None:
        """
        Выход пользователя
        :param user:
        :return:
        """
        ...

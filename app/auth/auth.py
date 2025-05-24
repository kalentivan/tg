from fastapi import Depends, HTTPException
from jose import JWTError, jwt
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from app.auth.config import get_auth_data
from app.auth.password import verify_password
from app.auth.token import get_token, get_ws_token
from app.tools import validate_uuid
from app.database import get_db
from app.models.models import User


async def authenticate_user(email: str,
                            password: str,
                            session: AsyncSession) -> User | None:
    """
    Валидация пользователя
    """
    user = await User.get_or_404(email=str(email), session=session,
                                 er_status=status.HTTP_401_UNAUTHORIZED, er_msg='UNAUTHORIZED')
    if not user or verify_password(plain_password=password, hashed_password=user.password) is False:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='UNAUTHORIZED')
    return user


async def get_current_user(token: str = Depends(get_token),
                           session: AsyncSession = Depends(get_db)) -> User:
    """
    Получить пользователя по токену
    :param session:
    :param token:
    """
    try:
        auth_data = get_auth_data()
        payload = jwt.decode(token, auth_data.secret, algorithms=[auth_data.algorithm])
    except JWTError as ex:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Токен не валидный!')

    user_id = validate_uuid(payload.get('sub'), er_status=status.HTTP_401_UNAUTHORIZED,
                            er_msg="Не найден ID пользователя")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Не найден ID пользователя')
    return await User.get_or_404(id=user_id, session=session, er_status=status.HTTP_401_UNAUTHORIZED)


async def get_current_user_and_device(token: str = Depends(get_token),
                                      session: AsyncSession = Depends(get_db)) -> tuple[User, str]:
    """
    Получить пользователя по токену
    :param session:
    :param token:
    """
    try:
        auth_data = get_auth_data()
        payload = jwt.decode(token, auth_data.secret, algorithms=[auth_data.algorithm])
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Токен не валидный!')

    user_id = validate_uuid(payload.get('sub'))
    device_id = payload.get('device_id')
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Не найден ID пользователя')
    if not device_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Не найден ID устройства')
    user = await User.get_or_404(id=user_id, session=session, er_status=status.HTTP_401_UNAUTHORIZED)
    return user, device_id


async def get_current_ws_user(token: str = Depends(get_ws_token),
                              session: AsyncSession = Depends(get_db)) -> User:
    try:
        auth_data = get_auth_data()
        payload = jwt.decode(token, auth_data.secret, algorithms=[auth_data.algorithm])
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Токен не валидный!')
    user_id = validate_uuid(payload.get('sub'))
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Не найден ID пользователя')
    return await User.get_or_404(id=user_id, session=session, er_status=status.HTTP_401_UNAUTHORIZED)


async def get_admin_user(token: str = Depends(get_token),
                         session: AsyncSession = Depends(get_db)) -> User | None:
    """
    Получить админа
    """
    user = await get_current_user(token, session=session)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='UNAUTHORIZED')
    if user.is_admin:
        return user
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Нет прав доступа')

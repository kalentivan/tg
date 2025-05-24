from fastapi import Depends, HTTPException
from jose import JWTError, jwt
from pydantic import EmailStr
from starlette import status

from app.auth.config import get_auth_data
from app.auth.password import verify_password
from app.auth.token import get_token
from app.models.models import User


async def authenticate_user(email: EmailStr,
                            password: str) -> User | None:
    """
    Валидация пользователя
    """
    user = await User.first(email=str(email))
    if not user or verify_password(plain_password=password, hashed_password=user.password) is False:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='UNAUTHORIZED')
    return user


async def get_current_user(token: str = Depends(get_token), db: AsyncSession = Depends(get_db)) -> User:
    try:
        auth_data = get_auth_data()
        payload = jwt.decode(token, auth_data.secret, algorithms=[auth_data.algorithm])
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Токен не валидный!')
    user_id = payload.get('sub')
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Не найден ID пользователя')
    return await User.get_or_404(id=user_id, session=db, is_active=True)


async def get_current_ws_user(token: str = Depends(get_ws_token), db: AsyncSession = Depends(get_db)) -> User:
    try:
        auth_data = get_auth_data()
        payload = jwt.decode(token, auth_data.secret, algorithms=[auth_data.algorithm])
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Токен не валидный!')
    user_id = payload.get('sub')
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Не найден ID пользователя')
    return await User.get_or_404(id=user_id, session=db, is_active=True)


async def get_admin_user(token: str = Depends(get_token)) -> User | None:
    """
    Получить админа
    """
    user = await get_current_user(token)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='UNAUTHORIZED')
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Нет прав доступа')

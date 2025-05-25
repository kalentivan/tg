import uuid
from datetime import datetime, timedelta, timezone

from jwt import InvalidTokenError
from sqlalchemy import update
from starlette import status
from starlette.exceptions import HTTPException

from app.auth.config import settings
from app.auth.my_jwt import JWTAuth
from app.auth.password import get_password_hash, verify_password
from app.auth.types import TokenType
from app.auth.utils import check_revoked, generate_device_id
from app.dto import TokensDTO, UserPwdDTO
from app.models.models import IssuedJWTToken, User
from app.tools import validate_uuid


class AuthService:
    """
    Регистрация пользователя, вход, выход пользователя
    """

    def __init__(self) -> None:
        self._jwt_auth = JWTAuth()

    async def register(self,
                       data: UserPwdDTO,
                       session) -> tuple[User | None, TokensDTO | None]:
        """Регистрация пользователя. Создать пользователя, создать токены"""
        if await User.first(email=data.email, session=session):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='CONFLICT')

        user = User(id=uuid.uuid4(), email=data.email, username=data.username,
                    password=get_password_hash(data.password))
        session.add(user)
        await session.flush()  # <== Заставляет SQLAlchemy сгенерировать ID и выполнить INSERT в БД

        access_token, refresh_token, notes = self._issue_tokens_for_user(user=user)
        for note in notes:
            session.add(note)
        await session.commit()
        return user, TokensDTO(
            access_token=access_token,
            refresh_token=refresh_token,
            access_ttl=settings.ACCESS_TOKEN_TTL.total_seconds(),
            refresh_ttl=settings.REFRESH_TOKEN_TTL.total_seconds(), )

    async def login(self,
                    data: UserPwdDTO,
                    session) -> TokensDTO | None:
        """Вход пользователя"""
        user = await User.get_or_404(email=data.email,
                                     session=session,
                                     er_status=status.HTTP_401_UNAUTHORIZED)
        if not verify_password(data.password, user.password):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='HTTP_401_UNAUTHORIZED')
        access_token, refresh_token, notes = self._issue_tokens_for_user(user=user)  # создать пользователя
        for note in notes:
            session.add(note)
        await session.commit()
        return TokensDTO(
            user_id=str(user.id),
            role=user.role,
            access_token=access_token,
            refresh_token=refresh_token,
            access_ttl=settings.ACCESS_TOKEN_TTL.total_seconds(),
            refresh_ttl=settings.REFRESH_TOKEN_TTL.total_seconds())

    @classmethod
    async def logout(cls,
                     user: User,
                     device_id: str,
                     session) -> None:
        """
        Выход пользователя
        :param user: пользователь
        :param device_id: устройство, с которого вошел пользователь, выход выполняется только для него.
        :return:
        """
        await session.execute((
            update(IssuedJWTToken)
            .where(IssuedJWTToken.user_id == user.id,
                   IssuedJWTToken.device_id == device_id)
            .values(revoked=True)
        ))
        await session.commit()

    async def update_tokens(self,
                            user: User,
                            refresh_token: str, session) -> TokensDTO | None:
        """Обновить токены"""
        try:
            payload = self._jwt_auth.verify_token(refresh_token)
        except InvalidTokenError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Некорректный токен')
        if payload['type'] != TokenType.REFRESH.value:  # проверка, что тип токена REFRESH
            return None

        user_id = payload['sub']
        user_id = user_id if not isinstance(user_id, str) else uuid.UUID(user_id)
        user = await User.first(id=user_id, session=session)

        if await check_revoked(payload['jti'], session=session):
            await session.execute((
                update(IssuedJWTToken)
                .where(IssuedJWTToken.user_id == user.id)
                .values(revoked=True)
            ))
            await session.commit()
            return None

        device_id = payload['device_id']
        await session.execute((
            update(IssuedJWTToken)
            .where(IssuedJWTToken.user_id == user.id,
                   IssuedJWTToken.device_id == device_id)
            .values(revoked=True)
        ))
        access_token, refresh_token, notes = self._issue_tokens_for_user(user, device_id)  # создать новые токены
        for note in notes:
            session.add(note)
        await session.commit()
        return TokensDTO(
            user_id=payload['sub'],
            role=user.role,
            access_token=access_token,
            refresh_token=refresh_token,
            access_ttl=settings.ACCESS_TOKEN_TTL.total_seconds(),
            refresh_ttl=settings.REFRESH_TOKEN_TTL.total_seconds(),
        )

    def _issue_tokens_for_user(self,
                               user: User,
                               device_id: str = generate_device_id()) -> tuple[str, str, list[IssuedJWTToken]]:
        """
        Создать токены
        :param user:
        :param device_id: id устройства пользователя
        :return:
        """
        access_token = self._jwt_auth.generate_access_token(subject=str(user.id), payload={'device_id': str(device_id)})
        refresh_token = self._jwt_auth.generate_refresh_token(subject=str(user.id), payload={'device_id': str(device_id)})
        notes = []
        # создаем записи о токенах для БД (без коммита)
        for token in [access_token, refresh_token]:
            token_payload = self._jwt_auth.get_raw_jwt(token)
            expired_time = datetime.fromtimestamp(token_payload['exp'], tz=timezone.utc)
            notes.append(IssuedJWTToken(
                user_id=user.id,
                jti=validate_uuid(token_payload['jti']),
                device_id=device_id,
                expired_time=expired_time
            ))
        return access_token, refresh_token, notes

from jwt import InvalidTokenError

from app.auth.my_jwt import JWTAuth


def try_decode_token(jwt_auth: JWTAuth,
                     token: str) -> tuple[dict, None] | tuple[None, InvalidTokenError]:
    """

    :param jwt_auth:
    :param token:
    :return:
    """
    try:
        payload = jwt_auth.verify_token(token)
        return payload, None
    except InvalidTokenError as error:
        return None, error

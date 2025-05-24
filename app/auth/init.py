from app.auth.service import AuthService


def get_auth_service() -> AuthService:
    return AuthService()

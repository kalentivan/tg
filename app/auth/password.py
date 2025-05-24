from fastapi.security import HTTPBasic
from passlib.context import CryptContext
from passlib.hash import django_pbkdf2_sha256

security = HTTPBasic()
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def get_password_hash(password: str) -> str:
    if not password:
        return password
    return django_pbkdf2_sha256.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    if not hashed_password:
        return False
    return django_pbkdf2_sha256.verify(plain_password, hashed_password)

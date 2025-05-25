from enum import Enum, unique


@unique
class TokenType(str, Enum):
    ACCESS = 'access'
    REFRESH = 'refresh'

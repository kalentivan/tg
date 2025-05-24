import uuid

from starlette import status
from starlette.exceptions import HTTPException


def validate_uuid(item_id: str, er_status=status.HTTP_400_BAD_REQUEST,
                  er_msg="Invalid validate_uuid ID format") -> uuid.UUID | None:
    if isinstance(item_id, uuid.UUID):
        return item_id
    try:
        if not item_id:
            return None
        return uuid.UUID(item_id)
    except ValueError:
        raise HTTPException(status_code=er_status, detail=er_msg)

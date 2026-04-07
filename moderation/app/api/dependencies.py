from fastapi import Header, HTTPException, status
from uuid import UUID


async def get_current_moderator_id(
    x_moderator_id: str = Header(..., alias="X-Moderator-Id")
) -> UUID:
    """
    Получить ID текущего модератора из заголовка.
    В реальном проекте здесь будет проверка JWT токена.
    """
    try:
        return UUID(x_moderator_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid X-Moderator-Id format"
        )